# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""EditorWidget and EditorMainWindow widgets."""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import logging
import os.path as osp
import sys

# Third party imports
import qstylizer.style
from qtpy.QtCore import QByteArray, QEvent, QPoint, QSize, Qt, Signal, Slot
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QAction, QApplication, QMainWindow, QSplitter,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.plugins import Plugins
from spyder.api.config.decorators import on_conf_change
from spyder.api.config.mixins import SpyderConfigurationObserver
from spyder.api.widgets.toolbars import ApplicationToolbar
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _
from spyder.plugins.editor.widgets.splitter import EditorSplitter
from spyder.plugins.editor.widgets.status import (CursorPositionStatus,
                                                  EncodingStatus, EOLStatus,
                                                  ReadWriteStatus, VCSStatus)
from spyder.plugins.mainmenu.api import (
    ApplicationMenu,
    ApplicationMenus,
    MENUBAR_STYLESHEET,
)
from spyder.plugins.outlineexplorer.main_widget import OutlineExplorerWidget
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.py3compat import qbytearray_to_str
from spyder.utils.palette import SpyderPalette
from spyder.utils.qthelpers import create_toolbutton
from spyder.utils.stylesheet import APP_STYLESHEET
from spyder.widgets.findreplace import FindReplace


logger = logging.getLogger(__name__)


# ---- Constants
# -----------------------------------------------------------------------------
class EditorMainWindowMenus:
    View = "view"


class ViewMenuSections:
    Outline = "outline"
    Toolbars = "toolbars"


class EditorMainWindowActions:
    ToggleOutline = "toggle_outline"


# ---- Widgets
# -----------------------------------------------------------------------------
class OutlineExplorerInEditorWindow(OutlineExplorerWidget):

    sig_collapse_requested = Signal()

    @Slot()
    def close_dock(self):
        """
        Reimplemented to preserve the widget's visible state when shown in an
        editor window.
        """
        self.sig_collapse_requested.emit()


class EditorWidget(QSplitter, SpyderConfigurationObserver):
    """Main widget to show in EditorMainWindow."""

    CONF_SECTION = 'editor'
    SPLITTER_WIDTH = "7px"

    def __init__(self, parent, main_widget, menu_actions, outline_plugin):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # ---- Attributes
        self.editorstacks = []
        self.main_widget = main_widget
        self._sizes = None

        # This needs to be done at this point to avoid an error at startup
        self._splitter_css = self._generate_splitter_stylesheet()

        # ---- Find widget
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()

        # ---- Status bar
        statusbar = parent.statusBar()
        self.vcs_status = VCSStatus(self)
        self.cursorpos_status = CursorPositionStatus(self)
        self.encoding_status = EncodingStatus(self)
        self.eol_status = EOLStatus(self)
        self.readwrite_status = ReadWriteStatus(self)

        statusbar.insertPermanentWidget(0, self.readwrite_status)
        statusbar.insertPermanentWidget(0, self.eol_status)
        statusbar.insertPermanentWidget(0, self.encoding_status)
        statusbar.insertPermanentWidget(0, self.cursorpos_status)
        statusbar.insertPermanentWidget(0, self.vcs_status)

        # ---- Outline.
        self.outlineexplorer = None
        if outline_plugin is not None:
            self.outlineexplorer = OutlineExplorerInEditorWindow(
                'outline_explorer',
                outline_plugin,
                self,
                context=f'editor_window_{str(id(self))}'
            )

            # Show widget's toolbar
            self.outlineexplorer.setup()
            self.outlineexplorer.update_actions()
            self.outlineexplorer._setup()
            self.outlineexplorer.render_toolbars()

            # Remove bottom section actions from Options menu because they
            # don't apply here.
            options_menu = self.outlineexplorer.get_options_menu()
            for action in ['undock_pane', 'lock_unlock_position']:
                options_menu.remove_action(action)

            # Signals
            self.outlineexplorer.edit_goto.connect(
                lambda filenames, goto, word:
                main_widget.load(filenames=filenames, goto=goto, word=word,
                                 editorwindow=self.parent())
            )

            self.outlineexplorer.sig_collapse_requested.connect(
                lambda: self.set_conf("show_outline_in_editor_window", False)
            )

            # Start symbol services for all supported languages
            for language in outline_plugin.get_supported_languages():
                self.outlineexplorer.start_symbol_services(language)

            # Tell Outline's treewidget that is visible
            self.outlineexplorer.change_tree_visibility(True)

        # ---- Editor widgets
        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setSpacing(0)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        self.editorsplitter = EditorSplitter(
            self,
            main_widget,
            menu_actions,
            register_editorstack_cb=self.register_editorstack,
            unregister_editorstack_cb=self.unregister_editorstack
        )
        editor_layout.addWidget(self.editorsplitter)
        editor_layout.addWidget(self.find_widget)

        # ---- Splitter
        self.splitter = QSplitter(self)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        if self.outlineexplorer is not None:
            self.splitter.addWidget(self.outlineexplorer)
        self.splitter.addWidget(editor_widgets)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)

        # This sets the same UX as the one users encounter when the editor is
        # maximized.
        self.splitter.setChildrenCollapsible(False)

        self.splitter.splitterMoved.connect(self.on_splitter_moved)

        if (
            self.outlineexplorer is not None
            and not self.get_conf("show_outline_in_editor_window")
        ):
            self.outlineexplorer.close_dock()

        # ---- Style
        self.splitter.setStyleSheet(self._splitter_css.toString())

    def register_editorstack(self, editorstack):
        logger.debug("Registering editorstack")
        self.__print_editorstacks()

        self.editorstacks.append(editorstack)
        self.main_widget.last_focused_editorstack[self.parent()] = editorstack
        editorstack.set_closable(len(self.editorstacks) > 1)
        editorstack.set_outlineexplorer(self.outlineexplorer)
        editorstack.set_find_widget(self.find_widget)
        editorstack.reset_statusbar.connect(self.readwrite_status.hide)
        editorstack.reset_statusbar.connect(self.encoding_status.hide)
        editorstack.reset_statusbar.connect(self.cursorpos_status.hide)
        editorstack.readonly_changed.connect(
            self.readwrite_status.update_readonly)
        editorstack.encoding_changed.connect(
            self.encoding_status.update_encoding)
        editorstack.sig_editor_cursor_position_changed.connect(
            self.cursorpos_status.update_cursor_position)
        editorstack.sig_refresh_eol_chars.connect(self.eol_status.update_eol)
        self.main_widget.register_editorstack(editorstack)

    def __print_editorstacks(self):
        logger.debug(
            f"{len(self.editorstacks)} editorstack(s) in EditorWidget:"
        )
        for es in self.editorstacks:
            logger.debug(f"    {es}")

    def _generate_splitter_stylesheet(self):
        # Set background color to be the same as the one used in any other
        # widget. This removes what appears to be some extra borders in several
        # places.
        css = qstylizer.style.StyleSheet()
        css.QSplitter.setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_1
        )

        # Make splitter handle to have the same size as the QMainWindow
        # separators. That's because the editor and outline are shown like
        # this when the editor is maximized.
        css['QSplitter::handle'].setValues(
            width=self.SPLITTER_WIDTH,
            height=self.SPLITTER_WIDTH
        )

        return css

    def unregister_editorstack(self, editorstack):
        logger.debug("Unregistering editorstack")
        self.main_widget.unregister_editorstack(editorstack)
        self.editorstacks.pop(self.editorstacks.index(editorstack))
        self.__print_editorstacks()

    def unregister_all_editorstacks(self):
        logger.debug("Unregistering all editorstacks")
        for es in self.editorstacks:
            es.close()

    @Slot(object)
    def on_window_state_changed(self, window_state):
        """
        Actions to take when the parent window state has changed.
        """
        # There's no need to update the Outline when the window is minimized
        if window_state == Qt.WindowMinimized:
            self.outlineexplorer.change_tree_visibility(False)
        else:
            self.outlineexplorer.change_tree_visibility(True)

    def on_splitter_moved(self, position, index):
        """Actions to take when the splitter is moved."""
        # There's no need to update the Outline when the user moves the
        # splitter to hide it.
        # Note: The 20 below was selected because the Outline can't have that
        # small width. So, if the splitter position plus that amount is greater
        # than the total widget width, it means the Outline was collapsed.
        if (position + 20) > self.size().width():
            self.outlineexplorer.change_tree_visibility(False)
        else:
            self.outlineexplorer.change_tree_visibility(True)

    @on_conf_change(option='show_outline_in_editor_window')
    def toggle_outlineexplorer(self, value):
        """Toggle outline explorer visibility."""
        if value:
            # When self._sizes is not available, the splitter sizes are set
            # automatically by the ratios set for it above.
            if self._sizes is not None:
                self.splitter.setSizes(self._sizes)

            # Show and enable splitter handle
            self._splitter_css['QSplitter::handle'].setValues(
                width=self.SPLITTER_WIDTH,
                height=self.SPLITTER_WIDTH
            )
            self.splitter.setStyleSheet(self._splitter_css.toString())
            if self.splitter.handle(1) is not None:
                self.splitter.handle(1).setEnabled(True)
        else:
            self._sizes = self.splitter.sizes()
            self.splitter.setChildrenCollapsible(True)

            # Collapse Outline
            self.splitter.moveSplitter(0, 1)

            # Hide and disable splitter handle
            self._splitter_css['QSplitter::handle'].setValues(
                width="0px",
                height="0px"
            )
            self.splitter.setStyleSheet(self._splitter_css.toString())
            if self.splitter.handle(1) is not None:
                self.splitter.handle(1).setEnabled(False)

            self.splitter.setChildrenCollapsible(False)


class EditorMainWindow(QMainWindow, SpyderWidgetMixin):
    CONF_SECTION = "editor"

    sig_window_state_changed = Signal(object)

    def __init__(self, main_widget, menu_actions, outline_plugin, parent=None):
        # Parent needs to be `None` if the created widget is meant to be
        # independent. See spyder-ide/spyder#17803
        super().__init__(parent, class_parent=main_widget)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # ---- Attributes
        self.main_widget = main_widget
        self.window_size = None
        self.toolbars = []

        # ---- Main widget
        self.editorwidget = EditorWidget(
            self,
            main_widget,
            menu_actions,
            outline_plugin
        )
        self.sig_window_state_changed.connect(
            self.editorwidget.on_window_state_changed
        )
        self.setCentralWidget(self.editorwidget)

        # ---- Style
        self.setStyleSheet(str(APP_STYLESHEET))
        if not sys.platform == "darwin":
            self.menuBar().setStyleSheet(str(MENUBAR_STYLESHEET))

        # Give focus to current editor to update/show all status bar widgets
        editorstack = self.editorwidget.editorsplitter.editorstack
        editor = editorstack.get_current_editor()
        if editor is not None:
            editor.setFocus()

        self.setWindowTitle("Spyder - %s" % main_widget.windowTitle())
        self.setWindowIcon(main_widget.windowIcon())

        # ---- Add toolbars
        toolbar_list = [
            ApplicationToolbars.File,
            ApplicationToolbars.Run,
            ApplicationToolbars.Debug
        ]

        for toolbar_id in toolbar_list:
            # This is necessary to run tests for this widget without Spyder's
            # main window
            try:
                toolbar = self.get_toolbar(toolbar_id, plugin=Plugins.Toolbar)
            except KeyError:
                continue

            new_toolbar = ApplicationToolbar(self, toolbar_id, toolbar._title)
            for action in toolbar.actions():
                new_toolbar.add_item(action)

            new_toolbar.render()
            new_toolbar.setMovable(False)

            self.addToolBar(new_toolbar)
            self.toolbars.append(new_toolbar)

        # ---- Add menus
        menu_list = [
            ApplicationMenus.File,
            ApplicationMenus.Edit,
            ApplicationMenus.Search,
            ApplicationMenus.Source,
            ApplicationMenus.Run,
            ApplicationMenus.Tools,
            EditorMainWindowMenus.View,
            ApplicationMenus.Help
        ]

        for menu_id in menu_list:
            if menu_id == EditorMainWindowMenus.View:
                view_menu = self._create_view_menu()
                self.menuBar().addMenu(view_menu)
            else:
                # This is necessary to run tests for this widget without
                # Spyder's main window
                try:
                    self.menuBar().addMenu(
                        self.get_menu(menu_id, plugin=Plugins.MainMenu)
                    )
                except KeyError:
                    continue

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def resizeEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.isFullScreen():
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)

    def closeEvent(self, event):
        """Reimplement Qt method"""
        self.editorwidget.unregister_all_editorstacks()
        if self.main_widget.windowwidget is not None:
            self.main_widget.dockwidget.setWidget(self.main_widget)
            self.main_widget.dockwidget.setVisible(True)
        self.main_widget.switch_to_plugin()
        QMainWindow.closeEvent(self, event)
        if self.main_widget.windowwidget is not None:
            self.main_widget.windowwidget = None

    def changeEvent(self, event):
        """
        Override Qt method to emit a custom `sig_windowstate_changed` signal
        when there's a change in the window state.
        """
        if event.type() == QEvent.WindowStateChange:
            self.sig_window_state_changed.emit(self.windowState())
        super().changeEvent(event)

    # ---- Public API
    # -------------------------------------------------------------------------
    def get_layout_settings(self):
        """Return layout state"""
        splitsettings = self.editorwidget.editorsplitter.get_layout_settings()
        return dict(size=(self.window_size.width(), self.window_size.height()),
                    pos=(self.pos().x(), self.pos().y()),
                    is_maximized=self.isMaximized(),
                    is_fullscreen=self.isFullScreen(),
                    hexstate=qbytearray_to_str(self.saveState()),
                    splitsettings=splitsettings)

    def set_layout_settings(self, settings):
        """Restore layout state"""
        size = settings.get('size')
        if size is not None:
            self.resize(QSize(*size))
            self.window_size = self.size()
        pos = settings.get('pos')
        if pos is not None:
            self.move(QPoint(*pos))
        hexstate = settings.get('hexstate')
        if hexstate is not None:
            self.restoreState(
                QByteArray().fromHex(str(hexstate).encode('utf-8'))
            )
        if settings.get('is_maximized'):
            self.setWindowState(Qt.WindowMaximized)
        if settings.get('is_fullscreen'):
            self.setWindowState(Qt.WindowFullScreen)
        splitsettings = settings.get('splitsettings')
        if splitsettings is not None:
            self.editorwidget.editorsplitter.set_layout_settings(splitsettings)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _create_view_menu(self):
        # Create menu
        view_menu = self._create_menu(
            menu_id=EditorMainWindowMenus.View,
            parent=self,
            title=_("&View"),
            register=False,
            MenuClass=ApplicationMenu
        )

        # Create Outline action
        self.toggle_outline_action = self.create_action(
            EditorMainWindowActions.ToggleOutline,
            _("Outline"),
            toggled=True,
            option="show_outline_in_editor_window"
        )

        view_menu.add_action(
            self.toggle_outline_action,
            section=ViewMenuSections.Outline
        )

        # Add toolbar toggle view actions
        visible_toolbars = self.get_conf(
            'last_visible_toolbars',
            section='toolbar'
        )

        for toolbar in self.toolbars:
            toolbar_action = toolbar.toggleViewAction()
            toolbar_action.action_id = f'toolbar_{toolbar.ID}'

            if toolbar.ID not in visible_toolbars:
                toolbar_action.setChecked(False)
                toolbar.setVisible(False)
            else:
                toolbar_action.setChecked(True)
                toolbar.setVisible(True)

            view_menu.add_action(
                toolbar_action,
                section=ViewMenuSections.Toolbars
            )

        return view_menu


class EditorMainWidgetExample(QSplitter):
    def __init__(self):
        QSplitter.__init__(self)

        self._plugin = None

        self.dock_action = None
        self.undock_action = None
        self.close_action = None
        self.windowwidget = None
        self.lock_unlock_action = None
        menu_actions = []

        self.editorstacks = []
        self.editorwindows = []

        self.last_focused_editorstack = {}  # fake

        self.find_widget = FindReplace(self, enable_replace=True)
        self.outlineexplorer = OutlineExplorerWidget(None, self, self)
        self.outlineexplorer.edit_goto.connect(self.go_to_file)
        self.editor_splitter = EditorSplitter(self, self, menu_actions,
                                              first=True,
                                              use_switcher=False)

        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setSpacing(0)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        editor_layout.addWidget(self.editor_splitter)
        editor_layout.addWidget(self.find_widget)

        self.setContentsMargins(0, 0, 0, 0)
        self.addWidget(editor_widgets)
        self.addWidget(self.outlineexplorer)

        self.setStretchFactor(0, 5)
        self.setStretchFactor(1, 1)

        self.menu_actions = menu_actions
        self.toolbar_list = None
        self.menu_list = None
        self.setup_window([], [])

    def go_to_file(self, fname, lineno, text='', start_column=None):
        editorstack = self.editorstacks[0]
        editorstack.set_current_filename(str(fname))
        editor = editorstack.get_current_editor()
        editor.go_to_line(lineno, word=text, start_column=start_column)

    def closeEvent(self, event):
        for win in self.editorwindows[:]:
            win.close()
        logger.debug("%d: %r" % (len(self.editorwindows), self.editorwindows))
        logger.debug("%d: %r" % (len(self.editorstacks), self.editorstacks))
        event.accept()

    def load(self, fname):
        QApplication.processEvents()
        editorstack = self.editorstacks[0]
        editorstack.load(fname)
        editorstack.analyze_script()

    def register_editorstack(self, editorstack):
        logger.debug(
            "FakeEditorMainWidget.register_editorstack: %r" % editorstack
        )
        self.editorstacks.append(editorstack)
        if self.isAncestorOf(editorstack):
            # editorstack is a child of the EditorMainWidget
            editorstack.set_closable(len(self.editorstacks) > 1)
            editorstack.set_outlineexplorer(self.outlineexplorer)
            editorstack.set_find_widget(self.find_widget)
            oe_btn = create_toolbutton(self)
            editorstack.add_corner_widgets_to_tabbar([5, oe_btn])

        action = QAction(self)
        editorstack.set_io_actions(action, action, action, action)
        font = QFont("Courier New")
        font.setPointSize(10)
        editorstack.set_default_font(font, color_scheme='Spyder')

        editorstack.sig_close_file.connect(self.close_file_in_all_editorstacks)
        editorstack.file_saved.connect(self.file_saved_in_editorstack)
        editorstack.file_renamed_in_data.connect(
                                      self.file_renamed_in_data_in_editorstack)
        editorstack.plugin_load.connect(self.load)

    def unregister_editorstack(self, editorstack):
        logger.debug(
            "EditorMainWidget.unregister_editorstack: %r" % editorstack
        )
        self.editorstacks.pop(self.editorstacks.index(editorstack))

    def clone_editorstack(self, editorstack):
        editorstack.clone_from(self.editorstacks[0])

    def setup_window(self, toolbar_list, menu_list):
        self.toolbar_list = toolbar_list
        self.menu_list = menu_list

    def create_new_window(self):
        window = EditorMainWindow(self, self.menu_actions,
                                  self.toolbar_list, self.menu_list,
                                  show_fullpath=False, show_all_files=False,
                                  group_cells=True, show_comments=True,
                                  sort_files_alphabetically=False)
        window.resize(self.size())
        window.show()
        self.register_editorwindow(window)
        window.destroyed.connect(lambda: self.unregister_editorwindow(window))

    def register_editorwindow(self, window):
        logger.debug("register_editorwindowQObject*: %r" % window)
        self.editorwindows.append(window)

    def unregister_editorwindow(self, window):
        logger.debug("unregister_editorwindow: %r" % window)
        self.editorwindows.pop(self.editorwindows.index(window))

    def get_focus_widget(self):
        pass

    @Slot(str, str)
    def close_file_in_all_editorstacks(self, editorstack_id_str, filename):
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.blockSignals(True)
                index = editorstack.get_index_from_filename(filename)
                editorstack.close_file(index, force=True)
                editorstack.blockSignals(False)

    # This method is never called in this plugin example. It's here only
    # to show how to use the file_saved signal (see above).
    @Slot(str, str, str)
    def file_saved_in_editorstack(self, editorstack_id_str,
                                  original_filename, filename):
        """A file was saved in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.file_saved_in_other_editorstack(original_filename,
                                                            filename)

    # This method is never called in this plugin example. It's here only
    # to show how to use the file_saved signal (see above).
    @Slot(str, str, str)
    def file_renamed_in_data_in_editorstack(
        self, original_filename, filename, editorstack_id_str
    ):
        """A file was renamed in data in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.rename_in_data(original_filename, filename)

    def _get_color_scheme(self):
        pass


def test():
    from spyder.utils.qthelpers import qapplication
    from spyder.config.base import get_module_path

    spyder_dir = get_module_path('spyder')
    app = qapplication(test_time=8)

    test = EditorMainWidgetExample()
    test.resize(900, 700)
    test.show()

    import time
    t0 = time.time()
    test.load(osp.join(spyder_dir, "widgets", "collectionseditor.py"))
    test.load(osp.join(spyder_dir, "plugins", "editor", "widgets",
                       "window.py"))
    test.load(osp.join(spyder_dir, "plugins", "explorer", "widgets",
                       'explorer.py'))
    test.load(osp.join(spyder_dir, "plugins", "editor", "widgets",
                       "codeeditor", "codeeditor.py"))
    print("Elapsed time: %.3f s" % (time.time()-t0))  # spyder: test-skip

    sys.exit(app.exec_())


if __name__ == "__main__":
    test()

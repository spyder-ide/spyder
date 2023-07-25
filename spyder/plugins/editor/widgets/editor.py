# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Widget"""

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
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.config.base import _, running_under_pytest
from spyder.plugins.editor.widgets.editorstack import EditorStack
from spyder.plugins.editor.widgets.status import (CursorPositionStatus,
                                                  EncodingStatus, EOLStatus,
                                                  ReadWriteStatus, VCSStatus)
from spyder.plugins.outlineexplorer.main_widget import OutlineExplorerWidget
from spyder.py3compat import qbytearray_to_str, to_text_string
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton)
from spyder.utils.stylesheet import APP_STYLESHEET, APP_TOOLBAR_STYLESHEET
from spyder.widgets.findreplace import FindReplace


logger = logging.getLogger(__name__)


class EditorSplitter(QSplitter):
    """QSplitter for editor windows."""

    def __init__(self, parent, plugin, menu_actions, first=False,
                 register_editorstack_cb=None, unregister_editorstack_cb=None,
                 use_switcher=True):
        """Create a splitter for dividing an editor window into panels.

        Adds a new EditorStack instance to this splitter.  If it's not
        the first splitter, clones the current EditorStack from the plugin.

        Args:
            parent: Parent widget.
            plugin: Plugin this widget belongs to.
            menu_actions: QActions to include from the parent.
            first: Boolean if this is the first splitter in the editor.
            register_editorstack_cb: Callback to register the EditorStack.
                        Defaults to plugin.register_editorstack() to
                        register the EditorStack with the Editor plugin.
            unregister_editorstack_cb: Callback to unregister the EditorStack.
                        Defaults to plugin.unregister_editorstack() to
                        unregister the EditorStack with the Editor plugin.
        """

        QSplitter.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setChildrenCollapsible(False)

        self.toolbar_list = None
        self.menu_list = None

        self.plugin = plugin

        if register_editorstack_cb is None:
            register_editorstack_cb = self.plugin.register_editorstack
        self.register_editorstack_cb = register_editorstack_cb
        if unregister_editorstack_cb is None:
            unregister_editorstack_cb = self.plugin.unregister_editorstack
        self.unregister_editorstack_cb = unregister_editorstack_cb

        self.menu_actions = menu_actions
        self.editorstack = EditorStack(self, menu_actions, use_switcher)
        self.register_editorstack_cb(self.editorstack)
        if not first:
            self.plugin.clone_editorstack(editorstack=self.editorstack)
        self.editorstack.destroyed.connect(self.editorstack_closed)
        self.editorstack.sig_split_vertically.connect(
            lambda: self.split(orientation=Qt.Vertical))
        self.editorstack.sig_split_horizontally.connect(
            lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editorstack)

        if not running_under_pytest():
            self.editorstack.set_color_scheme(plugin.get_color_scheme())

        self.setStyleSheet(self._stylesheet)

    def closeEvent(self, event):
        """Override QWidget closeEvent().

        This event handler is called with the given event when Qt
        receives a window close request from a top-level widget.
        """
        QSplitter.closeEvent(self, event)

    def __give_focus_to_remaining_editor(self):
        focus_widget = self.plugin.get_focus_widget()
        if focus_widget is not None:
            focus_widget.setFocus()

    @Slot()
    def editorstack_closed(self):
        logger.debug("Closing EditorStack")

        try:
            self.unregister_editorstack_cb(self.editorstack)
            self.editorstack = None
            close_splitter = self.count() == 1
            if close_splitter:
                # editorstack just closed was the last widget in this QSplitter
                self.close()
                return
            self.__give_focus_to_remaining_editor()
        except (RuntimeError, AttributeError):
            # editorsplitter has been destroyed (happens when closing a
            # EditorMainWindow instance)
            return

    def editorsplitter_closed(self):
        logger.debug("Closing EditorSplitter")
        try:
            close_splitter = self.count() == 1 and self.editorstack is None
        except RuntimeError:
            # editorsplitter has been destroyed (happens when closing a
            # EditorMainWindow instance)
            return

        if close_splitter:
            # editorsplitter just closed was the last widget in this QSplitter
            self.close()
            return
        elif self.count() == 2 and self.editorstack:
            # back to the initial state: a single editorstack instance,
            # as a single widget in this QSplitter: orientation may be changed
            self.editorstack.reset_orientation()

        self.__give_focus_to_remaining_editor()

    def split(self, orientation=Qt.Vertical):
        """Create and attach a new EditorSplitter to the current EditorSplitter.

        The new EditorSplitter widget will contain an EditorStack that
        is a clone of the current EditorStack.

        A single EditorSplitter instance can be split multiple times, but the
        orientation will be the same for all the direct splits.  If one of
        the child splits is split, then that split can have a different
        orientation.
        """
        logger.debug("Create a new EditorSplitter")
        self.setOrientation(orientation)
        self.editorstack.set_orientation(orientation)
        editorsplitter = EditorSplitter(
            self.parent(),
            self.plugin,
            self.menu_actions,
            register_editorstack_cb=self.register_editorstack_cb,
            unregister_editorstack_cb=self.unregister_editorstack_cb
        )
        self.addWidget(editorsplitter)
        editorsplitter.destroyed.connect(self.editorsplitter_closed)
        current_editor = editorsplitter.editorstack.get_current_editor()
        if current_editor is not None:
            current_editor.setFocus()

    def iter_editorstacks(self):
        """Return the editor stacks for this splitter and every first child.

        Note: If a splitter contains more than one splitter as a direct
              child, only the first child's editor stack is included.

        Returns:
            List of tuples containing (EditorStack instance, orientation).
        """
        editorstacks = [(self.widget(0), self.orientation())]
        if self.count() > 1:
            editorsplitter = self.widget(1)
            editorstacks += editorsplitter.iter_editorstacks()
        return editorstacks

    def get_layout_settings(self):
        """Return the layout state for this splitter and its children.

        Record the current state, including file names and current line
        numbers, of the splitter panels.

        Returns:
            A dictionary containing keys {hexstate, sizes, splitsettings}.
                hexstate: String of saveState() for self.
                sizes: List for size() for self.
                splitsettings: List of tuples of the form
                       (orientation, cfname, clines) for each EditorSplitter
                       and its EditorStack.
                           orientation: orientation() for the editor
                                 splitter (which may be a child of self).
                           cfname: EditorStack current file name.
                           clines: Current line number for each file in the
                               EditorStack.
        """
        splitsettings = []
        for editorstack, orientation in self.iter_editorstacks():
            clines = []
            cfname = ''
            # XXX - this overrides value from the loop to always be False?
            orientation = False
            if hasattr(editorstack, 'data'):
                clines = [finfo.editor.get_cursor_line_number()
                          for finfo in editorstack.data]
                cfname = editorstack.get_current_filename()
            splitsettings.append((orientation == Qt.Vertical, cfname, clines))
        return dict(hexstate=qbytearray_to_str(self.saveState()),
                    sizes=self.sizes(), splitsettings=splitsettings)

    def set_layout_settings(self, settings, dont_goto=None):
        """Restore layout state for the splitter panels.

        Apply the settings to restore a saved layout within the editor.  If
        the splitsettings key doesn't exist, then return without restoring
        any settings.

        The current EditorSplitter (self) calls split() for each element
        in split_settings, thus recreating the splitter panels from the saved
        state.  split() also clones the editorstack, which is then
        iterated over to restore the saved line numbers on each file.

        The size and positioning of each splitter panel is restored from
        hexstate.

        Args:
            settings: A dictionary with keys {hexstate, sizes, orientation}
                    that define the layout for the EditorSplitter panels.
            dont_goto: Defaults to None, which positions the cursor to the
                    end of the editor.  If there's a value, positions the
                    cursor on the saved line number for each editor.
        """
        splitsettings = settings.get('splitsettings')
        if splitsettings is None:
            return
        splitter = self
        editor = None
        for i, (is_vertical, cfname, clines) in enumerate(splitsettings):
            if i > 0:
                splitter.split(Qt.Vertical if is_vertical else Qt.Horizontal)
                splitter = splitter.widget(1)
            editorstack = splitter.widget(0)
            for j, finfo in enumerate(editorstack.data):
                editor = finfo.editor
                # TODO: go_to_line is not working properly (the line it jumps
                # to is not the corresponding to that file). This will be fixed
                # in a future PR (which will fix spyder-ide/spyder#3857).
                if dont_goto is not None:
                    # Skip go to line for first file because is already there.
                    pass
                else:
                    try:
                        editor.go_to_line(clines[j])
                    except IndexError:
                        pass
        hexstate = settings.get('hexstate')
        if hexstate is not None:
            self.restoreState( QByteArray().fromHex(
                    str(hexstate).encode('utf-8')) )
        sizes = settings.get('sizes')
        if sizes is not None:
            self.setSizes(sizes)
        if editor is not None:
            editor.clearFocus()
            editor.setFocus()

    @property
    def _stylesheet(self):
        css = qstylizer.style.StyleSheet()
        css.QSplitter.setValues(
            background=QStylePalette.COLOR_BACKGROUND_1
        )
        return css.toString()


class EditorWidget(QSplitter):
    CONF_SECTION = 'editor'

    def __init__(self, parent, plugin, menu_actions, outline_plugin):
        QSplitter.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        statusbar = parent.statusBar()  # Create a status bar
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

        self.editorstacks = []

        self.plugin = plugin

        self.find_widget = FindReplace(self, enable_replace=True)
        self.plugin.register_widget_shortcuts(self.find_widget)
        self.find_widget.hide()

        # Set up an outline but only if its corresponding plugin is available.
        self.outlineexplorer = None
        if outline_plugin is not None:
            self.outlineexplorer = OutlineExplorerWidget(
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
            for action in ['undock_pane', 'close_pane',
                           'lock_unlock_position']:
                options_menu.remove_action(action)

            self.outlineexplorer.edit_goto.connect(
                lambda filenames, goto, word:
                plugin.load(filenames=filenames, goto=goto, word=word,
                            editorwindow=self.parent())
            )

            # Start symbol services for all supported languages
            for language in outline_plugin.get_supported_languages():
                self.outlineexplorer.start_symbol_services(language)

            # Tell Outline's treewidget that is visible
            self.outlineexplorer.change_tree_visibility(True)

        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setSpacing(0)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        self.editorsplitter = EditorSplitter(
            self,
            plugin,
            menu_actions,
            register_editorstack_cb=self.register_editorstack,
            unregister_editorstack_cb=self.unregister_editorstack
        )
        editor_layout.addWidget(self.editorsplitter)
        editor_layout.addWidget(self.find_widget)

        self.splitter = QSplitter(self)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(editor_widgets)
        if outline_plugin is not None:
            self.splitter.addWidget(self.outlineexplorer)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.splitterMoved.connect(self.on_splitter_moved)

    def register_editorstack(self, editorstack):
        logger.debug("Registering editorstack")
        self.__print_editorstacks()

        self.editorstacks.append(editorstack)
        self.plugin.last_focused_editorstack[self.parent()] = editorstack
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
        self.plugin.register_editorstack(editorstack)

    def __print_editorstacks(self):
        logger.debug(
            f"{len(self.editorstacks)} editorstack(s) in EditorWidget:"
        )
        for es in self.editorstacks:
            logger.debug(f"    {es}")

    def unregister_editorstack(self, editorstack):
        logger.debug("Unregistering editorstack")
        self.plugin.unregister_editorstack(editorstack)
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


class EditorMainWindow(QMainWindow, SpyderConfigurationAccessor):
    sig_window_state_changed = Signal(object)

    def __init__(self, plugin, menu_actions, toolbar_list, menu_list,
                 outline_plugin, parent=None):
        # Parent needs to be `None` if the the created widget is meant to be
        # independent. See spyder-ide/spyder#17803
        QMainWindow.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.plugin = plugin
        self.window_size = None

        self.editorwidget = EditorWidget(self, plugin, menu_actions,
                                         outline_plugin)
        self.sig_window_state_changed.connect(
            self.editorwidget.on_window_state_changed)
        self.setCentralWidget(self.editorwidget)

        # Setting interface theme
        self.setStyleSheet(str(APP_STYLESHEET))

        # Give focus to current editor to update/show all status bar widgets
        editorstack = self.editorwidget.editorsplitter.editorstack
        editor = editorstack.get_current_editor()
        if editor is not None:
            editor.setFocus()

        self.setWindowTitle("Spyder - %s" % plugin.windowTitle())
        self.setWindowIcon(plugin.windowIcon())

        self.toolbars = []
        if toolbar_list:
            for title, object_name, actions in toolbar_list:
                toolbar = self.addToolBar(title)
                toolbar.setObjectName(object_name)
                toolbar.setStyleSheet(str(APP_TOOLBAR_STYLESHEET))
                toolbar.setMovable(False)
                add_actions(toolbar, actions)
                self.toolbars.append(toolbar)

        self.menus = []
        if menu_list:
            quit_action = create_action(self, _("Close window"),
                                        icon=ima.icon("close_pane"),
                                        tip=_("Close this window"),
                                        triggered=self.close)
            for index, (title, actions) in enumerate(menu_list):
                menu = self.menuBar().addMenu(title)
                if index == 0:
                    # File menu
                    add_actions(menu, actions+[None, quit_action])
                else:
                    add_actions(menu, actions)
                self.menus.append(menu)

    def get_toolbars(self):
        """Get the toolbars."""
        return self.toolbars

    def add_toolbars_to_menu(self, menu_title, actions):
        """Add toolbars to a menu."""
        # Six is the position of the view menu in menus list
        # that you can find in plugins/editor.py setup_other_windows.
        if self.menus:
            view_menu = self.menus[6]
            view_menu.setObjectName('checkbox-padding')
            if actions == self.toolbars and view_menu:
                toolbars = []
                for toolbar in self.toolbars:
                    action = toolbar.toggleViewAction()
                    toolbars.append(action)
                add_actions(view_menu, toolbars)

    def load_toolbars(self):
        """Loads the last visible toolbars from the .ini file."""
        toolbars_names = self.get_conf(
            'last_visible_toolbars', section='main', default=[]
        )
        if toolbars_names:
            dic = {}
            for toolbar in self.toolbars:
                dic[toolbar.objectName()] = toolbar
                toolbar.toggleViewAction().setChecked(False)
                toolbar.setVisible(False)
            for name in toolbars_names:
                if name in dic:
                    dic[name].toggleViewAction().setChecked(True)
                    dic[name].setVisible(True)

    def resizeEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.isFullScreen():
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)

    def closeEvent(self, event):
        """Reimplement Qt method"""
        self.editorwidget.unregister_all_editorstacks()
        if self.plugin._undocked_window is not None:
            self.plugin.dockwidget.setWidget(self.plugin)
            self.plugin.dockwidget.setVisible(True)
        self.plugin.switch_to_plugin()
        QMainWindow.closeEvent(self, event)
        if self.plugin._undocked_window is not None:
            self.plugin._undocked_window = None

    def changeEvent(self, event):
        """
        Override Qt method to emit a custom `sig_windowstate_changed` signal
        when there's a change in the window state.
        """
        if event.type() == QEvent.WindowStateChange:
            self.sig_window_state_changed.emit(self.windowState())
        super().changeEvent(event)

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
            self.resize( QSize(*size) )
            self.window_size = self.size()
        pos = settings.get('pos')
        if pos is not None:
            self.move( QPoint(*pos) )
        hexstate = settings.get('hexstate')
        if hexstate is not None:
            self.restoreState( QByteArray().fromHex(
                    str(hexstate).encode('utf-8')) )
        if settings.get('is_maximized'):
            self.setWindowState(Qt.WindowMaximized)
        if settings.get('is_fullscreen'):
            self.setWindowState(Qt.WindowFullScreen)
        splitsettings = settings.get('splitsettings')
        if splitsettings is not None:
            self.editorwidget.editorsplitter.set_layout_settings(splitsettings)


class EditorPluginExample(QSplitter):
    def __init__(self):
        QSplitter.__init__(self)

        self._dock_action = None
        self._undock_action = None
        self._close_plugin_action = None
        self._undocked_window = None
        self._lock_unlock_action = None
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
        editorstack.set_current_filename(to_text_string(fname))
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
        logger.debug("FakePlugin.register_editorstack: %r" % editorstack)
        self.editorstacks.append(editorstack)
        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
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
        logger.debug("FakePlugin.unregister_editorstack: %r" % editorstack)
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

    def register_widget_shortcuts(self, widget):
        """Fake!"""
        pass

    def get_color_scheme(self):
        pass


def test():
    from spyder.utils.qthelpers import qapplication
    from spyder.config.base import get_module_path

    spyder_dir = get_module_path('spyder')
    app = qapplication(test_time=8)

    test = EditorPluginExample()
    test.resize(900, 700)
    test.show()

    import time
    t0 = time.time()
    test.load(osp.join(spyder_dir, "widgets", "collectionseditor.py"))
    test.load(osp.join(spyder_dir, "plugins", "editor", "widgets",
                       "editor.py"))
    test.load(osp.join(spyder_dir, "plugins", "explorer", "widgets",
                       'explorer.py'))
    test.load(osp.join(spyder_dir, "plugins", "editor", "widgets",
                       "codeeditor.py"))
    print("Elapsed time: %.3f s" % (time.time()-t0))  # spyder: test-skip

    sys.exit(app.exec_())


if __name__ == "__main__":
    test()

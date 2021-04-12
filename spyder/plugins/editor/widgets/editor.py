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
import os
import os.path as osp
import sys
import functools
import unicodedata

# Third party imports
import qstylizer
from qtpy.compat import getsavefilename
from qtpy.QtCore import (QByteArray, QFileInfo, QPoint, QSize, Qt, QTimer,
                         Signal, Slot)
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QAction, QApplication, QFileDialog, QHBoxLayout,
                            QLabel, QMainWindow, QMessageBox, QMenu,
                            QSplitter, QVBoxLayout, QWidget, QListWidget,
                            QListWidgetItem, QSizePolicy, QToolBar)

# Local imports
from spyder.api.panel import Panel
from spyder.config.base import _, running_under_pytest
from spyder.config.manager import CONF
from spyder.config.utils import (get_edit_filetypes, get_edit_filters,
                                 get_filter, is_kde_desktop, is_anaconda)
from spyder.plugins.editor.utils.autosave import AutosaveForStack
from spyder.plugins.editor.utils.editor import get_file_language
from spyder.plugins.editor.utils.switcher import EditorSwitcherManager
from spyder.plugins.editor.widgets import codeeditor
from spyder.plugins.editor.widgets.editorstack_helpers import (
    ThreadManager, FileInfo, StackHistory)
from spyder.plugins.editor.widgets.status import (CursorPositionStatus,
                                                  EncodingStatus, EOLStatus,
                                                  ReadWriteStatus, VCSStatus)
from spyder.plugins.explorer.widgets.explorer import (
    show_in_external_file_explorer)
from spyder.plugins.outlineexplorer.widgets import OutlineExplorerWidget
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor
from spyder.plugins.outlineexplorer.api import cell_name
from spyder.py3compat import qbytearray_to_str, to_text_string
from spyder.utils import encoding, sourcecode, syntaxhighlighters
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, MENU_SEPARATOR,
                                    mimedata2url, set_menu_icons,
                                    create_waitspinner)
from spyder.utils.stylesheet import (
    APP_STYLESHEET, APP_TOOLBAR_STYLESHEET, PANES_TABBAR_STYLESHEET)
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.tabs import BaseTabs


logger = logging.getLogger(__name__)


class TabSwitcherWidget(QListWidget):
    """Show tabs in mru order and change between them."""

    def __init__(self, parent, stack_history, tabs):
        QListWidget.__init__(self, parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        self.editor = parent
        self.stack_history = stack_history
        self.tabs = tabs

        self.setSelectionMode(QListWidget.SingleSelection)
        self.itemActivated.connect(self.item_selected)

        self.id_list = []
        self.load_data()
        size = CONF.get('main', 'completion/size')
        self.resize(*size)
        self.set_dialog_position()
        self.setCurrentRow(0)

        CONF.config_shortcut(lambda: self.select_row(-1), context='Editor',
                             name='Go to previous file', parent=self)
        CONF.config_shortcut(lambda: self.select_row(1), context='Editor',
                             name='Go to next file', parent=self)

    def load_data(self):
        """Fill ListWidget with the tabs texts.

        Add elements in inverse order of stack_history.
        """
        for index in reversed(self.stack_history):
            text = self.tabs.tabText(index)
            text = text.replace('&', '')
            item = QListWidgetItem(ima.icon('TextFileIcon'), text)
            self.addItem(item)

    def item_selected(self, item=None):
        """Change to the selected document and hide this widget."""
        if item is None:
            item = self.currentItem()

        # stack history is in inverse order
        try:
            index = self.stack_history[-(self.currentRow()+1)]
        except IndexError:
            pass
        else:
            self.editor.set_stack_index(index)
            self.editor.current_changed(index)
        self.hide()

    def select_row(self, steps):
        """Move selected row a number of steps.

        Iterates in a cyclic behaviour.
        """
        row = (self.currentRow() + steps) % self.count()
        self.setCurrentRow(row)

    def set_dialog_position(self):
        """Positions the tab switcher in the top-center of the editor."""
        left = self.editor.geometry().width()/2 - self.width()/2
        top = (self.editor.tabs.tabBar().geometry().height() +
               self.editor.fname_label.geometry().height())

        self.move(self.editor.mapToGlobal(QPoint(left, top)))

    def keyReleaseEvent(self, event):
        """Reimplement Qt method.

        Handle "most recent used" tab behavior,
        When ctrl is released and tab_switcher is visible, tab will be changed.
        """
        if self.isVisible():
            qsc = CONF.get_shortcut(context='Editor', name='Go to next file')

            for key in qsc.split('+'):
                key = key.lower()
                if ((key == 'ctrl' and event.key() == Qt.Key_Control) or
                        (key == 'alt' and event.key() == Qt.Key_Alt)):
                    self.item_selected()
        event.accept()

    def keyPressEvent(self, event):
        """Reimplement Qt method to allow cyclic behavior."""
        if event.key() == Qt.Key_Down:
            self.select_row(1)
        elif event.key() == Qt.Key_Up:
            self.select_row(-1)

    def focusOutEvent(self, event):
        """Reimplement Qt method to close the widget when loosing focus."""
        event.ignore()
        if sys.platform == "darwin":
            if event.reason() != Qt.ActiveWindowFocusReason:
                self.close()
        else:
            self.close()


class EditorStack(QWidget):
    reset_statusbar = Signal()
    readonly_changed = Signal(bool)
    encoding_changed = Signal(str)
    sig_editor_cursor_position_changed = Signal(int, int)
    sig_refresh_eol_chars = Signal(str)
    sig_refresh_formatting = Signal(bool)
    starting_long_process = Signal(str)
    ending_long_process = Signal(str)
    redirect_stdio = Signal(bool)
    exec_in_extconsole = Signal(str, bool)
    run_cell_in_ipyclient = Signal(str, object, str, bool)
    debug_cell_in_ipyclient = Signal(str, object, str, bool)
    update_plugin_title = Signal()
    editor_focus_changed = Signal()
    zoom_in = Signal()
    zoom_out = Signal()
    zoom_reset = Signal()
    sig_open_file = Signal(dict)
    sig_close_file = Signal(str, str)
    file_saved = Signal(str, str, str)
    file_renamed_in_data = Signal(str, str, str)
    opened_files_list_changed = Signal()
    active_languages_stats = Signal(set)
    todo_results_changed = Signal()
    update_code_analysis_actions = Signal()
    refresh_file_dependent_actions = Signal()
    refresh_save_all_action = Signal()
    sig_breakpoints_saved = Signal()
    text_changed_at = Signal(str, int)
    current_file_changed = Signal(str, int, int, int)
    plugin_load = Signal((str,), ())
    edit_goto = Signal(str, int, str)
    sig_split_vertically = Signal()
    sig_split_horizontally = Signal()
    sig_new_file = Signal((str,), ())
    sig_save_as = Signal()
    sig_prev_edit_pos = Signal()
    sig_prev_cursor = Signal()
    sig_next_cursor = Signal()
    sig_prev_warning = Signal()
    sig_next_warning = Signal()
    sig_go_to_definition = Signal(str, int, int)
    sig_perform_completion_request = Signal(str, str, dict)
    sig_option_changed = Signal(str, object)  # config option needs changing
    sig_save_bookmark = Signal(int)
    sig_load_bookmark = Signal(int)
    sig_save_bookmarks = Signal(str, str)

    sig_help_requested = Signal(dict)
    """
    This signal is emitted to request help on a given object `name`.

    Parameters
    ----------
    help_data: dict
        Dictionary required by the Help pane to render a docstring.

    Examples
    --------
    >>> help_data = {
        'obj_text': str,
        'name': str,
        'argspec': str,
        'note': str,
        'docstring': str,
        'force_refresh': bool,
        'path': str,
    }

    See Also
    --------
    :py:meth:spyder.plugins.editor.widgets.editor.EditorStack.send_to_help
    """

    def __init__(self, parent, actions):
        QWidget.__init__(self, parent)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.threadmanager = ThreadManager(self)
        self.new_window = False
        self.horsplit_action = None
        self.versplit_action = None
        self.close_action = None
        self.__get_split_actions()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.menu = None
        self.switcher_dlg = None
        self.switcher_manager = None
        self.tabs = None
        self.tabs_switcher = None

        self.stack_history = StackHistory(self)

        # External panels
        self.external_panels = []

        self.setup_editorstack(parent, layout)

        self.find_widget = None

        self.data = []

        switcher_action = create_action(
            self,
            _("File switcher..."),
            icon=ima.icon('filelist'),
            triggered=self.open_switcher_dlg)
        symbolfinder_action = create_action(
            self,
            _("Find symbols in file..."),
            icon=ima.icon('symbol_find'),
            triggered=self.open_symbolfinder_dlg)
        copy_to_cb_action = create_action(self, _("Copy path to clipboard"),
                icon=ima.icon('editcopy'),
                triggered=lambda:
                QApplication.clipboard().setText(self.get_current_filename()))
        close_right = create_action(self, _("Close all to the right"),
                                    triggered=self.close_all_right)
        close_all_but_this = create_action(self, _("Close all but this"),
                                           triggered=self.close_all_but_this)

        sort_tabs = create_action(self, _("Sort tabs alphabetically"),
                                  triggered=self.sort_file_tabs_alphabetically)

        if sys.platform == 'darwin':
            text = _("Show in Finder")
        else:
            text = _("Show in external file explorer")
        external_fileexp_action = create_action(
            self, text,
            triggered=self.show_in_external_file_explorer,
            shortcut=CONF.get_shortcut(context="Editor",
                                       name="show in external file explorer"),
            context=Qt.WidgetShortcut)

        self.menu_actions = actions + [external_fileexp_action,
                                       None, switcher_action,
                                       symbolfinder_action,
                                       copy_to_cb_action, None, close_right,
                                       close_all_but_this, sort_tabs]
        self.outlineexplorer = None
        self.is_closable = False
        self.new_action = None
        self.open_action = None
        self.save_action = None
        self.revert_action = None
        self.tempfile_path = None
        self.title = _("Editor")
        self.todolist_enabled = True
        self.is_analysis_done = False
        self.linenumbers_enabled = True
        self.blanks_enabled = False
        self.scrollpastend_enabled = False
        self.edgeline_enabled = True
        self.edgeline_columns = (79,)
        self.close_parentheses_enabled = True
        self.close_quotes_enabled = True
        self.add_colons_enabled = True
        self.auto_unindent_enabled = True
        self.indent_chars = " "*4
        self.tab_stop_width_spaces = 4
        self.show_class_func_dropdown = False
        self.help_enabled = False
        self.default_font = None
        self.wrap_enabled = False
        self.tabmode_enabled = False
        self.stripmode_enabled = False
        self.intelligent_backspace_enabled = True
        self.automatic_completions_enabled = True
        self.automatic_completion_chars = 3
        self.automatic_completion_ms = 300
        self.completions_hint_enabled = True
        self.completions_hint_after_ms = 500
        self.hover_hints_enabled = True
        self.format_on_save = False
        self.code_snippets_enabled = True
        self.code_folding_enabled = True
        self.underline_errors_enabled = False
        self.highlight_current_line_enabled = False
        self.highlight_current_cell_enabled = False
        self.occurrence_highlighting_enabled = True
        self.occurrence_highlighting_timeout = 1500
        self.checkeolchars_enabled = True
        self.always_remove_trailing_spaces = False
        self.add_newline = False
        self.remove_trailing_newlines = False
        self.convert_eol_on_save = False
        self.convert_eol_on_save_to = 'LF'
        self.focus_to_editor = True
        self.run_cell_copy = False
        self.create_new_file_if_empty = True
        self.indent_guides = False
        ccs = 'spyder/dark'
        if ccs not in syntaxhighlighters.COLOR_SCHEME_NAMES:
            ccs = syntaxhighlighters.COLOR_SCHEME_NAMES[0]
        self.color_scheme = ccs
        self.__file_status_flag = False

        # Real-time code analysis
        self.analysis_timer = QTimer(self)
        self.analysis_timer.setSingleShot(True)
        self.analysis_timer.setInterval(1000)
        self.analysis_timer.timeout.connect(self.analyze_script)

        # Update filename label
        self.editor_focus_changed.connect(self.update_fname_label)

        # Accepting drops
        self.setAcceptDrops(True)

        # Local shortcuts
        self.shortcuts = self.create_shortcuts()

        # For opening last closed tabs
        self.last_closed_files = []

        # Reference to save msgbox and avoid memory to be freed.
        self.msgbox = None

        # File types and filters used by the Save As dialog
        self.edit_filetypes = None
        self.edit_filters = None

        # For testing
        self.save_dialog_on_tests = not running_under_pytest()

        # Autusave component
        self.autosave = AutosaveForStack(self)

        self.last_cell_call = None

    @Slot()
    def show_in_external_file_explorer(self, fnames=None):
        """Show file in external file explorer"""
        if fnames is None:
            fnames = self.get_current_filename()
        try:
            show_in_external_file_explorer(fnames)
        except FileNotFoundError as error:
            file = str(error).split("'")[1]
            if "xdg-open" in file:
                msg_title = _("Warning")
                msg = _("Spyder can't show this file in the external file "
                        "explorer because the <tt>xdg-utils</tt> package is "
                        "not available on your system.")
                QMessageBox.information(self, msg_title, msg,
                                        QMessageBox.Ok)

    def create_shortcuts(self):
        """Create local shortcuts"""
        # --- Configurable shortcuts
        inspect = CONF.config_shortcut(
            self.inspect_current_object,
            context='Editor',
            name='Inspect current object',
            parent=self)

        set_breakpoint = CONF.config_shortcut(
            self.set_or_clear_breakpoint,
            context='Editor',
            name='Breakpoint',
            parent=self)

        set_cond_breakpoint = CONF.config_shortcut(
            self.set_or_edit_conditional_breakpoint,
            context='Editor',
            name='Conditional breakpoint',
            parent=self)

        gotoline = CONF.config_shortcut(
            self.go_to_line,
            context='Editor',
            name='Go to line',
            parent=self)

        tab = CONF.config_shortcut(
            lambda: self.tab_navigation_mru(forward=False),
            context='Editor',
            name='Go to previous file',
            parent=self)

        tabshift = CONF.config_shortcut(
            self.tab_navigation_mru,
            context='Editor',
            name='Go to next file',
            parent=self)

        prevtab = CONF.config_shortcut(
            lambda: self.tabs.tab_navigate(-1),
            context='Editor',
            name='Cycle to previous file',
            parent=self)

        nexttab = CONF.config_shortcut(
            lambda: self.tabs.tab_navigate(1),
            context='Editor',
            name='Cycle to next file',
            parent=self)

        run_selection = CONF.config_shortcut(
            self.run_selection,
            context='Editor',
            name='Run selection',
            parent=self)

        new_file = CONF.config_shortcut(
            lambda: self.sig_new_file[()].emit(),
            context='Editor',
            name='New file',
            parent=self)

        open_file = CONF.config_shortcut(
            lambda: self.plugin_load[()].emit(),
            context='Editor',
            name='Open file',
            parent=self)

        save_file = CONF.config_shortcut(
            self.save,
            context='Editor',
            name='Save file',
            parent=self)

        save_all = CONF.config_shortcut(
            self.save_all,
            context='Editor',
            name='Save all',
            parent=self)

        save_as = CONF.config_shortcut(
            lambda: self.sig_save_as.emit(),
            context='Editor',
            name='Save As',
            parent=self)

        close_all = CONF.config_shortcut(
            self.close_all_files,
            context='Editor',
            name='Close all',
            parent=self)

        prev_edit_pos = CONF.config_shortcut(
            lambda: self.sig_prev_edit_pos.emit(),
            context="Editor",
            name="Last edit location",
            parent=self)

        prev_cursor = CONF.config_shortcut(
            lambda: self.sig_prev_cursor.emit(),
            context="Editor",
            name="Previous cursor position",
            parent=self)

        next_cursor = CONF.config_shortcut(
            lambda: self.sig_next_cursor.emit(),
            context="Editor",
            name="Next cursor position",
            parent=self)

        zoom_in_1 = CONF.config_shortcut(
            lambda: self.zoom_in.emit(),
            context="Editor",
            name="zoom in 1",
            parent=self)

        zoom_in_2 = CONF.config_shortcut(
            lambda: self.zoom_in.emit(),
            context="Editor",
            name="zoom in 2",
            parent=self)

        zoom_out = CONF.config_shortcut(
            lambda: self.zoom_out.emit(),
            context="Editor",
            name="zoom out",
            parent=self)

        zoom_reset = CONF.config_shortcut(
            lambda: self.zoom_reset.emit(),
            context="Editor",
            name="zoom reset",
            parent=self)

        close_file_1 = CONF.config_shortcut(
            self.close_file,
            context="Editor",
            name="close file 1",
            parent=self)

        close_file_2 = CONF.config_shortcut(
            self.close_file,
            context="Editor",
            name="close file 2",
            parent=self)

        run_cell = CONF.config_shortcut(
            self.run_cell,
            context="Editor",
            name="run cell",
            parent=self)

        debug_cell = CONF.config_shortcut(
            self.debug_cell,
            context="Editor",
            name="debug cell",
            parent=self)

        run_cell_and_advance = CONF.config_shortcut(
            self.run_cell_and_advance,
            context="Editor",
            name="run cell and advance",
            parent=self)

        go_to_next_cell = CONF.config_shortcut(
            self.advance_cell,
            context="Editor",
            name="go to next cell",
            parent=self)

        go_to_previous_cell = CONF.config_shortcut(
            lambda: self.advance_cell(reverse=True),
            context="Editor",
            name="go to previous cell",
            parent=self)

        re_run_last_cell = CONF.config_shortcut(
            self.re_run_last_cell,
            context="Editor",
            name="re-run last cell",
            parent=self)

        prev_warning = CONF.config_shortcut(
            lambda: self.sig_prev_warning.emit(),
            context="Editor",
            name="Previous warning",
            parent=self)

        next_warning = CONF.config_shortcut(
            lambda: self.sig_next_warning.emit(),
            context="Editor",
            name="Next warning",
            parent=self)

        split_vertically = CONF.config_shortcut(
            lambda: self.sig_split_vertically.emit(),
            context="Editor",
            name="split vertically",
            parent=self)

        split_horizontally = CONF.config_shortcut(
            lambda: self.sig_split_horizontally.emit(),
            context="Editor",
            name="split horizontally",
            parent=self)

        close_split = CONF.config_shortcut(
            self.close_split,
            context="Editor",
            name="close split panel",
            parent=self)

        external_fileexp = CONF.config_shortcut(
            self.show_in_external_file_explorer,
            context="Editor",
            name="show in external file explorer",
            parent=self)

        # Return configurable ones
        return [inspect, set_breakpoint, set_cond_breakpoint, gotoline, tab,
                tabshift, run_selection, new_file, open_file, save_file,
                save_all, save_as, close_all, prev_edit_pos, prev_cursor,
                next_cursor, zoom_in_1, zoom_in_2, zoom_out, zoom_reset,
                close_file_1, close_file_2, run_cell, debug_cell,
                run_cell_and_advance,
                go_to_next_cell, go_to_previous_cell, re_run_last_cell,
                prev_warning, next_warning, split_vertically,
                split_horizontally, close_split,
                prevtab, nexttab, external_fileexp]

    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]

    def setup_editorstack(self, parent, layout):
        """Setup editorstack's layout"""
        layout.setSpacing(0)

        # Create filename label, spinner and the toolbar that contains them
        self.create_top_widgets()

        # Add top toolbar
        layout.addWidget(self.top_toolbar)

        # Tabbar
        menu_btn = create_toolbutton(self, icon=ima.icon('tooloptions'),
                                     tip=_('Options'))
        menu_btn.setStyleSheet(str(PANES_TABBAR_STYLESHEET))
        self.menu = QMenu(self)
        menu_btn.setMenu(self.menu)
        menu_btn.setPopupMode(menu_btn.InstantPopup)
        self.menu.aboutToShow.connect(self.__setup_menu)

        corner_widgets = {Qt.TopRightCorner: [menu_btn]}
        self.tabs = BaseTabs(self, menu=self.menu, menu_use_tooltips=True,
                             corner_widgets=corner_widgets)
        self.tabs.set_close_function(self.close_file)
        self.tabs.tabBar().tabMoved.connect(self.move_editorstack_data)
        self.tabs.setMovable(True)

        self.stack_history.refresh()

        if hasattr(self.tabs, 'setDocumentMode') \
           and not sys.platform == 'darwin':
            # Don't set document mode to true on OSX because it generates
            # a crash when the editor is detached from the main window
            # Fixes spyder-ide/spyder#561.
            self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self.current_changed)

        tab_container = QWidget()
        tab_container.setObjectName('tab-container')
        tab_layout = QHBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(self.tabs)
        layout.addWidget(tab_container)

        # Show/hide icons in plugin menus for Mac
        if sys.platform == 'darwin':
            self.menu.aboutToHide.connect(
                lambda menu=self.menu:
                set_menu_icons(menu, False))

    def create_top_widgets(self):
        # Filename label
        self.fname_label = QLabel()

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Spinner
        self.spinner = create_waitspinner(size=16, parent=self.fname_label)

        # Add widgets to toolbar
        self.top_toolbar = QToolBar(self)
        self.top_toolbar.addWidget(self.fname_label)
        self.top_toolbar.addWidget(spacer)
        self.top_toolbar.addWidget(self.spinner)

        # Set toolbar style
        css = qstylizer.style.StyleSheet()
        css.QToolBar.setValues(
            margin='0px',
            padding='4px',
            borderBottom=f'1px solid {QStylePalette.COLOR_BACKGROUND_4}'
        )
        self.top_toolbar.setStyleSheet(css.toString())

    def hide_tooltip(self):
        """Hide any open tooltips."""
        for finfo in self.data:
            finfo.editor.hide_tooltip()

    @Slot()
    def update_fname_label(self):
        """Update file name label."""
        filename = to_text_string(self.get_current_filename())
        if len(filename) > 100:
            shorten_filename = u'...' + filename[-100:]
        else:
            shorten_filename = filename
        self.fname_label.setText(shorten_filename)

    def add_corner_widgets_to_tabbar(self, widgets):
        self.tabs.add_corner_widgets(widgets)

    @Slot()
    def close_split(self):
        """Closes the editorstack if it is not the last one opened."""
        if self.is_closable:
            self.close()

    def closeEvent(self, event):
        """Overrides QWidget closeEvent()."""
        self.threadmanager.close_all_threads()
        self.analysis_timer.timeout.disconnect(self.analyze_script)

        # Remove editor references from the outline explorer settings
        if self.outlineexplorer is not None:
            for finfo in self.data:
                self.outlineexplorer.remove_editor(finfo.editor.oe_proxy)

        for finfo in self.data:
            if not finfo.editor.is_cloned:
                finfo.editor.notify_close()
        QWidget.closeEvent(self, event)

    def clone_editor_from(self, other_finfo, set_current):
        fname = other_finfo.filename
        enc = other_finfo.encoding
        new = other_finfo.newly_created
        finfo = self.create_new_editor(fname, enc, "",
                                       set_current=set_current, new=new,
                                       cloned_from=other_finfo.editor)
        finfo.set_todo_results(other_finfo.todo_results)
        return finfo.editor

    def clone_from(self, other):
        """Clone EditorStack from other instance"""
        for other_finfo in other.data:
            self.clone_editor_from(other_finfo, set_current=True)
        self.set_stack_index(other.get_stack_index())

    @Slot()
    @Slot(str)
    def open_switcher_dlg(self, initial_text=''):
        """Open file list management dialog box"""
        if not self.tabs.count():
            return
        if self.switcher_dlg is not None and self.switcher_dlg.isVisible():
            self.switcher_dlg.hide()
            self.switcher_dlg.clear()
            return
        if self.switcher_dlg is None:
            from spyder.widgets.switcher import Switcher
            self.switcher_dlg = Switcher(self)
            self.switcher_manager = EditorSwitcherManager(
                self.get_plugin(),
                self.switcher_dlg,
                lambda: self.get_current_editor(),
                lambda: self,
                section=self.get_plugin_title())

        self.switcher_dlg.set_search_text(initial_text)
        self.switcher_dlg.setup()
        self.switcher_dlg.show()
        # Note: the +1 pixel on the top makes it look better
        delta_top = (self.tabs.tabBar().geometry().height() +
                     self.fname_label.geometry().height() + 1)
        self.switcher_dlg.set_position(delta_top)

    @Slot()
    def open_symbolfinder_dlg(self):
        self.open_switcher_dlg(initial_text='@')

    def get_plugin(self):
        """Get the plugin of the parent widget."""
        # Needed for the editor stack to use its own switcher instance.
        # See spyder-ide/spyder#10684.
        return self.parent().plugin

    def get_plugin_title(self):
        """Get the plugin title of the parent widget."""
        # Needed for the editor stack to use its own switcher instance.
        # See spyder-ide/spyder#9469.
        return self.get_plugin().get_plugin_title()

    def go_to_line(self, line=None):
        """Go to line dialog"""
        if line is not None:
            # When this method is called from the flileswitcher, a line
            # number is specified, so there is no need for the dialog.
            self.get_current_editor().go_to_line(line)
        else:
            if self.data:
                self.get_current_editor().exec_gotolinedialog()

    def set_or_clear_breakpoint(self):
        """Set/clear breakpoint"""
        if self.data:
            editor = self.get_current_editor()
            editor.debugger.toogle_breakpoint()

    def set_or_edit_conditional_breakpoint(self):
        """Set conditional breakpoint"""
        if self.data:
            editor = self.get_current_editor()
            editor.debugger.toogle_breakpoint(edit_condition=True)

    def set_bookmark(self, slot_num):
        """Bookmark current position to given slot."""
        if self.data:
            editor = self.get_current_editor()
            editor.add_bookmark(slot_num)

    def inspect_current_object(self, pos=None):
        """Inspect current object in the Help plugin"""
        editor = self.get_current_editor()
        editor.sig_display_object_info.connect(self.display_help)
        cursor = None
        offset = editor.get_position('cursor')
        if pos:
            cursor = editor.get_last_hover_cursor()
            if cursor:
                offset = cursor.position()
            else:
                return

        line, col = editor.get_cursor_line_column(cursor)
        editor.request_hover(line, col, offset,
                             show_hint=False, clicked=bool(pos))

    @Slot(str, bool)
    def display_help(self, help_text, clicked):
        editor = self.get_current_editor()
        if clicked:
            name = editor.get_last_hover_word()
        else:
            name = editor.get_current_word(help_req=True)

        try:
            editor.sig_display_object_info.disconnect(self.display_help)
        except TypeError:
            # Needed to prevent an error after some time in idle.
            # See spyder-ide/spyder#11228
            pass

        self.send_to_help(name, help_text, force=True)

    #  ------ Editor Widget Settings
    def set_closable(self, state):
        """Parent widget must handle the closable state"""
        self.is_closable = state

    def set_io_actions(self, new_action, open_action,
                       save_action, revert_action):
        self.new_action = new_action
        self.open_action = open_action
        self.save_action = save_action
        self.revert_action = revert_action

    def set_find_widget(self, find_widget):
        self.find_widget = find_widget

    def set_outlineexplorer(self, outlineexplorer):
        self.outlineexplorer = outlineexplorer

    def add_outlineexplorer_button(self, editor_plugin):
        oe_btn = create_toolbutton(editor_plugin)
        oe_btn.setDefaultAction(self.outlineexplorer.visibility_action)
        self.add_corner_widgets_to_tabbar([5, oe_btn])

    def set_tempfile_path(self, path):
        self.tempfile_path = path

    def set_title(self, text):
        self.title = text

    def set_classfunc_dropdown_visible(self, state):
        self.show_class_func_dropdown = state
        if self.data:
            for finfo in self.data:
                if finfo.editor.is_python_like():
                    finfo.editor.classfuncdropdown.setVisible(state)

    def __update_editor_margins(self, editor):
        editor.linenumberarea.setup_margins(
            linenumbers=self.linenumbers_enabled, markers=self.has_markers())

    def has_markers(self):
        """Return True if this editorstack has a marker margin for TODOs or
        code analysis"""
        return self.todolist_enabled

    def set_todolist_enabled(self, state, current_finfo=None):
        # CONF.get(self.CONF_SECTION, 'todo_list')
        self.todolist_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                finfo.cleanup_todo_results()
                if state and current_finfo is not None:
                    if current_finfo is not finfo:
                        finfo.run_todo_finder()

    def set_linenumbers_enabled(self, state, current_finfo=None):
        # CONF.get(self.CONF_SECTION, 'line_numbers')
        self.linenumbers_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)

    def set_blanks_enabled(self, state):
        self.blanks_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_blanks_enabled(state)

    def set_scrollpastend_enabled(self, state):
        self.scrollpastend_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_scrollpastend_enabled(state)

    def set_edgeline_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'edge_line')
        self.edgeline_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.edge_line.set_enabled(state)

    def set_edgeline_columns(self, columns):
        # CONF.get(self.CONF_SECTION, 'edge_line_column')
        self.edgeline_columns = columns
        if self.data:
            for finfo in self.data:
                finfo.editor.edge_line.set_columns(columns)

    def set_indent_guides(self, state):
        self.indent_guides = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_identation_guides(state)

    def set_close_parentheses_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'close_parentheses')
        self.close_parentheses_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_close_parentheses_enabled(state)

    def set_close_quotes_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'close_quotes')
        self.close_quotes_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_close_quotes_enabled(state)

    def set_add_colons_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'add_colons')
        self.add_colons_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_add_colons_enabled(state)

    def set_auto_unindent_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'auto_unindent')
        self.auto_unindent_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_auto_unindent_enabled(state)

    def set_indent_chars(self, indent_chars):
        # CONF.get(self.CONF_SECTION, 'indent_chars')
        indent_chars = indent_chars[1:-1]  # removing the leading/ending '*'
        self.indent_chars = indent_chars
        if self.data:
            for finfo in self.data:
                finfo.editor.set_indent_chars(indent_chars)

    def set_tab_stop_width_spaces(self, tab_stop_width_spaces):
        # CONF.get(self.CONF_SECTION, 'tab_stop_width')
        self.tab_stop_width_spaces = tab_stop_width_spaces
        if self.data:
            for finfo in self.data:
                finfo.editor.tab_stop_width_spaces = tab_stop_width_spaces
                finfo.editor.update_tab_stop_width_spaces()

    def set_help_enabled(self, state):
        self.help_enabled = state

    def set_default_font(self, font, color_scheme=None):
        self.default_font = font
        if color_scheme is not None:
            self.color_scheme = color_scheme
        if self.data:
            for finfo in self.data:
                finfo.editor.set_font(font, color_scheme)

    def set_color_scheme(self, color_scheme):
        self.color_scheme = color_scheme
        if self.data:
            for finfo in self.data:
                finfo.editor.set_color_scheme(color_scheme)

    def set_wrap_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'wrap')
        self.wrap_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_wrap_mode(state)

    def set_tabmode_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'tab_always_indent')
        self.tabmode_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_tab_mode(state)

    def set_stripmode_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'strip_trailing_spaces_on_modify')
        self.stripmode_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_strip_mode(state)

    def set_intelligent_backspace_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'intelligent_backspace')
        self.intelligent_backspace_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_intelligent_backspace(state)

    def set_code_snippets_enabled(self, state):
        self.code_snippets_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_code_snippets(state)

    def set_code_folding_enabled(self, state):
        self.code_folding_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_code_folding(state)

    def set_automatic_completions_enabled(self, state):
        self.automatic_completions_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_automatic_completions(state)

    def set_automatic_completions_after_chars(self, chars):
        self.automatic_completion_chars = chars
        if self.data:
            for finfo in self.data:
                finfo.editor.set_automatic_completions_after_chars(chars)

    def set_automatic_completions_after_ms(self, ms):
        self.automatic_completion_ms = ms
        if self.data:
            for finfo in self.data:
                finfo.editor.set_automatic_completions_after_ms(ms)

    def set_completions_hint_enabled(self, state):
        self.completions_hint_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_completions_hint(state)

    def set_completions_hint_after_ms(self, ms):
        self.completions_hint_after_ms = ms
        if self.data:
            for finfo in self.data:
                finfo.editor.set_completions_hint_after_ms(ms)

    def set_hover_hints_enabled(self, state):
        self.hover_hints_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_hover_hints(state)

    def set_format_on_save(self, state):
        self.format_on_save = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_format_on_save(state)

    def set_occurrence_highlighting_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'occurrence_highlighting')
        self.occurrence_highlighting_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurrence_highlighting(state)

    def set_occurrence_highlighting_timeout(self, timeout):
        # CONF.get(self.CONF_SECTION, 'occurrence_highlighting/timeout')
        self.occurrence_highlighting_timeout = timeout
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurrence_timeout(timeout)

    def set_underline_errors_enabled(self, state):
        self.underline_errors_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_underline_errors_enabled(state)

    def set_highlight_current_line_enabled(self, state):
        self.highlight_current_line_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_highlight_current_line(state)

    def set_highlight_current_cell_enabled(self, state):
        self.highlight_current_cell_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_highlight_current_cell(state)

    def set_checkeolchars_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'check_eol_chars')
        self.checkeolchars_enabled = state

    def set_always_remove_trailing_spaces(self, state):
        # CONF.get(self.CONF_SECTION, 'always_remove_trailing_spaces')
        self.always_remove_trailing_spaces = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_remove_trailing_spaces(state)

    def set_add_newline(self, state):
        self.add_newline = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_add_newline(state)

    def set_remove_trailing_newlines(self, state):
        self.remove_trailing_newlines = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_remove_trailing_newlines(state)

    def set_convert_eol_on_save(self, state):
        """If `state` is `True`, saving files will convert line endings."""
        # CONF.get(self.CONF_SECTION, 'convert_eol_on_save')
        self.convert_eol_on_save = state

    def set_convert_eol_on_save_to(self, state):
        """`state` can be one of ('LF', 'CRLF', 'CR')"""
        # CONF.get(self.CONF_SECTION, 'convert_eol_on_save_to')
        self.convert_eol_on_save_to = state

    def set_focus_to_editor(self, state):
        self.focus_to_editor = state

    def set_run_cell_copy(self, state):
        """If `state` is ``True``, code cells will be copied to the console."""
        self.run_cell_copy = state

    def set_current_project_path(self, root_path=None):
        """
        Set the current active project root path.

        Parameters
        ----------
        root_path: str or None, optional
            Path to current project root path. Default is None.
        """
        for finfo in self.data:
            finfo.editor.set_current_project_path(root_path)

    #  ------ Stacked widget management
    def get_stack_index(self):
        return self.tabs.currentIndex()

    def get_current_finfo(self):
        if self.data:
            return self.data[self.get_stack_index()]

    def get_current_editor(self):
        return self.tabs.currentWidget()

    def get_stack_count(self):
        return self.tabs.count()

    def set_stack_index(self, index, instance=None):
        if instance == self or instance == None:
            self.tabs.setCurrentIndex(index)

    def set_tabbar_visible(self, state):
        self.tabs.tabBar().setVisible(state)

    def remove_from_data(self, index):
        self.tabs.blockSignals(True)
        self.tabs.removeTab(index)
        self.data.pop(index)
        self.tabs.blockSignals(False)
        self.update_actions()

    def __modified_readonly_title(self, title, is_modified, is_readonly):
        if is_modified is not None and is_modified:
            title += "*"
        if is_readonly is not None and is_readonly:
            title = "(%s)" % title
        return title

    def get_tab_text(self, index, is_modified=None, is_readonly=None):
        """Return tab title."""
        files_path_list = [finfo.filename for finfo in self.data]
        fname = self.data[index].filename
        fname = sourcecode.disambiguate_fname(files_path_list, fname)
        return self.__modified_readonly_title(fname,
                                              is_modified, is_readonly)

    def get_tab_tip(self, filename, is_modified=None, is_readonly=None):
        """Return tab menu title"""
        text = u"%s — %s"
        text = self.__modified_readonly_title(text,
                                              is_modified, is_readonly)
        if self.tempfile_path is not None\
           and filename == encoding.to_unicode_from_fs(self.tempfile_path):
            temp_file_str = to_text_string(_("Temporary file"))
            return text % (temp_file_str, self.tempfile_path)
        else:
            return text % (osp.basename(filename), osp.dirname(filename))

    def add_to_data(self, finfo, set_current, add_where='end'):
        finfo.editor.oe_proxy = None
        index = 0 if add_where == 'start' else len(self.data)
        self.data.insert(index, finfo)
        index = self.data.index(finfo)
        editor = finfo.editor
        self.tabs.insertTab(index, editor, self.get_tab_text(index))
        self.set_stack_title(index, False)
        if set_current:
            self.set_stack_index(index)
            self.current_changed(index)
        self.update_actions()

    def __repopulate_stack(self):
        self.tabs.blockSignals(True)
        self.tabs.clear()
        for finfo in self.data:
            if finfo.newly_created:
                is_modified = True
            else:
                is_modified = None
            index = self.data.index(finfo)
            tab_text = self.get_tab_text(index, is_modified)
            tab_tip = self.get_tab_tip(finfo.filename)
            index = self.tabs.addTab(finfo.editor, tab_text)
            self.tabs.setTabToolTip(index, tab_tip)
        self.tabs.blockSignals(False)

    def rename_in_data(self, original_filename, new_filename):
        index = self.has_filename(original_filename)
        if index is None:
            return
        finfo = self.data[index]

        # Send close request to LSP
        finfo.editor.notify_close()

        # Set new filename
        finfo.filename = new_filename
        finfo.editor.filename = new_filename

        # File type has changed!
        original_ext = osp.splitext(original_filename)[1]
        new_ext = osp.splitext(new_filename)[1]
        if original_ext != new_ext:
            # Set file language and re-run highlighter
            txt = to_text_string(finfo.editor.get_text_with_eol())
            language = get_file_language(new_filename, txt)
            finfo.editor.set_language(language, new_filename)
            finfo.editor.run_pygments_highlighter()

            # If the user renamed the file to a different language, we
            # need to emit sig_open_file to see if we can start a
            # language server for it.
            options = {
                'language': language,
                'filename': new_filename,
                'codeeditor': finfo.editor
            }
            self.sig_open_file.emit(options)

            # Update panels
            finfo.editor.set_debug_panel(
                show_debug_panel=True, language=language)
            finfo.editor.cleanup_code_analysis()
            finfo.editor.cleanup_folding()
        else:
            # If there's no language change, we simply need to request a
            # document_did_open for the new file.
            finfo.editor.document_did_open()

        set_new_index = index == self.get_stack_index()
        current_fname = self.get_current_filename()
        finfo.editor.filename = new_filename
        new_index = self.data.index(finfo)
        self.__repopulate_stack()
        if set_new_index:
            self.set_stack_index(new_index)
        else:
            # Fixes spyder-ide/spyder#1287.
            self.set_current_filename(current_fname)
        if self.outlineexplorer is not None:
            self.outlineexplorer.file_renamed(
                finfo.editor.oe_proxy, finfo.filename)
        return new_index

    def set_stack_title(self, index, is_modified):
        finfo = self.data[index]
        fname = finfo.filename
        is_modified = (is_modified or finfo.newly_created) and not finfo.default
        is_readonly = finfo.editor.isReadOnly()
        tab_text = self.get_tab_text(index, is_modified, is_readonly)
        tab_tip = self.get_tab_tip(fname, is_modified, is_readonly)

        # Only update tab text if have changed, otherwise an unwanted scrolling
        # will happen when changing tabs. See spyder-ide/spyder#1170.
        if tab_text != self.tabs.tabText(index):
            self.tabs.setTabText(index, tab_text)
        self.tabs.setTabToolTip(index, tab_tip)

    #  ------ Context menu
    def __setup_menu(self):
        """Setup tab context menu before showing it"""
        self.menu.clear()
        if self.data:
            actions = self.menu_actions
        else:
            actions = (self.new_action, self.open_action)
            self.setFocus()  # --> Editor.__get_focus_editortabwidget
        add_actions(self.menu, list(actions) + self.__get_split_actions())
        self.close_action.setEnabled(self.is_closable)

        if sys.platform == 'darwin':
            set_menu_icons(self.menu, True)

    #  ------ Hor/Ver splitting
    def __get_split_actions(self):
        if self.parent() is not None:
            plugin = self.parent().plugin
        else:
            plugin = None

        # New window
        if plugin is not None:
            self.new_window_action = create_action(
                self, _("New window"),
                icon=ima.icon('newwindow'),
                tip=_("Create a new editor window"),
                triggered=plugin.create_new_window)

        # Splitting
        self.versplit_action = create_action(
            self,
            _("Split vertically"),
            icon=ima.icon('versplit'),
            tip=_("Split vertically this editor window"),
            triggered=lambda: self.sig_split_vertically.emit(),
            shortcut=CONF.get_shortcut(context='Editor',
                                       name='split vertically'),
            context=Qt.WidgetShortcut)

        self.horsplit_action = create_action(
            self,
            _("Split horizontally"),
            icon=ima.icon('horsplit'),
            tip=_("Split horizontally this editor window"),
            triggered=lambda: self.sig_split_horizontally.emit(),
            shortcut=CONF.get_shortcut(context='Editor',
                                       name='split horizontally'),
            context=Qt.WidgetShortcut)

        self.close_action = create_action(
            self,
            _("Close this panel"),
            icon=ima.icon('close_panel'),
            triggered=self.close_split,
            shortcut=CONF.get_shortcut(context='Editor',
                                       name='close split panel'),
            context=Qt.WidgetShortcut)

        # Regular actions
        actions = [MENU_SEPARATOR, self.versplit_action,
                   self.horsplit_action, self.close_action]

        if self.new_window:
            window = self.window()
            close_window_action = create_action(
                self, _("Close window"),
                icon=ima.icon('close_pane'),
                triggered=window.close)
            actions += [MENU_SEPARATOR, self.new_window_action,
                        close_window_action]
        elif plugin is not None:
            if plugin._undocked_window is not None:
                actions += [MENU_SEPARATOR, plugin._dock_action]
            else:
                actions += [MENU_SEPARATOR, self.new_window_action,
                            plugin._undock_action,
                            plugin._close_plugin_action]

        return actions

    def reset_orientation(self):
        self.horsplit_action.setEnabled(True)
        self.versplit_action.setEnabled(True)

    def set_orientation(self, orientation):
        self.horsplit_action.setEnabled(orientation == Qt.Horizontal)
        self.versplit_action.setEnabled(orientation == Qt.Vertical)

    def update_actions(self):
        state = self.get_stack_count() > 0
        self.horsplit_action.setEnabled(state)
        self.versplit_action.setEnabled(state)

    # ------ Accessors
    def get_current_filename(self):
        if self.data:
            return self.data[self.get_stack_index()].filename

    def get_current_language(self):
        if self.data:
            return self.data[self.get_stack_index()].editor.language

    def get_filenames(self):
        """
        Return a list with the names of all the files currently opened in
        the editorstack.
        """
        return [finfo.filename for finfo in self.data]

    def has_filename(self, filename):
        """Return the self.data index position for the filename.

        Args:
            filename: Name of the file to search for in self.data.

        Returns:
            The self.data index for the filename.  Returns None
            if the filename is not found in self.data.
        """
        fixpath = lambda path: osp.normcase(osp.realpath(path))
        for index, finfo in enumerate(self.data):
            if fixpath(filename) == fixpath(finfo.filename):
                return index
        return None

    def set_current_filename(self, filename, focus=True):
        """Set current filename and return the associated editor instance."""
        index = self.has_filename(filename)
        if index is not None:
            if focus:
                self.set_stack_index(index)
            editor = self.data[index].editor
            if focus:
                editor.setFocus()
            else:
                self.stack_history.remove_and_append(index)

            return editor

    def is_file_opened(self, filename=None):
        """Return if filename is in the editor stack.

        Args:
            filename: Name of the file to search for.  If filename is None,
                then checks if any file is open.

        Returns:
            True: If filename is None and a file is open.
            False: If filename is None and no files are open.
            None: If filename is not None and the file isn't found.
            integer: Index of file name in editor stack.
        """
        if filename is None:
            # Is there any file opened?
            return len(self.data) > 0
        else:
            return self.has_filename(filename)

    def get_index_from_filename(self, filename):
        """
        Return the position index of a file in the tab bar of the editorstack
        from its name.
        """
        filenames = [d.filename for d in self.data]
        return filenames.index(filename)

    @Slot(int, int)
    def move_editorstack_data(self, start, end):
        """Reorder editorstack.data so it is synchronized with the tab bar when
        tabs are moved."""
        if start < 0 or end < 0:
            return
        else:
            steps = abs(end - start)
            direction = (end-start) // steps  # +1 for right, -1 for left

        data = self.data
        self.blockSignals(True)

        for i in range(start, end, direction):
            data[i], data[i+direction] = data[i+direction], data[i]

        self.blockSignals(False)
        self.refresh()

    #  ------ Close file, tabwidget...
    def close_file(self, index=None, force=False):
        """Close file (index=None -> close current file)
        Keep current file index unchanged (if current file
        that is being closed)"""
        current_index = self.get_stack_index()
        count = self.get_stack_count()

        if index is None:
            if count > 0:
                index = current_index
            else:
                self.find_widget.set_editor(None)
                return

        new_index = None
        if count > 1:
            if current_index == index:
                new_index = self._get_previous_file_index()
            else:
                new_index = current_index

        can_close_file = self.parent().plugin.can_close_file(
            self.data[index].filename) if self.parent() else True
        is_ok = (force or self.save_if_changed(cancelable=True, index=index)
                 and can_close_file)
        if is_ok:
            finfo = self.data[index]
            self.threadmanager.close_threads(finfo)
            # Removing editor reference from outline explorer settings:
            if self.outlineexplorer is not None:
                self.outlineexplorer.remove_editor(finfo.editor.oe_proxy)

            filename = self.data[index].filename
            self.remove_from_data(index)
            finfo.editor.notify_close()

            # We pass self object ID as a QString, because otherwise it would
            # depend on the platform: long for 64bit, int for 32bit. Replacing
            # by long all the time is not working on some 32bit platforms.
            # See spyder-ide/spyder#1094 and spyder-ide/spyder#1098.
            self.sig_close_file.emit(str(id(self)), filename)

            self.opened_files_list_changed.emit()
            self.update_code_analysis_actions.emit()
            self.refresh_file_dependent_actions.emit()
            self.update_plugin_title.emit()

            editor = self.get_current_editor()
            if editor:
                editor.setFocus()

            if new_index is not None:
                if index < new_index:
                    new_index -= 1
                self.set_stack_index(new_index)

            self.add_last_closed_file(finfo.filename)

            if finfo.filename in self.autosave.file_hashes:
                del self.autosave.file_hashes[finfo.filename]

        if self.get_stack_count() == 0 and self.create_new_file_if_empty:
            self.sig_new_file[()].emit()
            return False
        self.__modify_stack_title()
        return is_ok

    def register_completion_capabilities(self, capabilities, language):
        """
        Register completion server capabilities across all editors.

        Parameters
        ----------
        capabilities: dict
            Capabilities supported by a language server.
        language: str
            Programming language for the language server (it has to be
            in small caps).
        """
        for index in range(self.get_stack_count()):
            editor = self.tabs.widget(index)
            if editor.language.lower() == language:
                editor.register_completion_capabilities(capabilities)

    def start_completion_services(self, language):
        """Notify language server availability to code editors."""
        for index in range(self.get_stack_count()):
            editor = self.tabs.widget(index)
            if editor.language.lower() == language:
                editor.start_completion_services()

    def stop_completion_services(self, language):
        """Notify language server unavailability to code editors."""
        for index in range(self.get_stack_count()):
            editor = self.tabs.widget(index)
            if editor.language.lower() == language:
                editor.stop_completion_services()

    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass

    def close_all_right(self):
        """ Close all files opened to the right """
        num = self.get_stack_index()
        n = self.get_stack_count()
        for __ in range(num, n-1):
            self.close_file(num+1)

    def close_all_but_this(self):
        """Close all files but the current one"""
        self.close_all_right()
        for __ in range(0, self.get_stack_count() - 1):
            self.close_file(0)

    def sort_file_tabs_alphabetically(self):
        """Sort open tabs alphabetically."""
        while self.sorted() is False:
            for i in range(0, self.tabs.tabBar().count()):
                if(self.tabs.tabBar().tabText(i) >
                        self.tabs.tabBar().tabText(i + 1)):
                    self.tabs.tabBar().moveTab(i, i + 1)

    def sorted(self):
        """Utility function for sort_file_tabs_alphabetically()."""
        for i in range(0, self.tabs.tabBar().count() - 1):
            if (self.tabs.tabBar().tabText(i) >
                    self.tabs.tabBar().tabText(i + 1)):
                return False
        return True

    def add_last_closed_file(self, fname):
        """Add to last closed file list."""
        if fname in self.last_closed_files:
            self.last_closed_files.remove(fname)
        self.last_closed_files.insert(0, fname)
        if len(self.last_closed_files) > 10:
            self.last_closed_files.pop(-1)

    def get_last_closed_files(self):
        return self.last_closed_files

    def set_last_closed_files(self, fnames):
        self.last_closed_files = fnames

    #  ------ Save
    def save_if_changed(self, cancelable=False, index=None):
        """Ask user to save file if modified.

        Args:
            cancelable: Show Cancel button.
            index: File to check for modification.

        Returns:
            False when save() fails or is cancelled.
            True when save() is successful, there are no modifications,
                or user selects No or NoToAll.

        This function controls the message box prompt for saving
        changed files.  The actual save is performed in save() for
        each index processed. This function also removes autosave files
        corresponding to files the user chooses not to save.
        """
        if index is None:
            indexes = list(range(self.get_stack_count()))
        else:
            indexes = [index]
        buttons = QMessageBox.Yes | QMessageBox.No
        if cancelable:
            buttons |= QMessageBox.Cancel
        unsaved_nb = 0
        for index in indexes:
            if self.data[index].editor.document().isModified():
                unsaved_nb += 1
        if not unsaved_nb:
            # No file to save
            return True
        if unsaved_nb > 1:
            buttons |= int(QMessageBox.YesToAll | QMessageBox.NoToAll)
        yes_all = no_all = False
        for index in indexes:
            self.set_stack_index(index)
            finfo = self.data[index]
            if finfo.filename == self.tempfile_path or yes_all:
                if not self.save(index):
                    return False
            elif no_all:
                self.autosave.remove_autosave_file(finfo)
            elif (finfo.editor.document().isModified() and
                  self.save_dialog_on_tests):

                self.msgbox = QMessageBox(
                        QMessageBox.Question,
                        self.title,
                        _("<b>%s</b> has been modified."
                          "<br>Do you want to save changes?"
                         ) % osp.basename(finfo.filename),
                          buttons,
                          parent=self)

                answer = self.msgbox.exec_()
                if answer == QMessageBox.Yes:
                    if not self.save(index):
                        return False
                elif answer == QMessageBox.No:
                    self.autosave.remove_autosave_file(finfo.filename)
                elif answer == QMessageBox.YesToAll:
                    if not self.save(index):
                        return False
                    yes_all = True
                elif answer == QMessageBox.NoToAll:
                    self.autosave.remove_autosave_file(finfo.filename)
                    no_all = True
                elif answer == QMessageBox.Cancel:
                    return False
        return True

    def compute_hash(self, fileinfo):
        """Compute hash of contents of editor.

        Args:
            fileinfo: FileInfo object associated to editor whose hash needs
                to be computed.

        Returns:
            int: computed hash.
        """
        txt = fileinfo.editor.get_text_with_eol()
        return hash(txt)

    def _write_to_file(self, fileinfo, filename):
        """Low-level function for writing text of editor to file.

        Args:
            fileinfo: FileInfo object associated to editor to be saved
            filename: str with filename to save to

        This is a low-level function that only saves the text to file in the
        correct encoding without doing any error handling.
        """
        txt = fileinfo.editor.get_text_with_eol()
        fileinfo.encoding = encoding.write(txt, filename, fileinfo.encoding)

    def save(self, index=None, force=False, save_new_files=True):
        """Write text of editor to a file.

        Args:
            index: self.data index to save.  If None, defaults to
                currentIndex().
            force: Force save regardless of file state.

        Returns:
            True upon successful save or when file doesn't need to be saved.
            False if save failed.

        If the text isn't modified and it's not newly created, then the save
        is aborted.  If the file hasn't been saved before, then save_as()
        is invoked.  Otherwise, the file is written using the file name
        currently in self.data.  This function doesn't change the file name.
        """
        if index is None:
            # Save the currently edited file
            if not self.get_stack_count():
                return
            index = self.get_stack_index()

        finfo = self.data[index]
        if not (finfo.editor.document().isModified() or
                finfo.newly_created) and not force:
            return True
        if not osp.isfile(finfo.filename) and not force:
            # File has not been saved yet
            if save_new_files:
                return self.save_as(index=index)
            # The file doesn't need to be saved
            return True
        if self.always_remove_trailing_spaces:
            self.remove_trailing_spaces(index)
        if self.remove_trailing_newlines:
            self.trim_trailing_newlines(index)
        if self.add_newline:
            self.add_newline_to_file(index)
        if self.convert_eol_on_save:
            # hack to account for the fact that the config file saves
            # CR/LF/CRLF while set_os_eol_chars wants the os.name value.
            osname_lookup = {'LF': 'posix', 'CRLF': 'nt', 'CR': 'mac'}
            osname = osname_lookup[self.convert_eol_on_save_to]
            self.set_os_eol_chars(osname=osname)

        try:
            if self.format_on_save and finfo.editor.formatting_enabled:
                # Autoformat document and then save
                finfo.editor.sig_stop_operation_in_progress.connect(
                    functools.partial(self._save_file, finfo, index))
                finfo.editor.format_document()
            else:
                self._save_file(finfo, index)
            return True
        except EnvironmentError as error:
            self.msgbox = QMessageBox(
                    QMessageBox.Critical,
                    _("Save Error"),
                    _("<b>Unable to save file '%s'</b>"
                      "<br><br>Error message:<br>%s"
                      ) % (osp.basename(finfo.filename),
                                        str(error)),
                    parent=self)
            self.msgbox.exec_()
            return False

    def _save_file(self, finfo, index):
        self._write_to_file(finfo, finfo.filename)
        file_hash = self.compute_hash(finfo)
        self.autosave.file_hashes[finfo.filename] = file_hash
        self.autosave.remove_autosave_file(finfo.filename)
        finfo.newly_created = False
        self.encoding_changed.emit(finfo.encoding)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()

        # We pass self object ID as a QString, because otherwise it would
        # depend on the platform: long for 64bit, int for 32bit. Replacing
        # by long all the time is not working on some 32bit platforms.
        # See spyder-ide/spyder#1094 and spyder-ide/spyder#1098.
        # The filename is passed instead of an index in case the tabs
        # have been rearranged. See spyder-ide/spyder#5703.
        self.file_saved.emit(str(id(self)),
                             finfo.filename, finfo.filename)

        finfo.editor.document().setModified(False)
        self.modification_changed(index=index)
        self.analyze_script(index)

        finfo.editor.notify_save()

    def file_saved_in_other_editorstack(self, original_filename, filename):
        """
        File was just saved in another editorstack, let's synchronize!
        This avoids file being automatically reloaded.

        The original filename is passed instead of an index in case the tabs
        on the editor stacks were moved and are now in a different order - see
        spyder-ide/spyder#5703.
        Filename is passed in case file was just saved as another name.
        """
        index = self.has_filename(original_filename)
        if index is None:
            return
        finfo = self.data[index]
        finfo.newly_created = False
        finfo.filename = to_text_string(filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()

    def select_savename(self, original_filename):
        """Select a name to save a file.

        Args:
            original_filename: Used in the dialog to display the current file
                    path and name.

        Returns:
            Normalized path for the selected file name or None if no name was
            selected.
        """
        if self.edit_filetypes is None:
            self.edit_filetypes = get_edit_filetypes()
        if self.edit_filters is None:
            self.edit_filters = get_edit_filters()

        # Don't use filters on KDE to not make the dialog incredible
        # slow
        # Fixes spyder-ide/spyder#4156.
        if is_kde_desktop() and not is_anaconda():
            filters = ''
            selectedfilter = ''
        else:
            filters = self.edit_filters
            selectedfilter = get_filter(self.edit_filetypes,
                                        osp.splitext(original_filename)[1])

        self.redirect_stdio.emit(False)
        filename, _selfilter = getsavefilename(self, _("Save file"),
                                    original_filename,
                                    filters=filters,
                                    selectedfilter=selectedfilter,
                                    options=QFileDialog.HideNameFilterDetails)
        self.redirect_stdio.emit(True)
        if filename:
            return osp.normpath(filename)
        return None

    def save_as(self, index=None):
        """Save file as...

        Args:
            index: self.data index for the file to save.

        Returns:
            False if no file name was selected or if save() was unsuccessful.
            True is save() was successful.

        Gets the new file name from select_savename().  If no name is chosen,
        then the save_as() aborts.  Otherwise, the current stack is checked
        to see if the selected name already exists and, if so, then the tab
        with that name is closed.

        The current stack (self.data) and current tabs are updated with the
        new name and other file info.  The text is written with the new
        name using save() and the name change is propagated to the other stacks
        via the file_renamed_in_data signal.
        """
        if index is None:
            # Save the currently edited file
            index = self.get_stack_index()
        finfo = self.data[index]
        original_newly_created = finfo.newly_created
        # The next line is necessary to avoid checking if the file exists
        # While running __check_file_status
        # See spyder-ide/spyder#3678 and spyder-ide/spyder#3026.
        finfo.newly_created = True
        original_filename = finfo.filename
        filename = self.select_savename(original_filename)
        if filename:
            ao_index = self.has_filename(filename)
            # Note: ao_index == index --> saving an untitled file
            if ao_index is not None and ao_index != index:
                if not self.close_file(ao_index):
                    return
                if ao_index < index:
                    index -= 1

            new_index = self.rename_in_data(original_filename,
                                            new_filename=filename)

            # We pass self object ID as a QString, because otherwise it would
            # depend on the platform: long for 64bit, int for 32bit. Replacing
            # by long all the time is not working on some 32bit platforms
            # See spyder-ide/spyder#1094 and spyder-ide/spyder#1098.
            self.file_renamed_in_data.emit(str(id(self)),
                                           original_filename, filename)

            ok = self.save(index=new_index, force=True)
            self.refresh(new_index)
            self.set_stack_index(new_index)
            return ok
        else:
            finfo.newly_created = original_newly_created
            return False

    def save_copy_as(self, index=None):
        """Save copy of file as...

        Args:
            index: self.data index for the file to save.

        Returns:
            False if no file name was selected or if save() was unsuccessful.
            True is save() was successful.

        Gets the new file name from select_savename().  If no name is chosen,
        then the save_copy_as() aborts.  Otherwise, the current stack is
        checked to see if the selected name already exists and, if so, then the
        tab with that name is closed.

        Unlike save_as(), this calls write() directly instead of using save().
        The current file and tab aren't changed at all.  The copied file is
        opened in a new tab.
        """
        if index is None:
            # Save the currently edited file
            index = self.get_stack_index()
        finfo = self.data[index]
        original_filename = finfo.filename
        filename = self.select_savename(original_filename)
        if filename:
            ao_index = self.has_filename(filename)
            # Note: ao_index == index --> saving an untitled file
            if ao_index is not None and ao_index != index:
                if not self.close_file(ao_index):
                    return
                if ao_index < index:
                    index -= 1
            try:
                self._write_to_file(finfo, filename)
                # open created copy file
                self.plugin_load.emit(filename)
                return True
            except EnvironmentError as error:
                self.msgbox = QMessageBox(
                    QMessageBox.Critical,
                    _("Save Error"),
                    _("<b>Unable to save file '%s'</b>"
                      "<br><br>Error message:<br>%s"
                      ) % (osp.basename(finfo.filename),
                                        str(error)),
                    parent=self)
                self.msgbox.exec_()
        else:
            return False

    def save_all(self, save_new_files=True):
        """Save all opened files.

        Iterate through self.data and call save() on any modified files.
        """
        all_saved = True
        for index in range(self.get_stack_count()):
            if self.data[index].editor.document().isModified():
                all_saved &= self.save(index, save_new_files=save_new_files)
        return all_saved

    #------ Update UI
    def start_stop_analysis_timer(self):
        self.is_analysis_done = False
        self.analysis_timer.stop()
        self.analysis_timer.start()

    def analyze_script(self, index=None):
        """Analyze current script for TODOs."""
        if self.is_analysis_done:
            return
        if index is None:
            index = self.get_stack_index()
        if self.data and len(self.data) > index:
            finfo = self.data[index]
            if self.todolist_enabled:
                finfo.run_todo_finder()
        self.is_analysis_done = True

    def set_todo_results(self, filename, todo_results):
        """Synchronize todo results between editorstacks"""
        index = self.has_filename(filename)
        if index is None:
            return
        self.data[index].set_todo_results(todo_results)

    def get_todo_results(self):
        if self.data:
            return self.data[self.get_stack_index()].todo_results

    def current_changed(self, index):
        """Stack index has changed"""
        editor = self.get_current_editor()
        if index != -1:
            editor.setFocus()
            logger.debug("Set focus to: %s" % editor.filename)
        else:
            self.reset_statusbar.emit()
        self.opened_files_list_changed.emit()

        self.stack_history.refresh()
        self.stack_history.remove_and_append(index)

        # Needed to avoid an error generated after moving/renaming
        # files outside Spyder while in debug mode.
        # See spyder-ide/spyder#8749.
        try:
            logger.debug("Current changed: %d - %s" %
                         (index, self.data[index].editor.filename))
        except IndexError:
            pass

        self.update_plugin_title.emit()
        # Make sure that any replace happens in the editor on top
        # See spyder-ide/spyder#9688.
        self.find_widget.set_editor(editor, refresh=False)

        if editor is not None:
            # Needed in order to handle the close of files open in a directory
            # that has been renamed. See spyder-ide/spyder#5157.
            try:
                line, col = editor.get_cursor_line_column()
                self.current_file_changed.emit(self.data[index].filename,
                                               editor.get_position('cursor'),
                                               line, col)
            except IndexError:
                pass

    def _get_previous_file_index(self):
        """Return the penultimate element of the stack history."""
        try:
            return self.stack_history[-2]
        except IndexError:
            return None

    def tab_navigation_mru(self, forward=True):
        """
        Tab navigation with "most recently used" behaviour.

        It's fired when pressing 'go to previous file' or 'go to next file'
        shortcuts.

        forward:
            True: move to next file
            False: move to previous file
        """
        self.tabs_switcher = TabSwitcherWidget(self, self.stack_history,
                                               self.tabs)
        self.tabs_switcher.show()
        self.tabs_switcher.select_row(1 if forward else -1)
        self.tabs_switcher.setFocus()

    def focus_changed(self):
        """Editor focus has changed"""
        fwidget = QApplication.focusWidget()
        for finfo in self.data:
            if fwidget is finfo.editor:
                if finfo.editor.operation_in_progress:
                    self.spinner.start()
                else:
                    self.spinner.stop()
                self.refresh()
        self.editor_focus_changed.emit()

    def _refresh_outlineexplorer(self, index=None, update=True, clear=False):
        """Refresh outline explorer panel"""
        oe = self.outlineexplorer
        if oe is None:
            return
        if index is None:
            index = self.get_stack_index()
        if self.data and len(self.data) > index:
            finfo = self.data[index]
            oe.setEnabled(True)
            oe.set_current_editor(finfo.editor.oe_proxy,
                                  update=update, clear=clear)
            if index != self.get_stack_index():
                # The last file added to the outline explorer is not the
                # currently focused one in the editor stack. Therefore,
                # we need to force a refresh of the outline explorer to set
                # the current editor to the currently focused one in the
                # editor stack. See spyder-ide/spyder#8015.
                self._refresh_outlineexplorer(update=False)
                return
        self._sync_outlineexplorer_file_order()

    def _sync_outlineexplorer_file_order(self):
        """
        Order the root file items of the outline explorer as in the tabbar
        of the current EditorStack.
        """
        if self.outlineexplorer is not None:
            self.outlineexplorer.treewidget.set_editor_ids_order(
                [finfo.editor.get_document_id() for finfo in self.data])

    def __refresh_statusbar(self, index):
        """Refreshing statusbar widgets"""
        if self.data and len(self.data) > index:
            finfo = self.data[index]
            self.encoding_changed.emit(finfo.encoding)
            # Refresh cursor position status:
            line, index = finfo.editor.get_cursor_line_column()
            self.sig_editor_cursor_position_changed.emit(line, index)

    def __refresh_readonly(self, index):
        if self.data and len(self.data) > index:
            finfo = self.data[index]
            read_only = not QFileInfo(finfo.filename).isWritable()
            if not osp.isfile(finfo.filename):
                # This is an 'untitledX.py' file (newly created)
                read_only = False
            elif os.name == 'nt':
                try:
                    # Try to open the file to see if its permissions allow
                    # to write on it
                    # Fixes spyder-ide/spyder#10657
                    fd = os.open(finfo.filename, os.O_RDWR)
                    os.close(fd)
                except (IOError, OSError):
                    read_only = True
            finfo.editor.setReadOnly(read_only)
            self.readonly_changed.emit(read_only)

    def __check_file_status(self, index):
        """Check if file has been changed in any way outside Spyder:
        1. removed, moved or renamed outside Spyder
        2. modified outside Spyder"""
        if self.__file_status_flag:
            # Avoid infinite loop: when the QMessageBox.question pops, it
            # gets focus and then give it back to the CodeEditor instance,
            # triggering a refresh cycle which calls this method
            return
        self.__file_status_flag = True

        if len(self.data) <= index:
            index = self.get_stack_index()

        finfo = self.data[index]
        name = osp.basename(finfo.filename)

        if finfo.newly_created:
            # File was just created (not yet saved): do nothing
            # (do not return because of the clean-up at the end of the method)
            pass

        elif not osp.isfile(finfo.filename):
            # File doesn't exist (removed, moved or offline):
            self.msgbox = QMessageBox(
                    QMessageBox.Warning,
                    self.title,
                    _("<b>%s</b> is unavailable "
                      "(this file may have been removed, moved "
                      "or renamed outside Spyder)."
                      "<br>Do you want to close it?") % name,
                    QMessageBox.Yes | QMessageBox.No,
                    self)
            answer = self.msgbox.exec_()
            if answer == QMessageBox.Yes:
                self.close_file(index)
            else:
                finfo.newly_created = True
                finfo.editor.document().setModified(True)
                self.modification_changed(index=index)

        else:
            # Else, testing if it has been modified elsewhere:
            lastm = QFileInfo(finfo.filename).lastModified()
            if to_text_string(lastm.toString()) \
               != to_text_string(finfo.lastmodified.toString()):
                if finfo.editor.document().isModified():
                    self.msgbox = QMessageBox(
                        QMessageBox.Question,
                        self.title,
                        _("<b>%s</b> has been modified outside Spyder."
                          "<br>Do you want to reload it and lose all "
                          "your changes?") % name,
                        QMessageBox.Yes | QMessageBox.No,
                        self)
                    answer = self.msgbox.exec_()
                    if answer == QMessageBox.Yes:
                        self.reload(index)
                    else:
                        finfo.lastmodified = lastm
                else:
                    self.reload(index)

        # Finally, resetting temporary flag:
        self.__file_status_flag = False

    def __modify_stack_title(self):
        for index, finfo in enumerate(self.data):
            state = finfo.editor.document().isModified()
            self.set_stack_title(index, state)

    def refresh(self, index=None):
        """Refresh tabwidget"""
        if index is None:
            index = self.get_stack_index()
        # Set current editor
        if self.get_stack_count():
            index = self.get_stack_index()
            finfo = self.data[index]
            editor = finfo.editor
            editor.setFocus()
            self._refresh_outlineexplorer(index, update=False)
            self.update_code_analysis_actions.emit()
            self.__refresh_statusbar(index)
            self.__refresh_readonly(index)
            self.__check_file_status(index)
            self.__modify_stack_title()
            self.update_plugin_title.emit()
        else:
            editor = None
        # Update the modification-state-dependent parameters
        self.modification_changed()
        # Update FindReplace binding
        self.find_widget.set_editor(editor, refresh=False)

    def modification_changed(self, state=None, index=None, editor_id=None):
        """
        Current editor's modification state has changed
        --> change tab title depending on new modification state
        --> enable/disable save/save all actions
        """
        if editor_id is not None:
            for index, _finfo in enumerate(self.data):
                if id(_finfo.editor) == editor_id:
                    break
        # This must be done before refreshing save/save all actions:
        # (otherwise Save/Save all actions will always be enabled)
        self.opened_files_list_changed.emit()
        # --
        if index is None:
            index = self.get_stack_index()
        if index == -1:
            return
        finfo = self.data[index]
        if state is None:
            state = finfo.editor.document().isModified() or finfo.newly_created
        self.set_stack_title(index, state)
        # Toggle save/save all actions state
        self.save_action.setEnabled(state)
        self.refresh_save_all_action.emit()
        # Refreshing eol mode
        eol_chars = finfo.editor.get_line_separator()
        self.refresh_eol_chars(eol_chars)
        self.stack_history.refresh()

    def refresh_eol_chars(self, eol_chars):
        os_name = sourcecode.get_os_name_from_eol_chars(eol_chars)
        self.sig_refresh_eol_chars.emit(os_name)

    #  ------ Load, reload
    def reload(self, index):
        """Reload file from disk."""
        finfo = self.data[index]
        logger.debug("Reloading {}".format(finfo.filename))

        txt, finfo.encoding = encoding.read(finfo.filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
        position = finfo.editor.get_position('cursor')
        finfo.editor.set_text(txt)
        finfo.editor.document().setModified(False)
        self.autosave.file_hashes[finfo.filename] = hash(txt)
        finfo.editor.set_cursor_position(position)

        #XXX CodeEditor-only: re-scan the whole text to rebuild outline
        # explorer data from scratch (could be optimized because
        # rehighlighting text means searching for all syntax coloring
        # patterns instead of only searching for class/def patterns which
        # would be sufficient for outline explorer data.
        finfo.editor.rehighlight()

    def revert(self):
        """Revert file from disk."""
        index = self.get_stack_index()
        finfo = self.data[index]
        logger.debug("Reverting {}".format(finfo.filename))

        filename = finfo.filename
        if finfo.editor.document().isModified():
            self.msgbox = QMessageBox(
                    QMessageBox.Warning,
                    self.title,
                    _("All changes to <b>%s</b> will be lost."
                      "<br>Do you want to revert file from disk?"
                      ) % osp.basename(filename),
                    QMessageBox.Yes | QMessageBox.No,
                    self)
            answer = self.msgbox.exec_()
            if answer != QMessageBox.Yes:
                return
        self.reload(index)

    def create_new_editor(self, fname, enc, txt, set_current, new=False,
                          cloned_from=None, add_where='end'):
        """
        Create a new editor instance
        Returns finfo object (instead of editor as in previous releases)
        """
        editor = codeeditor.CodeEditor(self)
        editor.go_to_definition.connect(
            lambda fname, line, column: self.sig_go_to_definition.emit(
                fname, line, column))

        finfo = FileInfo(fname, enc, editor, new, self.threadmanager)

        self.add_to_data(finfo, set_current, add_where)
        finfo.sig_send_to_help.connect(self.send_to_help)
        finfo.sig_show_object_info.connect(self.inspect_current_object)
        finfo.todo_results_changed.connect(
            lambda: self.todo_results_changed.emit())
        finfo.edit_goto.connect(lambda fname, lineno, name:
                                self.edit_goto.emit(fname, lineno, name))
        finfo.sig_save_bookmarks.connect(lambda s1, s2:
                                         self.sig_save_bookmarks.emit(s1, s2))
        editor.sig_run_selection.connect(self.run_selection)
        editor.sig_run_cell.connect(self.run_cell)
        editor.sig_debug_cell.connect(self.debug_cell)
        editor.sig_run_cell_and_advance.connect(self.run_cell_and_advance)
        editor.sig_re_run_last_cell.connect(self.re_run_last_cell)
        editor.sig_new_file.connect(self.sig_new_file.emit)
        editor.sig_breakpoints_saved.connect(self.sig_breakpoints_saved)
        editor.sig_process_code_analysis.connect(
            lambda: self.update_code_analysis_actions.emit())
        editor.sig_refresh_formatting.connect(self.sig_refresh_formatting)
        language = get_file_language(fname, txt)
        editor.setup_editor(
            linenumbers=self.linenumbers_enabled,
            show_blanks=self.blanks_enabled,
            underline_errors=self.underline_errors_enabled,
            scroll_past_end=self.scrollpastend_enabled,
            edge_line=self.edgeline_enabled,
            edge_line_columns=self.edgeline_columns,
            language=language,
            markers=self.has_markers(),
            font=self.default_font,
            color_scheme=self.color_scheme,
            wrap=self.wrap_enabled,
            tab_mode=self.tabmode_enabled,
            strip_mode=self.stripmode_enabled,
            intelligent_backspace=self.intelligent_backspace_enabled,
            automatic_completions=self.automatic_completions_enabled,
            automatic_completions_after_chars=self.automatic_completion_chars,
            automatic_completions_after_ms=self.automatic_completion_ms,
            code_snippets=self.code_snippets_enabled,
            completions_hint=self.completions_hint_enabled,
            completions_hint_after_ms=self.completions_hint_after_ms,
            hover_hints=self.hover_hints_enabled,
            highlight_current_line=self.highlight_current_line_enabled,
            highlight_current_cell=self.highlight_current_cell_enabled,
            occurrence_highlighting=self.occurrence_highlighting_enabled,
            occurrence_timeout=self.occurrence_highlighting_timeout,
            close_parentheses=self.close_parentheses_enabled,
            close_quotes=self.close_quotes_enabled,
            add_colons=self.add_colons_enabled,
            auto_unindent=self.auto_unindent_enabled,
            indent_chars=self.indent_chars,
            tab_stop_width_spaces=self.tab_stop_width_spaces,
            cloned_from=cloned_from,
            filename=fname,
            show_class_func_dropdown=self.show_class_func_dropdown,
            indent_guides=self.indent_guides,
            folding=self.code_folding_enabled,
            remove_trailing_spaces=self.always_remove_trailing_spaces,
            remove_trailing_newlines=self.remove_trailing_newlines,
            add_newline=self.add_newline,
            format_on_save=self.format_on_save
        )
        if cloned_from is None:
            editor.set_text(txt)
            editor.document().setModified(False)
        finfo.text_changed_at.connect(
            lambda fname, position:
            self.text_changed_at.emit(fname, position))
        editor.sig_cursor_position_changed.connect(
                                           self.editor_cursor_position_changed)
        editor.textChanged.connect(self.start_stop_analysis_timer)

        # Register external panels
        for panel_class, args, kwargs, position in self.external_panels:
            self.register_panel(
                panel_class, *args, position=position, **kwargs)

        def perform_completion_request(lang, method, params):
            self.sig_perform_completion_request.emit(lang, method, params)

        editor.sig_perform_completion_request.connect(
            perform_completion_request)
        editor.sig_start_operation_in_progress.connect(self.spinner.start)
        editor.sig_stop_operation_in_progress.connect(self.spinner.stop)
        editor.modificationChanged.connect(
            lambda state: self.modification_changed(
                state, editor_id=id(editor)))
        editor.focus_in.connect(self.focus_changed)
        editor.zoom_in.connect(lambda: self.zoom_in.emit())
        editor.zoom_out.connect(lambda: self.zoom_out.emit())
        editor.zoom_reset.connect(lambda: self.zoom_reset.emit())
        editor.sig_eol_chars_changed.connect(
            lambda eol_chars: self.refresh_eol_chars(eol_chars))

        self.find_widget.set_editor(editor)

        self.refresh_file_dependent_actions.emit()
        self.modification_changed(index=self.data.index(finfo))

        # To update the outline explorer.
        editor.oe_proxy = OutlineExplorerProxyEditor(editor, editor.filename)
        if self.outlineexplorer is not None:
            self.outlineexplorer.register_editor(editor.oe_proxy)

        # Needs to reset the highlighting on startup in case the PygmentsSH
        # is in use
        editor.run_pygments_highlighter()
        options = {
            'language': editor.language,
            'filename': editor.filename,
            'codeeditor': editor
        }
        self.sig_open_file.emit(options)
        if self.get_stack_index() == 0:
            self.current_changed(0)

        return finfo

    def editor_cursor_position_changed(self, line, index):
        """Cursor position of one of the editor in the stack has changed"""
        self.sig_editor_cursor_position_changed.emit(line, index)

    @Slot(str, str, bool)
    def send_to_help(self, name, signature, force=False):
        """qstr1: obj_text, qstr2: argpspec, qstr3: note, qstr4: doc_text"""
        if not force and not self.help_enabled:
            return

        editor = self.get_current_editor()
        language = editor.language.lower()
        signature = to_text_string(signature)
        signature = unicodedata.normalize("NFKD", signature)
        parts = signature.split('\n\n')
        definition = parts[0]
        documentation = '\n\n'.join(parts[1:])
        args = ''

        if '(' in definition and language == 'python':
            args = definition[definition.find('('):]
        else:
            documentation = signature

        doc = {
            'obj_text': '',
            'name': name,
            'argspec': args,
            'note': '',
            'docstring': documentation,
            'force_refresh': force,
            'path': editor.filename
        }
        self.sig_help_requested.emit(doc)

    def new(self, filename, encoding, text, default_content=False,
            empty=False):
        """
        Create new filename with *encoding* and *text*
        """
        finfo = self.create_new_editor(filename, encoding, text,
                                       set_current=False, new=True)
        finfo.editor.set_cursor_position('eof')
        if not empty:
            finfo.editor.insert_text(os.linesep)
        if default_content:
            finfo.default = True
            finfo.editor.document().setModified(False)
        return finfo

    def load(self, filename, set_current=True, add_where='end',
             processevents=True):
        """
        Load filename, create an editor instance and return it

        This also sets the hash of the loaded file in the autosave component.

        *Warning* This is loading file, creating editor but not executing
        the source code analysis -- the analysis must be done by the editor
        plugin (in case multiple editorstack instances are handled)
        """
        filename = osp.abspath(to_text_string(filename))
        if processevents:
            self.starting_long_process.emit(_("Loading %s...") % filename)
        text, enc = encoding.read(filename)
        self.autosave.file_hashes[filename] = hash(text)
        finfo = self.create_new_editor(filename, enc, text, set_current,
                                       add_where=add_where)
        index = self.data.index(finfo)
        if processevents:
            self.ending_long_process.emit("")
        if self.isVisible() and self.checkeolchars_enabled \
           and sourcecode.has_mixed_eol_chars(text):
            name = osp.basename(filename)
            self.msgbox = QMessageBox(
                    QMessageBox.Warning,
                    self.title,
                    _("<b>%s</b> contains mixed end-of-line "
                      "characters.<br>Spyder will fix this "
                      "automatically.") % name,
                    QMessageBox.Ok,
                    self)
            self.msgbox.exec_()
            self.set_os_eol_chars(index)
        self.is_analysis_done = False
        self.analyze_script(index)
        return finfo

    def set_os_eol_chars(self, index=None, osname=None):
        """Sets the EOL character(s) based on the operating system.

        If `osname` is None, then the default line endings for the current
        operating system (`os.name` value) will be used.

        `osname` can be one of:
            ('posix', 'nt', 'java')
        """
        if osname is None:
            osname = os.name
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        eol_chars = sourcecode.get_eol_chars_from_os_name(osname)
        finfo.editor.set_eol_chars(eol_chars)
        finfo.editor.document().setModified(True)

    def remove_trailing_spaces(self, index=None):
        """Remove trailing spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.trim_trailing_spaces()

    def trim_trailing_newlines(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.trim_trailing_newlines()

    def add_newline_to_file(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.add_newline_to_file()

    def fix_indentation(self, index=None):
        """Replace tab characters by spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.fix_indentation()

    def format_document_or_selection(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.format_document_or_range()

    #  ------ Run
    def run_selection(self):
        """
        Run selected text or current line in console.

        If some text is selected, then execute that text in console.

        If no text is selected, then execute current line, unless current line
        is empty. Then, advance cursor to next line. If cursor is on last line
        and that line is not empty, then add a new blank line and move the
        cursor there. If cursor is on last line and that line is empty, then do
        not move cursor.
        """
        text = self.get_current_editor().get_selection_as_executable_code()
        if text:
            self.exec_in_extconsole.emit(text.rstrip(), self.focus_to_editor)
            return
        editor = self.get_current_editor()
        line = editor.get_current_line()
        text = line.lstrip()
        if text:
            self.exec_in_extconsole.emit(text, self.focus_to_editor)
        if editor.is_cursor_on_last_line() and text:
            editor.append(editor.get_line_separator())
        editor.move_cursor_to_next('line', 'down')

    def run_cell(self, debug=False):
        """Run current cell."""
        text, block = self.get_current_editor().get_cell_as_executable_code()
        finfo = self.get_current_finfo()
        editor = self.get_current_editor()
        name = cell_name(block)
        filename = finfo.filename

        self._run_cell_text(text, editor, (filename, name), debug)

    def debug_cell(self):
        """Debug current cell."""
        self.run_cell(debug=True)

    def run_cell_and_advance(self):
        """Run current cell and advance to the next one"""
        self.run_cell()
        self.advance_cell()

    def advance_cell(self, reverse=False):
        """Advance to the next cell.

        reverse = True --> go to previous cell.
        """
        if not reverse:
            move_func = self.get_current_editor().go_to_next_cell
        else:
            move_func = self.get_current_editor().go_to_previous_cell

        if self.focus_to_editor:
            move_func()
        else:
            term = QApplication.focusWidget()
            move_func()
            term.setFocus()
            term = QApplication.focusWidget()
            move_func()
            term.setFocus()

    def re_run_last_cell(self):
        """Run the previous cell again."""
        if self.last_cell_call is None:
            return
        filename, cell_name = self.last_cell_call
        index = self.has_filename(filename)
        if index is None:
            return
        editor = self.data[index].editor

        try:
            text = editor.get_cell_code(cell_name)
        except RuntimeError:
            return

        self._run_cell_text(text, editor, (filename, cell_name))

    def _run_cell_text(self, text, editor, cell_id, debug=False):
        """Run cell code in the console.

        Cell code is run in the console by copying it to the console if
        `self.run_cell_copy` is ``True`` otherwise by using the `run_cell`
        function.

        Parameters
        ----------
        text : str
            The code in the cell as a string.
        line : int
            The starting line number of the cell in the file.
        """
        (filename, cell_name) = cell_id
        if editor.is_python_or_ipython():
            args = (text, cell_name, filename, self.run_cell_copy)
            if debug:
                self.debug_cell_in_ipyclient.emit(*args)
            else:
                self.run_cell_in_ipyclient.emit(*args)
        if self.focus_to_editor:
            editor.setFocus()
        else:
            console = QApplication.focusWidget()
            console.setFocus()

    #  ------ Drag and drop
    def dragEnterEvent(self, event):
        """
        Reimplemented Qt method.

        Inform Qt about the types of data that the widget accepts.
        """
        logger.debug("dragEnterEvent was received")
        source = event.mimeData()
        # The second check is necessary on Windows, where source.hasUrls()
        # can return True but source.urls() is []
        # The third check is needed since a file could be dropped from
        # compressed files. In Windows mimedata2url(source) returns None
        # Fixes spyder-ide/spyder#5218.
        has_urls = source.hasUrls()
        has_text = source.hasText()
        urls = source.urls()
        all_urls = mimedata2url(source)
        logger.debug("Drag event source has_urls: {}".format(has_urls))
        logger.debug("Drag event source urls: {}".format(urls))
        logger.debug("Drag event source all_urls: {}".format(all_urls))
        logger.debug("Drag event source has_text: {}".format(has_text))
        if has_urls and urls and all_urls:
            text = [encoding.is_text_file(url) for url in all_urls]
            logger.debug("Accept proposed action?: {}".format(any(text)))
            if any(text):
                event.acceptProposedAction()
            else:
                event.ignore()
        elif source.hasText():
            event.acceptProposedAction()
        elif os.name == 'nt':
            # This covers cases like dragging from compressed files,
            # which can be opened by the Editor if they are plain
            # text, but doesn't come with url info.
            # Fixes spyder-ide/spyder#2032.
            logger.debug("Accept proposed action on Windows")
            event.acceptProposedAction()
        else:
            logger.debug("Ignore drag event")
            event.ignore()

    def dropEvent(self, event):
        """
        Reimplement Qt method.

        Unpack dropped data and handle it.
        """
        logger.debug("dropEvent was received")
        source = event.mimeData()
        # The second check is necessary when mimedata2url(source)
        # returns None.
        # Fixes spyder-ide/spyder#7742.
        if source.hasUrls() and mimedata2url(source):
            files = mimedata2url(source)
            files = [f for f in files if encoding.is_text_file(f)]
            files = set(files or [])
            for fname in files:
                self.plugin_load.emit(fname)
        elif source.hasText():
            editor = self.get_current_editor()
            if editor is not None:
                editor.insert_text(source.text())
        else:
            event.ignore()
        event.acceptProposedAction()

    def register_panel(self, panel_class, *args,
                       position=Panel.Position.LEFT, **kwargs):
        """Register a panel in all codeeditors."""
        if (panel_class, args, kwargs, position) not in self.external_panels:
            self.external_panels.append((panel_class, args, kwargs, position))
        for finfo in self.data:
            cur_panel = finfo.editor.panels.register(
                panel_class(*args, **kwargs), position=position)
            if not cur_panel.isVisible():
                cur_panel.setVisible(True)


class EditorSplitter(QSplitter):
    """QSplitter for editor windows."""

    def __init__(self, parent, plugin, menu_actions, first=False,
                 register_editorstack_cb=None, unregister_editorstack_cb=None):
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
        self.editorstack = EditorStack(self, menu_actions)
        self.register_editorstack_cb(self.editorstack)
        if not first:
            self.plugin.clone_editorstack(editorstack=self.editorstack)
        self.editorstack.destroyed.connect(lambda: self.editorstack_closed())
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

    def editorstack_closed(self):
        logger.debug("method 'editorstack_closed':")
        logger.debug("    self  : %r" % self)
        try:
            self.unregister_editorstack_cb(self.editorstack)
            self.editorstack = None
            close_splitter = self.count() == 1
        except (RuntimeError, AttributeError):
            # editorsplitter has been destroyed (happens when closing a
            # EditorMainWindow instance)
            return
        if close_splitter:
            # editorstack just closed was the last widget in this QSplitter
            self.close()
            return
        self.__give_focus_to_remaining_editor()

    def editorsplitter_closed(self):
        logger.debug("method 'editorsplitter_closed':")
        logger.debug("    self  : %r" % self)
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
        self.setOrientation(orientation)
        self.editorstack.set_orientation(orientation)
        editorsplitter = EditorSplitter(self.parent(), self.plugin,
                    self.menu_actions,
                    register_editorstack_cb=self.register_editorstack_cb,
                    unregister_editorstack_cb=self.unregister_editorstack_cb)
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

    def __init__(self, parent, plugin, menu_actions):
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

        # TODO: Check this initialization once the editor is migrated to the
        # new API
        self.outlineexplorer = OutlineExplorerWidget(
            'outline_explorer',
            plugin,
            self,
            context=f'editor_window_{str(id(self))}'
        )
        self.outlineexplorer.edit_goto.connect(
                     lambda filenames, goto, word:
                     plugin.load(filenames=filenames, goto=goto, word=word,
                                 editorwindow=self.parent()))

        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        editorsplitter = EditorSplitter(self, plugin, menu_actions,
                        register_editorstack_cb=self.register_editorstack,
                        unregister_editorstack_cb=self.unregister_editorstack)
        self.editorsplitter = editorsplitter
        editor_layout.addWidget(editorsplitter)
        editor_layout.addWidget(self.find_widget)

        splitter = QSplitter(self)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(editor_widgets)
        splitter.addWidget(self.outlineexplorer)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        logger.debug("EditorWidget.register_editorstack: %r" % editorstack)
        self.__print_editorstacks()
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
        logger.debug("%d editorstack(s) in editorwidget:" %
                     len(self.editorstacks))
        for edst in self.editorstacks:
            logger.debug("    %r" % edst)

    def unregister_editorstack(self, editorstack):
        logger.debug("EditorWidget.unregister_editorstack: %r" % editorstack)
        self.plugin.unregister_editorstack(editorstack)
        self.editorstacks.pop(self.editorstacks.index(editorstack))
        self.__print_editorstacks()


class EditorMainWindow(QMainWindow):
    def __init__(self, plugin, menu_actions, toolbar_list, menu_list):
        QMainWindow.__init__(self)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.plugin = plugin
        self.window_size = None

        self.editorwidget = EditorWidget(self, plugin, menu_actions)
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

        if toolbar_list:
            self.toolbars = []
            for title, object_name, actions in toolbar_list:
                toolbar = self.addToolBar(title)
                toolbar.setObjectName(object_name)
                toolbar.setStyleSheet(str(APP_TOOLBAR_STYLESHEET))
                toolbar.setMovable(False)
                add_actions(toolbar, actions)
                self.toolbars.append(toolbar)
        if menu_list:
            quit_action = create_action(self, _("Close window"),
                                        icon=ima.icon("close_pane"),
                                        tip=_("Close this window"),
                                        triggered=self.close)
            self.menus = []
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
        toolbars_names = CONF.get('main', 'last_visible_toolbars', default=[])
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
        if self.plugin._undocked_window is not None:
            self.plugin.dockwidget.setWidget(self.plugin)
            self.plugin.dockwidget.setVisible(True)
        self.plugin.switch_to_plugin()
        QMainWindow.closeEvent(self, event)
        if self.plugin._undocked_window is not None:
            self.plugin._undocked_window = None

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
        menu_actions = []

        self.editorstacks = []
        self.editorwindows = []

        self.last_focused_editorstack = {} # fake

        self.find_widget = FindReplace(self, enable_replace=True)
        self.outlineexplorer = OutlineExplorerWidget(None, self, self)
        self.outlineexplorer.edit_goto.connect(self.go_to_file)
        self.editor_splitter = EditorSplitter(self, self, menu_actions,
                                              first=True)

        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
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
    def file_renamed_in_data_in_editorstack(self, editorstack_id_str,
                                            original_filename, filename):
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

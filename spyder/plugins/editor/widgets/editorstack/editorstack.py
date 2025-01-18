# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""EditorStack Widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import functools
import logging
import os
import os.path as osp
import sys
import unicodedata

# Third party imports
import qstylizer.style
from qtpy import PYQT5, PYQT6
from qtpy.compat import getsavefilename
from qtpy.QtCore import QFileInfo, Qt, QTimer, Signal, Slot
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                            QMessageBox, QVBoxLayout, QWidget, QSizePolicy,
                            QToolBar, QToolButton)
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.plugins import Plugins
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _, running_under_pytest
from spyder.config.gui import is_dark_interface
from spyder.config.utils import (
    get_edit_filetypes, get_edit_filters, get_filter, is_kde_desktop
)
from spyder.plugins.editor.api.panel import Panel
from spyder.plugins.editor.utils.autosave import AutosaveForStack
from spyder.plugins.editor.utils.editor import get_file_language
from spyder.plugins.editor.widgets import codeeditor
from spyder.plugins.editor.widgets.editorstack.helpers import (
    ThreadManager, FileInfo, StackHistory)
from spyder.plugins.editor.widgets.tabswitcher import TabSwitcherWidget
from spyder.plugins.explorer.widgets.explorer import (
    show_in_external_file_explorer)
from spyder.plugins.explorer.widgets.utils import fixpath
from spyder.plugins.outlineexplorer.editor import OutlineExplorerProxyEditor
from spyder.plugins.outlineexplorer.api import cell_name
from spyder.plugins.switcher.api import SwitcherActions
from spyder.py3compat import to_text_string
from spyder.utils import encoding, sourcecode, syntaxhighlighters
from spyder.utils.misc import getcwd_or_home
from spyder.utils.palette import SpyderPalette
from spyder.utils.qthelpers import mimedata2url, create_waitspinner
from spyder.utils.stylesheet import PANES_TABBAR_STYLESHEET
from spyder.widgets.tabs import BaseTabs

logger = logging.getLogger(__name__)


class EditorStackActions:
    CopyAbsolutePath = "copy_absolute_path_action"
    CopyRelativePath = "copy_relative_path_action"
    CloseAllRight = "close_all_rigth_action"
    CloseAllButThis = "close_all_but_this_action"
    SortTabs = "sort_tabs_action"
    ShowInExternalFileExplorer = "show in external file explorer"
    NewWindow = "new_window_action"
    SplitVertically = "split vertically"
    SplitHorizontally = "split horizontally"
    CloseSplitPanel = "close split panel"
    CloseWindow = "close_window_action"


class EditorStackButtons:
    OptionsButton = "editor_stack_options_button"


class EditorStackMenus:
    OptionsMenu = "editorstack_options_menu"


class EditorStackMenuSections:
    GivenSection = "given_section"
    SwitcherSection = "switcher_path_section"
    CloseOrderSection = "close_order_section"
    SplitCloseSection = "split_close_section"
    WindowSection = "window_section"
    NewWindowCloseSection = "new_window_and_close_section"


class EditorStack(QWidget, SpyderWidgetMixin):

    # This is necessary for the EditorStack tests to run independently of the
    # Editor plugin.
    CONF_SECTION = "editor"

    # Signals
    reset_statusbar = Signal()
    readonly_changed = Signal(bool)
    encoding_changed = Signal(str)
    sig_editor_cursor_position_changed = Signal(int, int)
    sig_refresh_eol_chars = Signal(str)
    sig_refresh_formatting = Signal(bool)
    starting_long_process = Signal(str)
    ending_long_process = Signal(str)
    redirect_stdio = Signal(bool)
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
    todo_results_changed = Signal()
    sig_update_code_analysis_actions = Signal()
    refresh_file_dependent_actions = Signal()
    refresh_save_all_action = Signal()
    text_changed_at = Signal(str, tuple)
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
    sig_save_bookmark = Signal(int)
    sig_load_bookmark = Signal(int)
    sig_save_bookmarks = Signal(str, str)
    sig_trigger_run_action = Signal(str)
    sig_trigger_debugger_action = Signal(str)

    sig_open_last_closed = Signal()
    """
    This signal requests that the last closed tab be re-opened.
    """

    sig_codeeditor_created = Signal(object)
    """
    This signal is emitted when a codeeditor is created.

    Parameters
    ----------
    codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        The codeeditor.
    """

    sig_codeeditor_deleted = Signal(object)
    """
    This signal is emitted when a codeeditor is closed.

    Parameters
    ----------
    codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        The codeeditor.
    """

    sig_codeeditor_changed = Signal(object)
    """
    This signal is emitted when the current codeeditor changes.

    Parameters
    ----------
    codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
        The codeeditor.
    """

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
    :py:meth:spyder.plugins.editor.widgets.editorstack.EditorStack.send_to_help
    """

    def __init__(self, parent, actions, use_switcher=True):
        if PYQT5 or PYQT6:
            super().__init__(parent, class_parent=parent)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.threadmanager = ThreadManager(self)

        self.is_closable = False
        self.new_window = False
        self.horsplit_action = None
        self.versplit_action = None
        self.close_split_action = None
        self.__get_split_actions()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.menu = None
        self.tabs = None
        self.tabs_switcher = None

        self.stack_history = StackHistory(self)

        # External panels
        self.external_panels = []

        self.setup_editorstack(parent, layout)

        self.find_widget = None

        self.data = []

        # Actions
        self.switcher_action = None
        self.symbolfinder_action = None
        self.use_switcher = use_switcher

        self.copy_absolute_path_action = self.create_action(
            EditorStackActions.CopyAbsolutePath,
            text=_("Copy absolute path"),
            icon=self.create_icon('editcopy'),
            triggered=lambda: self.copy_absolute_path(),
            register_action=False
        )
        self.copy_relative_path_action = self.create_action(
            EditorStackActions.CopyRelativePath,
            text=_("Copy relative path"),
            icon=self.create_icon('editcopy'),
            triggered=lambda: self.copy_relative_path(),
            register_action=False
        )
        self.close_right = self.create_action(
            EditorStackActions.CloseAllRight,
            text=_("Close all to the right"),
            triggered=self.close_all_right,
            register_action=False
        )
        self.close_all_but_this = self.create_action(
            EditorStackActions.CloseAllButThis,
            text=_("Close all but this"),
            triggered=self.close_all_but_this,
            register_action=False
        )
        self.sort_tabs = self.create_action(
            EditorStackActions.SortTabs,
            text=_("Sort tabs alphabetically"),
            triggered=self.sort_file_tabs_alphabetically,
            register_action=False
        )

        if sys.platform == 'darwin':
            text = _("Show in Finder")
        else:
            text = _("Show in external file explorer")
        self.external_fileexp_action = self.create_action(
            EditorStackActions.ShowInExternalFileExplorer,
            text=text,
            triggered=self.show_in_external_file_explorer,
            context=Qt.WidgetShortcut,
            register_shortcut=True,
            register_action=False
        )
        self.new_window_action = None
        if parent is not None:
            self.new_window_action = self.create_action(
                EditorStackActions.NewWindow,
                text=_("New window"),
                icon=self.create_icon('newwindow'),
                tip=_("Create a new editor window"),
                triggered=parent.main_widget.create_new_window,
                register_action=False
            )
        self._given_actions = actions
        self.outlineexplorer = None
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
        self.indent_chars = " " * 4
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
        self.multicursor_support = True
        self.create_new_file_if_empty = True
        self.indent_guides = False
        self.__file_status_flag = False

        # Set default color scheme
        color_scheme = 'spyder/dark' if is_dark_interface() else 'spyder'
        if color_scheme not in syntaxhighlighters.COLOR_SCHEME_NAMES:
            color_scheme = syntaxhighlighters.COLOR_SCHEME_NAMES[0]
        self.color_scheme = color_scheme

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
        self.register_shortcuts()

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
        if fnames is None or isinstance(fnames, bool):
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

    def copy_absolute_path(self):
        """Copy current filename absolute path to the clipboard."""
        QApplication.clipboard().setText(self.get_current_filename())

    def copy_relative_path(self):
        """Copy current filename relative path to the clipboard."""
        file_drive = osp.splitdrive(self.get_current_filename())[0]
        if (
            os.name == 'nt'
            and osp.splitdrive(getcwd_or_home())[0] != file_drive
        ):
            QMessageBox.warning(
                self,
                _("No available relative path"),
                _("It is not possible to copy a relative path "
                  "for this file because it is placed in a "
                  "different drive than your current working "
                  "directory. Please copy its absolute path.")
            )
        else:
            base_path = getcwd_or_home()
            if self.get_current_project_path():
                base_path = self.get_current_project_path()

            rel_path = osp.relpath(
                self.get_current_filename(), base_path
            ).replace(os.sep, "/")

            QApplication.clipboard().setText(rel_path)

    def register_shortcuts(self):
        """Register shortcuts for this widget."""
        shortcuts = (
            ('Inspect current object', self.inspect_current_object),
            ('Go to line', self.go_to_line),
            (
                "Go to previous file",
                lambda: self.tab_navigation_mru(forward=False),
            ),
            ('Go to next file', self.tab_navigation_mru),
            ('Cycle to previous file', lambda: self.tabs.tab_navigate(-1)),
            ('Cycle to next file', lambda: self.tabs.tab_navigate(1)),
            ('New file', self.sig_new_file[()]),
            ('Open file', self.plugin_load[()]),
            ('Open last closed', self.sig_open_last_closed),
            ('Save file', self.save),
            ('Save all', self.save_all),
            ('Save As', self.sig_save_as),
            ('Close all', self.close_all_files),
            ("Last edit location", self.sig_prev_edit_pos),
            ("Previous cursor position", self.sig_prev_cursor),
            ("Next cursor position", self.sig_next_cursor),
            ("zoom in 1", self.zoom_in),
            ("zoom in 2", self.zoom_in),
            ("zoom out", self.zoom_out),
            ("zoom reset", self.zoom_reset),
            ("close file 1", self.close_file),
            ("close file 2", self.close_file),
            ("go to next cell", self.advance_cell),
            ("go to previous cell", lambda: self.advance_cell(reverse=True)),
            ("Previous warning", self.sig_prev_warning),
            ("Next warning", self.sig_next_warning),
            ("split vertically", self.sig_split_vertically),
            ("split horizontally", self.sig_split_horizontally),
            ("close split panel", self.close_split),
            (
                "show in external file explorer",
                self.show_in_external_file_explorer,
            ),
        )

        for name, callback in shortcuts:
            self.register_shortcut_for_widget(name=name, triggered=callback)

        # Register shortcuts for run actions
        for action_id in [
            "run cell",
            "run cell and advance",
            "re-run cell",
            "run selection and advance",
            "run selection up to line",
            "run selection from line",
            "run cell in debugger",
            "run selection in debugger",
        ]:
            self.register_shortcut_for_widget(
                name=action_id,
                triggered=functools.partial(
                    self.sig_trigger_run_action.emit,
                    action_id,
                ),
            )

        # Register shortcuts for debugger actions
        for action_id in [
            "toggle breakpoint",
            "toggle conditional breakpoint",
        ]:
            self.register_shortcut_for_widget(
                name=action_id,
                triggered=functools.partial(
                    self.sig_trigger_debugger_action.emit,
                    action_id,
                ),
                context=Plugins.Debugger,
            )

    def update_switcher_actions(self, switcher_available):
        if self.use_switcher and switcher_available:
            self.switcher_action = self.get_action(
                SwitcherActions.FileSwitcherAction,
                plugin="switcher"
            )
            self.symbolfinder_action = self.get_action(
                SwitcherActions.SymbolFinderAction,
                plugin="switcher"
            )
        else:
            self.switcher_action = None
            self.symbolfinder_action = None

    def setup_editorstack(self, parent, layout):
        """Setup editorstack's layout"""
        layout.setSpacing(0)

        # Create filename label, spinner and the toolbar that contains them
        self.create_top_widgets()

        # Add top toolbar
        layout.addWidget(self.top_toolbar)

        # Tabbar
        menu_btn = self.create_toolbutton(
            EditorStackButtons.OptionsButton,
            icon=self.create_icon('tooloptions'),
            tip=_('Options'),
            register=False
        )
        menu_btn.setStyleSheet(str(PANES_TABBAR_STYLESHEET))
        self.menu = self.create_menu(
            EditorStackMenus.OptionsMenu,
            register=False
        )
        menu_btn.setMenu(self.menu)
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
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
            borderBottom=f'1px solid {SpyderPalette.COLOR_BACKGROUND_4}'
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

                # Delete reference to oe_proxy for cloned editors to prevent it
                # from receiving the signal to be updated.
                if finfo.editor.is_cloned:
                    finfo.editor.oe_proxy.deleteLater()

        # Notify the LSP that the file was closed, if necessary.
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

    def get_main_widget(self):
        """Get the main_widget of the parent widget."""
        # Needed for the editor stack to use its own switcher instance.
        # See spyder-ide/spyder#10684.
        return self.parent().main_widget

    def get_plugin_title(self):
        """Get the plugin title of the parent widget."""
        # Needed for the editor stack to use its own switcher instance.
        # See spyder-ide/spyder#9469.
        return self.get_main_widget().get_title()

    def go_to_line(self, line=None):
        """Go to line dialog"""
        if line is not None:
            # When this method is called from the fileswitcher, a line
            # number is specified, so there is no need for the dialog.
            self.get_current_editor().go_to_line(line)
        else:
            if self.data:
                self.get_current_editor().exec_gotolinedialog()

    def set_bookmark(self, slot_num):
        """Bookmark current position to given slot."""
        if self.data:
            editor = self.get_current_editor()
            editor.add_bookmark(slot_num)

    @Slot()
    @Slot(bool)
    def inspect_current_object(self, clicked=False):
        """Inspect current object in the Help plugin"""
        editor = self.get_current_editor()
        editor.sig_display_object_info.connect(self.display_help)
        cursor = None
        offset = editor.get_position('cursor')
        if clicked:
            cursor = editor.get_last_hover_cursor()
            if cursor:
                offset = cursor.position()
            else:
                return

        line, col = editor.get_cursor_line_column(cursor)
        editor.request_hover(line, col, offset,
                             show_hint=False, clicked=clicked)

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

    # ---- Editor Widget Settings
    @on_conf_change(section='help', option='connect/editor')
    def on_help_connection_change(self, value):
        self.set_help_enabled(value)

    @on_conf_change(section='appearance', option=['selected', 'ui_theme'])
    def on_color_scheme_change(self, option, value):
        if option == 'ui_theme':
            value = self.get_conf('selected', section='appearance')

        logger.debug(f"Set color scheme to {value}")
        self.set_color_scheme(value)

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

    def set_tempfile_path(self, path):
        self.tempfile_path = path

    def set_title(self, text):
        self.title = text

    @on_conf_change(option='show_class_func_dropdown')
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
        self.todolist_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                finfo.cleanup_todo_results()
                if state and current_finfo is not None:
                    if current_finfo is not finfo:
                        finfo.run_todo_finder()

    @on_conf_change(option='line_numbers')
    def set_linenumbers_enabled(self, state, current_finfo=None):
        self.linenumbers_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)

    @on_conf_change(option='blank_spaces')
    def set_blanks_enabled(self, state):
        self.blanks_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_blanks_enabled(state)

    @on_conf_change(option='scroll_past_end')
    def set_scrollpastend_enabled(self, state):
        self.scrollpastend_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_scrollpastend_enabled(state)

    @on_conf_change(option='edge_line')
    def set_edgeline_enabled(self, state):
        logger.debug(f"Set edge line to {state}")
        self.edgeline_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.edge_line.set_enabled(state)

    @on_conf_change(
        option=('provider_configuration', 'lsp', 'values',
                'pycodestyle/max_line_length'),
        section='completions'
    )
    def set_edgeline_columns(self, columns):
        logger.debug(f"Set edge line columns to {columns}")
        self.edgeline_columns = columns
        if self.data:
            for finfo in self.data:
                finfo.editor.edge_line.set_columns(columns)

    @on_conf_change(option='indent_guides')
    def set_indent_guides(self, state):
        self.indent_guides = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_identation_guides(state)

    @on_conf_change(option='close_parentheses')
    def set_close_parentheses_enabled(self, state):
        self.close_parentheses_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_close_parentheses_enabled(state)

    @on_conf_change(option='close_quotes')
    def set_close_quotes_enabled(self, state):
        self.close_quotes_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_close_quotes_enabled(state)

    @on_conf_change(option='add_colons')
    def set_add_colons_enabled(self, state):
        self.add_colons_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_add_colons_enabled(state)

    @on_conf_change(option='auto_unindent')
    def set_auto_unindent_enabled(self, state):
        self.auto_unindent_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_auto_unindent_enabled(state)

    @on_conf_change(option='indent_chars')
    def set_indent_chars(self, indent_chars):
        indent_chars = indent_chars[1:-1]  # removing the leading/ending '*'
        self.indent_chars = indent_chars
        if self.data:
            for finfo in self.data:
                finfo.editor.set_indent_chars(indent_chars)

    @on_conf_change(option='tab_stop_width_spaces')
    def set_tab_stop_width_spaces(self, tab_stop_width_spaces):
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

                # Update the most important extra selections so new color
                # schemes appear to users as expected.
                finfo.editor.unhighlight_current_line()
                finfo.editor.unhighlight_current_cell()
                finfo.editor.clear_occurrences()

                if self.highlight_current_line_enabled:
                    finfo.editor.highlight_current_line()
                if self.highlight_current_cell_enabled:
                    finfo.editor.highlight_current_cell()
                if self.occurrence_highlighting_enabled:
                    finfo.editor.mark_occurrences()

    @on_conf_change(option='wrap')
    def set_wrap_enabled(self, state):
        self.wrap_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_wrap_mode(state)

    @on_conf_change(option='tab_always_indent')
    def set_tabmode_enabled(self, state):
        self.tabmode_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_tab_mode(state)

    @on_conf_change(option='strip_trailing_spaces_on_modify')
    def set_stripmode_enabled(self, state):
        self.stripmode_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_strip_mode(state)

    @on_conf_change(option='intelligent_backspace')
    def set_intelligent_backspace_enabled(self, state):
        self.intelligent_backspace_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_intelligent_backspace(state)

    @on_conf_change(option='enable_code_snippets', section='completions')
    def set_code_snippets_enabled(self, state):
        logger.debug(f"Set code snippets to {state}")
        self.code_snippets_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_code_snippets(state)

    @on_conf_change(option='code_folding')
    def set_code_folding_enabled(self, state):
        self.code_folding_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_code_folding(state)

    @on_conf_change(option='automatic_completions')
    def set_automatic_completions_enabled(self, state):
        logger.debug(f"Set automatic completions to {state}")
        self.automatic_completions_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_automatic_completions(state)

    @on_conf_change(option='automatic_completions_after_chars')
    def set_automatic_completions_after_chars(self, chars):
        logger.debug(f"Set chars for automatic completions to {chars}")
        self.automatic_completion_chars = chars
        if self.data:
            for finfo in self.data:
                finfo.editor.set_automatic_completions_after_chars(chars)

    @on_conf_change(option='completions_hint')
    def set_completions_hint_enabled(self, state):
        logger.debug(f"Set completions hint to {state}")
        self.completions_hint_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_completions_hint(state)

    @on_conf_change(option='completions_hint_after_ms')
    def set_completions_hint_after_ms(self, ms):
        logger.debug(f"Set completions hint after {ms} ms")
        self.completions_hint_after_ms = ms
        if self.data:
            for finfo in self.data:
                finfo.editor.set_completions_hint_after_ms(ms)

    @on_conf_change(
        option=('provider_configuration', 'lsp', 'values',
                'enable_hover_hints'),
        section='completions'
    )
    def set_hover_hints_enabled(self, state):
        logger.debug(f"Set hover hints to {state}")
        self.hover_hints_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_hover_hints(state)

    @on_conf_change(
        option=('provider_configuration', 'lsp', 'values', 'format_on_save'),
        section='completions'
    )
    def set_format_on_save(self, state):
        logger.debug(f"Set format on save to {state}")
        self.format_on_save = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_format_on_save(state)

    @on_conf_change(option='occurrence_highlighting')
    def set_occurrence_highlighting_enabled(self, state):
        self.occurrence_highlighting_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurrence_highlighting(state)

    @on_conf_change(option='occurrence_highlighting/timeout')
    def set_occurrence_highlighting_timeout(self, timeout):
        self.occurrence_highlighting_timeout = timeout
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurrence_timeout(timeout)

    @on_conf_change(option='underline_errors')
    def set_underline_errors_enabled(self, state):
        logger.debug(f"Set underline errors to {state}")
        self.underline_errors_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_underline_errors_enabled(state)

    @on_conf_change(option='highlight_current_line')
    def set_highlight_current_line_enabled(self, state):
        self.highlight_current_line_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_highlight_current_line(state)

    @on_conf_change(option='highlight_current_cell')
    def set_highlight_current_cell_enabled(self, state):
        self.highlight_current_cell_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_highlight_current_cell(state)

    def set_checkeolchars_enabled(self, state):
        self.checkeolchars_enabled = state

    @on_conf_change(option='always_remove_trailing_spaces')
    def set_always_remove_trailing_spaces(self, state):
        self.always_remove_trailing_spaces = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_remove_trailing_spaces(state)

    @on_conf_change(option='add_newline')
    def set_add_newline(self, state):
        self.add_newline = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_add_newline(state)

    @on_conf_change(option='always_remove_trailing_newlines')
    def set_remove_trailing_newlines(self, state):
        self.remove_trailing_newlines = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_remove_trailing_newlines(state)

    @on_conf_change(option='convert_eol_on_save')
    def set_convert_eol_on_save(self, state):
        """If `state` is `True`, saving files will convert line endings."""
        self.convert_eol_on_save = state

    @on_conf_change(option='convert_eol_on_save_to')
    def set_convert_eol_on_save_to(self, state):
        """`state` can be one of ('LF', 'CRLF', 'CR')"""
        self.convert_eol_on_save_to = state

    @on_conf_change(option='multicursor_support')
    def set_multicursor_support(self, state):
        """If `state` is `True`, multi-cursor editing is enabled."""
        self.multicursor_support = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_multi_cursor(state)

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

    # ---- Stacked widget management
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
        if instance == self or instance is None:
            self.tabs.setCurrentIndex(index)

    @on_conf_change(option='show_tab_bar')
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

    # ---- Context menu
    def __setup_menu(self):
        """Setup tab context menu before showing it"""
        self.menu.clear_actions()
        if self.data:
            given_actions = self._given_actions + [
                self.external_fileexp_action
            ]
            for given_action in given_actions:
                self.menu.add_action(
                    given_action, section=EditorStackMenuSections.GivenSection
                )
            # switcher and path section
            switcher_path_actions = [
                self.switcher_action,
                self.symbolfinder_action,
                self.copy_absolute_path_action,
                self.copy_relative_path_action
            ]
            for switcher_path_action in switcher_path_actions:
                self.menu.add_action(
                    switcher_path_action,
                    section=EditorStackMenuSections.SwitcherSection
                )
            # close and order section
            close_order_actions = [
                self.close_right,
                self.close_all_but_this,
                self.sort_tabs
            ]
            for close_order_action in close_order_actions:
                self.menu.add_action(
                    close_order_action,
                    section=EditorStackMenuSections.CloseOrderSection
                )
        else:
            actions = (self.new_action, self.open_action)
            self.setFocus()  # --> Editor.__get_focus_editortabwidget
            for menu_action in actions:
                self.menu.add_action(menu_action)

        for split_actions in self.__get_split_actions():
            self.menu.add_action(
                split_actions,
                section=EditorStackMenuSections.SplitCloseSection
            )

        for window_actions in self.__get_window_actions():
            self.menu.add_action(
                window_actions, section=EditorStackMenuSections.WindowSection
            )

        for new_window_and_close_action in (
            self.__get_new_window_and_close_actions()
        ):
            self.menu.add_action(
                new_window_and_close_action,
                section=EditorStackMenuSections.NewWindowCloseSection
            )

        self.menu.render()

    # ---- Hor/Ver splitting actions
    def __get_split_actions(self):
        self.versplit_action = self.create_action(
            EditorStackActions.SplitVertically,
            text=_("Split vertically"),
            icon=self.create_icon('versplit'),
            tip=_("Split vertically this editor window"),
            triggered=self.sig_split_vertically,
            context=Qt.WidgetShortcut,
            register_shortcut=True,
            register_action=False
        )
        self.horsplit_action = self.create_action(
            EditorStackActions.SplitHorizontally,
            text=_("Split horizontally"),
            icon=self.create_icon('horsplit'),
            tip=_("Split horizontally this editor window"),
            triggered=self.sig_split_horizontally,
            context=Qt.WidgetShortcut,
            register_shortcut=True,
            register_action=False
        )
        self.close_split_action = self.create_action(
            EditorStackActions.CloseSplitPanel,
            text=_("Close this panel"),
            icon=self.create_icon('close_panel'),
            triggered=self.close_split,
            context=Qt.WidgetShortcut,
            register_shortcut=True,
            register_action=False
        )
        self.close_split_action.setEnabled(self.is_closable)

        actions = [
            self.versplit_action,
            self.horsplit_action,
            self.close_split_action
        ]

        return actions

    # ---- Window actions
    def __get_window_actions(self):
        actions = []

        if self.new_window:
            window = self.window()
            close_window_action = self.create_action(
                EditorStackActions.CloseWindow,
                text=_("Close window"),
                icon=self.create_icon('close_pane'),
                triggered=window.close,
                register_action=False
            )

            if self.new_window_action:
                actions += [self.new_window_action]
            actions += [close_window_action]

        return actions

    # ---- New window and close/docking/undocking actions
    def __get_new_window_and_close_actions(self):
        actions = []
        if self.parent() is not None:
            main_widget = self.get_main_widget()
        else:
            main_widget = None

        if main_widget is not None:
            if main_widget.windowwidget is not None:
                actions += [main_widget.dock_action]
            else:
                if self.new_window_action:
                    actions += [self.new_window_action]
                actions += [
                    main_widget.lock_unlock_action,
                    main_widget.undock_action,
                    main_widget.close_action
                ]

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

    def get_current_project_path(self):
        if self.data:
            finfo = self.get_current_finfo()
            if finfo:
                return finfo.editor.current_project_path

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
        data_filenames = self.get_filenames()
        try:
            # Try finding without calling the slow realpath
            return data_filenames.index(filename)
        except ValueError:
            # See note about OSError on set_current_filename
            # Fixes spyder-ide/spyder#17685
            try:
                filename = fixpath(filename)
            except OSError:
                return None

            for index, editor_filename in enumerate(data_filenames):
                if filename == fixpath(editor_filename):
                    return index
            return None

    def set_current_filename(self, filename, focus=True):
        """Set current filename and return the associated editor instance."""
        # FileNotFoundError: This is necessary to catch an error on Windows
        # for files in a directory junction pointing to a symlink whose target
        # is on a network drive that is unavailable at startup.
        # Fixes spyder-ide/spyder#15714
        # OSError: This is necessary to catch an error on Windows when Spyder
        # was closed with a file in a shared folder on a different computer on
        # the network, and is started again when that folder is not available.
        # Fixes spyder-ide/spyder#17685
        try:
            index = self.has_filename(filename)
        except (FileNotFoundError, OSError):
            index = None

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
            direction = (end - start) // steps  # +1 for right, -1 for left

        data = self.data
        self.blockSignals(True)

        for i in range(start, end, direction):
            data[i], data[i + direction] = data[i + direction], data[i]

        self.blockSignals(False)
        self.refresh()

    # ---- Close file, tabwidget...
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

        can_close_file = self.get_main_widget().can_close_file(
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
            editor = finfo.editor
            editor.notify_close()
            editor.setParent(None)
            editor.completion_widget.setParent(None)
            # TODO: Check move of this logic to be part of SpyderMenu itself/be
            # able to call a method to do this unregistration
            editor.menu.MENUS.remove((editor, None, editor.menu))
            editor.menu.setParent(None)
            editor.readonly_menu.MENUS.remove(
                (editor, None, editor.readonly_menu)
            )
            editor.readonly_menu.setParent(None)

            # We pass self object ID as a QString, because otherwise it would
            # depend on the platform: long for 64bit, int for 32bit. Replacing
            # by long all the time is not working on some 32bit platforms.
            # See spyder-ide/spyder#1094 and spyder-ide/spyder#1098.
            self.sig_close_file.emit(str(id(self)), filename)
            self.sig_codeeditor_deleted.emit(editor)

            self.opened_files_list_changed.emit()
            self.sig_update_code_analysis_actions.emit()
            self.refresh_file_dependent_actions.emit()
            self.update_plugin_title.emit()
            if new_index is not None:
                if index < new_index:
                    new_index -= 1
                self.set_stack_index(new_index)
            # Give focus to the previous editor in the stack
            editor = self.get_current_editor()
            if editor:
                # This is necessary to avoid a segfault when closing several
                # files that were removed outside Spyder one after the other.
                # Fixes spyder-ide/spyder#18838
                QApplication.processEvents()

                # This allows to close files that were removed outside Spyder
                # one after the other without refocusing each one.
                self.__file_status_flag = False

                editor.setFocus()

            self.add_last_closed_file(finfo.filename)

            if finfo.filename in self.autosave.file_hashes:
                del self.autosave.file_hashes[finfo.filename]

        if self.get_stack_count() == 0 and self.create_new_file_if_empty:
            self.sig_new_file[()].emit()
            self.update_fname_label()
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
        try:
            for index in range(self.get_stack_count()):
                editor = self.tabs.widget(index)
                if editor.language.lower() == language:
                    editor.stop_completion_services()
        except RuntimeError:
            pass

    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass

    def close_all_right(self):
        """ Close all files opened to the right """
        num = self.get_stack_index()
        n = self.get_stack_count()
        for __ in range(num, n - 1):
            self.close_file(num + 1)

    def close_all_but_this(self):
        """Close all files but the current one"""
        self.close_all_right()
        for __ in range(0, self.get_stack_count() - 1):
            self.close_file(0)

    def sort_file_tabs_alphabetically(self):
        """Sort open tabs alphabetically."""
        while self.sorted() is False:
            for i in range(0, self.tabs.tabBar().count()):
                if (self.tabs.tabBar().tabText(i) >
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

    # ---- Save
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
        yes_all = no_all = False
        for index in indexes:
            self.set_stack_index(index)

            # Prevent error when trying to remove several unsaved files from
            # Projects or Files.
            # Fixes spyder-ide/spyder#20998
            try:
                finfo = self.data[index]
            except IndexError:
                return False

            if finfo.filename == self.tempfile_path or yes_all:
                if not self.save(index):
                    return False
            elif no_all:
                self.autosave.remove_autosave_file(finfo)
            elif (
                finfo.editor.document().isModified()
                and self.save_dialog_on_tests
            ):
                if unsaved_nb > 1:
                    buttons |= QMessageBox.YesToAll | QMessageBox.NoToAll

                self.msgbox = QMessageBox(
                    QMessageBox.Question,
                    self.title,
                    _("<b>%s</b> has been modified."
                      "<br><br>Do you want to save changes?"
                      ) % osp.basename(finfo.filename),
                    buttons,
                    parent=self
                )

                self.msgbox.button(QMessageBox.Yes).setText(_("Save"))
                self.msgbox.button(QMessageBox.No).setText(_("Discard"))
                yta = self.msgbox.button(QMessageBox.YesToAll)
                nta = self.msgbox.button(QMessageBox.NoToAll)

                if yta:
                    yta.setText(_("Save all"))
                if nta:
                    nta.setText(_("Discard all"))

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
        txt = to_text_string(fileinfo.editor.get_text_with_eol())
        return hash(txt)

    def _write_to_file(self, fileinfo, filename):
        """Low-level function for writing text of editor to file.

        Args:
            fileinfo: FileInfo object associated to editor to be saved
            filename: str with filename to save to

        This is a low-level function that only saves the text to file in the
        correct encoding without doing any error handling.
        """
        txt = to_text_string(fileinfo.editor.get_text_with_eol())
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

        # The following options (`always_remove_trailing_spaces`,
        # `remove_trailing_newlines` and `add_newline`) also depend on the
        # `format_on_save` value.
        # See spyder-ide/spyder#17716
        if self.always_remove_trailing_spaces and not self.format_on_save:
            self.remove_trailing_spaces(index)
        if self.remove_trailing_newlines and not self.format_on_save:
            self.trim_trailing_newlines(index)
        if self.add_newline and not self.format_on_save:
            self.add_newline_to_file(index)

        if self.convert_eol_on_save:
            # hack to account for the fact that the config file saves
            # CR/LF/CRLF while set_os_eol_chars wants the os.name value.
            osname_lookup = {'LF': 'posix', 'CRLF': 'nt', 'CR': 'mac'}
            osname = osname_lookup[self.convert_eol_on_save_to]
            self.set_os_eol_chars(osname=osname)

        try:
            if (
                self.format_on_save
                and finfo.editor.formatting_enabled
                and finfo.editor.is_python()
            ):
                # Wait for document autoformat in case it is a Python file
                # and then save.
                # Just trigger the autoformat for Python files.
                # See spyder-ide/spyder#19344

                # Waiting for the autoformat to complete is needed
                # when the file is going to be closed after saving.
                # See spyder-ide/spyder#17836
                format_eventloop = finfo.editor.format_eventloop
                format_timer = finfo.editor.format_timer
                format_timer.setSingleShot(True)
                format_timer.timeout.connect(format_eventloop.quit)

                finfo.editor.sig_stop_operation_in_progress.connect(
                    lambda: self._save_file(finfo))
                finfo.editor.sig_stop_operation_in_progress.connect(
                    format_timer.stop)
                finfo.editor.sig_stop_operation_in_progress.connect(
                    format_eventloop.quit)

                format_timer.start(10000)
                finfo.editor.format_document()
                format_eventloop.exec_()
            else:
                self._save_file(finfo)
            return True
        except EnvironmentError as error:
            self.msgbox = QMessageBox(
                QMessageBox.Critical,
                _("Save Error"),
                _("<b>Unable to save file '%s'</b>"
                  "<br><br>Error message:<br>%s"
                  ) % (osp.basename(finfo.filename), str(error)),
                parent=self
            )
            self.msgbox.exec_()
            return False

    def _save_file(self, finfo):
        index = self.data.index(finfo)
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
        self.analyze_script(index=index)

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
        if is_kde_desktop() and not is_conda_env(sys.prefix):
            filters = ''
            selectedfilter = ''
        else:
            filters = self.edit_filters
            selectedfilter = get_filter(self.edit_filetypes,
                                        osp.splitext(original_filename)[1])

        self.redirect_stdio.emit(False)
        filename, _selfilter = getsavefilename(
            self, _("Save file"),
            original_filename,
            filters=filters,
            selectedfilter=selectedfilter,
            options=QFileDialog.HideNameFilterDetails
        )
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
            self.file_renamed_in_data.emit(
                original_filename, filename, str(id(self)))

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
                      ) % (osp.basename(finfo.filename), str(error)),
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

    # ------ Update UI
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
        self.sig_codeeditor_changed.emit(editor)

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

        # Update highlighted matches and its total number when switching files.
        self.find_widget.highlight_matches()
        self.find_widget.update_matches()

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
        """
        Check if file has been changed in any way outside Spyder.

        Notes
        -----
        Possible ways are:
        * The file was removed, moved or renamed outside Spyder.
        * The file was modified outside Spyder.
        """
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
                _("The file <b>%s</b> is unavailable."
                  "<br><br>"
                  "It may have been removed, moved or renamed outside Spyder."
                  "<br><br>"
                  "Do you want to close it?") % name,
                QMessageBox.Yes | QMessageBox.No,
                self
            )

            answer = self.msgbox.exec_()
            if answer == QMessageBox.Yes:
                self.close_file(index, force=True)
            else:
                finfo.newly_created = True
                finfo.editor.document().setModified(True)
                self.modification_changed(index=index)
        else:
            # Else, testing if it has been modified elsewhere:
            lastm = QFileInfo(finfo.filename).lastModified()
            if str(lastm.toString()) != str(finfo.lastmodified.toString()):
                # Catch any error when trying to reload a file and close it if
                # that's the case to prevent users from destroying external
                # changes in Spyder.
                # Fixes spyder-ide/spyder#21248
                try:
                    if finfo.editor.document().isModified():
                        self.msgbox = QMessageBox(
                            QMessageBox.Question,
                            self.title,
                            _("The file <b>{}</b> has been modified outside "
                              "Spyder."
                              "<br><br>"
                              "Do you want to reload it and lose all your "
                              "changes?").format(name),
                            QMessageBox.Yes | QMessageBox.No,
                            self
                        )

                        answer = self.msgbox.exec_()
                        if answer == QMessageBox.Yes:
                            self.reload(index)
                        else:
                            finfo.lastmodified = lastm
                    else:
                        self.reload(index)
                except Exception:
                    self.msgbox = QMessageBox(
                        QMessageBox.Warning,
                        self.title,
                        _("The file <b>{}</b> has been modified outside "
                          "Spyder but it was not possible to reload it."
                          "<br><br>"
                          "Therefore, it will be closed.").format(name),
                        QMessageBox.Ok,
                        self
                    )
                    self.msgbox.exec_()
                    self.close_file(index, force=True)

        # Finally, resetting temporary flag:
        self.__file_status_flag = False

    def __modify_stack_title(self):
        for index, finfo in enumerate(self.data):
            state = finfo.editor.document().isModified()
            self.set_stack_title(index, state)

    def refresh(self, index=None):
        """Refresh tabwidget"""
        logger.debug("Refresh EditorStack")

        if index is None:
            index = self.get_stack_index()

        # Set current editor
        if self.get_stack_count():
            index = self.get_stack_index()
            finfo = self.data[index]
            editor = finfo.editor
            editor.setFocus()
            self._refresh_outlineexplorer(index, update=False)
            self.sig_update_code_analysis_actions.emit()
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

        # Get index
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

    # ---- Load, reload
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

        # XXX CodeEditor-only: re-scan the whole text to rebuild outline
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
                _("All changes to file <b>%s</b> will be lost.<br>"
                  "Do you want to revert it from disk?"
                  ) % osp.basename(filename),
                QMessageBox.Yes | QMessageBox.No,
                self
            )

            answer = self.msgbox.exec_()
            if answer != QMessageBox.Yes:
                return

        # This is necessary to catch an error when trying to revert the
        # contents of files not saved on disk (e.g. untitled ones).
        # Fixes spyder-ide/spyder#20284
        try:
            self.reload(index)
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                _("Error"),
                _("File <b>%s</b> is not saved on disk, so it can't be "
                  "reverted.") % osp.basename(filename),
                QMessageBox.Ok
            )

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
        finfo.todo_results_changed.connect(self.todo_results_changed)
        finfo.edit_goto.connect(lambda fname, lineno, name:
                                self.edit_goto.emit(fname, lineno, name))
        finfo.sig_save_bookmarks.connect(lambda s1, s2:
                                         self.sig_save_bookmarks.emit(s1, s2))
        editor.sig_new_file.connect(self.sig_new_file)
        editor.sig_process_code_analysis.connect(
            self.sig_update_code_analysis_actions)
        editor.sig_refresh_formatting.connect(self.sig_refresh_formatting)
        editor.sig_save_requested.connect(self.save)
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
            format_on_save=self.format_on_save,
            multi_cursor_enabled=self.multicursor_support
        )

        if cloned_from is None:
            editor.set_text(txt)
            editor.document().setModified(False)
        finfo.text_changed_at.connect(
            lambda fname, positions:
            self.text_changed_at.emit(fname, positions))
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
        editor.zoom_in.connect(self.zoom_in)
        editor.zoom_out.connect(self.zoom_out)
        editor.zoom_reset.connect(self.zoom_reset)
        editor.sig_eol_chars_changed.connect(
            lambda eol_chars: self.refresh_eol_chars(eol_chars))
        editor.sig_next_cursor.connect(self.sig_next_cursor)
        editor.sig_prev_cursor.connect(self.sig_prev_cursor)

        self.find_widget.set_editor(editor)

        self.refresh_file_dependent_actions.emit()
        self.modification_changed(index=self.data.index(finfo))

        # To update the outline explorer.
        editor.oe_proxy = OutlineExplorerProxyEditor(editor, editor.filename)
        if self.outlineexplorer is not None:
            self.outlineexplorer.register_editor(editor.oe_proxy)

        if cloned_from is not None:
            # Connect necessary signals from the original editor so that
            # symbols for the clon are updated as expected.
            cloned_from.oe_proxy.sig_outline_explorer_data_changed.connect(
                editor.oe_proxy.update_outline_info)
            cloned_from.oe_proxy.sig_outline_explorer_data_changed.connect(
                editor._update_classfuncdropdown)
            cloned_from.oe_proxy.sig_start_outline_spinner.connect(
                editor.oe_proxy.emit_request_in_progress)

            # This ensures that symbols will be requested and its info saved
            # for the clon.
            cloned_from.document_did_change()

        # Needs to reset the highlighting on startup in case the PygmentsSH
        # is in use
        editor.run_pygments_highlighter()
        options = {
            'language': editor.language,
            'filename': editor.filename,
            'codeeditor': editor
        }
        self.sig_open_file.emit(options)
        self.sig_codeeditor_created.emit(editor)
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
        Load filename, create an editor instance and return it.

        This also sets the hash of the loaded file in the autosave component.
        """
        filename = osp.abspath(to_text_string(filename))

        if processevents:
            self.starting_long_process.emit(_("Loading %s...") % filename)

        # This is necessary to avoid a crash at startup when trying to restore
        # files from the previous session.
        # Fixes spyder-ide/spyder#20670
        try:
            # Read file contents
            text, enc = encoding.read(filename)
        except Exception:
            return

        # Associate hash of file's text with its name for autosave
        self.autosave.file_hashes[filename] = hash(text)

        # Create editor
        finfo = self.create_new_editor(filename, enc, text, set_current,
                                       add_where=add_where)
        index = self.data.index(finfo)

        if processevents:
            self.ending_long_process.emit("")

        # Fix mixed EOLs
        if (
            self.isVisible() and self.checkeolchars_enabled
            and sourcecode.has_mixed_eol_chars(text)
        ):
            name = osp.basename(filename)
            self.msgbox = QMessageBox(
                QMessageBox.Warning,
                self.title,
                _("<b>%s</b> contains mixed end-of-line characters.<br>"
                  "Spyder will fix this automatically.") % name,
                QMessageBox.Ok,
                self
            )
            self.msgbox.exec_()
            self.set_os_eol_chars(index)

        # Analyze file for TODOs, FIXMEs, etc
        self.is_analysis_done = False
        self.analyze_script(index)

        # Set timeout to sync symbols and folding
        finfo.editor.set_sync_symbols_and_folding_timeout()

        # Unhighlight and rehighlight current line to prevent a visual glitch
        # when opening files.
        # Fixes spyder-ide/spyder#20033
        finfo.editor.unhighlight_current_line()
        if self.highlight_current_line_enabled:
            finfo.editor.highlight_current_line()

        return finfo

    def set_os_eol_chars(self, index=None, osname=None):
        """
        Sets the EOL character(s) based on the operating system.

        If `osname` is None, then the default line endings for the current
        operating system will be used.

        `osname` can be one of: 'posix', 'nt', 'mac'.
        """
        if osname is None:
            if os.name == 'nt':
                osname = 'nt'
            elif sys.platform == 'darwin':
                osname = 'mac'
            else:
                osname = 'posix'

        if index is None:
            index = self.get_stack_index()

        finfo = self.data[index]
        eol_chars = sourcecode.get_eol_chars_from_os_name(osname)
        logger.debug(f"Set OS eol chars {eol_chars} for file {finfo.filename}")
        finfo.editor.set_eol_chars(eol_chars=eol_chars)
        finfo.editor.document().setModified(True)

    def remove_trailing_spaces(self, index=None):
        """Remove trailing spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        logger.debug(f"Remove trailing spaces for file {finfo.filename}")
        finfo.editor.trim_trailing_spaces()

    def trim_trailing_newlines(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        logger.debug(f"Trim trailing new lines for file {finfo.filename}")
        finfo.editor.trim_trailing_newlines()

    def add_newline_to_file(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        logger.debug(f"Add new line to file {finfo.filename}")
        finfo.editor.add_newline_to_file()

    def fix_indentation(self, index=None):
        """Replace tab characters by spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        logger.debug(f"Fix indentation for file {finfo.filename}")
        finfo.editor.fix_indentation()

    def format_document_or_selection(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        logger.debug(f"Run formatting in file {finfo.filename}")
        finfo.editor.format_document_or_range()

    # ---- Run
    def _get_lines_cursor(self, direction):
        """ Select and return all lines from cursor in given direction"""
        editor = self.get_current_editor()
        finfo = self.get_current_finfo()
        enc = finfo.encoding
        cursor = editor.textCursor()

        if direction == 'up':
            # Select everything from the beginning of the file up to the
            # current line
            cursor.movePosition(QTextCursor.EndOfLine)
            cursor.movePosition(QTextCursor.Start, QTextCursor.KeepAnchor)
        elif direction == 'down':
            # Select everything from the current line to the end of the file
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)

        selection = editor.get_selection_as_executable_code(cursor)
        if selection:
            code_text, off_pos, line_col_pos = selection
            return code_text.rstrip(), off_pos, line_col_pos, enc

    def get_to_current_line(self):
        """
        Get all lines from the beginning up to, but not including, current
        line.
        """
        return self._get_lines_cursor(direction='up')

    def get_from_current_line(self):
        """
        Get all lines from and including the current line to the end of
        the document.
        """
        return self._get_lines_cursor(direction='down')

    def get_selection(self):
        """
        Get selected text or current line in console.

        If some text is selected, then execute that text in console.

        If no text is selected, then execute current line, unless current line
        is empty. Then, advance cursor to next line. If cursor is on last line
        and that line is not empty, then add a new blank line and move the
        cursor there. If cursor is on last line and that line is empty, then do
        not move cursor.
        """
        editor = self.get_current_editor()
        encoding = self.get_current_finfo().encoding
        selection = editor.get_selection_as_executable_code()
        if selection:
            text, off_pos, line_col_pos = selection
            return text, off_pos, line_col_pos, encoding

        line_col_from, line_col_to = editor.get_current_line_bounds()
        line_off_from, line_off_to = editor.get_current_line_offsets()
        line = editor.get_current_line()
        text = line.lstrip()

        return (
            text, (line_off_from, line_off_to),
            (line_col_from, line_col_to),
            encoding
        )

    def advance_line(self):
        """Advance to the next line."""
        editor = self.get_current_editor()
        if (
            editor.is_cursor_on_last_line()
            and editor.get_current_line().strip()
        ):
            editor.append(editor.get_line_separator())

        editor.move_cursor_to_next('line', 'down')
        editor.merge_extra_cursors(True)

    def get_current_cell(self):
        """Get current cell attributes."""
        text, block, off_pos, line_col_pos = (
            self.get_current_editor().get_cell_as_executable_code())
        encoding = self.get_current_finfo().encoding
        name = cell_name(block)
        return text, off_pos, line_col_pos, name, encoding

    def advance_cell(self, reverse=False):
        """Advance to the next cell.

        reverse = True --> go to previous cell.
        """
        if not reverse:
            move_func = self.get_current_editor().go_to_next_cell
        else:
            move_func = self.get_current_editor().go_to_previous_cell

        move_func()

    def get_last_cell(self):
        """Run the previous cell again."""
        if self.last_cell_call is None:
            return
        filename, cell_name = self.last_cell_call
        index = self.has_filename(filename)
        if index is None:
            return
        editor = self.data[index].editor

        try:
            text, off_pos, col_pos = editor.get_cell_code_and_position(
                cell_name)
            encoding = self.get_current_finfo().encoding
        except RuntimeError:
            return

        return text, off_pos, col_pos, cell_name, encoding

    # ---- Drag and drop
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

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Main Widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
from datetime import datetime
import logging
import os
import os.path as osp
from pathlib import Path
import re
import sys
import time
from typing import Dict, Optional
import uuid

# Third party imports
from qtpy.compat import from_qvariant, getopenfilenames, to_qvariant
from qtpy.QtCore import QByteArray, Qt, Signal, Slot, QDir
from qtpy.QtGui import QTextCursor
from qtpy.QtPrintSupport import QAbstractPrintDialog, QPrintDialog, QPrinter
from qtpy.QtWidgets import (QAction, QActionGroup, QApplication, QDialog,
                            QFileDialog, QInputDialog, QSplitter,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.plugins import Plugins
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.base import _, get_conf_path, running_under_pytest
from spyder.config.utils import (get_edit_filetypes, get_edit_filters,
                                 get_filter)
from spyder.plugins.editor.api.panel import Panel
from spyder.py3compat import qbytearray_to_str, to_text_string
from spyder.utils import encoding, programs, sourcecode
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import create_action
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.findreplace import FindReplace
from spyder.plugins.editor.api.run import (
    EditorRunConfiguration, FileRun, SelectionRun, CellRun,
    SelectionContextModificator, ExtraAction)
from spyder.plugins.editor.utils.autosave import AutosaveForPlugin
from spyder.plugins.editor.utils.switcher_manager import EditorSwitcherManager
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.widgets.editorstack import EditorStack
from spyder.plugins.editor.widgets.splitter import EditorSplitter
from spyder.plugins.editor.widgets.window import EditorMainWindow
from spyder.plugins.editor.utils.bookmarks import (load_bookmarks,
                                                   update_bookmarks)
from spyder.plugins.editor.widgets.status import (CursorPositionStatus,
                                                  EncodingStatus, EOLStatus,
                                                  ReadWriteStatus, VCSStatus)
from spyder.plugins.run.api import (
    RunContext, RunConfigurationMetadata, RunConfiguration,
    SupportedExtensionContexts, ExtendedContext)
from spyder.widgets.mixins import BaseEditMixin
from spyder.widgets.printer import SpyderPrinter, SpyderPrintPreviewDialog
from spyder.widgets.simplecodeeditor import SimpleCodeEditor


logger = logging.getLogger(__name__)


class EditorWidgetActions:
    # File operations
    NewFile = "New file"
    OpenLastClosed = "Open last closed"
    OpenFile = "Open file"
    RevertFileFromDisk = "Revert file from disk"
    SaveFile = "Save file"
    SaveAll = "Save all"
    SaveAs = "Save As"
    SaveCopyAs = "save_copy_as_action"
    PrintPreview = "print_preview_action"
    Print = "print_action"
    CloseFile = "Close current file"
    CloseAll = "Close all"
    MaxRecentFiles = "max_recent_files_action"
    ClearRecentFiles = "clear_recent_files_action"

    # Navigation
    GoToNextFile = "Go to next file"
    GoToPreviousFile = "Go to previous file"

    # Find/Search operations
    FindText = "Find text"
    FindNext = "Find next"
    FindPrevious = "Find previous"
    ReplaceText = "Replace text"

    # Source code operations
    ShowTodoList = "show_todo_list_action"
    ShowCodeAnalysisList = "show_code_analaysis_action"
    GoToPreviousWarning = "Previous warning"
    GoToNextWarning = "Next warning"
    GoToLastEditLocation = "Last edit location"
    GoToPreviousCursorPosition = "Previous cursor position"
    GoToNextCursorPosition = "Next cursor position"
    WinEOL = "win_eol_action"
    LinuxEOL = "linux_eol_action"
    MacEOL = "mac_eol_action"
    RemoveTrailingSpaces = "remove_trailing_spaces_action"
    FormatCode = "autoformating"
    FixIndentation = "fix_indentation_action"

    # Checkable operations
    ShowBlanks = "blank_spaces_action"
    ScrollPastEnd = "scroll_past_end_action"
    ShowIndentGuides = "show_indent_guides_action"
    ShowCodeFolding = "show_code_folding_action"
    ShowClassFuncDropdown = "show_class_func_dropdown_action"
    ShowCodeStyleWarnings = "pycodestyle_action"
    ShowDoctringWarnings = "pydocstyle_action"
    UnderlineErrors = "underline_errors_action"

    # Stack menu
    GoToLine = "Go to line"
    SetWorkingDirectory = "set_working_directory_action"

    # Edit operations
    NewCell = "create_new_cell"
    ToggleComment = "Toggle comment"
    Blockcomment = "Blockcomment"
    Unblockcomment = "Unblockcomment"

    Indent = "indent_action"
    Unindent = "unindent_action"
    TransformToUppercase = "transform to uppercase"
    TransformToLowercase = "transform to lowercase"

    Undo = "Undo"
    Redo = "Redo"
    Copy = "Copy"
    Cut = "Cut"
    Paste = "Paste"
    SelectAll = "Select All"


class EditorWidgetMenus:

    TodoList = "todo_list_menu"
    WarningErrorList = "warning_error_list_menu"
    EOL = "eol_menu"
    RecentFiles = "recent_files_menu"


class EditorMainWidget(PluginMainWidget):
    """
    Multi-file Editor widget
    """
    TEMPFILE_PATH = get_conf_path('temp.py')
    TEMPLATE_PATH = get_conf_path('template.py')

    sig_dir_opened = Signal(str)
    """
    This signal is emitted when the editor changes the current directory.

    Parameters
    ----------
    new_working_directory: str
        The new working directory path.

    Notes
    -----
    This option is available on the options menu of the editor plugin
    """

    sig_file_opened_closed_or_updated = Signal(str, str)
    """
    This signal is emitted when a file is opened, closed or updated,
    including switching among files.

    Parameters
    ----------
    filename: str
        Name of the file that was opened, closed or updated.
    language: str
        Name of the programming language of the file that was opened,
        closed or updated.
    """

    # Managing visual feedback when processing things
    starting_long_process = Signal(str)
    ending_long_process = Signal(str)

    # This signal is fired for any focus change among all editor stacks
    sig_editor_focus_changed = Signal()

    # ---- Run related signals
    sig_editor_focus_changed_uuid = Signal(str)
    sig_register_run_configuration_provider_requested = Signal(list)
    sig_deregister_run_configuration_provider_requested = Signal(list)

    # ---- Completions related signals
    sig_after_configuration_update_requested = Signal(list)

    # ---- Other signals
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

    sig_open_files_finished = Signal()
    """
    This signal is emitted when the editor finished to open files.
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

    sig_switch_to_plugin_requested = Signal()
    """
    This signal will request to change the focus to the plugin.
    """

    def __init__(self, name, plugin, parent, ignore_last_opened_files=False):
        super().__init__(name, plugin, parent)

        self._font = None
        self.__set_eol_chars = True

        # Creating template if it doesn't already exist
        if not osp.isfile(self.TEMPLATE_PATH):
            if os.name == "nt":
                shebang = []
            else:
                shebang = ['#!/usr/bin/env python3']
            header = shebang + [
                '# -*- coding: utf-8 -*-',
                '"""', 'Created on %(date)s', '',
                '@author: %(username)s', '"""', '', '']
            try:
                encoding.write(os.linesep.join(header), self.TEMPLATE_PATH,
                               'utf-8')
            except EnvironmentError:
                pass

        self.pending_run_files = set({})
        self.run_configurations_per_origin = {}
        self.supported_run_configurations = {}

        self.file_per_id = {}
        self.id_per_file = {}
        self.metadata_per_id: Dict[str, RunConfigurationMetadata] = {}

        # TODO: Is there any other way to do this. See `setup_other_windows`
        self.outline_plugin = None
        self.outlineexplorer = None
        self.switcher_manager = None
        self.active_project_path = None

        self.file_dependent_actions = []
        self.pythonfile_dependent_actions = []
        self.stack_menu_actions = None
        self.checkable_actions = {}

        self.__first_open_files_setup = True
        self.editorstacks = []
        self.last_focused_editorstack = {}
        self.editorwindows = []
        self.editorwindows_to_be_created = []

        # Configuration dialog size
        self.dialog_size = None

        self.vcs_status = VCSStatus(self)
        self.cursorpos_status = CursorPositionStatus(self)
        self.encoding_status = EncodingStatus(self)
        self.eol_status = EOLStatus(self)
        self.readwrite_status = ReadWriteStatus(self)

        self.last_edit_cursor_pos = None
        self.cursor_undo_history = []
        self.cursor_redo_history = []
        self.__ignore_cursor_history = True

        # Completions setup
        self.completion_capabilities = {}

        # Find widget
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()

        # Start autosave component
        # (needs to be done before EditorSplitter)
        self.autosave = AutosaveForPlugin(self)
        self.autosave.try_recover_from_autosave()

        # Multiply by 1000 to convert seconds to milliseconds
        self.autosave.interval = self.get_conf('autosave_interval') * 1000
        self.autosave.enabled = self.get_conf('autosave_enabled')

        # SimpleCodeEditor instance used to print file contents
        self._print_editor = self._create_print_editor()
        self._print_editor.hide()

        # To save run extensions
        self.supported_run_extensions = []

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Editor')

    def get_focus_widget(self):
        """
        Return the widget to give focus to.

        This happens when plugin's dockwidget is raised on top-level.
        """
        return self.get_current_editor()

    def setup(self):
        # ---- File operations ----
        self.new_action = self.create_action(
            EditorWidgetActions.NewFile,
            text=_("&New file..."),
            icon=self.create_icon('filenew'),
            tip=_("New file"),
            triggered=self.new,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.open_last_closed_action = self.create_action(
            EditorWidgetActions.OpenLastClosed,
            text=_("O&pen last closed"),
            tip=_("Open last closed"),
            triggered=self.open_last_closed,
            register_shortcut=True
        )
        self.open_action = self.create_action(
            EditorWidgetActions.OpenFile,
            text=_("&Open..."),
            icon=self.create_icon('fileopen'),
            tip=_("Open file"),
            triggered=self.load,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.revert_action = self.create_action(
            EditorWidgetActions.RevertFileFromDisk,
            text=_("&Revert"),
            icon=self.create_icon('revert'),
            tip=_("Revert file from disk"),
            triggered=self.revert
        )
        self.save_action = self.create_action(
            EditorWidgetActions.SaveFile,
            text=_("&Save"),
            icon=self.create_icon('filesave'),
            tip=_("Save file"),
            triggered=self.save,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.save_all_action = self.create_action(
            EditorWidgetActions.SaveAll,
            text=_("Sav&e all"),
            icon=self.create_icon('save_all'),
            tip=_("Save all files"),
            triggered=self.save_all,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.save_as_action = self.create_action(
            EditorWidgetActions.SaveAs,
            text=_("Save &as..."),
            icon=self.create_icon('filesaveas'),
            tip=_("Save current file as..."),
            triggered=self.save_as,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.save_copy_as_action = self.create_action(
            EditorWidgetActions.SaveCopyAs,
            text=_("Save copy as..."),
            icon=self.create_icon('filesaveas'),
            tip=_("Save copy of current file as..."),
            triggered=self.save_copy_as
        )
        self.print_preview_action = self.create_action(
            EditorWidgetActions.PrintPreview,
            text=_("Print preview..."),
            tip=_("Print preview..."),
            triggered=self.print_preview
        )
        self.print_action = self.create_action(
            EditorWidgetActions.Print,
            text=_("&Print..."),
            icon=self.create_icon('print'),
            tip=_("Print current file..."),
            triggered=self.print_file
        )
        self.close_file_action = self.create_action(
            EditorWidgetActions.CloseFile,
            text=_("&Close"),
            icon=self.create_icon('fileclose'),
            tip=_("Close current file"),
            triggered=self.close_file
        )
        self.close_all_action = self.create_action(
            EditorWidgetActions.CloseAll,
            text=_("C&lose all"),
            icon=ima.icon('filecloseall'),
            tip=_("Close all opened files"),
            triggered=self.close_all_files,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.recent_file_menu = self.create_menu(
            EditorWidgetMenus.RecentFiles,
            title=_("Open &recent")
        )
        self.recent_file_menu.aboutToShow.connect(self.update_recent_file_menu)
        self.max_recent_action = self.create_action(
            EditorWidgetActions.MaxRecentFiles,
            text=_("Maximum number of recent files..."),
            triggered=self.change_max_recent_files
        )
        self.clear_recent_action = self.create_action(
            EditorWidgetActions.ClearRecentFiles,
            text=_("Clear this list"), tip=_("Clear recent files list"),
            triggered=self.clear_recent_files
        )
        self.workdir_action = self.create_action(
            EditorWidgetActions.SetWorkingDirectory,
            text=_("Set console working directory"),
            icon=self.create_icon('DirOpenIcon'),
            tip=_("Set current console (and file explorer) working "
                  "directory to current script directory"),
            triggered=self.__set_workdir
        )

        # Fixes spyder-ide/spyder#6055.
        # See: https://bugreports.qt.io/browse/QTBUG-8596
        if sys.platform == 'darwin':
            self.go_to_next_file_action = self.create_action(
                EditorWidgetActions.GoToNextFile,
                text=_("Go to next file"),
                triggered=self.go_to_next_file,
                register_shortcut=True
            )
            self.go_to_previous_file_action = self.create_action(
                EditorWidgetActions.GoToPreviousFile,
                text=_("Go to previous file"),
                triggered=self.go_to_previous_file,
                register_shortcut=True
            )

        # ---- Find/Search operations ----
        self.find_action = self.create_action(
            EditorWidgetActions.FindText,
            text=_("&Find text"),
            icon=self.create_icon('find'),
            tip=_("Find text"),
            triggered=self.find,
            context=Qt.WidgetShortcut,
            shortcut_context="find_replace",
        )
        self.find_next_action = self.create_action(
            EditorWidgetActions.FindNext,
            text=_("Find &next"),
            icon=self.create_icon('findnext'),
            triggered=self.find_next,
            context=Qt.WidgetShortcut,
            shortcut_context="find_replace",
        )
        self.find_previous_action = self.create_action(
            EditorWidgetActions.FindPrevious,
            text=_("Find &previous"),
            icon=ima.icon('findprevious'),
            triggered=self.find_previous,
            context=Qt.WidgetShortcut,
            shortcut_context="find_replace",
        )
        self.replace_action = self.create_action(
            EditorWidgetActions.ReplaceText,
            text=_("&Replace text"),
            icon=ima.icon('replace'),
            tip=_("Replace text"),
            triggered=self.replace,
            context=Qt.WidgetShortcut,
            shortcut_context="find_replace",
        )
        self.gotoline_action = self.create_action(
            EditorWidgetActions.GoToLine,
            text=_("Go to line..."),
            icon=self.create_icon('gotoline'),
            triggered=self.go_to_line,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )

        self.search_menu_actions = [
            self.find_action,
            self.find_next_action,
            self.find_previous_action,
            self.replace_action,
            self.gotoline_action
        ]

        # ---- Source code operations ----
        # Checkable actions
        self.showblanks_action = self._create_checkable_action(
            EditorWidgetActions.ShowBlanks,
            _("Show blank spaces"),
            'blank_spaces',
            method='set_blanks_enabled'
        )
        self.scrollpastend_action = self._create_checkable_action(
            EditorWidgetActions.ScrollPastEnd,
            _("Scroll past the end"),
            'scroll_past_end',
            method='set_scrollpastend_enabled'
        )
        self.showindentguides_action = self._create_checkable_action(
            EditorWidgetActions.ShowIndentGuides,
            _("Show indent guides"),
            'indent_guides',
            method='set_indent_guides'
        )
        self.showcodefolding_action = self._create_checkable_action(
            EditorWidgetActions.ShowCodeFolding,
            _("Show code folding"),
            'code_folding',
            method='set_code_folding_enabled'
        )
        self.show_classfunc_dropdown_action = self._create_checkable_action(
            EditorWidgetActions.ShowClassFuncDropdown,
            _("Show selector for classes and functions"),
            'show_class_func_dropdown',
            method='set_classfunc_dropdown_visible'
        )
        self.show_codestyle_warnings_action = self._create_checkable_action(
            EditorWidgetActions.ShowCodeStyleWarnings,
            _("Show code style warnings"),
            'pycodestyle',
        )
        self.show_docstring_warnings_action = self._create_checkable_action(
            EditorWidgetActions.ShowDoctringWarnings,
            _("Show docstring style warnings"),
            'pydocstyle'
        )
        self.underline_errors = self._create_checkable_action(
            EditorWidgetActions.UnderlineErrors,
            _("Underline errors and warnings"),
            'underline_errors',
            method='set_underline_errors_enabled'
        )
        self.checkable_actions = {
            'blank_spaces': self.showblanks_action,
            'scroll_past_end': self.scrollpastend_action,
            'indent_guides': self.showindentguides_action,
            'code_folding': self.showcodefolding_action,
            'show_class_func_dropdown': self.show_classfunc_dropdown_action,
            # TODO: Should these actions be created from the completion plugin?
            'pycodestyle': self.show_codestyle_warnings_action,
            'pydocstyle': self.show_docstring_warnings_action,
            'underline_errors': self.underline_errors
        }

        # Todo menu
        self.todo_list_action = self.create_action(
            EditorWidgetActions.ShowTodoList,
            text=_("Show todo list"),
            icon=self.create_icon('todo_list'),
            tip=_("Show comments list (TODO/FIXME/XXX/HINT/TIP/@todo/"
                  "HACK/BUG/OPTIMIZE/!!!/???)"),
            triggered=lambda: None
        )
        self.todo_menu = self.create_menu(EditorWidgetMenus.TodoList)
        todo_menu_css = self.todo_menu.css
        todo_menu_css["QMenu"]["menu-scrollable"].setValue("1")
        self.todo_menu.setStyleSheet(todo_menu_css.toString())
        self.todo_list_action.setMenu(self.todo_menu)
        self.todo_menu.aboutToShow.connect(self.update_todo_menu)

        # Warnings menu
        self.warning_list_action = self.create_action(
            EditorWidgetActions.ShowCodeAnalysisList,
            text=_("Show warning/error list"),
            icon=self.create_icon('wng_list'),
            tip=_("Show code analysis warnings/errors"),
            triggered=lambda: None
        )
        self.warning_menu = self.create_menu(
            EditorWidgetMenus.WarningErrorList
        )
        warning_menu_css = self.todo_menu.css
        warning_menu_css["QMenu"]["menu-scrollable"].setValue("1")
        self.warning_menu.setStyleSheet(warning_menu_css.toString())
        self.warning_list_action.setMenu(self.warning_menu)
        self.warning_menu.aboutToShow.connect(self.update_warning_menu)

        self.previous_warning_action = self.create_action(
            EditorWidgetActions.GoToPreviousWarning,
            text=_("Previous warning/error"),
            icon=self.create_icon('prev_wng'),
            tip=_("Go to previous code analysis warning/error"),
            triggered=self.go_to_previous_warning,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.next_warning_action = self.create_action(
            EditorWidgetActions.GoToNextWarning,
            text=_("Next warning/error"),
            icon=self.create_icon('next_wng'),
            tip=_("Go to next code analysis warning/error"),
            triggered=self.go_to_next_warning,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )

        # Cursor actions
        self.previous_edit_cursor_action = self.create_action(
            EditorWidgetActions.GoToLastEditLocation,
            text=_("Last edit location"),
            icon=self.create_icon('last_edit_location'),
            tip=_("Go to last edit location"),
            triggered=self.go_to_last_edit_location,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.previous_cursor_action = self.create_action(
            EditorWidgetActions.GoToPreviousCursorPosition,
            text=_("Previous cursor position"),
            icon=self.create_icon('prev_cursor'),
            tip=_("Go to previous cursor position"),
            triggered=self.go_to_previous_cursor_position,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.next_cursor_action = self.create_action(
            EditorWidgetActions.GoToNextCursorPosition,
            text=_("Next cursor position"),
            icon=self.create_icon('next_cursor'),
            tip=_("Go to next cursor position"),
            triggered=self.go_to_next_cursor_position,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )

        # Eol menu
        self.win_eol_action = self.create_action(
            EditorWidgetActions.WinEOL,
            text=_("CRLF (Windows)"),
            toggled=lambda checked: self.toggle_eol_chars('nt', checked)
        )
        self.linux_eol_action = self.create_action(
            EditorWidgetActions.LinuxEOL,
            text=_("LF (Unix)"),
            toggled=lambda checked: self.toggle_eol_chars('posix', checked)
        )
        self.mac_eol_action = self.create_action(
            EditorWidgetActions.MacEOL,
            text=_("CR (macOS)"),
            toggled=lambda checked: self.toggle_eol_chars('mac', checked)
        )

        eol_action_group = QActionGroup(self)
        self.eol_menu = self.create_menu(
            EditorWidgetMenus.EOL,
            title=_("Convert end-of-line characters")
        )

        for eol_action in [
            self.win_eol_action,
            self.linux_eol_action,
            self.mac_eol_action,
        ]:
            eol_action_group.addAction(eol_action)
            self.add_item_to_menu(eol_action, self.eol_menu)

        # Format actions
        self.trailingspaces_action = self.create_action(
            EditorWidgetActions.RemoveTrailingSpaces,
            text=_("Remove trailing spaces"),
            triggered=self.remove_trailing_spaces
        )
        self.fixindentation_action = self.create_action(
            EditorWidgetActions.FixIndentation,
            text=_("Fix indentation"),
            tip=_("Replace tab characters by space characters"),
            triggered=self.fix_indentation
        )
        formatter = self.get_conf(
            ('provider_configuration', 'lsp', 'values', 'formatting'),
            default='',
            section='completions'
        )
        self.formatting_action = self.create_action(
            EditorWidgetActions.FormatCode,
            text=_('Format file or selection with {0}').format(
                formatter.capitalize()
            ),
            context=Qt.WidgetShortcut,
            triggered=self.format_document_or_selection,
            register_shortcut=True
        )
        self.formatting_action.setEnabled(False)

        # ---- Edit operations ----
        self.create_new_cell = self.create_action(
            EditorWidgetActions.NewCell,
            text=_("Create new cell"),
            icon=self.create_icon('new_cell'),
            tip=_("Create new cell at the current line"),
            triggered=self.create_cell,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.toggle_comment_action = self.create_action(
            EditorWidgetActions.ToggleComment,
            text=_("Comment")+"/"+_("Uncomment"),
            icon=self.create_icon('comment'),
            tip=_("Comment current line or selection"),
            triggered=self.toggle_comment,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.blockcomment_action = self.create_action(
            EditorWidgetActions.Blockcomment,
            text=_("Add &block comment"),
            tip=_("Add block comment around current line or selection"),
            triggered=self.blockcomment,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.unblockcomment_action = self.create_action(
            EditorWidgetActions.Unblockcomment,
            text=_("R&emove block comment"),
            tip=_("Remove comment block around current line or selection"),
            triggered=self.unblockcomment,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )

        # ---------------------------------------------------------------------
        # The following action shortcuts are hard-coded in CodeEditor
        # keyPressEvent handler (the shortcut is here only to inform user):
        # (context=Qt.WidgetShortcut -> disable shortcut for other widgets)
        self.indent_action = self.create_action(
            EditorWidgetActions.Indent,
            text=_("Indent"),
            icon=self.create_icon('indent'),
            tip=_("Indent current line or selection"),
            triggered=self.indent,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.unindent_action = self.create_action(
            EditorWidgetActions.Unindent,
            text=_("Unindent"),
            icon=self.create_icon('unindent'),
            tip=_("Unindent current line or selection"),
            triggered=self.unindent,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )

        # ---------------------------------------------------------------------
        self.text_uppercase_action = self.create_action(
            EditorWidgetActions.TransformToUppercase,
            text=_("Toggle Uppercase"),
            icon=self.create_icon('toggle_uppercase'),
            tip=_("Change to uppercase current line or selection"),
            triggered=self.text_uppercase,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        self.text_lowercase_action = self.create_action(
            EditorWidgetActions.TransformToLowercase,
            text=_("Toggle Lowercase"),
            icon=self.create_icon('toggle_lowercase'),
            tip=_("Change to lowercase current line or selection"),
            triggered=self.text_lowercase,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )

        self.edit_menu_actions = [
            self.toggle_comment_action,
            self.blockcomment_action,
            self.unblockcomment_action,
            self.indent_action,
            self.unindent_action,
            self.text_uppercase_action,
            self.text_lowercase_action
        ]

        self.undo_action = self._create_edit_action(
            EditorWidgetActions.Undo,
            _('Undo'),
            self.create_icon('undo')
        )
        self.redo_action = self._create_edit_action(
            EditorWidgetActions.Redo,
            _('Redo'),
            self.create_icon('redo')
        )
        self.copy_action = self._create_edit_action(
            EditorWidgetActions.Copy,
            _('Copy'),
            self.create_icon('editcopy')
        )
        self.cut_action = self._create_edit_action(
            EditorWidgetActions.Cut,
            _('Cut'),
            self.create_icon('editcut')
        )
        self.paste_action = self._create_edit_action(
            EditorWidgetActions.Paste,
            _('Paste'),
            self.create_icon('editpaste')
        )
        self.selectall_action = self._create_edit_action(
            EditorWidgetActions.SelectAll,
            _("Select All"),
            self.create_icon('selectall')
        )

        # ---- Dockwidget and file dependent actions lists ----
        self.pythonfile_dependent_actions = [
            self.blockcomment_action,
            self.unblockcomment_action,
        ]
        self.file_dependent_actions = (
            self.pythonfile_dependent_actions +
            [
                self.save_action,
                self.save_as_action,
                self.save_copy_as_action,
                self.print_preview_action,
                self.print_action,
                self.save_all_action,
                self.gotoline_action,
                self.workdir_action,
                self.close_file_action,
                self.close_all_action,
                self.toggle_comment_action,
                self.revert_action,
                self.indent_action,
                self.unindent_action
            ]
        )
        self.stack_menu_actions = [self.gotoline_action, self.workdir_action]

        # ---- Finish child widgets and actions setup ----
        layout = QVBoxLayout()

        # Tabbed editor widget + Find/Replace widget
        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setSpacing(0)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        self.editorsplitter = EditorSplitter(
            self,
            self,
            self.stack_menu_actions,
            first=True
        )
        editor_layout.addWidget(self.editorsplitter)
        editor_layout.addWidget(self.find_widget)
        editor_layout.addWidget(self._print_editor)

        # Splitter: editor widgets (see above) + outline explorer
        self.splitter = QSplitter(self)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(editor_widgets)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        self.setFocusPolicy(Qt.ClickFocus)

        # Editor's splitter state
        state = self.get_conf('splitter_state', None)
        if state is not None:
            self.splitter.restoreState(
                QByteArray().fromHex(str(state).encode('utf-8'))
            )

        self.recent_files = self.get_conf('recent_files', [])
        self.untitled_num = 0

        # Parameters of last file execution:
        self.__last_ic_exec = None  # internal console
        self.__last_ec_exec = None  # external console

        # File types and filters used by the Open dialog
        self.edit_filetypes = None
        self.edit_filters = None

        self.__ignore_cursor_history = False
        current_editor = self.get_current_editor()
        if current_editor is not None:
            filename = self.get_current_filename()
            cursors = tuple(current_editor.all_cursors)
            if not current_editor.multi_cursor_ignore_history:
                self.add_cursor_to_history(filename, cursors)
        self.update_cursorpos_actions()

        # TODO: How the maintoolbar should be handled?
        # Each editorstack has its own toolbar?
        self._main_toolbar.hide()
        self._corner_toolbar.hide()
        self._options_button.hide()

    def set_ancestor(self, ancestor):
        """
        Set ancestor of child widgets like the CompletionWidget.

        Needed to properly set position of the widget based on the correct
        parent/ancestor.

        See spyder-ide/spyder#11076
        """
        for editorstack in self.editorstacks:
            for finfo in editorstack.data:
                comp_widget = finfo.editor.completion_widget

                # This is necessary to catch an error when the plugin is
                # undocked and docked back, and (probably) a completion is
                # in progress.
                # Fixes spyder-ide/spyder#17486
                try:
                    comp_widget.setParent(ancestor)
                except RuntimeError:
                    pass

    def change_visibility(self, state, force_focus=None):
        """DockWidget visibility has changed"""
        super().change_visibility(state)
        try:
            if self.dockwidget is None:
                return
            if state:
                self.refresh()
            self.update_title()
        except RuntimeError:
            pass

    def update_actions(self):
        pass

    def on_close(self):
        state = self.splitter.saveState()
        self.set_conf('splitter_state', qbytearray_to_str(state))
        self.set_conf(
            'layout_settings',
            self.editorsplitter.get_layout_settings()
        )
        self.set_conf(
            'windows_layout_settings',
            [win.get_layout_settings() for win in self.editorwindows]
        )
        for window in self.editorwindows:
            window.close()
        self.set_conf('recent_files', self.recent_files)
        self.autosave.stop_autosave_timer()

    # ---- Private API
    # ------------------------------------------------------------------------
    def _get_mainwindow(self):
        return self._plugin.main

    def _get_color_scheme(self):
        return self._plugin.get_color_scheme()

    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        # Widget is now visible, we may center cursor on top level editor:
        try:
            self.get_current_editor().centerCursor()
        except AttributeError:
            pass

    # ---- Related to the Run plugin
    # -------------------------------------------------------------------------
    def update_run_focus_file(self):
        """
        Inform run plugin that the current editor with focus has changed.
        """
        filename = self.get_current_filename()
        file_id = self.id_per_file.get(filename, None)
        self.sig_editor_focus_changed_uuid.emit(file_id)

    def register_file_run_metadata(self, filename):
        """Register opened files with the Run plugin."""
        all_uuids = self.get_conf('file_uuids', default={})
        file_id = all_uuids.get(filename, str(uuid.uuid4()))
        all_uuids[filename] = file_id
        self.set_conf('file_uuids', all_uuids)

        metadata: RunConfigurationMetadata = {
            'name': filename,
            'source': self._plugin.NAME,
            'path': filename,
            'datetime': datetime.now(),
            'uuid': file_id,
            'context': {
                'name': 'File'
            },
            'input_extension': osp.splitext(filename)[1][1:]
        }

        self.file_per_id[file_id] = filename
        self.id_per_file[filename] = file_id
        self.metadata_per_id[file_id] = metadata
        self._plugin._register_run_configuration_metadata(metadata)

    def deregister_file_run_metadata(self, filename):
        """Unregister files with the Run plugin."""
        if filename not in self.id_per_file:
            return

        file_id = self.id_per_file.pop(filename)
        self.file_per_id.pop(file_id)
        self.metadata_per_id.pop(file_id)
        self._plugin._deregister_run_configuration_metadata(file_id)

    def change_register_file_run_metadata(self, old_filename, new_filename):
        """Change registered run metadata when renaming files."""
        run_selected_config = (
            self._plugin._get_currently_selected_run_configuration()
        )

        is_selected = (
            run_selected_config == self.id_per_file.get(old_filename, None)
        )

        self.deregister_file_run_metadata(old_filename)

        # Get file extension (without the dot)
        filename_ext = osp.splitext(new_filename)[1][1:]

        # Check if we can actually register the new file
        if (
            # This avoids to register new_filename twice, which can happen for
            # some rename operations.
            not self.id_per_file.get(new_filename)
            # Check if the new file extension is supported.
            # Fixes spyder-ide/spyder#22630
            and filename_ext in self.supported_run_configurations
        ):
            self.register_file_run_metadata(new_filename)

        if is_selected and self.id_per_file.get(new_filename):
            self._plugin._switch_focused_run_configuration(
                self.id_per_file[new_filename]
            )

    # ---- Related to the completions plugin
    # -------------------------------------------------------------------------
    @Slot(dict)
    def report_open_file(self, options):
        """Report that a file was opened to other plugins."""
        filename = options['filename']
        language = options['language']
        codeeditor = options['codeeditor']
        __, filename_ext = osp.splitext(filename)
        filename_ext = filename_ext[1:]

        able_to_run_file = False
        if filename_ext in self.supported_run_configurations:
            ext_contexts = self.supported_run_configurations[filename_ext]

            if (
                filename not in self.id_per_file
                and RunContext.File in ext_contexts
            ):
                self.register_file_run_metadata(filename)
                able_to_run_file = True

        if not able_to_run_file:
            self.pending_run_files |= {(filename, filename_ext)}

        status, fallback_only = self._plugin._register_file_completions(
            language.lower(), filename, codeeditor
        )

        if status:
            if language.lower() in self.completion_capabilities:
                # When this condition is True, it means there's a server
                # that can provide completion services for this file.
                codeeditor.register_completion_capabilities(
                    self.completion_capabilities[language.lower()])
                codeeditor.start_completion_services()
            elif fallback_only:
                # This is required to use fallback completions for files
                # without a language server.
                codeeditor.start_completion_services()
        else:
            if codeeditor.language == language.lower():
                logger.debug('Setting {0} completions off'.format(filename))
                codeeditor.completions_available = False

    @Slot(dict, str)
    def register_completion_capabilities(self, capabilities, language):
        """
        Register completion server capabilities in all editorstacks.

        Parameters
        ----------
        capabilities: dict
            Capabilities supported by a language server.
        language: str
            Programming language for the language server (it has to be
            in small caps).
        """
        logger.debug(
            'Completion server capabilities for {!s} are: {!r}'.format(
                language, capabilities)
        )

        # This is required to start workspace before completion
        # services when Spyder starts with an open project.
        # TODO: Find a better solution for it in the future!!
        # TODO: main_widget calling logic for the projects plugin
        self._plugin._start_project_workspace_services()

        self.completion_capabilities[language] = dict(capabilities)
        for editorstack in self.editorstacks:
            editorstack.register_completion_capabilities(
                capabilities, language)

        self.start_completion_services(language)

    def start_completion_services(self, language):
        """Notify all editorstacks about LSP server availability."""
        for editorstack in self.editorstacks:
            editorstack.start_completion_services(language)

    def stop_completion_services(self, language):
        """Notify all editorstacks about LSP server unavailability."""
        for editorstack in self.editorstacks:
            editorstack.stop_completion_services(language)

    def send_completion_request(self, language, request, params):
        logger.debug("Perform request {0} for: {1}".format(
            request, params['file']))
        # TODO: main_widget calling logic from the completions plugin
        self._plugin._send_completions_request(
            language, request, params
        )

    def refresh(self):
        """Refresh editor widgets"""
        editorstack = self.get_current_editorstack()
        editorstack.refresh()
        self.refresh_save_all_action()

    # ---- Update menus
    # -------------------------------------------------------------------------
    def _base_edit_actions_callback(self):
        """Callback for base edit actions of text based widgets."""
        widget = QApplication.focusWidget()
        action = self.sender()
        callback = from_qvariant(action.data(), to_text_string)

        if isinstance(widget, BaseEditMixin) and hasattr(widget, callback):
            getattr(widget, callback)()
        else:
            return

    def update_edit_menu(self):
        """
        Enable edition related actions only when the Editor has focus.

        Also enable actions in case the focused widget has editable properties.
        """
        # Disabling all actions to begin with
        for child in [
                self.undo_action, self.redo_action, self.copy_action,
                self.cut_action, self.paste_action, self.selectall_action
                ] + self.edit_menu_actions:
            child.setEnabled(False)

        possible_text_widget = QApplication.focusWidget()
        editor = self.get_current_editor()
        readwrite_editor = possible_text_widget == editor

        # We need the first validation to avoid a bug at startup. That probably
        # happens when the menu is tried to be rendered automatically in some
        # Linux distros.
        # Fixes spyder-ide/spyder#22432
        if editor is not None and readwrite_editor and not editor.isReadOnly():
            # Case where the current editor has the focus
            if not self.is_file_opened():
                return

            # Undo, redo
            self.undo_action.setEnabled(editor.document().isUndoAvailable())
            self.redo_action.setEnabled(editor.document().isRedoAvailable())

            # Editor only actions
            for action in self.edit_menu_actions:
                action.setEnabled(True)
            not_readonly = not editor.isReadOnly()
            has_selection = editor.has_selected_text()
        elif (isinstance(possible_text_widget, BaseEditMixin) and
              hasattr(possible_text_widget, "isReadOnly")):
            # Case when a text based widget has the focus.
            not_readonly = not possible_text_widget.isReadOnly()
            has_selection = possible_text_widget.has_selected_text()
        else:
            # Case when no text based widget has the focus.
            return

        # Copy, cut, paste, select all
        self.copy_action.setEnabled(has_selection)
        self.cut_action.setEnabled(has_selection and not_readonly)
        self.paste_action.setEnabled(not_readonly)
        self.selectall_action.setEnabled(True)

    def update_search_menu(self):
        """
        Enable search related actions only when the Editor has focus.
        """
        editor = self.get_current_editor()
        if editor:
            editor_focus = (
                self.find_widget.search_text.lineEdit().hasFocus() or
                editor.hasFocus()
            )
            for search_menu_action in self.search_menu_actions:
                action_enabled = editor_focus
                if search_menu_action == self.replace_action:
                    action_enabled = editor_focus and not editor.isReadOnly()
                search_menu_action.setEnabled(action_enabled)

    def update_font(self, font):
        """Update font from Preferences"""
        self._font = font
        color_scheme = self._get_color_scheme()
        for editorstack in self.editorstacks:
            editorstack.set_default_font(font, color_scheme)
            completion_size = self.get_conf('completion/size', section='main')
            for finfo in editorstack.data:
                comp_widget = finfo.editor.completion_widget
                comp_widget.setup_appearance(completion_size, font)

    def _create_edit_action(self, name, tr_text, icon):
        """
        Helper method to create edit actions.

        Parameters
        ----------
        name : str
            Text that will be used to identifiy the method associated with the
            action and set as action id.
        tr_text : str
            Text that the action will show. Usually it will be some
            translated text.
        icon : QIcon
            Icon that the action will have.

        Returns
        -------
        action : SpyderAction
            The created action.
        """
        nameseq = name.split(' ')
        method_name = nameseq[0].lower() + "".join(nameseq[1:])
        action = self.create_action(
            name,
            text=tr_text,
            icon=icon,
            triggered=self._base_edit_actions_callback,
            data=method_name,
            context=Qt.WidgetShortcut,
            register_shortcut=True
        )
        return action

    def _create_checkable_action(self, name, text, conf_name, method=''):
        """
        Helper function to create a checkable action.

        Parameters
        ----------
        name: str
            Name that will be used as action identifier.
        text: str
            Text to be displayed in the action.
        conf_name: str
            Configuration setting associated with the action.
        method: str, optional
            Name of EditorStack class that will be used to update the changes
            in each editorstack.
        """
        def toggle(checked):
            self.switch_to_plugin()
            self._toggle_checkable_action(checked, method, conf_name)

        action = self.create_action(name, text=text, toggled=toggle)
        action.blockSignals(True)

        if conf_name not in ['pycodestyle', 'pydocstyle']:
            action.setChecked(self.get_conf(conf_name))
        else:
            opt = self.get_conf(
                ('provider_configuration', 'lsp', 'values', conf_name),
                default=False,
                section='completions'
            )
            action.setChecked(opt)

        action.blockSignals(False)

        return action

    @Slot(bool, str, str)
    def _toggle_checkable_action(self, checked, method_name, conf_name):
        """
        Handle the toogle of a checkable action.

        Update editorstacks, PyLS and CONF.

        Args:
            checked (bool): State of the action.
            method_name (str): name of EditorStack class that will be used
                to update the changes in each editorstack.
            conf_name (str): configuration setting associated with the
                action.
        """
        if method_name:
            if self.editorstacks:
                for editorstack in self.editorstacks:
                    try:
                        method = getattr(editorstack, method_name)
                        method(checked)
                    except AttributeError as e:
                        logger.error(e, exc_info=True)
            self.set_conf(conf_name, checked)
        else:
            if conf_name in ('pycodestyle', 'pydocstyle'):
                self.set_conf(
                    ('provider_configuration', 'lsp', 'values', conf_name),
                    checked,
                    section='completions'
                )
            self.sig_after_configuration_update_requested.emit([])

    # ---- Focus tabwidget (private)
    def __get_focused_editorstack(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, EditorStack):
            return fwidget
        else:
            for editorstack in self.editorstacks:
                try:
                    if editorstack.isAncestorOf(fwidget):
                        return editorstack
                except RuntimeError:
                    pass

    # ---- For other plugins
    # -------------------------------------------------------------------------
    def set_outlineexplorer(self, outlineexplorer_widget):
        # TODO: Is there another way to do this?
        self.outlineexplorer = outlineexplorer_widget
        for editorstack in self.editorstacks:
            editorstack.set_outlineexplorer(self.outlineexplorer)

    def set_switcher(self, switcher):
        # TODO: Is there another way to do this?
        switcher_available = switcher is not None
        if switcher_available:
            self.switcher_manager = EditorSwitcherManager(
                self,
                switcher,
                self.get_current_editor,
                self.get_current_editorstack,
                section=self.get_title()
            )
        else:
            self.switcher_manager = None
        for editorstack in self.editorstacks:
            editorstack.update_switcher_actions(switcher_available)

    # ---- Focus tabwidget (public)
    # -------------------------------------------------------------------------
    def set_last_focused_editorstack(self, editorwindow, editorstack):
        self.last_focused_editorstack[editorwindow] = editorstack
        # very last editorstack
        self.last_focused_editorstack[None] = editorstack

    def get_last_focused_editorstack(self, editorwindow=None):
        return self.last_focused_editorstack[editorwindow]

    def remove_last_focused_editorstack(self, editorstack):
        for editorwindow, widget in list(
                self.last_focused_editorstack.items()):
            if widget is editorstack:
                self.last_focused_editorstack[editorwindow] = None

    def save_focused_editorstack(self):
        editorstack = self.__get_focused_editorstack()
        if editorstack is not None:
            for win in [self]+self.editorwindows:
                if win.isAncestorOf(editorstack):
                    self.set_last_focused_editorstack(win, editorstack)

    # ---- Handling editorstacks
    # -------------------------------------------------------------------------
    def register_editorstack(self, editorstack):
        logger.debug("Registering new EditorStack")
        self.editorstacks.append(editorstack)

        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            self.set_last_focused_editorstack(self, editorstack)
            editorstack.set_closable(len(self.editorstacks) > 1)
            if self.outlineexplorer is not None:
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
            editorstack.sig_editor_cursor_position_changed.connect(
                self.current_editor_cursor_changed)
            editorstack.sig_refresh_eol_chars.connect(
                self.eol_status.update_eol)
            editorstack.current_file_changed.connect(
                self.vcs_status.update_vcs)
            editorstack.file_saved.connect(
                self.vcs_status.update_vcs_state)

        editorstack.update_switcher_actions(self.switcher_manager is not None)
        editorstack.set_io_actions(self.new_action, self.open_action,
                                   self.save_action, self.revert_action)
        editorstack.set_tempfile_path(self.TEMPFILE_PATH)

        # *********************************************************************
        # Although the `EditorStack` observes all of the options below,
        # applying them when registring a new `EditorStack` instance is needed.
        # The options are notified only for the first `EditorStack` instance
        # created at startup. New instances, created for example when
        # using `Split vertically/horizontally`, require the logic
        # below to follow the current values in the configuration.
        settings = (
            ('set_todolist_enabled',                'todo_list'),
            ('set_blanks_enabled',                  'blank_spaces'),
            ('set_underline_errors_enabled',        'underline_errors'),
            ('set_scrollpastend_enabled',           'scroll_past_end'),
            ('set_linenumbers_enabled',             'line_numbers'),
            ('set_edgeline_enabled',                'edge_line'),
            ('set_indent_guides',                   'indent_guides'),
            ('set_code_folding_enabled',            'code_folding'),
            ('set_close_parentheses_enabled',       'close_parentheses'),
            ('set_close_quotes_enabled',            'close_quotes'),
            ('set_add_colons_enabled',              'add_colons'),
            ('set_auto_unindent_enabled',           'auto_unindent'),
            ('set_indent_chars',                    'indent_chars'),
            ('set_tab_stop_width_spaces',           'tab_stop_width_spaces'),
            ('set_wrap_enabled',                    'wrap'),
            ('set_tabmode_enabled',                 'tab_always_indent'),
            ('set_stripmode_enabled',               'strip_trailing_spaces_on_modify'),  # noqa
            ('set_intelligent_backspace_enabled',   'intelligent_backspace'),
            ('set_automatic_completions_enabled',   'automatic_completions'),
            ('set_automatic_completions_after_chars',
             'automatic_completions_after_chars'),
            ('set_completions_hint_enabled',        'completions_hint'),
            ('set_completions_hint_after_ms',
             'completions_hint_after_ms'),
            ('set_highlight_current_line_enabled',  'highlight_current_line'),
            ('set_highlight_current_cell_enabled',  'highlight_current_cell'),
            ('set_occurrence_highlighting_enabled', 'occurrence_highlighting'),  # noqa
            ('set_occurrence_highlighting_timeout', 'occurrence_highlighting/timeout'),  # noqa
            ('set_checkeolchars_enabled',           'check_eol_chars'),
            ('set_tabbar_visible',                  'show_tab_bar'),
            ('set_classfunc_dropdown_visible',      'show_class_func_dropdown'),  # noqa
            ('set_always_remove_trailing_spaces',   'always_remove_trailing_spaces'),  # noqa
            ('set_remove_trailing_newlines',        'always_remove_trailing_newlines'),  # noqa
            ('set_add_newline',                     'add_newline'),
            ('set_convert_eol_on_save',             'convert_eol_on_save'),
            ('set_convert_eol_on_save_to',          'convert_eol_on_save_to'),
            ('set_multicursor_support',             'multicursor_support'),
        )

        for method, setting in settings:
            getattr(editorstack, method)(self.get_conf(setting))

        editorstack.set_help_enabled(
            self.get_conf('connect/editor', section='help')
        )

        hover_hints = self.get_conf(
            ('provider_configuration', 'lsp', 'values', 'enable_hover_hints'),
            default=True,
            section='completions'
        )

        format_on_save = self.get_conf(
            ('provider_configuration', 'lsp', 'values', 'format_on_save'),
            default=False,
            section='completions'
        )

        edge_line_columns = self.get_conf(
            ('provider_configuration', 'lsp', 'values',
             'pycodestyle/max_line_length'),
            default=79,
            section='completions'
        )

        editorstack.set_hover_hints_enabled(hover_hints)
        editorstack.set_format_on_save(format_on_save)
        editorstack.set_edgeline_columns(edge_line_columns)
        # *********************************************************************

        color_scheme = self._get_color_scheme()
        editorstack.set_default_font(self._font, color_scheme)

        editorstack.starting_long_process.connect(self.starting_long_process)
        editorstack.ending_long_process.connect(self.ending_long_process)

        # Signals
        editorstack.redirect_stdio.connect(self.sig_redirect_stdio_requested)
        editorstack.update_plugin_title.connect(self.update_title)
        editorstack.editor_focus_changed.connect(self.save_focused_editorstack)
        editorstack.editor_focus_changed.connect(self.sig_editor_focus_changed)
        editorstack.editor_focus_changed.connect(self.update_run_focus_file)
        editorstack.zoom_in.connect(lambda: self.zoom(1))
        editorstack.zoom_out.connect(lambda: self.zoom(-1))
        editorstack.zoom_reset.connect(lambda: self.zoom(0))
        editorstack.sig_open_file.connect(self.report_open_file)
        editorstack.sig_new_file.connect(lambda s: self.new(text=s))
        editorstack.sig_new_file[()].connect(self.new)
        editorstack.sig_open_last_closed.connect(self.open_last_closed)
        editorstack.sig_close_file.connect(self.close_file_in_all_editorstacks)
        editorstack.sig_close_file.connect(self.remove_file_cursor_history)
        editorstack.file_saved.connect(self.file_saved_in_editorstack)
        editorstack.file_renamed_in_data.connect(self.renamed)
        editorstack.opened_files_list_changed.connect(
            self.opened_files_list_changed)
        editorstack.sig_go_to_definition.connect(
            lambda fname, line, col: self.load(
                fname, line, start_column=col))
        editorstack.sig_perform_completion_request.connect(
            self.send_completion_request)
        editorstack.todo_results_changed.connect(self.todo_results_changed)
        editorstack.sig_update_code_analysis_actions.connect(
            self.update_code_analysis_actions)
        editorstack.sig_update_code_analysis_actions.connect(
            self.update_todo_actions)
        editorstack.refresh_file_dependent_actions.connect(
            self.refresh_file_dependent_actions)
        editorstack.refresh_save_all_action.connect(
            self.refresh_save_all_action
        )
        editorstack.sig_refresh_eol_chars.connect(self.refresh_eol_chars)
        editorstack.sig_refresh_formatting.connect(self.refresh_formatting)
        editorstack.text_changed_at.connect(self.text_changed_at)
        editorstack.current_file_changed.connect(self.current_file_changed)
        editorstack.plugin_load.connect(self.load)
        editorstack.plugin_load[()].connect(self.load)
        editorstack.edit_goto.connect(self.load)
        editorstack.sig_save_as.connect(self.save_as)
        editorstack.sig_prev_edit_pos.connect(self.go_to_last_edit_location)
        editorstack.sig_prev_cursor.connect(
            self.go_to_previous_cursor_position
        )
        editorstack.sig_next_cursor.connect(self.go_to_next_cursor_position)
        editorstack.sig_prev_warning.connect(self.go_to_previous_warning)
        editorstack.sig_next_warning.connect(self.go_to_next_warning)
        editorstack.sig_save_bookmark.connect(self.save_bookmark)
        editorstack.sig_load_bookmark.connect(self.load_bookmark)
        editorstack.sig_save_bookmarks.connect(self.save_bookmarks)
        editorstack.sig_help_requested.connect(self.sig_help_requested)
        editorstack.sig_codeeditor_created.connect(self.sig_codeeditor_created)
        editorstack.sig_codeeditor_changed.connect(self.sig_codeeditor_changed)
        editorstack.sig_codeeditor_deleted.connect(self.sig_codeeditor_deleted)
        editorstack.sig_trigger_run_action.connect(self.trigger_run_action)
        editorstack.sig_trigger_debugger_action.connect(
            self.trigger_debugger_action
        )

        # Register editorstack's autosave component with plugin's autosave
        # component
        self.autosave.register_autosave_for_stack(editorstack.autosave)

    def unregister_editorstack(self, editorstack):
        """Removing editorstack only if it's not the last remaining"""
        logger.debug("Unregistering EditorStack")
        self.remove_last_focused_editorstack(editorstack)
        if len(self.editorstacks) > 1:
            index = self.editorstacks.index(editorstack)
            self.editorstacks.pop(index)
            self.find_widget.set_editor(self.get_current_editor())
            return True
        else:
            # editorstack was not removed!
            return False

    def clone_editorstack(self, editorstack):
        editorstack.clone_from(self.editorstacks[0])

    @Slot(str, str)
    def close_file_in_all_editorstacks(self, editorstack_id_str, filename):
        if filename in self.id_per_file:
            self.deregister_file_run_metadata(filename)
        else:
            _, filename_ext = osp.splitext(filename)
            filename_ext = filename_ext[1:]
            self.pending_run_files -= {(filename, filename_ext)}

        try:
            for editorstack in self.editorstacks:
                if str(id(editorstack)) != editorstack_id_str:
                    editorstack.blockSignals(True)
                    index = editorstack.get_index_from_filename(filename)
                    editorstack.close_file(index, force=True)
                    editorstack.blockSignals(False)
        except RuntimeError:
            pass

    @Slot(str, str, str)
    def file_saved_in_editorstack(self, editorstack_id_str,
                                  original_filename, filename):
        """A file was saved in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.file_saved_in_other_editorstack(original_filename,
                                                            filename)

    # ---- Handling editor windows
    # -------------------------------------------------------------------------
    def setup_other_windows(self, main, outline_plugin):
        """Setup toolbars and menus for 'New window' instances"""
        # Outline setup
        self.outline_plugin = outline_plugin

        # Create pending new windows:
        for layout_settings in self.editorwindows_to_be_created:
            win = self.create_new_window()
            win.set_layout_settings(layout_settings)

    def switch_to_plugin(self):
        """Deactivate shortcut when opening a new window."""
        if not self.editorwindows:
            self.sig_switch_to_plugin_requested.emit()

    def create_new_window(self):
        """Create a new editor window."""
        window = EditorMainWindow(
            self,
            self.stack_menu_actions,
            outline_plugin=self.outline_plugin
        )

        # Give a default size to new windows so they're shown with a nice size
        # regardless of the current one of this widget (we were using self.size
        # here before).
        window.resize(800, 800)
        window.show()

        window.editorwidget.editorsplitter.editorstack.new_window = True
        self.register_editorwindow(window)
        window.destroyed.connect(lambda: self.unregister_editorwindow(window))
        return window

    def register_editorwindow(self, window):
        """Register a new editor window."""
        logger.debug("Registering new window")
        self.editorwindows.append(window)

    def unregister_editorwindow(self, window):
        """Unregister editor window."""
        logger.debug("Unregistering window")
        idx = self.editorwindows.index(window)
        self.editorwindows[idx] = None
        self.editorwindows.pop(idx)

    # ---- Accessors
    # -------------------------------------------------------------------------
    def get_filenames(self):
        return [finfo.filename for finfo in self.editorstacks[0].data]

    def get_filename_index(self, filename):
        return self.editorstacks[0].has_filename(filename)

    def get_current_editorstack(self, editorwindow=None):
        if self.editorstacks is not None and len(self.editorstacks) > 0:
            if len(self.editorstacks) == 1:
                editorstack = self.editorstacks[0]
            else:
                editorstack = self.__get_focused_editorstack()
                if editorstack is None or editorwindow is not None:
                    editorstack = self.get_last_focused_editorstack(
                        editorwindow)
                    if editorstack is None:
                        editorstack = self.editorstacks[0]
            return editorstack

    def get_current_editor(self):
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            return editorstack.get_current_editor()

    def get_current_finfo(self):
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            return editorstack.get_current_finfo()

    def get_current_filename(self):
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            return editorstack.get_current_filename()

    def get_current_language(self):
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            return editorstack.get_current_language()

    def is_file_opened(self, filename=None):
        return self.editorstacks[0].is_file_opened(filename)

    def set_current_filename(self, filename, editorwindow=None, focus=True):
        """Set focus to *filename* if this file has been opened.

        Return the editor instance associated to *filename*.
        """
        editorstack = self.get_current_editorstack(editorwindow)
        return editorstack.set_current_filename(filename, focus)

    # ---- Refresh methods
    # -------------------------------------------------------------------------
    def refresh_file_dependent_actions(self):
        """
        Enable/disable file dependent actions (only if dockwidget is visible).
        """
        if self.dockwidget and self.dockwidget.isVisible():
            enable = self.get_current_editor() is not None
            for action in self.file_dependent_actions:
                action.setEnabled(enable)

    def refresh_save_all_action(self):
        """Enable 'Save All' if there are files to be saved"""
        editorstack = self.get_current_editorstack()
        if editorstack:
            state = any(
                finfo.editor.document().isModified() or finfo.newly_created
                for finfo in editorstack.data
            )
            self.save_all_action.setEnabled(state)

    def update_warning_menu(self):
        """Update warning list menu"""
        editor = self.get_current_editor()
        check_results = editor.get_current_warnings()
        self.warning_menu.clear()
        filename = self.get_current_filename()
        for message, line_number in check_results:
            error = 'syntax' in message
            text = message[:1].upper() + message[1:]
            icon = (
                self.create_icon('error') if error else
                self.create_icon('warning')
            )
            slot = (
                lambda _checked, _l=line_number: self.load(filename, goto=_l)  # noqa
            )
            action = create_action(self, text=text, icon=icon)
            action.triggered[bool].connect(slot)
            self.warning_menu.addAction(action)

    def update_todo_menu(self):
        """Update todo list menu"""
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        self.todo_menu.clear()
        filename = self.get_current_filename()
        for text, line0 in results:
            icon = self.create_icon('todo')
            slot = lambda _checked, _l=line0: self.load(filename, goto=_l)
            action = create_action(self, text=text, icon=icon)
            action.triggered[bool].connect(slot)
            self.todo_menu.addAction(action)
        self.update_todo_actions()

    def todo_results_changed(self):
        """
        Synchronize todo results between editorstacks and refresh todo list
        navigation buttons.
        """
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        index = editorstack.get_stack_index()
        if index != -1:
            filename = editorstack.data[index].filename
            for other_editorstack in self.editorstacks:
                if other_editorstack is not editorstack:
                    other_editorstack.set_todo_results(filename, results)
        self.update_todo_actions()

    def refresh_eol_chars(self, os_name):
        os_name = to_text_string(os_name)
        self.__set_eol_chars = False
        if os_name == 'nt':
            self.win_eol_action.setChecked(True)
        elif os_name == 'posix':
            self.linux_eol_action.setChecked(True)
        else:
            self.mac_eol_action.setChecked(True)
        self.__set_eol_chars = True

    def refresh_formatting(self, status):
        self.formatting_action.setEnabled(status)

    def refresh_formatter_name(self):
        formatter = self.get_conf(
            ('provider_configuration', 'lsp', 'values', 'formatting'),
            default='',
            section='completions'
        )

        self.formatting_action.setText(
            _('Format file or selection with {0}').format(
                formatter.capitalize()))

    # ---- Slots
    def opened_files_list_changed(self):
        """
        Opened files list has changed:
        --> open/close file action
        --> modification ('*' added to title)
        --> current edited file has changed
        """
        # Refresh Python file dependent actions:
        editor = self.get_current_editor()
        if editor:
            python_enable = editor.is_python_or_ipython()
            cython_enable = python_enable or (
                programs.is_module_installed('Cython') and editor.is_cython())
            for action in self.pythonfile_dependent_actions:
                enable = python_enable
                action.setEnabled(enable)
            self.sig_file_opened_closed_or_updated.emit(
                self.get_current_filename(), self.get_current_language())

    def update_code_analysis_actions(self):
        """Update actions in the warnings menu."""
        editor = self.get_current_editor()

        # To fix an error at startup
        if editor is None:
            return

        # Update actions state if there are errors present
        for action in (self.warning_list_action, self.previous_warning_action,
                       self.next_warning_action):
            action.setEnabled(editor.errors_present())

    def update_todo_actions(self):
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        state = (self.get_conf('todo_list') and
                 results is not None and len(results))
        if state is not None:
            self.todo_list_action.setEnabled(state)

    # ---- Bookmarks
    # -------------------------------------------------------------------------
    def save_bookmarks(self, filename, bookmarks):
        """Receive bookmark changes and save them."""
        filename = to_text_string(filename)
        bookmarks = to_text_string(bookmarks)
        filename = osp.normpath(osp.abspath(filename))
        bookmarks = eval(bookmarks)
        old_slots = self.get_conf('bookmarks', default={})
        new_slots = update_bookmarks(filename, bookmarks, old_slots)
        if new_slots:
            self.set_conf('bookmarks', new_slots)

    # ---- File I/O
    # -------------------------------------------------------------------------
    def __load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if not osp.isfile(self.TEMPFILE_PATH):
            # Creating temporary file
            default = ['# -*- coding: utf-8 -*-',
                       '"""', _("Spyder Editor"), '',
                       _("This is a temporary script file."),
                       '"""', '', '']
            text = os.linesep.join([encoding.to_unicode(qstr)
                                    for qstr in default])
            try:
                encoding.write(to_text_string(text), self.TEMPFILE_PATH,
                               'utf-8')
            except EnvironmentError:
                self.new()
                return

        self.load(self.TEMPFILE_PATH)

    @Slot()
    def __set_workdir(self):
        """Set current script directory as working directory"""
        fname = self.get_current_filename()
        if fname is not None:
            directory = osp.dirname(osp.abspath(fname))
            self.sig_dir_opened.emit(directory)

    def __add_recent_file(self, fname):
        """Add to recent file list"""
        if fname is None:
            return
        if fname in self.recent_files:
            self.recent_files.remove(fname)
        self.recent_files.insert(0, fname)
        if len(self.recent_files) > self.get_conf('max_recent_files'):
            self.recent_files.pop(-1)

    def _clone_file_everywhere(self, finfo):
        """
        Clone file (*src_editor* widget) in all editorstacks.

        Cloning from the first editorstack in which every single new editor
        is created (when loading or creating a new file).
        """
        for editorstack in self.editorstacks[1:]:
            editorstack.clone_editor_from(finfo, set_current=False)

    @Slot()
    @Slot(str)
    def new(self, fname=None, editorstack=None, text=None):
        """
        Create a new file.

        fname=None --> fname will be 'untitledXX.py' but do not create file
        fname=<basestring> --> create file
        """
        # If no text is provided, create default content
        try:
            if text is None:
                default_content = True
                text, enc = encoding.read(self.TEMPLATE_PATH)
                enc_match = re.search(r'-*- coding: ?([a-z0-9A-Z\-]*) -*-',
                                      text)
                if enc_match:
                    enc = enc_match.group(1)

                # Initialize template variables
                # Windows
                username = encoding.to_unicode_from_fs(
                                os.environ.get('USERNAME', ''))
                # Linux, Mac OS X
                if not username:
                    username = encoding.to_unicode_from_fs(
                                   os.environ.get('USER', '-'))
                VARS = {
                    'date': time.ctime(),
                    'username': username,
                }
                try:
                    text = text % VARS
                except Exception:
                    pass
            else:
                default_content = False
                enc = encoding.read(self.TEMPLATE_PATH)[1]
        except (IOError, OSError):
            text = ''
            enc = 'utf-8'
            default_content = True

        create_fname = lambda n: to_text_string(_("untitled")) + ("%d.py" % n)  # noqa

        # Creating editor widget
        if editorstack is None:
            current_es = self.get_current_editorstack()
        else:
            current_es = editorstack

        created_from_here = fname is None
        if created_from_here:
            if self.untitled_num == 0:
                for finfo in current_es.data:
                    current_filename = finfo.editor.filename
                    if _("untitled") in current_filename:
                        # Start the counter of the untitled_num with respect
                        # to this number if there's other untitled file in
                        # spyder. Please see spyder-ide/spyder#7831
                        fname_data = osp.splitext(current_filename)

                        try:
                            act_num = int(
                                fname_data[0].split(_("untitled"))[-1])
                            self.untitled_num = act_num + 1
                        except ValueError:
                            # Catch the error in case the user has something
                            # different from a number after the untitled
                            # part.
                            # Please see spyder-ide/spyder#12892
                            self.untitled_num = 0

            while True:
                fname = create_fname(self.untitled_num)
                self.untitled_num += 1
                if not osp.isfile(fname):
                    break

            basedir = getcwd_or_home()
            active_project_path = self.get_active_project_path()
            if active_project_path is not None:
                basedir = active_project_path
            else:
                c_fname = self.get_current_filename()
                if c_fname is not None and c_fname != self.TEMPFILE_PATH:
                    basedir = osp.dirname(c_fname)
            fname = osp.abspath(osp.join(basedir, fname))
        else:
            # QString when triggered by a Qt signal
            fname = osp.abspath(to_text_string(fname))
            index = current_es.has_filename(fname)
            if index is not None and not current_es.close_file(index):
                return

        # Creating the editor widget in the first editorstack (the one that
        # can't be destroyed), then cloning this editor widget in all other
        # editorstacks:
        # Setting empty to True by default to avoid the additional space
        # created at the end of the templates.
        # See: spyder-ide/spyder#12596
        finfo = self.editorstacks[0].new(fname, enc, text, default_content,
                                         empty=True)
        self._clone_file_everywhere(finfo)
        current_es.set_current_filename(finfo.filename)

        if not created_from_here:
            self.save(force=True)

    def edit_template(self):
        """Edit new file template"""
        self.load(self.TEMPLATE_PATH)

    def update_recent_file_menu(self):
        """Update recent file menu"""
        recent_files = []
        for fname in self.recent_files:
            if osp.isfile(fname):
                recent_files.append(fname)

        self.recent_file_menu.clear_actions()
        if recent_files:
            for fname in recent_files:
                action = create_action(
                    self, fname,
                    icon=ima.get_icon_by_extension_or_type(
                        fname, scale_factor=1.0))
                action.triggered[bool].connect(self.load)
                action.setData(to_qvariant(fname))

                self.recent_file_menu.add_action(
                    action,
                    section="recent_files_section",
                    omit_id=True,
                    before_section="recent_files_actions_section"
                )

        self.clear_recent_action.setEnabled(len(recent_files) > 0)
        for menu_action in (self.max_recent_action, self.clear_recent_action):
            self.recent_file_menu.add_action(
                menu_action, section="recent_files_actions_section"
            )

        self.recent_file_menu.render()

    @Slot()
    def clear_recent_files(self):
        """Clear recent files list"""
        self.recent_files = []

    @Slot()
    def change_max_recent_files(self):
        """Change max recent files entries"""
        editorstack = self.get_current_editorstack()
        mrf, valid = QInputDialog.getInt(
            editorstack,
            _('Editor'),
            _('Maximum number of recent files'),
            self.get_conf('max_recent_files'),
            1,
            35
        )

        if valid:
            self.set_conf('max_recent_files', mrf)

    @Slot()
    @Slot(str)
    @Slot(str, int, str)
    @Slot(str, int, str, object)
    def load(self, filenames=None, goto=None, word='',
             editorwindow=None, processevents=True, start_column=None,
             end_column=None, set_focus=True, add_where='end'):
        """
        Load a text file.

        editorwindow: load in this editorwindow (useful when clicking on
        outline explorer with multiple editor windows)
        processevents: determines if processEvents() should be called at the
        end of this method (set to False to prevent keyboard events from
        creeping through to the editor during debugging)
        If goto is not none it represent a line to go to. start_column is
        the start position in this line and end_column the length
        (So that the end position is start_column + end_column)
        Alternatively, the first match of word is used as a position.
        """
        cursor_history_state = self.__ignore_cursor_history
        self.__ignore_cursor_history = True

        # Switch to editor before trying to load a file.
        # Here we catch RuntimeError to avoid an issue when loading files.
        # Fixes spyder-ide/spyder#20055
        try:
            self.switch_to_plugin()
        except (AttributeError, RuntimeError):
            pass

        editor0 = self.get_current_editor()
        if editor0 is not None:
            filename0 = self.get_current_filename()
        else:
            filename0 = None

        if not filenames:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filenames = from_qvariant(action.data(), to_text_string)

        if not filenames:
            basedir = getcwd_or_home()
            if self.edit_filetypes is None:
                self.edit_filetypes = get_edit_filetypes()
            if self.edit_filters is None:
                self.edit_filters = get_edit_filters()

            c_fname = self.get_current_filename()
            if c_fname is not None and c_fname != self.TEMPFILE_PATH:
                basedir = osp.dirname(c_fname)

            self.sig_redirect_stdio_requested.emit(False)
            parent_widget = self.get_current_editorstack()
            if filename0 is not None:
                selectedfilter = get_filter(self.edit_filetypes,
                                            osp.splitext(filename0)[1])
            else:
                selectedfilter = ''

            if not running_under_pytest():
                # See: spyder-ide/spyder#3291
                if sys.platform == 'darwin':
                    dialog = QFileDialog(
                        parent=parent_widget,
                        caption=_("Open file"),
                        directory=basedir,
                    )
                    dialog.setNameFilters(self.edit_filters.split(';;'))
                    dialog.setOption(QFileDialog.HideNameFilterDetails, True)
                    dialog.setFilter(QDir.AllDirs | QDir.Files | QDir.Drives
                                     | QDir.Hidden)
                    dialog.setFileMode(QFileDialog.ExistingFiles)

                    if dialog.exec_():
                        filenames = dialog.selectedFiles()
                else:
                    filenames, _sf = getopenfilenames(
                        parent_widget,
                        _("Open file"),
                        basedir,
                        self.edit_filters,
                        selectedfilter=selectedfilter,
                        options=QFileDialog.HideNameFilterDetails,
                    )
            else:
                # Use a Qt (i.e. scriptable) dialog for pytest
                dialog = QFileDialog(parent_widget, _("Open file"),
                                     options=QFileDialog.DontUseNativeDialog)
                if dialog.exec_():
                    filenames = dialog.selectedFiles()

            self.sig_redirect_stdio_requested.emit(True)

            if filenames:
                filenames = [osp.normpath(fname) for fname in filenames]
            else:
                self.__ignore_cursor_history = cursor_history_state
                return

        focus_widget = QApplication.focusWidget()
        if self.editorwindows and not self.dockwidget.isVisible():
            # We override the editorwindow variable to force a focus on
            # the editor window instead of the hidden editor dockwidget.
            # See spyder-ide/spyder#5742.
            if editorwindow not in self.editorwindows:
                editorwindow = self.editorwindows[0]
            editorwindow.setFocus()
            editorwindow.raise_()
        elif (self.dockwidget and not self._is_maximized
              and not self.dockwidget.isAncestorOf(focus_widget)
              and not isinstance(focus_widget, CodeEditor)):
            self.switch_to_plugin()

        def _convert(fname):
            fname = encoding.to_unicode_from_fs(fname)
            if os.name == 'nt':
                # Try to get the correct capitalization and absolute path
                try:
                    # This should correctly capitalize the path on Windows
                    fname = str(Path(fname).resolve())
                except OSError:
                    # On Windows, "<string>" is not a valid path
                    # But it can be used as filename while debugging
                    fname = osp.abspath(fname)
            else:
                fname = osp.abspath(fname)

            if os.name == 'nt' and len(fname) >= 2 and fname[1] == ':':
                fname = fname[0].upper()+fname[1:]

            return fname

        if hasattr(filenames, 'replaceInStrings'):
            # This is a QStringList instance (PyQt API #1), converting to list:
            filenames = list(filenames)
        if not isinstance(filenames, list):
            filenames = [_convert(filenames)]
        else:
            filenames = [_convert(fname) for fname in list(filenames)]
        if isinstance(goto, int):
            goto = [goto]
        elif goto is not None and len(goto) != len(filenames):
            goto = None

        for index, filename in enumerate(filenames):
            # -- Do not open an already opened file
            focus = set_focus and index == 0
            current_editor = self.set_current_filename(filename,
                                                       editorwindow,
                                                       focus=focus)
            if current_editor is None:
                # Not a valid filename, we need to continue.
                if not osp.isfile(filename):
                    continue

                current_es = self.get_current_editorstack(editorwindow)

                # Creating the editor widget in the first editorstack
                # (the one that can't be destroyed), then cloning this
                # editor widget in all other editorstacks:
                finfo = self.editorstacks[0].load(
                    filename, set_current=False, add_where=add_where,
                    processevents=processevents)

                # This can happen when it was not possible to load filename
                # from disk.
                # Fixes spyder-ide/spyder#20670
                if finfo is None:
                    continue

                self._clone_file_everywhere(finfo)
                current_editor = current_es.set_current_filename(filename,
                                                                 focus=focus)
                slots = self.get_conf('bookmarks', default={})
                current_editor.set_bookmarks(load_bookmarks(filename, slots))
                current_es.analyze_script()
                self.__add_recent_file(filename)

            if goto is not None:  # 'word' is assumed to be None as well
                current_editor.go_to_line(goto[index], word=word,
                                          start_column=start_column,
                                          end_column=end_column)
            current_editor.clearFocus()
            current_editor.setFocus()
            current_editor.window().raise_()

            if processevents:
                QApplication.processEvents()

        self.__ignore_cursor_history = cursor_history_state
        self.add_cursor_to_history()

    def _create_print_editor(self):
        """Create a SimpleCodeEditor instance to print file contents."""
        editor = SimpleCodeEditor(self)
        editor.setup_editor(
            color_scheme="scintilla", highlight_current_line=False
        )
        return editor

    @Slot()
    def print_file(self):
        """Print current file."""
        editor = self.get_current_editor()
        filename = self.get_current_filename()

        # Set print editor
        self._print_editor.set_text(editor.toPlainText())
        self._print_editor.set_language(editor.language)
        self._print_editor.set_font(self._font)

        # Create printer
        printer = SpyderPrinter(mode=QPrinter.HighResolution,
                                header_font=self._font)
        print_dialog = QPrintDialog(printer, self._print_editor)

        # Adjust print options when user has selected text
        if editor.has_selected_text():
            print_dialog.setOption(QAbstractPrintDialog.PrintSelection, True)

            # Copy selection from current editor to print editor
            cursor_1 = editor.textCursor()
            start, end = cursor_1.selectionStart(), cursor_1.selectionEnd()

            cursor_2 = self._print_editor.textCursor()
            cursor_2.setPosition(start)
            cursor_2.setPosition(end, QTextCursor.KeepAnchor)
            self._print_editor.setTextCursor(cursor_2)

        # Print
        self.sig_redirect_stdio_requested.emit(False)
        answer = print_dialog.exec_()
        self.sig_redirect_stdio_requested.emit(True)

        if answer == QDialog.Accepted:
            self.starting_long_process.emit(_("Printing..."))
            printer.setDocName(filename)
            self._print_editor.print_(printer)
            self.ending_long_process.emit("")

        # Clear selection
        self._print_editor.textCursor().removeSelectedText()

    @Slot()
    def print_preview(self):
        """Print preview for current file."""
        editor = self.get_current_editor()

        # Set print editor
        self._print_editor.set_text(editor.toPlainText())
        self._print_editor.set_language(editor.language)
        self._print_editor.set_font(self._font)

        # Create printer
        printer = SpyderPrinter(mode=QPrinter.HighResolution,
                                header_font=self._font)

        # Create preview
        preview = SpyderPrintPreviewDialog(printer, self)
        preview.setWindowFlags(Qt.Window)
        preview.paintRequested.connect(
            lambda printer: self._print_editor.print_(printer)
        )

        # Show preview
        self.sig_redirect_stdio_requested.emit(False)
        preview.exec_()
        self.sig_redirect_stdio_requested.emit(True)

    def can_close_file(self, filename=None):
        """
        Check if a file can be closed taking into account debugging state.
        """
        return self._plugin._debugger_close_file(filename)

    @Slot()
    def close_file(self):
        """Close current file"""
        filename = self.get_current_filename()
        if self.can_close_file(filename=filename):
            editorstack = self.get_current_editorstack()
            editorstack.close_file()

    @Slot()
    def close_all_files(self):
        """Close all opened scripts"""
        self.editorstacks[0].close_all_files()

    @Slot()
    def save(self, index=None, force=False):
        """Save file"""
        editorstack = self.get_current_editorstack()
        return editorstack.save(index=index, force=force)

    @Slot()
    def save_as(self):
        """Save *as* the currently edited file"""
        editorstack = self.get_current_editorstack()
        if editorstack.save_as():
            fname = editorstack.get_current_filename()
            self.__add_recent_file(fname)

    @Slot()
    def save_copy_as(self):
        """Save *copy as* the currently edited file"""
        editorstack = self.get_current_editorstack()
        editorstack.save_copy_as()

    @Slot()
    def save_all(self, save_new_files=True):
        """Save all opened files"""
        self.get_current_editorstack().save_all(save_new_files=save_new_files)

    @Slot()
    def revert(self):
        """Revert the currently edited file from disk"""
        editorstack = self.get_current_editorstack()
        editorstack.revert()

    @Slot()
    def find(self):
        """Find slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.show()
        editorstack.find_widget.search_text.setFocus()

    @Slot()
    def find_next(self):
        """Find next slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.find_next()

    @Slot()
    def find_previous(self):
        """Find previous slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.find_previous()

    @Slot()
    def replace(self):
        """Replace slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.show_replace()

    def open_last_closed(self):
        """Reopens the last closed tab."""
        editorstack = self.get_current_editorstack()
        last_closed_files = editorstack.get_last_closed_files()
        if (len(last_closed_files) > 0):
            file_to_open = last_closed_files[0]
            last_closed_files.remove(file_to_open)
            editorstack.set_last_closed_files(last_closed_files)
            self.load(file_to_open)

    # ---- Related to the Files/Projects plugins
    # -------------------------------------------------------------------------
    def get_active_project_path(self):
        """Get the active project path."""
        return self.active_project_path

    def update_active_project_path(self, active_project_path):
        """
        Update the active project path attribute used to set the current
        opened files or when creating new files in case a project is active.

        Parameters
        ----------
        active_project_path : str
            Root path of the active project if any.

        Returns
        -------
        None.
        """
        self.active_project_path = active_project_path

    def close_file_from_name(self, filename):
        """Close file from its name"""
        filename = osp.abspath(to_text_string(filename))
        index = self.get_filename_index(filename)
        if index is not None:
            self.editorstacks[0].close_file(index)

    def removed(self, filename):
        """File was removed in file explorer widget or in project explorer"""
        self.close_file_from_name(filename)

    def removed_tree(self, dirname):
        """Directory was removed in project explorer widget"""
        dirname = osp.abspath(to_text_string(dirname))
        for fname in self.get_filenames():
            if osp.abspath(fname).startswith(dirname):
                self.close_file_from_name(fname)

    @Slot(str, str)
    @Slot(str, str, str)
    def renamed(self, source, dest, editorstack_id_str=None):
        """
        Propagate file rename to editor stacks and autosave component.

        This function is called when a file is renamed in the file explorer
        widget or the project explorer. The file may not be opened in the
        editor.
        """
        filename = osp.abspath(to_text_string(source))
        index = self.get_filename_index(filename)

        if index is not None or editorstack_id_str is not None:
            self.change_register_file_run_metadata(filename, dest)

            for editorstack in self.editorstacks:
                if (
                    editorstack_id_str is None or
                    str(id(editorstack)) != editorstack_id_str
                ):
                    editorstack.rename_in_data(
                        filename, new_filename=str(dest)
                    )

            self.editorstacks[0].autosave.file_renamed(filename, str(dest))

    def renamed_tree(self, source, dest):
        """Directory was renamed in file explorer or in project explorer."""
        dirname = osp.abspath(to_text_string(source))
        tofile = to_text_string(dest)
        for fname in self.get_filenames():
            if osp.abspath(fname).startswith(dirname):
                source_re = "^" + re.escape(source)
                dest_quoted = dest.replace("\\", r"\\")
                new_filename = re.sub(source_re, dest_quoted, fname)
                self.renamed(source=fname, dest=new_filename)

    # ---- Source code
    # -------------------------------------------------------------------------
    @Slot()
    def indent(self):
        """Indent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.indent()

    @Slot()
    def unindent(self):
        """Unindent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unindent()

    @Slot()
    def text_uppercase(self):
        """Change current line or selection to uppercase."""
        editor = self.get_current_editor()
        if editor is not None:
            editor.transform_to_uppercase()

    @Slot()
    def text_lowercase(self):
        """Change current line or selection to lowercase."""
        editor = self.get_current_editor()
        if editor is not None:
            editor.transform_to_lowercase()

    @Slot()
    def toggle_comment(self):
        """Comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.toggle_comment()

    @Slot()
    def blockcomment(self):
        """Block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.blockcomment()

    @Slot()
    def unblockcomment(self):
        """Un-block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unblockcomment()

    @Slot()
    def go_to_next_warning(self):
        self.switch_to_plugin()
        editor = self.get_current_editor()
        editor.go_to_next_warning()
        filename = self.get_current_filename()
        cursor = editor.textCursor()
        self.add_cursor_to_history(filename, cursor)

    @Slot()
    def go_to_previous_warning(self):
        self.switch_to_plugin()
        editor = self.get_current_editor()
        editor.go_to_previous_warning()
        filename = self.get_current_filename()
        cursor = editor.textCursor()
        self.add_cursor_to_history(filename, cursor)

    def toggle_eol_chars(self, os_name, checked):
        if checked:
            editor = self.get_current_editor()
            if self.__set_eol_chars:
                self.switch_to_plugin()
                editor.set_eol_chars(
                    eol_chars=sourcecode.get_eol_chars_from_os_name(os_name)
                )

    @Slot()
    def remove_trailing_spaces(self):
        self.switch_to_plugin()
        editorstack = self.get_current_editorstack()
        editorstack.remove_trailing_spaces()

    @Slot()
    def format_document_or_selection(self):
        self.switch_to_plugin()
        editorstack = self.get_current_editorstack()
        editorstack.format_document_or_selection()

    @Slot()
    def fix_indentation(self):
        self.switch_to_plugin()
        editorstack = self.get_current_editorstack()
        editorstack.fix_indentation()

    # ---- Cursor position history management
    # -------------------------------------------------------------------------
    def update_cursorpos_actions(self):
        self.previous_edit_cursor_action.setEnabled(
            self.last_edit_cursor_pos is not None)
        self.previous_cursor_action.setEnabled(
            len(self.cursor_undo_history) > 0)
        self.next_cursor_action.setEnabled(
            len(self.cursor_redo_history) > 0)

    def add_cursor_to_history(self, filename=None, cursor=None):
        if self.__ignore_cursor_history:
            return
        if filename is None:
            filename = self.get_current_filename()
        if isinstance(cursor, tuple):
            cursors = cursor
        elif cursor is None:
            editor = self.get_editor(filename)
            if editor is None:
                return
            cursors = tuple(editor.all_cursors)
        else:
            cursors = (cursor,)

        replace_last_entry = False
        if len(self.cursor_undo_history) > 0:
            fname, hist_cursors = self.cursor_undo_history[-1]
            if fname == filename and len(cursors) == len(hist_cursors):
                for cursor, hist_cursor in zip(cursors, hist_cursors):
                    if not cursor.blockNumber() == hist_cursor.blockNumber():
                        break  # If any cursor is now on a different line
                else:
                    # No cursors have changed line
                    replace_last_entry = True

        if replace_last_entry:
            self.cursor_undo_history.pop()
        else:
            # Drop redo stack as we moved
            self.cursor_redo_history = []

        self.cursor_undo_history.append((filename, cursors))
        self.update_cursorpos_actions()

    def text_changed_at(self, filename, positions):
        self.last_edit_cursor_pos = (to_text_string(filename), positions)

    def current_file_changed(self, filename, position, line, column):
        editor = self.get_current_editor()

        # Needed to validate if an editor exists.
        # See spyder-ide/spyder#20643
        if editor:
            cursors = tuple(editor.all_cursors)
            if not editor.multi_cursor_ignore_history:
                self.add_cursor_to_history(to_text_string(filename), cursors)

            # Hide any open tooltips
            current_stack = self.get_current_editorstack()
            if current_stack is not None:
                current_stack.hide_tooltip()

    def current_editor_cursor_changed(self, line, column):
        """Handles the change of the cursor inside the current editor."""
        editor = self.get_current_editor()

        # Needed to validate if an editor exists.
        # See spyder-ide/spyder#20643
        if editor:
            code_editor = self.get_current_editor()
            filename = code_editor.filename
            cursors = tuple(code_editor.all_cursors)
            if not editor.multi_cursor_ignore_history:
                self.add_cursor_to_history(to_text_string(filename), cursors)

    def remove_file_cursor_history(self, id, filename):
        """Remove the cursor history of a file if the file is closed."""
        new_history = []
        for i, (cur_filename, cursors) in enumerate(
                self.cursor_undo_history):
            if cur_filename != filename:
                new_history.append((cur_filename, cursors))
        self.cursor_undo_history = new_history

        new_redo_history = []
        for i, (cur_filename, cursors) in enumerate(
                self.cursor_redo_history):
            if cur_filename != filename:
                new_redo_history.append((cur_filename, cursors))
        self.cursor_redo_history = new_redo_history

    @Slot()
    def go_to_last_edit_location(self):
        if self.last_edit_cursor_pos is None:
            return

        filename, positions = self.last_edit_cursor_pos
        editor = None
        if osp.isfile(filename):
            self.load(filename)
            editor = self.get_current_editor()
        else:
            editor = self.set_current_filename(filename)

        if editor is None:
            self.last_edit_cursor_pos = None
            return

        character_count = editor.document().characterCount()
        if positions[-1] < character_count:
            editor.set_cursor_position(positions[-1])

        for position in positions[:-1]:
            if position < character_count:
                cursor = editor.textCursor()
                cursor.setPosition(position)
                editor.add_cursor(cursor)

    def _pop_next_cursor_diff(self, history, current_filename,
                              current_cursors):
        """Get the next cursor from history that is different from current."""
        while history:
            filename, cursors = history.pop()
            if filename != current_filename:
                return filename, cursors
            if len(cursors) != len(current_cursors):
                return filename, cursors

            for cursor, current_cursor in zip(cursors, current_cursors):
                if cursor.position() != current_cursor.position():
                    return filename, cursors

        return None, None

    def _history_step(self, backwards_history, forwards_history,
                      current_filename, current_cursors):
        """
        Move number_steps in the forwards_history, filling backwards_history.
        """
        if len(forwards_history) > 0:
            # Put the current cursor in history
            backwards_history.append(
                (current_filename, current_cursors))
            # Extract the next different cursor
            current_filename, current_cursors = (
                self._pop_next_cursor_diff(
                    forwards_history,
                    current_filename, current_cursors))

        if current_cursors is None:
            # Went too far, back up once
            current_filename, current_cursors = (
                backwards_history.pop())
        return current_filename, current_cursors

    def __move_cursor_position(self, undo: bool):
        """
        Move the cursor position forward or backward in the cursor
        position history by the specified index increment.
        """
        self.__ignore_cursor_history = True
        # Remove last position as it will be replaced by the current position
        if self.cursor_undo_history:
            self.cursor_undo_history.pop()

        # Update last position on the line
        current_filename = self.get_current_filename()
        current_cursors = tuple(self.get_current_editor().all_cursors)

        if undo:
            current_filename, current_cursors = self._history_step(
                self.cursor_redo_history,
                self.cursor_undo_history,
                current_filename, current_cursors)
        else:  # Redo
            current_filename, current_cursors = self._history_step(
                self.cursor_undo_history,
                self.cursor_redo_history,
                current_filename, current_cursors)

        # Place current cursor in history
        self.cursor_undo_history.append(
            (current_filename, current_cursors))
        filenames = self.get_current_editorstack().get_filenames()
        if (not osp.isfile(current_filename)
                and current_filename not in filenames):
            self.cursor_undo_history.pop()
        else:
            self.load(current_filename)
            editor = self.get_current_editor()
            editor.clear_extra_cursors()
            editor.setTextCursor(current_cursors[-1])
            for cursor in current_cursors[:-1]:
                editor.add_cursor(cursor)
            editor.merge_extra_cursors(True)
            editor.ensureCursorVisible()
        self.__ignore_cursor_history = False
        self.update_cursorpos_actions()

    @Slot()
    def create_cell(self):
        editor = self.get_current_editor()
        if editor is not None:
            editor.create_new_cell()

    @Slot()
    def go_to_previous_cursor_position(self):
        self.__ignore_cursor_history = True
        self.switch_to_plugin()
        self.__move_cursor_position(undo=True)

    @Slot()
    def go_to_next_cursor_position(self):
        self.__ignore_cursor_history = True
        self.switch_to_plugin()
        self.__move_cursor_position(undo=False)

    @Slot()
    def go_to_line(self, line=None):
        """Open 'go to line' dialog"""
        if isinstance(line, bool):
            line = None
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.go_to_line(line)

    # ---- Handlers for the IPython Console kernels
    # -------------------------------------------------------------------------
    def _get_editorstack(self):
        """
        Get the current editorstack.

        Raises an exception in case no editorstack is found
        """
        editorstack = self.get_current_editorstack()
        if editorstack is None:
            raise RuntimeError('No editorstack found.')

        return editorstack

    def get_editor(self, filename):
        """Get editor for filename and set it as the current editor."""
        editorstack = self._get_editorstack()
        if editorstack is None:
            return None

        if not filename:
            return None

        index = editorstack.has_filename(filename)
        if index is None:
            return None

        return editorstack.data[index].editor

    def handle_run_cell(self, cell_name, filename):
        """
        Get cell code from cell name and file name.
        """
        editorstack = self._get_editorstack()
        editor = self.get_editor(filename)

        if editor is None:
            raise RuntimeError(
                "File {} not open in the editor".format(filename))

        editorstack.last_cell_call = (filename, cell_name)

        # The file is open, load code from editor
        return editor.get_cell_code(cell_name)

    def handle_cell_count(self, filename):
        """Get number of cells in file to loop."""
        editor = self.get_editor(filename)

        if editor is None:
            raise RuntimeError(
                "File {} not open in the editor".format(filename))

        # The file is open, get cell count from editor
        return editor.get_cell_count()

    def handle_current_filename(self):
        """Get the current filename."""
        return self._get_editorstack().get_current_finfo().filename

    def handle_get_file_code(self, filename, save_all=True):
        """
        Return the bytes that compose the file.

        Bytes are returned instead of str to support non utf-8 files.
        """
        editorstack = self._get_editorstack()
        if save_all and self.get_conf('save_all_before_run', section="run"):
            editorstack.save_all(save_new_files=False)
        editor = self.get_editor(filename)

        if editor is None:
            # Load it from file instead
            text, _enc = encoding.read(filename)
            return text

        return editor.toPlainText()

    # ---- Run/debug files
    # -------------------------------------------------------------------------
    def add_supported_run_configuration(self, config: EditorRunConfiguration):
        origin = config['origin']
        extensions = config['extension']
        contexts = config['contexts']

        if not isinstance(extensions, list):
            extensions = [extensions]

        for extension in extensions:
            ext_contexts = []
            for context in contexts:
                is_super = RunContext[context['name']] == RunContext.File
                ext_contexts.append(
                    ExtendedContext(context=context, is_super=is_super))
            supported_extension = SupportedExtensionContexts(
                input_extension=extension, contexts=ext_contexts)
            self.supported_run_extensions.append(supported_extension)

            # This is necessary for plugins that register run configs after Run
            # is available
            self.sig_register_run_configuration_provider_requested.emit(
                [supported_extension]
            )

            actual_contexts = set({})
            ext_origins = self.run_configurations_per_origin.get(extension, {})

            file_enabled = False
            for context in contexts:
                context_name = context['name']
                context_id = getattr(RunContext, context_name)
                actual_contexts |= {context_id}
                context_origins = ext_origins.get(context_id, set({}))
                context_origins |= {origin}
                ext_origins[context_id] = context_origins
                if context_id == RunContext.File:
                    file_enabled = True

            ext_contexts = self.supported_run_configurations.get(
                extension, set({}))
            ext_contexts |= actual_contexts
            self.supported_run_configurations[extension] = ext_contexts
            self.run_configurations_per_origin[extension] = ext_origins

            for filename, filename_ext in list(self.pending_run_files):
                if filename_ext == extension and file_enabled:
                    self.register_file_run_metadata(filename)
                else:
                    self.pending_run_files -= {(filename, filename_ext)}

    def remove_supported_run_configuration(
        self,
        config: EditorRunConfiguration
    ):
        origin = config['origin']
        extension = config['extension']
        contexts = config['contexts']

        ext_contexts = []
        for context in contexts:
            is_super = RunContext[context['name']] == RunContext.File
            ext_contexts.append(
                ExtendedContext(context=context, is_super=is_super)
            )
        unsupported_extension = SupportedExtensionContexts(
            input_extension=extension, contexts=ext_contexts
        )

        self.sig_deregister_run_configuration_provider_requested.emit(
            [unsupported_extension]
        )

        to_remove = []
        ext_origins = self.run_configurations_per_origin[extension]
        for context in contexts:
            context_name = context['name']
            context_id = getattr(RunContext, context_name)
            context_origins = ext_origins[context_id]
            context_origins -= {origin}
            if len(context_origins) == 0:
                to_remove.append(context_id)
                ext_origins.pop(context_id)

        if len(ext_origins) == 0:
            self.run_configurations_per_origin.pop(extension)

        ext_contexts = self.supported_run_configurations[extension]
        for context in to_remove:
            ext_contexts -= {context}

        if len(ext_contexts) == 0:
            self.supported_run_configurations.pop(extension)

        for metadata_id in list(self.metadata_per_id.keys()):
            metadata = self.metadata_per_id[metadata_id]
            if metadata['input_extension'] == extension:
                if metadata['context'] in to_remove:
                    self.metadata_per_id.pop(metadata_id)
                    filename = self.file_per_id.pop(metadata_id)
                    self.id_per_file.pop(filename)
                    self.pending_run_files |= {
                        (filename, metadata['input_extension'])}

    def get_run_configuration(self, metadata_id: str) -> RunConfiguration:
        editorstack = self.get_current_editorstack()
        self.focus_run_configuration(metadata_id)
        if self.get_conf('save_all_before_run', section="run"):
            editorstack.save_all(save_new_files=False)
        metadata = self.metadata_per_id[metadata_id]
        context = metadata['context']['name']
        context = getattr(RunContext, context)
        run_input = {}
        if context == RunContext.File:
            run_input = FileRun(path=metadata['name'])
        run_conf = RunConfiguration(output_formats=[], run_input=run_input,
                                    metadata=metadata)
        return run_conf

    def get_run_configuration_per_context(
        self, context, extra_action_name, context_modificator, re_run=False
    ) -> Optional[RunConfiguration]:
        editorstack = self.get_current_editorstack()
        run_input = {}
        context_name = None

        if context == RunContext.Selection:
            fname = self.get_current_filename()

            if context_modificator == SelectionContextModificator.ToLine:
                to_current_line = editorstack.get_to_current_line()
                if to_current_line is not None:
                    text, offsets, line_cols, enc = to_current_line
                else:
                    return
            elif (
                context_modificator == SelectionContextModificator.FromLine
            ):
                text, offsets, line_cols, enc = (
                    editorstack.get_from_current_line())
            else:
                text, offsets, line_cols, enc = editorstack.get_selection()

            # Don't advance line if the selection includes multiple lines. That
            # was the behavior in Spyder 5 and users are accustomed to it.
            # Fixes spyder-ide/spyder#22060
            eol = self.get_current_editor().get_line_separator()
            if extra_action_name == ExtraAction.Advance and not (eol in text):
                editorstack.advance_line()

            context_name = 'Selection'
            run_input = SelectionRun(
                path=fname, selection=text, encoding=enc,
                line_col_bounds=line_cols, character_bounds=offsets)
        elif context == RunContext.Cell:
            if re_run:
                info = editorstack.get_last_cell()
                fname = editorstack.last_cell_call[0]
            else:
                info = editorstack.get_current_cell()
                fname = self.get_current_filename()

            text, offsets, line_cols, cell_name, enc = info
            context_name = 'Cell'
            copy_cell = self.get_conf('run_cell_copy', section='run')
            run_input = CellRun(
                path=fname, cell=text, cell_name=cell_name, encoding=enc,
                line_col_bounds=line_cols, character_bounds=offsets,
                copy=copy_cell)

            if extra_action_name == ExtraAction.Advance:
                editorstack.advance_cell()

        __, filename_ext = osp.splitext(fname)
        fname_ext = filename_ext[1:]

        metadata: RunConfigurationMetadata = {
            'name': fname,
            'source': self._plugin.NAME,
            'path': fname,
            'datetime': datetime.now(),
            'uuid': None,
            'context': {
                'name': context_name
            },
            'input_extension': fname_ext
        }
        run_conf = RunConfiguration(output_formats=[], run_input=run_input,
                                    metadata=metadata)

        return run_conf

    def focus_run_configuration(self, uuid: str):
        fname = self.file_per_id[uuid]
        editorstack = self.get_current_editorstack()
        current_fname = self.get_current_filename()
        if current_fname != fname:
            editorstack.set_current_filename(fname)

    def trigger_run_action(self, action_id):
        """Trigger a run action according to its id."""
        action = self.get_action(action_id, plugin=Plugins.Run)
        action.trigger()

    def trigger_debugger_action(self, action_id):
        """Trigger a run action according to its id."""
        action = self.get_action(action_id, plugin=Plugins.Debugger)
        action.trigger()

    # ---- Code bookmarks
    # -------------------------------------------------------------------------
    @Slot(int)
    def save_bookmark(self, slot_num):
        """Save current line and position as bookmark."""
        bookmarks = self.get_conf('bookmarks')
        editorstack = self.get_current_editorstack()
        if slot_num in bookmarks:
            filename, line_num, column = bookmarks[slot_num]
            if osp.isfile(filename):
                index = editorstack.has_filename(filename)
                if index is not None:
                    block = (editorstack.tabs.widget(index).document()
                             .findBlockByNumber(line_num))
                    block.userData().bookmarks.remove((slot_num, column))
        if editorstack is not None:
            self.switch_to_plugin()
            editorstack.set_bookmark(slot_num)

    @Slot(int)
    def load_bookmark(self, slot_num):
        """Set cursor to bookmarked file and position."""
        bookmarks = self.get_conf('bookmarks')
        if slot_num in bookmarks:
            filename, line_num, column = bookmarks[slot_num]
        else:
            return
        if not osp.isfile(filename):
            self.last_edit_cursor_pos = None
            return
        self.load(filename)
        editor = self.get_current_editor()
        if line_num < editor.document().lineCount():
            linelength = len(editor.document()
                             .findBlockByNumber(line_num).text())
            if column <= linelength:
                editor.go_to_line(line_num + 1, column)
            else:
                # Last column
                editor.go_to_line(line_num + 1, linelength)

    # ---- Zoom in/out/reset
    # -------------------------------------------------------------------------
    def zoom(self, factor):
        """Zoom in/out/reset"""
        editor = self.get_current_editorstack().get_current_editor()
        if factor == 0:
            font = self._font
            editor.set_font(font)
        else:
            font = editor.font()
            size = font.pointSize() + factor
            if size > 0:
                font.setPointSize(size)
                editor.set_font(font)
        editor.update_tab_stop_width_spaces()

    # ---- Options
    # -------------------------------------------------------------------------
    def _on_checkable_action_change(self, option, value):
        action = self.checkable_actions[option]
        # Avoid triggering the action when it changes state
        action.blockSignals(True)
        action.setChecked(value)
        action.blockSignals(False)
        # See: spyder-ide/spyder#9915

    @on_conf_change(
        option=[
            ('provider_configuration', 'lsp', 'values', 'pycodestyle'),
            ('provider_configuration', 'lsp', 'values', 'pydocstyle')
        ],
        section='completions'
    )
    def on_completions_checkable_action_change(self, option, value):
        option = option[-1]  # Get 'pycodestyle' or 'pydocstyle'
        self._on_checkable_action_change(option, value)

    @on_conf_change(
        option=[
            'blank_spaces',
            'scroll_past_end',
            'indent_guides',
            'code_folding',
            'show_class_func_dropdown',
            'underline_errors'
        ]
    )
    def on_editor_checkable_action_change(self, option, value):
        self._on_checkable_action_change(option, value)

    @on_conf_change(
        option=[
            'line_numbers',
            'todo_list'
        ]
    )
    def on_current_finfo_option_change(self, option, value):
        option_to_method = {
            'line_numbers': 'set_linenumbers_enabled',
            'todo_list': 'set_todolist_enabled'
        }
        finfo = self.get_current_finfo()
        if self.editorstacks is not None:
            for editorstack in self.editorstacks:
                getattr(editorstack, option_to_method[option])(
                    value, current_finfo=finfo
                )
        # We must update the current editor after the others:
        # (otherwise, code analysis buttons state would correspond to the
        #  last editor instead of showing the one of the current editor)
        if finfo is not None and option == 'todo_list':
            finfo.run_todo_finder()

    @on_conf_change(option='autosave_enabled')
    def on_autosave_enabled_change(self, value):
        self.autosave.enabled = value

    @on_conf_change(option='autosave_interval')
    def on_autosave_interval_change(self, value):
        # Multiply by 1000 to convert seconds to milliseconds
        self.autosave.interval = value * 1000

    # ---- Open files
    # -------------------------------------------------------------------------
    def setup_open_files(self, close_previous_files=True):
        """
        Open the list of saved files per project.

        Also open any files that the user selected in the recovery dialog.
        """
        self.set_create_new_file_if_empty(False)
        active_project_path = self.get_active_project_path()

        if active_project_path:
            filenames = self._plugin._get_project_filenames()
        else:
            filenames = self.get_conf('filenames', default=[])

        if close_previous_files:
            self.close_all_files()

        all_filenames = self.autosave.recover_files_to_open + filenames
        if all_filenames and any([osp.isfile(f) for f in all_filenames]):
            layout = self.get_conf('layout_settings', None)
            # Check if no saved layout settings exist, e.g. clean prefs file.
            # If not, load with default focus/layout, to fix
            # spyder-ide/spyder#8458.
            if layout:
                is_vertical, cfname, clines = layout.get('splitsettings')[0]
                # Check that a value for current line exist for each filename
                # in the available settings. See spyder-ide/spyder#12201
                if cfname in filenames and len(filenames) == len(clines):
                    index = filenames.index(cfname)
                    # First we load the last focused file.
                    self.load(
                        filenames[index],
                        goto=clines[index],
                        set_focus=True
                    )
                    # Then we load the files located to the left of the last
                    # focused file in the tabbar, while keeping the focus on
                    # the last focused file.
                    if index > 0:
                        self.load(filenames[index::-1], goto=clines[index::-1],
                                  set_focus=False, add_where='start')
                    # Then we load the files located to the right of the last
                    # focused file in the tabbar, while keeping the focus on
                    # the last focused file.
                    if index < (len(filenames) - 1):
                        self.load(filenames[index+1:], goto=clines[index:],
                                  set_focus=False, add_where='end')
                    # Finally we load any recovered files at the end of
                    # the tabbar, while keeping focus on the last focused file.
                    if self.autosave.recover_files_to_open:
                        self.load(self.autosave.recover_files_to_open,
                                  set_focus=False, add_where='end')
                else:
                    if filenames:
                        self.load(filenames, goto=clines)
                    if self.autosave.recover_files_to_open:
                        self.load(self.autosave.recover_files_to_open)
            else:
                if filenames:
                    self.load(filenames)
                if self.autosave.recover_files_to_open:
                    self.load(self.autosave.recover_files_to_open)

            if self.__first_open_files_setup:
                self.__first_open_files_setup = False
                if layout is not None:
                    self.editorsplitter.set_layout_settings(
                        layout,
                        dont_goto=filenames[0])
                win_layout = self.get_conf('windows_layout_settings', [])
                if win_layout:
                    for layout_settings in win_layout:
                        self.editorwindows_to_be_created.append(
                            layout_settings)
                self.set_last_focused_editorstack(self, self.editorstacks[0])

            # This is necessary to update the statusbar widgets after files
            # have been loaded.
            editorstack = self.get_current_editorstack()
            if editorstack:
                editorstack.refresh()

            # This is necessary to paint correctly the editorstack tabbars.
            for editorstack in self.editorstacks:
                if editorstack:
                    editorstack.tabs.refresh_style()
        else:
            self.__load_temp_file()
        self.set_create_new_file_if_empty(True)
        self.sig_open_files_finished.emit()

    def save_open_files(self):
        """Save the list of open files"""
        self.set_conf('filenames', self.get_filenames())

    def set_create_new_file_if_empty(self, value):
        """Change the value of create_new_file_if_empty"""
        for editorstack in self.editorstacks:
            editorstack.create_new_file_if_empty = value

    # ---- File Menu actions (Mac only)
    # -------------------------------------------------------------------------
    @Slot()
    def go_to_next_file(self):
        """Switch to next file tab on the current editor stack."""
        editorstack = self.get_current_editorstack()
        editorstack.tabs.tab_navigate(+1)

    @Slot()
    def go_to_previous_file(self):
        """Switch to previous file tab on the current editor stack."""
        editorstack = self.get_current_editorstack()
        editorstack.tabs.tab_navigate(-1)

    # ---- Misc
    # -------------------------------------------------------------------------
    def set_current_project_path(self, root_path=None):
        """
        Set the current active project root path.

        Parameters
        ----------
        root_path: str or None, optional
            Path to current project root path. Default is None.
        """
        for editorstack in self.editorstacks:
            editorstack.set_current_project_path(root_path)

    def register_panel(self, panel_class, *args, position=Panel.Position.LEFT,
                       **kwargs):
        """Register a panel in all the editorstacks in the given position."""
        for editorstack in self.editorstacks:
            editorstack.register_panel(
                panel_class, *args, position=position, **kwargs)

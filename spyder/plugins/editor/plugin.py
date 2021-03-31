# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import logging
import os
import os.path as osp
import re
import sys
import time

# Third party imports
from qtpy.compat import from_qvariant, getopenfilenames, to_qvariant
from qtpy.QtCore import QByteArray, Qt, Signal, Slot, QDir
from qtpy.QtPrintSupport import QAbstractPrintDialog, QPrintDialog, QPrinter
from qtpy.QtWidgets import (QAction, QActionGroup, QApplication, QDialog,
                            QFileDialog, QInputDialog, QMenu, QSplitter,
                            QToolBar, QVBoxLayout, QWidget)

# Local imports
from spyder.api.panel import Panel
from spyder.api.plugins import Plugins, SpyderPluginWidget
from spyder.config.base import _, get_conf_path, running_under_pytest
from spyder.config.manager import CONF
from spyder.config.utils import (get_edit_filetypes, get_edit_filters,
                                 get_filter)
from spyder.py3compat import PY2, qbytearray_to_str, to_text_string
from spyder.utils import encoding, programs, sourcecode
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import create_action, add_actions, MENU_SEPARATOR
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.findreplace import FindReplace
from spyder.plugins.editor.confpage import EditorConfigPage
from spyder.plugins.editor.utils.autosave import AutosaveForPlugin
from spyder.plugins.editor.utils.switcher import EditorSwitcherManager
from spyder.plugins.editor.widgets.codeeditor_widgets import Printer
from spyder.plugins.editor.widgets.editor import (EditorMainWindow,
                                                  EditorSplitter,
                                                  EditorStack,)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.utils.bookmarks import (load_bookmarks,
                                                   save_bookmarks)
from spyder.plugins.editor.utils.debugger import (clear_all_breakpoints,
                                                  clear_breakpoint)
from spyder.plugins.editor.widgets.status import (CursorPositionStatus,
                                                  EncodingStatus, EOLStatus,
                                                  ReadWriteStatus, VCSStatus)
from spyder.plugins.run.widgets import (ALWAYS_OPEN_FIRST_RUN_OPTION,
                                        get_run_configuration,
                                        RunConfigDialog, RunConfigOneDialog)
from spyder.plugins.mainmenu.api import ApplicationMenus


logger = logging.getLogger(__name__)


WINPDB_PATH = programs.find_program('winpdb')


class Editor(SpyderPluginWidget):
    """
    Multi-file Editor widget
    """
    CONF_SECTION = 'editor'
    CONFIGWIDGET_CLASS = EditorConfigPage
    CONF_FILE = False
    TEMPFILE_PATH = get_conf_path('temp.py')
    TEMPLATE_PATH = get_conf_path('template.py')
    DISABLE_ACTIONS_WHEN_HIDDEN = False  # SpyderPluginWidget class attribute

    # This is required for the new API
    NAME = 'editor'
    REQUIRES = []
    OPTIONAL = [Plugins.Completions, Plugins.OutlineExplorer]

    # Signals
    run_in_current_ipyclient = Signal(str, str, str,
                                      bool, bool, bool, bool, bool)
    run_cell_in_ipyclient = Signal(str, object, str, bool)
    debug_cell_in_ipyclient = Signal(str, object, str, bool)
    exec_in_extconsole = Signal(str, bool)
    redirect_stdio = Signal(bool)

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

    breakpoints_saved = Signal()

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

    sig_file_debug_message_requested = Signal()

    # This signal is fired for any focus change among all editor stacks
    sig_editor_focus_changed = Signal()

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

    def __init__(self, parent, ignore_last_opened_files=False):
        SpyderPluginWidget.__init__(self, parent)

        self.__set_eol_chars = True

        # Creating template if it doesn't already exist
        if not osp.isfile(self.TEMPLATE_PATH):
            if os.name == "nt":
                shebang = []
            else:
                shebang = ['#!/usr/bin/env python' + ('2' if PY2 else '3')]
            header = shebang + [
                '# -*- coding: utf-8 -*-',
                '"""', 'Created on %(date)s', '',
                '@author: %(username)s', '"""', '', '']
            try:
                encoding.write(os.linesep.join(header), self.TEMPLATE_PATH,
                               'utf-8')
            except EnvironmentError:
                pass

        self.projects = None
        self.outlineexplorer = None

        self.file_dependent_actions = []
        self.pythonfile_dependent_actions = []
        self.dock_toolbar_actions = None
        self.edit_menu_actions = None #XXX: find another way to notify Spyder
        self.stack_menu_actions = None
        self.checkable_actions = {}

        self.__first_open_files_setup = True
        self.editorstacks = []
        self.last_focused_editorstack = {}
        self.editorwindows = []
        self.editorwindows_to_be_created = []
        self.toolbar_list = None
        self.menu_list = None

        # We need to call this here to create self.dock_toolbar_actions,
        # which is used below.
        self._setup()
        self.options_button.hide()

        # Configuration dialog size
        self.dialog_size = None

        self.vcs_status = VCSStatus(self)
        self.cursorpos_status = CursorPositionStatus(self)
        self.encoding_status = EncodingStatus(self)
        self.eol_status = EOLStatus(self)
        self.readwrite_status = ReadWriteStatus(self)

        # TODO: temporal fix while editor uses new API
        statusbar = self.main.statusbar
        statusbar.add_status_widget(self.readwrite_status, 3)
        statusbar.add_status_widget(self.eol_status, 3)
        statusbar.add_status_widget(self.encoding_status, 3)
        statusbar.add_status_widget(self.cursorpos_status, 3)
        statusbar.add_status_widget(self.vcs_status, 3)

        layout = QVBoxLayout()
        self.dock_toolbar = QToolBar(self)
        add_actions(self.dock_toolbar, self.dock_toolbar_actions)
        layout.addWidget(self.dock_toolbar)

        self.last_edit_cursor_pos = None
        self.cursor_pos_history = []
        self.cursor_pos_index = None
        self.__ignore_cursor_position = True

        # Completions setup
        self.completion_capabilities = {}

        # Setup new windows:
        self.main.all_actions_defined.connect(self.setup_other_windows)

        # Change module completions when PYTHONPATH changes
        self.main.sig_pythonpath_changed.connect(self.set_path)

        # Find widget
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        self.register_widget_shortcuts(self.find_widget)

        # Start autosave component
        # (needs to be done before EditorSplitter)
        self.autosave = AutosaveForPlugin(self)
        self.autosave.try_recover_from_autosave()
        # Multiply by 1000 to convert seconds to milliseconds
        self.autosave.interval = self.get_option('autosave_interval') * 1000
        self.autosave.enabled = self.get_option('autosave_enabled')

        # Tabbed editor widget + Find/Replace widget
        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        self.editorsplitter = EditorSplitter(self, self,
                                         self.stack_menu_actions, first=True)
        editor_layout.addWidget(self.editorsplitter)
        editor_layout.addWidget(self.find_widget)

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
        state = self.get_option('splitter_state', None)
        if state is not None:
            self.splitter.restoreState( QByteArray().fromHex(
                    str(state).encode('utf-8')) )

        self.recent_files = self.get_option('recent_files', [])
        self.untitled_num = 0

        # Parameters of last file execution:
        self.__last_ic_exec = None # internal console
        self.__last_ec_exec = None # external console

        # File types and filters used by the Open dialog
        self.edit_filetypes = None
        self.edit_filters = None

        self.__ignore_cursor_position = False
        current_editor = self.get_current_editor()
        if current_editor is not None:
            filename = self.get_current_filename()
            position = current_editor.get_position('cursor')
            line, column = current_editor.get_cursor_line_column()
            self.add_cursor_position_to_history(filename, position, line,
                                                column)
        self.update_cursorpos_actions()
        self.set_path()

    def set_projects(self, projects):
        self.projects = projects

    @Slot()
    def show_hide_projects(self):
        if self.projects is not None:
            dw = self.projects.dockwidget
            if dw.isVisible():
                dw.hide()
            else:
                dw.show()
                dw.raise_()
            self.switch_to_plugin()

    def set_outlineexplorer(self, outlineexplorer):
        self.outlineexplorer = outlineexplorer
        for editorstack in self.editorstacks:
            # Pass the OutlineExplorer widget to the stacks because they
            # don't need the plugin
            editorstack.set_outlineexplorer(self.outlineexplorer.get_widget())
        self.outlineexplorer.get_widget().edit_goto.connect(
                           lambda filenames, goto, word:
                           self.load(filenames=filenames, goto=goto, word=word,
                                     editorwindow=self))
        self.outlineexplorer.get_widget().edit.connect(
                             lambda filenames:
                             self.load(filenames=filenames, editorwindow=self))

    #------ Private API --------------------------------------------------------
    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        # Widget is now visible, we may center cursor on top level editor:
        try:
            self.get_current_editor().centerCursor()
        except AttributeError:
            pass

    @Slot(dict)
    def report_open_file(self, options):
        """Report that a file was opened to the completion manager."""
        filename = options['filename']
        language = options['language']
        codeeditor = options['codeeditor']

        status = self.main.completions.start_completion_services_for_language(
            language.lower())
        self.main.completions.register_file(
            language.lower(), filename, codeeditor)
        if status:
            if language.lower() in self.completion_capabilities:
                # When this condition is True, it means there's a server
                # that can provide completion services for this file.
                codeeditor.register_completion_capabilities(
                    self.completion_capabilities[language.lower()])
                codeeditor.start_completion_services()
            elif self.main.completions.is_fallback_only(language.lower()):
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
        self.main.projects.start_workspace_services()

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
        self.main.completions.send_request(language, request, params)

    @Slot(str, tuple, dict)
    def _rpc_call(self, method, args, kwargs):
        meth = getattr(self, method)
        meth(*args, **kwargs)

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        title = _('Editor')
        return title

    def get_plugin_icon(self):
        """Return widget icon."""
        return ima.icon('edit')

    def get_focus_widget(self):
        """
        Return the widget to give focus to.

        This happens when plugin's dockwidget is raised on top-level.
        """
        return self.get_current_editor()

    def _visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        SpyderPluginWidget._visibility_changed(self, enable)
        if self.dockwidget is None:
            return
        if self.dockwidget.isWindow():
            self.dock_toolbar.show()
        else:
            self.dock_toolbar.hide()
        if enable:
            self.refresh_plugin()
        self.sig_update_plugin_title.emit()

    def refresh_plugin(self):
        """Refresh editor plugin"""
        editorstack = self.get_current_editorstack()
        editorstack.refresh()
        self.refresh_save_all_action()

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        state = self.splitter.saveState()
        self.set_option('splitter_state', qbytearray_to_str(state))
        editorstack = self.editorstacks[0]

        active_project_path = None
        if self.projects is not None:
            active_project_path = self.projects.get_active_project_path()
        if not active_project_path:
            self.set_open_filenames()
        else:
            self.projects.set_project_filenames(
                [finfo.filename for finfo in editorstack.data])

        self.set_option('layout_settings',
                        self.editorsplitter.get_layout_settings())
        self.set_option('windows_layout_settings',
                    [win.get_layout_settings() for win in self.editorwindows])
#        self.set_option('filenames', filenames)
        self.set_option('recent_files', self.recent_files)

        # Stop autosave timer before closing windows
        self.autosave.stop_autosave_timer()

        try:
            if not editorstack.save_if_changed(cancelable) and cancelable:
                return False
            else:
                for win in self.editorwindows[:]:
                    win.close()
                return True
        except IndexError:
            return True

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        # ---- File menu and toolbar ----
        self.new_action = create_action(
                self,
                _("&New file..."),
                icon=ima.icon('filenew'), tip=_("New file"),
                triggered=self.new,
                context=Qt.WidgetShortcut
        )
        self.register_shortcut(self.new_action, context="Editor",
                               name="New file", add_shortcut_to_tip=True)

        self.open_last_closed_action = create_action(
                self,
                _("O&pen last closed"),
                tip=_("Open last closed"),
                triggered=self.open_last_closed
        )
        self.register_shortcut(self.open_last_closed_action, context="Editor",
                               name="Open last closed")

        self.open_action = create_action(self, _("&Open..."),
                icon=ima.icon('fileopen'), tip=_("Open file"),
                triggered=self.load,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.open_action, context="Editor",
                               name="Open file", add_shortcut_to_tip=True)

        self.revert_action = create_action(self, _("&Revert"),
                icon=ima.icon('revert'), tip=_("Revert file from disk"),
                triggered=self.revert)

        self.save_action = create_action(self, _("&Save"),
                icon=ima.icon('filesave'), tip=_("Save file"),
                triggered=self.save,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.save_action, context="Editor",
                               name="Save file", add_shortcut_to_tip=True)

        self.save_all_action = create_action(self, _("Sav&e all"),
                icon=ima.icon('save_all'), tip=_("Save all files"),
                triggered=self.save_all,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.save_all_action, context="Editor",
                               name="Save all", add_shortcut_to_tip=True)

        save_as_action = create_action(self, _("Save &as..."), None,
                ima.icon('filesaveas'), tip=_("Save current file as..."),
                triggered=self.save_as,
                context=Qt.WidgetShortcut)
        self.register_shortcut(save_as_action, "Editor", "Save As")

        save_copy_as_action = create_action(self, _("Save copy as..."), None,
                ima.icon('filesaveas'), _("Save copy of current file as..."),
                triggered=self.save_copy_as)

        print_preview_action = create_action(self, _("Print preview..."),
                tip=_("Print preview..."), triggered=self.print_preview)
        self.print_action = create_action(self, _("&Print..."),
                icon=ima.icon('print'), tip=_("Print current file..."),
                triggered=self.print_file)
        # Shortcut for close_action is defined in widgets/editor.py
        self.close_action = create_action(self, _("&Close"),
                icon=ima.icon('fileclose'), tip=_("Close current file"),
                triggered=self.close_file)

        self.close_all_action = create_action(self, _("C&lose all"),
                icon=ima.icon('filecloseall'), tip=_("Close all opened files"),
                triggered=self.close_all_files,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.close_all_action, context="Editor",
                               name="Close all")

        # ---- Find menu and toolbar ----
        _text = _("&Find text")
        find_action = create_action(self, _text, icon=ima.icon('find'),
                                    tip=_text, triggered=self.find,
                                    context=Qt.WidgetShortcut)
        self.register_shortcut(find_action, context="find_replace",
                               name="Find text", add_shortcut_to_tip=True)
        find_next_action = create_action(self, _("Find &next"),
                                         icon=ima.icon('findnext'),
                                         triggered=self.find_next,
                                         context=Qt.WidgetShortcut)
        self.register_shortcut(find_next_action, context="find_replace",
                               name="Find next")
        find_previous_action = create_action(self, _("Find &previous"),
                                             icon=ima.icon('findprevious'),
                                             triggered=self.find_previous,
                                             context=Qt.WidgetShortcut)
        self.register_shortcut(find_previous_action, context="find_replace",
                               name="Find previous")
        _text = _("&Replace text")
        replace_action = create_action(self, _text, icon=ima.icon('replace'),
                                       tip=_text, triggered=self.replace,
                                       context=Qt.WidgetShortcut)
        self.register_shortcut(replace_action, context="find_replace",
                               name="Replace text")

        # ---- Debug menu and toolbar ----
        set_clear_breakpoint_action = create_action(self,
                                    _("Set/Clear breakpoint"),
                                    icon=ima.icon('breakpoint_big'),
                                    triggered=self.set_or_clear_breakpoint,
                                    context=Qt.WidgetShortcut)
        self.register_shortcut(set_clear_breakpoint_action, context="Editor",
                               name="Breakpoint")

        set_cond_breakpoint_action = create_action(self,
                            _("Set/Edit conditional breakpoint"),
                            icon=ima.icon('breakpoint_cond_big'),
                            triggered=self.set_or_edit_conditional_breakpoint,
                            context=Qt.WidgetShortcut)
        self.register_shortcut(set_cond_breakpoint_action, context="Editor",
                               name="Conditional breakpoint")

        clear_all_breakpoints_action = create_action(self,
                                    _('Clear breakpoints in all files'),
                                    triggered=self.clear_all_breakpoints)

        self.winpdb_action = create_action(self, _("Debug with winpdb"),
                                           triggered=self.run_winpdb)
        self.winpdb_action.setEnabled(WINPDB_PATH is not None and PY2)

        # --- Debug toolbar ---
        self.debug_action = create_action(
            self, _("&Debug"),
            icon=ima.icon('debug'),
            tip=_("Debug file"),
            triggered=self.debug_file)
        self.register_shortcut(self.debug_action, context="_", name="Debug",
                               add_shortcut_to_tip=True)

        self.debug_next_action = create_action(
            self, _("Step"),
            icon=ima.icon('arrow-step-over'), tip=_("Run current line"),
            triggered=lambda: self.debug_command("next"))
        self.register_shortcut(self.debug_next_action, "_", "Debug Step Over",
                               add_shortcut_to_tip=True)

        self.debug_continue_action = create_action(
            self, _("Continue"),
            icon=ima.icon('arrow-continue'),
            tip=_("Continue execution until next breakpoint"),
            triggered=lambda: self.debug_command("continue"))
        self.register_shortcut(
            self.debug_continue_action, "_", "Debug Continue",
            add_shortcut_to_tip=True)

        self.debug_step_action = create_action(
            self, _("Step Into"),
            icon=ima.icon('arrow-step-in'),
            tip=_("Step into function or method of current line"),
            triggered=lambda: self.debug_command("step"))
        self.register_shortcut(self.debug_step_action, "_", "Debug Step Into",
                               add_shortcut_to_tip=True)

        self.debug_return_action = create_action(
            self, _("Step Return"),
            icon=ima.icon('arrow-step-out'),
            tip=_("Run until current function or method returns"),
            triggered=lambda: self.debug_command("return"))
        self.register_shortcut(
            self.debug_return_action, "_", "Debug Step Return",
            add_shortcut_to_tip=True)

        self.debug_exit_action = create_action(
            self, _("Stop"),
            icon=ima.icon('stop_debug'), tip=_("Stop debugging"),
            triggered=self.stop_debugging)
        self.register_shortcut(self.debug_exit_action, "_", "Debug Exit",
                               add_shortcut_to_tip=True)

        # --- Run toolbar ---
        run_action = create_action(self, _("&Run"), icon=ima.icon('run'),
                                   tip=_("Run file"),
                                   triggered=self.run_file)
        self.register_shortcut(run_action, context="_", name="Run",
                               add_shortcut_to_tip=True)

        configure_action = create_action(
            self,
            _("&Configuration per file..."),
            icon=ima.icon('run_settings'),
            tip=_("Run settings"),
            menurole=QAction.NoRole,
            triggered=self.edit_run_configurations)

        self.register_shortcut(configure_action, context="_",
                               name="Configure", add_shortcut_to_tip=True)

        re_run_action = create_action(self, _("Re-run &last script"),
                                      icon=ima.icon('run_again'),
                            tip=_("Run again last file"),
                            triggered=self.re_run_file)
        self.register_shortcut(re_run_action, context="_",
                               name="Re-run last script",
                               add_shortcut_to_tip=True)

        run_selected_action = create_action(self, _("Run &selection or "
                                                    "current line"),
                                            icon=ima.icon('run_selection'),
                                            tip=_("Run selection or "
                                                  "current line"),
                                            triggered=self.run_selection,
                                            context=Qt.WidgetShortcut)
        self.register_shortcut(run_selected_action, context="Editor",
                               name="Run selection", add_shortcut_to_tip=True)

        run_cell_action = create_action(self,
                            _("Run cell"),
                            icon=ima.icon('run_cell'),
                            tip=_("Run current cell \n"
                                  "[Use #%% to create cells]"),
                            triggered=self.run_cell,
                            context=Qt.WidgetShortcut)

        self.register_shortcut(run_cell_action, context="Editor",
                               name="Run cell", add_shortcut_to_tip=True)

        run_cell_advance_action = create_action(
            self,
            _("Run cell and advance"),
            icon=ima.icon('run_cell_advance'),
            tip=_("Run current cell and go to the next one "),
            triggered=self.run_cell_and_advance,
            context=Qt.WidgetShortcut)

        self.register_shortcut(run_cell_advance_action, context="Editor",
                               name="Run cell and advance",
                               add_shortcut_to_tip=True)

        self.debug_cell_action = create_action(
            self,
            _("Debug cell"),
            icon=ima.icon('debug_cell'),
            tip=_("Debug current cell "
                  "(Alt+Shift+Enter)"),
            triggered=self.debug_cell,
            context=Qt.WidgetShortcut)

        self.register_shortcut(self.debug_cell_action, context="Editor",
                               name="Debug cell",
                               add_shortcut_to_tip=True)

        re_run_last_cell_action = create_action(self,
                   _("Re-run last cell"),
                   tip=_("Re run last cell "),
                   triggered=self.re_run_last_cell,
                   context=Qt.WidgetShortcut)
        self.register_shortcut(re_run_last_cell_action,
                               context="Editor",
                               name='re-run last cell',
                               add_shortcut_to_tip=True)

        # --- Source code Toolbar ---
        self.todo_list_action = create_action(self,
                _("Show todo list"), icon=ima.icon('todo_list'),
                tip=_("Show comments list (TODO/FIXME/XXX/HINT/TIP/@todo/"
                      "HACK/BUG/OPTIMIZE/!!!/???)"),
                triggered=self.go_to_next_todo)
        self.todo_menu = QMenu(self)
        self.todo_menu.setStyleSheet("QMenu {menu-scrollable: 1;}")
        self.todo_list_action.setMenu(self.todo_menu)
        self.todo_menu.aboutToShow.connect(self.update_todo_menu)

        self.warning_list_action = create_action(self,
                _("Show warning/error list"), icon=ima.icon('wng_list'),
                tip=_("Show code analysis warnings/errors"),
                triggered=self.go_to_next_warning)
        self.warning_menu = QMenu(self)
        self.warning_menu.setStyleSheet("QMenu {menu-scrollable: 1;}")
        self.warning_list_action.setMenu(self.warning_menu)
        self.warning_menu.aboutToShow.connect(self.update_warning_menu)
        self.previous_warning_action = create_action(self,
                _("Previous warning/error"), icon=ima.icon('prev_wng'),
                tip=_("Go to previous code analysis warning/error"),
                triggered=self.go_to_previous_warning,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.previous_warning_action,
                               context="Editor",
                               name="Previous warning",
                               add_shortcut_to_tip=True)
        self.next_warning_action = create_action(self,
                _("Next warning/error"), icon=ima.icon('next_wng'),
                tip=_("Go to next code analysis warning/error"),
                triggered=self.go_to_next_warning,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.next_warning_action,
                               context="Editor",
                               name="Next warning",
                               add_shortcut_to_tip=True)

        self.previous_edit_cursor_action = create_action(self,
                _("Last edit location"), icon=ima.icon('last_edit_location'),
                tip=_("Go to last edit location"),
                triggered=self.go_to_last_edit_location,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.previous_edit_cursor_action,
                               context="Editor",
                               name="Last edit location",
                               add_shortcut_to_tip=True)
        self.previous_cursor_action = create_action(self,
                _("Previous cursor position"), icon=ima.icon('prev_cursor'),
                tip=_("Go to previous cursor position"),
                triggered=self.go_to_previous_cursor_position,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.previous_cursor_action,
                               context="Editor",
                               name="Previous cursor position",
                               add_shortcut_to_tip=True)
        self.next_cursor_action = create_action(self,
                _("Next cursor position"), icon=ima.icon('next_cursor'),
                tip=_("Go to next cursor position"),
                triggered=self.go_to_next_cursor_position,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.next_cursor_action,
                               context="Editor",
                               name="Next cursor position",
                               add_shortcut_to_tip=True)

        # --- Edit Toolbar ---
        self.toggle_comment_action = create_action(self,
                _("Comment")+"/"+_("Uncomment"), icon=ima.icon('comment'),
                tip=_("Comment current line or selection"),
                triggered=self.toggle_comment, context=Qt.WidgetShortcut)
        self.register_shortcut(self.toggle_comment_action, context="Editor",
                               name="Toggle comment")
        blockcomment_action = create_action(self, _("Add &block comment"),
                tip=_("Add block comment around "
                            "current line or selection"),
                triggered=self.blockcomment, context=Qt.WidgetShortcut)
        self.register_shortcut(blockcomment_action, context="Editor",
                               name="Blockcomment")
        unblockcomment_action = create_action(self,
                _("R&emove block comment"),
                tip = _("Remove comment block around "
                              "current line or selection"),
                triggered=self.unblockcomment, context=Qt.WidgetShortcut)
        self.register_shortcut(unblockcomment_action, context="Editor",
                               name="Unblockcomment")

        # ----------------------------------------------------------------------
        # The following action shortcuts are hard-coded in CodeEditor
        # keyPressEvent handler (the shortcut is here only to inform user):
        # (context=Qt.WidgetShortcut -> disable shortcut for other widgets)
        self.indent_action = create_action(self,
                _("Indent"), "Tab", icon=ima.icon('indent'),
                tip=_("Indent current line or selection"),
                triggered=self.indent, context=Qt.WidgetShortcut)
        self.unindent_action = create_action(self,
                _("Unindent"), "Shift+Tab", icon=ima.icon('unindent'),
                tip=_("Unindent current line or selection"),
                triggered=self.unindent, context=Qt.WidgetShortcut)

        self.text_uppercase_action = create_action(self,
                _("Toggle Uppercase"), icon=ima.icon('toggle_uppercase'),
                tip=_("Change to uppercase current line or selection"),
                triggered=self.text_uppercase, context=Qt.WidgetShortcut)
        self.register_shortcut(self.text_uppercase_action, context="Editor",
                               name="transform to uppercase")

        self.text_lowercase_action = create_action(self,
                _("Toggle Lowercase"), icon=ima.icon('toggle_lowercase'),
                tip=_("Change to lowercase current line or selection"),
                triggered=self.text_lowercase, context=Qt.WidgetShortcut)
        self.register_shortcut(self.text_lowercase_action, context="Editor",
                               name="transform to lowercase")
        # ----------------------------------------------------------------------

        self.win_eol_action = create_action(self,
                           _("Carriage return and line feed (Windows)"),
                           toggled=lambda checked: self.toggle_eol_chars('nt', checked))
        self.linux_eol_action = create_action(self,
                           _("Line feed (UNIX)"),
                           toggled=lambda checked: self.toggle_eol_chars('posix', checked))
        self.mac_eol_action = create_action(self,
                           _("Carriage return (Mac)"),
                           toggled=lambda checked: self.toggle_eol_chars('mac', checked))
        eol_action_group = QActionGroup(self)
        eol_actions = (self.win_eol_action, self.linux_eol_action,
                       self.mac_eol_action)
        add_actions(eol_action_group, eol_actions)
        eol_menu = QMenu(_("Convert end-of-line characters"), self)
        add_actions(eol_menu, eol_actions)

        trailingspaces_action = create_action(
            self,
            _("Remove trailing spaces"),
            triggered=self.remove_trailing_spaces)

        formatter = CONF.get(
            'completions',
            ('provider_configuration', 'lsp', 'values', 'formatting'),
            '')
        self.formatting_action = create_action(
            self,
            _('Format file or selection with {0}').format(
                formatter.capitalize()),
            shortcut=CONF.get_shortcut('editor', 'autoformatting'),
            context=Qt.WidgetShortcut,
            triggered=self.format_document_or_selection)
        self.formatting_action.setEnabled(False)

        # Checkable actions
        showblanks_action = self._create_checkable_action(
            _("Show blank spaces"), 'blank_spaces', 'set_blanks_enabled')

        scrollpastend_action = self._create_checkable_action(
            _("Scroll past the end"), 'scroll_past_end',
            'set_scrollpastend_enabled')

        showindentguides_action = self._create_checkable_action(
            _("Show indent guides"), 'indent_guides', 'set_indent_guides')

        showcodefolding_action = self._create_checkable_action(
            _("Show code folding"), 'code_folding', 'set_code_folding_enabled')

        show_classfunc_dropdown_action = self._create_checkable_action(
            _("Show selector for classes and functions"),
            'show_class_func_dropdown', 'set_classfunc_dropdown_visible')

        show_codestyle_warnings_action = self._create_checkable_action(
            _("Show code style warnings"), 'pycodestyle',)

        show_docstring_warnings_action = self._create_checkable_action(
            _("Show docstring style warnings"), 'pydocstyle')

        underline_errors = self._create_checkable_action(
            _("Underline errors and warnings"),
            'underline_errors', 'set_underline_errors_enabled')

        self.checkable_actions = {
                'blank_spaces': showblanks_action,
                'scroll_past_end': scrollpastend_action,
                'indent_guides': showindentguides_action,
                'code_folding': showcodefolding_action,
                'show_class_func_dropdown': show_classfunc_dropdown_action,
                'pycodestyle': show_codestyle_warnings_action,
                'pydocstyle': show_docstring_warnings_action,
                'underline_errors': underline_errors}

        fixindentation_action = create_action(self, _("Fix indentation"),
                      tip=_("Replace tab characters by space characters"),
                      triggered=self.fix_indentation)

        gotoline_action = create_action(self, _("Go to line..."),
                                        icon=ima.icon('gotoline'),
                                        triggered=self.go_to_line,
                                        context=Qt.WidgetShortcut)
        self.register_shortcut(gotoline_action, context="Editor",
                               name="Go to line")

        workdir_action = create_action(self,
                _("Set console working directory"),
                icon=ima.icon('DirOpenIcon'),
                tip=_("Set current console (and file explorer) working "
                            "directory to current script directory"),
                triggered=self.__set_workdir)

        self.max_recent_action = create_action(self,
            _("Maximum number of recent files..."),
            triggered=self.change_max_recent_files)
        self.clear_recent_action = create_action(self,
            _("Clear this list"), tip=_("Clear recent files list"),
            triggered=self.clear_recent_files)

        # Fixes spyder-ide/spyder#6055.
        # See: https://bugreports.qt.io/browse/QTBUG-8596
        self.tab_navigation_actions = []
        if sys.platform == 'darwin':
            self.go_to_next_file_action = create_action(
                self,
                _("Go to next file"),
                shortcut=CONF.get_shortcut('editor', 'go to previous file'),
                triggered=self.go_to_next_file,
            )
            self.go_to_previous_file_action = create_action(
                self,
                _("Go to previous file"),
                shortcut=CONF.get_shortcut('editor', 'go to next file'),
                triggered=self.go_to_previous_file,
            )
            self.register_shortcut(
                self.go_to_next_file_action,
                context="Editor",
                name="Go to next file",
            )
            self.register_shortcut(
                self.go_to_previous_file_action,
                context="Editor",
                name="Go to previous file",
            )
            self.tab_navigation_actions = [
                MENU_SEPARATOR,
                self.go_to_previous_file_action,
                self.go_to_next_file_action,
            ]

        # ---- File menu/toolbar construction ----
        self.recent_file_menu = QMenu(_("Open &recent"), self)
        self.recent_file_menu.aboutToShow.connect(self.update_recent_file_menu)

        from spyder.plugins.mainmenu.api import (
            ApplicationMenus, FileMenuSections)
        # New Section
        self.main.mainmenu.add_item_to_application_menu(
            self.new_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.New,
            before_section=FileMenuSections.Restart)
        # Open section
        open_actions = [
            self.open_action,
            self.open_last_closed_action,
            self.recent_file_menu,
        ]
        for open_action in open_actions:
            self.main.mainmenu.add_item_to_application_menu(
                open_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Open,
                before_section=FileMenuSections.Restart)
        # Save section
        save_actions = [
            self.save_action,
            self.save_all_action,
            save_as_action,
            save_copy_as_action,
            self.revert_action,
        ]
        for save_action in save_actions:
            self.main.mainmenu.add_item_to_application_menu(
                save_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Save,
                before_section=FileMenuSections.Restart)
        # Print
        print_actions = [
            print_preview_action,
            self.print_action,
        ]
        for print_action in print_actions:
            self.main.mainmenu.add_item_to_application_menu(
                print_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Print,
                before_section=FileMenuSections.Restart)
        # Close
        close_actions = [
            self.close_action,
            self.close_all_action
        ]
        for close_action in close_actions:
            self.main.mainmenu.add_item_to_application_menu(
                close_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Close,
                before_section=FileMenuSections.Restart)
        # Navigation
        if sys.platform == 'darwin':
            self.main.mainmenu.add_item_to_application_menu(
                self.tab_navigation_actions,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Navigation,
                before_section=FileMenuSections.Restart)

        file_toolbar_actions = ([self.new_action, self.open_action,
                                self.save_action, self.save_all_action] +
                                self.main.file_toolbar_actions)

        self.main.file_toolbar_actions += file_toolbar_actions

        # ---- Find menu/toolbar construction ----
        self.main.search_menu_actions = [find_action,
                                         find_next_action,
                                         find_previous_action,
                                         replace_action]
        self.main.search_toolbar_actions = [find_action,
                                            find_next_action,
                                            replace_action]

        # ---- Edit menu/toolbar construction ----
        self.edit_menu_actions = [self.toggle_comment_action,
                                  blockcomment_action, unblockcomment_action,
                                  self.indent_action, self.unindent_action,
                                  self.text_uppercase_action,
                                  self.text_lowercase_action]
        self.main.edit_menu_actions += [MENU_SEPARATOR] + self.edit_menu_actions

        # ---- Search menu/toolbar construction ----
        self.main.search_menu_actions += [gotoline_action]

        # ---- Run menu/toolbar construction ----
        run_menu_actions = [run_action, run_cell_action,
                            run_cell_advance_action,
                            re_run_last_cell_action, MENU_SEPARATOR,
                            run_selected_action, re_run_action,
                            configure_action, MENU_SEPARATOR]
        self.main.run_menu_actions += run_menu_actions
        run_toolbar_actions = [run_action, run_cell_action,
                               run_cell_advance_action, run_selected_action]
        self.main.run_toolbar_actions += run_toolbar_actions

        # ---- Debug menu/toolbar construction ----
        # NOTE: 'list_breakpoints' is used by the breakpoints
        # plugin to add its "List breakpoints" action to this
        # menu
        debug_menu_actions = [
            self.debug_action,
            self.debug_cell_action,
            self.debug_next_action,
            self.debug_step_action,
            self.debug_return_action,
            self.debug_continue_action,
            self.debug_exit_action,
            MENU_SEPARATOR,
            set_clear_breakpoint_action,
            set_cond_breakpoint_action,
            clear_all_breakpoints_action,
            'list_breakpoints',
            MENU_SEPARATOR,
            self.winpdb_action
        ]
        self.main.debug_menu_actions += debug_menu_actions
        debug_toolbar_actions = [
            self.debug_action,
            self.debug_next_action,
            self.debug_step_action,
            self.debug_return_action,
            self.debug_continue_action,
            self.debug_exit_action
        ]
        self.main.debug_toolbar_actions += debug_toolbar_actions

        # ---- Source menu/toolbar construction ----
        source_menu_actions = [
            showblanks_action,
            scrollpastend_action,
            showindentguides_action,
            showcodefolding_action,
            show_classfunc_dropdown_action,
            show_codestyle_warnings_action,
            show_docstring_warnings_action,
            underline_errors,
            MENU_SEPARATOR,
            self.todo_list_action,
            self.warning_list_action,
            self.previous_warning_action,
            self.next_warning_action,
            MENU_SEPARATOR,
            self.previous_edit_cursor_action,
            self.previous_cursor_action,
            self.next_cursor_action,
            MENU_SEPARATOR,
            eol_menu,
            trailingspaces_action,
            fixindentation_action,
            self.formatting_action
        ]
        self.main.source_menu_actions += source_menu_actions

        # ---- Dock widget and file dependent actions ----
        self.dock_toolbar_actions = (
            file_toolbar_actions +
            [MENU_SEPARATOR] +
            run_toolbar_actions +
            [MENU_SEPARATOR] +
            debug_toolbar_actions
        )
        self.pythonfile_dependent_actions = [
            run_action,
            configure_action,
            set_clear_breakpoint_action,
            set_cond_breakpoint_action,
            self.debug_action,
            self.debug_cell_action,
            run_selected_action,
            run_cell_action,
            run_cell_advance_action,
            re_run_last_cell_action,
            blockcomment_action,
            unblockcomment_action,
            self.winpdb_action
        ]
        self.cythonfile_compatible_actions = [run_action, configure_action]
        self.file_dependent_actions = (
            self.pythonfile_dependent_actions +
            [
                self.save_action,
                save_as_action,
                save_copy_as_action,
                print_preview_action,
                self.print_action,
                self.save_all_action,
                gotoline_action,
                workdir_action,
                self.close_action,
                self.close_all_action,
                self.toggle_comment_action,
                self.revert_action,
                self.indent_action,
                self.unindent_action
            ]
        )
        self.stack_menu_actions = [gotoline_action, workdir_action]

        return self.file_dependent_actions

    def update_pdb_state(self, state, last_step):
        """
        Enable/disable debugging actions and handle pdb state change.

        Some examples depending on the debugging state:
        self.debug_action.setEnabled(not state)
        self.debug_cell_action.setEnabled(not state)
        self.debug_next_action.setEnabled(state)
        self.debug_step_action.setEnabled(state)
        self.debug_return_action.setEnabled(state)
        self.debug_continue_action.setEnabled(state)
        self.debug_exit_action.setEnabled(state)
        """
        current_editor = self.get_current_editor()
        if current_editor:
            current_editor.update_debugger_panel_state(state, last_step)

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.restore_scrollbar_position.connect(
            self.restore_scrollbar_position)
        self.main.console.sig_edit_goto_requested.connect(self.load)
        self.exec_in_extconsole.connect(self.main.execute_in_external_console)
        self.redirect_stdio.connect(self.main.redirect_internalshell_stdio)
        self.main.completions.sig_language_completions_available.connect(
            self.register_completion_capabilities)
        self.main.completions.sig_open_file.connect(self.load)
        self.main.completions.sig_editor_rpc.connect(self._rpc_call)
        self.main.completions.sig_stop_completions.connect(
            self.stop_completion_services)

        self.sig_file_opened_closed_or_updated.connect(
            self.main.completions.file_opened_closed_or_updated)

        if self.main.outlineexplorer is not None:
            self.set_outlineexplorer(self.main.outlineexplorer)

        self.add_dockwidget()
        self.update_pdb_state(False, {})

        # Add modes to switcher
        self.switcher_manager = EditorSwitcherManager(
            self,
            self.main.switcher,
            lambda: self.get_current_editor(),
            lambda: self.get_current_editorstack(),
            section=self.get_plugin_title())

    def update_source_menu(self, options, **kwargs):
        option_names = [opt[-1] if isinstance(opt, tuple) else opt
                        for opt in options]
        named_options = dict(zip(option_names, options))
        for name, action in self.checkable_actions.items():
            if name in named_options:
                section = 'completions'
                if name == 'underline_errors':
                    section = 'editor'

                opt = named_options[name]
                state = self.get_option(opt, section=section)

                # Avoid triggering the action when this action changes state
                # See: spyder-ide/spyder#9915
                action.blockSignals(True)
                action.setChecked(state)
                action.blockSignals(False)

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font()
        color_scheme = self.get_color_scheme()
        for editorstack in self.editorstacks:
            editorstack.set_default_font(font, color_scheme)
            completion_size = CONF.get('main', 'completion/size')
            for finfo in editorstack.data:
                comp_widget = finfo.editor.completion_widget
                kite_call_to_action = finfo.editor.kite_call_to_action
                comp_widget.setup_appearance(completion_size, font)
                kite_call_to_action.setFont(font)

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
                kite_call_to_action = finfo.editor.kite_call_to_action
                comp_widget.setParent(ancestor)
                kite_call_to_action.setParent(ancestor)

    def _create_checkable_action(self, text, conf_name, method=''):
        """Helper function to create a checkable action.

        Args:
            text (str): Text to be displayed in the action.
            conf_name (str): configuration setting associated with the
                action
            method (str): name of EditorStack class that will be used
                to update the changes in each editorstack.
        """
        def toogle(checked):
            self.switch_to_plugin()
            self._toggle_checkable_action(checked, method, conf_name)

        action = create_action(self, text, toggled=toogle)
        action.blockSignals(True)

        if conf_name not in ['pycodestyle', 'pydocstyle']:
            action.setChecked(self.get_option(conf_name))
        else:
            opt = CONF.get(
                'completions',
                ('provider_configuration', 'lsp', 'values', conf_name),
                False
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
            self.set_option(conf_name, checked)
        else:
            if conf_name in ('pycodestyle', 'pydocstyle'):
                CONF.set(
                    'completions',
                    ('provider_configuration', 'lsp', 'values', conf_name),
                    checked)
            completions = self.main.completions
            completions.after_configuration_update([])

    #------ Focus tabwidget
    def __get_focused_editorstack(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, EditorStack):
            return fwidget
        else:
            for editorstack in self.editorstacks:
                if editorstack.isAncestorOf(fwidget):
                    return editorstack

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

    # ------ Handling editorstacks
    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        self.register_widget_shortcuts(editorstack)

        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            self.set_last_focused_editorstack(self, editorstack)
            editorstack.set_closable(len(self.editorstacks) > 1)
            if self.outlineexplorer is not None:
                editorstack.set_outlineexplorer(
                    self.outlineexplorer.get_widget())
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

        editorstack.set_io_actions(self.new_action, self.open_action,
                                   self.save_action, self.revert_action)
        editorstack.set_tempfile_path(self.TEMPFILE_PATH)

        settings = (
            ('set_todolist_enabled',                'todo_list'),
            ('set_blanks_enabled',                  'blank_spaces'),
            ('set_underline_errors_enabled',        'underline_errors'),
            ('set_scrollpastend_enabled',           'scroll_past_end'),
            ('set_linenumbers_enabled',             'line_numbers'),
            ('set_edgeline_enabled',                'edge_line'),
            ('set_edgeline_columns',                'edge_line_columns'),
            ('set_indent_guides',                   'indent_guides'),
            ('set_code_folding_enabled',            'code_folding'),
            ('set_focus_to_editor',                 'focus_to_editor'),
            ('set_run_cell_copy',                   'run_cell_copy'),
            ('set_close_parentheses_enabled',       'close_parentheses'),
            ('set_close_quotes_enabled',            'close_quotes'),
            ('set_add_colons_enabled',              'add_colons'),
            ('set_auto_unindent_enabled',           'auto_unindent'),
            ('set_indent_chars',                    'indent_chars'),
            ('set_tab_stop_width_spaces',           'tab_stop_width_spaces'),
            ('set_wrap_enabled',                    'wrap'),
            ('set_tabmode_enabled',                 'tab_always_indent'),
            ('set_stripmode_enabled',               'strip_trailing_spaces_on_modify'),
            ('set_intelligent_backspace_enabled',   'intelligent_backspace'),
            ('set_automatic_completions_enabled',   'automatic_completions'),
            ('set_automatic_completions_after_chars',
             'automatic_completions_after_chars'),
            ('set_automatic_completions_after_ms',
             'automatic_completions_after_ms'),
            ('set_completions_hint_enabled',        'completions_hint'),
            ('set_completions_hint_after_ms',
             'completions_hint_after_ms'),
            ('set_highlight_current_line_enabled',  'highlight_current_line'),
            ('set_highlight_current_cell_enabled',  'highlight_current_cell'),
            ('set_occurrence_highlighting_enabled',  'occurrence_highlighting'),
            ('set_occurrence_highlighting_timeout',  'occurrence_highlighting/timeout'),
            ('set_checkeolchars_enabled',           'check_eol_chars'),
            ('set_tabbar_visible',                  'show_tab_bar'),
            ('set_classfunc_dropdown_visible',      'show_class_func_dropdown'),
            ('set_always_remove_trailing_spaces',   'always_remove_trailing_spaces'),
            ('set_remove_trailing_newlines',        'always_remove_trailing_newlines'),
            ('set_add_newline',                     'add_newline'),
            ('set_convert_eol_on_save',             'convert_eol_on_save'),
            ('set_convert_eol_on_save_to',          'convert_eol_on_save_to'),
                    )

        for method, setting in settings:
            getattr(editorstack, method)(self.get_option(setting))

        editorstack.set_help_enabled(CONF.get('help', 'connect/editor'))

        hover_hints = CONF.get(
            'completions',
            ('provider_configuration', 'lsp', 'values',
                'enable_hover_hints'),
            True
        )

        format_on_save = CONF.get(
            'completions',
            ('provider_configuration', 'lsp', 'values', 'format_on_save'),
            False
        )

        editorstack.set_hover_hints_enabled(hover_hints)
        editorstack.set_format_on_save(format_on_save)
        color_scheme = self.get_color_scheme()
        editorstack.set_default_font(self.get_font(), color_scheme)

        editorstack.starting_long_process.connect(self.starting_long_process)
        editorstack.ending_long_process.connect(self.ending_long_process)

        # Redirect signals
        editorstack.sig_option_changed.connect(self.sig_option_changed)
        editorstack.redirect_stdio.connect(
                                 lambda state: self.redirect_stdio.emit(state))
        editorstack.exec_in_extconsole.connect(
                                    lambda text, option:
                                    self.exec_in_extconsole.emit(text, option))
        editorstack.run_cell_in_ipyclient.connect(
            lambda code, cell_name, filename, run_cell_copy:
            self.run_cell_in_ipyclient.emit(code, cell_name, filename,
                                            run_cell_copy))
        editorstack.debug_cell_in_ipyclient.connect(
            lambda code, cell_name, filename, run_cell_copy:
            self.debug_cell_in_ipyclient.emit(code, cell_name, filename,
                                              run_cell_copy))
        editorstack.update_plugin_title.connect(
                                   lambda: self.sig_update_plugin_title.emit())
        editorstack.editor_focus_changed.connect(self.save_focused_editorstack)
        editorstack.editor_focus_changed.connect(self.main.plugin_focus_changed)
        editorstack.editor_focus_changed.connect(self.sig_editor_focus_changed)
        editorstack.zoom_in.connect(lambda: self.zoom(1))
        editorstack.zoom_out.connect(lambda: self.zoom(-1))
        editorstack.zoom_reset.connect(lambda: self.zoom(0))
        editorstack.sig_open_file.connect(self.report_open_file)
        editorstack.sig_new_file.connect(lambda s: self.new(text=s))
        editorstack.sig_new_file[()].connect(self.new)
        editorstack.sig_close_file.connect(self.close_file_in_all_editorstacks)
        editorstack.sig_close_file.connect(self.remove_file_cursor_history)
        editorstack.file_saved.connect(self.file_saved_in_editorstack)
        editorstack.file_renamed_in_data.connect(
                                      self.file_renamed_in_data_in_editorstack)
        editorstack.opened_files_list_changed.connect(
                                                self.opened_files_list_changed)
        editorstack.active_languages_stats.connect(
            self.update_active_languages)
        editorstack.sig_go_to_definition.connect(
            lambda fname, line, col: self.load(
                fname, line, start_column=col))
        editorstack.sig_perform_completion_request.connect(
            self.send_completion_request)
        editorstack.todo_results_changed.connect(self.todo_results_changed)
        editorstack.update_code_analysis_actions.connect(
            self.update_code_analysis_actions)
        editorstack.update_code_analysis_actions.connect(
            self.update_todo_actions)
        editorstack.refresh_file_dependent_actions.connect(
                                           self.refresh_file_dependent_actions)
        editorstack.refresh_save_all_action.connect(self.refresh_save_all_action)
        editorstack.sig_refresh_eol_chars.connect(self.refresh_eol_chars)
        editorstack.sig_refresh_formatting.connect(self.refresh_formatting)
        editorstack.sig_breakpoints_saved.connect(self.breakpoints_saved)
        editorstack.text_changed_at.connect(self.text_changed_at)
        editorstack.current_file_changed.connect(self.current_file_changed)
        editorstack.plugin_load.connect(self.load)
        editorstack.plugin_load[()].connect(self.load)
        editorstack.edit_goto.connect(self.load)
        editorstack.sig_save_as.connect(self.save_as)
        editorstack.sig_prev_edit_pos.connect(self.go_to_last_edit_location)
        editorstack.sig_prev_cursor.connect(self.go_to_previous_cursor_position)
        editorstack.sig_next_cursor.connect(self.go_to_next_cursor_position)
        editorstack.sig_prev_warning.connect(self.go_to_previous_warning)
        editorstack.sig_next_warning.connect(self.go_to_next_warning)
        editorstack.sig_save_bookmark.connect(self.save_bookmark)
        editorstack.sig_load_bookmark.connect(self.load_bookmark)
        editorstack.sig_save_bookmarks.connect(self.save_bookmarks)
        editorstack.sig_help_requested.connect(self.sig_help_requested)

        # Register editorstack's autosave component with plugin's autosave
        # component
        self.autosave.register_autosave_for_stack(editorstack.autosave)

    def unregister_editorstack(self, editorstack):
        """Removing editorstack only if it's not the last remaining"""
        self.remove_last_focused_editorstack(editorstack)
        if len(self.editorstacks) > 1:
            index = self.editorstacks.index(editorstack)
            self.editorstacks.pop(index)
            return True
        else:
            # editorstack was not removed!
            return False

    def clone_editorstack(self, editorstack):
        editorstack.clone_from(self.editorstacks[0])
        for finfo in editorstack.data:
            self.register_widget_shortcuts(finfo.editor)

    @Slot(str, str)
    def close_file_in_all_editorstacks(self, editorstack_id_str, filename):
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.blockSignals(True)
                index = editorstack.get_index_from_filename(filename)
                editorstack.close_file(index, force=True)
                editorstack.blockSignals(False)

    @Slot(str, str, str)
    def file_saved_in_editorstack(self, editorstack_id_str,
                                  original_filename, filename):
        """A file was saved in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.file_saved_in_other_editorstack(original_filename,
                                                            filename)

    @Slot(str, str, str)
    def file_renamed_in_data_in_editorstack(self, editorstack_id_str,
                                            original_filename, filename):
        """A file was renamed in data in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.rename_in_data(original_filename, filename)

    def call_all_editorstacks(self, method, *args, **kwargs):
        """Call a method with arguments on all editorstacks."""
        for editorstack in self.editorstacks:
            method = getattr(editorstack, method)
            method(*args, **kwargs)

    #------ Handling editor windows
    def setup_other_windows(self):
        """Setup toolbars and menus for 'New window' instances"""
        # TODO: All the actions here should be taken from
        # the MainMenus plugin
        file_menu_actions = self.main.mainmenu.get_application_menu(
            ApplicationMenus.File).get_actions()
        tools_menu_actions = self.main.mainmenu.get_application_menu(
            ApplicationMenus.Tools).get_actions()
        help_menu_actions = self.main.mainmenu.get_application_menu(
            ApplicationMenus.Help).get_actions()

        self.toolbar_list = ((_("File toolbar"), "file_toolbar",
                              self.main.file_toolbar_actions),
                             (_("Run toolbar"), "run_toolbar",
                              self.main.run_toolbar_actions),
                             (_("Debug toolbar"), "debug_toolbar",
                              self.main.debug_toolbar_actions))

        self.menu_list = ((_("&File"), file_menu_actions),
                          (_("&Edit"), self.main.edit_menu_actions),
                          (_("&Search"), self.main.search_menu_actions),
                          (_("Sour&ce"), self.main.source_menu_actions),
                          (_("&Run"), self.main.run_menu_actions),
                          (_("&Tools"), tools_menu_actions),
                          (_("&View"), []),
                          (_("&Help"), help_menu_actions))
        # Create pending new windows:
        for layout_settings in self.editorwindows_to_be_created:
            win = self.create_new_window()
            win.set_layout_settings(layout_settings)

    def switch_to_plugin(self):
        """
        Reimplemented method to deactivate shortcut when
        opening a new window.
        """
        if not self.editorwindows:
            super(Editor, self).switch_to_plugin()

    def create_new_window(self):
        oe_options = self.outlineexplorer.get_widget().get_options()
        window = EditorMainWindow(
            self, self.stack_menu_actions, self.toolbar_list, self.menu_list,
            outline_explorer_options=oe_options)
        window.add_toolbars_to_menu("&View", window.get_toolbars())
        window.load_toolbars()
        window.resize(self.size())
        window.show()
        window.editorwidget.editorsplitter.editorstack.new_window = True
        self.register_editorwindow(window)
        window.destroyed.connect(lambda: self.unregister_editorwindow(window))
        return window

    def register_editorwindow(self, window):
        self.editorwindows.append(window)

    def unregister_editorwindow(self, window):
        self.editorwindows.pop(self.editorwindows.index(window))


    #------ Accessors
    def get_filenames(self):
        return [finfo.filename for finfo in self.editorstacks[0].data]

    def get_filename_index(self, filename):
        return self.editorstacks[0].has_filename(filename)

    def get_current_editorstack(self, editorwindow=None):
        if self.editorstacks is not None:
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

    def set_path(self):
        for finfo in self.editorstacks[0].data:
            finfo.path = self.main.get_spyder_pythonpath()

    #------ Refresh methods
    def refresh_file_dependent_actions(self):
        """Enable/disable file dependent actions
        (only if dockwidget is visible)"""
        if self.dockwidget and self.dockwidget.isVisible():
            enable = self.get_current_editor() is not None
            for action in self.file_dependent_actions:
                action.setEnabled(enable)

    def refresh_save_all_action(self):
        """Enable 'Save All' if there are files to be saved"""
        editorstack = self.get_current_editorstack()
        if editorstack:
            state = any(finfo.editor.document().isModified() or finfo.newly_created
                        for finfo in editorstack.data)
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
            icon = ima.icon('error') if error else ima.icon('warning')
            slot = lambda _checked, _l=line_number: self.load(filename, goto=_l)
            action = create_action(self, text=text, icon=icon, triggered=slot)
            self.warning_menu.addAction(action)

    def update_todo_menu(self):
        """Update todo list menu"""
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        self.todo_menu.clear()
        filename = self.get_current_filename()
        for text, line0 in results:
            icon = ima.icon('todo')
            slot = lambda _checked, _l=line0: self.load(filename, goto=_l)
            action = create_action(self, text=text, icon=icon, triggered=slot)
            self.todo_menu.addAction(action)
        self.update_todo_actions()

    def todo_results_changed(self):
        """
        Synchronize todo results between editorstacks
        Refresh todo list navigation buttons
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
        formatter = CONF.get(
            'completions',
            ('provider_configuration', 'lsp', 'values', 'formatting'),
            '')
        self.formatting_action.setText(
            _('Format file or selection with {0}').format(
                formatter.capitalize()))

    #------ Slots
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
                if action in self.cythonfile_compatible_actions:
                    enable = cython_enable
                else:
                    enable = python_enable
                if action is self.winpdb_action:
                    action.setEnabled(enable and WINPDB_PATH is not None)
                else:
                    action.setEnabled(enable)
            self.sig_file_opened_closed_or_updated.emit(
                self.get_current_filename(), self.get_current_language())

    def update_code_analysis_actions(self):
        """Update actions in the warnings menu."""
        editor = self.get_current_editor()
        # To fix an error at startup
        if editor is None:
            return
        results = editor.get_current_warnings()
        # Update code analysis actions
        state = results is not None and len(results)
        for action in (self.warning_list_action, self.previous_warning_action,
                       self.next_warning_action):
            if state is not None:
                action.setEnabled(state)

    def update_todo_actions(self):
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        state = (self.get_option('todo_list') and
                 results is not None and len(results))
        if state is not None:
            self.todo_list_action.setEnabled(state)

    @Slot(set)
    def update_active_languages(self, languages):
        self.main.completions.update_client_status(languages)


    # ------ Bookmarks
    def save_bookmarks(self, filename, bookmarks):
        """Receive bookmark changes and save them."""
        filename = to_text_string(filename)
        bookmarks = to_text_string(bookmarks)
        filename = osp.normpath(osp.abspath(filename))
        bookmarks = eval(bookmarks)
        save_bookmarks(filename, bookmarks)

    #------ File I/O
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
        if len(self.recent_files) > self.get_option('max_recent_files'):
            self.recent_files.pop(-1)

    def _clone_file_everywhere(self, finfo):
        """Clone file (*src_editor* widget) in all editorstacks
        Cloning from the first editorstack in which every single new editor
        is created (when loading or creating a new file)"""
        for editorstack in self.editorstacks[1:]:
            editor = editorstack.clone_editor_from(finfo, set_current=False)
            self.register_widget_shortcuts(editor)


    @Slot()
    @Slot(str)
    def new(self, fname=None, editorstack=None, text=None):
        """
        Create a new file - Untitled

        fname=None --> fname will be 'untitledXX.py' but do not create file
        fname=<basestring> --> create file
        """
        # If no text is provided, create default content
        empty = False
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

        create_fname = lambda n: to_text_string(_("untitled")) + ("%d.py" % n)
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

            if self.main.projects.get_active_project() is not None:
                basedir = self.main.projects.get_active_project_path()
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
        finfo.path = self.main.get_spyder_pythonpath()
        self._clone_file_everywhere(finfo)
        current_editor = current_es.set_current_filename(finfo.filename)
        self.register_widget_shortcuts(current_editor)
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
        self.recent_file_menu.clear()
        if recent_files:
            for fname in recent_files:
                action = create_action(
                    self, fname,
                    icon=ima.get_icon_by_extension_or_type(
                        fname, scale_factor=1.0),
                    triggered=self.load)
                action.setData(to_qvariant(fname))
                self.recent_file_menu.addAction(action)
        self.clear_recent_action.setEnabled(len(recent_files) > 0)
        add_actions(self.recent_file_menu, (None, self.max_recent_action,
                                            self.clear_recent_action))

    @Slot()
    def clear_recent_files(self):
        """Clear recent files list"""
        self.recent_files = []

    @Slot()
    def change_max_recent_files(self):
        "Change max recent files entries"""
        editorstack = self.get_current_editorstack()
        mrf, valid = QInputDialog.getInt(editorstack, _('Editor'),
                               _('Maximum number of recent files'),
                               self.get_option('max_recent_files'), 1, 35)
        if valid:
            self.set_option('max_recent_files', mrf)

    @Slot()
    @Slot(str)
    @Slot(str, int, str)
    @Slot(str, int, str, object)
    def load(self, filenames=None, goto=None, word='',
             editorwindow=None, processevents=True, start_column=None,
             end_column=None, set_focus=True, add_where='end'):
        """
        Load a text file
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
        # Switch to editor before trying to load a file
        try:
            self.switch_to_plugin()
        except AttributeError:
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

            self.redirect_stdio.emit(False)
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

            self.redirect_stdio.emit(True)

            if filenames:
                filenames = [osp.normpath(fname) for fname in filenames]
            else:
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
        elif (self.dockwidget and not self._ismaximized
              and not self.dockwidget.isAncestorOf(focus_widget)
              and not isinstance(focus_widget, CodeEditor)):
            self.switch_to_plugin()

        def _convert(fname):
            fname = osp.abspath(encoding.to_unicode_from_fs(fname))
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
                # -- Not a valid filename:
                if not osp.isfile(filename):
                    continue
                # --
                current_es = self.get_current_editorstack(editorwindow)
                # Creating the editor widget in the first editorstack
                # (the one that can't be destroyed), then cloning this
                # editor widget in all other editorstacks:
                finfo = self.editorstacks[0].load(
                    filename, set_current=False, add_where=add_where,
                    processevents=processevents)
                finfo.path = self.main.get_spyder_pythonpath()
                self._clone_file_everywhere(finfo)
                current_editor = current_es.set_current_filename(filename,
                                                                 focus=focus)
                current_editor.debugger.load_breakpoints()
                current_editor.set_bookmarks(load_bookmarks(filename))
                self.register_widget_shortcuts(current_editor)
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
            else:
                # processevents is false only when calling from debugging
                current_editor.sig_debug_stop.emit(goto[index])
                current_sw = self.main.ipyconsole.get_current_shellwidget()
                current_sw.sig_prompt_ready.connect(
                    current_editor.sig_debug_stop[()].emit)
                current_pdb_state = self.main.ipyconsole.get_pdb_state()
                pdb_last_step = self.main.ipyconsole.get_pdb_last_step()
                self.update_pdb_state(current_pdb_state, pdb_last_step)

    @Slot()
    def print_file(self):
        """Print current file"""
        editor = self.get_current_editor()
        filename = self.get_current_filename()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=self.get_font())
        printDialog = QPrintDialog(printer, editor)
        if editor.has_selected_text():
            printDialog.setOption(QAbstractPrintDialog.PrintSelection, True)
        self.redirect_stdio.emit(False)
        answer = printDialog.exec_()
        self.redirect_stdio.emit(True)
        if answer == QDialog.Accepted:
            self.starting_long_process(_("Printing..."))
            printer.setDocName(filename)
            editor.print_(printer)
            self.ending_long_process()

    @Slot()
    def print_preview(self):
        """Print preview for current file"""
        from qtpy.QtPrintSupport import QPrintPreviewDialog

        editor = self.get_current_editor()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=self.get_font())
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowFlags(Qt.Window)
        preview.paintRequested.connect(lambda printer: editor.print_(printer))
        self.redirect_stdio.emit(False)
        preview.exec_()
        self.redirect_stdio.emit(True)

    def can_close_file(self, filename=None):
        """
        Check if a file can be closed taking into account debugging state.
        """
        if not CONF.get('ipython_console', 'pdb_prevent_closing'):
            return True
        debugging = self.main.ipyconsole.get_pdb_state()
        last_pdb_step = self.main.ipyconsole.get_pdb_last_step()
        can_close = True
        if debugging and 'fname' in last_pdb_step and filename:
            if osp.normcase(last_pdb_step['fname']) == osp.normcase(filename):
                can_close = False
                self.sig_file_debug_message_requested.emit()
        elif debugging:
            can_close = False
            self.sig_file_debug_message_requested.emit()
        return can_close

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
        """Fnd next slot"""
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
        """ Reopens the last closed tab."""
        editorstack = self.get_current_editorstack()
        last_closed_files = editorstack.get_last_closed_files()
        if (len(last_closed_files) > 0):
            file_to_open = last_closed_files[0]
            last_closed_files.remove(file_to_open)
            editorstack.set_last_closed_files(last_closed_files)
            self.load(file_to_open)

    #------ Explorer widget
    def close_file_from_name(self, filename):
        """Close file from its name"""
        filename = osp.abspath(to_text_string(filename))
        index = self.editorstacks[0].has_filename(filename)
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

    def renamed(self, source, dest):
        """
        Propagate file rename to editor stacks and autosave component.

        This function is called when a file is renamed in the file explorer
        widget or the project explorer. The file may not be opened in the
        editor.
        """
        filename = osp.abspath(to_text_string(source))
        index = self.editorstacks[0].has_filename(filename)
        if index is not None:
            for editorstack in self.editorstacks:
                editorstack.rename_in_data(filename,
                                           new_filename=to_text_string(dest))
            self.editorstacks[0].autosave.file_renamed(
                filename, to_text_string(dest))

    def renamed_tree(self, source, dest):
        """Directory was renamed in file explorer or in project explorer."""
        dirname = osp.abspath(to_text_string(source))
        tofile = to_text_string(dest)
        for fname in self.get_filenames():
            if osp.abspath(fname).startswith(dirname):
                new_filename = fname.replace(dirname, tofile)
                self.renamed(source=fname, dest=new_filename)

    #------ Source code
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
    def go_to_next_todo(self):
        self.switch_to_plugin()
        editor = self.get_current_editor()
        position = editor.go_to_next_todo()
        filename = self.get_current_filename()
        line, column = editor.get_cursor_line_column()
        self.add_cursor_position_to_history(filename, position, line, column)

    @Slot()
    def go_to_next_warning(self):
        self.switch_to_plugin()
        editor = self.get_current_editor()
        position = editor.go_to_next_warning()
        filename = self.get_current_filename()
        line, column = editor.get_cursor_line_column()
        self.add_cursor_position_to_history(filename, position, line, column)

    @Slot()
    def go_to_previous_warning(self):
        self.switch_to_plugin()
        editor = self.get_current_editor()
        position = editor.go_to_previous_warning()
        filename = self.get_current_filename()
        line, column = editor.get_cursor_line_column()
        self.add_cursor_position_to_history(filename, position, line, column)

    @Slot()
    def run_winpdb(self):
        """Run winpdb to debug current file"""
        if self.save():
            fname = self.get_current_filename()
            runconf = get_run_configuration(fname)
            if runconf is None:
                args = []
                wdir = None
            else:
                args = runconf.get_arguments().split()
                wdir = runconf.get_working_directory()
            # Handle the case where wdir comes back as an empty string
            # when the working directory dialog checkbox is unchecked.
            # (subprocess "cwd" default is None, so empty str
            # must be changed to None in this case.)
            programs.run_program(WINPDB_PATH, [fname] + args, cwd=wdir or None)

    def toggle_eol_chars(self, os_name, checked):
        if checked:
            editor = self.get_current_editor()
            if self.__set_eol_chars:
                self.switch_to_plugin()
                editor.set_eol_chars(sourcecode.get_eol_chars_from_os_name(os_name))

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

    #------ Cursor position history management
    def update_cursorpos_actions(self):
        self.previous_edit_cursor_action.setEnabled(
                                        self.last_edit_cursor_pos is not None)
        self.previous_cursor_action.setEnabled(
               self.cursor_pos_index is not None and self.cursor_pos_index > 0)
        self.next_cursor_action.setEnabled(self.cursor_pos_index is not None \
                    and self.cursor_pos_index < len(self.cursor_pos_history)-1)

    def add_cursor_position_to_history(self, filename, position, line, column,
                                       fc=False):
        if self.__ignore_cursor_position:
            return
        for index, (fname, pos, c_line, c_col) in enumerate(
                self.cursor_pos_history):
            if fname == filename:
                if pos == position or pos == 0 or line == c_line:
                    if fc:
                        self.cursor_pos_history[index] = (filename, position,
                                                          line, column)
                        self.cursor_pos_index = index
                        self.update_cursorpos_actions()
                        return
                    else:
                        if self.cursor_pos_index >= index:
                            self.cursor_pos_index -= 1
                        self.cursor_pos_history.pop(index)
                        break
        if self.cursor_pos_index is not None:
            self.cursor_pos_history = \
                        self.cursor_pos_history[:self.cursor_pos_index+1]
        self.cursor_pos_history.append((filename, position, line, column))
        self.cursor_pos_index = len(self.cursor_pos_history)-1
        self.update_cursorpos_actions()

    def text_changed_at(self, filename, position):
        self.last_edit_cursor_pos = (to_text_string(filename), position)

    def current_file_changed(self, filename, position, line, column):
        self.add_cursor_position_to_history(to_text_string(filename), position,
                                            line, column, fc=True)

        # Hide any open tooltips
        current_stack = self.get_current_editorstack()
        if current_stack is not None:
            current_stack.hide_tooltip()

        # Update debugging state
        if self.main.ipyconsole is not None:
            pdb_state = self.main.ipyconsole.get_pdb_state()
            pdb_last_step = self.main.ipyconsole.get_pdb_last_step()
            self.update_pdb_state(pdb_state, pdb_last_step)

    def current_editor_cursor_changed(self, line, column):
        """Handles the change of the cursor inside the current editor."""
        code_editor = self.get_current_editor()
        filename = code_editor.filename
        position = code_editor.get_position('cursor')
        line, column = code_editor.get_cursor_line_column()
        self.add_cursor_position_to_history(
            to_text_string(filename), position, line, column, fc=True)

    def remove_file_cursor_history(self, id, filename):
        """Remove the cursor history of a file if the file is closed."""
        new_history = []
        for i, (cur_filename, pos, line, column) in enumerate(
                self.cursor_pos_history):
            if cur_filename == filename:
                if i < self.cursor_pos_index:
                    self.cursor_pos_index = self.cursor_pos_index - 1
            else:
                new_history.append((cur_filename, pos, line, column))
        self.cursor_pos_history = new_history

    @Slot()
    def go_to_last_edit_location(self):
        if self.last_edit_cursor_pos is not None:
            filename, position = self.last_edit_cursor_pos
            if not osp.isfile(filename):
                self.last_edit_cursor_pos = None
                return
            else:
                self.load(filename)
                editor = self.get_current_editor()
                if position < editor.document().characterCount():
                    editor.set_cursor_position(position)

    def __move_cursor_position(self, index_move):
        """
        Move the cursor position forward or backward in the cursor
        position history by the specified index increment.
        """
        if self.cursor_pos_index is None:
            return
        filename, _position, _line, _column = (
            self.cursor_pos_history[self.cursor_pos_index])
        cur_line, cur_col = self.get_current_editor().get_cursor_line_column()
        self.cursor_pos_history[self.cursor_pos_index] = (
            filename, self.get_current_editor().get_position('cursor'),
            cur_line, cur_col)
        self.__ignore_cursor_position = True
        old_index = self.cursor_pos_index
        self.cursor_pos_index = min(len(self.cursor_pos_history) - 1,
                                    max(0, self.cursor_pos_index + index_move))
        filename, position, line, col = (
            self.cursor_pos_history[self.cursor_pos_index])
        filenames = self.get_current_editorstack().get_filenames()
        if not osp.isfile(filename) and filename not in filenames:
            self.cursor_pos_history.pop(self.cursor_pos_index)
            if self.cursor_pos_index <= old_index:
                old_index -= 1
            self.cursor_pos_index = old_index
        else:
            self.load(filename)
            editor = self.get_current_editor()
            if position < editor.document().characterCount():
                editor.set_cursor_position(position)
        self.__ignore_cursor_position = False
        self.update_cursorpos_actions()

    @Slot()
    def go_to_previous_cursor_position(self):
        self.switch_to_plugin()
        self.__move_cursor_position(-1)

    @Slot()
    def go_to_next_cursor_position(self):
        self.switch_to_plugin()
        self.__move_cursor_position(1)

    @Slot()
    def go_to_line(self, line=None):
        """Open 'go to line' dialog"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.go_to_line(line)

    @Slot()
    def set_or_clear_breakpoint(self):
        """Set/Clear breakpoint"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            self.switch_to_plugin()
            editorstack.set_or_clear_breakpoint()

    @Slot()
    def set_or_edit_conditional_breakpoint(self):
        """Set/Edit conditional breakpoint"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            self.switch_to_plugin()
            editorstack.set_or_edit_conditional_breakpoint()

    @Slot()
    def clear_all_breakpoints(self):
        """Clear breakpoints in all files"""
        self.switch_to_plugin()
        clear_all_breakpoints()
        self.breakpoints_saved.emit()
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            for data in editorstack.data:
                data.editor.debugger.clear_breakpoints()
        self.refresh_plugin()

    def clear_breakpoint(self, filename, lineno):
        """Remove a single breakpoint"""
        clear_breakpoint(filename, lineno)
        self.breakpoints_saved.emit()
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            index = self.is_file_opened(filename)
            if index is not None:
                editorstack.data[index].editor.debugger.toogle_breakpoint(
                        lineno)

    def stop_debugging(self):
        """Stop debugging"""
        self.main.ipyconsole.stop_debugging()

    def debug_command(self, command):
        """Debug actions"""
        self.switch_to_plugin()
        self.main.ipyconsole.pdb_execute_command(command)
        focus_widget = self.main.ipyconsole.get_focus_widget()
        if focus_widget:
            focus_widget.setFocus()

    #------ Run Python script
    @Slot()
    def edit_run_configurations(self):
        dialog = RunConfigDialog(self)
        dialog.size_change.connect(lambda s: self.set_dialog_size(s))
        if self.dialog_size is not None:
            dialog.resize(self.dialog_size)
        fname = osp.abspath(self.get_current_filename())
        dialog.setup(fname)
        if dialog.exec_():
            fname = dialog.file_to_run
            if fname is not None:
                self.load(fname)
                self.run_file()

    @Slot()
    def run_file(self, debug=False):
        """Run script inside current interpreter or in a new one"""
        editorstack = self.get_current_editorstack()

        editor = self.get_current_editor()
        fname = osp.abspath(self.get_current_filename())

        # Get fname's dirname before we escape the single and double
        # quotes. Fixes spyder-ide/spyder#6771.
        dirname = osp.dirname(fname)

        # Escape single and double quotes in fname and dirname.
        # Fixes spyder-ide/spyder#2158.
        fname = fname.replace("'", r"\'").replace('"', r'\"')
        dirname = dirname.replace("'", r"\'").replace('"', r'\"')

        runconf = get_run_configuration(fname)
        if runconf is None:
            dialog = RunConfigOneDialog(self)
            dialog.size_change.connect(lambda s: self.set_dialog_size(s))
            if self.dialog_size is not None:
                dialog.resize(self.dialog_size)
            dialog.setup(fname)
            if CONF.get('run', 'open_at_least_once',
                        not running_under_pytest()):
                # Open Run Config dialog at least once: the first time
                # a script is ever run in Spyder, so that the user may
                # see it at least once and be conscious that it exists
                show_dlg = True
                CONF.set('run', 'open_at_least_once', False)
            else:
                # Open Run Config dialog only
                # if ALWAYS_OPEN_FIRST_RUN_OPTION option is enabled
                show_dlg = CONF.get('run', ALWAYS_OPEN_FIRST_RUN_OPTION)
            if show_dlg and not dialog.exec_():
                return
            runconf = dialog.get_configuration()

        args = runconf.get_arguments()
        python_args = runconf.get_python_arguments()
        interact = runconf.interact
        post_mortem = runconf.post_mortem
        current = runconf.current
        systerm = runconf.systerm
        clear_namespace = runconf.clear_namespace
        console_namespace = runconf.console_namespace

        if runconf.file_dir:
            wdir = dirname
        elif runconf.cw_dir:
            wdir = ''
        elif osp.isdir(runconf.dir):
            wdir = runconf.dir
        else:
            wdir = ''

        python = True  # Note: in the future, it may be useful to run
        # something in a terminal instead of a Python interp.
        self.__last_ec_exec = (fname, wdir, args, interact, debug,
                               python, python_args, current, systerm,
                               post_mortem, clear_namespace,
                               console_namespace)
        self.re_run_file(save_new_files=False)
        if not interact and not debug:
            # If external console dockwidget is hidden, it will be
            # raised in top-level and so focus will be given to the
            # current external shell automatically
            # (see SpyderPluginWidget.visibility_changed method)
            editor.setFocus()

    def set_dialog_size(self, size):
        self.dialog_size = size

    @Slot()
    def debug_file(self):
        """Debug current script"""
        self.switch_to_plugin()
        current_editor = self.get_current_editor()
        if current_editor is not None:
            current_editor.sig_debug_start.emit()
        self.run_file(debug=True)

    @Slot()
    def re_run_file(self, save_new_files=True):
        """Re-run last script"""
        if self.get_option('save_all_before_run'):
            all_saved = self.save_all(save_new_files=save_new_files)
            if all_saved is not None and not all_saved:
                return
        if self.__last_ec_exec is None:
            return
        (fname, wdir, args, interact, debug,
         python, python_args, current, systerm,
         post_mortem, clear_namespace,
         console_namespace) = self.__last_ec_exec
        if not systerm:
            self.run_in_current_ipyclient.emit(fname, wdir, args,
                                               debug, post_mortem,
                                               current, clear_namespace,
                                               console_namespace)
        else:
            self.main.open_external_console(fname, wdir, args, interact,
                                            debug, python, python_args,
                                            systerm, post_mortem)

    @Slot()
    def run_selection(self):
        """Run selection or current line in external console"""
        editorstack = self.get_current_editorstack()
        editorstack.run_selection()

    @Slot()
    def run_cell(self):
        """Run current cell"""
        editorstack = self.get_current_editorstack()
        editorstack.run_cell()

    @Slot()
    def run_cell_and_advance(self):
        """Run current cell and advance to the next one"""
        editorstack = self.get_current_editorstack()
        editorstack.run_cell_and_advance()

    @Slot()
    def debug_cell(self):
        '''Debug Current cell.'''
        editorstack = self.get_current_editorstack()
        editorstack.debug_cell()

    @Slot()
    def re_run_last_cell(self):
        """Run last executed cell."""
        editorstack = self.get_current_editorstack()
        editorstack.re_run_last_cell()

    # ------ Code bookmarks
    @Slot(int)
    def save_bookmark(self, slot_num):
        """Save current line and position as bookmark."""
        bookmarks = CONF.get('editor', 'bookmarks')
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
        bookmarks = CONF.get('editor', 'bookmarks')
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

    #------ Zoom in/out/reset
    def zoom(self, factor):
        """Zoom in/out/reset"""
        editor = self.get_current_editorstack().get_current_editor()
        if factor == 0:
            font = self.get_font()
            editor.set_font(font)
        else:
            font = editor.font()
            size = font.pointSize() + factor
            if size > 0:
                font.setPointSize(size)
                editor.set_font(font)
        editor.update_tab_stop_width_spaces()

    #------ Options
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        if self.editorstacks is not None:
            # --- syntax highlight and text rendering settings
            color_scheme_n = 'color_scheme_name'
            color_scheme_o = self.get_color_scheme()
            currentline_n = 'highlight_current_line'
            currentline_o = self.get_option(currentline_n)
            currentcell_n = 'highlight_current_cell'
            currentcell_o = self.get_option(currentcell_n)
            occurrence_n = 'occurrence_highlighting'
            occurrence_o = self.get_option(occurrence_n)
            occurrence_timeout_n = 'occurrence_highlighting/timeout'
            occurrence_timeout_o = self.get_option(occurrence_timeout_n)
            focus_to_editor_n = 'focus_to_editor'
            focus_to_editor_o = self.get_option(focus_to_editor_n)

            for editorstack in self.editorstacks:
                if color_scheme_n in options:
                    editorstack.set_color_scheme(color_scheme_o)
                if currentline_n in options:
                    editorstack.set_highlight_current_line_enabled(
                                                                currentline_o)
                if currentcell_n in options:
                    editorstack.set_highlight_current_cell_enabled(
                                                                currentcell_o)
                if occurrence_n in options:
                    editorstack.set_occurrence_highlighting_enabled(occurrence_o)
                if occurrence_timeout_n in options:
                    editorstack.set_occurrence_highlighting_timeout(
                                                           occurrence_timeout_o)
                if focus_to_editor_n in options:
                    editorstack.set_focus_to_editor(focus_to_editor_o)

            # --- everything else
            tabbar_n = 'show_tab_bar'
            tabbar_o = self.get_option(tabbar_n)
            classfuncdropdown_n = 'show_class_func_dropdown'
            classfuncdropdown_o = self.get_option(classfuncdropdown_n)
            linenb_n = 'line_numbers'
            linenb_o = self.get_option(linenb_n)
            blanks_n = 'blank_spaces'
            blanks_o = self.get_option(blanks_n)
            scrollpastend_n = 'scroll_past_end'
            scrollpastend_o = self.get_option(scrollpastend_n)
            edgeline_n = 'edge_line'
            edgeline_o = self.get_option(edgeline_n)
            edgelinecols_n = 'edge_line_columns'
            edgelinecols_o = self.get_option(edgelinecols_n)
            wrap_n = 'wrap'
            wrap_o = self.get_option(wrap_n)
            indentguides_n = 'indent_guides'
            indentguides_o = self.get_option(indentguides_n)
            codefolding_n = 'code_folding'
            codefolding_o = self.get_option(codefolding_n)
            tabindent_n = 'tab_always_indent'
            tabindent_o = self.get_option(tabindent_n)
            stripindent_n = 'strip_trailing_spaces_on_modify'
            stripindent_o = self.get_option(stripindent_n)
            ibackspace_n = 'intelligent_backspace'
            ibackspace_o = self.get_option(ibackspace_n)
            autocompletions_n = 'automatic_completions'
            autocompletions_o = self.get_option(autocompletions_n)
            completionshint_n = 'completions_hint'
            completionshint_o = self.get_option(completionshint_n)
            removetrail_n = 'always_remove_trailing_spaces'
            removetrail_o = self.get_option(removetrail_n)
            add_newline_n = 'add_newline'
            add_newline_o = self.get_option(add_newline_n)
            removetrail_newlines_n = 'always_remove_trailing_newlines'
            removetrail_newlines_o = self.get_option(removetrail_newlines_n)
            converteol_n = 'convert_eol_on_save'
            converteol_o = self.get_option(converteol_n)
            converteolto_n = 'convert_eol_on_save_to'
            converteolto_o = self.get_option(converteolto_n)
            runcellcopy_n = 'run_cell_copy'
            runcellcopy_o = self.get_option(runcellcopy_n)
            closepar_n = 'close_parentheses'
            closepar_o = self.get_option(closepar_n)
            close_quotes_n = 'close_quotes'
            close_quotes_o = self.get_option(close_quotes_n)
            add_colons_n = 'add_colons'
            add_colons_o = self.get_option(add_colons_n)
            autounindent_n = 'auto_unindent'
            autounindent_o = self.get_option(autounindent_n)
            indent_chars_n = 'indent_chars'
            indent_chars_o = self.get_option(indent_chars_n)
            tab_stop_width_spaces_n = 'tab_stop_width_spaces'
            tab_stop_width_spaces_o = self.get_option(tab_stop_width_spaces_n)
            help_n = 'connect_to_oi'
            help_o = CONF.get('help', 'connect/editor')
            todo_n = 'todo_list'
            todo_o = self.get_option(todo_n)

            finfo = self.get_current_finfo()


            for editorstack in self.editorstacks:
                # Checkable options
                if blanks_n in options:
                    editorstack.set_blanks_enabled(blanks_o)
                if scrollpastend_n in options:
                    editorstack.set_scrollpastend_enabled(scrollpastend_o)
                if indentguides_n in options:
                    editorstack.set_indent_guides(indentguides_o)
                if codefolding_n in options:
                    editorstack.set_code_folding_enabled(codefolding_o)
                if classfuncdropdown_n in options:
                    editorstack.set_classfunc_dropdown_visible(
                        classfuncdropdown_o)

                if tabbar_n in options:
                    editorstack.set_tabbar_visible(tabbar_o)
                if linenb_n in options:
                    editorstack.set_linenumbers_enabled(linenb_o,
                                                        current_finfo=finfo)
                if autocompletions_n in options:
                    editorstack.set_automatic_completions_enabled(
                        autocompletions_o)
                if completionshint_n in options:
                    editorstack.set_completions_hint_enabled(completionshint_o)
                if edgeline_n in options:
                    editorstack.set_edgeline_enabled(edgeline_o)
                if edgelinecols_n in options:
                    editorstack.set_edgeline_columns(edgelinecols_o)
                if wrap_n in options:
                    editorstack.set_wrap_enabled(wrap_o)
                if tabindent_n in options:
                    editorstack.set_tabmode_enabled(tabindent_o)
                if stripindent_n in options:
                    editorstack.set_stripmode_enabled(stripindent_o)
                if ibackspace_n in options:
                    editorstack.set_intelligent_backspace_enabled(ibackspace_o)
                if removetrail_n in options:
                    editorstack.set_always_remove_trailing_spaces(removetrail_o)
                if add_newline_n in options:
                    editorstack.set_add_newline(add_newline_o)
                if removetrail_newlines_n in options:
                    editorstack.set_remove_trailing_newlines(
                        removetrail_newlines_o)
                if converteol_n in options:
                    editorstack.set_convert_eol_on_save(converteol_o)
                if converteolto_n in options:
                    editorstack.set_convert_eol_on_save_to(converteolto_o)
                if runcellcopy_n in options:
                    editorstack.set_run_cell_copy(runcellcopy_o)
                if closepar_n in options:
                    editorstack.set_close_parentheses_enabled(closepar_o)
                if close_quotes_n in options:
                    editorstack.set_close_quotes_enabled(close_quotes_o)
                if add_colons_n in options:
                    editorstack.set_add_colons_enabled(add_colons_o)
                if autounindent_n in options:
                    editorstack.set_auto_unindent_enabled(autounindent_o)
                if indent_chars_n in options:
                    editorstack.set_indent_chars(indent_chars_o)
                if tab_stop_width_spaces_n in options:
                    editorstack.set_tab_stop_width_spaces(tab_stop_width_spaces_o)
                if help_n in options:
                    editorstack.set_help_enabled(help_o)
                if todo_n in options:
                    editorstack.set_todolist_enabled(todo_o,
                                                     current_finfo=finfo)

            for name, action in self.checkable_actions.items():
                if name in options:
                    # Avoid triggering the action when this action changes state
                    action.blockSignals(True)
                    state = self.get_option(name)
                    action.setChecked(state)
                    action.blockSignals(False)
                    # See: spyder-ide/spyder#9915

            # Multiply by 1000 to convert seconds to milliseconds
            self.autosave.interval = (
                    self.get_option('autosave_interval') * 1000)
            self.autosave.enabled = self.get_option('autosave_enabled')

            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            if finfo is not None:
                if todo_n in options and todo_o:
                    finfo.run_todo_finder()

    # --- Open files
    def get_open_filenames(self):
        """Get the list of open files in the current stack"""
        editorstack = self.editorstacks[0]
        filenames = []
        filenames += [finfo.filename for finfo in editorstack.data]
        return filenames

    def set_open_filenames(self):
        """
        Set the recent opened files on editor based on active project.

        If no project is active, then editor filenames are saved, otherwise
        the opened filenames are stored in the project config info.
        """
        if self.projects is not None:
            if not self.projects.get_active_project():
                filenames = self.get_open_filenames()
                self.set_option('filenames', filenames)

    def setup_open_files(self, close_previous_files=True):
        """
        Open the list of saved files per project.

        Also open any files that the user selected in the recovery dialog.
        """
        self.set_create_new_file_if_empty(False)
        active_project_path = None
        if self.projects is not None:
            active_project_path = self.projects.get_active_project_path()

        if active_project_path:
            filenames = self.projects.get_project_filenames()
        else:
            filenames = self.get_option('filenames', default=[])

        if close_previous_files:
            self.close_all_files()

        all_filenames = self.autosave.recover_files_to_open + filenames
        if all_filenames and any([osp.isfile(f) for f in all_filenames]):
            layout = self.get_option('layout_settings', None)
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
                    self.load(filenames[index], goto=clines[index], set_focus=True)
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
                    # Finally we load any recovered files at the end of the tabbar,
                    # while keeping focus on the last focused file.
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
                win_layout = self.get_option('windows_layout_settings', [])
                if win_layout:
                    for layout_settings in win_layout:
                        self.editorwindows_to_be_created.append(
                            layout_settings)
                self.set_last_focused_editorstack(self, self.editorstacks[0])
        else:
            self.__load_temp_file()
        self.set_create_new_file_if_empty(True)

    def save_open_files(self):
        """Save the list of open files"""
        self.set_option('filenames', self.get_open_filenames())

    def set_create_new_file_if_empty(self, value):
        """Change the value of create_new_file_if_empty"""
        for editorstack in self.editorstacks:
            editorstack.create_new_file_if_empty = value

    # --- File Menu actions (Mac only)
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

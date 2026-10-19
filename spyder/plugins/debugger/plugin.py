# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Debugger Plugin."""

# Standard library imports
from concurrent.futures import Future
import os.path as osp
from typing import List, Optional

# Third-party imports
from qtpy.QtCore import Qt, Slot

# Local imports
from spyder.api.plugins import (
    ExposedCallError,
    Plugins,
    SpyderDockablePlugin,
    current_caller,
    expose,
)
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.shellconnect.mixins import ShellConnectPluginMixin
from spyder.api.translations import _
from spyder.plugins.debugger.confpage import DebuggerConfigPage
from spyder.plugins.debugger.utils.breakpointsmanager import (
    BreakpointsManager,
    _load_all_breakpoints,
    clear_all_breakpoints,
    clear_breakpoint,
    load_breakpoints,
    save_breakpoints,
)
from spyder.plugins.debugger.panels.debuggerpanel import DebuggerPanel
from spyder.plugins.debugger.widgets.main_widget import (
    DebuggerBreakpointActions, DebuggerWidget, DebuggerWidgetActions)
from spyder.plugins.editor.utils.editor import get_file_language
from spyder.plugins.editor.utils.languages import ALL_LANGUAGES
from spyder.plugins.ipythonconsole.api import IPythonConsolePyConfiguration
from spyder.plugins.ipythonconsole.utils.execution import (
    DEFAULT_EXECUTE_TIMEOUT,
    PdbCommandCollector,
    build_run_line,
    check_ready,
    get_pdb_location,
    run_code,
)
from spyder.plugins.ipythonconsole.utils.scheduler import (
    describe_caller,
    get_scheduler,
)
from spyder.plugins.mainmenu.api import ApplicationMenus, DebugMenuSections
from spyder.plugins.run.api import (
    RunConfiguration, ExtendedRunExecutionParameters, RunExecutor, run_execute,
    RunContext, RunResult)
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.ipythonconsole.widgets.run_conf import IPythonConfigOptions
from spyder.plugins.editor.api.run import CellRun, SelectionRun


class Debugger(SpyderDockablePlugin, ShellConnectPluginMixin, RunExecutor):
    """Debugger plugin."""

    NAME = 'debugger'
    REQUIRES = [
        Plugins.IPythonConsole,
        Plugins.MainMenu,
        Plugins.Preferences,
        Plugins.Run,
        Plugins.Toolbar,
    ]
    OPTIONAL = [Plugins.Editor]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = DebuggerWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = DebuggerConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    def __init__(self, parent, configuration=None):
        SpyderDockablePlugin.__init__(self, parent, configuration)

        # Combined with ShellConnectPluginMixin and RunExecutor via multiple
        # inheritance; set up their state here since SpyderDockablePlugin's
        # __init__ doesn't reach them (and RunExecutor.__init__ would also
        # re-init the QObject part).
        ShellConnectPluginMixin.__init__(self)
        self.setup_run_executor()

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Debugger')

    @staticmethod
    def get_description():
        return _('View, explore and navigate stack frames while debugging.')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('debug')

    def on_initialize(self):
        widget = self.get_widget()
        widget.sig_pdb_state_changed.connect(
            self._update_current_codeeditor_pdb_state)
        widget.sig_toggle_breakpoints.connect(self._set_or_clear_breakpoint)
        widget.sig_toggle_conditional_breakpoints.connect(
            self._set_or_edit_conditional_breakpoint)
        widget.sig_clear_all_breakpoints.connect(self.clear_all_breakpoints)
        widget.sig_load_pdb_file.connect(self._load_pdb_file_in_editor)
        widget.sig_clear_breakpoint.connect(self.clear_breakpoint)
        widget.sig_switch_to_plugin_requested.connect(self.switch_to_plugin)

        self.python_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'py',
            'contexts': [
                {'name': 'File'},
                {'name': 'Cell'},
                {'name': 'Selection'},
            ]
        }

        self.ipython_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'ipy',
            'contexts': [
                {'name': 'File'},
                {'name': 'Cell'},
                {'name': 'Selection'},
            ]
        }

        self.pyw_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'pyw',
            'contexts': [
                {'name': 'File'},
                {'name': 'Cell'},
                {'name': 'Selection'},
            ]
        }

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'pyw',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'py',
                'context': {'name': 'Cell'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'Cell'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'pyw',
                'context': {'name': 'Cell'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'py',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'pyw',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
        ]

    def on_mainwindow_visible(self):
        self.get_widget().update_splitter_widths(self.get_widget().width())

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)
        run.register_executor_configuration(self, self.executor_configuration)

        run.create_run_in_executor_button(
            RunContext.File,
            self.NAME,
            text=_("&Debug file"),
            tip=_("Debug file"),
            icon=self.create_icon('debug'),
            shortcut_context="_",
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Debug,
                "section": DebugMenuSections.StartDebug,
                "before_section": DebugMenuSections.ControlDebug
            },
            add_to_toolbar={
                "toolbar": ApplicationToolbars.Debug,
                "before": DebuggerWidgetActions.Next,
            },
            shortcut_widget_context=Qt.ApplicationShortcut,
        )

        run.create_run_in_executor_button(
            RunContext.Cell,
            self.NAME,
            text=_("Debug cell"),
            tip=_("Debug cell"),
            icon=self.create_icon('debug_cell'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Debug,
                "section": DebugMenuSections.StartDebug,
                "before_section": DebugMenuSections.ControlDebug
            },
            add_to_toolbar={
                "toolbar": ApplicationToolbars.Debug,
                "before": DebuggerWidgetActions.Next,
            },
        )

        run.create_run_in_executor_button(
            RunContext.Selection,
            self.NAME,
            text=_("Debug the current line or selection"),
            tip=_("Debug the current line or selection"),
            icon=self.create_icon('debug_selection'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Debug,
                "section": DebugMenuSections.StartDebug,
                "before_section": DebugMenuSections.ControlDebug
            },
            add_to_toolbar={
                "toolbar": ApplicationToolbars.Debug,
                "before": DebuggerWidgetActions.Next,
            },
        )

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration
        )
        run.destroy_run_in_executor_button(RunContext.File, self.NAME)
        run.destroy_run_in_executor_button(RunContext.Cell, self.NAME)
        run.destroy_run_in_executor_button(RunContext.Selection, self.NAME)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()

        for run_config in [
            self.python_editor_run_configuration,
            self.ipython_editor_run_configuration,
            self.pyw_editor_run_configuration
        ]:
            editor.add_supported_run_configuration(run_config)

        # The editor is available, connect signals.
        widget.sig_edit_goto.connect(editor.load)
        editor.sig_codeeditor_created.connect(self._add_codeeditor)
        editor.sig_codeeditor_changed.connect(self._update_codeeditor)
        editor.sig_codeeditor_deleted.connect(self._remove_codeeditor)

        # Apply shortcuts to editor and add actions to pythonfile list
        editor_shortcuts = [
            DebuggerBreakpointActions.ToggleBreakpoint,
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
            DebuggerBreakpointActions.ShowBreakpointsTable,
        ]
        for name in editor_shortcuts:
            action = self.get_action(name)
            # TODO: This should be handled differently?
            editor.get_widget().pythonfile_dependent_actions += [action]

        editor.add_panel(DebuggerPanel)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()

        for run_config in [
            self.python_editor_run_configuration,
            self.ipython_editor_run_configuration,
            self.pyw_editor_run_configuration
        ]:
            editor.remove_supported_run_configuration(run_config)

        widget.sig_edit_goto.disconnect(editor.load)

        editor.sig_codeeditor_created.disconnect(self._add_codeeditor)
        editor.sig_codeeditor_changed.disconnect(self._update_codeeditor)
        editor.sig_codeeditor_deleted.disconnect(self._remove_codeeditor)

        # Remove editor actions
        editor_shortcuts = [
            DebuggerBreakpointActions.ToggleBreakpoint,
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
            DebuggerBreakpointActions.ShowBreakpointsTable,
        ]
        for name in editor_shortcuts:
            action = self.get_action(name)
            if action in editor.get_widget().pythonfile_dependent_actions:
                editor.get_widget().pythonfile_dependent_actions.remove(action)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        # ControlDebug section
        for action in [DebuggerWidgetActions.Next,
                       DebuggerWidgetActions.Step,
                       DebuggerWidgetActions.Return,
                       DebuggerWidgetActions.Continue,
                       DebuggerWidgetActions.Stop]:
            mainmenu.add_item_to_application_menu(
                self.get_action(action),
                menu_id=ApplicationMenus.Debug,
                section=DebugMenuSections.ControlDebug,
                before_section=DebugMenuSections.EditBreakpoints)

        # Breakpoints section
        for action in [DebuggerBreakpointActions.ToggleBreakpoint,
                       DebuggerBreakpointActions.ToggleConditionalBreakpoint,
                       DebuggerBreakpointActions.ClearAllBreakpoints,
                       DebuggerBreakpointActions.ShowBreakpointsTable]:
            mainmenu.add_item_to_application_menu(
                self.get_action(action),
                menu_id=ApplicationMenus.Debug,
                section=DebugMenuSections.EditBreakpoints)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        names = [
            DebuggerWidgetActions.Next,
            DebuggerWidgetActions.Step,
            DebuggerWidgetActions.Return,
            DebuggerWidgetActions.Continue,
            DebuggerWidgetActions.Stop,
            DebuggerBreakpointActions.ToggleBreakpoint,
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
            DebuggerBreakpointActions.ClearAllBreakpoints,
            DebuggerBreakpointActions.ShowBreakpointsTable,
        ]
        for name in names:
            mainmenu.remove_item_from_application_menu(
                name,
                menu_id=ApplicationMenus.Debug
            )

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.create_application_toolbar(
            ApplicationToolbars.Debug, _("Debug toolbar")
        )

        for action_id in [
            DebuggerWidgetActions.Next,
            DebuggerWidgetActions.Step,
            DebuggerWidgetActions.Return,
            DebuggerWidgetActions.Continue,
            DebuggerWidgetActions.Stop,
        ]:
            toolbar.add_item_to_application_toolbar(
                self.get_action(action_id),
                toolbar_id=ApplicationToolbars.Debug,
            )

        debug_toolbar = toolbar.get_application_toolbar(
            ApplicationToolbars.Debug
        )
        debug_toolbar.sig_is_rendered.connect(
            self.get_widget().on_debug_toolbar_rendered
        )

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)

        for action_id in [
            DebuggerWidgetActions.Next,
            DebuggerWidgetActions.Step,
            DebuggerWidgetActions.Return,
            DebuggerWidgetActions.Continue,
            DebuggerWidgetActions.Stop,
        ]:
            toolbar.remove_item_from_application_toolbar(
                action_id,
                toolbar_id=ApplicationToolbars.Debug,
            )

        toolbar.remove_application_toolbar(ApplicationToolbars.Debug)

    # ---- Private API
    # ------------------------------------------------------------------------
    def _load_pdb_file_in_editor(self, fname, lineno):
        """Load file using processevents."""
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return

        # Prevent keyboard input from accidentally entering the
        # editor during repeated, rapid entry of debugging commands.
        editor.load(fname, lineno, processevents=False)

    def _is_python_editor(self, codeeditor):
        """Check if the editor is a python editor."""
        if codeeditor.filename is None:
            return False
        txt = codeeditor.get_text_with_eol()
        language = get_file_language(codeeditor.filename, txt)
        return language.lower() in ALL_LANGUAGES["Python"]

    def _connect_codeeditor(self, codeeditor):
        """Connect a code editor."""
        codeeditor.breakpoints_manager = BreakpointsManager(codeeditor)
        codeeditor.breakpoints_manager.sig_breakpoints_saved.connect(
            self.get_widget().sig_breakpoints_saved
        )

    def _disconnect_codeeditor(self, codeeditor):
        """Disconnect a code editor."""
        codeeditor.breakpoints_manager.sig_breakpoints_saved.disconnect(
            self.get_widget().sig_breakpoints_saved
        )
        codeeditor.breakpoints_manager.debugger_panel.setVisible(False)
        codeeditor.breakpoints_manager = None

    @Slot(str)
    def _filename_changed(self, filename):
        """Change filename."""
        codeeditor = self._get_editor_for_filename(filename)
        if codeeditor is None:
            return

        if codeeditor.breakpoints_manager is None:
            # Was not a python editor
            if self._is_python_editor(codeeditor):
                self._connect_codeeditor(codeeditor)
        else:
            # Was a python editor
            if self._is_python_editor(codeeditor):
                codeeditor.breakpoints_manager.set_filename(filename)
            else:
                self._disconnect_codeeditor(codeeditor)

    @Slot(object)
    def _add_codeeditor(self, codeeditor):
        """
        Add a new codeeditor.
        """
        codeeditor.sig_filename_changed.connect(self._filename_changed)
        codeeditor.breakpoints_manager = None
        if self._is_python_editor(codeeditor):
            self._connect_codeeditor(codeeditor)

    @Slot(object)
    def _remove_codeeditor(self, codeeditor):
        """
        Remove a codeeditor.
        """
        codeeditor.sig_filename_changed.disconnect(self._filename_changed)
        if codeeditor.breakpoints_manager is not None:
            self._disconnect_codeeditor(codeeditor)

    @Slot(object)
    def _update_codeeditor(self, codeeditor):
        """
        Focus codeeditor has changed.
        """
        if (
            codeeditor.filename is None or
            codeeditor.breakpoints_manager is None
        ):
            return

        # Update debugging state
        widget = self.get_widget()
        pdb_state = widget.get_pdb_state()
        filename, lineno = widget.get_pdb_last_step()
        codeeditor.breakpoints_manager.update_pdb_state(
            pdb_state, filename, lineno)

    @Slot(bool)
    def _update_current_codeeditor_pdb_state(self, pdb_state):
        """
        The pdb state has changed.
        """
        try:
            codeeditor = self._get_current_editor()
            if codeeditor is None or codeeditor.breakpoints_manager is None:
                return
            filename, line_number = self.get_widget().get_pdb_last_step()
            codeeditor.breakpoints_manager.update_pdb_state(
                pdb_state, filename, line_number)
        except RuntimeError:
            pass

    def _get_current_editor(self):
        """
        Get current codeeditor.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None
        return editor.get_current_editor()

    def _get_shellwidget(self, console_id):
        """Get the shellwidget of a console for outside callers."""
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        shellwidget = ipyconsole.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        return shellwidget

    def _get_editor_for_filename(self, filename):
        """Get editor for filename."""
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None

        return editor.get_codeeditor_for_filename(filename)

    def _get_current_editorstack(self):
        """
        Get current editorstack.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None
        return editor.get_current_editorstack()

    @Slot()
    def _set_or_clear_breakpoint(self):
        """Toggle breakpoint."""
        codeeditor = self._get_current_editor()
        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return
        codeeditor.breakpoints_manager.toogle_breakpoint()

    @Slot()
    def _set_or_edit_conditional_breakpoint(self):
        """Set/edit conditional breakpoint."""
        codeeditor = self._get_current_editor()
        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return
        codeeditor.breakpoints_manager.toogle_breakpoint(
            edit_condition=True)

    # ---- Public API
    # ------------------------------------------------------------------------

    @Slot()
    def clear_all_breakpoints(self):
        """Clear breakpoints in all files"""
        clear_all_breakpoints()
        self.get_widget().sig_breakpoints_saved.emit()

        editorstack = self._get_current_editorstack()
        if editorstack is not None:
            for data in editorstack.data:
                if data.editor.breakpoints_manager is not None:
                    data.editor.breakpoints_manager.clear_breakpoints()

    @Slot(str, int)
    def clear_breakpoint(self, filename, lineno):
        """Remove a single breakpoint"""
        clear_breakpoint(filename, lineno)
        self.get_widget().sig_breakpoints_saved.emit()

        codeeditor = self._get_editor_for_filename(filename)

        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return None

        codeeditor.breakpoints_manager.toogle_breakpoint(lineno)

    def can_close_file(self, filename=None):
        """
        Check if a file can be closed taking into account debugging state.
        """
        if not self.get_conf('pdb_prevent_closing'):
            return True

        widget = self.get_widget()

        debugging = widget.get_pdb_state()
        if not debugging:
            return True

        pdb_fname, __ = widget.get_pdb_last_step()

        if pdb_fname and filename:
            if osp.normcase(pdb_fname) == osp.normcase(filename):
                widget.print_debug_file_msg()
                return False
            return True

        widget.print_debug_file_msg()
        return False

    # ---- For outside callers (e.g. AI agents)
    @expose
    def start_debugging(
        self,
        filename: str,
        args: str = "",
        console_id: Optional[str] = None,
        timeout: float = DEFAULT_EXECUTE_TIMEOUT,
    ) -> Future:
        """
        Start debugging a Python file in an IPython console, like pressing
        Ctrl+F5 in Spyder. The debugger stops at the first breakpoint of the
        file if it has any (see set_breakpoint) or else at its first line.
        Then use debug_command to step through the code and inspect it.

        Parameters
        ----------
        filename : str
            Absolute path of the file. If it's open in the Editor, its current
            contents are debugged, including unsaved changes.
        args : str, optional
            Command line arguments for the file.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        timeout : float, optional
            Seconds to wait for the console to be free and the debugger to
            stop before returning the output collected so far.
        """
        filename = osp.abspath(filename)
        if not osp.isfile(filename):
            raise ExposedCallError(f"{filename} doesn't exist.")

        shellwidget = self._get_shellwidget(console_id)
        line = build_run_line(shellwidget, filename, args, method="debugfile")
        return run_code(shellwidget, line, timeout)

    @expose
    def debug_command(
        self,
        command: str,
        console_id: Optional[str] = None,
        timeout: float = DEFAULT_EXECUTE_TIMEOUT,
    ) -> Future:
        """
        Run a debugger (Pdb) command in an IPython console that is
        debugging, and get its output and the new location. For instance:
        ``n`` (next line), ``s`` (step into), ``r`` (return), ``c``
        (continue), ``u``/``d`` (move up/down the stack), ``w`` (where),
        ``l`` (list code), ``a`` (arguments), ``b file:line`` (breakpoint),
        ``p expr`` or ``pp expr`` (evaluate an expression in the current
        frame) or ``q`` (stop debugging).

        If another agent's code is being debugged in the console, only that
        agent can send commands.

        Parameters
        ----------
        command : str
            Pdb command.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        timeout : float, optional
            Seconds to wait for the command to finish (e.g. ``c`` runs until
            the next breakpoint) before returning the output collected so
            far.

        Returns
        -------
        Future
            Resolved with a dict with the ``output``, whether the console is
            still ``debugging``, the new ``location`` and ``notes``.
        """
        shellwidget = self._get_shellwidget(console_id)
        if not shellwidget.is_debugging():
            raise ExposedCallError(
                "The console isn't debugging. Use start_debugging, or set a "
                "breakpoint and run code."
            )
        scheduler = get_scheduler(shellwidget)
        owner = scheduler.get_running_caller()
        if scheduler.is_running_outside_code() and owner != current_caller():
            raise ExposedCallError(
                f"{describe_caller(owner)} is debugging in this console, so "
                f"only it can send debugger commands. Use another console "
                f"(see list_consoles and new_console)."
            )
        if not shellwidget.is_waiting_pdb_input():
            raise ExposedCallError(
                "The debugger is busy running the previous command. Wait for "
                "it to finish or use interrupt_console."
            )
        return PdbCommandCollector(shellwidget, timeout).run(command)

    @expose(read_only=True)
    def get_debug_state(self, console_id: Optional[str] = None) -> dict:
        """
        Get whether an IPython console is debugging and, if so, the current
        location and the call stack (oldest frame first), with the index of
        the frame the debugger is in.

        Parameters
        ----------
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        """
        shellwidget = self._get_shellwidget(console_id)
        state = {
            "debugging": shellwidget.is_debugging(),
            "waiting_for_command": shellwidget.is_waiting_pdb_input(),
            "location": get_pdb_location(shellwidget),
            "stack": None,
            "current_frame": None,
        }

        browser = self.get_widget().get_widget_for_shellwidget(shellwidget)
        pdb_state = getattr(browser, "_pdb_state", None)
        if state["debugging"] and pdb_state and pdb_state[-1]:
            stack, index = pdb_state[-1]
            state["stack"] = [
                {
                    "filename": frame["filename"],
                    "line": frame["lineno"],
                    "function": frame["name"],
                    "code": frame["line"],
                }
                for frame in stack
            ]
            state["current_frame"] = index
        return state

    @expose(read_only=True)
    def list_breakpoints(self) -> list:
        """
        List the breakpoints set in Spyder, with their file, line and
        condition.
        """
        return [
            {"filename": filename, "line": line, "condition": condition}
            for filename, breakpoints in _load_all_breakpoints().items()
            for line, condition in breakpoints
        ]

    @expose
    def set_breakpoint(
        self, filename: str, line: int, condition: Optional[str] = None
    ) -> None:
        """
        Set a breakpoint, which stops code run with debugging (e.g. with
        start_debugging) when it reaches the line. It's shown in the Editor.

        Parameters
        ----------
        filename : str
            Absolute path of the file.
        line : int
            Line number (1-based). It can't be blank or a comment.
        condition : str, optional
            Python expression; the debugger only stops if it's true.
        """
        filename = osp.abspath(filename)
        if not osp.isfile(filename):
            raise ExposedCallError(f"{filename} doesn't exist.")

        codeeditor = self._get_editor_for_filename(filename)
        manager = getattr(codeeditor, "breakpoints_manager", None)
        if manager is not None:
            # Toggling removes an existing breakpoint, e.g. to change its
            # condition
            if line in dict(manager.get_breakpoints()):
                manager.toogle_breakpoint(line)
            manager.toogle_breakpoint(line, condition)
            if line not in dict(manager.get_breakpoints()):
                raise ExposedCallError(
                    f"Can't set a breakpoint at line {line}: it's blank, a "
                    f"comment or outside the file."
                )
            return

        with open(filename, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        text = lines[line - 1].strip() if 0 < line <= len(lines) else ""
        if not text or text.startswith(("#", '"', "'")):
            raise ExposedCallError(
                f"Can't set a breakpoint at line {line}: it's blank, a "
                f"comment or outside the file."
            )

        breakpoints = [
            breakpoint
            for breakpoint in load_breakpoints(filename)
            if breakpoint[0] != line
        ]
        save_breakpoints(filename, breakpoints + [(line, condition)])
        self.get_widget().sig_breakpoints_saved.emit()

    @expose
    def remove_breakpoint(self, filename: str, line: int) -> None:
        """
        Remove a breakpoint.

        Parameters
        ----------
        filename : str
            Absolute path of the file.
        line : int
            Line number (1-based) of the breakpoint.
        """
        filename = osp.abspath(filename)
        if line not in dict(load_breakpoints(filename)):
            raise ExposedCallError(
                f"There's no breakpoint at line {line} of {filename}."
            )

        codeeditor = self._get_editor_for_filename(filename)
        manager = getattr(codeeditor, "breakpoints_manager", None)
        if manager is not None:
            manager.toogle_breakpoint(line)
        else:
            clear_breakpoint(filename, line)
            self.get_widget().sig_breakpoints_saved.emit()

    # ---- For execution
    @run_execute(context=RunContext.File)
    def debug_file(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        console = self.get_plugin(Plugins.IPythonConsole)
        if console is None:
            return

        exec_params = conf['params']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']
        params["run_method"] = "debugfile"

        console.exec_files(input, conf)

        self.get_widget().set_pdb_take_focus(False)

    @run_execute(context=RunContext.Cell)
    def debug_cell(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        console = self.get_plugin(Plugins.IPythonConsole)
        if console is None:
            return

        run_input: CellRun = input['run_input']
        if run_input['copy']:
            code = run_input['cell']
            if not code.strip():
                # Empty cell
                return
            console.run_selection("%%debug\n" + code)
            return

        exec_params = conf['params']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']
        params["run_method"] = "debugcell"

        console.exec_cell(input, conf)

        self.get_widget().set_pdb_take_focus(False)


    @run_execute(context=RunContext.Selection)
    def debug_selection(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        console = self.get_plugin(Plugins.IPythonConsole)
        if console is None:
            return

        run_input: SelectionRun = input['run_input']
        code = run_input['selection']
        if not code.strip():
            # No selection
            return

        run_input['selection'] = "%%debug\n" + code

        console.exec_selection(input, conf)

        self.get_widget().set_pdb_take_focus(False)

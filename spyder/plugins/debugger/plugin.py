# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Debugger Plugin."""

# Standard library imports
import os.path as osp
from typing import List

# Third-party imports
from qtpy.QtCore import Qt, Slot

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.shellconnect.mixins import ShellConnectPluginMixin
from spyder.api.translations import _
from spyder.plugins.debugger.confpage import DebuggerConfigPage
from spyder.plugins.debugger.utils.breakpointsmanager import (
    BreakpointsManager, clear_all_breakpoints, clear_breakpoint)
from spyder.plugins.debugger.widgets.main_widget import (
    DebuggerBreakpointActions, DebuggerWidget, DebuggerWidgetActions)
from spyder.plugins.editor.utils.editor import get_file_language
from spyder.plugins.editor.utils.languages import ALL_LANGUAGES
from spyder.plugins.ipythonconsole.api import IPythonConsolePyConfiguration
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
    REQUIRES = [Plugins.IPythonConsole, Plugins.Preferences, Plugins.Run]
    OPTIONAL = [Plugins.Editor, Plugins.MainMenu, Plugins.Toolbar]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = DebuggerWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = DebuggerConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

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
            text=_("Debug selection or current line"),
            tip=_("Debug selection or current line"),
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
            self.ipython_editor_run_configuration
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

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()

        for run_config in [
            self.python_editor_run_configuration,
            self.ipython_editor_run_configuration
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
            self.get_widget().sig_breakpoints_saved)

    def _disconnect_codeeditor(self, codeeditor):
        """Connect a code editor."""
        codeeditor.breakpoints_manager.sig_breakpoints_saved.disconnect(
            self.get_widget().sig_breakpoints_saved)
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
        """Set/Clear breakpoint"""
        codeeditor = self._get_current_editor()
        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return
        codeeditor.breakpoints_manager.toogle_breakpoint()

    @Slot()
    def _set_or_edit_conditional_breakpoint(self):
        """Set/Edit conditional breakpoint"""
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

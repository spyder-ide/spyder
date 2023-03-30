# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler Plugin.
"""

# Standard library imports
from typing import List

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.mainmenu.api import ApplicationMenus, DebugMenuSections
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import ProfilerWidget
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.ipythonconsole.api import IPythonConsolePyConfiguration
from spyder.plugins.run.api import (
    RunContext, RunExecutor, RunConfiguration,
    ExtendedRunExecutionParameters, RunResult, run_execute)
from spyder.plugins.ipythonconsole.widgets.config import IPythonConfigOptions
from spyder.plugins.editor.api.run import CellRun, SelectionRun




# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin, ShellConnectMixin, RunExecutor):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Preferences, Plugins.IPythonConsole, Plugins.Run]
    OPTIONAL = [Plugins.Editor]
    TABIFY = [Plugins.Help]
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Profiler")

    def get_description(self):
        return _("Profile your scripts and find bottlenecks.")

    def get_icon(self):
        return self.create_icon('profiler')

    def on_initialize(self):

        self.python_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'py',
            'contexts': [
                {
                    'name': 'File'
                },
                {
                    'name': 'Cell'
                },
                {
                    'name': 'Selection'
                },
            ]
        }

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {
                    'name': 'File'
                },
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'py',
                'context': {
                    'name': 'Cell'
                },
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': 'py',
                'context': {
                    'name': 'Selection'
                },
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
        ]

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)
        run.register_executor_configuration(self, self.executor_configuration)

        run.create_run_in_executor_button(
            RunContext.File,
            self.NAME,
            text=_("Profile file"),
            tip=_("Profile file"),
            icon=self.create_icon('profiler'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Debug,
                "section": DebugMenuSections.StartDebug,
                "before_section": DebugMenuSections.ControlDebug
            },
            add_to_toolbar=ApplicationToolbars.Profile
        )

        run.create_run_in_executor_button(
            RunContext.Cell,
            self.NAME,
            text=_("Profile cell"),
            tip=_("Profile cell"),
            icon=self.create_icon('profile_cell'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Debug,
                "section": DebugMenuSections.StartDebug,
                "before_section": DebugMenuSections.ControlDebug
            },
            add_to_toolbar=ApplicationToolbars.Profile
        )

        run.create_run_in_executor_button(
            RunContext.Selection,
            self.NAME,
            text=_("Profile selection or current line"),
            tip=_("Profile selection or current line"),
            icon=self.create_icon('profile_selection'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Debug,
                "section": DebugMenuSections.StartDebug,
                "before_section": DebugMenuSections.ControlDebug
            },
            add_to_toolbar=ApplicationToolbars.Profile
        )

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.add_supported_run_configuration(
            self.python_editor_run_configuration)

        widget.sig_edit_goto_requested.connect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.remove_supported_run_configuration(
            self.python_editor_run_configuration)

        widget.sig_edit_goto_requested.disconnect(editor.load)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    # ---- For execution
    @run_execute(context=RunContext.File)
    def profile_files(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        console = self.get_plugin(Plugins.IPythonConsole)
        if console is None:
            return

        exec_params = conf['params']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']
        params["run_method"] = "profilefile"

        return console.exec_files(input, conf)

    @run_execute(context=RunContext.Cell)
    def profile_cell(
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
            console.run_selection("%%profile\n" + code)
            return

        exec_params = conf['params']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']
        params["run_method"] = "profilecell"

        return console.exec_cell(input, conf)


    @run_execute(context=RunContext.Selection)
    def profile_selection(
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
        run_input['selection'] = "%%profile\n" + code

        return console.exec_selection(input, conf)

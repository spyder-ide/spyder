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

# Third party imports
from packaging.version import parse

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.shellconnect.mixins import ShellConnectPluginMixin
from spyder.api.translations import _
from spyder.plugins.mainmenu.api import ApplicationMenus, RunMenuSections
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import ProfilerWidget
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.plugins.ipythonconsole.api import IPythonConsolePyConfiguration
from spyder.plugins.run.api import (
    ExtendedRunExecutionParameters,
    RunConfiguration,
    RunContext,
    RunExecutor,
    RunResult,
    run_execute,
)
from spyder.plugins.ipythonconsole.widgets.run_conf import IPythonConfigOptions
from spyder.plugins.editor.api.run import CellRun, SelectionRun


# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin, ShellConnectPluginMixin, RunExecutor):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Preferences, Plugins.IPythonConsole, Plugins.Run]
    OPTIONAL = [Plugins.Editor]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Profiler")

    @staticmethod
    def get_description():
        return _("Profile Python files to find execution bottlenecks.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon('profiler')

    def on_initialize(self):

        self.python_editor_run_configuration = {
            'origin': self.NAME,
            'extension': ['py', 'ipy'],
            "contexts": [
                {"name": "File"},
                {"name": "Cell"},
                {"name": "Selection"},
            ],
        }

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 3
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
                'input_extension': ['py', 'ipy'],
                'context': {'name': 'Cell'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
            {
                'input_extension': ['py', 'ipy'],
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 10
            },
        ]

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)

        # Remove current parameters to recreate them due to the new
        # architecture for profiling introduced in PR spyder-ide/spyder#24794
        if (
            # This is needed when updgrading from Spyder 6.0 to 6.1
            (
                parse(self.old_spyder_conf_version) <= parse("87.3.0")
                and parse(self.spyder_conf_version) > parse("87.3.0")
            )
            # And this when downgrading from Spyder 6.1 to 6.0
            or (
                parse(self.old_spyder_conf_version) > parse("87.3.0")
                and parse(self.spyder_conf_version) <= parse("87.3.0")
            )
        ):
            all_execution_params = self.get_conf(
                "parameters", section="run", default={}
            )
            if self.NAME in all_execution_params:
                all_execution_params.pop(self.NAME)
                self.set_conf(
                    "parameters", all_execution_params, section="run"
                )

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
                "menu": ApplicationMenus.Run,
                "section": RunMenuSections.Profile,
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
                "menu": ApplicationMenus.Run,
                "section": RunMenuSections.Profile,
            },
            add_to_toolbar=ApplicationToolbars.Profile
        )

        run.create_run_in_executor_button(
            RunContext.Selection,
            self.NAME,
            text=_("Profile current line or selection"),
            tip=_("Profile current line or selection"),
            icon=self.create_icon('profile_selection'),
            shortcut_context=self.NAME,
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Run,
                "section": RunMenuSections.Profile,
            },
            add_to_toolbar=ApplicationToolbars.Profile
        )

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration
        )

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.add_supported_run_configuration(
            self.python_editor_run_configuration
        )

        widget.sig_edit_goto_requested.connect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        editor.remove_supported_run_configuration(
            self.python_editor_run_configuration
        )

        widget.sig_edit_goto_requested.disconnect(editor.load)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    def on_mainwindow_visible(self):
        # Make plugin visible in case it's not but only once. For most users
        # this will display it in the UI when moving from 6.0 to 6.1
        if not self.get_conf("make_visible", default=False):
            if not self.get_widget().is_visible:
                self.get_widget().toggle_view(True)
            self.set_conf("make_visible", True)

    # ---- For execution
    # -------------------------------------------------------------------------
    @run_execute(context=RunContext.File)
    def profile_file(
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

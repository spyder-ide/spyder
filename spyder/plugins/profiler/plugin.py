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
from qtpy.QtCore import Qt, Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.editor.api.run import FileRun
from spyder.plugins.mainmenu.api import ApplicationMenus, RunMenuSections
from spyder.plugins.profiler.api import ProfilerPyConfiguration
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import (
    ProfilerWidget, is_profiler_installed)
from spyder.plugins.profiler.widgets.run_conf import (
    ProfilerPyConfigurationGroup)
from spyder.plugins.run.api import (
    RunExecutor, run_execute, RunContext, RunConfiguration,
    ExtendedRunExecutionParameters, PossibleRunResult)


class Profiler(SpyderDockablePlugin, RunExecutor):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Preferences, Plugins.Editor, Plugins.Run]
    OPTIONAL = []
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    # ---- Signals
    # -------------------------------------------------------------------------
    sig_started = Signal()
    """This signal is emitted to inform the profiling process has started."""

    sig_finished = Signal()
    """This signal is emitted to inform the profile profiling has finished."""

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
        widget = self.get_widget()
        widget.sig_started.connect(self.sig_started)
        widget.sig_finished.connect(self.sig_finished)

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': ProfilerPyConfigurationGroup,
                'requires_cwd': True,
                'priority': 3
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': ProfilerPyConfigurationGroup,
                'requires_cwd': True,
                'priority': 3
            },
        ]

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        widget.sig_edit_goto_requested.connect(editor.load)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)
        run.register_executor_configuration(self, self.executor_configuration)

        if is_profiler_installed():
            run.create_run_in_executor_button(
                RunContext.File,
                self.NAME,
                text=_("Run profiler"),
                tip=_("Run profiler"),
                icon=self.create_icon('profiler'),
                shortcut_context='profiler',
                register_shortcut=True,
                add_to_menu={
                    "menu": ApplicationMenus.Run,
                    "section": RunMenuSections.RunInExecutors
                },
                shortcut_widget_context=Qt.ApplicationShortcut,
            )

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        widget.sig_edit_goto_requested.disconnect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration)
        run.destroy_run_in_executor_button(
            RunContext.File, self.NAME)

    # ---- Public API
    # -------------------------------------------------------------------------
    def run_profiler(self):
        """
        Run profiler.

        Notes
        -----
        This method will check if the file on the editor can be saved first.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor.save():
            self.switch_to_plugin()
            self.analyze(editor.get_current_filename())

    def stop_profiler(self):
        """
        Stop profiler.
        """
        self.get_widget().stop()

    @run_execute(context=RunContext.File)
    def run_file(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[PossibleRunResult]:
        self.switch_to_plugin()

        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: ProfilerPyConfiguration = exec_params['executor_params']

        run_input: FileRun = input['run_input']
        filename = run_input['path']

        wdir = cwd_opts['path']
        args = params['args']

        self.get_widget().analyze(
            filename,
            wdir=wdir,
            args=args
        )

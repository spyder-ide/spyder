# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Pylint Code Analysis Plugin.
"""

# Standard library imports
from typing import List

# Third party imports
from qtpy.QtCore import Qt, Signal, Slot

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.editor.api.run import FileRun
from spyder.plugins.mainmenu.api import ApplicationMenus, SourceMenuSections
from spyder.plugins.pylint.confpage import PylintConfigPage
from spyder.plugins.pylint.main_widget import PylintWidget
from spyder.plugins.run.api import (
    RunContext, RunConfiguration, PossibleRunResult, run_execute,
    ExtendedRunExecutionParameters, RunExecutor)


class PylintActions:
    AnalyzeCurrentFile = 'run analysis'


class Pylint(SpyderDockablePlugin, RunExecutor):

    NAME = "pylint"
    WIDGET_CLASS = PylintWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = PylintConfigPage
    REQUIRES = [Plugins.Preferences, Plugins.Editor, Plugins.Run]
    OPTIONAL = [Plugins.MainMenu, Plugins.Projects]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # --- Signals
    sig_edit_goto_requested = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    # ---- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Code Analysis")

    @staticmethod
    def get_description():
        return _("Analyze code and view the results from both static and "
                 "real-time analysis.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon("pylint")

    def on_initialize(self):
        widget = self.get_widget()

        # Expose widget signals at the plugin level
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_start_analysis_requested.connect(self.start_code_analysis)

        # To have a reference to the run action of this plugin
        self.run_action = None

        # Run configuration
        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': False,
                'priority': 4
            },
        ]

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        # Connect to Editor
        widget.sig_edit_goto_requested.connect(editor.load)
        editor.sig_editor_focus_changed.connect(self._set_filename)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        # Connect to projects
        projects = self.get_plugin(Plugins.Projects)

        projects.sig_project_loaded.connect(self._set_project_dir)
        projects.sig_project_closed.connect(self._unset_project_dir)

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)
        run.register_executor_configuration(self, self.executor_configuration)

        self.run_action = run.create_run_in_executor_button(
            RunContext.File,
            self.NAME,
            text=_("Run code analysis"),
            tip=_("Run code analysis"),
            icon=self.create_icon("pylint"),
            shortcut_context='pylint',
            register_shortcut=True,
            add_to_menu={
                "menu": ApplicationMenus.Source,
                "section": SourceMenuSections.CodeAnalysis
            },
            shortcut_widget_context=Qt.ApplicationShortcut,
        )

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        # Connect to Editor
        widget.sig_edit_goto_requested.disconnect(editor.load)
        editor.sig_editor_focus_changed.disconnect(self._set_filename)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        # Disconnect from projects
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._set_project_dir)
        projects.sig_project_closed.disconnect(self._unset_project_dir)

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration)
        run.destroy_run_in_executor_button(
            RunContext.File,
            self.NAME)

    # ---- Private API
    # -------------------------------------------------------------------------
    @Slot()
    def _set_filename(self):
        """
        Set filename without code analysis.
        """
        try:
            editor = self.get_plugin(Plugins.Editor)
            if editor:
                self.get_widget().set_filename(editor.get_current_filename())
        except SpyderAPIError:
            # Editor was deleted
            pass

    def _set_project_dir(self, value):
        widget = self.get_widget()
        widget.set_conf("project_dir", value)

    def _unset_project_dir(self, _unused):
        widget = self.get_widget()
        widget.set_conf("project_dir", None)

    # ---- Public API
    # -------------------------------------------------------------------------
    def change_history_depth(self, value=None):
        """
        Change history maximum number of entries.

        Parameters
        ----------
        value: int or None, optional
            The valur to set  the maximum history depth. If no value is
            provided, an input dialog will be launched. Default is None.
        """
        self.get_widget().change_history_depth(value=value)

    def get_filename(self):
        """
        Get current filename in combobox.
        """
        return self.get_widget().get_filename()

    @run_execute(context=RunContext.File)
    def run_file(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[PossibleRunResult]:

        self.switch_to_plugin()
        run_input: FileRun = input['run_input']
        filename = run_input['path']
        self.start_code_analysis(filename)

    @Slot()
    def start_code_analysis(self, filename=None):
        """
        Perform code analysis for given `filename`.

        If `filename` is None default to current filename in combobox.

        If this method is called while still running it will stop the code
        analysis.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor:
            if self.get_conf("save_before", True) and not editor.save():
                return

        if filename is None or isinstance(filename, bool):
            filename = self.get_widget().get_filename()

        self.switch_to_plugin(force_focus=True)
        self.get_widget().start_code_analysis(filename)

    def stop_code_analysis(self):
        """
        Stop the code analysis process.
        """
        self.get_widget().stop_code_analysis()

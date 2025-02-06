# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""External terminal plugin."""

# Standard library imports.
import os
import sys
import tempfile
import platform
from typing import List

# Third-party imports
from packaging.version import parse
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import _
from spyder.plugins.editor.api.run import FileRun, SelectionRun
from spyder.plugins.externalterminal.api import (
    ExtTerminalPyConfiguration, ExtTerminalShConfiguration)
from spyder.plugins.externalterminal.widgets.run_conf import (
    ExternalTerminalPyConfiguration, ExternalTerminalShConfiguration)
from spyder.plugins.mainmenu.api import ApplicationMenus, RunMenuSections
from spyder.plugins.run.api import (
    RunContext, run_execute, RunConfiguration, ExtendedRunExecutionParameters,
    RunResult, RunExecutor)
from spyder.utils import programs
from spyder.utils.misc import get_python_executable


class ExternalTerminal(SpyderPluginV2, RunExecutor):
    """External terminal plugin."""

    NAME = 'external_terminal'
    REQUIRES = [Plugins.Run]
    OPTIONAL = [Plugins.Editor]
    CONF_SECTION = NAME
    CONF_FILE = False

    # ---- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("External terminal")

    @staticmethod
    def get_description():
        return _("Run scripts in an external system terminal.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon('DollarFileIcon')

    def on_initialize(self):
        self.editor_configurations = [
            {
                'origin': self.NAME,
                'extension': 'py',
                'contexts': [{'name': 'File'}]
            }
        ]

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': ExternalTerminalPyConfiguration,
                'requires_cwd': True,
                'priority': 2
            },
        ]

        if os.name == 'nt':
            self.editor_configurations.append({
                'origin': self.NAME,
                'extension': 'bat',
                'contexts': [{'name': 'File'}, {'name': 'Selection'}]
            })

            self.executor_configuration.append({
                'input_extension': 'bat',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': ExternalTerminalShConfiguration(
                    'cmd.exe', '/K'
                ),
                'requires_cwd': True,
                'priority': 1
            })

            self.executor_configuration.append({
                'input_extension': 'bat',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': ExternalTerminalShConfiguration(
                    'cmd.exe', '/K'
                ),
                'requires_cwd': True,
                'priority': 1
            })

            self.editor_configurations.append({
                'origin': self.NAME,
                'extension': 'ps1',
                'contexts': [{'name': 'File'}, {'name': 'Selection'}]
            })

            self.executor_configuration.append({
                'input_extension': 'ps1',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': ExternalTerminalShConfiguration(
                    'powershell.exe'
                ),
                'requires_cwd': True,
                'priority': 1
            })

            self.executor_configuration.append({
                'input_extension': 'ps1',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': ExternalTerminalShConfiguration(
                    'powershell.exe'
                ),
                'requires_cwd': True,
                'priority': 1
            })

        if sys.platform in {'linux', 'darwin'}:
            default_shell = 'bash'
            if sys.platform == 'darwin':
                mac_ver = parse(platform.mac_ver()[0])
                if mac_ver >= parse('10.15.0'):
                    # Catalina changed the default shell to zsh
                    default_shell = 'zsh'

            self.editor_configurations.append({
                'origin': self.NAME,
                'extension': 'sh',
                'contexts': [{'name': 'File'}, {'name': 'Selection'}]
            })

            self.executor_configuration.append({
                'input_extension': 'sh',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': ExternalTerminalShConfiguration(
                    programs.is_program_installed(default_shell)
                ),
                'requires_cwd': True,
                'priority': 1
            })

            self.executor_configuration.append({
                'input_extension': 'sh',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': ExternalTerminalShConfiguration(
                    programs.is_program_installed(default_shell)
                ),
                'requires_cwd': True,
                'priority': 1
            })

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)
        run.register_executor_configuration(self, self.executor_configuration)

        run.create_run_in_executor_button(
            RunContext.File,
            self.NAME,
            text=_("Run in external terminal"),
            tip=_("Run in an operating system terminal"),
            icon=self.get_icon(),
            register_shortcut=False,
            add_to_menu={
                "menu": ApplicationMenus.Run,
                "section": RunMenuSections.RunInExecutors
            },
        )

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        for conf in self.editor_configurations:
            editor.add_supported_run_configuration(conf)

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration
        )
        run.destroy_run_in_executor_button(RunContext.File, self.NAME)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        for conf in self.editor_configurations:
            editor.remove_supported_run_configuration(conf)

    # ---- Public API
    # -------------------------------------------------------------------------
    def open_external_python_terminal(self, fname, wdir, args, interact, debug,
                                      python_args):
        """Open external terminal."""
        # Running script in an external system terminal
        try:
            if self.get_conf('default', section='main_interpreter'):
                executable = get_python_executable()
            else:
                executable = self.get_conf(
                    'executable',
                    section='main_interpreter'
                )

            pypath = self.get_conf(
                'spyder_pythonpath',
                section='pythonpath_manager',
                default=[]
            )

            programs.run_python_script_in_terminal(
                fname, wdir, args, interact, debug, python_args, executable,
                pypath=pypath
            )
        except NotImplementedError:
            QMessageBox.critical(
                self,
                _("Run"),
                _("Running an external system terminal is not supported on "
                  "platform %s.") % os.name
            )

    @run_execute(extension='py')
    def run_python_files(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:
        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: ExtTerminalPyConfiguration = exec_params['executor_params']

        run_input: FileRun = input['run_input']
        filename = run_input['path']

        wdir = cwd_opts['path']
        args = params['args']
        interact = params['interact']
        debug = False
        python_args = params['python_args']
        self.open_external_python_terminal(
            filename, wdir, args, interact, debug, python_args
        )

    @run_execute(extension=['sh', 'bat', 'ps1'])
    def run_shell_files(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:
        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: ExtTerminalShConfiguration = exec_params['executor_params']

        run_input: FileRun = input['run_input']
        filename = run_input['path']
        extension = input['metadata']['input_extension']

        executable = params['interpreter']
        executable_args = params['interpreter_opts']
        script_args = params['script_opts']
        close_after_exec = params['close_after_exec']
        wdir = cwd_opts['path']

        windows_shell = 'cmd.exe'
        no_exit_flag = '/K'
        if extension == 'ps1':
            windows_shell = 'powershell.exe'
            no_exit_flag = '-NoExit'

        if close_after_exec:
            no_exit_flag = ''

        windows_shell = f'{windows_shell} {no_exit_flag}'.strip()

        programs.run_general_file_in_terminal(
            executable, executable_args, filename, script_args, wdir,
            close_after_exec, windows_shell=windows_shell)

    @run_execute(extension=['sh', 'bat', 'ps1'], context=RunContext.Selection)
    def run_shell_selection(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:
        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: ExtTerminalShConfiguration = exec_params['executor_params']

        metadata = input['metadata']
        run_input: SelectionRun = input['run_input']
        selection = run_input['selection']

        executable = params['interpreter']
        executable_args = params['interpreter_opts']
        script_args = params['script_opts']
        close_after_exec = params['close_after_exec']
        wdir = cwd_opts['path']

        f = tempfile.NamedTemporaryFile(
            'wt', prefix='run_spyder_',
            suffix=f'.{metadata["input_extension"]}',
            dir=programs.get_temp_dir(),
            delete=False)

        with f:
            f.write(selection)
            programs.run_general_file_in_terminal(
                executable, executable_args, f.name, script_args, wdir,
                close_after_exec)

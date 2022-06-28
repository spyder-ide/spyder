# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""External console plugin."""

# Standard library imports.
import os
import sys
import tempfile
import platform
from typing import List
from distutils.version import LooseVersion

# Third-party imports
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.utils import programs
from spyder.utils.misc import get_python_executable
from spyder.plugins.run.api import (
    RunContext, run_execute, RunConfiguration, ExtendedRunExecutionParameters,
    RunResult, RunExecutor)
from spyder.api.translations import get_translation
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.plugins.editor.api.run import FileRun, SelectionRun
from spyder.plugins.externalconsole.api import (
    ExtConsolePyConfiguration, ExtConsoleShConfiguration)
from spyder.plugins.externalconsole.widgets.run_conf import (
    ExternalConsolePyConfiguration, ExternalConsoleShConfiguration)

# Localization
_ = get_translation('spyder')


class ExternalConsole(SpyderPluginV2, RunExecutor):
    """External console plugin."""

    NAME = 'external_console'
    REQUIRES = [Plugins.Run]
    OPTIONAL = [Plugins.Editor]
    CONF_SECTION = NAME
    CONF_FILE = False

    # --- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("External console")

    def get_description(self):
        return _("Manage run configuration.")

    def get_icon(self):
        return self.create_icon('copywop')

    def on_initialize(self):
        self.editor_configurations = [
            {
                'origin': self.NAME,
                'extension': 'py',
                'contexts': [
                    {
                        'name': 'File'
                    }
                ]
            }
        ]

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {
                    'name': 'File'
                },
                'output_formats': [],
                'configuration_widget': ExternalConsolePyConfiguration,
                'requires_cwd': True,
                'priority': 2
            }
        ]

        if os.name == 'nt':
            self.editor_configurations.append({
                'origin': self.NAME,
                'extension': 'bat',
                'contexts': [
                    {
                        'name': 'File'
                    },
                    {
                        'name': 'Selection'
                    }
                ]
            })

            self.executor_configuration.append({
                'input_extension': 'bat',
                'context': {
                    'name': 'File'
                },
                'output_formats': [],
                'configuration_widget': ExternalConsoleShConfiguration(
                    'cmd.exe', '/K'),
                'requires_cwd': True,
                'priority': 1
            })

            self.executor_configuration.append({
                'input_extension': 'bat',
                'context': {
                    'name': 'Selection'
                },
                'output_formats': [],
                'configuration_widget': ExternalConsoleShConfiguration(
                    'cmd.exe', '/K'),
                'requires_cwd': True,
                'priority': 1
            })

            self.editor_configurations.append({
                'origin': self.NAME,
                'extension': 'ps1',
                'contexts': [
                    {
                        'name': 'File'
                    },
                    {
                        'name': 'Selection'
                    }
                ]
            })

            self.executor_configuration.append({
                'input_extension': 'ps1',
                'context': {
                    'name': 'File'
                },
                'output_formats': [],
                'configuration_widget': ExternalConsoleShConfiguration(
                    'powershell.exe'),
                'requires_cwd': True,
                'priority': 1
            })

            self.executor_configuration.append({
                'input_extension': 'ps1',
                'context': {
                    'name': 'Selection'
                },
                'output_formats': [],
                'configuration_widget': ExternalConsoleShConfiguration(
                    'powershell.exe'),
                'requires_cwd': True,
                'priority': 1
            })

        if sys.platform in {'linux', 'darwin'}:
            default_shell = 'bash'
            if sys.platform == 'darwin':
                mac_ver = LooseVersion(platform.mac_ver()[0])
                if mac_ver >= LooseVersion('10.15.0'):
                    # Catalina changed the default shell to zsh
                    default_shell = 'zsh'

            self.editor_configurations.append({
                'origin': self.NAME,
                'extension': 'sh',
                'contexts': [
                    {
                        'name': 'File'
                    },
                    {
                        'name': 'Selection'
                    }
                ]
            })

            self.executor_configuration.append({
                'input_extension': 'sh',
                'context': {
                    'name': 'File'
                },
                'output_formats': [],
                'configuration_widget': ExternalConsoleShConfiguration(
                    programs.is_program_installed(default_shell)),
                'requires_cwd': True,
                'priority': 1
            })

            self.executor_configuration.append({
                'input_extension': 'sh',
                'context': {
                    'name': 'Selection'
                },
                'output_formats': [],
                'configuration_widget': ExternalConsoleShConfiguration(
                    programs.is_program_installed(default_shell)),
                'requires_cwd': True,
                'priority': 1
            })

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)
        run.register_executor_configuration(self, self.executor_configuration)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        for conf in self.editor_configurations:
            editor.add_supported_run_configuration(conf)

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        for conf in self.editor_configurations:
            editor.remove_supported_run_configuration(conf)

    def open_external_python_console(
            self, fname, wdir, args, interact, debug,
            python_args):
        """Open external console"""
        # Running script in an external system terminal
        try:
            if self.get_conf('default', section='main_interpreter'):
                executable = get_python_executable()
            else:
                executable = self.get_conf(
                    'executable', section='main_interpreter')
            programs.run_python_script_in_terminal(
                    fname, wdir, args, interact, debug, python_args,
                    executable)
        except NotImplementedError:
            QMessageBox.critical(self, _("Run"),
                                    _("Running an external system terminal "
                                    "is not supported on platform %s."
                                    ) % os.name)

    @run_execute(extension='py')
    def run_python_files(
            self, input: RunConfiguration,
            conf: ExtendedRunExecutionParameters) -> List[RunResult]:
        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: ExtConsolePyConfiguration = exec_params['executor_params']

        run_input: FileRun = input['run_input']
        filename = run_input['path']

        wdir = cwd_opts['path']
        args = params['args']
        interact = params['interact']
        debug = False
        python_args = params['python_args']
        self.open_external_python_console(
            filename, wdir, args, interact, debug, python_args)

    @run_execute(extension=['sh', 'bat', 'ps1'])
    def run_shell_files(
            self, input: RunConfiguration,
            conf: ExtendedRunExecutionParameters) -> List[RunResult]:
        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: ExtConsoleShConfiguration = exec_params['executor_params']

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
            self, input: RunConfiguration,
            conf: ExtendedRunExecutionParameters) -> List[RunResult]:
        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: ExtConsoleShConfiguration = exec_params['executor_params']

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

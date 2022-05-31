# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""External console run executor configurations."""

# Standard library imports
import os
import sys
import os.path as osp
from typing import Callable

# Third-party imports
from qtpy.compat import getexistingdirectory, getopenfilename
from qtpy.QtWidgets import (
    QWidget, QRadioButton, QGroupBox, QVBoxLayout, QGridLayout,
    QCheckBox, QLineEdit, QHBoxLayout, QLabel)

# Local imports
from spyder.api.translations import get_translation
from spyder.plugins.run.api import (
    RunExecutorConfigurationGroup, Context, RunConfigurationMetadata,
    RunExecutorConfigurationGroupFactory)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import create_toolbutton
from spyder.plugins.externalconsole.api import ExtConsoleShConfiguration

_ = get_translation('spyder')

RUN_DEFAULT_CONFIG = _("Run file with default configuration")
RUN_CUSTOM_CONFIG = _("Run file with custom configuration")
CURRENT_INTERPRETER = _("Execute in current console")
DEDICATED_INTERPRETER = _("Execute in a dedicated console")
SYSTERM_INTERPRETER = _("Execute in an external system terminal")
CLEAR_ALL_VARIABLES = _("Remove all variables before execution")
CONSOLE_NAMESPACE = _("Run in console's namespace instead of an empty one")
POST_MORTEM = _("Directly enter debugging when errors appear")
INTERACT = _("Interact with the Python console after execution")


class ExternalConsolePyConfiguration(RunExecutorConfigurationGroup):
    """External console Python run configuration options."""

    def __init__(self, parent, context: Context,
                 input_extension: str, input_metadata: RunConfigurationMetadata):
        super().__init__(parent, context, input_extension, input_metadata)

        self.dir = None

        # --- Interpreter ---
        interpreter_group = QGroupBox(_("Console"))
        interpreter_layout = QVBoxLayout(interpreter_group)

        # --- System terminal ---
        external_group = QWidget()

        external_layout = QGridLayout()
        external_group.setLayout(external_layout)
        self.interact_cb = QCheckBox(INTERACT)
        external_layout.addWidget(self.interact_cb, 1, 0, 1, -1)

        self.pclo_cb = QCheckBox(_("Command line options:"))
        external_layout.addWidget(self.pclo_cb, 3, 0)
        self.pclo_edit = QLineEdit()
        self.pclo_cb.toggled.connect(self.pclo_edit.setEnabled)
        self.pclo_edit.setEnabled(False)
        self.pclo_edit.setToolTip(_("<b>-u<_b> is added to the "
                                    "other options you set here"))
        external_layout.addWidget(self.pclo_edit, 3, 1)

        interpreter_layout.addWidget(external_group)

        # --- General settings ----
        common_group = QGroupBox(_("General settings"))

        common_layout = QGridLayout(common_group)

        self.clo_cb = QCheckBox(_("Command line options:"))
        common_layout.addWidget(self.clo_cb, 0, 0)
        self.clo_edit = QLineEdit()
        self.clo_cb.toggled.connect(self.clo_edit.setEnabled)
        self.clo_edit.setEnabled(False)
        common_layout.addWidget(self.clo_edit, 0, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(interpreter_group)
        layout.addWidget(common_group)
        layout.addStretch(100)

    def select_directory(self):
        """Select directory"""
        basedir = str(self.wd_edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd_or_home()
        directory = getexistingdirectory(self, _("Select directory"), basedir)
        if directory:
            self.wd_edit.setText(directory)
            self.dir = directory

    def get_default_configuration(self) -> dict:
        return {
            'args_enabled': False,
            'args': '',
            'interact': False,
            'python_args_enabled': False,
            'python_args': '',
        }

    def set_configuration(self, config: dict):
        interact = config['interact']
        args_enabled = config['args_enabled']
        args = config['args']
        py_args_enabled = config['python_args_enabled']
        py_args = config['python_args']

        self.interact_cb.setChecked(interact)
        self.pclo_cb.setChecked(args_enabled)
        self.pclo_edit.setText(args)
        self.clo_cb.setChecked(py_args_enabled)
        self.clo_edit.setText(py_args)

    def get_configuration(self) -> dict:
        return {
            'args_enabled': self.pclo_cb.isChecked(),
            'args': self.pclo_edit.text(),
            'interact': self.interact_cb.isChecked(),
            'python_args_enabled': self.clo_cb.isChecked(),
            'python_args': self.clo_edit.text(),
        }


class GenExternalConsoleShConfiguration(RunExecutorConfigurationGroup):
    """External console shell run configuration options."""

    def __init__(self, default_shell: str, parent,
                 context: Context, input_extension: str,
                 input_metadata: RunConfigurationMetadata,
                 shell_args: str = ''):
        super().__init__(parent, context, input_extension, input_metadata)

        self.default_shell = default_shell

        # --- Interpreter ---
        interpreter_group = QGroupBox(_("Interpreter"))
        interpreter_layout = QGridLayout(interpreter_group)

        interpreter_label = QLabel(_("Shell interpreter:"))
        interpreter_layout.addWidget(interpreter_label, 0, 0)
        edit_layout = QHBoxLayout()
        self.interpreter_edit = QLineEdit()
        browse_btn = create_toolbutton(
            self,
            triggered=self.select_directory,
            icon=ima.icon('DirOpenIcon'),
            tip=_("Select directory")
        )
        edit_layout.addWidget(self.interpreter_edit)
        edit_layout.addWidget(browse_btn)
        interpreter_layout.addLayout(edit_layout, 0, 1)

        self.interpreter_opts_cb = QCheckBox(_("Interpreter arguments:"))
        interpreter_layout.addWidget(self.interpreter_opts_cb, 1, 0)
        self.interpreter_opts_edit = QLineEdit()
        self.interpreter_opts_cb.toggled.connect(
            self.interpreter_opts_edit.setEnabled)
        self.interpreter_opts_edit.setEnabled(False)
        interpreter_layout.addWidget(self.interpreter_opts_edit, 1, 1)

        if shell_args:
            self.interpreter_opts_cb.setChecked(True)
            self.interpreter_opts_edit.setText(shell_args)

        # --- Script ---
        script_group = QGroupBox(_('Script'))
        script_layout = QGridLayout(script_group)

        self.script_opts_cb = QCheckBox(_("Script arguments:"))
        script_layout.addWidget(self.script_opts_cb, 1, 0)
        self.script_opts_edit = QLineEdit()
        self.script_opts_cb.toggled.connect(
            self.script_opts_edit.setEnabled)
        self.script_opts_edit.setEnabled(False)
        script_layout.addWidget(self.script_opts_edit, 1, 1)

        self.close_after_exec_cb = QCheckBox(
            _('Close console after execution'))
        script_layout.addWidget(self.close_after_exec_cb, 2, 0)

        layout = QVBoxLayout(self)
        layout.addWidget(interpreter_group)
        layout.addWidget(script_group)
        layout.addStretch(100)

    def select_directory(self):
        """Select directory"""
        basedir = str(self.interpreter_edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd_or_home()
        file, __ = getopenfilename(self, _("Select executable"), basedir)
        if file:
            self.interpreter_edit.setText(file)

    def get_default_configuration(self) -> ExtConsoleShConfiguration:
        return {
            'interpreter': self.default_shell,
            'interpreter_opts_enabled': False,
            'interpreter_opts': '',
            'script_opts_enabled': False,
            'script_opts': '',
            'close_after_exec': False,
        }

    def set_configuration(self, config: ExtConsoleShConfiguration):
        interpreter = config['interpreter']
        interpreter_opts_enabled = config['interpreter_opts_enabled']
        interpreter_opts = config['interpreter_opts']
        script_opts_enabled = config['script_opts_enabled']
        script_opts = config['script_opts']
        close_after_exec = config['close_after_exec']

        self.interpreter_edit.setText(interpreter)
        self.interpreter_opts_cb.setChecked(interpreter_opts_enabled)
        self.interpreter_opts_edit.setText(interpreter_opts)
        self.script_opts_cb.setChecked(script_opts_enabled)
        self.script_opts_edit.setText(script_opts)
        self.close_after_exec_cb.setChecked(close_after_exec)

    def get_configuration(self) -> ExtConsoleShConfiguration:
        return {
            'interpreter': self.interpreter_edit.text(),
            'interpreter_opts_enabled': self.interpreter_opts_cb.isChecked(),
            'interpreter_opts': self.interpreter_opts_edit.text(),
            'script_opts_enabled': self.script_opts_cb.isChecked(),
            'script_opts': self.script_opts_edit.text(),
            'close_after_exec': self.close_after_exec_cb.isChecked()
        }


def ExternalConsoleShConfiguration(
        default_shell: str,
        shell_args: str = '') -> RunExecutorConfigurationGroupFactory:

    def spawn_console_conf(
            parent, context: Context,
            input_extension: str, input_metadata: RunConfigurationMetadata):
        return GenExternalConsoleShConfiguration(
            default_shell,
            parent,
            context,
            input_extension,
            input_metadata,
            shell_args=shell_args
        )

    return spawn_console_conf

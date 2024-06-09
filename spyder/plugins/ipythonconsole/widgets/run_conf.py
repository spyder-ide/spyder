# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder___init__.py for details)

"""IPython console run executor configuration widget."""

# Standard library imports
import os.path as osp

# Third-party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLineEdit, QRadioButton, QVBoxLayout)

# Local imports
from spyder.api.translations import _
from spyder.plugins.run.api import (
    RunExecutorConfigurationGroup, Context, RunConfigurationMetadata)
from spyder.utils.misc import getcwd_or_home


# Main constants
CURRENT_INTERPRETER = _("Execute in current console")
DEDICATED_INTERPRETER = _("Execute in a dedicated console")
CLEAR_ALL_VARIABLES = _("Remove all variables before execution")
CONSOLE_NAMESPACE = _("Run in console's namespace instead of an empty one")
POST_MORTEM = _("Directly enter debugging when errors appear")


class IPythonConfigOptions(RunExecutorConfigurationGroup):
    """IPython console run configuration options."""

    def __init__(self, parent, context: Context, input_extension: str,
                 input_metadata: RunConfigurationMetadata):
        super().__init__(parent, context, input_extension, input_metadata)

        self.dir = None

        # --- Interpreter ---
        interpreter_group = QGroupBox(_("Console"))
        interpreter_layout = QVBoxLayout(interpreter_group)

        self.current_radio = QRadioButton(CURRENT_INTERPRETER)
        interpreter_layout.addWidget(self.current_radio)

        self.dedicated_radio = QRadioButton(DEDICATED_INTERPRETER)
        interpreter_layout.addWidget(self.dedicated_radio)

        # --- General settings ----
        common_group = QGroupBox(_("Advanced settings"))
        common_layout = QVBoxLayout(common_group)

        self.clear_var_cb = QCheckBox(CLEAR_ALL_VARIABLES)
        common_layout.addWidget(self.clear_var_cb)

        self.console_ns_cb = QCheckBox(CONSOLE_NAMESPACE)
        common_layout.addWidget(self.console_ns_cb)

        self.post_mortem_cb = QCheckBox(POST_MORTEM)
        common_layout.addWidget(self.post_mortem_cb)

        self.clo_cb = QCheckBox(_("Command line options:"))
        self.clo_edit = QLineEdit(self)
        self.clo_edit.setMinimumWidth(300)
        self.clo_cb.toggled.connect(self.clo_edit.setEnabled)
        self.clo_edit.setEnabled(False)

        cli_layout = QHBoxLayout()
        cli_layout.addWidget(self.clo_cb)
        cli_layout.addWidget(self.clo_edit)
        common_layout.addLayout(cli_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
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

    @staticmethod
    def get_default_configuration() -> dict:
        return {
            'current': True,
            'post_mortem': False,
            'python_args_enabled': False,
            'python_args': '',
            'clear_namespace': False,
            'console_namespace': False,
        }

    def set_configuration(self, config: dict):
        use_current_console = config['current']
        post_mortem = config['post_mortem']
        py_args_enabled = config['python_args_enabled']
        py_args = config['python_args']
        clear_namespace = config['clear_namespace']
        console_namespace = config['console_namespace']

        self.current_radio.setChecked(use_current_console)
        self.dedicated_radio.setChecked(not use_current_console)
        self.post_mortem_cb.setChecked(post_mortem)
        self.clo_cb.setChecked(py_args_enabled)
        self.clo_edit.setText(py_args)
        self.clear_var_cb.setChecked(clear_namespace)
        self.console_ns_cb.setChecked(console_namespace)

    def get_configuration(self) -> dict:
        return {
            'current': self.current_radio.isChecked(),
            'post_mortem': self.post_mortem_cb.isChecked(),
            'python_args_enabled': self.clo_cb.isChecked(),
            'python_args': self.clo_edit.text(),
            'clear_namespace': self.clear_var_cb.isChecked(),
            'console_namespace': self.console_ns_cb.isChecked(),
        }

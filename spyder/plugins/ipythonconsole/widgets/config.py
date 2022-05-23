
# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""IPython console run executor configuration widget."""

# Standard library imports
import os.path as osp

# Third-party imports
from qtpy.compat import getexistingdirectory
from qtpy.QtWidgets import (
    QWidget, QRadioButton, QGroupBox, QVBoxLayout, QGridLayout,
    QCheckBox, QLineEdit, QHBoxLayout)

# Local imports
from spyder.api.translations import get_translation
from spyder.plugins.run.api import (
    RunExecutorConfigurationGroup, Context, RunConfigurationMetadata)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import create_toolbutton

# Localization
_ = get_translation("spyder")

RUN_DEFAULT_CONFIG = _("Run file with default configuration")
RUN_CUSTOM_CONFIG = _("Run file with custom configuration")
CURRENT_INTERPRETER = _("Execute in current console")
DEDICATED_INTERPRETER = _("Execute in a dedicated console")
SYSTERM_INTERPRETER = _("Execute in an external system terminal")
CLEAR_ALL_VARIABLES = _("Remove all variables before execution")
CONSOLE_NAMESPACE = _("Run in console's namespace instead of an empty one")
POST_MORTEM = _("Directly enter debugging when errors appear")
INTERACT = _("Interact with the Python console after execution")
FILE_DIR = _("The directory of the file being executed")
CW_DIR = _("The current working directory")
FIXED_DIR = _("The following directory:")
ALWAYS_OPEN_FIRST_RUN = _("Always show %s on a first file run")


class IPythonConfigOptions(RunExecutorConfigurationGroup):
    """IPython console run configuration options."""

    def __init__(self, parent, context: Context,
                 input_extension: str, input_metadata: RunConfigurationMetadata):
        super().__init__(parent, context, input_extension, input_metadata)

        self.dir = None
        # self.runconf = RunConfiguration()
        # firstrun_o = CONF.get('run', ALWAYS_OPEN_FIRST_RUN_OPTION, False)

        # --- Run settings ---
        # self.run_default_config_radio = QRadioButton(RUN_DEFAULT_CONFIG)
        # self.run_custom_config_radio = QRadioButton(RUN_CUSTOM_CONFIG)

        # --- Interpreter ---
        interpreter_group = QGroupBox(_("Console"))
        # interpreter_group.setDisabled(True)

        # self.run_custom_config_radio.toggled.connect(
        #     interpreter_group.setEnabled)

        interpreter_layout = QVBoxLayout(interpreter_group)

        self.current_radio = QRadioButton(CURRENT_INTERPRETER)
        interpreter_layout.addWidget(self.current_radio)

        self.dedicated_radio = QRadioButton(DEDICATED_INTERPRETER)
        interpreter_layout.addWidget(self.dedicated_radio)

        self.systerm_radio = QRadioButton(SYSTERM_INTERPRETER)
        interpreter_layout.addWidget(self.systerm_radio)

        # --- System terminal ---
        external_group = QWidget()
        external_group.setDisabled(True)
        self.systerm_radio.toggled.connect(external_group.setEnabled)

        external_layout = QGridLayout()
        external_group.setLayout(external_layout)
        self.interact_cb = QCheckBox(INTERACT)
        external_layout.addWidget(self.interact_cb, 1, 0, 1, -1)

        self.pclo_cb = QCheckBox(_("Command line options:"))
        external_layout.addWidget(self.pclo_cb, 3, 0)
        self.pclo_edit = QLineEdit()
        self.pclo_cb.toggled.connect(self.pclo_edit.setEnabled)
        self.pclo_edit.setEnabled(False)
        self.pclo_edit.setToolTip(_("<b>-u</b> is added to the "
                                    "other options you set here"))
        external_layout.addWidget(self.pclo_edit, 3, 1)

        interpreter_layout.addWidget(external_group)

        # --- General settings ----
        common_group = QGroupBox(_("General settings"))
        # common_group.setDisabled(True)

        # self.run_custom_config_radio.toggled.connect(common_group.setEnabled)

        common_layout = QGridLayout(common_group)

        self.clear_var_cb = QCheckBox(CLEAR_ALL_VARIABLES)
        common_layout.addWidget(self.clear_var_cb, 0, 0)

        self.console_ns_cb = QCheckBox(CONSOLE_NAMESPACE)
        common_layout.addWidget(self.console_ns_cb, 1, 0)

        self.post_mortem_cb = QCheckBox(POST_MORTEM)
        common_layout.addWidget(self.post_mortem_cb, 2, 0)

        self.clo_cb = QCheckBox(_("Command line options:"))
        common_layout.addWidget(self.clo_cb, 3, 0)
        self.clo_edit = QLineEdit()
        self.clo_cb.toggled.connect(self.clo_edit.setEnabled)
        self.clo_edit.setEnabled(False)
        common_layout.addWidget(self.clo_edit, 3, 1)

        # --- Working directory ---
        # wdir_group = QGroupBox(_("Working directory settings"))
        # wdir_group.setDisabled(True)

        # self.run_custom_config_radio.toggled.connect(wdir_group.setEnabled)

        # wdir_layout = QVBoxLayout(wdir_group)

        # self.file_dir_radio = QRadioButton(FILE_DIR)
        # wdir_layout.addWidget(self.file_dir_radio)

        # self.cwd_radio = QRadioButton(CW_DIR)
        # wdir_layout.addWidget(self.cwd_radio)

        # fixed_dir_layout = QHBoxLayout()
        # self.fixed_dir_radio = QRadioButton(FIXED_DIR)
        # fixed_dir_layout.addWidget(self.fixed_dir_radio)
        # self.wd_edit = QLineEdit()
        # self.fixed_dir_radio.toggled.connect(self.wd_edit.setEnabled)
        # self.wd_edit.setEnabled(False)
        # fixed_dir_layout.addWidget(self.wd_edit)
        # browse_btn = create_toolbutton(
        #     self,
        #     triggered=self.select_directory,
        #     icon=ima.icon('DirOpenIcon'),
        #     tip=_("Select directory")
        #     )
        # fixed_dir_layout.addWidget(browse_btn)
        # wdir_layout.addLayout(fixed_dir_layout)

        # Checkbox to preserve the old behavior, i.e. always open the dialog
        # on first run
        # self.firstrun_cb = QCheckBox(ALWAYS_OPEN_FIRST_RUN % _("this dialog"))
        # self.firstrun_cb.clicked.connect(self.set_firstrun_o)
        # self.firstrun_cb.setChecked(firstrun_o)

        layout = QVBoxLayout(self)
        # layout.addWidget(self.run_default_config_radio)
        # layout.addWidget(self.run_custom_config_radio)
        layout.addWidget(interpreter_group)
        layout.addWidget(common_group)
        # layout.addWidget(wdir_group)
        # layout.addWidget(self.firstrun_cb)
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
            # 'default': True,
            'args/enabled': False,
            'args': '',
            'current': True,
            'systerm': False,
            'interact': False,
            'post_mortem': False,
            'python_args/enabled': False,
            'python_args': '',
            'clear_namespace': False,
            'console_namespace': False,
        }

    def set_configuration(self, config: dict):
        # self.run_default_config_radio.blockSignals(True)
        # self.run_default_config_radio.setChecked(config['default'])
        # self.run_custom_config_radio.setChecked(not config['default'])
        # self.run_default_config_radio.blockSignals(False)

        use_current_console = config['current']
        use_systerm = config['systerm']
        self.current_radio.setChecked(use_current_console)
        self.dedicated_radio.setChecked(not use_current_console and not use_systerm)
        self.systerm_radio.setChecked(use_systerm)

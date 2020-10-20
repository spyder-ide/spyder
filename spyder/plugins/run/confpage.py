# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Run configuration page."""

# Third party imports
from qtpy.QtWidgets import (QButtonGroup, QGroupBox, QHBoxLayout, QLabel,
                            QVBoxLayout)

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import get_translation
from spyder.plugins.run.widgets import (ALWAYS_OPEN_FIRST_RUN,
                                        ALWAYS_OPEN_FIRST_RUN_OPTION,
                                        CLEAR_ALL_VARIABLES,
                                        CONSOLE_NAMESPACE,
                                        CURRENT_INTERPRETER,
                                        CURRENT_INTERPRETER_OPTION, CW_DIR,
                                        DEDICATED_INTERPRETER,
                                        DEDICATED_INTERPRETER_OPTION,
                                        FILE_DIR, FIXED_DIR, INTERACT,
                                        POST_MORTEM, SYSTERM_INTERPRETER,
                                        SYSTERM_INTERPRETER_OPTION,
                                        WDIR_FIXED_DIR_OPTION,
                                        WDIR_USE_CWD_DIR_OPTION,
                                        WDIR_USE_FIXED_DIR_OPTION,
                                        WDIR_USE_SCRIPT_DIR_OPTION)
from spyder.utils.misc import getcwd_or_home

# Localization
_ = get_translation("spyder")


class RunConfigPage(PluginConfigPage):
    """Default Run Settings configuration page."""

    def setup_page(self):
        about_label = QLabel(_("The following are the default options for "
                               "running files.These options may be overriden "
                               "using the <b>Configuration per file</b> entry "
                               "of the <b>Run</b> menu."))
        about_label.setWordWrap(True)

        interpreter_group = QGroupBox(_("Console"))
        interpreter_bg = QButtonGroup(interpreter_group)
        self.current_radio = self.create_radiobutton(
            CURRENT_INTERPRETER,
            CURRENT_INTERPRETER_OPTION,
            True,
            button_group=interpreter_bg)
        self.dedicated_radio = self.create_radiobutton(
            DEDICATED_INTERPRETER,
            DEDICATED_INTERPRETER_OPTION,
            False,
            button_group=interpreter_bg)
        self.systerm_radio = self.create_radiobutton(
            SYSTERM_INTERPRETER,
            SYSTERM_INTERPRETER_OPTION, False,
            button_group=interpreter_bg)

        interpreter_layout = QVBoxLayout()
        interpreter_group.setLayout(interpreter_layout)
        interpreter_layout.addWidget(self.current_radio)
        interpreter_layout.addWidget(self.dedicated_radio)
        interpreter_layout.addWidget(self.systerm_radio)

        general_group = QGroupBox(_("General settings"))
        post_mortem = self.create_checkbox(POST_MORTEM, 'post_mortem', False)
        clear_variables = self.create_checkbox(CLEAR_ALL_VARIABLES,
                                               'clear_namespace', False)
        console_namespace = self.create_checkbox(CONSOLE_NAMESPACE,
                                                 'console_namespace', False)

        general_layout = QVBoxLayout()
        general_layout.addWidget(clear_variables)
        general_layout.addWidget(console_namespace)
        general_layout.addWidget(post_mortem)
        general_group.setLayout(general_layout)

        wdir_group = QGroupBox(_("Working directory settings"))
        wdir_bg = QButtonGroup(wdir_group)
        wdir_label = QLabel(_("Default working directory is:"))
        wdir_label.setWordWrap(True)
        dirname_radio = self.create_radiobutton(
            FILE_DIR,
            WDIR_USE_SCRIPT_DIR_OPTION,
            True,
            button_group=wdir_bg)
        cwd_radio = self.create_radiobutton(
            CW_DIR,
            WDIR_USE_CWD_DIR_OPTION,
            False,
            button_group=wdir_bg)

        thisdir_radio = self.create_radiobutton(
            FIXED_DIR,
            WDIR_USE_FIXED_DIR_OPTION,
            False,
            button_group=wdir_bg)
        thisdir_bd = self.create_browsedir("", WDIR_FIXED_DIR_OPTION,
                                           getcwd_or_home())
        thisdir_radio.toggled.connect(thisdir_bd.setEnabled)
        dirname_radio.toggled.connect(thisdir_bd.setDisabled)
        cwd_radio.toggled.connect(thisdir_bd.setDisabled)
        thisdir_layout = QHBoxLayout()
        thisdir_layout.addWidget(thisdir_radio)
        thisdir_layout.addWidget(thisdir_bd)

        wdir_layout = QVBoxLayout()
        wdir_layout.addWidget(wdir_label)
        wdir_layout.addWidget(dirname_radio)
        wdir_layout.addWidget(cwd_radio)
        wdir_layout.addLayout(thisdir_layout)
        wdir_group.setLayout(wdir_layout)

        external_group = QGroupBox(_("External system terminal"))
        interact_after = self.create_checkbox(INTERACT, 'interact', False)

        external_layout = QVBoxLayout()
        external_layout.addWidget(interact_after)
        external_group.setLayout(external_layout)

        firstrun_cb = self.create_checkbox(
            ALWAYS_OPEN_FIRST_RUN % _("Run Settings dialog"),
            ALWAYS_OPEN_FIRST_RUN_OPTION,
            False)

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(about_label)
        vlayout.addSpacing(10)
        vlayout.addWidget(interpreter_group)
        vlayout.addWidget(general_group)
        vlayout.addWidget(wdir_group)
        vlayout.addWidget(external_group)
        vlayout.addWidget(firstrun_cb)
        vlayout.addStretch(1)

    def apply_settings(self, options):
        pass

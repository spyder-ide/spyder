# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Working Directory Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Third party imports
from qtpy.QtWidgets import (QButtonGroup, QGroupBox, QHBoxLayout, QLabel,
                            QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.api.preferences import PluginConfigPage
from spyder.utils.misc import getcwd_or_home


class WorkingDirectoryConfigPage(PluginConfigPage):
    def setup_page(self):
        about_label = QLabel(_("The <b>current working directory</b> is "
                    "the working directory for IPython consoles "
                    "and the current directory for the File Explorer."))
        about_label.setWordWrap(True)

        startup_group = QGroupBox(_("Startup"))
        startup_bg = QButtonGroup(startup_group)
        startup_label = QLabel(_("At startup, the current working "
                                 "directory is:"))
        startup_label.setWordWrap(True)
        lastdir_radio = self.create_radiobutton(
                                _("The current project directory "
                                  "or user home directory "
                                  "(if no project is active)"),
                                'startup/use_project_or_home_directory',
                                True,
                                _("At startup,"),  # TODO
                                button_group=startup_bg)
        thisdir_radio = self.create_radiobutton(
                                _("The following directory:"),
                                'startup/use_fixed_directory', False,
                                _("At startup, the current working "
                                  "directory will be the specified path"),
                                button_group=startup_bg)
        thisdir_bd = self.create_browsedir("", 'startup/fixed_directory',
                                           getcwd_or_home())
        thisdir_radio.toggled.connect(thisdir_bd.setEnabled)
        lastdir_radio.toggled.connect(thisdir_bd.setDisabled)
        thisdir_layout = QHBoxLayout()
        thisdir_layout.addWidget(thisdir_radio)
        thisdir_layout.addWidget(thisdir_bd)

        startup_layout = QVBoxLayout()
        startup_layout.addWidget(startup_label)
        startup_layout.addWidget(lastdir_radio)
        startup_layout.addLayout(thisdir_layout)
        startup_group.setLayout(startup_layout)

        # Console Directory

        console_group = QGroupBox(_("Console directory"))
        console_label = QLabel(_("The working directory for new consoles is:"))
        console_label.setWordWrap(True)
        console_bg = QButtonGroup(console_group)
        console_project_radio = self.create_radiobutton(
                                _("The current project directory "
                                  "or user home directory "
                                  "(if no project is active)"),
                                'console/use_project_or_home_directory',
                                True,
                                button_group=console_bg)
        console_cwd_radio = self.create_radiobutton(
                                _("The current working directory"),
                                'console/use_cwd',
                                False,
                                button_group=console_bg)

        console_dir_radio = self.create_radiobutton(
                                _("The following directory:"),
                                'console/use_fixed_directory', False,
                                _("The directory when a new console "
                                  "is open will be the specified path"),
                                button_group=console_bg)
        console_dir_bd = self.create_browsedir("", 'console/fixed_directory',
                                               getcwd_or_home())
        console_dir_radio.toggled.connect(console_dir_bd.setEnabled)
        console_project_radio.toggled.connect(console_dir_bd.setDisabled)
        console_cwd_radio.toggled.connect(console_dir_bd.setDisabled)
        console_dir_layout = QHBoxLayout()
        console_dir_layout.addWidget(console_dir_radio)
        console_dir_layout.addWidget(console_dir_bd)

        console_layout = QVBoxLayout()
        console_layout.addWidget(console_label)
        console_layout.addWidget(console_project_radio)
        console_layout.addWidget(console_cwd_radio)
        console_layout.addLayout(console_dir_layout)
        console_group.setLayout(console_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(about_label)
        vlayout.addSpacing(10)
        vlayout.addWidget(startup_group)
        vlayout.addWidget(console_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

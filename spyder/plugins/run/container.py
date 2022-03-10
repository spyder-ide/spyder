# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder run container."""

# Standard library imports

# Third-party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.api.translations import get_translation
from spyder.plugins.run.api import RunActions

# Localization
_ = get_translation('spyder')


class RunContainer(PluginMainContainer):
    """Non-graphical container used to spawn dialogs and creating actions."""


    def setup(self):
        self.run_action = self.create_action(
            RunActions.Run, _('&Run'), self.create_icon('run'),
            tip=_("Run file"), triggered=self.run_file,
            register_shortcut=True, shortcut_context='_')

        self.configure_action = self.create_action(
            RunActions.Configure, _('&Configuration per file...'),
            self.create_icon('run_settings'), tip=_('Run settings'),
            triggered=self.edit_run_configurations, register_shortcut=True,
            shortcut_context='_'
        )

        self.re_run_action = self.create_action(
            RunActions.ReRun, _('Re-run &last script'),
            self.create_icon('run_again'), tip=_('Run again last file'),
            triggered=self.re_run_file, register_shortcut=True,
            shortcut_context='_'
        )

    def update_actions(self):
        pass


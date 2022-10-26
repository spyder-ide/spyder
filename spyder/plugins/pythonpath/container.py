# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pythopath container."""

from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.pythonpath.widgets.pathmanager import PathManager

# Localization
_ = get_translation('spyder')


class PythonpathActions:
    Manager = "manager_action"


class PythonpathContainer(PluginMainContainer):

    # ---- PluginMainContainer API
    def setup(self):

        self.path_manager_dialog = PathManager(self)

        self.path_manager_action = self.create_action(
            PythonpathActions.Manager,
            _("PYTHONPATH manager"),
            icon=self.create_icon('pythonpath'),
            triggered=self.show_path_manager
        )

    def update_actions(self):
        pass

    # ---- Public API
    def show_path_manager(self):
        """Show path manager dialog."""
        self.path_manager_dialog.show()
        self.path_manager_dialog.activateWindow()
        self.path_manager_dialog.raise_()
        self.path_manager_dialog.setFocus()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pythopath container."""

import os.path as osp

from spyder.api.translations import get_translation
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.config.base import get_conf_path
from spyder.plugins.pythonpath.widgets.pathmanager import PathManager
from spyder.utils.environ import get_user_env

# Localization
_ = get_translation('spyder')


class PythonpathActions:
    Manager = "manager_action"


class PythonpathContainer(PluginMainContainer):

    PATH_FILE = get_conf_path('path')
    NOT_ACTIVE_PATH_FILE = get_conf_path('not_active_path')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = ()
        self.not_active_path = ()
        self.project_path = ()

    # ---- PluginMainContainer API
    def setup(self):

        self._load_pythonpath()
        self.path_manager_dialog = PathManager(self, self.path)

        self.path_manager_action = self.create_action(
            PythonpathActions.Manager,
            _("PYTHONPATH manager"),
            icon=self.create_icon('pythonpath'),
            triggered=self.show_path_manager
        )

    def update_actions(self):
        pass

    # ---- Public API
    def update_active_project_path(self, path):
        """Update active project path."""
        if path is None:
            path = ()
        else:
            path = (path,)

        self.project_path = path
        self.path_manager_dialog.project_path = path

    def show_path_manager(self):
        """Show path manager dialog."""
        self.path_manager_dialog.setup()
        self.path_manager_dialog.show()
        self.path_manager_dialog.activateWindow()
        self.path_manager_dialog.raise_()
        self.path_manager_dialog.setFocus()

    # ---- Private API
    def _load_pythonpath(self):
        """Load Python paths."""
        # Get current system PYTHONPATH
        env = get_user_env()
        system_path = env.get('PYTHONPATH', [])
        if not isinstance(system_path, list):
            system_path = [system_path]
        system_path = reversed(system_path)

        # Get previous system PYTHONPATH
        previous_system_path = self.get_conf('system_path', default=())

        # Load all paths
        if osp.isfile(self.PATH_FILE):
            with open(self.PATH_FILE, 'r', encoding='utf-8') as f:
                previous_paths = f.read().splitlines()

            paths = []
            for path in previous_paths:
                # Path was removed since last time or it's not a directory
                # anymore
                if not osp.isdir(path):
                    continue

                # Path was removed from system path
                if path in previous_system_path and path not in system_path:
                    continue

                paths.append(path)

            self.path = tuple(paths)

        # Add system path
        if system_path:
            self.path = (
                self.path +
                tuple(p for p in system_path if osp.isdir(p))
            )

        # Load not active paths
        if osp.isfile(self.NOT_ACTIVE_PATH_FILE):
            with open(self.NOT_ACTIVE_PATH_FILE, 'r', encoding='utf-8') as f:
                not_active_path = f.read().splitlines()
            self.not_active_path = tuple(name for name in not_active_path
                                         if osp.isdir(name))

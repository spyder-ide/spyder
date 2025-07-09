# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pythopath container."""

from collections import OrderedDict
import logging
import os
import os.path as osp

from qtpy.QtCore import Signal

from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.config.base import get_conf_path
from spyder.plugins.pythonpath.utils import get_system_pythonpath
from spyder.plugins.pythonpath.widgets.pathmanager import PathManager


# Logging
logger = logging.getLogger(__name__)


# ---- Constants
# -----------------------------------------------------------------------------
class PythonpathActions:
    Manager = "manager_action"


# ---- Container
# -----------------------------------------------------------------------------
class PythonpathContainer(PluginMainContainer):

    sig_pythonpath_changed = Signal(object, bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        # Migrate to new config options if necessary
        if not self.get_conf("config_options_migrated", False):
            self._migrate_to_config_options()

        # This attribute is only used to detect changes and after initializing
        # here should only be set in update_active_project_path.
        self._project_path = OrderedDict()

        # These attributes are only used to detect changes and after
        # initializing here should only be set in _save_paths.
        self._user_paths = OrderedDict(self.get_conf('user_paths'))
        self._system_paths = self.get_conf('system_paths')
        self._prioritize = self.get_conf('prioritize')
        self._spyder_pythonpath = self.get_conf('spyder_pythonpath')

        # Path manager dialog
        self.path_manager_dialog = PathManager(parent=self, sync=True)
        self.path_manager_dialog.sig_path_changed.connect(
            self._save_paths
        )
        self.path_manager_dialog.redirect_stdio.connect(
            self.sig_redirect_stdio_requested)

        # Path manager action
        self.path_manager_action = self.create_action(
            PythonpathActions.Manager,
            _("PYTHONPATH manager"),
            icon=self.create_icon('pythonpath'),
            triggered=self.show_path_manager
        )

    def update_actions(self):
        pass

    # ---- Public API
    # -------------------------------------------------------------------------
    def update_active_project_path(self, path):
        """
        Update active project path.

        _project_path is set in this method and nowhere else.
        """
        # _project_path should be reset whenever it is updated.
        self._project_path = OrderedDict()
        if path is None:
            logger.debug("Update Spyder PYTHONPATH because project was closed")
        else:
            logger.debug(f"Add project paths to Spyder PYTHONPATH: {path}")
            self._project_path.update({path: True})

        self._save_paths()

    def show_path_manager(self):
        """
        Show path manager dialog.
        """
        # Do not update paths if widget is already open,
        # see spyder-ide/spyder#20808.
        if not self.path_manager_dialog.isVisible():
            self.path_manager_dialog.update_paths(
                project_path=self._project_path,
                user_paths=self._user_paths,
                system_paths=self._system_paths,
                prioritize=self._prioritize
            )

        # Show and give it focus
        self.path_manager_dialog.show()
        self.path_manager_dialog.activateWindow()
        self.path_manager_dialog.raise_()
        self.path_manager_dialog.setFocus()

    def get_spyder_pythonpath(self):
        """Return active Spyder PYTHONPATH as a list of paths."""
        # Desired behavior is project_path | user_paths | system_paths, but
        # Python 3.8 does not support | operator for OrderedDict.
        all_paths = OrderedDict(reversed(self._system_paths.items()))
        all_paths.update(reversed(self._user_paths.items()))
        all_paths.update(reversed(self._project_path.items()))
        all_paths = OrderedDict(reversed(all_paths.items()))

        return [p for p, v in all_paths.items() if v]

    # ---- Private API
    # -------------------------------------------------------------------------
    def _get_system_paths(self):
        system_paths = get_system_pythonpath()
        conf_system_paths = self.get_conf('system_paths', {})

        # If a system path already exists in the configuration, use the
        # configuration active state. If it does not exist in the
        # configuration, then set the active state to True.
        system_paths = OrderedDict(
            {p: conf_system_paths.get(p, True) for p in system_paths}
        )

        return system_paths

    def _save_paths(self, user_paths=None, system_paths=None, prioritize=None):
        """
        Save user and system path dictionaries and prioritize to config.

        Parameters
        ----------
        user_paths: OrderedDict
            Paths set by the user.
        system_paths: OrderedDict
            Paths set in the PYTHONPATH environment variable.
        prioritize: bool
            Whether paths should be prepended (True) or appended (False) to
            sys.path.

        Notes
        -----
        - Each dictionary key is a path and the value is the active state.
        - sig_pythonpath_changed is emitted from this method, and nowhere else,
        on condition that _spyder_pythonpath changed.

        """
        assert isinstance(user_paths, (type(None), OrderedDict))
        assert isinstance(system_paths, (type(None), OrderedDict))
        assert isinstance(prioritize, (type(None), bool))

        emit = False

        # Don't set options unless necessary
        if user_paths is not None and user_paths != self._user_paths:
            logger.debug(f"Saving user paths: {user_paths}")
            self.set_conf('user_paths', dict(user_paths))
            self._user_paths = user_paths

        if system_paths is not None and system_paths != self._system_paths:
            logger.debug(f"Saving system paths: {system_paths}")
            self.set_conf('system_paths', dict(system_paths))
            self._system_paths = system_paths

        if prioritize is not None and prioritize != self._prioritize:
            logger.debug(f"Saving prioritize: {prioritize}")
            self.set_conf('prioritize', prioritize)
            self._prioritize = prioritize
            emit = True

        spyder_pythonpath = self.get_spyder_pythonpath()
        if spyder_pythonpath != self._spyder_pythonpath:
            logger.debug(f"Saving Spyder pythonpath: {spyder_pythonpath}")
            self.set_conf('spyder_pythonpath', spyder_pythonpath)
            self._spyder_pythonpath = spyder_pythonpath
            emit = True

        # Only emit signal if spyder_pythonpath or prioritize changed
        if emit:
            self.sig_pythonpath_changed.emit(
                self._spyder_pythonpath, self._prioritize
            )

    def _migrate_to_config_options(self):
        """
        Migrate paths saved in the `path` and `not_active_path` files located
        in our config directory to our config system.

        # TODO: Remove for Spyder 7
        """
        path_file = get_conf_path('path')
        not_active_path_file = get_conf_path('not_active_path')
        config_path = self.get_conf('path', ())
        config_not_active_path = self.get_conf('not_active_path', ())
        system_path = self.get_conf('system_path', ())

        path = []
        not_active_path = []

        # Get path from file
        if osp.isfile(path_file):
            with open(path_file, 'r', encoding='utf-8') as f:
                path = f.read().splitlines()
            try:
                os.remove(path_file)
            except OSError:
                pass

        # Get inactive paths from file
        if osp.isfile(not_active_path_file):
            with open(not_active_path_file, 'r', encoding='utf-8') as f:
                not_active_path = f.read().splitlines()
            try:
                os.remove(not_active_path_file)
            except OSError:
                pass

        # Get path from config; supersedes paths from file
        if config_path:
            path = config_path

        # Get inactive path from config; supersedes paths from file
        if config_not_active_path is not None:
            not_active_path = config_not_active_path

        # Get system path
        system_paths = {}
        if system_path:
            system_paths = {p: p not in not_active_path for p in system_path}

        # path config has all user and system paths; only want user paths
        user_paths = {
            p: p not in not_active_path for p in path if p not in system_path
        }


        # Update the configuration
        self.set_conf('user_paths', user_paths)
        self.set_conf('system_paths', system_paths)

        # Do not migrate again
        self.set_conf("config_options_migrated", True)

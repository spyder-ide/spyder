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

    sig_pythonpath_changed = Signal(object, object, bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        # Load Python paths
        self._load_paths()

        # Path manager dialog
        self.path_manager_dialog = PathManager(parent=self, sync=True)
        self.path_manager_dialog.sig_path_changed.connect(
            self._update_python_path)
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

    def on_close(self):
        # Save current system path to detect changes next time Spyder starts
        self.set_conf('system_path', get_system_pythonpath())

    # ---- Public API
    # -------------------------------------------------------------------------
    def update_active_project_path(self, path):
        """Update active project path."""
        if path is None:
            logger.debug("Update Pythonpath because project was closed")
            path = ()
        else:
            logger.debug(f"Add to Pythonpath project's path -> {path}")
            path = (path,)

        # Old path
        old_path = self.get_spyder_pythonpath()

        # Change project path
        self.project_path = path
        self.path_manager_dialog.project_path = path

        # New path
        new_path = self.get_spyder_pythonpath()

        prioritize = self.get_conf('prioritize', default=False)

        # Update path
        self.set_conf('spyder_pythonpath', new_path)
        self.sig_pythonpath_changed.emit(old_path, new_path, prioritize)

    def show_path_manager(self):
        """Show path manager dialog."""
        # Do not update paths or run setup if widget is already open,
        # see spyder-ide/spyder#20808
        if not self.path_manager_dialog.isVisible():
            # Set main attributes saved here
            self.path_manager_dialog.update_paths(
                self.path, self.not_active_path, get_system_pythonpath()
            )

            # Setup its contents again
            self.path_manager_dialog.setup()

        # Show and give it focus
        self.path_manager_dialog.show()
        self.path_manager_dialog.activateWindow()
        self.path_manager_dialog.raise_()
        self.path_manager_dialog.setFocus()

    def get_spyder_pythonpath(self):
        """
        Return active Spyder PYTHONPATH plus project path as a list of paths.
        """
        path_dict = self._get_spyder_pythonpath_dict()
        path = [k for k, v in path_dict.items() if v]
        return path

    # ---- Private API
    # -------------------------------------------------------------------------
    def _load_paths(self):
        """Load Python paths.

        The attributes _project_paths, _user_paths, _system_paths, _prioritize,
        and _spyder_pythonpath, are initialize here and should be updated only
        in _save_paths. They are only used to detect changes.
        """
        self._project_paths = OrderedDict()
        self._user_paths = OrderedDict()
        self._system_paths = OrderedDict()
        self._prioritize = False
        self._spyder_pythonpath = []

        # Get user paths. Check migration from old conf files
        user_paths = self._migrate_to_config_options()
        if user_paths is None:
            user_paths = self.get_conf('user_paths', {})
        user_paths = OrderedDict(user_paths)

        # Get current system PYTHONPATH
        system_paths = self._get_system_paths()

        # Get prioritize
        prioritize = self.get_conf('prioritize', False)

        self._save_paths(user_paths, system_paths, prioritize)

    def _get_system_paths(self):
        system_paths = get_system_pythonpath()
        conf_system_paths = self.get_conf('system_paths', {})

        system_paths = OrderedDict(
            {p: conf_system_paths.get(p, True) for p in system_paths}
        )

        return system_paths

    def _save_paths(self, new_path_dict, new_prioritize):
        """
        Save tuples for all paths and not active ones to config system and
        update their associated attributes.

        `new_path_dict` is an OrderedDict that has the new paths as keys and
        the state as values. The state is `True` for active and `False` for
        inactive.

        `prioritize` is a boolean indicating whether paths should be
        prioritized over sys.path.
        """
        path = tuple(p for p in new_path_dict)
        not_active_path = tuple(
            p for p in new_path_dict if not new_path_dict[p]
        )
        old_spyder_pythonpath = self.get_spyder_pythonpath()

        # Don't set options unless necessary
        if path != self.path:
            logger.debug(f"Saving path: {path}")
            self.set_conf('path', path)
            self.path = path

        if not_active_path != self.not_active_path:
            logger.debug(f"Saving inactive paths: {not_active_path}")
            self.set_conf('not_active_path', not_active_path)
            self.not_active_path = not_active_path

        if new_prioritize != self.prioritize:
            logger.debug(f"Saving prioritize: {new_prioritize}")
            self.set_conf('prioritize', new_prioritize)
            self.prioritize = new_prioritize

        new_spyder_pythonpath = self.get_spyder_pythonpath()
        if new_spyder_pythonpath != old_spyder_pythonpath:
            logger.debug(f"Saving Spyder pythonpath: {new_spyder_pythonpath}")
            self.set_conf('spyder_pythonpath', new_spyder_pythonpath)

    def _get_spyder_pythonpath_dict(self):
        """
        Return Spyder PYTHONPATH plus project path as dictionary of paths.

        The returned ordered dictionary has the paths as keys and the state
        as values. The state is `True` for active and `False` for inactive.

        Example:
            OrderedDict([('/some/path, True), ('/some/other/path, False)])
        """
        path_dict = OrderedDict()

        # Make project path to be the first one so that modules developed in a
        # project are not shadowed by those present in other paths.
        for path in self.project_path:
            path_dict[path] = True

        for path in self.path:
            path_dict[path] = path not in self.not_active_path

        return path_dict

    def _update_python_path(self, new_path_dict=None, new_prioritize=None):
        """
        Update Python path on language server and kernels.

        The `new_path_dict` should not include the project path.
        """
        # Load existing path plus project path
        old_path = self.get_spyder_pythonpath()
        old_prioritize = self.prioritize

        # Save new path
        if new_path_dict is not None or new_prioritize is not None:
            self._save_paths(new_path_dict, new_prioritize)

        # Load new path plus project path
        new_path = self.get_spyder_pythonpath()

        # Do not notify observers unless necessary
        if (
            new_path != old_path
            or new_prioritize != old_prioritize
        ):
            self.sig_pythonpath_changed.emit(
                old_path, new_path, new_prioritize
            )

    def _migrate_to_config_options(self):
        """
        Migrate paths saved in the `path` and `not_active_path` files located
        in our config directory to our config system.

        This was the way we save those paths in Spyder 5 and before.
        """
        path_file = get_conf_path('path')
        not_active_path_file = get_conf_path('not_active_path')
        config_path = self.get_conf('path', None)
        config_not_active_path = self.get_conf('not_active_path', None)
        paths_in_conf_files = self.get_conf('paths_in_conf_files', None)
        system_path = self.get_conf('system_path', None)

        if (
            not osp.isfile(path_file)
            and not osp.isfile(not_active_path_file)
            and config_path is not None
            and config_not_active_path is not None
            and paths_in_conf_files is not None
            and system_path is not None
        ):
            # The configuration does not need to be updated
            return None

        path = []
        not_active_path = []

        # Get path from file
        if osp.isfile(path_file):
            with open(path_file, 'r', encoding='utf-8') as f:
                path = f.read().splitlines()
            os.remove(path_file)

        # Get inactive paths from file
        if osp.isfile(not_active_path_file):
            with open(not_active_path_file, 'r', encoding='utf-8') as f:
                not_active_path = f.read().splitlines()
            os.remove(not_active_path_file)

        # Get path from config; supercedes paths from file
        if config_path is not None:
            path = config_path
            self.remove_conf('path')

        # Get inactive path from config; supercedes paths from file
        if config_not_active_path is not None:
            not_active_path = config_not_active_path
            self.remove_conf('not_active_path')

        if paths_in_conf_files is not None:
            self.remove_conf('paths_in_conf_files')

        # Get system path
        if system_path is not None:
            self.remove_conf('system_path')

        # path config has all user and system paths; only want user paths
        user_paths = {
            p: p not in not_active_path for p in path if p not in system_path
        }

        return user_paths

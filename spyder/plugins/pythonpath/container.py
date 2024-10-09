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
        # Load Python paths
        self._load_paths()

        # Path manager dialog
        self.path_manager_dialog = PathManager(parent=self, sync=True)
        self.path_manager_dialog.sig_path_changed.connect(
            self._save_paths)
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
        """Update active project path.

        _project_paths is initialized in _load_paths, but set in this method
        and nowhere else.
        """
        # _project_paths should be reset whenever it is updated.
        self._project_paths = OrderedDict()
        if path is None:
            logger.debug("Update Spyder PYTHONPATH because project was closed")
        else:
            logger.debug(f"Add project paths to Spyder PYTHONPATH: {path}")
            path = [path] if isinstance(path, str) else path
            self._project_paths.update({p: True for p in path})

        self._save_paths()

    def show_path_manager(self):
        """Show path manager dialog.

        Send the most up-to-date system paths to the dialog in case they have
        changed. But do not _save_paths until after the dialog exits, in order
        to consolidate possible changes and avoid emitting multiple signals.
        This requires that the dialog return its original paths on cancel or
        close.
        """
        # Do not update paths if widget is already open,
        # see spyder-ide/spyder#20808.
        if not self.path_manager_dialog.isVisible():
            self.path_manager_dialog.update_paths(
                project_paths=self._project_paths,
                user_paths=self._user_paths,
                system_paths=self._get_system_paths(),
                prioritize=self._prioritize
            )

        # Show and give it focus
        self.path_manager_dialog.show()
        self.path_manager_dialog.activateWindow()
        self.path_manager_dialog.raise_()
        self.path_manager_dialog.setFocus()

    def get_spyder_pythonpath(self):
        """Return active Spyder PYTHONPATH as a list of paths."""
        # Desired behavior is project_paths | user_paths | system_paths, but
        # Python 3.8 does not support | operator for OrderedDict.
        all_paths = OrderedDict(reversed(self._system_paths.items()))
        all_paths.update(reversed(self._user_paths.items()))
        all_paths.update(reversed(self._project_paths.items()))
        all_paths = OrderedDict(reversed(all_paths.items()))

        return [p for p, v in all_paths.items() if v]

    # ---- Private API
    # -------------------------------------------------------------------------
    def _load_paths(self):
        """Load Python paths.

        The attributes _project_paths, _user_paths, _system_paths, _prioritize,
        and _spyder_pythonpath, are initialized here. All but _project_paths
        should be updated only in _save_paths. They are only used to detect
        changes.
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

    def _save_paths(self, user_paths=None, system_paths=None, prioritize=None):
        """
        Save user and system path dictionaries to config and prioritize to
        config. Each dictionary key is a path and the value is the active
        state.

        `user_paths` is user paths. `system_paths` is system paths, and
        `prioritize` is a boolean indicating whether paths should be
        prepended (True) or appended (False) to sys.path.

        sig_pythonpath_changed is emitted from this method, and nowhere else,
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

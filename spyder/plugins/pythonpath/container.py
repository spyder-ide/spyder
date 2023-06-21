# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pythopath container."""

from collections import OrderedDict
import logging
import os.path as osp

from qtpy.QtCore import Signal

from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.config.base import get_conf_path
from spyder.plugins.pythonpath.utils import get_system_pythonpath
from spyder.plugins.pythonpath.widgets.pathmanager import PathManager
from spyder.utils import encoding


# Logging
logger = logging.getLogger(__name__)


# ---- Constants
# -----------------------------------------------------------------------------
class PythonpathActions:
    Manager = "manager_action"


# ---- Container
# -----------------------------------------------------------------------------
class PythonpathContainer(PluginMainContainer):

    PATH_FILE = get_conf_path('path')
    NOT_ACTIVE_PATH_FILE = get_conf_path('not_active_path')

    sig_pythonpath_changed = Signal(object, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = ()
        self.not_active_path = ()
        self.project_path = ()

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):

        # Load Python path
        self._load_pythonpath()

        # Save current Pythonpath at startup so plugins can use it afterwards
        self.set_conf('spyder_pythonpath', self.get_spyder_pythonpath())

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
        old_path_dict_p = self._get_spyder_pythonpath_dict()

        # Change project path
        self.project_path = path
        self.path_manager_dialog.project_path = path

        # New path
        new_path_dict_p = self._get_spyder_pythonpath_dict()

        # Update path
        self.set_conf('spyder_pythonpath', self.get_spyder_pythonpath())
        self.sig_pythonpath_changed.emit(old_path_dict_p, new_path_dict_p)

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
    def _load_pythonpath(self):
        """Load Python paths."""
        # Get current system PYTHONPATH
        system_path = get_system_pythonpath()

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

        # Update path file contents. This avoids loading paths that were
        # removed in this session in later ones.
        try:
            encoding.writelines(self.path, self.PATH_FILE)
        except OSError as e:
            logger.error(str(e))

        # Update system path so that path_manager_dialog can work with its
        # latest contents.
        self.set_conf('system_path', system_path)

        # Add system path
        if system_path:
            self.path = self.path + system_path

        # Load not active paths
        if osp.isfile(self.NOT_ACTIVE_PATH_FILE):
            with open(self.NOT_ACTIVE_PATH_FILE, 'r', encoding='utf-8') as f:
                not_active_path = f.read().splitlines()
            self.not_active_path = tuple(name for name in not_active_path
                                         if osp.isdir(name))

    def _save_python_path(self, new_path_dict):
        """
        Save Spyder PYTHONPATH to configuration folder and update attributes.

        `new_path_dict` is an OrderedDict that has the new paths as keys and
        the state as values. The state is `True` for active and `False` for
        inactive.
        """
        path = tuple(p for p in new_path_dict)
        not_active_path = tuple(p for p in new_path_dict
                                if not new_path_dict[p])

        if path != self.path or not_active_path != self.not_active_path:
            # Do not write unless necessary
            try:
                encoding.writelines(path, self.PATH_FILE)
                encoding.writelines(not_active_path,
                                    self.NOT_ACTIVE_PATH_FILE)
            except OSError as e:
                logger.error(str(e))

            self.path = path
            self.not_active_path = not_active_path

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

    def _update_python_path(self, new_path_dict=None):
        """
        Update Python path on language server and kernels.

        The new_path_dict should not include the project path.
        """
        # Load existing path plus project path
        old_path_dict_p = self._get_spyder_pythonpath_dict()

        # Save new path
        if new_path_dict is not None:
            self._save_python_path(new_path_dict)

        # Load new path plus project path
        new_path_dict_p = self._get_spyder_pythonpath_dict()

        # Do not notify observers unless necessary
        if new_path_dict_p != old_path_dict_p:
            pypath = self.get_spyder_pythonpath()
            logger.debug(f"Update Pythonpath to {pypath}")
            self.set_conf('spyder_pythonpath', pypath)
            self.sig_pythonpath_changed.emit(old_path_dict_p, new_path_dict_p)

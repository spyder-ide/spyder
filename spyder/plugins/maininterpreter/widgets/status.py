# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main interpreter status widget."""

# Standard library imports
import os
import os.path as osp
import sys

# Third party imports
from qtpy.QtCore import QTimer, Signal

# Local imports
from spyder.api.widgets.status import BaseTimerStatus
from spyder.config.base import is_pynsist, running_in_mac_app
from spyder.utils.conda import get_list_conda_envs
from spyder.utils.programs import get_interpreter_info
from spyder.utils.pyenv import get_list_pyenv_envs
from spyder.utils.workers import WorkerManager


class InterpreterStatus(BaseTimerStatus):
    """Status bar widget for displaying the current conda environment."""
    ID = 'interpreter_status'
    CONF_SECTION = 'main_interpreter'

    sig_open_preferences_requested = Signal()
    """
    Signal to open the main interpreter preferences.
    """

    def __init__(self, parent, icon=None, interpreter=None):
        """Status bar widget for displaying the current conda environment."""
        self._interpreter = interpreter
        super().__init__(parent)
        self.main = parent
        self.env_actions = []
        self.path_to_env = {}
        self.envs = {}
        self.value = ''
        self.default_interpreter = sys.executable

        if is_pynsist():
            # Be sure to use 'python' executable instead of 'pythonw' since
            # no output is generated with 'pythonw'.
            self.default_interpreter = self.default_interpreter.replace(
                'pythonw.exe', 'python.exe').lower()

        # Worker to compute envs in a thread
        self._worker_manager = WorkerManager(max_threads=1)

        # Timer to get envs every minute
        self._get_envs_timer = QTimer(self)
        self._get_envs_timer.setInterval(60000)
        self._get_envs_timer.timeout.connect(self.get_envs)
        self._get_envs_timer.start()

        # Update the list of envs at startup
        self.get_envs()

    # ---- BaseTimerStatus API
    def get_value(self):
        """
        Switch to default interpreter if current env was removed or
        update Python version of current one.
        """
        env_dir = self._get_env_dir(self._interpreter)

        if not osp.isdir(env_dir):
            # Env was removed on Mac or Linux
            self._on_interpreter_removed()
        elif not osp.isfile(self._interpreter):
            # This can happen on Windows because the interpreter was
            # renamed to .conda_trash
            if not osp.isdir(osp.join(env_dir, 'conda-meta')):
                # If conda-meta is missing, it means the env was removed
                self._on_interpreter_removed()
            else:
                # If not, it means the interpreter is being updated so
                # we need to update its version
                self.get_envs()
        else:
            # We need to do this in case the Python version was
            # changed in the env
            if self._interpreter in self.path_to_env:
                self.update_interpreter()

        return self.value

    # ---- Qt reimplemented methods
    def closeEvent(self, event):
        self._get_envs_timer.stop()
        self._worker_manager.terminate_all()
        super().closeEvent(event)

    # ---- Private API
    def _get_env_dir(self, interpreter):
        """Get env directory from interpreter executable."""
        if os.name == 'nt':
            return osp.dirname(interpreter)
        else:
            return osp.dirname(osp.dirname(interpreter))

    def _get_envs(self):
        """Get the list of environments in the system."""
        # Compute info of default interpreter to have it available in
        # case we need to switch to it. This will avoid lags when
        # doing that in get_value.
        if self.default_interpreter not in self.path_to_env:
            self._get_env_info(self.default_interpreter)

        # Get envs
        conda_env = get_list_conda_envs()
        pyenv_env = get_list_pyenv_envs()
        return {**conda_env, **pyenv_env}

    def _get_env_info(self, path):
        """Get environment information."""
        path = path.lower() if os.name == 'nt' else path

        try:
            name = self.path_to_env[path]
        except KeyError:
            if (
                self.default_interpreter == path
                and (running_in_mac_app() or is_pynsist())
            ):
                name = 'internal'
            elif 'conda' in path:
                name = 'conda'
            elif 'pyenv' in path:
                name = 'pyenv'
            else:
                name = 'custom'
            version = get_interpreter_info(path)
            self.path_to_env[path] = name
            self.envs[name] = (path, version)

        __, version = self.envs[name]
        return f'{name} ({version})'

    def _on_interpreter_removed(self):
        """
        Actions to take when the current custom interpreter is removed
        outside Spyder.
        """
        # NOTES:
        # 1. The interpreter will be updated when the option changes below
        # generate a change in the 'executable' one in the container.
        # 2. *Do not* change the order in which these options are set or the
        # interpreter won't be updated correctly.
        self.set_conf('custom_interpreter', ' ')
        self.set_conf('custom', False)
        self.set_conf('default', True)

    # ---- Public API
    def get_envs(self):
        """
        Get the list of environments in a thread to keep them up to
        date.
        """
        self._worker_manager.terminate_all()
        worker = self._worker_manager.create_python_worker(self._get_envs)
        worker.sig_finished.connect(self.update_envs)
        worker.start()

    def update_envs(self, worker, output, error):
        """Update the list of environments in the system."""
        # This is necessary to avoid an error when the worker can't return a
        # proper output.
        # Fixes spyder-ide/spyder#20539
        if output is not None:
            self.envs.update(**output)

        for env in list(self.envs.keys()):
            path, version = self.envs[env]
            # Save paths in lowercase on Windows to avoid issues with
            # capitalization.
            path = path.lower() if os.name == 'nt' else path
            self.path_to_env[path] = env

        self.update_interpreter()

    def open_interpreter_preferences(self):
        """Request to open the main interpreter preferences."""
        self.sig_open_preferences_requested.emit()

    def update_interpreter(self, interpreter=None):
        """Set main interpreter and update information."""
        if interpreter:
            self._interpreter = interpreter
        self.value = self._get_env_info(self._interpreter)
        self.set_value(self.value)

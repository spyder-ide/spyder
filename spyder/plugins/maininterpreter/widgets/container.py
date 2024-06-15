# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main interpreter container."""

# Standard library imports
import os
import os.path as osp
import sys

# Third-party imports
from qtpy.QtCore import QTimer, Signal

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.config.base import is_conda_based_app
from spyder.plugins.maininterpreter.widgets.status import InterpreterStatus
from spyder.utils.envs import get_list_envs
from spyder.utils.misc import get_python_executable
from spyder.utils.programs import get_interpreter_info
from spyder.utils.workers import WorkerManager


class MainInterpreterContainer(PluginMainContainer):

    sig_open_preferences_requested = Signal()
    """
    Signal to open the main interpreter preferences.
    """

    sig_interpreter_changed = Signal()
    """
    Signal to report that the interpreter has changed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._interpreter = self.get_main_interpreter()
        self.path_to_env = {}
        self.envs = {}
        self.default_interpreter = sys.executable

        if os.name == 'nt' and is_conda_based_app():
            # Be sure to use 'python' executable instead of 'pythonw' since
            # no output is generated with 'pythonw'.
            self.default_interpreter = self.default_interpreter.replace(
                "pythonw.exe", "python.exe"
            ).lower()

        # Worker to compute envs in a thread
        self._worker_manager = WorkerManager(max_threads=1)

        # Timer to get envs every minute
        self._get_envs_timer = QTimer(self)
        self._get_envs_timer.setInterval(60000)
        self._get_envs_timer.timeout.connect(self._get_envs)
        self._get_envs_timer.start()

        self._check_interpreter_timer = QTimer(self)
        self._check_interpreter_timer .setInterval(2000)
        self._check_interpreter_timer.start(2000)

        # Update the list of envs at startup
        self._get_envs()

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        self.interpreter_status = InterpreterStatus(parent=self)
        self.interpreter_status.sig_open_preferences_requested.connect(
            self.sig_open_preferences_requested)

    def update_actions(self):
        pass

    @on_conf_change(option=['default', 'custom_interpreter', 'custom'])
    def on_interpreter_changed(self, option, value):
        if (option == "default" and value) or (
            option == "custom" and not value
        ):
            executable = get_python_executable()
        else:
            executable = osp.normpath(self.get_conf('custom_interpreter'))
            self.add_to_custom_interpreters(executable)

        # Setting executable option that will be used by other plugins in Spyder.
        if executable != self.get_conf('executable'):
            self.set_conf('executable', executable)

    @on_conf_change(option=['executable'])
    def on_executable_changed(self, value):
        # announce update
        self._update_status()
        self.sig_interpreter_changed.emit()

    def on_close(self):
        self._get_envs_timer.stop()
        self._check_interpreter_timer.stop()
        self._worker_manager.terminate_all()

    # ---- Public API
    # -------------------------------------------------------------------------
    def get_main_interpreter(self):
        return self.get_conf('executable', get_python_executable())

    def add_to_custom_interpreters(self, interpreter):
        """Add a new interpreter to the list of saved ones."""
        custom_list = self.get_conf('custom_interpreters_list')
        if interpreter not in custom_list:
            custom_list.append(interpreter)
            self.set_conf('custom_interpreters_list', custom_list)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _update_status(self):
        """Update status widget."""
        self._update_interpreter(self.get_main_interpreter())

    def _get_envs(self):
        """
        Get the list of environments in a thread to keep them up to date.
        """
        self._worker_manager.terminate_all()

        # Compute info of default interpreter to have it available in case we
        # need to switch to it. This will avoid lags when doing that in
        # _check_interpreter.
        if self.default_interpreter not in self.path_to_env:
            default_worker = self._worker_manager.create_python_worker(
                self._get_env_info,
                self.default_interpreter
            )
            default_worker.start()

        worker = self._worker_manager.create_python_worker(get_list_envs)
        worker.sig_finished.connect(self._update_envs)
        worker.start()

    def _update_envs(self, worker, output, error):
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

        self._update_interpreter()

    def _update_interpreter(self, interpreter=None):
        """Set main interpreter and update information."""
        if interpreter:
            self._interpreter = interpreter
        value = self._get_env_info(self._interpreter)
        self.interpreter_status.set_value(value)

    def _get_env_info(self, path):
        """Get environment information."""
        path = path.lower() if os.name == 'nt' else path

        try:
            name = self.path_to_env[path]
        except KeyError:
            if self.default_interpreter == path and is_conda_based_app():
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

    def _check_interpreter(self):
        """
        Switch to default interpreter if current env was removed or update
        Python version of current one.
        """
        env_dir = self._get_env_dir(self._interpreter)

        if not osp.isdir(env_dir):
            # Env was removed on Mac or Linux
            self._on_interpreter_removed()
        elif not osp.isfile(self._interpreter):
            # This can happen on Windows because the interpreter was renamed to
            # .conda_trash
            if not osp.isdir(osp.join(env_dir, 'conda-meta')):
                # If conda-meta is missing, it means the env was removed
                self._on_interpreter_removed()
            else:
                # If not, it means the interpreter is being updated so we need
                # to update its version
                self._get_envs()
        else:
            # We need to do this in case the Python version was changed in the
            # env
            if self._interpreter in self.path_to_env:
                self._update_interpreter()

    def _get_env_dir(self, interpreter):
        """Get env directory from interpreter executable."""
        if os.name == 'nt':
            return osp.dirname(interpreter)
        else:
            return osp.dirname(osp.dirname(interpreter))

    def _on_interpreter_removed(self):
        """
        Actions to take when the current custom interpreter is removed
        outside Spyder.
        """
        # NOTES:
        # 1. The interpreter will be updated when the option changes below
        # generate a change in the 'executable' ooption.
        # 2. *Do not* change the order in which these options are set or the
        # interpreter won't be updated correctly.
        self.set_conf('custom_interpreter', ' ')
        self.set_conf('custom', False)
        self.set_conf('default', True)

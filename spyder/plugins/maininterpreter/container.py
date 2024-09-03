# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main interpreter container."""

# Standard library imports
import logging
import os
import os.path as osp
import sys

# Third-party imports
from qtpy.QtCore import QMutex, QMutexLocker, QTimer, Signal
from spyder_kernels.utils.pythonenv import get_env_dir

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.config.base import is_conda_based_app
from spyder.utils.envs import get_list_envs
from spyder.utils.misc import get_python_executable
from spyder.utils.programs import get_interpreter_info
from spyder.utils.workers import WorkerManager


logger = logging.getLogger(__name__)


class MainInterpreterContainer(PluginMainContainer):

    sig_interpreter_changed = Signal(str)
    """
    Signal to report that the main interpreter has changed.

    Parameters
    ----------
    path: str
        Path to the new interpreter.
    """

    sig_environments_updated = Signal(dict)
    """
    This signal is emitted when the conda, pyenv or custom environments tracked
    by this plugin were updated.

    Parameters
    ----------
    envs: dict
        Environments dictionary in the format given by
        :py:meth:`spyder.utils.envs.get_list_envs`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._interpreter = self.get_main_interpreter()
        self._startup = True
        self._current_envs = None
        self._lock = QMutex()

        self.path_to_env = {}
        self.envs = {}
        self.internal_interpreter = sys.executable

        if os.name == 'nt' and is_conda_based_app():
            # Be sure to use 'python' executable instead of 'pythonw' since
            # no output is generated with 'pythonw'.
            self.internal_interpreter = self.internal_interpreter.replace(
                "pythonw.exe", "python.exe"
            ).lower()

        # Worker to compute envs info in a thread
        self._worker_manager = WorkerManager(self)

        # Timer to get envs every minute
        self._get_envs_timer = QTimer(self)
        self._get_envs_timer.setInterval(60000)
        self._get_envs_timer.timeout.connect(self._get_envs)
        self._get_envs_timer.start()

        # Timer to check the current interpreter
        self._check_interpreter_timer = QTimer(self)
        self._check_interpreter_timer.setInterval(2000)
        self._check_interpreter_timer.start(2000)

        # Update the list of envs at startup
        self._get_envs()

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        pass

    def update_actions(self):
        pass

    @on_conf_change(option=['default', 'custom_interpreter', 'custom'])
    def on_interpreter_changed(self, option, value):
        if (option == "default" and value) or (
            option == "custom" and not value
        ):
            executable = get_python_executable()
        else:
            executable = ""
            if self.get_conf("custom"):
                custom_interpreter = self.get_conf('custom_interpreter')
                if custom_interpreter:
                    executable = osp.normpath(custom_interpreter)
                    if osp.isfile(executable):
                        self.add_to_custom_interpreters(executable)

        # Setting executable option that will be used by other plugins in
        # Spyder.
        if osp.isfile(executable) and executable != self.get_conf(
            "executable"
        ):
            self.set_conf('executable', executable)

    @on_conf_change(option=['executable'])
    def on_executable_changed(self, value):
        # announce update
        interpreter = self.get_main_interpreter()
        self._update_interpreter(interpreter)
        self.sig_interpreter_changed.emit(interpreter)

    def on_close(self):
        self._get_envs_timer.stop()
        self._check_interpreter_timer.stop()
        self._worker_manager.terminate_all()
        self.set_conf("last_envs", self.envs)

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

    def validate_custom_interpreters_list(self):
        """Check that the used custom interpreters are still valid."""
        custom_list = self.get_conf('custom_interpreters_list')
        valid_custom_list = []
        for value in custom_list:
            if osp.isfile(value) and not is_conda_based_app(value):
                valid_custom_list.append(value)

        self.set_conf('custom_interpreters_list', valid_custom_list)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _get_envs(self):
        """
        Get the list of environments in a thread to keep them up to date.
        """
        # Save copy of current envs to compare it after they are updated
        self._current_envs = self.envs.copy()

        # Validate list of custom interpreters before updating them
        self.validate_custom_interpreters_list()

        # Update envs
        worker = self._worker_manager.create_python_worker(self._update_envs)
        worker.sig_finished.connect(self._finish_updating_envs)
        worker.start()

    def _update_envs(self):
        """Update environments."""
        # Compute info of default interpreter. We only need to do this once (at
        # startup).
        if self._startup:
            self._get_env_info(self.internal_interpreter)
            self._startup = False

        # Update custom envs
        last_envs: dict[str, tuple[str, str]] = self.get_conf("last_envs")
        if last_envs:
            for env in last_envs:
                if not(
                    last_envs[env][0] == self.internal_interpreter
                    or env.startswith("Conda")
                    or env.startswith("Pyenv")
                ):
                    path = last_envs[env][0]
                    if osp.isfile(path):
                        self._get_env_info(path)
                    else:
                        self.envs.pop(env)

        # Update conda/pyenv envs
        return get_list_envs()

    def _finish_updating_envs(self, worker, output, error):
        """Finish updating environments."""
        # This is necessary to avoid an error when the worker can't return a
        # proper output.
        # Fixes spyder-ide/spyder#20539
        if output is not None:
            # Update envs with autodetected info
            for new_name, new_info in output.items():
                if new_name in self.envs:
                    # The env is already listed, so we don't need to do
                    # anything else.
                    continue
                elif (
                    new_name not in self.envs
                    and new_info in self.envs.values()
                ):
                    # Replace name of envs that are detected as Conda/Pyenv
                    # envs after running _update_envs, but were listed in
                    # self.envs differently.
                    for name, info in self.envs.copy().items():
                        if info == new_info:
                            self.envs.pop(name)
                            self.envs[new_name] = info
                            break
                else:
                    # Add new env to the current ones
                    self.envs[new_name] = new_info

        if self._current_envs != self.envs:
            for env in list(self.envs.keys()):
                path, version = self.envs[env]
                # Save paths in lowercase on Windows to avoid issues with
                # capitalization.
                path = path.lower() if os.name == 'nt' else path
                self.path_to_env[path] = env

            self._update_interpreter()
            self.sig_environments_updated.emit(self.envs)

    def _update_interpreter(self, interpreter=None):
        """Set main interpreter and update information."""
        if interpreter:
            logger.debug(f"Main interpreter changed to {interpreter}")
            self._interpreter = interpreter

        if self._interpreter not in self.path_to_env:
            worker = self._worker_manager.create_python_worker(
                self._get_env_info,
                self._interpreter
            )
            worker.start()
            worker.sig_finished.connect(self._finish_updating_interpreter)

    def _finish_updating_interpreter(self, worker, output, error):
        if output is None or error:
            return

        # We need to inform about envs being updated in case a custom env was
        # added in Preferences, which will update its info.
        self.sig_environments_updated.emit(self.envs)

    def _get_env_info(self, path):
        """Get environment information."""
        with QMutexLocker(self._lock):
            original_path = path
            path = path.lower() if os.name == 'nt' else path

            try:
                name = self.path_to_env[path]
            except KeyError:
                env_name = get_env_dir(original_path, only_dir=True)

                if (
                    # For Anaconda/Miniconda distros
                    "conda" in path.lower()
                    # For Mambaforge
                    or "mamba" in path.lower()
                    # For Miniforge
                    or "miniforge" in path.lower()
                    # For our installers
                    or (is_conda_based_app() and "spyder-runtime" in path)
                ):
                    name = 'Conda: ' + env_name
                elif 'pyenv' in path:
                    name = 'Pyenv: ' + env_name
                else:
                    name = _("Custom") + ": " + env_name

                version = get_interpreter_info(path)
                self.path_to_env[path] = name
                self.envs[name] = (original_path, version)

            __, version = self.envs[name]
            return f'{name} ({version})'

    def _check_interpreter(self):
        """
        Switch to default interpreter if current env was removed or update
        Python version of current one.
        """
        env_dir = get_env_dir(self._interpreter)

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

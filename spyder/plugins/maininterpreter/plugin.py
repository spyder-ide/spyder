# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main interpreter Plugin.
"""

# Standard library imports
import logging
import os.path as osp

# Third-party import
from qtpy.QtCore import Signal


# Local imports
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.maininterpreter.confpage import MainInterpreterConfigPage
from spyder.plugins.maininterpreter.container import MainInterpreterContainer
from spyder.utils.misc import get_python_executable
from spyder.utils.conda import find_local_venv_interpreter


logger = logging.getLogger(__name__)

# Project option (in the workspace section) that stores the interpreter path
PROJECT_INTERPRETER_OPTION = "interpreter"


class MainInterpreter(SpyderPluginV2):
    """
    Main interpreter Plugin.
    """

    NAME = "main_interpreter"
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [Plugins.Projects]
    CONTAINER_CLASS = MainInterpreterContainer
    CONF_WIDGET_CLASS = MainInterpreterConfigPage
    CONF_SECTION = NAME
    CONF_FILE = False
    CAN_BE_DISABLED = False
    _global_interpreter = None

    # ---- Signals
    # -------------------------------------------------------------------------
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

    sig_interpreter_changed = Signal(str)
    """
    Signal to report that the main interpreter has changed.

    Parameters
    ----------
    path: str
        Path to the new interpreter.
    """

    # ---- SpyderPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Python interpreter")

    @staticmethod
    def get_description():
        return _(
            "Manage the default Python interpreter used to run, analyze and "
            "profile your code in Spyder."
        )

    @classmethod
    def get_icon(cls):
        return cls.create_icon('python')

    def on_initialize(self):
        container = self.get_container()

        # Connect container signals
        container.sig_environments_updated.connect(
            self.sig_environments_updated
        )
        container.sig_interpreter_changed.connect(self.sig_interpreter_changed)

        # Validate that the custom interpreter from the previous session
        # still exists
        if self.get_conf('custom'):
            interpreter = self.get_conf('custom_interpreter')
            if not osp.isfile(interpreter):
                self.set_conf('custom', False)
                self.set_conf('default', True)
                self.set_conf('executable', get_python_executable())

    def on_close(self, cancelable=False):
        self._restore_global_interpreter()

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._on_project_loaded)
        projects.sig_project_closed.connect(self._on_project_closed)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._on_project_loaded)
        projects.sig_project_closed.disconnect(self._on_project_closed)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        # Deregister conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_custom_interpreter(self, interpreter):
        """Set given interpreter as the current selected one."""
        self.get_container().add_to_custom_interpreters(interpreter)
        self.set_conf("default", False)
        self.set_conf("custom", True)
        self.set_conf("custom_interpreter", interpreter)
        self.set_conf("executable", interpreter)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _on_project_loaded(self, project_path):
        """Use the interpreter of the project that was just loaded."""
        # Always start from the global interpreter, so projects without an
        # interpreter fall back to the one set in Preferences.
        self._restore_global_interpreter()

        projects = self.get_plugin(Plugins.Projects)
        project = projects.get_active_project()
        if project is None:
            return

        interpreter = project.get_option(PROJECT_INTERPRETER_OPTION)
        if not interpreter:
            interpreter = self._detect_project_interpreter(project)

        if interpreter:
            self._apply_project_interpreter(interpreter)

    def _on_project_closed(self, project_path):
        """Go back to the global interpreter when a project is closed."""
        self._restore_global_interpreter()

    def _detect_project_interpreter(self, project):
        """
        Look for an interpreter inside the project and save it in the project
        preferences if it's usable.

        This is only called when the project doesn't have an interpreter set.
        """
        interpreter = find_local_venv_interpreter(project.root_path)
        if interpreter is None:
            return None

        project.set_option(PROJECT_INTERPRETER_OPTION, interpreter)
        return interpreter

    def _apply_project_interpreter(self, interpreter):
        """Make the given project interpreter the current one."""
        if not osp.isfile(interpreter):
            logger.warning(
                "The project interpreter %s doesn't exist, so the global "
                "one will be used",
                interpreter,
            )
            return

        # Save the global settings, but only once if projects are switched
        if self._global_interpreter is None:
            self._global_interpreter = {
                option: self.get_conf(option)
                for option in ("default", "custom", "custom_interpreter")
            }

        self.set_conf("default", False)
        self.set_conf("custom", True)
        self.set_conf("custom_interpreter", interpreter)
        self.set_conf("executable", interpreter)

    def _restore_global_interpreter(self):
        """Restore the interpreter set in Preferences, if it was replaced."""
        if self._global_interpreter is None:
            return

        saved = self._global_interpreter
        self._global_interpreter = None
        for option in ("custom_interpreter", "custom", "default"):
            self.set_conf(option, saved[option])

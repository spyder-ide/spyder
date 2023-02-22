# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Working Directory Plugin.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import SpyderPluginV2, Plugins
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.config.base import get_conf_path
from spyder.plugins.workingdirectory.confpage import WorkingDirectoryConfigPage
from spyder.plugins.workingdirectory.container import (
    WorkingDirectoryContainer)
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils import encoding


class WorkingDirectory(SpyderPluginV2):
    """
    Working directory changer plugin.
    """

    NAME = 'workingdir'
    REQUIRES = [Plugins.Preferences, Plugins.Console, Plugins.Toolbar]
    OPTIONAL = [Plugins.Editor, Plugins.Explorer, Plugins.IPythonConsole,
                Plugins.Find, Plugins.Projects]
    CONTAINER_CLASS = WorkingDirectoryContainer
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = WorkingDirectoryConfigPage
    CAN_BE_DISABLED = False
    CONF_FILE = False
    LOG_PATH = get_conf_path(CONF_SECTION)

    # --- Signals
    # ------------------------------------------------------------------------
    sig_current_directory_changed = Signal(str)
    """
    This signal is emitted when the current directory has changed.

    Parameters
    ----------
    new_working_directory: str
        The new new working directory path.
    """

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Working directory')

    def get_description(self):
        return _('Set the current working directory for various plugins.')

    def get_icon(self):
        return self.create_icon('DirOpenIcon')

    def on_initialize(self):
        container = self.get_container()

        container.sig_current_directory_changed.connect(
            self.sig_current_directory_changed)
        self.sig_current_directory_changed.connect(
            lambda path, plugin=None: self.chdir(path, plugin))

        cli_options = self.get_command_line_options()
        container.set_history(
            self.load_history(),
            cli_options.working_directory
        )

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        container = self.get_container()
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.add_application_toolbar(container.toolbar)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        editor.sig_dir_opened.connect(self._editor_change_dir)

    @on_plugin_available(plugin=Plugins.Explorer)
    def on_explorer_available(self):
        explorer = self.get_plugin(Plugins.Explorer)
        self.sig_current_directory_changed.connect(self._explorer_change_dir)
        explorer.sig_dir_opened.connect(self._explorer_dir_opened)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_available(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        self.sig_current_directory_changed.connect(
            ipyconsole.set_current_client_working_directory)
        ipyconsole.sig_current_directory_changed.connect(
            self._ipyconsole_change_dir)

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._project_loaded)
        projects.sig_project_closed[object].connect(self._project_closed)

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        toolbar.remove_application_toolbar(
            ApplicationToolbars.WorkingDirectory)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        editor.sig_dir_opened.disconnect(self._editor_change_dir)

    @on_plugin_teardown(plugin=Plugins.Explorer)
    def on_explorer_teardown(self):
        explorer = self.get_plugin(Plugins.Explorer)
        self.sig_current_directory_changed.disconnect(self._explorer_change_dir)
        explorer.sig_dir_opened.disconnect(self._explorer_dir_opened)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_teardown(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        self.sig_current_directory_changed.disconnect(
            ipyconsole.set_current_client_working_directory)
        ipyconsole.sig_current_directory_changed.disconnect(
            self._ipyconsole_change_dir)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._project_loaded)
        projects.sig_project_closed[object].disconnect(self._project_closed)

    # --- Public API
    # ------------------------------------------------------------------------
    def chdir(self, directory, sender_plugin=None):
        """
        Change current working directory.

        Parameters
        ----------
        directory: str
            The new working directory to set.
        sender_plugin: spyder.api.plugins.SpyderPluginsV2
            The plugin that requested this change: Default is None.
        """
        explorer = self.get_plugin(Plugins.Explorer)
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        find = self.get_plugin(Plugins.Find)

        if explorer and sender_plugin != explorer:
            explorer.chdir(directory, emit=False)
            explorer.refresh(directory, force_current=True)

        if ipyconsole and sender_plugin != ipyconsole:
            ipyconsole.set_current_client_working_directory(directory)

        if find:
            find.refresh_search_directory()

        if sender_plugin is not None:
            container = self.get_container()
            container.chdir(directory, emit=False)
            if ipyconsole:
                ipyconsole.save_working_directory(directory)

        self.save_history()

    def load_history(self, workdir=None):
        """
        Load history from a text file located in Spyder configuration folder
        or use `workdir` if there are no directories saved yet.

        Parameters
        ----------
        workdir: str
            The working directory to return. Default is None.
        """
        if osp.isfile(self.LOG_PATH):
            history, _ = encoding.readlines(self.LOG_PATH)
            history = [name for name in history if osp.isdir(name)]
        else:
            if workdir is None:
                workdir = self.get_container()._get_init_workdir()

            history = [workdir]

        return history

    def save_history(self):
        """
        Save history to a text file located in Spyder configuration folder.
        """
        history = self.get_container().get_history()
        try:
            encoding.writelines(history, self.LOG_PATH)
        except EnvironmentError:
            pass

    def get_workdir(self):
        """
        Get current working directory.

        Returns
        -------
        str
            Current working directory.
        """
        return self.get_container().get_workdir()

    # -------------------------- Private API ----------------------------------
    def _editor_change_dir(self, path):
        editor = self.get_plugin(Plugins.Editor)
        self.chdir(path, editor)

    def _explorer_change_dir(self, path):
        explorer = self.get_plugin(Plugins.Explorer)
        explorer.chdir(path, emit=False)

    def _explorer_dir_opened(self, path):
        explorer = self.get_plugin(Plugins.Explorer)
        self.chdir(path, explorer)

    def _ipyconsole_change_dir(self, path):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        self.chdir(path, ipyconsole)

    def _project_loaded(self, path):
        projects = self.get_plugin(Plugins.Projects)
        self.chdir(directory=path, sender_plugin=projects)

    def _project_closed(self, path):
        projects = self.get_plugin(Plugins.Projects)
        self.chdir(
            directory=projects.get_last_working_dir(),
            sender_plugin=projects
        )

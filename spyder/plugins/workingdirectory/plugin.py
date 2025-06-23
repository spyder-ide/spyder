# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Working Directory Plugin.
"""

# Standard library imports
import logging
import os.path as osp
from typing import Optional

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

logger = logging.getLogger(__name__)


class WorkingDirectory(SpyderPluginV2):
    """
    Working directory changer plugin.
    """

    NAME = 'workingdir'
    REQUIRES = [Plugins.Preferences, Plugins.Console, Plugins.Toolbar]
    OPTIONAL = [
        Plugins.Editor,
        Plugins.Explorer,
        Plugins.IPythonConsole,
        Plugins.Projects,
    ]
    CONTAINER_CLASS = WorkingDirectoryContainer
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = WorkingDirectoryConfigPage
    CAN_BE_DISABLED = False
    CONF_FILE = False
    LOG_PATH = get_conf_path(CONF_SECTION)

    # --- Signals
    # ------------------------------------------------------------------------
    sig_current_directory_changed = Signal(str, str, str)
    """
    This signal is emitted when the current directory has changed.

    Parameters
    ----------
    new_working_directory: str
        The new working directory path.
    sender_plugin: str
        Name of the plugin that requested the directory to be changed.
    server_id: str
        The server identification from where the new working directory is
        reachable.
    """

    # --- SpyderPluginV2 API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Working directory')

    @staticmethod
    def get_description():
        return _("Manage the current working directory used in Spyder.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon('DirOpenIcon')

    def on_initialize(self):
        container = self.get_container()

        # To report to other plugins that cwd changed when the user selected a
        # new one directly in the toolbar.
        container.sig_current_directory_changed.connect(self.chdir)

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
        container = self.get_container()
        container.edit_goto.connect(editor.load)

    @on_plugin_available(plugin=Plugins.Explorer)
    def on_explorer_available(self):
        explorer = self.get_plugin(Plugins.Explorer)
        explorer.sig_dir_opened.connect(self._explorer_dir_opened)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_available(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        ipyconsole.sig_current_directory_changed.connect(
            self._ipyconsole_change_dir
        )

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._project_loaded)
        projects.sig_project_closed[str].connect(self._project_closed)

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
        explorer.sig_dir_opened.disconnect(self._explorer_dir_opened)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipyconsole_teardown(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        ipyconsole.sig_current_directory_changed.disconnect(
            self._ipyconsole_change_dir
        )

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._project_loaded)
        projects.sig_project_closed[str].disconnect(self._project_closed)

    # --- Public API
    # ------------------------------------------------------------------------
    def chdir(
        self,
        directory: str,
        sender_plugin: Optional[str] = None,
        server_id: Optional[str] = None
    ):
        """
        Change current working directory.

        Parameters
        ----------
        directory: str
            The new working directory to set.
        sender_plugin: str, optional
            The plugin that requested this change. Default is None, which means
            this is the plugin requesting the change.
        server_id: str, optional
            The server identification from where the directory is reachable.
            Default is None.
        """
        container = self.get_container()

        if container.server_id != server_id:
            # Remove previous paths history in case we are changing not only cwd
            # but also `server_id` while saving the history for local paths
            container.pathedit.clear()
            if not server_id:
                history = self.load_history()
                self.set_conf("history", history)
                container.pathedit.addItems(history)

        if sender_plugin is None:
            sender_plugin = self.NAME

        logger.debug(
            f"The plugin {sender_plugin} requested changing the cwd to "
            f"{directory}"
        )
        # Prevent setting the cwd twice if it was changed by the user in the
        # toolbar.
        if sender_plugin != self.NAME:
            container.chdir(directory, emit=False, server_id=server_id)
        self.sig_current_directory_changed.emit(
            directory, sender_plugin, server_id
        )

        if server_id is None:
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
        self.chdir(path, Plugins.Editor)

    def _explorer_dir_opened(self, path, server_id=None):
        self.chdir(path, Plugins.Explorer, server_id)

    def _ipyconsole_change_dir(self, path, server_id=None):
        self.chdir(path, Plugins.IPythonConsole, server_id)

    def _project_loaded(self, path):
        self.chdir(directory=path, sender_plugin=Plugins.Projects)

    def _project_closed(self, path):
        projects = self.get_plugin(Plugins.Projects)
        self.chdir(
            directory=projects.get_last_working_dir(),
            sender_plugin=Plugins.Projects
        )

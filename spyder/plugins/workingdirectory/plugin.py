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
from spyder.api.translations import get_translation
from spyder.config.base import get_conf_path
from spyder.plugins.workingdirectory.confpage import WorkingDirectoryConfigPage
from spyder.plugins.workingdirectory.container import (
    WorkingDirectoryContainer)
from spyder.utils import encoding

# Localization
_ = get_translation('spyder')


class WorkingDirectory(SpyderPluginV2):
    """
    Working directory changer plugin.
    """

    NAME = 'workingdir'
    REQUIRES = [Plugins.Preferences, Plugins.Console, Plugins.Toolbar]
    OPTIONAL = [Plugins.Editor, Plugins.Explorer, Plugins.IPythonConsole,
                Plugins.Find]
    CONTAINER_CLASS = WorkingDirectoryContainer
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = WorkingDirectoryConfigPage
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
    def get_name(self):
        return _('Current working directory')

    def get_description(self):
        return _('Set the current working directory for various plugins.')

    def get_icon(self):
        return self.create_icon('DirOpenIcon')

    def register(self):
        container = self.get_container()
        toolbar = self.get_plugin(Plugins.Toolbar)
        editor = self.get_plugin(Plugins.Editor)
        explorer = self.get_plugin(Plugins.Explorer)
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

        toolbar.add_application_toolbar(container.toolbar)
        container.sig_current_directory_changed.connect(
            self.sig_current_directory_changed)
        self.sig_current_directory_changed.connect(
            lambda path, plugin=None: self.chdir(path, plugin))
        container.set_history(self.load_history())

        if editor:
            editor.sig_dir_opened.connect(
                lambda path, plugin=editor: self.chdir(path, editor))

        if ipyconsole:
            self.sig_current_directory_changed.connect(
                ipyconsole.set_current_client_working_directory)
            # TODO: chdir_current_client might follow a better naming
            # convention
            ipyconsole.sig_current_directory_changed.connect(
                lambda path, plugin=ipyconsole: self.chdir(path, plugin))

        if explorer:
            self.sig_current_directory_changed.connect(
                lambda path: explorer.chdir(path, emit=False))
            explorer.sig_dir_opened.connect(
                lambda path, plugin=explorer: self.chdir(path, plugin))

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
                workdir = self.get_workdir()

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

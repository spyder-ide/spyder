# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Files and Directories Explorer Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import logging
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal
from superqt.utils import qdebounced

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.translations import _
from spyder.api.plugins import SpyderDockablePlugin, Plugins
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.plugins.explorer.widgets.main_widget import ExplorerWidget
from spyder.plugins.explorer.confpage import ExplorerConfigPage

logger = logging.getLogger(__name__)


class Explorer(SpyderDockablePlugin):
    """File and Directories Explorer DockWidget."""

    NAME = 'explorer'
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [
        Plugins.IPythonConsole,
        Plugins.Editor,
        Plugins.WorkingDirectory,
        Plugins.RemoteClient,
        Plugins.Application,
    ]
    TABIFY = Plugins.VariableExplorer
    WIDGET_CLASS = ExplorerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ExplorerConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_dir_opened = Signal(str, str)
    """
    This signal is emitted to indicate a folder has been opened.

    Parameters
    ----------
    directory: str
        The opened path directory.
    server_id: str
        The server identification from where the directory path is reachable.

    Notes
    -----
    This will update the current working directory.
    """

    sig_file_created = Signal(str)
    """
    This signal is emitted to request creating a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_file_removed = Signal(str)
    """
    This signal is emitted when a file is removed.

    Parameters
    ----------
    path: str
        File path removed.
    """

    sig_file_renamed = Signal(str, str)
    """
    This signal is emitted when a file is renamed.

    Parameters
    ----------
    old_path: str
        Old path for renamed file.
    new_path: str
        New path for renamed file.
    """

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted to request opening a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_folder_removed = Signal(str)
    """
    This signal is emitted when a folder is removed.

    Parameters
    ----------
    path: str
        Folder to remove.
    """

    sig_folder_renamed = Signal(str, str)
    """
    This signal is emitted when a folder is renamed.

    Parameters
    ----------
    old_path: str
        Old path for renamed folder.
    new_path: str
        New path for renamed folder.
    """

    sig_open_interpreter_requested = Signal(str)
    """
    This signal is emitted to request opening an interpreter with the given
    path as working directory.

    Parameters
    ----------
    path: str
        Path to use as working directory of interpreter.
    """

    sig_module_created = Signal(str)
    """
    This signal is emitted to indicate a module has been created.

    Parameters
    ----------
    directory: str
        The created path directory.
    """

    sig_run_requested = Signal(str)
    """
    This signal is emitted to request running a file.

    Parameters
    ----------
    path: str
        File path to run.
    """

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        """Return widget title"""
        return _("Files")

    @staticmethod
    def get_description():
        """Return the description of the explorer widget."""
        return _("Explore your filesystem in a tree view.")

    @classmethod
    def get_icon(cls):
        """Return the explorer icon."""
        return cls.create_icon('files')

    def on_initialize(self):
        self._file_managers = {}
        widget = self.get_widget()

        # Expose widget signals on the plugin
        widget.sig_dir_opened.connect(self.sig_dir_opened)
        widget.sig_file_created.connect(self.sig_file_created)
        widget.sig_open_file_requested.connect(self.sig_open_file_requested)
        widget.sig_open_interpreter_requested.connect(
            self.sig_open_interpreter_requested)
        widget.sig_module_created.connect(self.sig_module_created)
        widget.sig_removed.connect(self.sig_file_removed)
        widget.sig_renamed.connect(self.sig_file_renamed)
        widget.sig_run_requested.connect(self.sig_run_requested)
        widget.sig_tree_removed.connect(self.sig_folder_removed)
        widget.sig_tree_renamed.connect(self.sig_folder_renamed)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)

        editor.sig_dir_opened.connect(self.chdir)
        self.sig_file_created.connect(lambda t: editor.new(text=t))
        self.sig_file_removed.connect(editor.removed)
        self.sig_file_renamed.connect(editor.renamed)
        self.sig_folder_removed.connect(editor.removed_tree)
        self.sig_folder_renamed.connect(editor.renamed_tree)
        self.sig_module_created.connect(editor.new)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Add preference config page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        self.sig_open_interpreter_requested.connect(
            ipyconsole.create_client_from_path)
        self.sig_run_requested.connect(
            lambda fname:
            ipyconsole.run_script(
                filename=fname,
                wdir=osp.dirname(fname),
                current_client=False,
                clear_variables=True,
            )
        )

    @on_plugin_available(plugin=Plugins.WorkingDirectory)
    def on_working_directory_available(self):
        working_directory = self.get_plugin(Plugins.WorkingDirectory)
        working_directory.sig_current_directory_changed.connect(
            self._chdir_from_working_directory
        )

    @on_plugin_available(plugin=Plugins.Application)
    def on_application_available(self):
        application = self.get_plugin(Plugins.Application)
        self.sig_open_file_requested.connect(application.open_file_in_plugin)

    @on_plugin_available(plugin=Plugins.RemoteClient)
    def on_remote_client_available(self):
        remoteclient = self.get_plugin(Plugins.RemoteClient)
        remoteclient.sig_server_stopped.connect(self._on_server_stopped)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)

        editor.sig_dir_opened.disconnect(self.chdir)
        self.sig_file_created.disconnect()
        self.sig_file_removed.disconnect(editor.removed)
        self.sig_file_renamed.disconnect(editor.renamed)
        self.sig_folder_removed.disconnect(editor.removed_tree)
        self.sig_folder_renamed.disconnect(editor.renamed_tree)
        self.sig_module_created.disconnect(editor.new)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self):
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        self.sig_open_interpreter_requested.disconnect(
            ipyconsole.create_client_from_path)
        self.sig_run_requested.disconnect()

    @on_plugin_teardown(plugin=Plugins.WorkingDirectory)
    def on_working_directory_teardown(self):
        working_directory = self.get_plugin(Plugins.WorkingDirectory)
        working_directory.sig_current_directory_changed.disconnect(
            self._chdir_from_working_directory
        )

    @on_plugin_teardown(plugin=Plugins.Application)
    def on_application_teardown(self):
        application = self.get_plugin(Plugins.Application)
        self.sig_open_file_requested.disconnect(
            application.open_file_in_plugin
        )

    @on_plugin_teardown(plugin=Plugins.RemoteClient)
    def on_remote_client_teardown(self):
        remoteclient = self.get_plugin(Plugins.RemoteClient)
        remoteclient.sig_server_stopped.disconnect(self._on_server_stopped)

    def on_close(self, cancelable=False):
        if len(self._file_managers):
            for file_manager in self._file_managers.values():
                AsyncDispatcher(
                    loop=file_manager.session._loop, early_return=False
                )(file_manager.close)()
            self._file_managers = {}

    # ---- Public API
    # ------------------------------------------------------------------------
    def chdir(self, directory, emit=True, server_id=None):
        """
        Set working directory.

        Parameters
        ----------
        directory: str
            The new working directory path.
        emit: bool, optional
            Emit a signal to indicate the working directory has changed.
            Default is True.
        server_id: str
            The server identification from where the new working directory is
            reachable.
        """
        self.get_widget().chdir(directory, emit=emit, server_id=server_id)

    def get_current_folder(self):
        """Get folder displayed at the moment."""
        return self.get_widget().get_current_folder()

    def refresh(self, new_path=None, force_current=True):
        """
        Refresh history.

        Parameters
        ----------
        new_path: str, optional
            Path to add to history. Default is None.
        force_current: bool, optional
            Default is True.
        """
        widget = self.get_widget()
        widget.update_history(new_path)
        widget.refresh(new_path, force_current=force_current)

    # ---- Private API
    # -------------------------------------------------------------------------
    @qdebounced(timeout=100)
    def _chdir_from_working_directory(
        self, directory, sender_plugin, server_id=None
    ):
        """
        Change the working directory when requested from the Working Directory
        plugin.

        Notes
        -----
        * This method is debounced to avoid calling it several times when
          multiple plugins try to change the cwd in quick succession.
        """
        # Only update the cwd if this plugin didn't request changing it
        if sender_plugin != self.NAME:
            self.chdir(directory, emit=False, server_id=server_id)
            self.refresh(directory)

    @AsyncDispatcher(loop="explorer")
    async def _get_remote_files_manager(self, server_id):
        remoteclient = self.get_plugin(Plugins.RemoteClient, error=False)
        if not remoteclient:
            return
        if server_id not in self._file_managers:
            self._file_managers[server_id] = remoteclient.get_file_api(
                server_id
            )()
            await self._file_managers[server_id].connect()
        return self._file_managers.get(server_id, None)

    def _on_server_stopped(self, server_id):
        file_manager = self._file_managers.get(server_id)
        if file_manager:
            AsyncDispatcher(
                loop=file_manager.session._loop, early_return=False
            )(file_manager.close)()
            self._file_managers.pop(server_id)

        self.get_widget().reset_remote_treewidget(server_id)

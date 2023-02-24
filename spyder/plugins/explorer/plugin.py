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
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.translations import _
from spyder.api.plugins import SpyderDockablePlugin, Plugins
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.plugins.explorer.widgets.main_widget import ExplorerWidget
from spyder.plugins.explorer.confpage import ExplorerConfigPage


class Explorer(SpyderDockablePlugin):
    """File and Directories Explorer DockWidget."""

    NAME = 'explorer'
    REQUIRES = [Plugins.Preferences]
    OPTIONAL = [Plugins.IPythonConsole, Plugins.Editor]
    TABIFY = Plugins.VariableExplorer
    WIDGET_CLASS = ExplorerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ExplorerConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_dir_opened = Signal(str)
    """
    This signal is emitted to indicate a folder has been opened.

    Parameters
    ----------
    directory: str
        The opened path directory.

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

    def get_description(self):
        """Return the description of the explorer widget."""
        return _("Explore files in the computer with a tree view.")

    def get_icon(self):
        """Return the explorer icon."""
        # TODO: Find a decent icon for the explorer
        return self.create_icon('outline_explorer')

    def on_initialize(self):
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
        self.sig_open_file_requested.connect(editor.load)

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
        self.sig_open_file_requested.disconnect(editor.load)

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

    # ---- Public API
    # ------------------------------------------------------------------------
    def chdir(self, directory, emit=True):
        """
        Set working directory.

        Parameters
        ----------
        directory: str
            The new working directory path.
        emit: bool, optional
            Emit a signal to indicate the working directory has changed.
            Default is True.
        """
        self.get_widget().chdir(directory, emit=emit)

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

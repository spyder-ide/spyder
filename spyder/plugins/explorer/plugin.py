# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Files and Directories Explorer Plugin.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.translations import get_translation
from spyder.api.plugins import SpyderDockablePlugin, Plugins
from spyder.plugins.explorer.widgets.explorer import ExplorerWidget
from spyder.plugins.explorer.confpage import ExplorerConfigPage

# Localization
_ = get_translation('spyder')


class Explorer(SpyderDockablePlugin):
    """
    File and Directories Explorer DockWidget.
    """

    NAME = 'explorer'
    OPTIONAL = [Plugins.IPythonConsole, Plugins.Editor]
    TABIFY = Plugins.VariableExplorer
    WIDGET_CLASS = ExplorerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ExplorerConfigPage
    CONF_FILE = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_folder_opened = Signal(str)
    """
    This signal is emitted to indicate a folder has been opened.

    Parameters
    ----------
    directory: str
        The path to the directory opened.

    Notes
    -----
    This will update the current working directory.
    """

    sig_file_externally_opened = Signal(str)
    """
    This signal is emitted when a file is open outside Spyder for edition.

    Parameters
    ----------
    path: str
        File path opened externally for edition.
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

    sig_folder_removed = Signal(str)
    """
    This signal is emitted when a folder is removed.

    Parameters
    ----------
    path: str
        Folder to remove.
    """

    sig_folder_renamed = Signal(str)
    """
    This signal is emitted when a folder is renamed.

    Parameters
    ----------
    path: str
        Folder to remove.
    """

    sig_run_requested = Signal(str)
    """
    This signal is emitted to request running a file.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_new_file_requested = Signal()
    """
    This signal is emitted to request creating a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted to request opening a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
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

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Files")

    def get_description(self):
        return _("Explore files in the computer with a tree view.")

    def get_icon(self):
        return self.create_icon('outline_explorer')

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Expose widget signals on the plugin
        widget.sig_dir_opened.connect(self.sig_folder_opened)
        widget.sig_edited.connect(self.sig_file_externally_opened)
        widget.sig_removed.connect(self.sig_file_removed)
        widget.sig_renamed.connect(self.sig_file_renamed)
        widget.sig_tree_removed.connect(self.sig_folder_removed)
        widget.sig_tree_renamed.connect(self.sig_folder_renamed)
        widget.sig_new_file_requested.connect(self.sig_new_file_requested)
        widget.sig_run_requested.connect(self.sig_run_requested)
        widget.sig_open_file_requested.connect(self.sig_open_file_requested)
        widget.sig_open_interpreter_requested.connect(
            self.sig_open_interpreter_requested)

        # Connect plugin signals with plugins slots
        if editor:
            editor.sig_dir_opened.connect(self.chdir)
            self.sig_open_file_requested.connect(editor.load)
            self.sig_file_externally_opened.connect(editor.load)
            self.sig_new_file_requested.connect(
                lambda t: editor.new(text=t))
            self.sig_file_removed.connect(editor.removed)
            self.sig_file_renamed.connect(editor.renamed)
            self.sig_folder_removed.connect(editor.removed_tree)
            self.sig_folder_renamed.connect(editor.renamed_tree)

        if ipyconsole:
            self.sig_open_interpreter_requested.connect(
                ipyconsole.create_client_from_path)
            # TODO: use name arguments to clarify what is going on with the
            # booleans
            self.sig_run_requested.connect(
                lambda f: ipyconsole.run_script(  # f -> filename
                    f, osp.dirname(f), '', False, False, False, True, False))

    # --- API
    # ------------------------------------------------------------------------
    def chdir(self, directory, emit=True):
        """
        Set working directory.

        Parameters
        ----------
        directory: str
            Directory to set as working directory.
        """
        self.get_widget().chdir(directory, emit=emit)

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

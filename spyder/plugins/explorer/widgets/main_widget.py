# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Explorer Main Widget.
"""

# Standard library imports
import logging
import os.path as osp

# Third-party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.explorer.widgets.remote_explorer import RemoteExplorer
from spyder.plugins.explorer.widgets.explorer import (
    DirViewActions, ExplorerTreeWidget
)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home

logger = logging.getLogger(__name__)


# ---- Constants
class ExplorerWidgetOptionsMenuSections:
    Files = 'files_section'
    Header = 'header_section'
    Common = 'common_section'


class ExplorerWidgetMainToolbarSections:
    Main = 'main_section'

class ExplorerWidgetActions:
    # Toggles
    ToggleFilter = 'toggle_filter_files_action'

    # Triggers
    Next = 'next_action'
    Parent = 'parent_action'
    Previous = 'previous_action'


# ---- Main widget
class ExplorerWidget(PluginMainWidget):
    """Explorer widget"""

    # --- Signals
    # ------------------------------------------------------------------------
    sig_dir_opened = Signal(str, str)
    """
    This signal is emitted to indicate a folder has been opened.

    Parameters
    ----------
    directory: str
        The path to the directory opened.
    """

    sig_module_created = Signal(str)
    """
    This signal is emitted when a new python module is created.

    Parameters
    ----------
    module: str
        Path to the new module created.
    """

    sig_file_created = Signal(str)
    """
    This signal is emitted to request creating a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to create.
    """

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted to request opening a new file with Spyder.

    Parameters
    ----------
    path: str
        File path to run.
    """

    sig_removed = Signal(str)
    """
    This signal is emitted when a file is removed.

    Parameters
    ----------
    path: str
        File path removed.
    """

    sig_renamed = Signal(str, str)
    """
    This signal is emitted when a file is renamed.

    Parameters
    ----------
    old_path: str
        Old path for renamed file.
    new_path: str
        New path for renamed file.
    """

    sig_tree_removed = Signal(str)
    """
    This signal is emitted when a folder is removed.

    Parameters
    ----------
    path: str
        Folder to remove.
    """

    sig_tree_renamed = Signal(str, str)
    """
    This signal is emitted when a folder is renamed.

    Parameters
    ----------
    old_path: str
        Old path for renamed folder.
    new_path: str
        New path for renamed folder.
    """

    sig_run_requested = Signal(str)
    """
    This signal is emitted to request running a file.

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

    ENABLE_SPINNER = True

    def __init__(self, name, plugin, parent=None):
        """
        Initialize the widget.

        Parameters
        ----------
        name: str
            Name of the container.
        plugin: SpyderDockablePlugin
            Plugin of the container
        parent: QWidget
            Parent of this widget
        """
        super().__init__(name, plugin=plugin, parent=parent)

        # Widgets
        self.stackwidget = QStackedWidget(parent=self)
        self.treewidget = ExplorerTreeWidget(parent=self)
        self.remote_treewidget = RemoteExplorer(parent=self)
        self.stackwidget.addWidget(self.remote_treewidget)
        self.stackwidget.addWidget(self.treewidget)

        # Layouts
        layout = QHBoxLayout()
        layout.addWidget(self.stackwidget)
        self.setLayout(layout)

        # Signals
        self.treewidget.sig_dir_opened.connect(self.sig_dir_opened)
        self.remote_treewidget.sig_dir_opened.connect(self._do_remote_sig_dir_opened)
        self.treewidget.sig_file_created.connect(self.sig_file_created)
        self.treewidget.sig_open_file_requested.connect(
            self.sig_open_file_requested)
        self.treewidget.sig_module_created.connect(self.sig_module_created)
        self.treewidget.sig_open_interpreter_requested.connect(
            self.sig_open_interpreter_requested)
        self.treewidget.sig_renamed.connect(self.sig_renamed)
        self.treewidget.sig_removed.connect(self.sig_removed)
        self.treewidget.sig_run_requested.connect(self.sig_run_requested)
        self.treewidget.sig_tree_removed.connect(self.sig_tree_removed)
        self.treewidget.sig_tree_renamed.connect(self.sig_tree_renamed)
        self.treewidget.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_focus_widget(self):
        """Define the widget to focus."""
        return self.treewidget

    def get_title(self):
        """Return the title of the plugin tab."""
        return _("Files")

    def _setup(self):
        super()._setup()

    def setup(self):
        """Performs the setup of plugin's menu and actions."""
        # Actions
        self.previous_action = self.create_action(
            ExplorerWidgetActions.Previous,
            text=_("Previous"),
            icon=self.create_icon('previous'),
            triggered=self.go_to_previous_directory,
        )
        self.next_action = self.create_action(
            ExplorerWidgetActions.Next,
            text=_("Next"),
            icon=self.create_icon('next'),
            triggered=self.go_to_next_directory,
        )
        self.parent_action = self.create_action(
            ExplorerWidgetActions.Parent,
            text=_("Parent"),
            icon=self.create_icon('up'),
            triggered=self.go_to_parent_directory
        )

        # Toolbuttons
        self.filter_button = self.create_action(
            ExplorerWidgetActions.ToggleFilter,
            text="",
            icon=ima.icon('filter'),
            toggled=self.change_filter_state
        )
        self.filter_button.setCheckable(True)

        # Set actions for tree widgets
        # A `create_new_treewdiget` method should do this?
        self.treewidget.previous_action = self.previous_action
        self.treewidget.next_action = self.next_action
        self.treewidget.filter_button = self.filter_button

        self.remote_treewidget.previous_action = self.previous_action
        self.remote_treewidget.next_action = self.next_action
        self.remote_treewidget.filter_button = self.filter_button

        # Setup widgets
        self.treewidget.setup()
        self.chdir(getcwd_or_home())
        
        # Menu
        menu = self.get_options_menu()

        for item in [self.get_action(DirViewActions.ToggleHiddenFiles),
                     self.get_action(DirViewActions.EditNameFilters)]:
            self.add_item_to_menu(
                item, menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Common)

        for item in [self.get_action(DirViewActions.ToggleSizeColumn),
                     self.get_action(DirViewActions.ToggleTypeColumn),
                     self.get_action(DirViewActions.ToggleDateColumn)]:
            self.add_item_to_menu(
                item, menu=menu,
                section=ExplorerWidgetOptionsMenuSections.Header)

        single_click_action = self.get_action(DirViewActions.ToggleSingleClick)
        self.add_item_to_menu(
            single_click_action,
            menu=menu, section=ExplorerWidgetOptionsMenuSections.Files)

        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [self.previous_action,
                     self.next_action,
                     self.parent_action,
                     self.filter_button]:
            self.add_item_to_toolbar(
                item, toolbar=toolbar,
                section=ExplorerWidgetMainToolbarSections.Main)

    def update_actions(self):
        """Handle the update of actions of the plugin."""
        pass

    # ---- Private API
    # ------------------------------------------------------------------------
    @AsyncDispatcher.QtSlot
    def _on_remote_ls(self, future):
        data = future.result()
        logger.info(data)
        self.remote_treewidget.import_data(data)
        self.stop_spinner()

    def _do_remote_sig_dir_opened(self, path, server_id, emit=True):
        self.start_spinner()
        self._plugin._do_remote_ls(path, server_id).connect(self._on_remote_ls)
        if emit:
            self.sig_dir_opened.emit(path, server_id)

    # ---- Public API
    # ------------------------------------------------------------------------
    def chdir(self, directory, emit=True, server_id=None):
        """
        Set working directory.

        Parameters
        ----------
        directory: str
            Directory to set as working directory.
        emit: bool, optional
            Default is True.
        """
        if not server_id:
            self.treewidget.chdir(directory, emit=emit)
            self.stackwidget.setCurrentWidget(self.treewidget)
        else:
            logger.info(f"Request ls for {server_id} at {directory}")
            self._do_remote_sig_dir_opened(directory, server_id, emit=False)
            self.remote_treewidget.chdir(directory, server_id=server_id, emit=emit)
            self.stackwidget.setCurrentWidget(self.remote_treewidget)

    def get_current_folder(self):
        """Get current folder in the tree widget."""
        return self.stackwidget.currentWidget().get_current_folder()

    def set_current_folder(self, folder):
        """
        Set the current folder in the tree widget.

        Parameters
        ----------
        folder: str
            Folder path to set as current folder.
        """
        self.stackwidget.currentWidget().set_current_folder(folder)

    def go_to_parent_directory(self):
        """Move to parent directory."""
        self.stackwidget.currentWidget().go_to_parent_directory()

    def go_to_previous_directory(self):
        """Move to previous directory in history."""
        self.stackwidget.currentWidget().go_to_previous_directory()

    def go_to_next_directory(self):
        """Move to next directory in history."""
        self.stackwidget.currentWidget().go_to_next_directory()

    def refresh(self, new_path=None, force_current=False):
        """
        Refresh history.

        Parameters
        ----------
        new_path: str, optional
            Path to add to history. Default is None.
        force_current: bool, optional
            Default is True.
        """
        self.stackwidget.currentWidget().refresh(new_path, force_current)

    def change_filter_state(self):
        self.stackwidget.currentWidget().change_filter_state()

    def update_history(self, directory):
        """
        Update history with directory.

        Parameters
        ----------
        directory: str
            Path to add to history.
        """
        self.treewidget.update_history(directory)


# =============================================================================
# Tests
# =============================================================================
class FileExplorerTest(QWidget):
    def __init__(self, directory=None, file_associations={}):
        self.CONF_SECTION = 'explorer'
        super().__init__()

        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))

        self.explorer = ExplorerWidget('explorer', self, parent=self)
        self.explorer.set_conf('file_associations', file_associations)
        self.explorer._setup()
        self.explorer.setup()
        self.label_dir = QLabel("<b>Open dir:</b>")
        self.label_file = QLabel("<b>Open file:</b>")
        self.label1 = QLabel()
        self.label_dir.setAlignment(Qt.AlignRight)
        self.label2 = QLabel()
        self.label_option = QLabel("<b>Option changed:</b>")
        self.label3 = QLabel()

        # Setup
        self.explorer.set_current_folder(self.directory)
        self.label_file.setAlignment(Qt.AlignRight)
        self.label_option.setAlignment(Qt.AlignRight)

        # Layout
        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(self.label_file)
        hlayout1.addWidget(self.label1)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.label_dir)
        hlayout2.addWidget(self.label2)

        hlayout3 = QHBoxLayout()
        hlayout3.addWidget(self.label_option)
        hlayout3.addWidget(self.label3)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.explorer)
        vlayout.addLayout(hlayout1)
        vlayout.addLayout(hlayout2)
        vlayout.addLayout(hlayout3)
        self.setLayout(vlayout)

        # Signals
        self.explorer.sig_dir_opened.connect(self.label2.setText)
        self.explorer.sig_dir_opened.connect(
            lambda: self.explorer.treewidget.refresh('..'))
        self.explorer.sig_open_file_requested.connect(self.label1.setText)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    test = FileExplorerTest()
    test.resize(640, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()

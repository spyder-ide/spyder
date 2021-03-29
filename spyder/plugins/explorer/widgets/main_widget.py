# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Explorer Main Widget.
"""

# Standard library imports
import os.path as osp

# Third-party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.plugins.explorer.widgets.explorer import (
    DirViewActions, ExplorerTreeWidget, ExplorerTreeWidgetActions,
    FilteredDirView)
from spyder.utils.misc import getcwd_or_home


_ = get_translation('spyder')


# ---- Constants
class ExplorerWidgetOptionsMenuSections:
    Files = 'files_section'
    Header = 'header_section'
    Common = 'common_section'


class ExplorerWidgetMainToolbarSections:
    Main = 'main_section'


# ---- Main widget
class ExplorerWidget(PluginMainWidget):
    """Explorer widget"""

    # --- Signals
    # ------------------------------------------------------------------------
    sig_dir_opened = Signal(str)
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

    sig_tree_renamed = Signal(str)
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

    sig_open_interpreter_requested = Signal(str)
    """
    This signal is emitted to request opening an interpreter with the given
    path as working directory.

    Parameters
    ----------
    path: str
        Path to use as working directory of interpreter.
    """

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
        self.treewidget = ExplorerTreeWidget(parent=self)

        # Setup widgets
        self.treewidget.setup()
        self.chdir(getcwd_or_home())

        # Layouts
        layout = QHBoxLayout()
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

        # Signals
        self.treewidget.sig_dir_opened.connect(self.sig_dir_opened)
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

    def setup(self):
        """Performs the setup of plugin's menu and actions."""
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
        for item in [self.get_action(ExplorerTreeWidgetActions.Previous),
                     self.get_action(ExplorerTreeWidgetActions.Next),
                     self.get_action(ExplorerTreeWidgetActions.Parent),
                     self.get_action(ExplorerTreeWidgetActions.ToggleFilter)]:
            self.add_item_to_toolbar(
                item, toolbar=toolbar,
                section=ExplorerWidgetMainToolbarSections.Main)

    def update_actions(self):
        """Handle the update of actions of the plugin."""
        pass

    # ---- Public API
    # ------------------------------------------------------------------------
    def chdir(self, directory, emit=True):
        """
        Set working directory.

        Parameters
        ----------
        directory: str
            Directory to set as working directory.
        emit: bool, optional
            Default is True.
        """
        self.treewidget.chdir(directory, emit=emit)

    def get_current_folder(self):
        """Get current folder in the tree widget."""
        return self.treewidget.get_current_folder()

    def set_current_folder(self, folder):
        """
        Set the current folder in the tree widget.

        Parameters
        ----------
        folder: str
            Folder path to set as current folder.
        """
        self.treewidget.set_current_folder(folder)

    def go_to_parent_directory(self):
        """Move to parent directory."""
        self.treewidget.go_to_parent_directory()

    def go_to_previous_directory(self):
        """Move to previous directory in history."""
        self.treewidget.go_to_previous_directory()

    def go_to_next_directory(self):
        """Move to next directory in history."""
        self.treewidget.go_to_next_directory()

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
        self.treewidget.refresh(new_path, force_current)

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


class ProjectExplorerTest(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.CONF_SECTION = 'explorer'
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.treewidget = FilteredDirView(self)
        self.treewidget.setup_view()
        self.treewidget.set_root_path(osp.dirname(osp.abspath(__file__)))
        self.treewidget.set_folder_names(['variableexplorer'])
        self.treewidget.setup_project_view()
        vlayout.addWidget(self.treewidget)


def test(file_explorer):
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    if file_explorer:
        test = FileExplorerTest()
    else:
        test = ProjectExplorerTest()
    test.resize(640, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test(file_explorer=True)
    test(file_explorer=False)

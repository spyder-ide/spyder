# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer"""

# pylint: disable=C0103

# Standard library imports
from __future__ import print_function

import os.path as osp

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

# Local imports
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.translations import get_translation
from spyder.plugins.explorer.api import DirViewActions
from spyder.plugins.projects.widgets.projectexplorer import (
    ProjectExplorerTreeWidget)


_ = get_translation('spyder')


class ProjectExplorerOptionsMenuSections:
    Main = 'main'


class ProjectExplorerWidget(PluginMainWidget):
    """Project Explorer"""

    sig_open_file_requested = Signal(str)
    """
    This signal is emitted when a file is requested to be opened.

    Parameters
    ----------
    directory: str
        The path to the requested file.
    """

    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin=plugin, parent=parent)
        self.name_filters = self.get_conf('name_filters')
        self.show_hscrollbar = self.get_conf('show_hscrollbar')

        self.treewidget = ProjectExplorerTreeWidget(self, self.show_hscrollbar)
        self.treewidget.setup()
        self.treewidget.setup_view()
        self.treewidget.hide()
        self.treewidget.sig_open_file_requested.connect(
            self.sig_open_file_requested)

        self.emptywidget = ProjectExplorerTreeWidget(self)

        layout = QVBoxLayout()
        layout.addWidget(self.emptywidget)
        layout.addWidget(self.treewidget)
        self.setLayout(layout)
        self.setMinimumWidth(200)

    def setup(self):
        """Setup the widget."""
        menu = self.get_options_menu()

        hidden_action = self.get_action(DirViewActions.ToggleHiddenFiles)
        single_click_action = self.get_action(DirViewActions.ToggleSingleClick)

        for action in [hidden_action, single_click_action]:
            self.add_item_to_menu(
                action,
                menu=menu,
                section=ProjectExplorerOptionsMenuSections.Main)

    def update_actions(self):
        pass

    def get_title(self):
        return _("Project")

    def set_project_dir(self, directory):
        """Set the project directory"""
        if directory is not None:
            self.treewidget.set_root_path(osp.dirname(directory))
            self.treewidget.set_folder_names([osp.basename(directory)])
        self.treewidget.setup_project_view()
        try:
            self.treewidget.setExpanded(self.treewidget.get_index(directory),
                                        True)
        except TypeError:
            pass

    def clear(self):
        """Show an empty view"""
        self.treewidget.hide()
        self.emptywidget.show()

    def setup_project(self, directory):
        """Setup project"""
        self.emptywidget.hide()
        self.treewidget.show()

        # Setup the directory shown by the tree
        self.set_project_dir(directory)


# =============================================================================
# Tests
# =============================================================================
class ProjectExplorerTest(QWidget):
    def __init__(self, directory=None):
        QWidget.__init__(self)
        self.CONF_SECTION = 'project_explorer'
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        self.explorer = ProjectExplorerWidget(None, self, self)
        if directory is not None:
            self.directory = directory
        else:
            self.directory = osp.dirname(osp.abspath(__file__))
        self.explorer.setup_project(self.directory)
        vlayout.addWidget(self.explorer)

        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.explorer.sig_open_file_requested.connect(self.label1.setText)

        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    test = ProjectExplorerTest()
    test.resize(250, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QToolBar,
    QTreeView,
    QVBoxLayout,
)

from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.plugins.explorer.widgets.remote_explorer import RemoteExplorer
from spyder.utils.qthelpers import create_waitspinner


class RemoteFileDialogWidgets:
    Spinner = "remote_file_dialog_spinner_widget"


class RemoteFileDialogActions:
    Previous = "remote_file_dialog_previous_action"
    Next = "remote_file_dialog_next_action"
    Parent = "remote_file_dialog_parent_action"


class RemoteFileDialog(QDialog, SpyderWidgetMixin):
    
    def __init__(
        self,
        server_id,
        remote_files_manager,
        directory,
        parent=None,
        class_parent=None,
    ):
        super().__init__(parent=parent, class_parent=parent)

        self.setWindowTitle(_("Remote Files"))
        self.setModal(True)
        self._directory = None

        # Actions
        self.previous_action = self.create_action(
            RemoteFileDialogActions.Previous,
            text=_("Previous"),
            icon=self.create_icon("previous"),
            triggered=self.go_to_previous_directory,
        )
        self.next_action = self.create_action(
            RemoteFileDialogActions.Next,
            text=_("Next"),
            icon=self.create_icon("next"),
            triggered=self.go_to_next_directory,
        )
        self.parent_action = self.create_action(
            RemoteFileDialogActions.Parent,
            text=_("Parent"),
            icon=self.create_icon("up"),
            triggered=self.go_to_parent_directory,
        )
        self._spinner = create_waitspinner(
            size=16, parent=self, name=RemoteFileDialogWidgets.Spinner
        )

        # Toolbar
        self.toolbar = QToolBar(self)
        for action in [
            self.previous_action,
            self.next_action,
            self.parent_action,
        ]:
            self.toolbar.addAction(action)

        self.toolbar.addWidget(self._spinner)

        # RemoteExplorer
        self.remote_treewidget = RemoteExplorer(parent=self, only_dir=True)
        self.remote_treewidget.previous_action = self.previous_action
        self.remote_treewidget.next_action = self.next_action
        self.remote_treewidget.set_single_click_to_open(False)
        self.remote_treewidget.view.setSelectionMode(QTreeView.SingleSelection)

        self.remote_treewidget.sig_dir_opened.connect(
            self.set_selected_directory
        )
        self.remote_treewidget.sig_start_spinner_requested.connect(
            self.start_spinner
        )
        self.remote_treewidget.sig_stop_spinner_requested.connect(
            self.stop_spinner
        )

        # ButtonBox
        button_box = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.rejected)

        # Layout
        layout = QVBoxLayout()
        layout.setMenuBar(self.toolbar)
        layout.addWidget(self.remote_treewidget)
        layout.addWidget(button_box)
        self.setLayout(layout)

        self.start_spinner()
        self.remote_treewidget.chdir(
            directory=directory,
            server_id=server_id,
            remote_files_manager=remote_files_manager,
        )

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_directory(self, directory, server_id, remote_files_manager):
        self.remote_treewidget.chdir(
            directory=directory,
            server_id=server_id,
            remote_files_manager=remote_files_manager,
        )

    def start_spinner(self):
        self._spinner.start()

    def stop_spinner(self):
        self._spinner.stop()

    def go_to_previous_directory(self):
        self.remote_treewidget.go_to_previous_directory()

    def go_to_next_directory(self):
        self.remote_treewidget.go_to_next_directory()

    def go_to_parent_directory(self):
        self.remote_treewidget.go_to_parent_directory()

    def set_selected_directory(self, directory):
        if directory:
            self._directory = directory

    def get_selected_directory(self):
        return self._directory

    @staticmethod
    def get_remote_directory(
        server_id,
        remote_files_manager,
        directory,
        parent=None,
        class_parent=None,
    ):
        dialog = RemoteFileDialog(
            server_id,
            remote_files_manager,
            directory,
            parent=parent,
            class_parent=class_parent,
        )
        if dialog.exec_():
            return dialog.get_selected_directory()

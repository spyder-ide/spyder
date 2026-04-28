# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import QSize
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

if TYPE_CHECKING:
    from qtpy.QtCore import QObject
    from qtpy.QtWidgets import QWidget

    from spyder.plugins.remoteclient.api.modules.file_services import (
        SpyderRemoteFileServicesAPI,
    )


class RemoteFileDialogWidgets:
    Spinner = "remote_file_dialog_spinner_widget"


class RemoteFileDialogActions:
    Previous = "remote_file_dialog_previous_action"
    Next = "remote_file_dialog_next_action"
    Parent = "remote_file_dialog_parent_action"


class RemoteFileDialog(QDialog, SpyderWidgetMixin):
    def __init__(
        self,
        server_id: str,
        remote_files_manager: SpyderRemoteFileServicesAPI,
        directory: str,
        parent: QWidget = None,
        class_parent: QObject = None,
        only_dir: bool = False,
    ) -> None:
        super().__init__(parent=parent, class_parent=parent)

        self.setWindowTitle(
            _("Select remote directory")
            if only_dir
            else _("Select remote file")
        )
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
        self.remote_treewidget = RemoteExplorer(parent=self, only_dir=only_dir)
        self.remote_treewidget.previous_action = self.previous_action
        self.remote_treewidget.next_action = self.next_action
        self.remote_treewidget.view.header().hide()
        self.remote_treewidget.view.setColumnHidden(1, True)
        self.remote_treewidget.view.setColumnHidden(2, True)
        self.remote_treewidget.view.setColumnHidden(3, True)
        self.remote_treewidget.view.setRootIsDecorated(False)
        self.remote_treewidget.view.setSelectionMode(QTreeView.SingleSelection)
        self.remote_treewidget.view.setIconSize(QSize(22, 22))
        self.remote_treewidget.set_single_click_to_open(False)

        # Signals
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
        button_box.rejected.connect(self.reject)

        # Layout
        layout = QVBoxLayout()
        layout.setMenuBar(self.toolbar)
        layout.addWidget(self.remote_treewidget)
        layout.addWidget(button_box)
        self.setLayout(layout)

        self.set_directory(directory, server_id, remote_files_manager)

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_directory(
        self,
        directory: str,
        server_id: str,
        remote_files_manager: SpyderRemoteFileServicesAPI,
    ) -> None:
        """
        Set current directory being shown by the dialog.

        Parameters
        ----------
        directory : str
            Path of the directory that will be shown.
        server_id : str
            Id of the server where the directory is located.
        remote_files_manager : SpyderRemoteFileServicesAPI
            API instance to handle remote files access/operations.
        """
        self.start_spinner()
        self.remote_treewidget.chdir(
            directory=directory,
            server_id=server_id,
            remote_files_manager=remote_files_manager,
        )

    def start_spinner(self) -> None:
        """Start spinner."""
        self._spinner.start()

    def stop_spinner(self) -> None:
        """Stop spinner."""
        self._spinner.stop()

    def go_to_previous_directory(self) -> None:
        """Go to previous directory."""
        self.remote_treewidget.go_to_previous_directory()

    def go_to_next_directory(self) -> None:
        """Go to next directory."""
        self.remote_treewidget.go_to_next_directory()

    def go_to_parent_directory(self) -> None:
        """Go to parent directory."""
        self.remote_treewidget.go_to_parent_directory()

    def set_selected_directory(self, directory: str) -> None:
        """
        Set current selected directory.

        Parameters
        ----------
        directory : str
            Path to the currently selected directory.
        """
        if directory:
            self._directory = directory

    def get_selected_directory(self) -> str | None:
        """
        Get currently selected directory.

        Returns
        -------
        str | None
            Current selected directory or `None` if nothing has been selected.
        """
        return self._directory

    @staticmethod
    def get_remote_directory(
        server_id: str,
        remote_files_manager: SpyderRemoteFileServicesAPI,
        directory: str,
        parent: QWidget = None,
        class_parent: QObject = None,
        only_dir: bool = True,
    ) -> str | None:
        """
        Allow to get a remote files system directory path.

        Handles `RemoteFileDialog` instantiation.

        Parameters
        ----------
        server_id : str
            Id of the server where the directory is located.
        remote_files_manager : SpyderRemoteFileServicesAPI
            API instance to handle remote files access/operations.
        directory : str
            Path of the initial directory to show in the dialog.
        parent : QWidget, optional
            Parent widget to use for the dialog. The default is `None`.
        class_parent : QObject, optional
            Class definition of the parent to use for the dialog. The default
            is `None`.
        only_dir : bool, optional
            If only directories should be shown/listed in the dialog. The
            default is `True`.

        Returns
        -------
        str | None
            Path to the selected directory or `None` if nothing has been selected
            or the dialog is not accepted.
        """
        dialog = RemoteFileDialog(
            server_id,
            remote_files_manager,
            directory,
            parent=parent,
            class_parent=class_parent,
        )
        if dialog.exec_():
            return dialog.get_selected_directory()

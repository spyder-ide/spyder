# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QSizePolicy,
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
        server_name: str,
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
        self.setFixedSize(650, 400)
        self._server_name = server_name
        self._current_directory = None
        self._selected = None
        self._only_dir = only_dir

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
        self.current_directory = QLabel(self)
        self.current_directory.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred,
        )

        self.toolbar.addWidget(self.current_directory)
        self.toolbar.addWidget(self._spinner)

        for action in [
            self.previous_action,
            self.next_action,
            self.parent_action,
        ]:
            self.toolbar.addAction(action)

        # RemoteExplorer
        self.remote_treewidget = RemoteExplorer(
            parent=self, only_dir=only_dir, register_actions_and_menus=False
        )
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
            self.set_current_directory
        )
        self.remote_treewidget.sig_start_spinner_requested.connect(
            self.start_spinner
        )
        self.remote_treewidget.sig_stop_spinner_requested.connect(
            self.stop_spinner
        )
        self.remote_treewidget.view.selectionModel().currentChanged.connect(
            self._set_selected
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

        self.set_initial_directory(directory, server_id, remote_files_manager)

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_initial_directory(
        self,
        directory: str,
        server_id: str,
        remote_files_manager: SpyderRemoteFileServicesAPI,
    ) -> None:
        """
        Set initial directory being shown by the dialog.

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

    def set_current_directory(self, directory: str) -> None:
        """
        Set current directory.

        Parameters
        ----------
        directory : str
            Path to the currently selected directory.
        """
        if directory:
            current_directory = directory
            if len(directory) > 30:
                metrics = QFontMetrics(self.font())
                max_width = 30 * metrics.width("W")
                current_directory = metrics.elidedText(
                    directory, Qt.ElideMiddle, max_width
                )
            self.current_directory.setText(
                _(
                    "Current location: {server_name}:/{current_directory}"
                ).format(
                    server_name=self._server_name,
                    current_directory=current_directory,
                )
            )
            self._current_directory = directory

    def get_current_directory(self) -> str:
        """
        Get currently directory.

        Returns
        -------
        str
            Current directory.
        """
        return self._current_directory

    def _set_selected(self, current, previous) -> None:
        """
        Set current directory.

        Parameters
        ----------
        current : QModelIndex
            Current selected index.
        previous : QModelIndex
            Previously selected index.
        """
        data = current.data(role=Qt.UserRole + 1)
        if data:
            if not self._only_dir and data["type"] == "directory":
                return
            self._selected = data["name"]

    def get_selected(self) -> str | None:
        """
        Get currently selected directory/file.

        Returns
        -------
        str | None
            Current selected directory/file or `None` if nothing has been selected.
        """
        return self._selected

    @staticmethod
    def get_remote_directory(
        server_name: str,
        server_id: str,
        remote_files_manager: SpyderRemoteFileServicesAPI,
        directory: str,
        parent: QWidget = None,
        class_parent: QObject = None,
    ) -> str | None:
        """
        Allow to get a directory path from a remote file system.

        Handles `RemoteFileDialog` instantiation.

        Parameters
        ----------
        server_name: str
            Name of the server where the directory is located.
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

        Returns
        -------
        str | None
            Path to the selected directory or `None` if nothing has been selected
            or the dialog is not accepted.
        """
        dialog = RemoteFileDialog(
            server_name,
            server_id,
            remote_files_manager,
            directory,
            parent=parent,
            class_parent=class_parent,
            only_dir=True,
        )
        if dialog.exec_():
            return dialog.get_selected() or dialog.get_current_directory()

    @staticmethod
    def get_remote_file(
        server_name: str,
        server_id: str,
        remote_files_manager: SpyderRemoteFileServicesAPI,
        directory: str,
        parent: QWidget = None,
        class_parent: QObject = None,
    ) -> str | None:
        """
        Allow to get a file path from a remote file system.

        Handles `RemoteFileDialog` instantiation.

        Parameters
        ----------
        server_name: str
            Name of the server where the directory is located.
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

        Returns
        -------
        str | None
            Path to the selected file or `None` if no file has been selected
            or the dialog is not accepted.
        """
        dialog = RemoteFileDialog(
            server_name,
            server_id,
            remote_files_manager,
            directory,
            parent=parent,
            class_parent=class_parent,
            only_dir=False,
        )
        if dialog.exec_():
            return dialog.get_selected()

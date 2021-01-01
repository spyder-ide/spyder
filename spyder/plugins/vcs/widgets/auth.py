#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Components and widgets with auth handling."""

# pylint: disable=W0102

# Standard library imports
import os
import shutil
import typing
import os.path as osp
from tempfile import TemporaryDirectory
from functools import partial
from concurrent.futures import ThreadPoolExecutor

# Third party imports
from qtpy.QtCore import Qt, Slot, Signal
from qtpy.QtWidgets import (
    QLabel,
    QAction,
    QDialog,
    QWidget,
    QComboBox,
    QLineEdit,
    QFormLayout,
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QPlainTextEdit,
    QDialogButtonBox
)

# Local imports
from spyder.utils.qthelpers import action2button as spy_action2button
from spyder.api.translations import get_translation
from spyder.widgets.comboboxes import UrlComboBox

from .utils import THREAD_ENABLED, LoginDialog, ThreadWrapper, action2button
from .common import BaseComponent
from ..backend.errors import VCSAuthError

_ = get_translation('spyder')


class AuthComponent(BaseComponent):
    """An abstract component to manage :class:`~VCSBackendBase` auth."""

    sig_auth_operation_success = Signal(str, object)
    """
    This signal is emitted when an auth operation was done successfully.

    Parameters
    ----------
    operation : str
        The operation done.
        It is usually the backend method name.

    result : object
        The result of operation.
        It is always a non-zero object.
    """
    @Slot(str)
    @Slot(str, tuple, dict)
    def auth_operation(  # pylint: disable=W0102
            self,
            operation: str,
            args: tuple = (),
            kwargs: dict = {},
    ):
        """
        A helper to do operations that can requires authentication.

        Parameters
        ----------
        operation : str
            The method name to call.
            This will be used to get the corresponding backend error.
        args : tuple, optional
            Extra positional parameters to pass to the method.
        kwargs : dict, optional
            Extra keyword parameters to pass to the method.
        """
        @Slot(object)
        def _handle_result(result):
            if result:
                self.sig_auth_operation_success.emit(operation, result)
            # Maybe it's better to show an error here?

        def _error(ex):
            if isinstance(ex, VCSAuthError):
                self.handle_auth_error(ex, operation, args, kwargs)
            else:
                self.error_handler(ex, raise_=True)

        feature = self.manager.safe_check(operation)
        if feature is not None:
            ThreadWrapper(
                self,
                partial(feature, *args, **kwargs),
                result_slots=(_handle_result, ),
                error_slots=(_error, ),
                nothread=not THREAD_ENABLED,
            ).start()

    def handle_auth_error(self,
                          ex: VCSAuthError,
                          operation: str,
                          args: tuple = (),
                          kwargs: dict = {}) -> None:
        """Handle authentication errors by showing an input dialog."""
        def _accepted():
            try:
                ex.credentials = dialog.to_credentials()
            except ValueError:
                _rejected()
            else:
                self.auth_operation(operation, args, kwargs)

        def _rejected():
            QMessageBox.critical(
                self,
                _("Authentication failed"),
                _("Failed to authenticate to the {} remote server.".format(
                    manager.VCSNAME)),
            )

        manager = self.manager
        credentials = ex.credentials

        # UNSAFE: Use backend credentials if error credentials are not given.
        credentials.update((key, manager.credentials.get(key))
                           for key in ex.required_credentials
                           if credentials.get(key) is None)

        if credentials:
            dialog = LoginDialog(self, **credentials)
            dialog.accepted.connect(_accepted)
            dialog.rejected.connect(_rejected)
            dialog.show()


class CommitComponent(AuthComponent, QWidget):
    """A widget for committing."""
    def __init__(self, *args, commit_action: QAction, **kwargs):
        super().__init__(*args, **kwargs)

        self.commit_message = QPlainTextEdit()
        commit_button = spy_action2button(commit_action, parent=self)

        self.commit_message.setPlaceholderText(_("Commit message ..."))

        commit_button.setToolButtonStyle(Qt.ToolButtonTextOnly)

        commit_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed))

        # FIXME: change color
        commit_button.setStyleSheet("background-color: #1122cc;")

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.commit_message)
        layout.addWidget(commit_button)

        # Slots
        commit_button.triggered.connect(self.commit)
        self.sig_auth_operation_success.connect(self.commit_message.clear)

    @Slot()
    def setup(self):
        with self.block_timer():
            # BUG: this does not preserve undo history
            self.commit_message.clear()

        self.setVisible(bool(self.manager.safe_check("commit")))

    @Slot()
    def commit(self) -> None:
        """Do a commit."""
        text = self.commit_message.toPlainText()

        if text:
            self.auth_operation("commit", (text, ), dict(is_path=False))

    # Allow to commit by calling the instance
    __call__ = commit


class RemoteComponent(AuthComponent, QWidget):
    """A widget for remove operations."""

    REFRESH_TIME = 4000

    def __init__(self, *args, fetch_action: QAction, pull_action: QAction,
                 push_action: QAction, **kwargs):
        super().__init__(*args, **kwargs)

        self._old_nums = (None, None)

        # Widgets
        self.fetch_button = action2button(
            fetch_action,
            text_beside_icon=True,
            parent=self,
        )

        self.pull_button = action2button(
            pull_action,
            text_beside_icon=True,
            parent=self,
        )

        self.push_button = action2button(
            push_action,
            text_beside_icon=True,
            parent=self,
        )

        # Layout
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.fetch_button)
        layout.addWidget(self.pull_button)
        layout.addWidget(self.push_button)

        self.setLayout(layout)

        # Slots
        self.sig_auth_operation_success.connect(self.refresh)
        self.fetch_button.triggered.connect(lambda: self.auth_operation(
            "fetch",
            kwargs=dict(sync=True),
        ))
        self.pull_button.triggered.connect(lambda: self.auth_operation("pull"))
        self.push_button.triggered.connect(lambda: self.auth_operation("push"))

    @Slot()
    def setup(self):
        with self.block_timer():
            pass

        manager = self.manager
        if manager.repodir:
            self.fetch_button.setEnabled(manager.fetch.enabled)
            self.pull_button.setEnabled(manager.pull.enabled)
            self.push_button.setEnabled(manager.push.enabled)

            self.setVisible(manager.fetch.enabled or manager.fetch.enabled
                            or manager.push.enabled)
        else:
            self.hide()

    @Slot()
    def refresh(self) -> None:
        """
        Show the numbers of commits to pull and push compared to remote.
        """
        def _handle_result(commits_nums):
            if commits_nums:
                # FIXME: Don't edit button text through actions
                for i, action in enumerate((
                        self.pull_button.defaultAction(),
                        self.push_button.defaultAction(),
                )):
                    if commits_nums[i] != self._old_nums[i]:
                        label = action.text().rsplit(" ", 1)
                        if (len(label) == 2
                                and label[1][0] + label[1][-1] == "()"):
                            # Found existing number
                            del label[1]

                        if commits_nums[i] > 0:
                            action.setText("{} ({})".format(
                                " ".join(label), commits_nums[i]))
                        else:
                            action.setText(" ".join(label))

                self._old_nums = commits_nums
            else:
                self.pull_button.defaultAction().setText(_("pull"))
                self.push_button.defaultAction().setText(_("push"))
                self._old_nums = (None, None)

        self.do_call("fetch", result_slots=_handle_result)


class CreateDialog(AuthComponent, QDialog):
    """A dialog to manage cloning operation."""

    sig_repository_ready = Signal(str)
    """
    This signal is emitted when repository creation is done.

    Parameters
    ----------
    repodir : str
        The repository directory.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = {}
        self.tempdir = None

        # Widgets
        self.vcs_select = QComboBox()
        self.directory = QLineEdit()
        self.url_select = UrlComboBox(self)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok
                                     | QDialogButtonBox.Cancel)

        # Currently, only opened projects can create repositories,
        # so it is forbidden to change the repository path.
        self.directory.setReadOnly(True)

        # Layout
        rootlayout = QFormLayout(self)
        rootlayout.addRow(QLabel(_("<h3>Create new repository</h3>")))
        rootlayout.addRow(_("VCS Type"), self.vcs_select)
        rootlayout.addRow(_("Destination"), self.directory)
        rootlayout.addRow(_("Source repository"), self.url_select)
        rootlayout.addRow(buttonbox)

        # Slots
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        buttonbox.rejected.connect(self.cleanup)

    @Slot()
    def setup(self, rootpath: str):
        with self.block_timer():
            self.vcs_select.clear()
            self.directory.clear()
            self.url_select.clear()

        create_vcs_types = self.manager.create_vcs_types

        if create_vcs_types:
            self.vcs_select.addItems(create_vcs_types)
            self.directory.setText(rootpath)
        else:
            # Force dialog to be hidden
            self.hide()

    # Public slots
    @Slot()
    def cleanup(self, fail: bool = False) -> None:
        """Remove the temporary directory."""
        self.tempdir = None
        if fail:
            # Inform the parent that the clone is failed.
            self.rejected.emit()

    # Qt overrides
    @Slot()
    def accept(self) -> None:
        url = self.url_select.currentText()
        if url:
            if not self.url_select.is_valid(url):
                QMessageBox.critical(
                    self, _("Invalid URL"),
                    _("Creating a repository from an existing"
                      "one requires a valid URL."))
                return

            if os.listdir(self.directory.text()):
                ret = QMessageBox.warning(
                    self,
                    _("File override"),
                    _("Local files will be overriden by cloning.\n"
                      "Would you like to continue anyway?"),
                    QMessageBox.Ok | QMessageBox.Cancel,
                )
                if ret != QMessageBox.Ok:
                    return
        else:
            url = None
        self._try_create(
            self.vcs_select.currentText(),
            self.directory.text(),
            url,
        )

        super().accept()

    def show(self) -> None:
        self.tempdir = TemporaryDirectory()
        super().show()

    # Private methods
    def _try_create(self, vcs_type: str, path: str,
                    from_: typing.Optional[str]) -> None:
        def _error(ex):
            if isinstance(ex, VCSAuthError):
                self._handle_auth_error(ex)
            else:
                QMessageBox.critical(
                    self, _("Create failed"),
                    _("Repository creation failed unexpectedly."))
                self.cleanup(True)

        def _handle_result(result):
            if result:
                ThreadWrapper(
                    self,
                    _move,
                    result_slots=(
                        lambda _: self.sig_repository_ready.emit(path),
                        self.cleanup),
                    error_slots=(_error, ),
                ).start()
            else:
                QMessageBox.critical(
                    self, _("Create failed"),
                    _("Repository creation failed unexpectedly."))
                self.cleanup(True)

        def _move():
            tempdir = self.tempdir.name
            with ThreadPoolExecutor() as pool:
                pool.map(lambda x: shutil.move(osp.join(tempdir, x), path),
                         os.listdir(tempdir))

        ThreadWrapper(
            self,
            partial(
                self.manager.create_with,
                vcs_type,
                self.tempdir.name,
                from_=from_,
                credentials=self.credentials,
            ),
            result_slots=(_handle_result, ),
            error_slots=(_error, ),
            nothread=not THREAD_ENABLED,
        ).start()

    @Slot(VCSAuthError)
    def _handle_auth_error(self, ex: VCSAuthError):
        def _accepted():
            self.credentials = dialog.to_credentials()
            self._try_create(self.vcs_select.currentText(),
                             self.directory.text(),
                             self.url_select.currentText())

        def _rejected():
            QMessageBox.critical(
                self,
                _("Authentication failed"),
                _("Failed to authenticate to the {} remote server.").format(
                    self.vcs_select.currentText()),
            )
            self.cleanup()

        credentials = {
            # Use stored credentials if the error
            # does not give them.
            key: getattr(ex, key, None) or self.credentials.get(key)
            for key in ex.required_credentials
        }

        if credentials:
            dialog = LoginDialog(self, **credentials)
            dialog.accepted.connect(_accepted)
            dialog.rejected.connect(_rejected)
            dialog.show()

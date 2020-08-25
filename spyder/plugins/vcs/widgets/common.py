#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Common widgets for the VCS GUI."""

# Standard library imports
import typing

# Third party imports
import qtawesome as qta
from qtpy.QtCore import Slot, Signal, QThread, QObject
from qtpy.QtWidgets import (QTreeWidgetItem, QDialog, QWidget, QLineEdit,
                            QVBoxLayout, QLabel, QLayout, QDialogButtonBox,
                            QAbstractButton, QComboBox, QCompleter)

# Local imports
from spyder.api.translations import get_translation
from spyder.config.gui import is_dark_interface

from ..utils.api import ChangedStatus, VCSBackendManager

_ = get_translation('spyder')

THREAD_ENABLED = True

SLOT = typing.Union[(
    typing.Callable[..., typing.Optional[object]],
    Signal,
    Slot,
)]

if is_dark_interface():
    STATE_TO_TEXT = {
        ChangedStatus.ADDED:
        qta.icon("fa5.plus-square", color="#00ff00"),
        ChangedStatus.MODIFIED:
        qta.icon(
            "fa5.square",
            "fa.circle",
            color="orange",
            options=[{}, {
                'scale_factor': 0.5,
            }],
        ),
        ChangedStatus.REMOVED:
        qta.icon("fa5.minus-square", color="red"),
        ChangedStatus.IGNORED:
        qta.icon(
            "fa5.square",
            "mdi.slash-forward",
            color="gray",
            options=[{}, {
                'scale_factor': 0.5,
            }],
        ),
        ChangedStatus.UNKNOWN:
        qta.icon(
            "fa5.square",
            "fa5s.question",
            color="gray",
            options=[{}, {
                'scale_factor': 0.5,
            }],
        ),
    }
else:
    # FIXME: use different colors for white theme
    STATE_TO_TEXT = {
        ChangedStatus.ADDED:
        qta.icon("fa5.plus-square", color="#00ff00"),
        ChangedStatus.MODIFIED:
        qta.icon(
            "fa5.square",
            "fa.circle",
            color="orange",
            options=[{}, {
                'scale_factor': 0.5,
            }],
        ),
        ChangedStatus.REMOVED:
        qta.icon("fa5.minus-square", color="red"),
        ChangedStatus.IGNORED:
        qta.icon(
            "fa5.square",
            "mdi.slash-forward",
            color="gray",
            options=[{}, {
                'scale_factor': 0.5,
            }],
        ),
        ChangedStatus.UNKNOWN:
        qta.icon(
            "fa5.square",
            "fa5s.question",
            color="gray",
            options=[{}, {
                'scale_factor': 0.5,
            }],
        ),
    }

_STATE_LIST = tuple(STATE_TO_TEXT.keys())


class ChangesItem(QTreeWidgetItem):
    """
    An item for staged/unstaged files.

    It creates a fake icon representing the file state in the VCS.

    See Also
    --------
    __lt__ : For item comparison details.
    """
    def __init__(self, *args: object):
        super().__init__(*args)
        self.state: typing.Optional[int] = None

    def setup(self, state: int, path: str) -> None:
        """
        Set up the item UI. Can be called multiple times.

        Parameters
        ----------
        state : int
            The changed status of file.
            Must be a valid value of ChangedStatus.
        path : str
            The path to show.
        """
        self.state = state
        icon_spec = STATE_TO_TEXT.get(state,
                                      STATE_TO_TEXT[ChangedStatus.UNKNOWN])
        self.setIcon(0, icon_spec)

        if path:
            self.setText(0, path)
        else:
            self.setText(0, "")

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        """
        Compare two treewidget items, prioritizing state over path.

        Parameters
        ----------
        other : QTreeWidgetItem
            The item to compare.

        Returns
        -------
        bool
            True if self is less than other, False otherwise.
        """
        if self.state == other.state:
            # compare with paths if the states are the same
            return bool(self.text(0) < other.text(0))

        return _STATE_LIST.index(self.state) < _STATE_LIST.index(other.state)


class BranchesComboBox(QComboBox):
    """
    An editable combo box that manages branches.

    Parameters
    ----------
    manager : VCSBackendManager
        The VCS manager.
    """

    def __init__(self, manager: VCSBackendManager, *args: object,
                 **kwargs: object):
        super().__init__(*args, **kwargs)
        self._manager = manager
        self.setEditable(True)
        # branches cache
        self._branches: typing.List[str] = []

    @Slot()
    def refresh(self) -> None:
        """Clear and re-add branches."""
        def _task():
            """Task executed in another thread."""

            if manager.type_().branch.fget.enabled:
                current_branch = manager.branch
            else:
                current_branch = None

            if manager.type_().branches.fget.enabled:
                self._branches.extend(manager.editable_branches)
            elif current_branch is not None:
                self._branches.append(manager.branch)
            return current_branch

        @Slot(object)
        def _handle_result(current_branch):
            if self._branches:
                # Block signals to reduce useless signal emissions
                oldstate = self.blockSignals(True)

                self.addItems(self._branches)
                if current_branch is not None:
                    index = self.findText(current_branch)
                    if index == -1:
                        self.setCurrentText(current_branch)
                    else:
                        self.setCurrentIndex(index)

                self.blockSignals(oldstate)
                self.setDisabled(False)
                self.setCompleter(QCompleter(self._branches, self))

            # If there are not any branches, keep the widget disabled.

        @Slot(Exception)
        def _raise(ex):
            raise ex

        manager = self._manager

        # Disable the widget during changes
        self.setDisabled(True)
        self.clear()
        self._branches = []
        self.setCompleter(QCompleter(self))

        if THREAD_ENABLED:
            ThreadWrapper(
                self,
                _task,
                result_slots=(_handle_result, ),
                error_slots=(_raise, ),
            ).start()
        else:
            _handle_result(_task())


class LoginDialog(QDialog):
    """
    A modeless dialog for VCS credentials.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget. The default is None.
    **credentials
        A valid VCSBackendBase.credentials mapping.
        To respect the specifications, an input field
        is created for each key in credentials.
        Credential keys with value will be automatically
        set as initial text for input fields.
    """
    def __init__(self, parent: QWidget = None, **credentials: object):
        super().__init__(parent=parent)

        rootlayout = QVBoxLayout()
        self._old_credentials: typing.Dict[str, object] = credentials
        self.credentials_edit: typing.Dict[str, QLineEdit] = {}

        for key in ("username", "email", "token"):
            if key in credentials:
                rootlayout.addLayout(
                    self._create_credentials_field(key, credentials[key]))

        if "password" in credentials:
            rootlayout.addLayout(
                self._create_credentials_field(
                    "password",
                    credentials["password"],
                    hide=True,
                ))

        self.buttonbox = buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Reset
            | QDialogButtonBox.Cancel)
        buttonbox.clicked.connect(self.handle_reset)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        rootlayout.addWidget(buttonbox)

        self.setLayout(rootlayout)

    @Slot(QAbstractButton)
    def handle_reset(self, widget: QAbstractButton) -> None:
        """Handle all the buttons in button box."""
        role = self.buttonbox.buttonRole(widget)
        if role == self.buttonbox.ResetRole:
            for key, val in self._old_credentials.items():
                self.credentials_edit[key].setText(val if val else "")

    def to_credentials(self) -> typing.Dict[str, object]:
        """
        Get credentials from the dialog.

        Returns
        -------
        dict
            A valid VCSBackendBase.credentials mapping.
        """
        credentials = {}
        for key, lineedit in self.credentials_edit.items():
            credentials[key] = lineedit.text()

        return credentials

    def _create_credentials_field(self,
                                  key: str,
                                  default: typing.Optional[object] = None,
                                  hide: bool = False) -> QLayout:
        if not default:
            default = ""

        layout = QVBoxLayout()
        layout.addWidget(QLabel(_(key.capitalize()) + ":"))
        self.credentials_edit[key] = lineedit = QLineEdit(str(default))

        if hide:
            lineedit.setEchoMode(QLineEdit.Password)

        layout.addWidget(lineedit)
        return layout


class ThreadWrapper(QThread):
    """
    Wrap QThread.

    Parameters
    ----------
    parent : QObject
        The parent object.
        This is must be a valid QObject for emitting signals.

    func : callable
        The function to be called in the thread.
    result_slots : tuple, optional
        The slots to connect to the sig_result signal.
    error_slots : tuple, optional
        The slots to connect to the sig_error signal.

    pass_self : bool, optional
        If True, internal result/exception handling is disabled,
        the result_slots and error_slots parameters have no effects
        and this object will be passed as parameter to func.
        The default is False.
    """

    sig_result = Signal(object)
    """
    This signal is emitted if func is executed without exceptions.

    Parameters
    ----------
    result: object
        The object returned from func.
    """

    sig_error = Signal(Exception)
    """
    This signal is emitted if func raises an exception.

    Parameters
    ----------
    ex: Exception
        The exception raised.
    """

    def __init__(self,
                 parent: QObject,
                 func: typing.Callable[..., None],
                 result_slots: typing.Iterable[SLOT] = (),
                 error_slots: typing.Iterable[SLOT] = (),
                 pass_self: bool = False):
        super().__init__(parent)
        self.func = func
        self.pass_self = pass_self

        # bind slots
        for slot in result_slots:
            self.sig_result.connect(slot)
        for slot in error_slots:
            self.sig_error.connect(slot)

    def run(self) -> None:
        if self.pass_self:
            self.func(self)
        else:
            try:
                result = self.func()
            except Exception as ex:
                self.sig_error.emit(ex)
            else:
                self.sig_result.emit(result)

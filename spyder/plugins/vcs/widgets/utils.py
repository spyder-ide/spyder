#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Common widgets for the VCS UI."""

# Standard library imports
from typing import Dict, Tuple, Union, Callable, Iterator, Optional

# Third party imports
from qtpy.QtCore import Slot, Signal, QObject, QThread
from qtpy.QtWidgets import (
    QDialog,
    QWidget,
    QLineEdit,
    QFormLayout,
    QAbstractButton,
    QDialogButtonBox
)

# Local imports
from spyder.utils.qthelpers import action2button as spy_action2button
from spyder.api.translations import get_translation

_ = get_translation('spyder')

__all__ = ("THREAD_ENABLED", "PAUSE_CYCLE", "SLOT", "LoginDialog",
           "ThreadWrapper", "action2button")

# TODO: move these to configs for debug purposes
THREAD_ENABLED = True
PAUSE_CYCLE = 16

SLOT = Union[(
    Callable[..., Optional[object]],
    Signal,
    Slot,
)]


class LoginDialog(QDialog):
    """
    A modeless dialog for VCS credentials.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget. The default is None.
    **credentials
        A valid :attr:`.VCSBackendBase.credentials` mapping.
        To respect the specifications, an input field
        is created for each key in credentials.
        Credential keys with value will be automatically
        set as initial text for input fields.

    .. tip::
        This dialog can be used for any credentials prompt
        as it does not depend on :class:`~VCSBackendBase`.
    """
    def __init__(self, parent: QWidget = None, **credentials: object):
        super().__init__(parent=parent)

        rootlayout = QFormLayout(self)
        self._old_credentials: Dict[str, object] = credentials
        self.credentials_edit: Dict[str, QLineEdit] = {}

        for key in ("username", "email", "token"):
            if key in credentials:
                rootlayout.addRow(
                    *self._create_credentials_field(key, credentials[key]))

        if "password" in credentials:
            rootlayout.addRow(*self._create_credentials_field(
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

        rootlayout.addRow(buttonbox)

    @Slot(QAbstractButton)
    def handle_reset(self, widget: QAbstractButton) -> None:
        """Handle all the buttons in button box."""
        role = self.buttonbox.buttonRole(widget)
        if role == self.buttonbox.ResetRole:
            for key, val in self._old_credentials.items():
                self.credentials_edit[key].setText(val if val else "")

    def to_credentials(self) -> Dict[str, object]:
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
                                  default: Optional[object] = None,
                                  hide: bool = False) -> Tuple[str, QWidget]:
        if not default:
            default = ""
        label = _(key.capitalize()) + ":"
        self.credentials_edit[key] = lineedit = QLineEdit(str(default))

        if hide:
            lineedit.setEchoMode(QLineEdit.Password)

        return label, lineedit


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

    nothread : bool, optional
        If True, the run method is called direcly in `__init__`
        and the start method will do nothing.
        The default is False.
    """

    sig_result = Signal(object)
    """
    This signal is emitted if func is executed without exceptions.

    Parameters
    ----------
    result: object
        The object returned from :attr:`~ThreadWrapper.func`.
    """

    sig_error = Signal(Exception)
    """
    This signal is emitted if func raises an exception.

    Parameters
    ----------
    ex: Exception
        The exception raised by :attr:`~ThreadWrapper.func`.
    """
    def __init__(self,
                 parent: QObject,
                 func: Callable[..., None],
                 result_slots: Iterator[SLOT] = (),
                 error_slots: Iterator[SLOT] = (),
                 pass_self: bool = False,
                 nothread: bool = False):
        super().__init__(parent)
        self.func = func
        self.pass_self = pass_self

        # bind slots
        for slot in result_slots:
            self.sig_result.connect(slot)
        for slot in error_slots:
            self.sig_error.connect(slot)

        if nothread:
            self.run()
            self.func = None

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

    def start(self, *args, **kwargs) -> None:
        if self.func is not None:
            super().start(*args, **kwargs)


def action2button(action, *args, **kwargs):
    """
    A wrapper around action2button that update button properties
    when they changes in the action.
    """
    def _update():
        button.setText(action.text())

    action.changed.connect(_update)
    button = spy_action2button(action, *args, **kwargs)
    return button

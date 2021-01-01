#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Widgets for branch management."""

# Standard library imports
from typing import Set, Union
from functools import partial

# Third party imports
from qtpy.QtCore import Slot, Signal
from qtpy.QtWidgets import (
    QLabel,
    QDialog,
    QComboBox,
    QCompleter,
    QMessageBox,
    QVBoxLayout,
    QAbstractButton,
    QDialogButtonBox
)

# Local imports
from spyder.api.translations import get_translation

from .utils import THREAD_ENABLED, ThreadWrapper
from .common import BaseComponent
from ..backend.errors import VCSPropertyError

_ = get_translation('spyder')


class BranchesComponent(BaseComponent, QComboBox):
    """
    An editable combo box that manages branches.
    """

    sig_branch_changed = Signal(str)
    """
    This signal is emitted when the current branch change

    Parameters
    ----------
    branchname: str
        The current branch name in the VCS.

    See Also
    --------
    BranchesComboBox.select
        To change the current branch.
    """

    REFRESH_TIME = 2500

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditable(True)
        # branches cache
        self._branches: Set[str] = set()

        self.sig_branch_changed.connect(self.refresh)
        self.currentIndexChanged.connect(self.select)

    @Slot()
    def setup(self):
        with self.block_timer():
            self._branches.clear()
            self.clear()

        if self.manager.repodir is not None:
            backend_type = self.manager.type
            self.setVisible(backend_type.branches.fget.enabled
                            or backend_type.branch.fget.enabled)
            self.setEnabled(backend_type.branch.fset.enabled)
        else:
            self.hide()

    @Slot()
    def refresh(self) -> None:
        """Clear and re-add branches."""
        def _task():
            """Task executed in another thread."""
            branches = set()
            manager = self.manager
            if manager.type.branch.fget.enabled:
                current_branch = manager.branch
            else:
                current_branch = None

            if manager.type.editable_branches.fget.enabled:
                try:
                    branches.update(manager.editable_branches)
                except VCSPropertyError:
                    # Suppress editable_branches fail
                    pass
            elif current_branch is not None:
                branches.add(manager.branch)
            return (current_branch, branches)

        @Slot(object)
        def _handle_result(result):
            if any(result):
                current_branch, branches = result
                new_branches = branches - self._branches
                old_branches = self._branches - branches
                self._branches = branches

                # Block signals to reduce useless signal emissions
                oldstate = self.blockSignals(True)

                # Add/Remove branches
                self.addItems(sorted(new_branches))
                for branch in old_branches:
                    index = self.findText(branch)
                    if index != -1:
                        self.removeItem(index)

                if (current_branch is not None
                        and not self.lineEdit().hasFocus()):
                    index = self.findText(current_branch)
                    if index == -1:
                        self.setCurrentText(current_branch)
                    else:
                        self.setCurrentIndex(index)

                self.blockSignals(oldstate)
            else:
                # Reset branch list
                self.clear()
                self._branches.clear()

            self.setCompleter(QCompleter(self._branches, self))
            self.setDisabled(not self._branches)

        if self.manager.repodir is not None:
            ThreadWrapper(
                self,
                _task,
                result_slots=(_handle_result, ),
                error_slots=(lambda: self.setCompleter(QCompleter(self)),
                             partial(self.error_handler, raise_=True)),
                nothread=not THREAD_ENABLED,
            ).start()

    @Slot()
    @Slot(str)
    @Slot(int)
    def select(self, branchname: Union[str, int] = None) -> None:
        """
        Select a branch given its name.

        Parameters
        ----------
        branchname : str or int, optional
            The branch name.
            Can be also an integer that will be used
            to get the corresponding value.
        """
        if self.isEnabled():
            # Ignore the event when the widget is disabled

            if branchname is None:
                branchname = self.currentText()

            elif isinstance(branchname, int):
                if branchname == -1:
                    branchname = ""
                else:
                    branchname = self.currentText()

            if branchname:
                branch_prop = self.manager.type.branch
                if branch_prop.fget.enabled and branch_prop.fset.enabled:
                    ThreadWrapper(
                        self,
                        partial(setattr, self.manager, "branch", branchname),
                        result_slots=(partial(self.sig_branch_changed.emit,
                                              branchname), ),
                        error_slots=(partial(self._handle_select_error,
                                             branchname), ),
                        nothread=not THREAD_ENABLED,
                    ).start()

    @Slot(Exception)
    def _handle_select_error(self, branchname: str, ex: Exception) -> None:
        @Slot()
        def _show_error():
            reason = ex.raw_error if ex.error is None else ex.error
            with self.block_timer():
                self.refresh()
            QMessageBox.critical(
                self,
                _("Failed to change branch"),
                _("Cannot switch to branch {}." +
                  ("\nReason: {}" if reason else "")).format(
                      branchname, reason),
            )

        @Slot(QAbstractButton)
        def _handle_buttons(widget):
            create = empty = False
            if widget == empty_button:
                create = empty = True
            else:
                role = buttonbox.buttonRole(widget)
                if role == QDialogButtonBox.YesRole:
                    create = True

            if create:
                ThreadWrapper(
                    self,
                    partial(self.manager.create_branch,
                            branchname,
                            empty=empty),
                    result_slots=(lambda result:
                                  (self.sig_branch_changed.emit(branchname)
                                   if result else _show_error()), ),
                    error_slots=(_show_error, ),
                    nothread=not THREAD_ENABLED,
                ).start()
                dialog.accept()
            else:
                dialog.reject()

        if not isinstance(ex, VCSPropertyError):
            self.refresh()
            self.error_handler(ex, raise_=True)

        if (self.manager.create_branch.enabled
                and branchname not in self._branches):
            dialog = QDialog(self)
            dialog.setModal(True)

            rootlayout = QVBoxLayout(dialog)
            rootlayout.addWidget(
                QLabel(
                    _("The branch {} does not exist.\n"
                      "Would you like to create it?").format(branchname)))

            buttonbox = QDialogButtonBox()
            buttonbox.addButton(QDialogButtonBox.Yes)
            if self.manager.create_branch.extra["empty"]:
                # Allow the empty branch creation only if supported
                empty_button = buttonbox.addButton(
                    _("Yes, create empty branch"),
                    QDialogButtonBox.YesRole,
                )
            else:
                empty_button = None
            buttonbox.addButton(QDialogButtonBox.No)
            buttonbox.clicked.connect(_handle_buttons)

            rootlayout.addWidget(buttonbox)
            dialog.show()
        else:
            with self.block_timer():
                self.refresh()
            _show_error()

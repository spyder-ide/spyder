#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Widgets for change areas."""

# Standard library imports
from collections.abc import Iterable
from functools import partial
import typing

# Third party imports
from qtpy.QtCore import Qt, Signal, Slot, QCoreApplication, QPoint
from qtpy.QtWidgets import (QTreeWidgetItem, QTreeWidget, QMenu)
import qtawesome as qta

# Local imports
from spyder.api.translations import get_translation
from spyder.config.gui import is_dark_interface

from .common import ThreadWrapper, THREAD_ENABLED, PAUSE_CYCLE
from ..utils.api import ChangedStatus, VCSBackendManager

_ = get_translation('spyder')

if is_dark_interface():
    STATE_TO_ICON = {
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
    STATE_TO_ICON = {
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

_STATE_LIST = tuple(STATE_TO_ICON.keys())

CHANGE = typing.Dict[str, object]


class ChangeItem(QTreeWidgetItem):
    """
    An item for staged/unstaged files lists.

    See Also
    --------
    __lt__ : For item comparison details.
    """
    def __init__(self, repodir: str, *args: object):
        super().__init__(*args)
        self.state: typing.Optional[int] = None
        self.repodir: str = repodir

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
        icon_spec = STATE_TO_ICON.get(state,
                                      STATE_TO_ICON[ChangedStatus.UNKNOWN])
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

    @property
    def path(self) -> typing.Optional[str]:
        """Return a path suitable for VCS backend calls."""
        text = self.text(0)
        if text:
            return text
        return None


class ChangesTree(QTreeWidget):
    """
    A tree widget for vcs changes.

    Parameters
    ----------
    manager : VCSBackendManager
        The VCS manager.
    staged : bool, optional
        If True, all the changes listed should be staged.
        If False, all the changes listed should be unstaged.
        If None, the staged field in changes is ignored.
        The default is None.
    """

    sig_stage_toggled = Signal((bool, ), (bool, str))
    """
    This signal is emitted when the one or all changes are now (un)staged.

    Parameters
    ----------
    staged : bool
        If True, a stage operation occurred,
        otherwise an unstaged operation occurred.

    path : str
        The path affected by the operation.
        If not specified, all the paths will be interested in that changes.

    See Also
    --------
    VCSBackendBase.stage
    VCSBackendBase.unstage
    """
    def __init__(self, manager: VCSBackendManager, *args,
                 staged: typing.Optional[bool], **kwargs):
        super().__init__(*args, **kwargs)
        self.manager = manager
        self.staged = staged

        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.setSortingEnabled(True)
        self.sortItems(0, Qt.AscendingOrder)

        # Slots
        self.sig_stage_toggled.connect(self.clear)
        self.customContextMenuRequested.connect(self.show_ctx_menu)

        if ((staged is True and manager.unstage.enabled)
                or (staged is False and manager.stage.enabled)):
            self.itemDoubleClicked.connect(self.toggle_stage)

    @Slot(QPoint)
    def show_ctx_menu(self, pos: QPoint) -> None:
        """Show context menu built with suppored features."""
        item = self.itemAt(pos)
        if item is not None:
            menu = QMenu(self)
            manager = self.manager

            # TODO: Add jump to file
            if self.staged is True and manager.unstage.enabled:
                action = menu.addAction(_("Unstage"))
                action.triggered.connect(partial(self.toggle_stage, item))

            elif self.staged is False and manager.stage.enabled:
                action = menu.addAction(_("Stage"))
                action.triggered.connect(partial(self.toggle_stage, item))

            if not self.staged and manager.undo_change.enabled:
                action = menu.addAction(_("Discard"))
                action.triggered.connect(partial(self.discard, item))

            menu.exec(self.mapToGlobal(pos))

    # Refreshes
    @Slot()
    @Slot(list)
    def refresh(
        self,
        changes: typing.Optional[typing.Iterator[CHANGE]] = None,
    ) -> None:
        """
        Clear and add given changes as items.

        The changes are filtered by the staged attribute
        in the following manners:

        - If staged is True, only changes that have True as staged field.
        - If staged is False, only changes that have False as staged field.
        - If staged is None, changes are not filtered.
        - When the staged field is not available and staged is a bool,
          changes are always discarded.

        Parameters
        ----------
        changes : Iterator[Dict[str, object]], optional
            The changes to show.
            If nothing is given, changes are obtained through the manager.
        """
        @Slot(object)
        def _handle_result(result):
            if isinstance(result, Iterable):
                if isinstance(self.staged, bool):
                    result = filter(lambda x: x.get("staged") is self.staged,
                                    result)
                for i, change in enumerate(result):
                    kind = change.get("kind", ChangedStatus.UNKNOWN)
                    if kind not in (ChangedStatus.UNCHANGED,
                                    ChangedStatus.IGNORED):
                        if kind not in STATE_TO_ICON:
                            kind = ChangedStatus.UNKNOWN

                        item = ChangeItem(self.manager.repodir)
                        self.addTopLevelItem(item)
                        item.setup(kind, change["path"])

                    if i % PAUSE_CYCLE == 0:
                        QCoreApplication.processEvents()

        self.clear()
        if changes:
            _handle_result(changes)
        else:
            ThreadWrapper(self,
                          lambda: self.manager.changes,
                          result_slots=(_handle_result, ),
                          error_slots=(_raise, ),
                          nothread=not THREAD_ENABLED).start()

    @Slot(str)
    def refresh_one(self, path: str):
        """
        Clear and add given changes as items.

        The changes are filtered by the staged attribute
        in the following manners:

        - If staged is True, only changes that have True as staged field.
        - If staged is False, only changes that have False as staged field.
        - If staged is None, changes are not filtered.
        - When the staged field is not available and staged is a bool,
          changes are always discarded.

        Parameters
        ----------
        path : str
            The path to refresh.
            If it does not exists and there is a change for it,
            a new item will be added.
        """
        @Slot(object)
        def _handle_result(result):
            if (isinstance(result, dict)
                    and result.get("staged", self.staged) is self.staged):

                item = ChangeItem(self.manager.repodir)
                self.addTopLevelItem(item)
                item.setup(result["kind"], result["path"])

        items = self.findItems(path,
                               Qt.MatchFixedString | Qt.MatchCaseSensitive)
        if items:
            self.invisibleRootItem().removeChild(items[0])
            path = items[0].path

        ThreadWrapper(
            self,
            partial(
                self.manager.change,
                path,
                prefer_unstaged=not self.staged,
            ),
            result_slots=(_handle_result, ),
            error_slots=(_raise, ),
            nothread=not THREAD_ENABLED,
        ).start()

    # Stage operations
    @Slot(QTreeWidgetItem)
    def toggle_stage(self, item: ChangeItem) -> None:
        """
        Toggle the item state from unstage to stage or vice versa.

        The executed operation depend on the staged attribute
        in the following manners:

        - If staged is True, the given change will be unstaged.
        - If staged is False, the given change will be staged.
        - If staged is None, an AttributeError will be raised.

        Parameters
        ----------
        item : ChangeItem
            The item representing a changed file.

        Raises
        ------
        AttributeError
            If the staged attribute is None.

        NotImplementedError
            If the required feature is not supported by the current backend.
        """
        @Slot(object)
        def _handle_result(result):
            if result:
                path = item.path
                self.invisibleRootItem().removeChild(item)
                item.setup(item.state, path)
                self.sig_stage_toggled[bool, str].emit(not self.staged, path)

        if (self.staged is True and self.manager.unstage.enabled):
            # unstage item
            operation = self.manager.unstage
        elif (self.staged is False and self.manager.stage.enabled):
            # stage item
            operation = self.manager.stage
        elif self.staged is None:
            raise AttributeError("The staged attribute is not set.")
        else:
            raise NotImplementedError(
                "The current VCS does not support {}".format(
                    "stage" if self.staged else "unstage"))

        ThreadWrapper(self,
                      partial(operation, item.path),
                      result_slots=(_handle_result, ),
                      error_slots=(_raise, ),
                      nothread=not THREAD_ENABLED).start()

    @Slot()
    def toggle_stage_all(self) -> None:
        """
        Move all the unstaged changes to the staged area or vice versa.

        The executed operation depend on the staged attribute
        in the following manners:

        - If staged is True, :meth:`~VCSBackendBase.unstage_all` is called.
        - If staged is False, :meth:`~VCSBackendBase.stage_all` is called.
        - If staged is None, an AttributeError will be raised.

        Raises
        ------
        AttributeError
            If the staged attribute is None.
        NotImplementedError
            If the required feature is not supported by the current backend.
        """
        if self.staged is None:
            raise AttributeError("The staged attribute is not set.")

        operation = (self.manager.unstage_all
                     if self.staged else self.manager.stage_all)
        if not operation.enabled:
            raise NotImplementedError(
                "The current VCS does not support {}".format(
                    operation.__name__))

        ThreadWrapper(self,
                      operation,
                      result_slots=(lambda result: result and self.
                                    sig_stage_toggled.emit(not self.staged), ),
                      error_slots=(_raise, ),
                      nothread=not THREAD_ENABLED).start()

    @Slot(QTreeWidgetItem)
    def discard(self, item: ChangeItem) -> None:
        """
        Discard an unstaged change and remove the item.

        Parameters
        ----------
        item : ChangeItem
            The change item.
        """
        if self.manager.undo_change.enabled:
            ThreadWrapper(
                self,
                partial(self.manager.undo_change, item.path),
                result_slots=(lambda res: res and self.invisibleRootItem().
                              removeChild(item), ),
                error_slots=(_raise, ),
                nothread=not THREAD_ENABLED,
            ).start()


def _raise(ex):
    raise ex

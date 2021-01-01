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
from typing import Dict, Iterator, Optional
from functools import partial
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

# Third party imports
import qtawesome as qta
from qtpy.QtCore import Qt, Slot, QPoint, Signal
from qtpy.QtWidgets import (
    QMenu,
    QLabel,
    QAction,
    QWidget,
    QHBoxLayout,
    QTreeWidget,
    QVBoxLayout,
    QTreeWidgetItem
)

# Local imports
from spyder.config.gui import is_dark_interface
from spyder.api.translations import get_translation

from .utils import action2button
from .common import BaseComponent
from ..backend.api import ChangedStatus

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

CHANGE = Dict[str, object]


class ChangeItem(QTreeWidgetItem):
    """
    An item for staged/unstaged files lists.

    See Also
    --------
    __lt__ : For item comparison details.
    """
    def __init__(self, repodir: str, *args: object):
        super().__init__(*args)
        self.state: Optional[int] = None
        self.repodir: str = repodir

    def __eq__(self, other: QTreeWidgetItem) -> bool:
        """Check equality between two items."""
        return self.state == other.state and self.text(0) == other.text(0)

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        """Compare two items, prioritizing state over path."""
        if self.state == other.state:
            # compare with paths if the states are the same
            return bool(self.text(0) < other.text(0))

        return _STATE_LIST.index(self.state) < _STATE_LIST.index(other.state)

    def __hash__(self) -> int:
        return hash(self.state) + hash(self.text(0))

    def __repr__(self) -> str:
        return "<ChangesItem ({}, {})>".format(
            ChangedStatus.to_string(self.state), self.text(0))

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

    @property
    def path(self) -> Optional[str]:
        """Return a path suitable for backend calls."""
        text = self.text(0)
        if text:
            return text
        return None


class ChangesTreeComponent(BaseComponent, QTreeWidget):
    """
    A tree widget for VCS changes.

    Parameters
    ----------
    staged : bool or None
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
    VCSBackendBase.stage_all
    VCSBackendBase.unstage
    VCSBackendBase.unstage_all
    """

    REFRESH_TIME = 1500

    def __init__(self, *args, staged: Optional[bool], **kwargs):
        super().__init__(*args, **kwargs)
        self._staged = staged

        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.setSortingEnabled(True)
        self.sortItems(0, Qt.AscendingOrder)

        # Slots
        self.customContextMenuRequested.connect(self.show_ctx_menu)
        self.sig_stage_toggled.connect(self.clear)

    @property
    def staged(self) -> bool:
        """Return staged status."""
        return self._staged

    @Slot()
    def setup(self):
        with self.block_timer():
            self.clear()

        manager = self.manager
        if not manager.safe_check(("changes", "fget")):
            self.hide()
            self.timer.stop()
            return
        self.show()

        # Slots
        try:
            self.itemDoubleClicked.disconnect(self.toggle_stage)
        except (RuntimeError, TypeError):
            pass

        if ((self._staged is True and manager.unstage.enabled)
                or (self._staged is False and manager.stage.enabled)):
            self.itemDoubleClicked.connect(self.toggle_stage)

    @Slot(QPoint)
    def show_ctx_menu(self, pos: QPoint) -> None:
        """Show context menu built with suppored features."""
        item = self.itemAt(pos)
        if item is not None:
            menu = QMenu(self)
            manager = self.manager

            # TODO: Add jump to file
            if self._staged is True and manager.unstage.enabled:
                action = menu.addAction(_("Unstage"))
                action.triggered.connect(partial(self.toggle_stage, item))

            elif self._staged is False and manager.stage.enabled:
                action = menu.addAction(_("Stage"))
                action.triggered.connect(partial(self.toggle_stage, item))

            if not self._staged and manager.undo_change.enabled:
                action = menu.addAction(_("Discard"))
                action.triggered.connect(partial(self.discard, item))

            menu.exec_(self.mapToGlobal(pos))

    # Refreshes
    @Slot()
    @Slot(list)
    def refresh(self, changes: Optional[Iterator[CHANGE]] = None) -> None:
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

                def _task(change):
                    kind = change.get("kind", ChangedStatus.UNKNOWN)
                    if kind not in (ChangedStatus.UNCHANGED,
                                    ChangedStatus.IGNORED):
                        if kind not in STATE_TO_ICON:
                            kind = ChangedStatus.UNKNOWN

                        item = ChangeItem(self.manager.repodir)
                        item.setup(kind, change["path"])
                        return item
                    return None

                if isinstance(self._staged, bool):
                    result = filter(lambda x: x.get("staged") is self._staged,
                                    result)

                # OPTIMIZE: Don't spawn ChangesItem objects
                #           if they will not be added to self.
                with ThreadPoolExecutor() as pool:
                    old_items = set(
                        pool.map(self.topLevelItem,
                                 range(self.topLevelItemCount())))
                    items = set(pool.map(_task, result))

                new_items = items - old_items
                old_items -= items
                for item in new_items:
                    if item.treeWidget() is None:
                        self.addTopLevelItem(item)

                for item in old_items:
                    if item.treeWidget() == self:
                        self.invisibleRootItem().removeChild(item)

        if changes:
            _handle_result(changes)
        else:
            self.do_call(("changes", "get"), result_slots=_handle_result)

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
            if (isinstance(result, dict)) and result.get(
                    "staged", self._staged) is self._staged:

                item = ChangeItem(self.manager.repodir)
                self.addTopLevelItem(item)
                item.setup(result["kind"], result["path"])

        items = self.findItems(path,
                               Qt.MatchFixedString | Qt.MatchCaseSensitive)
        if items:
            self.invisibleRootItem().removeChild(items[0])
            path = items[0].path

        self.do_call(
            "change",
            path,
            prefer_unstaged=not self._staged,
            result_slots=_handle_result,
        )

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
            If the required feature is not supported by the backend.
        """
        @Slot(object)
        def _handle_result(result):
            if result:
                path = item.path
                self.invisibleRootItem().removeChild(item)
                item.setup(item.state, path)
                self.sig_stage_toggled[bool, str].emit(not self._staged, path)

        if self._staged is None:
            raise AttributeError("The staged attribute is not set.")

        self.do_call(
            "unstage" if self._staged else "stage",
            item.path,
            result_slots=_handle_result,
        )

    @Slot()
    def toggle_stage_all(self) -> None:
        """
        Move all the unstaged changes to the staged area or vice versa.

        The executed operation depend on the staged attribute
        in the following manners:

        - If staged is True, :meth:`~VCSBackendBase.unstage_all` is called.
        - If staged is False, :meth:`~VCSBackendBase.stage_all` is called.
        - If staged is None, AttributeError is raised.

        Raises
        ------
        AttributeError
            If the staged attribute is None.
        NotImplementedError
            If the required feature is not supported by the backend.
        """
        if self._staged is None:
            raise AttributeError("The staged attribute is not set.")

        self.do_call(
            "unstage_all" if self._staged else "stage_all",
            result_slots=lambda res: res and self.sig_stage_toggled.emit(
                not self._staged),
        )

    @Slot(QTreeWidgetItem)
    def discard(self, item: ChangeItem) -> None:
        """
        Discard an unstaged change and remove the item.

        Parameters
        ----------
        item : ChangeItem
            The change item.
        """
        self.do_call(
            "undo_change",
            item.path,
            result_slots=lambda res: res and self.invisibleRootItem().
            removeChild(item),
        )


class ChangesComponent(BaseComponent, QWidget):
    """
    A widget for VCS changes management.

    Parameters
    ----------
    staged : bool or None
        If True, all the changes listed should be staged.
        If False, all the changes listed should be unstaged.
        If None, the staged field in changes is ignored.
        The default is None.

    stage_all_action : QAction or None
        The action to use for creating the stage all/unstage all button.
        Must be given if staged is not None.

    Raises
    ------
    TypeError
        If staged is not None and stage_all_action is None.
    """
    def __init__(self,
                 *args,
                 staged: Optional[bool],
                 stage_all_action: QAction = None,
                 **kwargs):
        super().__init__(*args, **kwargs)

        # Widgets
        self.title = QLabel()
        if staged is None:
            self.stage_all_button = QWidget()
        elif stage_all_action is None:
            raise TypeError(
                "The stage_all_action parameter must be specified.")
        else:
            self.stage_all_button = action2button(
                stage_all_action,
                parent=self,
                text_beside_icon=True,
            )

        self.changes_tree = ChangesTreeComponent(
            self.manager,
            staged=staged,
            parent=self,
        )

        # Widgets setup
        font = self.title.font()
        font.setPointSize(11)
        font.setBold(True)
        self.title.setFont(font)

        if staged is True:
            self.title.setText(_("Staged changes"))
        elif staged is False:
            self.title.setText(_("Unstaged changes"))
        else:
            self.title.setText(_("Changes"))

        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        header_layout = QHBoxLayout()

        header_layout.addWidget(self.title)
        header_layout.addStretch(1)
        header_layout.addWidget(self.stage_all_button)

        layout.addLayout(header_layout)
        layout.addWidget(self.changes_tree)

        # Slot
        self.changes_tree.sig_vcs_error.connect(self.sig_vcs_error)
        if stage_all_action is not None:
            stage_all_action.triggered.connect(
                self.changes_tree.toggle_stage_all)

    @Slot()
    def setup(self) -> None:
        manager = self.manager
        staged = self.changes_tree.staged

        self.changes_tree.setup()
        if manager.repodir is not None and self.changes_tree.isEnabled():
            if staged is True:
                self.stage_all_button.setVisible(manager.unstage_all.enabled)
            elif staged is False:
                self.stage_all_button.setVisible(manager.stage_all.enabled)

            states = manager.type.changes.fget.extra.get("states", ())
            self.setVisible(("staged" in states) ^ (staged is None))
        else:
            self.hide()

    @Slot()
    def refresh(self) -> None:
        with self.changes_tree.block_timer():
            self.changes_tree.refresh()

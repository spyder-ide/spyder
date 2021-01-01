#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Widgets for the history area."""

# Standard library imports
from datetime import datetime, timezone
from functools import partial

# Third party imports
from qtpy.QtCore import Slot, Signal, QCoreApplication
from qtpy.QtWidgets import (
    QHeaderView,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem
)

# Local imports
from spyder.utils import icon_manager as ima
from spyder.api.translations import get_translation

from .utils import PAUSE_CYCLE
from .common import BaseComponent

_ = get_translation('spyder')

# TODO: move this to configs
MAX_HISTORY_ROWS = 8


class CommitHistoryComponent(BaseComponent, QTreeWidget):
    """A tree widget for commit history."""

    sig_last_commit = Signal(dict)
    """
    This signal is emitted when the last commit changed.

    Parameters
    ----------
    commit : dict
        The dict returned by :meth:`~VCSBackendBase.undo_commit`.
    """
    REFRESH_TIME = 5000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setColumnCount(3)

        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self._old_commits = None

    @Slot()
    def setup(self):
        with self.block_timer():
            self._old_commits = None
            self.clear()

        self.setVisible(bool(self.manager.safe_check("get_last_commits")))

    @Slot()
    def refresh(self) -> None:
        def _handle_result(result):
            if result is None:
                if self._old_commits is not None:
                    self.clear()

            elif result != self._old_commits:
                self.clear()
                undo_enabled = bool(self.manager.undo_commit.enabled)
                for i, commit in enumerate(result):

                    item = QTreeWidgetItem()
                    # Keep the commit attributes in the item.
                    item.commit = commit

                    # Set commit title
                    if commit.get("title"):
                        title = commit["title"]
                    elif commit.get("description"):
                        title = commit["description"].lstrip().splitlines()[0]
                    else:
                        title = None

                    # TODO: Tell the user that the title is missing
                    #       (e.g. with an icon)
                    item.setText(1, title.strip() if title else "")
                    item.setToolTip(1, item.text(1))

                    # Set commit date
                    if commit.get("commit_date") is not None:
                        # TODO: update times
                        delta = (datetime.now(tz=timezone.utc) -
                                 commit["commit_date"])
                        # FIXME: Suffixes should be translated
                        if delta.days:
                            item.setText(2, "{}d".format(abs(delta.days)))
                        elif delta.seconds >= 3600:
                            item.setText(
                                2, "{}h".format(int(delta.seconds / 3600)))
                        elif delta.seconds >= 60:
                            item.setText(
                                2,
                                "{}m".format(int(delta.seconds / 60)),
                            )
                        else:
                            item.setText(2, "<1m")

                    else:
                        # TODO: Use an icon
                        item.setText(2, "?")

                    self.addTopLevelItem(item)
                    if undo_enabled:
                        button = QToolButton()
                        button.setIcon(ima.icon("undo"))
                        button.setToolTip(_("Undo commit"))
                        button.clicked.connect(
                            partial(
                                self.undo_commits,
                                i + 1,
                            ))
                        self.setItemWidget(item, 0, button)

                    # Reduce lag when inserting commits.
                    if not i % PAUSE_CYCLE:
                        QCoreApplication.processEvents()

            self._old_commits = result

        self.do_call(
            "get_last_commits",
            MAX_HISTORY_ROWS,
            result_slots=_handle_result,
        )

    @Slot()
    @Slot(int)
    def undo_commits(self, commits: int = 1) -> None:
        """
        Undo commits.

        Parameters
        ----------
        commits : int, optional
            The number of commits to undo. The default is 1.
        """
        self.do_call(
            "undo_commit",
            commits,
            result_slots=(lambda commit: self.sig_last_commit.emit(commit)
                          if commit else None, self.refresh),
        )

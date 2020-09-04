#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""VCS widgets."""

# pylint: disable = W0201

# Standard library imports
from collections.abc import Sequence
from datetime import datetime, timezone
import functools
import typing

# Third party imports
from qtpy.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
                            QTreeWidgetItem, QPlainTextEdit, QSizePolicy,
                            QMessageBox, QLayout, QToolButton, QHeaderView)

from qtpy.QtGui import QIcon
from qtpy.QtCore import Signal, Slot, Qt, QCoreApplication

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainWidget
import spyder.utils.icon_manager as ima
from spyder.utils.qthelpers import action2button

from .common import (STATE_TO_TEXT, ChangesItem, BranchesComboBox, LoginDialog,
                     ThreadWrapper, THREAD_ENABLED)
from ..utils.errors import VCSAuthError
from ..utils.api import ChangedStatus

_ = get_translation('spyder')

# TODO: move this to configs
MAX_HISTORY_ROWS = 10


class VCSWidget(PluginMainWidget):
    """VCS main widget."""

    DEFAULT_OPTIONS = {}

    sig_auth_operation = Signal((str, ), (str, tuple, dict))
    """
    This signal is emitted when an auth operation is requested

    It is intended to be used only internally. Use plugin's actions instead.
    """

    sig_auth_operation_success = Signal(str, object)
    """
    This signal is emitted when an auth operation was done successfully.

    It is intended to be used only internally and can corrupt the widget's UI.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()
        # For debugging purposes
        layout.setObjectName("vcs_widget_layout")
        self.setLayout(layout)

        # define all the widget variables
        self.branch_combobox = self.unstaged_files = self.staged_files = None
        self.commit_message = self.history = None

    # Reimplemented APIs

    def get_title(self):
        return self.get_plugin().get_name()

    def update_actions(self):
        # Exposed actions are located in the plugin
        pass

    def on_option_update(self, option, value):
        pass

    @Slot()
    def setup(self, options=DEFAULT_OPTIONS) -> None:
        """Set up the GUI for the current repository."""
        # get the required stuffs
        plugin = self.get_plugin()
        manager = plugin.vcs_manager

        # remove the old layout
        clear_layout(self.layout())

        # unset all the widgets
        self.branch_combobox = self.unstaged_files = self.staged_files = None
        self.commit_message = self.history = None

        if plugin.get_repository():
            rootlayout = self.layout()

            # --- Toolbar ---
            toolbar = QHBoxLayout()

            self.branch_combobox = BranchesComboBox(plugin.vcs_manager, None)
            self.branch_combobox.setEnabled(manager.type.branch.fset.enabled)
            self.branch_combobox.setSizePolicy(
                QSizePolicy(
                    QSizePolicy.Expanding,
                    QSizePolicy.Preferred,
                ))
            toolbar.addWidget(self.branch_combobox)

            toolbar.addStretch(0)
            toolbar.addWidget(action2button(plugin.refresh_action,
                                            parent=self))
            # toolbar.addWidget(plugin.options_button)

            rootlayout.addLayout(toolbar)

            # --- Changes ---
            if manager.type.changes.fget.enabled:
                is_stage_supported = (manager.stage.enabled
                                      and manager.unstage.enabled)

                # header
                header_layout = QHBoxLayout()
                header_layout.addWidget(
                    QLabel("<h3>Unstaged changes</h3>")
                    if is_stage_supported else QLabel("<h3>Changes</h3>"))

                header_layout.addStretch(1)
                rootlayout.addLayout(header_layout)

                # --- Untaged changes (or simply changes) ---
                self.unstaged_files = QTreeWidget()
                _prepare_changes_widget(self.unstaged_files)

                rootlayout.addWidget(self.unstaged_files)

                if is_stage_supported:
                    if manager.stage_all.enabled:
                        header_layout.addWidget(
                            action2button(
                                plugin.stage_all_action,
                                parent=self,
                                text_beside_icon=True,
                            ))

                    # --- Staged changes ---

                    # header
                    header_layout = QHBoxLayout()
                    header_layout.addWidget(QLabel("<h3>Staged changes</h3>"))
                    header_layout.addStretch(1)

                    if manager.unstage_all.enabled:
                        header_layout.addWidget(
                            action2button(
                                plugin.unstage_all_action,
                                parent=self,
                                text_beside_icon=True,
                            ))

                    rootlayout.addLayout(header_layout)

                    self.staged_files = QTreeWidget()
                    _prepare_changes_widget(self.staged_files)

                    rootlayout.addWidget(self.staged_files)

            # --- Commit ---
            if manager.commit.enabled:
                # commit message
                self.commit_message = QPlainTextEdit()
                self.commit_message.setPlaceholderText(_("Commit message ..."))
                rootlayout.addWidget(self.commit_message)

                # commit button
                commit_button = action2button(plugin.commit_action,
                                              parent=self)
                commit_button.setIcon(QIcon())
                commit_button.setText(_("Commit changes"))

                commit_button.setSizePolicy(
                    QSizePolicy(
                        QSizePolicy.Preferred,
                        QSizePolicy.Fixed,
                    ))

                # FIXME: change color if dark or white
                commit_button.setStyleSheet("background-color: #1122cc;")
                rootlayout.addWidget(commit_button)

            # intermediary step
            QCoreApplication.processEvents()

            # --- History ---
            rootlayout.addStretch(0)
            if manager.get_last_commits.enabled:

                self.history = QTreeWidget()
                self.history.setHeaderHidden(True)
                self.history.setRootIsDecorated(False)
                self.history.setColumnCount(3)
                self.history.header().setStretchLastSection(False)
                self.history.header().setSectionResizeMode(
                    QHeaderView.ResizeToContents)
                self.history.header().setSectionResizeMode(
                    1, QHeaderView.Stretch)
                rootlayout.addWidget(self.history)

            # --- Commands ---
            commandslayout = QHBoxLayout()
            if manager.fetch.enabled:
                commandslayout.addWidget(
                    action2button(plugin.fetch_action,
                                  text_beside_icon=True,
                                  parent=self))
            if manager.pull.enabled:
                commandslayout.addWidget(
                    action2button(plugin.pull_action,
                                  text_beside_icon=True,
                                  parent=self))

            if manager.push.enabled:
                commandslayout.addWidget(
                    action2button(plugin.push_action,
                                  text_beside_icon=True,
                                  parent=self))

            rootlayout.addLayout(commandslayout)

            # --- Slots ---
            if (getattr(self, "branch_combobox", None) is not None
                    and manager.type.branch.fset.enabled):
                self.branch_combobox.currentIndexChanged.connect(
                    self.branch_combobox.select)

                self.branch_combobox.sig_branch_changed.connect(
                    self.refresh_changes)

                self.branch_combobox.sig_branch_changed.connect(
                    plugin.sig_branch_changed)

            if getattr(self, "staged_files", None) is not None:
                # unstaged are supposed to be already here
                self.staged_files.itemDoubleClicked.connect(self.toggle_stage)
                self.unstaged_files.itemDoubleClicked.connect(
                    self.toggle_stage)

            # Show the whole UI before refreshes
            QCoreApplication.processEvents()

        else:
            # TODO: show "no repository available"
            #       when repository is missing,
            #       including buttons for create
            #       a new one or clone it.
            pass

    # Public methods
    def setup_slots(self) -> None:
        """Connect all the common slots, including the plugins actions."""
        plugin = self.get_plugin()

        # Plugin signals
        plugin.sig_repository_changed.connect(self.setup)
        plugin.sig_repository_changed.connect(self.refresh_all)

        # Plugin actions
        plugin.stage_all_action.triggered.connect(self.toggle_stage_all)
        plugin.unstage_all_action.triggered.connect(
            functools.partial(self.toggle_stage_all, True))

        plugin.commit_action.triggered.connect(self.commit)
        plugin.fetch_action.triggered.connect(
            functools.partial(
                self.sig_auth_operation[str, tuple, dict].emit,
                "fetch",
                (),
                dict(sync=True),
            ))
        plugin.pull_action.triggered.connect(
            functools.partial(self.sig_auth_operation.emit, "pull"))
        plugin.push_action.triggered.connect(
            functools.partial(self.sig_auth_operation.emit, "push"))

        plugin.refresh_action.triggered.connect(self.refresh_all)

        # Auth actions
        self.sig_auth_operation.connect(self.auth_operation)
        self.sig_auth_operation[str, tuple, dict].connect(self.auth_operation)

        # Post auth slots
        self.sig_auth_operation_success.connect(self.post_commit)
        self.sig_auth_operation_success.connect(
            Slot(str)(lambda operation: (
                self.refresh_changes(),
                self.refresh_history(),
            ) if operation == "pull" else None))

    # refreshes slots
    @Slot()
    @Slot(bool)
    def refresh_changes(self) -> None:
        """Clear and re-add items in unstaged and staged changes."""
        @Slot(object)
        def _handle_result(result):
            if isinstance(result, Sequence):
                # Prevent sorting when inserting items
                unstaged = self.unstaged_files
                unstaged.clear()
                unstaged.setSortingEnabled(False)

                is_staged_enabled = (manager.stage.enabled
                                     and manager.unstage.enabled)
                if is_staged_enabled:
                    staged = self.staged_files
                    staged.clear()
                    staged.setSortingEnabled(False)

                # Iterate over result
                for state_spec in result:
                    state = state_spec.get("kind", ChangedStatus.UNKNOWN)
                    if state not in (ChangedStatus.UNCHANGED,
                                     ChangedStatus.IGNORED):
                        if state not in STATE_TO_TEXT:
                            state = ChangedStatus.UNKNOWN

                        item = ChangesItem()
                        if is_staged_enabled and state_spec.get("staged"):
                            staged.addTopLevelItem(item)
                        else:
                            unstaged.addTopLevelItem(item)
                        item.setup(state, state_spec["path"])

                # Restore sorting
                unstaged.setSortingEnabled(True)
                if is_staged_enabled:
                    staged.setSortingEnabled(True)

                QCoreApplication.processEvents()

        manager = self.get_plugin().vcs_manager

        if manager.type.changes.fget.enabled:
            if THREAD_ENABLED:
                ThreadWrapper(
                    self,
                    lambda: manager.changes,
                    result_slots=(_handle_result, ),
                    error_slots=(_raise_if, ),
                ).start()
            else:
                _handle_result(manager.changes)

    @Slot()
    @Slot(tuple)
    def refresh_commit_difference(
        self,
        commit_difference: typing.Optional[typing.Tuple[int, int]] = None,
    ) -> None:
        """
        Show the numbers of commits to pull and push compared to the remote.

        Parameters
        ----------
        commit_difference : tuple of int, optional
            A tuple of 2 integers.
            The first one is the amount of commit to pull,
            the second one is the amount of commit to push.
            Can be None, that allows this method to call the backend
            to :meth:`~VCSBackendBase.fetch` the repository.
            The default is None.
        """

        # FIXME: This method definitely needs a better name
        #        commit difference is ugly and probably wrong.
        def _handle_result(differences):
            # pull
            if differences:
                for difference, action in zip(
                        differences, (plugin.pull_action, plugin.push_action)):

                    label = action.text().rsplit(" ", 1)
                    if len(label) == 2 and label[1][0] + label[1][-1] == "()":
                        # found existing number
                        del label[1]
                    if difference > 0:
                        action.setText(" ".join(label) +
                                       " ({})".format(difference))
                    else:
                        action.setText(" ".join(label))
            else:
                plugin.pull_action.setText(_("pull"))
                plugin.push_action.setText(_("push"))

        plugin = self.get_plugin()
        if commit_difference is None:
            if THREAD_ENABLED:
                ThreadWrapper(
                    self,
                    plugin.vcs_manager.fetch,  # pylint:disable=W0108
                    result_slots=(_handle_result, ),
                    error_slots=(_raise_if, ),
                ).start()
            else:
                _handle_result(plugin.vcs_manager.fetch())
        else:
            _handle_result(plugin.vcs_manager.fetch())

    @Slot()
    def refresh_history(self) -> None:
        """Populate history widget with old commits."""
        def _handle_result(result):
            if result:
                undo_enabled = bool(manager.undo_commit.enabled)
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

                    # TODO: Tell the user that there is no title
                    #       (e.g. with an icon)
                    item.setText(1, title.strip() if title else "")

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

                    self.history.addTopLevelItem(item)
                    if undo_enabled:
                        button = QToolButton()
                        button.setIcon(ima.icon("undo"))
                        button.clicked.connect(
                            functools.partial(self.undo_commit, i + 1))
                        self.history.setItemWidget(item, 0, button)

        manager = self.get_plugin().vcs_manager
        if manager.get_last_commits.enabled:
            self.history.clear()
            if THREAD_ENABLED:
                ThreadWrapper(
                    self,
                    functools.partial(manager.get_last_commits,
                                      MAX_HISTORY_ROWS),
                    result_slots=(_handle_result, ),
                    error_slots=(_raise_if, ),
                ).start()
            else:
                _handle_result(manager.get_last_commits(MAX_HISTORY_ROWS))

    @Slot()
    @Slot(str)
    def refresh_all(self, path: str = ...) -> None:
        """
        Populate widgets with backend data.

        Parameters
        ----------
        path : str, optional
            The repository path.
            The default is ..., which means the path is unchanged.
        """
        # ... is used when this slot invoked by plugin.refresh_action
        if path:
            self.refresh_changes()
            if getattr(self, "branch_combobox", None) is not None:
                self.branch_combobox.refresh()
            self.refresh_commit_difference()
            # self.refresh_commit()
            self.refresh_history()

    # VCS edit slots
    @Slot(str)
    def select_branch(self, branchname: str) -> None:
        """
        Select a branch given its name.

        Parameters
        ----------
        branchname : str, optional
            The branch name.

        Raises
        ------
        AttributeError
            If changing branch is not supported.
        """
        if (getattr(self, "branch_combobox", None) is None
                or not self.branch_combobox.isEnabled()):
            raise AttributeError("Cannot change branch in the current VCS")
        self.branch_combobox.select(branchname)

    @Slot(QTreeWidgetItem)
    def toggle_stage(self, item: ChangesItem) -> None:
        """
        Toggle the item state from unstage to stage and vice versa.

        Parameters
        ----------
        item : ChangesItem
            The item representing a changed file.
        """
        @Slot(object)
        def _handle_result(result):
            if result:
                oldtreewidget.invisibleRootItem().removeChild(item)
                newtreewidget.addTopLevelItem(item)
                item.setup(item.state, item.text(0))

        oldtreewidget = item.treeWidget()
        newtreewidget = None
        operation = None
        manager = self.get_plugin().vcs_manager
        if (manager.stage.enabled and manager.unstage.enabled):
            if oldtreewidget == self.unstaged_files:
                # stage item
                newtreewidget = self.staged_files
                operation = manager.stage

            elif oldtreewidget == self.staged_files:
                # unstage item
                newtreewidget = self.unstaged_files
                operation = manager.unstage

            if THREAD_ENABLED:
                ThreadWrapper(
                    self,
                    functools.partial(operation, item.text(0)),
                    result_slots=(_handle_result, ),
                    error_slots=(_raise_if, ),
                ).start()

            else:
                _handle_result(operation(item.text(0)))

    @Slot()
    def toggle_stage_all(self, unstage: bool = False) -> None:
        """
        Move all the unstaged changes to the staged area or vice versa.

        Parameters
        ----------
        unstage : bool
            If True, staged changes are moved in the unstaged area.
            The defaults is False, which does the opposite.
        """
        @Slot(object)
        def _handle_result(result):
            if result:
                self.refresh_changes()

        manager = self.get_plugin().vcs_manager
        operation = manager.unstage_all if unstage else manager.stage_all
        if THREAD_ENABLED:
            ThreadWrapper(
                self,
                operation,
                result_slots=(_handle_result, ),
                error_slots=(_raise_if, ),
            ).start()
        else:
            _handle_result(operation())

    @Slot()
    def commit(self) -> None:
        """
        Commit all the changes in the VCS.

        If the VCS has a staging area,
        only the staged file will be committed.
        """
        text = self.commit_message.toPlainText()

        if self.staged_files is not None:
            changes_to_commit = self.staged_files
        elif self.unstaged_files is not None:
            changes_to_commit = self.unstaged_files
        else:
            changes_to_commit = None

        if (text and (changes_to_commit is None
                      or changes_to_commit.invisibleRootItem().childCount())):
            self.sig_auth_operation[str, tuple, dict].emit(
                "commit",
                (text, ),
                dict(is_path=False),
            )

    @Slot(str)
    def post_commit(self, operation: str) -> None:
        """Update the UI after commit operation."""
        if operation == "commit":
            manager = self.get_plugin().vcs_manager

            # FIXME: Preserve undo history of commit textedit
            self.commit_message.clear()
            self.refresh_history()

            if manager.type.changes.fget.enabled:
                if (manager.stage.enabled and manager.unstage.enabled):
                    self.staged_files.clear()
                else:
                    self.unstaged_files.clear()

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

        manager = self.get_plugin().vcs_manager
        func = getattr(manager, operation, None)
        if func is not None and func.enabled:
            func = functools.partial(func, *args, **kwargs)
            if THREAD_ENABLED:
                ThreadWrapper(
                    self,
                    func,
                    result_slots=(_handle_result,
                                  self.refresh_commit_difference),
                    error_slots=(
                        lambda ex: _raise_if(ex, VCSAuthError, True) or self.
                        handle_auth_error(ex, operation, args, kwargs), ),
                ).start()
            else:
                try:
                    result = func()
                except VCSAuthError as ex:
                    self.handle_auth_error(ex, operation, args, kwargs)
                else:
                    _handle_result(result)

    def handle_auth_error(  # pylint: disable=W0102
            self,
            ex: VCSAuthError,
            operation: str,
            args: tuple = (),
            kwargs: dict = {}  # pylint: disable=W0102
    ) -> None:
        """Handle authentication errors by showing an input dialog."""
        def _accepted():
            manager.credentials = dialog.to_credentials()
            self.sig_auth_operation[str, tuple, dict].emit(
                operation,
                args,
                kwargs,
            )

        def _rejected():
            QMessageBox.critical(
                self,
                _("Authentication failed"),
                _("Failed to authenticate to the {} remote server.".format(
                    manager.VCSNAME)),
            )

        manager = self.get_plugin().vcs_manager
        required_credentials = manager.REQUIRED_CREDENTIALS
        credentials = manager.credentials
        credentials = {
            # prefer error credentials over the backend ones
            key: getattr(ex, key, None) or credentials.get(key)
            for key in required_credentials
        }

        if credentials:
            dialog = LoginDialog(self, **credentials)
            dialog.accepted.connect(_accepted)
            dialog.rejected.connect(_rejected)
            dialog.show()

    @Slot()
    @Slot(int)
    def undo_commit(self, commits: int = 1) -> None:
        """
        Undo commit and refresh the UI.

        Parameters
        ----------
        commits : int, optional
            DESCRIPTION. The default is 1.
        """
        @Slot()
        @Slot(dict)
        def _refresh_commit_message(commit=None):
            if commit:
                text = (commit.get("content") or commit.get("description")
                        or commit.get("title", ""))
                self.commit_message.setPlainText(text)

        manager = self.get_plugin().vcs_manager
        if manager.undo_commit.enabled:
            slots = [
                self.refresh_changes,
                self.refresh_commit_difference,
                self.refresh_history,
            ]
            if THREAD_ENABLED:
                slots.append(_refresh_commit_message)
                ThreadWrapper(
                    self,
                    functools.partial(manager.undo_commit, commits),
                    result_slots=slots,
                    error_slots=(_raise_if, ),
                ).start()
            else:
                commit = manager.undo_commit(commits)
                for slot in slots:
                    slot()
                _refresh_commit_message(commit)


@Slot(Exception)
@Slot(Exception, type)
@Slot(Exception, type, bool)
def _raise_if(ex: Exception,
              required_type: type = Exception,
              inverse: bool = False):
    condition = isinstance(ex, required_type) ^ inverse
    if condition:
        raise ex


def _prepare_changes_widget(treewid: QTreeWidget) -> QTreeWidget:
    treewid.setHeaderHidden(True)
    treewid.setRootIsDecorated(False)

    treewid.setSortingEnabled(True)
    treewid.sortItems(0, Qt.AscendingOrder)

    return treewid


def clear_layout(layout: QLayout) -> None:
    """
    Clear the given layout from all the widgets and layouts.

    From https://stackoverflow.com/a/9383780/
    """
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                clear_layout(item.layout())

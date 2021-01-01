#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""VCS main widget."""

# pylint: disable = W0201

# Standard library imports
from typing import Optional
from functools import partial

# Third party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QLabel,
    QAction,
    QWidget,
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout
)

# Local imports
from spyder.api.plugins import Plugins
from spyder.api.widgets import PluginMainWidget
from spyder.api.translations import get_translation

from .auth import CreateDialog, CommitComponent, RemoteComponent
from .utils import action2button
from .branch import BranchesComponent
from .common import BaseComponent
from .changes import ChangesComponent
from .history import CommitHistoryComponent
from ..backend.errors import VCSBackendFail

_ = get_translation('spyder')


class VCSWidget(PluginMainWidget):
    """VCS main widget."""

    DEFAULT_OPTIONS = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = []

        self.branch_list = None
        self.changes = self.unstaged_changes = self.staged_changes = None
        self.commit = self.history = self.remote = None

        self.setLayout(QVBoxLayout())

    # Overriden methods
    def get_title(self):
        return self.get_plugin().get_name()

    def update_actions(self):
        # Exposed actions are located in the plugin
        pass

    def on_option_update(self, option, value):
        pass

    # Setups
    def setup(self, options=DEFAULT_OPTIONS) -> None:
        """Initialize components and slots."""
        plugin = self.get_plugin()
        manager = plugin.vcs_manager

        # HACK: Should be called in the plugin and not here.
        plugin.create_actions()

        # Widgets
        toolbar = QHBoxLayout()
        self.branch_list = BranchesComponent(manager, parent=self)
        self.branch_list.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))

        refresh_button = action2button(plugin.refresh_action, parent=self)

        self.changes = ChangesComponent(
            manager,
            staged=None,
            parent=self,
        )
        self.unstaged_changes = ChangesComponent(
            manager,
            staged=False,
            stage_all_action=plugin.stage_all_action,
            parent=self,
        )
        self.staged_changes = ChangesComponent(
            manager,
            staged=True,
            stage_all_action=plugin.unstage_all_action,
            parent=self,
        )

        self.commit = CommitComponent(
            manager,
            commit_action=plugin.commit_action,
            parent=self,
        )

        self.history = CommitHistoryComponent(manager, parent=self)

        self.remote = RemoteComponent(
            manager,
            fetch_action=plugin.fetch_action,
            pull_action=plugin.pull_action,
            push_action=plugin.push_action,
            parent=self,
        )
        self.repo_not_found = RepoNotFoundComponent(
            manager,
            create_vcs_action=plugin.create_vcs_action,
            parent=self,
        )

        # Layout
        rootlayout = self.layout()

        self.components.append(self.branch_list)

        rootlayout.addWidget(self.changes)
        rootlayout.addWidget(self.unstaged_changes)
        rootlayout.addWidget(self.staged_changes)
        self.components.extend((
            self.changes,
            self.unstaged_changes,
            self.staged_changes,
        ))

        rootlayout.addWidget(self.commit)
        self.components.append(self.commit)

        rootlayout.addWidget(self.history)
        self.components.append(self.history)

        rootlayout.addWidget(self.remote)
        self.components.append(self.remote)

        # TIP: Don't add repo_not_found to components list

        rootlayout.addWidget(
            self.repo_not_found,
            # Allows the widget to be expanded
            100,
        )

        rootlayout.addStretch(1)

        # Slots
        self.branch_list.sig_branch_changed.connect(self.refresh_all)
        self.branch_list.sig_branch_changed.connect(plugin.sig_branch_changed)

        self.unstaged_changes.changes_tree.sig_stage_toggled.connect(
            self._post_stage)
        self.unstaged_changes.changes_tree.sig_stage_toggled[
            bool, str].connect(self._post_stage)

        self.staged_changes.changes_tree.sig_stage_toggled.connect(
            self._post_stage)
        self.staged_changes.changes_tree.sig_stage_toggled[bool, str].connect(
            self._post_stage)

        self.commit.sig_auth_operation_success.connect(self.history.refresh)
        self.commit.sig_auth_operation_success.connect(self.remote.refresh)

        self.history.sig_last_commit.connect(self._post_undo)
        self.history.sig_last_commit.connect(self.remote.refresh)

        self.repo_not_found.create_dialog.sig_repository_ready.connect(
            plugin.set_repository)

        plugin.sig_repository_changed.connect(self.setup_repo)
        plugin.refresh_action.triggered.connect(self.refresh_all)

        # Toolbar
        toolbar = self.get_main_toolbar()
        toolbar.addWidget(self.branch_list)
        self.add_item_to_toolbar(
            refresh_button,
            toolbar=toolbar,
            section="main_section",
        )

        # Extra setup
        self.repo_not_found.hide()
        for component in self.components:
            component.hide()
            component.sig_vcs_error.connect(self.handle_error)

    @Slot()
    def setup_repo(self):
        """Set up the GUI for the current repository."""
        plugin = self.get_plugin()

        # Components setup
        for component in self.components:
            component.setup()

        if plugin.get_repository() is None:
            if getattr(plugin, "create_vcs_action", None) is not None:
                project_path = plugin.get_plugin(
                    Plugins.Projects).get_active_project_path()

                # Show No repository available only if there is an active project
                if project_path:
                    self.repo_not_found.setup(project_path)
                    self.repo_not_found.show()
                    return
            self.repo_not_found.hide()
        else:
            self.refresh_all()
            self.repo_not_found.hide()

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
        # ... is used when this slot is invoked by the refresh button
        if path:
            for component in self.components:
                component.refresh()

    @Slot(Exception)
    def handle_error(self, ex: Exception) -> None:
        """
        A centralized method where exceptions are handled.

        Parameters
        ----------
        ex : Exception
            The exception to handle.
        """
        if isinstance(ex, VCSBackendFail):
            plugin = self.get_plugin()
            if not ex.is_valid_repository:
                if not plugin.get_repository():
                    # Suppress errors raised by other operations
                    # in the backend (running in another threads)
                    return

                # Set broken repository to refresh the pane
                # and show "No repository found"
                plugin.set_repository(ex.directory)

                if not plugin.get_repository():
                    # Prevent show the error if the backend is buggy and
                    # the repository is not really broken
                    QMessageBox.critical(
                        self, _("Broken repository"),
                        _("The repository is broken and cannot be used anymore."
                          ))
                    return

        # TODO: use issue reporter
        raise ex

    # Private slots
    @Slot(bool)
    @Slot(bool, str)
    def _post_stage(self, staged: bool, path: Optional[str] = None) -> None:
        """
        Refresh changes after a successful stage/unstage operation.

        See Also
        --------
        ChangesTreeComponent.sig_stage_toggled
            For a description of parameters.
        """
        if staged:
            treewid = self.staged_changes
        else:
            treewid = self.unstaged_changes

        if treewid is not None:
            if path is None:
                treewid.changes_tree.refresh()
            else:
                treewid.changes_tree.refresh_one(path)

    @Slot(dict)
    def _post_undo(self, commit: dict) -> None:
        """Update commit message."""
        if not self.commit.commit_message.toPlainText():
            text = (commit.get("content") or commit.get("description")
                    or commit.get("title", ""))
            self.commit.commit_message.setPlainText(text)


class RepoNotFoundComponent(BaseComponent, QWidget):
    """A widget to show when no repository is found."""
    def __init__(self, *args, create_vcs_action: QAction, **kwargs):
        super().__init__(*args, **kwargs)

        self.project_path = None

        self.no_repo_found_label = QLabel(parent=self)
        self.create_button = action2button(
            create_vcs_action,
            text_beside_icon=True,
            parent=self,
        )
        self.create_dialog = CreateDialog(self.manager, parent=self)

        self.no_repo_found_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.create_button.setStyleSheet("background-color: #1122cc;")
        self.create_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred))

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        layout.addWidget(self.no_repo_found_label)
        layout.addWidget(self.create_button)

        # Slots
        self.create_button.triggered.connect(self.show_create_dialog)
        self.create_dialog.rejected.connect(
            partial(self.create_button.setEnabled, True))

    def setup(self, project_path: str):
        self.no_repo_found_label.setText(
            _("<h3>No repository available</h3>\nin ") + str(project_path))

        self.create_dialog.setup(project_path)
        self.create_button.setEnabled(bool(self.manager.create_vcs_types))

    @Slot()
    def show_create_dialog(self) -> None:
        """Show a :class:`~CreateDialog` for creating a repository."""
        self.create_button.setEnabled(False)
        self.create_dialog.show()

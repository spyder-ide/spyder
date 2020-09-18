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
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
import os
import os.path as osp
import shutil
from tempfile import TemporaryDirectory
import typing

# Third party imports
from qtpy.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
                            QTreeWidgetItem, QPlainTextEdit, QSizePolicy,
                            QMessageBox, QLayout, QToolButton, QHeaderView,
                            QDialog, QFormLayout, QComboBox, QDialogButtonBox,
                            QLineEdit)

from qtpy.QtGui import QIcon
from qtpy.QtCore import Signal, Slot, QCoreApplication

# Local imports
from spyder.api.plugins import Plugins
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainWidget
import spyder.utils.icon_manager as ima
from spyder.utils.qthelpers import action2button
from spyder.widgets.comboboxes import UrlComboBox

from .common import (BranchesComboBox, LoginDialog, ThreadWrapper,
                     THREAD_ENABLED, PAUSE_CYCLE)
from .changes import ChangesTree
from ..utils.api import VCSBackendManager
from ..utils.errors import VCSAuthError, VCSUnexpectedError

_ = get_translation('spyder')

# TODO: move this to configs
MAX_HISTORY_ROWS = 10


class VCSWidget(PluginMainWidget):
    """VCS main widget."""

    DEFAULT_OPTIONS = {}

    sig_auth_operation = Signal((str, ), (str, tuple, dict))
    """
    This signal is emitted when an auth operation is requested.

    It is intended to be used only internally. Use plugin's actions instead.
    """

    sig_auth_operation_success = Signal(str, object)
    """
    This signal is emitted when an auth operation was done successfully.

    It is intended to be used only internally and can corrupt widget's UI.
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

        rootlayout = self.layout()
        if plugin.get_repository():

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
            changes_feature = manager.type.changes.fget
            if changes_feature.enabled:
                is_stage_supported = ("staged"
                                      in changes_feature.extra["states"])

                # header
                header_layout = QHBoxLayout()
                header_layout.addWidget(
                    QLabel("<h3>Unstaged changes</h3>")
                    if is_stage_supported else QLabel("<h3>Changes</h3>"))

                header_layout.addStretch(1)
                rootlayout.addLayout(header_layout)

                # --- Untaged changes (or just changes) ---
                self.unstaged_files = ChangesTree(
                    manager,
                    staged=False if is_stage_supported else None,
                )
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

                    self.staged_files = ChangesTree(manager, staged=True)
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
                # Branch slots
                self.branch_combobox.currentIndexChanged.connect(
                    self.branch_combobox.select)

                self.branch_combobox.sig_branch_changed.connect(
                    self.refresh_changes)

                self.branch_combobox.sig_branch_changed.connect(
                    plugin.sig_branch_changed)

            if getattr(self, "unstaged_files", None) is not None:
                # Unstage slots
                self.unstaged_files.sig_stage_toggled.connect(self.post_stage)
                self.unstaged_files.sig_stage_toggled[bool, str].connect(
                    self.post_stage)

                plugin.stage_all_action.triggered.connect(
                    self.unstaged_files.toggle_stage_all)

            if getattr(self, "staged_files", None):
                # Stage slots
                self.staged_files.sig_stage_toggled.connect(self.post_stage)
                self.staged_files.sig_stage_toggled[bool, str].connect(
                    self.post_stage)

                plugin.unstage_all_action.triggered.connect(
                    self.staged_files.toggle_stage_all)

            # Show the whole UI before refreshes
            QCoreApplication.processEvents()

        elif getattr(plugin, "create_vcs_action", None) is not None:
            # TODO: show "no repository available"
            #       when repository is missing,
            #       including buttons for create
            #       a new one or create it.
            rootlayout.addStretch(1)
            rootlayout.addWidget(
                QLabel(
                    _("<h3>No repository available</h3><br/>"
                      "in ") + str(
                          plugin.get_plugin(
                              Plugins.Projects).get_active_project_path())))

            create_button = action2button(
                plugin.create_vcs_action,
                text_beside_icon=True,
                parent=self,
            )
            create_button.setEnabled(bool(manager.create_vcs_types))
            # FIXME: change color if dark or white
            create_button.setStyleSheet("background-color: #1122cc;")
            rootlayout.addWidget(create_button)

            rootlayout.addStretch(1)

    # Public methods
    def setup_slots(self) -> None:
        """Connect all the common slots, including the plugins actions."""
        plugin = self.get_plugin()

        # Plugin signals
        plugin.sig_repository_changed.connect(self.setup)
        plugin.sig_repository_changed.connect(self.refresh_all)

        # Plugin actions
        plugin.create_vcs_action.triggered.connect(self.show_create_dialog)
        plugin.commit_action.triggered.connect(self.commit)
        plugin.fetch_action.triggered.connect(
            partial(
                self.sig_auth_operation[str, tuple, dict].emit,
                "fetch",
                (),
                dict(sync=True),
            ))
        plugin.pull_action.triggered.connect(
            partial(self.sig_auth_operation.emit, "pull"))
        plugin.push_action.triggered.connect(
            partial(self.sig_auth_operation.emit, "push"))

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
                self.unstaged_files.refresh(result)
                if getattr(self, "staged_files", None) is not None:
                    self.staged_files.refresh(result)

        manager = self.get_plugin().vcs_manager

        # Only one changes call is done for both the widgets.
        if manager.type.changes.fget.enabled:
            ThreadWrapper(
                self,
                lambda: manager.changes,
                result_slots=(_handle_result, ),
                error_slots=(_raise_if, ),
                nothread=not THREAD_ENABLED,
            ).start()

    @Slot()
    @Slot(tuple)
    def refresh_commit_difference(
        self,
        commit_difference: typing.Optional[typing.Tuple[int, int]] = None,
    ) -> None:
        """
        Show the numbers of commits to pull and push compared to remote.

        Parameters
        ----------
        commit_difference : tuple of int, optional
            A tuple of 2 integers.
            The first one is the amount of commit to pull,
            the second one is the amount of commit to push.
            Can be None, that allows this method to call the backend's
            ':meth:`~VCSBackendBase.fetch` method.
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
                        action.setText("{} ({})".format(
                            " ".join(label), difference))
                    else:
                        action.setText(" ".join(label))
            else:
                plugin.pull_action.setText(_("pull"))
                plugin.push_action.setText(_("push"))

        plugin = self.get_plugin()
        if commit_difference is None:
            ThreadWrapper(
                self,
                plugin.vcs_manager.fetch,  # pylint:disable=W0108
                result_slots=(_handle_result, ),
                error_slots=(_raise_if, ),
                nothread=not THREAD_ENABLED,
            ).start()
        else:
            _handle_result(commit_difference)

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
                            partial(
                                self.undo_commit,
                                i + 1,
                            ))
                        self.history.setItemWidget(item, 0, button)

                    if i % PAUSE_CYCLE == 0:
                        QCoreApplication.processEvents()

        manager = self.get_plugin().vcs_manager
        if manager.get_last_commits.enabled:
            self.history.clear()
            ThreadWrapper(
                self,
                partial(manager.get_last_commits, MAX_HISTORY_ROWS),
                result_slots=(_handle_result, ),
                error_slots=(lambda ex: _raise_if(ex, VCSUnexpectedError, True)
                             and self.history.addTopLevelItem(
                                 QTreeWidgetItem([None, ex.error, None])), ),
                nothread=not THREAD_ENABLED,
            ).start()

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
        if getattr(self, "branch_combobox",
                   None) is None or not self.branch_combobox.isEnabled():
            raise AttributeError("Cannot change branch in the current VCS")
        self.branch_combobox.select(branchname)

    @Slot(bool)
    @Slot(bool, str)
    def post_stage(
        self,
        staged: bool,
        path: typing.Optional[str] = None,
    ) -> None:
        """
        Refresh changes after a successful stage/unstage operation.

        See Also
        --------
        ChangesTree.sig_stage_toggled
            For a description of parameters.
        """
        if staged:
            treewid = self.staged_files
        else:
            treewid = self.unstaged_files
        if treewid is not None:
            if path is None:
                treewid.refresh()
            else:
                treewid.refresh_one(path)

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
            func = partial(func, *args, **kwargs)
            ThreadWrapper(
                self,
                func,
                result_slots=(_handle_result,
                              lambda res: self.refresh_commit_difference()
                              if res else None),
                error_slots=(
                    lambda ex: _raise_if(ex, VCSAuthError, True) or self.
                    handle_auth_error(ex, operation, args, kwargs), ),
                nothread=not THREAD_ENABLED,
            ).start()

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
        credentials = {
            # prefer error credentials instead of the backend ones
            key: getattr(ex, key, None) or manager.credentials.get(key)
            for key in ex.required_credentials
        }

        if credentials:
            dialog = LoginDialog(self, **credentials)
            dialog.accepted.connect(_accepted)
            dialog.rejected.connect(_rejected)
            dialog.show()

    @Slot()
    def show_create_dialog(self) -> None:
        """Show a :class:`CreateDialog` dialog for creating a repository."""
        plugin = self.get_plugin()
        plugin.create_vcs_action.setEnabled(False)
        dialog = CreateDialog(
            plugin.vcs_manager,
            plugin.get_plugin(Plugins.Projects).get_active_project_path(),
            parent=self,
        )
        dialog.rejected.connect(
            partial(plugin.create_vcs_action.setEnabled, True))
        dialog.sig_repository_ready.connect(plugin.set_repository)
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
            slots.append(_refresh_commit_message)
            ThreadWrapper(
                self,
                partial(manager.undo_commit, commits),
                result_slots=slots,
                error_slots=(_raise_if, ),
                nothread=not THREAD_ENABLED,
            ).start()


class CreateDialog(QDialog):
    """A dialog to manage cloning operation."""

    sig_repository_ready = Signal(str)
    """
    This signal is emitted when repository creation is done.

    Parameters
    ----------
    repodir : str
        The repository directory.
    """
    def __init__(self, manager: VCSBackendManager, rootpath: str, parent=None):
        super().__init__(parent=parent)
        self.credentials = {}
        self.tempdir = None
        self.manager = manager

        # Widgets
        self.vcs_select = QComboBox()
        self.directory = QLineEdit()
        self.url_select = UrlComboBox(self)
        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok
                                     | QDialogButtonBox.Cancel)

        # Widget setup
        self.vcs_select.addItems(manager.create_vcs_types)
        self.directory.setText(rootpath)

        # TODO: Currently, only opened projects can create repositories,
        #       so it is forbidden to change the repository path.
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
        buttonbox.rejected.connect(self.cleanup)
        buttonbox.rejected.connect(self.reject)

    # Public slots
    @Slot()
    def cleanup(self) -> None:
        """Remove the temporary directory."""
        self.tempdir = None

    # Qt overrides
    @Slot()
    def accept(self) -> None:
        url = self.url_select.currentText()
        if url:
            if not self.url_select.is_valid(url):
                QMessageBox.critical(
                    self, _("Invalid URL"),
                    -("Creating a repository from an existing"
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
        def _handle_result(result):
            if result:
                ThreadWrapper(
                    self,
                    _move,
                    result_slots=(
                        lambda _: self.sig_repository_ready.emit(path),
                        self.cleanup),
                    error_slots=(_raise_if, self.cleanup),
                ).start()
            else:
                QMessageBox.critical(self, _("Create failed"),
                                     _("The create fails unexpectedly."))

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
            error_slots=(lambda ex: _raise_if(ex, VCSAuthError, True) or self.
                         _handle_auth_error(ex), ),
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
            # Inform the main widget that the operation had failed.
            self.cleanup()
            self.rejected.emit()

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


@Slot(Exception)
@Slot(Exception, type)
@Slot(Exception, type, bool)
def _raise_if(ex: Exception,
              required_type: type = Exception,
              inverse: bool = False):
    condition = isinstance(ex, required_type) ^ inverse
    if condition:
        raise ex


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

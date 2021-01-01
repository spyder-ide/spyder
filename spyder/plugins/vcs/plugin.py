#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Version Control Support Plugin."""

# Standard library imports
from typing import Optional
from functools import partial

# Third party imports
import qtawesome as qta
from qtpy.QtCore import Slot, Signal

# Local imports
from spyder.api.translations import get_translation
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.config.manager import CONF
from spyder.utils import icon_manager as ima

from .backend.api import VCSBackendManager
from .backend.git import GitBackend
from .backend.errors import VCSError
from .widgets.vcsgui import VCSWidget

# Localization
_ = get_translation("spyder")


class VCS(SpyderDockablePlugin):  # pylint: disable=W0201
    """
    VCS plugin.
    """

    NAME = "VCS"
    REQUIRES = [Plugins.Projects]
    OPTIONAL = [Plugins.Shortcuts, Plugins.MainMenu]
    TABIFY = [Plugins.Help]
    WIDGET_CLASS = VCSWidget
    CONF_SECTION = NAME

    # Signals definition
    sig_repository_changed = Signal(str, str)
    """
    This signal is emitted when the current managed repository change.

    Parameters
    ----------
    repository_path: str
        The path where repository files are stored.
        This path never indicate VCS-specific directory,
        such as .git, .hg, .svn, etc.

        Can be None which means no repository is loaded.

    vcs_type: str
        The canonical name for the VCS. Common names are: git, mercurial.
    """

    sig_branch_changed = Signal(str)
    """
    This signal is emitted when the current branch change

    Parameters
    ----------
    branchname: str
        The current branch name in the VCS.
    """

    # Other attributes definition

    vcs_manager: VCSBackendManager
    """
    The manager for the current VCS.

    This can be used to get information about the repository.

    Notes
    -----
    This is usually referred as "backend".

    Warnings
    --------
    Any backend call blocks the current thread and
    may invoke subprocess or other long-running operation.
    It is better to run those calls in separate threads
    and wait results asynchronously.
    The class :class:`~ThreadWrapper` may help you.
    """

    def __init__(self, *args, **kwargs):
        self.vcs_manager = VCSBackendManager(None)
        # workaround when imported as 3rd party plugin
        kwargs.setdefault("configuration", CONF)
        super().__init__(*args, **kwargs)

    # Reimplemented APIs
    def get_name(self):
        return _("VCS")

    def get_description(self):
        return _("Manage project VCS repository in a unified pane.")

    def get_icon(self):
        # return self.create_icon("code_fork")
        return qta.icon("mdi.source-branch")

    def register(self):
        # Register backends
        self.vcs_manager.register_backend(GitBackend)

        # Hide view
        self.toggle_view(False)

        # Connect external signals
        project = self.get_plugin(Plugins.Projects)
        project.sig_project_loaded.connect(self.set_repository)
        project.sig_project_loaded.connect(partial(self.toggle_view, True))
        project.sig_project_closed.connect(lambda: self.set_repository(None))
        project.sig_project_closed.connect(partial(self.toggle_view, False))

    # Internal methods
    def create_actions(self):
        create_action = self.create_action
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        mainmenu = self.get_plugin(Plugins.MainMenu)

        self.create_vcs_action = create_action(
            "vcs_create_vcs_action",
            _("Create a new repository"),
            icon=qta.icon("mdi.source-branch-plus", color=ima.MAIN_FG_COLOR),
            icon_text=_("Create a new repository"),
            tip=_("Create a new repository"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )
        self.stage_all_action = create_action(
            "vcs_stage_all_action",
            _("Stage all"),
            icon=qta.icon("fa.long-arrow-down", color=ima.MAIN_FG_COLOR),
            icon_text=_("stage all"),
            tip=_("Stage all the unstaged changed"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )
        self.unstage_all_action = create_action(
            "vcs_unstage_all_action",
            _("Unstage all"),
            icon=qta.icon("fa.long-arrow-up", color=ima.MAIN_FG_COLOR),
            icon_text=_("unstage all"),
            tip=_("Unstage all the staged changes"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )
        self.commit_action = create_action(
            "vcs_commit_action",
            _("Commit"),
            icon=qta.icon("mdi.source-commit", color=ima.MAIN_FG_COLOR),
            icon_text=_("Commit changes"),
            tip=_("Commit changes"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.fetch_action = create_action(
            "vcs_fetch_action",
            _("Fetch"),
            icon=qta.icon("fa5s.sync", color=ima.MAIN_FG_COLOR),
            icon_text=_("fetch"),
            tip=_("Fetch changes from the remote repository"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.pull_action = create_action(
            "vcs_pull_action",
            _("Pull"),
            icon=qta.icon("fa.long-arrow-down", color=ima.MAIN_FG_COLOR),
            icon_text=_("pull"),
            tip=_("Pull changes from the remote repository"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.push_action = create_action(
            "vcs_push_action",
            _("Push"),
            icon=qta.icon("fa.long-arrow-up", color=ima.MAIN_FG_COLOR),
            icon_text=_("push"),
            tip=_("Push changes to the remote repository"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.refresh_action = create_action(
            "vcs_refresh_action",
            _("Refresh"),
            icon=qta.icon("mdi.refresh", color=ima.MAIN_FG_COLOR),
            icon_text=_("refresh"),
            tip=_("Refresh the VCS pane immediately"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        if shortcuts:
            for action_name, action in self.get_actions().items():
                shortcuts.register_shortcut(
                    action, self.NAME, action_name, plugin_name=self.NAME
                )
        if mainmenu:
            appmenu = mainmenu.create_application_menu(
                self.NAME + "_menu",
                _("&VCS"),
            )
            for action in self.get_actions().values():
                mainmenu.add_item_to_application_menu(action, menu=appmenu)

    # Public API
    def get_repository(self) -> Optional[str]:
        """
        Get the current managed VCS repository.

        Returns
        -------
        str or None
            The current VCS repository or None if no repository is managed.
        """
        return self.vcs_manager.repodir

    # compatibility with sig_project_loaded
    @Slot(object)
    @Slot(str)
    def set_repository(self, repodir: str) -> Optional[str]:
        """
        Set the current VCS repository.

        Parameters
        ----------
        repository_dir: str
            The path where repository files are stored.
            Subdirectories are also accepted.

            This path should not indicate VCS-specific directory,
            such as .git, .hg, .svn, etc.

        Returns
        -------
        str or None
            The repository root path.
            This path is different compared to the repository_dir parameter
            only if that refers to a subdirectory of the repository.
            None is returned when no valid repository was found.
        """
        try:
            if repodir is None:
                # Raise dummy error
                raise VCSError()
            self.vcs_manager.repodir = repodir

        except VCSError:
            self.vcs_manager.repodir = None
            self.refresh_action.setEnabled(False)
            self.sig_repository_changed.emit(None, None)

        else:
            self.refresh_action.setEnabled(True)
            self.sig_repository_changed.emit(
                self.vcs_manager.repodir, self.vcs_manager.VCSNAME
            )
        return self.get_repository()

    repodir = property(
        get_repository,
        set_repository,
        doc="A property shorthand for get_repository and set_repository",
    )

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

        Notes
        -----
        Branch selection is done through the properly widget.
        If you just want to change the branch, call the backend.
        """
        branch_list = self.get_widget().branch_list
        if not branch_list.isEnabled() and not branch_list.isVisible():
            raise AttributeError("Cannot change branch in the current VCS")
        branch_list.select(branchname)

        self.get_widget().select_branch(branchname)

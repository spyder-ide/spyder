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
import typing

# Third party imports
import qtawesome as qta
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QAction

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.config.manager import CONF
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import toggle_actions

from .utils.api import VCSBackendManager
from .utils.backend import GitBackend, MercurialBackend
from .utils.errors import VCSError
from .widgets.vcsgui import VCSWidget

# Localization
_ = get_translation('spyder')


class VCS(SpyderDockablePlugin):  # pylint: disable=W0201
    """
    VCS plugin.
    """

    NAME = 'VCS'
    REQUIRES = [Plugins.Projects]
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

    # Actions defintion
    stage_all_action: QAction
    """
    Action for stage all the unstaged changes.

    When triggered,
    the :py:meth:`~VCSBackendBase.stage_all` method is called.
    """

    unstage_all_action: QAction
    """
    Action for unstage all the staged changes.

    When triggered,
    the :py:meth:`~VCSBackendBase.unstage_all` method is called.
    """

    commit_action: QAction
    """
    Action for commit.

    When triggered and there is a commit message,
    the :py:meth:`~VCSBackendBase.commit` method is called.
    """

    fetch_action: QAction
    """
    Action for fetch.

    When triggered, the :py:meth:`~VCSBackendBase.fetch` method is called.
    """

    pull_action: QAction
    """
    Action for pull.

    When triggered, the :py:meth:`~VCSBackendBase.pull` method is called.
    """

    push_action: QAction
    """
    Action for push.

    When triggered, the :py:meth:`~VCSBackendBase.push` method is called.
    """

    create_vcs_action: QAction
    """
    Action for create an empty repository.

    When triggered, a dialog box is showed,
    then :py:meth:`~VCSBackendBase.create` is called.
    """

    # Other attributes definition

    vcs_manager: VCSBackendManager
    """
    The manager for the current VCS.

    This can be used to get information about the repository.

    .. warning::
        Any call to the manager blocks the current thread and
        may invoke subprocess or other long-running operation.
        It is better to run those calls in separate threads
        and wait results asynchronously.
        The :class:`~ThreadWrapper` may help you.

    .. danger::
        Do any operation that changes the repository state
        will break the VCS pane UI.
        Use actions where possible.
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
        # register backends
        self.vcs_manager.register_backend(GitBackend)
        self.vcs_manager.register_backend(MercurialBackend)

        # Create actions
        self._create_actions()
        self.get_widget().setup_slots()

        # connect external signals
        project = self.get_plugin(Plugins.Projects)
        project.sig_project_loaded.connect(self.set_repository)

    # Public API
    def get_repository(self) -> typing.Optional[str]:
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
    def set_repository(self, repository_dir: str) -> str:
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
            self.vcs_manager.repodir = repository_dir
        except VCSError:
            self.vcs_manager.repodir = None
            toggle_actions(
                (self.commit_action, self.fetch_action, self.pull_action,
                 self.push_action, self.refresh_action), False)
            self.sig_repository_changed.emit(None, None)
        else:
            for (action, featurename) in (
                (self.commit_action, "commit"),
                (self.fetch_action, "fetch"),
                (self.pull_action, "pull"),
                (self.push_action, "push"),
            ):
                feature = getattr(self.vcs_manager, featurename, None)
                if feature is not None:
                    action.setEnabled(feature.enabled)
            self.refresh_action.setEnabled(True)
            self.sig_repository_changed.emit(self.vcs_manager.repodir,
                                             self.vcs_manager.VCSNAME)
        self.create_vcs_action.setEnabled(True)
        return self.get_repository()

    repository_path = property(
        get_repository,
        set_repository,
        doc="A property shorthand for get_repository and set_repository")

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
        self.get_widget().select_branch(branchname)

    # Private methods
    def _create_actions(self):
        # TODO: Add tips
        create_action = self.create_action

        self.create_vcs_action = create_action(
            "vcs_create_vcs_action",
            _("create new repository"),
            # icon=qta.icon("fa.long-arrow-down", color=ima.MAIN_FG_COLOR),
            icon_text=_("create new repository"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )
        self.stage_all_action = create_action(
            "vcs_stage_all_action",
            _("stage all"),
            icon=qta.icon("fa.long-arrow-down", color=ima.MAIN_FG_COLOR),
            icon_text=_("stage all"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )
        self.unstage_all_action = create_action(
            "vcs_unstage_all_action",
            _("unstage all"),
            icon=qta.icon("fa.long-arrow-up", color=ima.MAIN_FG_COLOR),
            icon_text=_("unstage all"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )
        self.commit_action = create_action(
            "vcs_commit_action",
            _("commit"),
            icon=qta.icon("mdi.source-commit", color=ima.MAIN_FG_COLOR),
            icon_text=_("commit"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.fetch_action = create_action(
            "vcs_fetch_action",
            _("fetch"),
            icon=qta.icon("fa5s.sync", color=ima.MAIN_FG_COLOR),
            icon_text=_("fetch"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.pull_action = create_action(
            "vcs_pull_action",
            _("pull"),
            icon=qta.icon("fa.long-arrow-down", color=ima.MAIN_FG_COLOR),
            icon_text=_("pull"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.push_action = create_action(
            "vcs_push_action",
            _("push"),
            icon=qta.icon("fa.long-arrow-up", color=ima.MAIN_FG_COLOR),
            icon_text=_("push"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

        self.refresh_action = create_action(
            "vcs_refresh_action",
            _("refresh"),
            icon=qta.icon("mdi.refresh", color=ima.MAIN_FG_COLOR),
            icon_text=_("refresh"),
            # tip=_("ADD TIP HERE"),
            shortcut_context=self.NAME,
            triggered=lambda: None,
        )

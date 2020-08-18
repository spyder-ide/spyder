#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Backend specifications and utilities for VCSs."""

# TODO: fix classes/methods/attributes/variables name
#       (consistency, abbreviations and style)

# Standard library imports
import functools
import typing

# Local imports
from .errors import VCSError, VCSBackendFail

_decorated = typing.Callable[..., object]


def checker(*features: str) -> _decorated:
    """
    Check features before running.

    Parameters
    ----------
    *features : str
        A list of features to the checker.

    See Also
    --------
    check_features
    """
    def _decorator(func: _decorated) -> _decorated:
        @functools.wraps(func)
        def wrapper(self, *args: object,
                    **kwargs: object) -> object:  # type: ignore
            self.check_features(*features)
            return func(self, *args, **kwargs)

        return wrapper

    return _decorator


class ChangedStatus(object):
    """Representing the possible change state that a file can have."""

    UNCHANGED = 0

    # minimal support
    ADDED = 1
    REMOVED = 2
    MODIFIED = 3
    EDITED = 3  # alias of MODIFIED

    # extra support
    RENAMED = 10
    COPIED = 11

    # special cases
    IGNORED = 98
    UNKNOWN = 99

    @classmethod
    def from_string(cls, state: str) -> int:
        """
        Convert the given string in a valid int state.

        Parameters
        ----------
        state : str
            The state as a string.

        Raises
        ------
        AttributeError
            If the given state does not exists.

        Returns
        -------
        int
            The corresponding int value.

        """
        intstate = getattr(cls, state.upper(), None)
        if isinstance(intstate, int):
            return intstate

        raise AttributeError("Given state {} does not exists".format(state))

    @classmethod
    def to_string(cls, state: int) -> str:
        """
        Convert the given state to the respective string representation.

        Parameters
        ----------
        state : int
            The state

        Raises
        ------
        AttributeError
            If the state is invalid.

        Returns
        -------
        str
            The string representation of the state.
        """
        attrs = vars(cls)
        for name, val in attrs.items():
            if val == state:
                return name.lower()

        raise AttributeError("Given state {} does not exists".format(state))


class VCSBackendBase(object):
    """
    Uniforms VCS fundamental operations across different VCSs.


    **Error handling**

    By default, if a generic error occurred,
    all the method for VCS operations raises a VCSUnexpectedError
    and all the properties raises VCSPropertyError.
    """

    VCSNAME: str = None  # type: ignore
    """
    The VCS name (the common one) supported.

    This name can be duplicated.

    See Also
    --------
    VCSBackendManager
    """

    FEATURES: typing.Dict[str, bool] = {
        "file-state": False,
        "file-diff": False,
        "current-branch": False,
        "change-branch": False,
        "branches": False,
        "manage-branches": False,
        "stage-unstage": False,
        "commit": False,
        "pull": False,
        "push": False,
        "undo": False,
        "history": False,
        "merge": False,
    }
    # ???: list properties and methods associated to each feature here
    """
    Supported VCS features.

    - file-state: Allows to get the current state of files in the repo.

    - file-diff: Allows to get the difference between the current revision
                 and the the old one (upstream).

    - current-branch: Allows to get the current branch where the local repo is.

    - change-branch: Allows to change the current branch.

    - branches: Allows to get all the branches (local and remote if supported).

    - manage-branches: Allows to create, edit, and delete branches.

    - stage-unstage: Allows to change a file state
                     from staged to unstaged and viceversa.
                     This feature can be implemented by doing nothing
                     if the VCS does not have a staging area.

    - commit: Allows to create a revision from staged file.

    - fetch: Allows to download the remote repository state.

    - pull: Allows to update the current branch to the latest revision.

    - push: Allows to upload a revision to the remote repository.

    - undo: Allows to undo operations. This feature usually complete another.

    - history: Allows to see previous commits.

    - merge: Allows to join 2 revision.
    """

    REQUIRED_CREDENTIALS: typing.Sequence[str] = None
    """
    The required keys for credentials.

    If this value is non-zero, credentials are suppored.

    Warnings
    -------
    Since some VCS does not have a simple way to check
    if credentials are necessary for the current repository (notably git),
    the only way to know that is trying to do the operation
    and catch the VCSAuthError,
    then ask/get the credentials and retry the operation.
    """

    # --- Non-features ---
    @classmethod
    def check_features(cls,
                       *features: str,
                       suppress_raise: bool = False) -> bool:
        """
        Check if given features are supported.

        Parameters
        ----------
        *features : str
            The feature to check for.
         suppress_raise : bool, optional
            If True, a NotImplementedError will not be raised
            when a feature is not supported. The default is False.

        Raises
        ------
        NotImplementedError
            If one of the feature is not supported
        ValueError
            If one of the feature is invalid

        Returns
        -------
        bool
            True that means that all the features are supported.
            False if suppress_raise is True
            and one of the feature is not supported.
        """
        for feature in features:
            enabled = cls.FEATURES.get(feature)
            if enabled is None:
                raise ValueError("Invalid feature {}".format(feature))

            if not enabled:
                if suppress_raise:
                    return False
                raise NotImplementedError(
                    "Feature {} is not implemented for {}".format(
                        feature, cls.VCSNAME))

        return True

    def __init__(self, repodir: str):
        super().__init__()
        self.repodir = repodir

    @property
    def credentials(self) -> typing.Dict[str, object]:
        """
        The required credentials to do operation on VCS remotes.

        **Get**

        Return the credentials as a dict.
        If no credential are set, an empty dict is returned instead.

        **Set**

        Set the credentials.

        Implementations can use persistent methods (file, keyring, ...)
        for saving credentials.

        **Del**

        Clear the credentials.

        If the implementation save credential in a persistent way,
        this method should make it no longer persistent.

        Warnings
        --------
        Due to difference in credential management or usage between VCSs,
        this property can not be VCS-indipendent.
        In any case, this property should use only these keys for credentials:
        username, password, email, token.

        .. note::
            This property does not refer to a particular feature.
        """
        raise NotImplementedError("Credential property is not implemented")

    @credentials.setter
    def credentials(self, credentials: typing.Dict[str, object]) -> None:
        raise NotImplementedError("Credential property is not implemented")

    @credentials.deleter
    def credentials(self) -> None:
        raise NotImplementedError("Credential property is not implemented")

    # features
    @property
    @checker("current-branch")
    def branch(self) -> str:
        """
        Handle the current repository branch.

        This property support get, set and del.

        **Get** (Requires current-branch)

        Return the current branch/tag/revision where the local repo is

        **Set** (Requires change-branch)

        Set the current branch to the given one.

        The given branch must exist in the repository.
        Implementations must raises an error if the given branch
        does not exists.

        **Del** (Requires manage-branches)

        Delete the current branch.

        .. warning::
            This deleter can fail even if the manage-branches is enabled.
            It's the caller reponsibility to handle the exception.
        """

    @branch.setter
    @checker("change-branch")
    def branch(self, branchname: str) -> None:  # pylint: disable=W0613
        pass

    @branch.deleter
    @checker("manage-branches")
    def branch(self) -> None:
        pass

    @property
    @checker("branches")
    def branches(self) -> typing.List[str]:
        """
        A list of branch names.

        **Get** (requires branches)

        Get a list of branches.
        The list may not include tags or other revisions that are VCS-specific.

        .. warning::
            The implementation can return an observable list
            that reflect its changes to the VCS.
            It is encouraged to make a shallow copy before editing it.

        See Also
        --------
        editable_branches
        """

    @property
    @checker("branches")
    def editable_branches(self) -> typing.List[str]:
        """
        A list of editable branch names.

        An editable branch is a branch where committing is allowed.

        If VCS do not support this difference,
        all the branches will be returned.

        **Get** (requires branches)


        Get a list of editable branches.

        See Also
        --------
        branches
        """
        return self.branches.copy()

    @property
    @checker("file-state")
    def changes(self) -> typing.List[typing.Dict[str, object]]:
        """
        A list of changed files and its states.

        **Get** (requires file-state)

        Get a list of changed paths,
        associated with a dict containing file state.

        Warnings
        -------
        If VCS supports the staging area and
        a path has both an unstaged and staged status,
        each status is

        See Also
        --------
        change
            The change method for a detailed description of states.
        """

    @checker("file-state")
    def change(self, path: str) -> typing.Dict[str, object]:
        """
        Get the state dict associated of path (requires file-state).

        The state dict can have several fields (all of them optional):

        - path: the path to the file (mostly used by the changes property)

        - kind: what change is occurred to the file.
                Possible values are listed in ChangedStatus.

        - staged: a flag indicated if the file is staged or not

        - comment: a comment describing the changes.
                   Do not confuse it with the commit description.

        .. note::
            The backend can add extra VCS-dependent fields.

        .. note::
            The usage of the UNCHANGED state is VCS-dependent.

        Parameters
        ----------
        path : str
            The relative path.

        Returns
        -------
        dict
            The file state.

        Warnings
        --------
        Implementations can use an immutable mapping instead of dict
        to improve performance/saving memory.
        If you need to change it, cast it into a dict.

        Implementation specific:
        Even if all the fields are optional,
        the ideal goal is to implement all of them,
        unless the underlying VCS has no support for some of them.
        """

    @checker("stage-unstage")
    def stage(self, path: str) -> bool:
        """
        Set the given path state to staged (requires stage-unstage).

        Returns
        -------
        True if the path is now staged, False otherwise.
        """

    @checker("stage-unstage")
    def unstage(self, path: str) -> bool:
        """
        Clear the given path state to be staged (requires stage-unstage).

        Returns
        -------
        True if the path is now unstaged, False otherwise.
        """

    @checker("commit")
    def commit(self,
               message: str,
               is_path: typing.Optional[bool] = None) -> bool:
        """
        Commit changes (requires commit).

        Parameters
        ----------
        message
            The commit message or the path to that.

        is_path
            Specify if the given message parameter is a path or not.
            By default is None, that let this to decide.

        Returns
        -------
        True if the commit was done, False otherwise.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
        """

    @checker("pull")
    def fetch(self, sync: bool = False) -> typing.Tuple[int, int]:
        """
        Scan the current local branch to get commit status.

        The method main purpuse (unlike git fetch) is not to syncronize
        to the server, but give a comparison between local revision and
        the remote one.

        Parameters
        ----------
        sync : bool, optional
            If True and the VCS support it, syncronize the local
            repository with the remote one. The default is False.

        Returns
        -------
        (int, int)
            A tuple with 2 integers:
            the number of commit to pull and the number of commit to push.
            If push is not supported, the second int become -1.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
            Only if sync is True.

        .. note::
            Implementations can do no operation on the VCS.
            However, the return value should be processed in object case.
        """

    @checker("pull")
    def pull(self, fetch: bool = True) -> bool:  # pylint: disable=W0613
        """
        Get latest revision from remote.

        Parameters
        ----------
        fetch : bool, optional
            If True (default), do a fetch before pulling.

        Returns
        -------
        bool
            True if the pull was done correcly.
            False otherwise.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
        """

    @checker("push")
    def push(self) -> bool:
        """
        Get latest revision from remote.

        Returns
        -------
        True if the push was done correcly and there is no commits to pull,
        False otherwise.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
        """


class VCSBackendManager(object):
    """Automatic backend selector and repository manager."""

    __slots__ = (
        "_backends",
        "_backend",
    )

    def __init__(self, repodir: str, *backends: type):
        super().__init__()
        self._backends = list(backends)
        self._backend = None
        self.repodir = repodir

    def __getattr__(self, name: str) -> object:
        """Get attributes from the backend."""
        return getattr(self._backend, name)

    def __setattr__(self, name: str, value: object) -> None:
        """Set attributes to the backend."""
        if name in dir(self):
            super().__setattr__(name, value)
        elif name in dir(self._backend):
            setattr(self._backend, name, value)

    def __delattr__(self, name: str) -> None:
        """Del attributes in the backend."""
        if name in dir(self):
            super().__delattr__(name)
        elif name in dir(self._backend):
            delattr(self, name)

    @property
    def repodir(self) -> typing.Optional[str]:
        """
        The current managed repository directory.

        You can load another repository directory by setting this property.
        """
        return self._backend.repodir if self._backend else None

    @repodir.setter
    def repodir(self, path: str) -> None:
        self._backend = selected_backend = None
        if path:
            errors = []
            for backend in self._backends:
                try:
                    selected_backend = backend(path)
                except VCSBackendFail as ex:
                    errors.append(ex)
                except VCSError:
                    # Ignore weird errors.
                    pass
                else:
                    break

            if selected_backend is None:
                raise VCSError(
                    "Valid backend not found for the given directory")

            self._backend = selected_backend

    def register_backend(self, backend: type) -> None:
        """
        Register a VCSBackendBase subclass.

        The given type will be used in the backend selection.

        Parameters
        ----------
        backend : type
            The VCSBackendBase subclass.
        """
        self._backends.append(backend)

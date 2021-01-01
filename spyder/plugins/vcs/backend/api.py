#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Backend specifications and utilities for VCSs."""

# pylint: disable=C0302

import typing
# Standard library imports
import builtins
import itertools
from typing import Dict, Tuple, Union, Callable, Optional, Sequence
from functools import partial

# Local imports
from .errors import VCSError, VCSAuthError, VCSBackendFail


def feature(
        name: str = None,
        enabled: bool = True,
        extra: Optional[Dict[object, object]] = None) -> Callable[..., object]:
    """
    Decorate a function to become a feature.

    A feature is a function (or any callable)
    that implement a particular prototype of API specification.

    The main purpose of a feature is introspection.
    In fact, a feature hold several informations
    about the wrapped function.
    These informations are set to the decorared function
    to be getted easily.

    Parameters
    ----------
    name : str, optional
        The feature unique name.
        The default is None, that allows to use the decorated
        function name through his `__name__` attribute.

    enabled : bool, optional
        A flag indicating if the feature can be used. THe default is True.
        The default is True.

    extra : Dict[str, object], optional
        Extra arguments which define the feature behaviour.
        Should be defined by the API specification.

    Warnings
    --------
    If you want to decorate a property getter,
    don't decorate the property object.


    Examples
    --------
    Here is some examples of feature definitions.

    Define a feature with its name

    >>> @feature(name="feature")
    ... def my_feature_implementation(arg1, ..., argn):
    ...     # Feature code
    <function my_feature_implementation at 0xnnnnnnnnnnnn>

    Define a feature using the function name as feature name

    >>> @feature()
    ... def feature(arg1, ..., argn):
    ...     # Feature code
    <function feature at 0xnnnnnnnnnnnn>

    Define a disabled feature

    >>> @feature(enabled=False)
    ... def feature(arg1, ..., argn):
    ...     pass
    <function feature at 0xnnnnnnnnnnnn>

    Define a feature with some extras

    >>> @feature(extra={"my_extra": "value"})
    ... def feature(arg1, ..., argn):
    ...     # Feature code
    <function feature at 0xnnnnnnnnnnnn>
    """
    if extra is None:
        extra = {}

    def _decorator(func: Callable[..., object]):
        if name is not None:
            # Set the new function name
            func.__name__ = name
        func.enabled = enabled
        func.extra = extra
        func._is_feature = True  # pylint: disable=W0212
        return func

    return _decorator


class ChangedStatus(object):
    """Representing the possible change state that a file can have."""

    UNCHANGED = 0

    # minimal support
    ADDED = 1
    REMOVED = 2
    DELETED = 2  # alias of REMOVED
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


# TODO: Complete backend detailed description
class VCSBackendBase(object):  # pylint: disable=R0904
    """
    Uniforms VCS fundamental operations across different VCSs.

    **Instance usage**

    Unlike backend implementators, backend users should use only
    features (methods marked with :func:`~feature`)
    and common attributes.

    **Error handling**

    By default, if a generic error occurred,
    all the method for VCS operations raises a :class:`~VCSFeatureError`
    and all the properties raises :class:`~VCSPropertyError`.

    If any requisite stopped working
    (e.g. executable removed or module unrecoverable failure),
    a :class:`~VCSBackendFail` exception will be raised.

    Parameters
    ----------
    repodir : str
        The absolute path to the repository directory.

    Raises
    ------
    VCSBackendFail
        If an error that prevent the backend to be initialized occurred.
        See its documentation for more information.
    FileNotFoundError
        If the given path is invalid or does not exists.
    """

    VCSNAME: str = None  # type: ignore
    """
    The VCS name (the common one) supported.

    This name can be duplicated.

    See Also
    --------
    VCSBackendManager
    """

    # Defined groups with associated members
    GROUPS_MAPPING: Dict[str, Sequence[Union[Tuple[str, str], str]]] = {
        "create": ("create", ),
        "status": (
            ("branch", "fget"),
            "change",
            ("changes", "fget"),
        ),
        "branches": (
            ("branch", "fget"),
            ("branch", "fset"),
            ("remote_branch", "fget"),
            ("branches", "fget"),
            ("editable_branches", "fget"),
            "delete_branch",
        ),
        "diff": (),
        "stage-unstage": (
            "stage",
            "unstage",
            "stage_all",
            "unstage_all",
        ),
        "commit": ("commit", "undo_commit"),
        "remote": ("fetch", "push", "pull"),
        "undo": ("unstage", "undo_commit", "undo_change", "undo_change_all"),
        "history": (
            ("tags", "fget"),
            "get_last_commits",
        ),
        "merge": (),
    }
    """
    VCS features groups mapping.

    **Groups descrtiption**

    Here are listed all the supported groups.

    Each group name has a short description and a list of members
    that belong to the group.
    Each member has a short description and,
    for properties, each operation is specified by the classifier
    and has its own section.

    - create: Allows to create a new local repository or get it from an URI.

        :meth:`~VCSBackendBase.create`
            Create a repository and initialize the backend.

    - status: Allows to get the current repository status.

        :attr:`~VCSBackendBase.branch` : getter
            Current local branch (provided by branches)

        :meth:`~VCSBackendBase.change`
            File state (staged status provided by stage-unstage).

        :attr:`~VCSBackendBase.changes` : getter
            All files states (staged status provided by stage-unstage)

    - branches: Allows to manage the branches
        :attr:`~VCSBackendBase.branch` : getter
            Current local branch.

        :attr:`~VCSBackendBase.branch` : setter
            Change the current local branch.

        .. Maybe?
        .. :attr:`~VCSBackendBase.remote_branch` : getter
        ..     Current remote branch.

        :attr:`~VCSBackendBase.branches` : getter
            A list of branches.

        :attr:`~VCSBackendBase.editable_branches` : getter
            A subset of branches that contains only editable branches.

        :meth:`~VCSBackendBase.create_branch`
            Create a new branch.

        :meth:`~VCSBackendBase.delete_branch`
            Delete the branch.

    - diff: WIP specification.

    - stage-unstage: Allows to change a file state
      from staged to unstaged and viceversa.

        :meth:`~VCSBackendBase.stage`
            Stage a file.

        :meth:`~VCSBackendBase.unstage`
            Unstage a file.

        :meth:`~VCSBackendBase.stage_all`
            Stage all the files.

        :meth:`~VCSBackendBase.unstage_all`
            Unstage al the files.

    - commit: Allows to create a revision.
        :meth:`~VCSBackendBase.commit`
            Do a commit.

    - remote: Allows to do operations on remote repository.
        :meth:`~VCSBackendBase.fetch` (sync=False)
            Compare the local branch with the remote one.

        :meth:`~VCSBackendBase.fetch` (sync=True)
            Download the remote repository state.

        :meth:`~VCSBackendBase.pull`
            Update the current branch to the latest revision.

        :meth:`~VCSBackendBase.push`
            Upload the local revision to the remote repository.

    - undo: Allows to undo an operation in the repository
        :meth:`~VCSBackendBase.unstage`
            Unstage a file.

        :meth:`~VCSBackendBase.undo_commit`
            Undo the last commit.

        :meth:`~VCSBackendBase.undo_change`
            Remove all the changes in a file.
            This operation can't be recovered.

        :meth:`~VCSBackendBase.undo_change_all`
            Remove all the changes in any changed file.
            This operation can't be recovered.

    - history: Allows to get the VCS history
        :meth:`~VCSBackendBase.get_last_commits`
            Get the last commits in the current branch.
            (provided by commit)

        :attr:`~VCSBackendBase.tags` : getter
            A list of revision labels.


    - merge: WIP specification.
    """

    REQUIRED_CREDENTIALS: Sequence[str] = None
    """
    The required keys for credentials.

    If this value is non-zero, credentials are suppored.

    Warnings
    --------
    Since some VCS does not have a simple way to check
    if credentials are necessary for the current repository (notably git),
    the only way to know that is trying to do the operation
    and catch VCSAuthError,
    then ask/get the credentials and retry the operation.
    """

    # --- Non-features ---
    @classmethod
    def check(
            cls,
            group: str,
            all: bool = False,  # pylint: disable=W0622
    ) -> Union[int, bool]:
        """
        Check if features in the group are enabled.

        Parameters
        ----------
        group : str
            The group to check.
        all : bool, optional
            If True, all the feature are checked to be enabled
            and this method stops if at least one feature is disabled.
            Otherwise all the features are checked. For that reason,
            the return value type differs if this parameter is True or False,
            see below. The default is False.

        Returns
        -------
        int
            Only if all is False.
            The number of enabled features.

        bool
            Only if all is True.
            True if all the features are enabled, False otherwise.
        """
        def _name_to_feature(
                featurename: Union[Tuple[str, str], str]) -> object:
            if isinstance(featurename, str):
                feature_func = getattr(cls, featurename, None)
            elif len(featurename) > 1:
                # Only the first and the second element are considered
                feature_func = getattr(getattr(cls, featurename[0], None),
                                       featurename[1], None)
            else:
                feature_func = None

            if (feature_func is None
                    or getattr(feature, "_is_feature", False)):
                raise TypeError("Invalid feature name {}".format(featurename))

            return feature_func

        group = cls.GROUPS_MAPPING.get(group)
        if group is None:
            raise KeyError("Group {} does not exists".format(group))

        if all:
            return builtins.all(
                _name_to_feature(featurename).enabled for featurename in group)

        return sum(
            bool(_name_to_feature(featurename).enabled)
            for featurename in group)

    def __init__(self, repodir: str):
        super().__init__()
        self.repodir = repodir

    def __init_subclass__(cls, **kwargs):
        """Adjust subclass attributes to match the feature name."""
        def _dummy_feature(self, *_, **__):
            raise NotImplementedError("This feature is not implemented yet.")

        super().__init_subclass__(**kwargs)
        attrs = {
            key: getattr(cls, key)
            for key in dir(cls) if not key.startswith("_")
        }

        for key, attr in attrs.items():
            # check if attr is a feature.
            if getattr(attr, "_is_feature", False):
                if attr.__name__ != key:
                    # This approach can broke the backend
                    # if the attribute already exists.
                    setattr(cls, attr.__name__, attr)

            # check if attr is a property.
            elif isinstance(attr, property):
                # check if property is a feature
                is_feature = getattr(attr.fget, "_is_feature", None)
                if is_feature:
                    # Add disabled features for fset and fdel
                    # if they do not exists.
                    if attr.fset is None:
                        attr.setter(
                            feature(name=key, enabled=False)(_dummy_feature))
                    elif not getattr(attr.fset, "_is_feature", None):
                        attr.setter(
                            feature(name=key, enabled=False)(attr.fset))

                    if attr.fdel is None:
                        attr.deleter(
                            feature(name=key, enabled=False)(_dummy_feature))
                    elif not getattr(attr.fdel, "_is_feature", None):
                        attr.deleter(
                            feature(name=key, enabled=False)(attr.fdel))

    @property
    def type(self) -> type:
        """
        The backend (self) type.

        Useful when the backend object is hidden by the manager
        and you need to access to the property objects
        for their features.
        """
        return type(self)

    @property
    def credentials(self) -> Dict[str, object]:
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
            This property is not a feature.
        """
        raise NotImplementedError("Credential property is not implemented")

    @credentials.setter
    def credentials(self, credentials: Dict[str, object]) -> None:
        raise NotImplementedError("Credential property is not implemented")

    @credentials.deleter
    def credentials(self) -> None:
        raise NotImplementedError("Credential property is not implemented")

    # --- Features ---

    # Create group
    @classmethod
    @feature(enabled=False)
    def create(cls,
               path: str,
               from_: str = None,
               credentials: Dict[str, object] = None) -> "VCSBackendBase":
        """
        Create a new repository in the given path.

        Parameters
        ----------
        path : str
            The path where the repository directory will be created.
            The directory must not exists or it must be empty
            as it will be created by this method, or by a call to the VCS.

        from_ : str, optional
            If given, an URL to an existing repository.
            That repository will be cloned into the given path.
            The default is None.

        credentials : Dict[str, object]
            A :attr:`~VCSBackendBase.credentials` like dict.
            Used only if from_ is provided and
            the VCS requires remote authentication.

        Returns
        -------
        VCSBackendBase
            The instance for the given repository path.

        Raises
        ------
        OSError
            If the directory creation fails for any reason
            (see :func:`os.makedirs` for more information).

        ValueError
            If the from_ parameter is not a valid URL.

        NotImplementedError
            If `from_` is specified and
            there is at least one missing feature.

        VCSAuthError
            If the credentials are wrong or missing.
            The directory will be deleted before raising the exception.

        VCSBackendFail
            If something fails in backend construction.
        """

    # Status group
    @property
    @feature(enabled=False, extra={"states": ()})
    def changes(self) -> Sequence[Dict[str, object]]:
        """
        A list of changed files and its states.

        **Get**

        Get a list of all the changes in the repository.
        Each element is a dict that represents the file state.

        --------
        If VCS supports the staging area and
        a path in both the staged and unstaged area,
        that path will have a state for the unstaged area
        and another stage for the staged area.

        .. important::
            Implementations must list the supported state keys
            in the feature extra, under the states key.

        See Also
        --------
        change
            For a detailed description of states.
        """

    @feature(enabled=False, extra={"states": ()})
    def change(self,
               path: str,
               prefer_unstaged: bool = False) -> Optional[Dict[str, object]]:
        """
        Get the state dict associated of path.

        The state dict can have several optional fields:

        path : :class:`str`
            The path to the file.

        kind : :class:`int`
            What change is occurred to the file.
            Possible values are listed in :class:`~ChangedStatus`.

        staged : :class:`bool`
            Indicate if the file is staged or not.

        comment : :class:`str`
            Describe the change.
            Do not confuse it with the commit description.

        .. important::
            Implementations must list the supported state keys
            in the feature extra, under the states key.

            There they can add VCS-dependent keys.

        Parameters
        ----------
        path : str
            The relative path.

        prefer_unstaged : bool
            If True, if the path has both a staged status
            and a unstaged one, the latter will be returned,
            otherwise the first will be returned.
            The default is False.

        Returns
        -------
        Dict[str, object], optional
            The file state or None
            if there is no changes for the given path.
        """

    # Branch group
    @property
    @feature(enabled=False)
    def branch(self) -> str:
        """
        Handle the current repository branch.

        **Get**

        Return the current branch/tag/revision where the local repo is

        **Set**

        Set the current branch to the given one.

        The given branch must exist in the repository.
        Implementations must raises an error if the given branch
        does not exists.
        """

    @branch.setter
    @feature(enabled=False)
    def branch(self, branchname: str) -> None:  # pylint: disable=W0613
        pass

    @property
    @feature(enabled=False)
    def branches(self) -> Sequence[str]:
        """
        A list of branch names.

        **Get**

        Get a list of branches.
        The list may include tags or other revisions that are VCS-specific.
        Also, some of them cannot be used to set
        :attr:`~VCSBackendBase.branch`.

        See Also
        --------
        editable_branches
            For a list of editable and :attr:`~VCSBackendBase.branch`
            allowed branches.

        tags
            For a list of tags.
        """

    @property
    @feature(enabled=False)
    def editable_branches(self) -> Sequence[str]:
        """
        A list of editable branch names.

        An editable branch is a branch where committing is allowed.

        If the VCS do not support this difference,
        :attr:`~VCSBackendBase.branches` is returned instead.

        **Get**
            Get a list of editable branches.

        See Also
        --------
        branches
        """
        return self.branches

    @feature(enabled=False, extra={"empty": False})
    def create_branch(self, branchname: str, empty: bool = False) -> bool:
        """
        Create a new branch.

        Branch creation is possible only if another branch
        with the same name does not exists.

        Parameters
        ----------
        branchname : str
            The branch name.

        empty : bool, optional
            If True, a new empty branch is created,
            otherwise the new branch is created as clone of the current one.
            It is allowed only if the empty extra is True.
            An empty branch must have no files.
            It is not guaranteed that an empty branch has an empty history.
            The default is False.

        Returns
        -------
        bool
            True if the current branch is now the given one, False otherwise.
        """

    @feature(enabled=False)
    def delete_branch(self, branchname: str) -> bool:
        """
        Delete an existing branch.

        Branch deletion is possible only if
        the following conditions are satisfied:

        - The current branch must be different compared to the current one.
        - Should be a local branch (removing a remote branch
          or a non-editable branch depends on both the VCS
          and the implementation and can cause weird behaviours
          or unwanted exceptions).

        Parameters
        ----------
        branchname : str
            The branch name.

        Returns
        -------
        bool
            True if the given branch was existed before calling this and
            now it is deleted, False otherwise.
        """

    # Stage-unstage group
    @feature(enabled=False)
    def stage(self, path: str) -> bool:
        """
        Set the given path state to staged.

        Parameters
        ----------
        path : str
            The path to add to the stage area.

        Returns
        -------
        True if the path is staged (or the file is already staged),
        False otherwise.
        """

    @feature(enabled=False)
    def unstage(self, path: str) -> bool:
        """
        Clear the given path state to be staged.

        Parameters
        ----------
        path : str
            The path to add to the unstage area.

        Returns
        -------
        True if the path is unstaged (or the file is already unstaged),
        False otherwise.
        """

    @feature(enabled=False)
    def stage_all(self) -> bool:
        """
        Set all the unstaged paths to staged.

        Returns
        -------
        True if there are no unstaged file left, False otherwise.
        """

    @feature(enabled=False)
    def unstage_all(self) -> bool:
        """
        Set all the staged paths to unstaged.

        Returns
        -------
        True if there are no staged file left, False otherwise.
        """

    # Remote group
    @feature(enabled=False)
    def commit(self, message: str, is_path: Optional[bool] = None) -> bool:
        """
        Commit current changes.

        If the VCS supports the staging area,
        only the staged changes are included in the commit,

        Parameters
        ----------
        message : str
            The commit message or the path to that.

        is_path : bool
            Specify if the given message parameter is a path or not.
            By default is None, that let this method to decide.

        Returns
        -------
        True if the commit was done, False otherwise.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
        """

    @feature(enabled=False)
    def fetch(self, sync: bool = False) -> Tuple[int, int]:
        """
        Scan the current local branch to get commit status.

        The method main purpose (unlike, for example, git fetch)
        is not to syncronize to the server,
        but give a comparison between local revision and
        the remote one.

        Parameters
        ----------
        sync : bool, optional
            If True and the VCS supports it, syncronize the local
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
            However, the return value should be processed in any case.
        """

    @feature(enabled=False)
    def pull(self, fetch: bool = True) -> bool:  # pylint: disable=W0613
        """
        Get latest revision from remote.

        Parameters
        ----------
        fetch : bool, optional
            If True, do a fetch with sync=True before pulling,
            otherwise do nothing. The default is True.

        Returns
        -------
        True if the pull was done correcly and there are no commits to pull,
        False otherwise.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
        """

    @feature(enabled=False)
    def push(self) -> bool:
        """
        Get latest revision from remote.

        Returns
        -------
        True if the push was done correctly and there are no commits to push,
        False otherwise.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
        """

    # Undo group

    @feature(enabled=False)
    def undo_commit(self, commits: int = 1) -> Optional[Dict[str, object]]:
        """
        Undo a commit or some of them.

        Parameters
        ----------
        commits : int, optional
            The number of commit to undo. The default is 1.

        Returns
        -------
        Dict[str, object]
            Only if history is supported.
            The commit attributes.
            If commits > 1, the returned commit is the last one.

        Raises
        ------
        ValueError
            If the commit parameter is less than 1

        None
            If there are no commits in the branch or the undo fails.
        """

    @feature(enabled=False)
    def undo_change(self, path: str) -> bool:
        """
        Undo a change in the given path.

        If the VCS provides a staging area,
        only the unstaged changes are touched.

        Parameters
        ----------
        path : str
            The path to undo.
            Can be a directory, but the real effectiveness of
            it depends on the underlying VCS.

        Returns
        -------
        True if there are no changes for the specified path, False otherwise.

        See Also
        --------
        undo_change_all
        unstage
        """

    @feature(enabled=False)
    def undo_change_all(self) -> bool:
        """
        Undo all the changes.

        If the VCS provides a staging area,
        only the unstaged changes are touched.

        Returns
        -------
        True if there are no changes for the specified path, False otherwise.

        See Also
        --------
        undo_change
        unstage_all
        """

    # history group
    @feature(enabled=False, extra={"attrs": ()})
    def get_last_commits(self,
                         commits: int = 1) -> Sequence[Dict[str, object]]:
        """
        Get a list of old commits and its attributes.

        The attributes dict can have several optional fields
        (all of them optional):

        id : :class:`str`
            An unique identifier of the commit.

        title : :class:`str`
            The commit title. Used only if the VCS make a dinstiction
            between the title and the description body.

        description : :class:`str`
            The commit description.

        content : :class:`str`
            The commit message with bot title and description.
            Specified only if title is defined.

        author_name : :class:`str`
            The author's name. Used only if the VCS track
            both name and username or the VCS do not support
            usernames as identifier.

        author_username : :class:`str`
            The author's username.
            Implementation should remove any prefix or suffix
            (`@` for example).

        author_email : :class:`str`
            The author's email.

        commit_date : :class:`datetime.datetime`
            The date when the commit is done.
            Must be UTC.

        .. important::
            Implementations must list the supported attributes keys
            in the feature extra, under the attrs key.

            There they can add VCS-dependent keys.

        If :attr:`~VCSBackendBase.branch` is supported,
        then the commits returned are related
        to the current branch.

        Parameters
        ----------
        commits : int, optional
            The number of commits to get. The default is 1.

        Raises
        ------
        ValueError
            If the commits parameter is less than 1

        Returns
        -------
        list of Dict[str, object]
            The commits.
        """

    @property
    @feature(enabled=False, extra={"branch": False})
    def tags(self) -> Sequence[str]:
        """
        A list of revision labels.

        If the VCS allows to view a tag as a pseudo branch,
        so you can set it as current through
        the :attr:`VCSBackendBase.branch` attribute.
        That support is specified by the `branch` extra key.

        **Get**

        Get a list of labels.
        """


class VCSBackendManager(object):
    """Automatic backend selector and repository manager."""

    __slots__ = (
        "_backends",
        "_backend",
        "_to_sort",
        "_broken_backends",
    )

    def __init__(self, repodir: str, *backends: type):
        super().__init__()

        self._backends = {}
        self._broken_backends = []
        self._to_sort = set()
        self._backend = None

        for backend in backends:
            self.register_backend(backend)

        self.repodir = repodir

    def __getattr__(self, name: str) -> object:
        """Get attributes from the backend."""
        if name == "_backend":
            # Prevent stack overflow on Windows
            raise AttributeError("'{}' object has no attribute '{}'".format(
                type(self).__name__, name))

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
    def vcs_types(self) -> Sequence[str]:
        """A list of available VCS types."""
        return tuple(self._backends)

    @property
    def create_vcs_types(self) -> Sequence[str]:
        """
        A list of available VCS types that have at least one backend
        that supports :meth:`~VCSBackendBase.clone`.
        """
        types = []
        for vcs, backends in self._backends.items():
            if any(x.create.enabled for x in backends):
                types.append(vcs)
        return types

    @property
    def repodir(self) -> Optional[str]:
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
            broken = []
            self.sort_backends()
            for backends in itertools.zip_longest(*self._backends.values()):
                for backend in backends:
                    if backend is not None:
                        try:
                            selected_backend = backend(path)
                        except VCSBackendFail as ex:
                            # TODO: complete error formatting
                            # traceback.print_exception(VCSBackendFail, ex,
                            #                           ex.__traceback__)
                            errors.append(ex)
                        except Exception:
                            broken.append(backend)
                        else:
                            break
                else:
                    continue
                break

            if selected_backend is None:
                raise VCSError(
                    "Valid backend not found for the given directory")

            self._backend = selected_backend

    def create_with(self, vcs_type: str, *args, **kwargs) -> bool:
        """
        Do a clone operation with the given type.

        Parameters
        ----------
        vcs_type : str
            The VCS type.
            Must be one of :attr:`VCSBackendManager.create_vcs_types.`
        *args, **kwargs
            Parameters passed to :meth:`~VCSBackendBase.clone`.

        Returns
        -------
        bool
            True if the clone operation is done successfully, False otherwise.

        Raises
        ------
        NotImplementedError
            If there is no VCSs that supports :meth:`~VCSBackendBase.clone`
            completely.

        Warnings
        --------
        If any error, caused by bad arguments given to
        :meth:`~VCSBackendBase.clone`, is raised by the backend,
        it will be propagated to the caller.

        See Also
        --------
        create_vcs_types
            For a list of vcs types that supports clone.
        """
        if vcs_type not in self.create_vcs_types:
            raise NotImplementedError(
                "The VCS type {} does not support clone.".format(vcs_type))

        for backend in filter(lambda x: x.create.enabled,
                              self._backends[vcs_type]):
            try:
                inst = backend.create(*args, **kwargs)
            except (OSError, ValueError, VCSAuthError) as ex:
                # Reraise good exceptions to caller
                raise ex
            except (NotImplementedError, VCSBackendFail):
                # Skip any backend that does not have
                # all the required features.
                pass
            except Exception:
                # Suppress other exceptions
                # Should be reported (e.g. with logging)
                self._broken_backends.append(backend)
            else:
                self._backend = inst
                return True
        return False

    def register_backend(self, backend: typing.Type[VCSBackendBase]) -> None:
        """
        Register a VCSBackendBase subclass.

        The given type will be used in the backend selection.

        Parameters
        ----------
        backend : Type[VCSBackendBase]
            The VCSBackendBase subclass.
        """
        if backend not in self._broken_backends:
            vcsname = backend.VCSNAME.lower()
            if vcsname in self._backends:
                if backend not in self._backends:
                    self._backends[vcsname].append(backend)
                    self._to_sort.add(vcsname)
            else:
                self._backends[vcsname] = [backend]

    def safe_check(
        self, feature_name: Union[str, Sequence[str]]
    ) -> Optional[Callable[..., object]]:
        """
        Check in a safe manner if a feature is enabled.

        Unlike direct check, this method controls if the feature
        can be checked or not.

        Parameters
        ----------
        feature_name : str or tuple of str.
            The feature to check.
            Can be a string if the feature is a method
            or a tuple of 2 strings if the feature is a property operation
            (get, set, del).

        Returns
        -------
        bool
            True if the feature can be checked and
            its enabled attribute is True, False otherwise.
        """
        if self.repodir is None:
            return None

        is_property = False
        if isinstance(feature_name, str):
            feature_inst = getattr(self._backend, feature_name, None)
        else:
            is_property = True
            feature_name, operation, *_ = feature_name

            if operation in ("fget", "fset", "fdel"):
                # Nothing to do
                pass
            elif operation in ("get", "getter"):
                operation = "fget"
            elif operation in ("set", "setter"):
                operation = "fset"
            elif operation in ("del", "deleter"):
                operation = "fdel"
            else:
                raise ValueError("Unknown operation {}".format(operation))

            feature_inst = getattr(
                getattr(
                    type(self._backend),
                    feature_name,
                    None,
                ),
                operation,
            )

        if (getattr(feature_inst, "_is_feature", False)
                and feature_inst.enabled):
            if is_property:
                return partial(feature_inst, self._backend)
            return feature_inst
        return None

    # Debug API
    def force_use(self, backend: type, path: str) -> None:
        """
        Force the usage of the given backend.

        This method bypass the backends priority system and
        the internal error handling,
        so it should be used for debugging purposes only.
        Also, this method never registers the given backend.
        """
        self._backend = backend(path)

    def sort_backends(self) -> None:
        """Sort backends by feature implemented."""
        if self._to_sort:
            for vcsname in self._to_sort:
                backends = self._backends[vcsname]
                backends.sort(
                    key=lambda backend: sum(
                        backend.check(group, all=False)
                        for group in backend.GROUP_MAPPING),
                    reverse=True,
                )

            self._to_sort.clear()

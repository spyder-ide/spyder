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
import builtins
import typing

# Local imports
from .errors import VCSError, VCSBackendFail

_generic_func = typing.Callable[..., object]


def feature(
    name: str = None,
    enabled: bool = True,
    extra: typing.Optional[typing.Dict[object, object]] = None,
) -> _generic_func:
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

    def _decorator(func: _generic_func) -> _generic_func:
        if name is not None:
            # Set the new function name
            func.__name__ = name
        func.enabled = enabled
        func.extra = extra
        func._is_feature = True
        return func

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
    all the method for VCS operations raises a :class:`~VCSUnexpectedError`
    and all the properties raises :class:`~VCSPropertyError`.

    If any requisite stopped working
    (e.g. executable removed or module unrecoverable failure),
    a :class:`~VCSBackendFail` exception will be raised.
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
    GROUPS_MAPPING: typing.Dict[str, typing.Sequence[typing.Union[typing.Tuple[
        str, str], str]]] = {
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
                "create_branch",
                "delete_branch",
            ),
            "diff": (),
            "stage-unstage": (
                "stage",
                "unstage",
                "stage_all",
                "unstage_all",
                "undo_stage",
            ),
            "commit": ("commit", "undo_commit"),
            "remote": ("fetch", "push", "pull"),
            "undo":
            ("undo_commit", "undo_stage", "undo_change", "undo_change_all"),
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
        :meth:`~VCSBackendBase.undo_stage`
            Unstage a file (same as :meth:`~VCSBackendBase.unstage`)

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

    REQUIRED_CREDENTIALS: typing.Sequence[str] = None
    """
    The required keys for credentials.

    If this value is non-zero, credentials are suppored.

    .. warning::
        Since some VCS does not have a simple way to check
        if credentials are necessary for the current repository (notably git),
        the only way to know that is trying to do the operation
        and catch the VCSAuthError,
        then ask/get the credentials and retry the operation.
    """

    # --- Non-features ---
    @classmethod
    def check(cls, group: str, all: bool = False) -> typing.Union[int, bool]:
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
                featurename: typing.Union[typing.Tuple[str, str],
                                          str]) -> object:
            if isinstance(featurename, str):
                feature = getattr(cls, featurename, None)
            elif len(featurename) > 1:
                # Only the first and the second element are considered
                feature = getattr(getattr(cls, featurename[0], None),
                                  featurename[1], None)
            else:
                feature = None

            if (feature is None or getattr(feature, "_is_feature", False)):
                raise TypeError("Invalid feature name {}".format(featurename))

            return feature

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

                    # if getattr(cls, attr.__name__, None) is not None:
                    #     print("Attribute", attr.__name__, "overriden")
                    setattr(cls, attr.__name__, attr)

    @property
    def type(self) -> type:
        """
        The backend (self) type.

        Useful when the backend object is hidden by the manager
        and you need to access to properties features.
        """
        return type(self)

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
            This property is not a feature.
        """
        raise NotImplementedError("Credential property is not implemented")

    @credentials.setter
    def credentials(self, credentials: typing.Dict[str, object]) -> None:
        raise NotImplementedError("Credential property is not implemented")

    @credentials.deleter
    def credentials(self) -> None:
        raise NotImplementedError("Credential property is not implemented")

    # --- Features ---

    # Create group
    @classmethod
    @feature(enabled=False)
    def create(
            cls,
            path: str,
            from_: str = None,
            credentials: typing.Dict[str, object] = None) -> "VCSBackendBase":
        """
        Create a new repository in the given path.

        Parameters
        ----------
        path : str
            The path where the repository directory will be created.
            The directory must not exists as it will be created by this method,
            or by a call to the VCS.

        from_ : str, optional
            An URL to an existing repository.
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

        NotImplementedError
            If `from_` is specified and
            there is at least one missing feature.

        VCSAuthError
            If the credentials are wrong or missing.
            The directory will be deleted before raising the exception.
        """

    # Status group
    @property
    @feature(enabled=False, extra={"states": ()})
    def changes(self) -> typing.Sequence[typing.Dict[str, object]]:
        """
        A list of changed files and its states.

        **Get**

        Get a list of all the changes in the repository.
        Each element is a dict that represents the file state.

        .. warning::
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
    def change(
        self,
        path: str,
        prefer_unstaged: bool = False,
    ) -> typing.Optional[typing.Dict[str, object]]:
        """
        Get the state dict associated of path.

        The state dict can have several optional fields (all of them optional):

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
            If True, if the path has both the staged status
            and the unstaged one, the latter will be returned,
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
    def branches(self) -> typing.Sequence[str]:
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
    def editable_branches(self) -> typing.List[str]:
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

    @feature(enabled=False)
    def create_branch(self,
                      branchname: str,
                      from_current: bool = False) -> bool:
        """
        Create a new branch.

        Branch creation is possible only if another branch
        with the same name does not exists.

        Parameters
        ----------
        branchname : str
            The branch name.

        from_current : bool, optional
            If True, the new branch is created as clone of the current one,
            otherwise a new empty branch is created.
            The default is False.

        Returns
        -------
        bool
            True if the current branch is the given one, False otherwise.
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
            True if the given branch was existed, False otherwise.
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
    def commit(self,
               message: str,
               is_path: typing.Optional[bool] = None) -> bool:
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
    def fetch(self, sync: bool = False) -> typing.Tuple[int, int]:
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
        bool
            True if the pull was done correcly.
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
        True if the push was done correctly and there is no commits to pull,
        False otherwise.

        Raises
        ------
        VCSAuthError
            When authentication to the remote server is required and
            wrong credentials were given.
        """

    # Undo group
    @feature(enabled=False)
    def undo_stage(self, path: str) -> bool:
        """
        Unstage a file.

        Parameters
        ----------
        path : str
            The path to remove from the stage area.

        Returns
        -------
        True if the path is unstaged (or the file is already unstaged),
        False otherwise.

        See Also
        --------
        unstage
        """

    @feature(enabled=False)
    def undo_commit(
        self,
        commits: int = 1,
    ) -> typing.Optional[typing.Dict[str, object]]:
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

        undo_stage
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

        undo_stage
        """

    # history group
    @feature(enabled=False, extra={"attrs": ()})
    def get_last_commits(
        self,
        commits: int = 1,
    ) -> typing.Sequence[typing.Dict[str, object]]:
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
    def tags(self) -> typing.Sequence[str]:
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
        "_sorted",
    )

    def __init__(self, repodir: str, *backends: type):
        super().__init__()
        self._backends = list(backends)
        self._backend = None
        self._sorted = True
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
            self.sort_backends()
            for backend in self._backends:
                try:
                    selected_backend = backend(path)
                except VCSBackendFail as ex:
                    # TODO: complete error formatting
                    import traceback
                    traceback.print_exception(VCSBackendFail, ex,
                                              ex.__traceback__)
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
        if backend not in self._backends:
            self._backends.append(backend)
            self._sorted = False

    # Debug API
    def force_use(self, backend: type, path: str) -> None:
        """
        Force the usage of the given backend.

        This method bypass the backends priority system and
        the internal error handling,
        so it should be used for debugging purposes only.
        Also, this method never registers the backend.
        """
        self._backend = backend(path)

    def sort_backends(self) -> None:
        """Sort backends by feature implemented."""
        if not self._sorted:
            new_backends = []
            names = {}
            for backend in self._backends:
                if backend.VCSNAME not in names:
                    names[backend.VCSNAME] = [backend]
                else:
                    names[backend.VCSNAME].append(backend)

            for name, backends in names.copy().items():
                if len(backends) == 1:
                    new_backends.append(backends[0])
                    del names[name]

            if names:
                for backends in names.values():
                    backend.sort(
                        key=lambda backend: sum(
                            backend.check(group, all=False)
                            for group in backend.GROUP_MAPPING),
                        reverse=True,
                    )

                for name in sorted(names):
                    new_backends.extend(names[name])

            self._sorted = True

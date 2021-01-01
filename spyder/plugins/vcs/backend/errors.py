#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""A collection of VCS exceptions."""

# Standard library imports
from typing import Dict, Callable, Optional, Sequence


class VCSError(Exception):
    """
    The base for all VCS errors.

    Parameters
    ----------
    error : str, optional
        The formatted error. Should respect the spec guidelines if any.
        The default is None.
    raw_error : str, optional
        The raw error message returned by the VCS. The default is None.
    """
    # HINT: No specification define the message format.

    __slots__ = ("error", "raw_error")

    def __init__(self,
                 error: Optional[str] = None,
                 raw_error: Optional[str] = None):
        args = []
        if error:
            args.append(error)
        if raw_error:
            args.append(raw_error)

        super().__init__(*args)
        self.error = error
        self.raw_error = raw_error


class VCSFeatureError(VCSError):
    """
    Raised when a generic error happens in the feature.

    Currently, only non-property features can raise this error.

    Parameters
    ----------
    feature : Callable[..., object]
        The feature where the error occurred.
        Must be a valid feature decorated with :func:`~.api.feature

    See Also
    --------
    VCSPropertyError
    """

    __slots__ = ("feature", )

    def __init__(self, *args: object, feature: Callable[..., object],
                 **kwargs: Optional[str]):
        super().__init__(*args, **kwargs)
        self.feature = feature

    def retry(self, *args, **kwargs) -> object:
        """Call again the feature with given parameters."""
        if self.feature.enabled:
            return self.feature(*args, **kwargs)
        raise NotImplementedError("The feature {} is disabled.".format(
            self.feature.__name__))


class VCSPropertyError(VCSError):
    """
    Raised when an operation on a property fails.

    Parameters
    ----------
    name : str
        The property name, this usually refers
        to the property name in the backend.
    operation : str
        The operation done to the property.
        Accepted values are: get, set, del.

    Notes
    -----
    This error is never raised by methods.

    See Also
    --------
    VCSFeatureError
    """

    __slots__ = ("name", "operation")

    def __init__(self, name: str, operation: str, *args: object,
                 **kwargs: Optional[str]):
        super().__init__(*args, **kwargs)
        self.name = name
        operation = operation.lstrip("f")
        if operation in ("get", "set", "del"):
            self.operation = operation


class VCSBackendFail(VCSError):
    """
    Raised when a backend cannot initialize itself.

    This exception is raised for missing dependencies
    and missing repository in folder.

    Parameters
    ----------
    directory : str
        The directory given to the backend.
    backend_type : type
        The backend that raise the error
    programs : list, optional
        A list of missing executables. The default is an empty list.
    modules : list, optional
        A list of missing python modules. The default is an empty list.

        .. note::
            Module does refer to actual import-style module name,
            not pip package name.

    is_valid_repository : bool, optional
        A flag indicating if the directory contains a valid repository.
        The default is True.
    """
    __slots__ = ("directory", "backend_type", "programs", "modules",
                 "is_valid_repository")

    def __init__(self,
                 directory: str,
                 backend_type: type,
                 *args: object,
                 programs: Sequence[str] = (),
                 modules: Sequence[str] = (),
                 is_valid_repository: bool = True,
                 **kwargs: Optional[str]):

        super().__init__(*args, **kwargs)
        self.directory = directory
        self.backend_type = backend_type
        self.programs = programs
        self.modules = modules
        self.is_valid_repository = is_valid_repository

    @property
    def missing_dependencies(self) -> bool:
        """Check if there are missing dependencies."""
        return any((self.programs, self.modules))


class VCSAuthError(VCSError):
    """
    Raised when an authentication error occurred.

    Parameters
    ----------
    required_credentials : str
        The credentials that the backend requires.
    credentials_callback : str
        The function to call when :meth:`VCSAuthError.set_credentials`
        is called.
    credentials : Dict[str, object], optional
        The credentials that causes the error.

    """

    __slots__ = ("required_credentials", "_credentials",
                 "_credentials_callback")

    def __init__(self,
                 required_credentials: Sequence[str],
                 credentials_callback: Callable[..., None],
                 *args: object,
                 credentials: Optional[Dict[str, object]] = None,
                 **kwargs: Optional[str]):

        super().__init__(*args, **kwargs)
        self.required_credentials = required_credentials
        self._credentials = credentials
        self._credentials_callback = credentials_callback

    @property
    def credentials(self) -> Dict[str, object]:
        """
        A proxy for required backend credentials.

        This property contains the required credentials fields.

        You can set to it update the backend credentials.

        It is preferred to interact with this property instead of
        using the :attr:`.VCSBackendBase.credentials` property directly.

        Raises
        ------
        ValueError
            When setting, if one of the required field is missing.
        """
        return {
            key: self._credentials.get(key)
            for key in self.required_credentials
        }

    @credentials.setter
    def credentials(self, credentials: Dict[str, object]) -> None:
        new_cred = {}
        for key in self.required_credentials:
            if credentials.get(key) is None:
                raise ValueError("Missing field {}".format(key))
            new_cred[key] = credentials[key]
        self._credentials_callback(new_cred)

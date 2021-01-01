#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Some mixins for the backends."""

# Standard library imports
from typing import Dict, Optional

# Third party imports
import keyring

# Local imports
from .errors import VCSAuthError


class CredentialsKeyringMixin(object):
    """
    An helper mixin to manage credential with keyring.

    Steps to implement and use it properly:

    - change the SCOPENAME.
      For core backends, "spyder-vcs-VCSNAME" syntax is preferred.
      For third party backends, "spyder_PLUGINNAME-vcs-VCSNAME" is preferred.
    - Implement the credential_context property (see its docs).

    - If you want to set the credentials the first time:
      Pass the desidered type of credentials:
      username-password, email-password, token.

    - If you want to get stored credentials:
      Pass the incompleted credentials:
      Username only, email only or token=None.
      You can also use the helpers get_user_credentials and get_token.

    After implemetation you have a ready-to-use credentials implementation.

    .. note::
        This mixin is not strictly respecting the backends
        specifications in the credentials property.
        In particular, the setter can raise VCSAuthError
        if there is no credentials stored in the keyring.
    """

    SCOPENAME = "spyder-vcs-changeit"

    def __init__(self, *args: object, **kwargs: object):
        super().__init__(*args, **kwargs)
        self.__internal_credentials: Dict[str, object] = {}

    @property
    def credential_context(self) -> str:
        """
        Get the credential context of the repo.

        A possible context can be the remote URL.

        This property is read only.
        """
        raise NotImplementedError("Credential context must be defined")

    @property
    def credentials(self) -> Dict[str, object]:
        if self.__internal_credentials:
            return self.__internal_credentials.copy()
        return {}

    @credentials.setter
    def credentials(self, credentials: Dict[str, object]) -> None:
        if not credentials:
            self.__internal_credentials = {}
            return

        # check token
        token = credentials.get("token", False)

        if token is None:
            # get last token
            i = self._get_last_token()
            if i == -1:
                raise VCSAuthError(
                    credentials={"token", None},
                    credentials_callback=lambda x: setattr(
                        self, "credentials", x),
                    required_credentials=self.REQUIRED_CREDENTIALS,
                    error="No token is found for {}".format(
                        self.credential_context),
                )

            token = keyring.get_password(self._get_servicename(True), str(i))

            self.__internal_credentials = dict(token=token)

        elif token:
            # set token

            keyring.set_password(self._get_servicename(True),
                                 str(self._get_last_token()),
                                 credentials.get("token"))

            self.__internal__context = dict(token=token)
        else:
            # check email or password
            if credentials.get("username"):
                user, type_ = credentials.get("username"), "username"
            elif credentials.get("email"):
                user, type_ = credentials.get("email"), "email"
            else:
                raise ValueError("No valid credentials type given.\n"
                                 "Valid types are: "
                                 "username-password, email-password and token")

            password = credentials.get("password")
            if credentials.get("password"):
                keyring.set_password(self._get_servicename(), user, password)
                self.__internal_credentials = {
                    type_: user,
                    "password": password
                }

            else:
                password = keyring.get_password(self._get_servicename(), user)
                if password:
                    self.__internal_credentials = {
                        type_: user,
                        "password": password
                    }
                else:
                    raise VCSAuthError(
                        credentials={type_: user},
                        credentials_callback=lambda x: setattr(
                            self, "credentials", x),
                        required_credentials=self.REQUIRED_CREDENTIALS,
                        error="The given {} is not found for {}".format(
                            type_, self.credential_context))

    @credentials.deleter
    def credentials(self) -> None:
        credentials = self.__internal_credentials
        try:
            if credentials:
                # remove last token
                if credentials.get("token"):
                    i = self._get_last_token() - 1
                    if i != -1:
                        keyring.delete_password(self._get_servicename(),
                                                str(i))
                else:
                    user = (credentials.get("username")
                            or credentials.get("email"))
                    if user:
                        keyring.delete_password(self._get_servicename(), user)
        except keyring.errors.KeyringError:
            # suppress any keyring error
            pass

        self.__internal_credentials = {}

    # utils
    def get_user_credentials(self,
                             username: Optional[str] = None,
                             email: Optional[str] = None) -> Dict[str, object]:
        """
        A shorthand for username and email credentials initialization.

        Parameters
        ----------
        username : str, optional
            The username to use to get the corresponding password.
            The default is None.
        email : str, optional
            The email to use to get the corresponding password.
            The default is None.

        Returns
        -------
        dict
            The credentials.
        """
        self.credentials = dict(username=username, email=email)
        return self.credentials

    def get_token(self) -> Dict[str, object]:
        """
        A shorthand for token credentials initialization.

        Returns
        -------
        dict
            The credentials.
        """
        self.credentials = dict(token=None)
        return self.credentials

    def _get_servicename(self, is_token: bool = False) -> str:
        return "{} @ {} {}".format(self.SCOPENAME, self.credential_context,
                                   "token" if is_token else "")

    def _get_last_token(self) -> int:
        i = 0
        while True:
            try:
                token = keyring.get_password(self._get_servicename(True),
                                             str(i))
            except keyring.errors.KeyringError:
                break
            else:
                if not token:
                    break
                i += 1
        return i

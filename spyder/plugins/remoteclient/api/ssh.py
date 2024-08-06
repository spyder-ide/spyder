# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import logging
from typing import Optional

from asyncssh import SSHClientConnection, SSHClient
from asyncssh.auth import PasswordChangeResponse
from asyncssh.public_key import KeyPairListArg

from spyder.api.translations import _
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
)

_logger = logging.getLogger(__name__)


class SpyderSSHClient(SSHClient):
    def __init__(self, client):
        self.client = client

    def connection_made(self, conn: SSHClientConnection) -> None:
        """Called when a connection is made

        This method is called as soon as the TCP connection completes.
        The `conn` parameter should be stored if needed for later use.

        :param conn:
            The connection which was successfully opened
        :type conn: :class:`SSHClientConnection`

        """
        if self.client._plugin:
            self.client._plugin.sig_connection_established.emit(
                self.client.config_id
            )

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Called when a connection is lost or closed

        This method is called when a connection is closed. If the
        connection is shut down cleanly, *exc* will be `None`.
        Otherwise, it will be an exception explaining the reason for
        the disconnect.

        :param exc:
            The exception which caused the connection to close, or
            `None` if the connection closed cleanly
        :type exc: :class:`Exception`

        """
        if self.client._plugin:
            self.client._plugin.sig_connection_lost.emit(self.client.config_id)
        self.client._handle_connection_lost(exc)

    def debug_msg_received(
        self, msg: str, lang: str, always_display: bool
    ) -> None:
        """A debug message was received on this connection

        This method is called when the other end of the connection sends
        a debug message. Applications should implement this method if
        they wish to process these debug messages.

        :param msg:
            The debug message sent
        :param lang:
            The language the message is in
        :param always_display:
            Whether or not to display the message
        :type msg: `str`
        :type lang: `str`
        :type always_display: `bool`

        """
        _logger.debug(f"Debug message received: {msg}")

    def auth_completed(self) -> None:
        """Authentication was completed successfully

        This method is called when authentication has completed
        successfully. Applications may use this method to create
        whatever client sessions and direct TCP/IP or UNIX domain
        connections are needed and/or set up listeners for incoming
        TCP/IP or UNIX domain connections coming from the server.
        However, :func:`create_connection` now blocks until
        authentication is complete, so any code which wishes to
        use the SSH connection can simply follow that call and
        doesn't need to be performed in a callback.

        """

    def public_key_auth_requested(self) -> Optional[KeyPairListArg]:
        """Public key authentication has been requested

        This method should return a private key corresponding to
        the user that authentication is being attempted for.

        This method may be called multiple times and can return a
        different key to try each time it is called. When there are
        no keys left to try, it should return `None` to indicate
        that some other authentication method should be tried.

        If client keys were provided when the connection was opened,
        they will be tried before this method is called.

        If blocking operations need to be performed to determine the
        key to authenticate with, this method may be defined as a
        coroutine.

        :returns: A key as described in :ref:`SpecifyingPrivateKeys`
                  or `None` to move on to another authentication
                  method

        """

        return None  # pragma: no cover

    def password_auth_requested(self) -> Optional[str]:
        """Password authentication has been requested

        This method should return a string containing the password
        corresponding to the user that authentication is being
        attempted for. It may be called multiple times and can
        return a different password to try each time, but most
        servers have a limit on the number of attempts allowed.
        When there's no password left to try, this method should
        return `None` to indicate that some other authentication
        method should be tried.

        If a password was provided when the connection was opened,
        it will be tried before this method is called.

        If blocking operations need to be performed to determine the
        password to authenticate with, this method may be defined as
        a coroutine.

        :returns: A string containing the password to authenticate
                  with or `None` to move on to another authentication
                  method

        """

        return None  # pragma: no cover

    def password_change_requested(
        self, prompt: str, lang: str
    ) -> PasswordChangeResponse:
        """A password change has been requested

        This method is called when password authentication was
        attempted and the user's password was expired on the
        server. To request a password change, this method should
        return a tuple or two strings containing the old and new
        passwords. Otherwise, it should return `NotImplemented`.

        If blocking operations need to be performed to determine the
        passwords to authenticate with, this method may be defined
        as a coroutine.

        By default, this method returns `NotImplemented`.

        :param prompt:
            The prompt requesting that the user enter a new password
        :param lang:
            The language that the prompt is in
        :type prompt: `str`
        :type lang: `str`

        :returns: A tuple of two strings containing the old and new
                  passwords or `NotImplemented` if password changes
                  aren't supported

        """

        return NotImplemented  # pragma: no cover

    def password_changed(self) -> None:
        """The requested password change was successful

        This method is called to indicate that a requested password
        change was successful. It is generally followed by a call to
        :meth:`auth_completed` since this means authentication was
        also successful.

        """

    def password_change_failed(self) -> None:
        """The requested password change has failed

        This method is called to indicate that a requested password
        change failed, generally because the requested new password
        doesn't meet the password criteria on the remote system.
        After this method is called, other forms of authentication
        will automatically be attempted.

        """

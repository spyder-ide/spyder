# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.remoteclient.api.manager
=======================================

Remote Client Plugin API Manager.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import typing
from abc import abstractmethod
from functools import partial

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.translations import _
from spyder.api.utils import ABCMeta
from spyder.config.base import get_debug_level
from spyder.plugins.remoteclient.api.modules.base import (
    JupyterAPI,
)
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
    RemoteClientLog,
)

if typing.TYPE_CHECKING:
    from spyder.plugins.remoteclient.api.modules.base import (
        SpyderBaseJupyterAPIType,
    )
    from spyder.plugins.remoteclient.plugin import RemoteClient


class SpyderRemoteAPILoggerHandler(logging.Handler):
    def __init__(self, client, *args, **kwargs):
        self._client = client
        super().__init__(*args, **kwargs)

        log_format = "%(message)s &#8212; %(asctime)s"
        formatter = logging.Formatter(log_format, datefmt="%H:%M:%S %d/%m/%Y")
        self.setFormatter(formatter)

    def emit(self, record):
        self._client._plugin.sig_client_message_logged.emit(
            RemoteClientLog(
                id=self._client.config_id,
                message=self.format(record),
                level=record.levelno,
                created=record.created,
            )
        )


class SpyderRemoteAPIManagerBase(metaclass=ABCMeta):
    """Class to manage a remote server and its APIs."""

    REGISTERED_MODULE_APIS: typing.ClassVar[
        dict[str, type[SpyderBaseJupyterAPIType]]
    ] = {
        JupyterAPI.__qualname__: JupyterAPI,
    }

    def __init__(
        self,
        conf_id: str,
        options: dict[str, typing.Any],
        _plugin: typing.Optional[RemoteClient] = None,
    ):
        self._config_id = conf_id
        self.options = options
        self._plugin = _plugin

        self.__create_events()

        self.__installing_server = False
        self.__starting_server = False
        self.__connection_task: asyncio.Task | None = None

        # For logging
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}({self.config_id})"
        )

        if not get_debug_level():
            self.logger.setLevel(logging.DEBUG)

        if self._plugin is not None and not self.logger.hasHandlers():
            self.logger.addHandler(SpyderRemoteAPILoggerHandler(self))

    @AsyncDispatcher(loop="asyncssh", early_return=False)
    async def __create_events(self):
        self.__server_installed = asyncio.Event()
        self.__starting_event = asyncio.Event()
        self.__abort_requested = asyncio.Event()
        self.__lock = asyncio.Lock()

    def _emit_connection_status(self, status: str, message: str):
        if self._plugin is not None:
            self._plugin.sig_connection_status_changed.emit(
                ConnectionInfo(
                    id=self.config_id, status=status, message=message
                )
            )

    def _emit_version_mismatch(self, version: str):
        if self._plugin is not None:
            self._plugin.sig_version_mismatch.emit(self.config_id, version)

    @property
    def server_started(self):
        return self.__starting_event.is_set() and not self.__starting_server

    @property
    def connected(self) -> bool:
        """Check if a connection is currently established."""
        return (
            self.__connection_task is not None
            and self.__connection_task.done()
            and not self.__connection_task.cancelled()
            and not self.__connection_task.exception()
            and self.__connection_task.result() is True
        )

    @property
    def is_connecting(self) -> bool:
        """Check if a connection attempt is ongoing."""
        return (
            self.__connection_task is not None
            and not self.__connection_task.done()
        )

    @property
    def config_id(self):
        """Return the configuration ID"""
        return self._config_id

    @property
    def server_name(self):
        if self._plugin is None:
            return None
        return self._plugin.get_server_name(self.config_id)

    @property
    @abstractmethod
    def server_url(self):
        """Return Jypyter server URL."""
        msg = "This method should be implemented in the derived class"
        raise NotImplementedError(msg)

    @property
    @abstractmethod
    def api_token(self):
        """Return Jupyter server API token."""
        msg = "This method should be implemented in the derived class"
        raise NotImplementedError(msg)

    async def close(self):
        """Closes the remote server and the SSH connection."""
        self._emit_connection_status(
            ConnectionStatus.Stopping,
            _("We're closing the connection. Please be patient"),
        )

        await self.stop_remote_server()
        await self.close_connection()

    def _handle_connection_lost(self, exc: Exception | None = None):
        if self.connected:
            self.__connection_task = None
        self.__starting_event.clear()
        self._port_forwarder = None
        if exc:
            self.logger.error(
                "Connection to %s was lost",
                self.server_name,
                exc_info=exc,
            )
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("The connection was lost"),
            )

    # ---- Connection and server management
    async def connect_and_install_remote_server(self) -> bool:
        """Connect to the remote server and install the server."""
        if await self.create_new_connection():
            return await self.install_remote_server()

        return False

    async def connect_and_start_server(self) -> bool:
        """Connect to the remote server and start the server."""
        if await self.create_new_connection():
            return await self.start_remote_server()

        return False

    async def ensure_connection_and_server(self) -> bool:
        """Ensure connected and the remote server is running."""
        if self.connected and not self.server_started:
            return await self.ensure_server()

        if not self.connected:
            return await self.connect_and_ensure_server()

        return True

    async def connect_and_ensure_server(self) -> bool:
        """Connect and ensure the remote server is running."""
        if await self.create_new_connection() and not self.server_started:
            return await self.ensure_server()

        return bool(self.server_started)

    async def ensure_connection(self) -> bool:
        """Ensure the SSH connection is open."""
        if self.connected:
            return True

        return await self.create_new_connection()

    async def ensure_server(self, *, check_installed: bool = True) -> bool:
        """Ensure remote server is installed and running."""
        if self.server_started:
            return True

        if check_installed and not await self.ensure_server_installed():
            return False

        return await self.start_remote_server()

    async def start_remote_server(self):
        """Start remote server."""
        if self.__starting_server:
            await self.__starting_event.wait()
            return self.server_started

        self.__starting_server = True
        self._emit_connection_status(
            ConnectionStatus.Starting, _("Starting Spyder remote services")
        )
        try:
            if await self._start_remote_server():
                self.__starting_event.set()
                # emit signal that connection and server are established
                if self._plugin:
                    self._plugin.sig_connection_established.emit(
                        self.config_id
                    )
                return True
        finally:
            self.__starting_server = False

        self.__starting_event.clear()
        return False

    @abstractmethod
    async def _start_remote_server(self):
        """Start remote server."""
        msg = "This method should be implemented in the derived class"
        raise NotImplementedError(msg)

    @abstractmethod
    async def ensure_server_installed(self) -> bool:
        """Check remote server version."""
        msg = "This method should be implemented in the derived class"
        raise NotImplementedError(msg)

    async def install_remote_server(self) -> bool:
        """Install remote server."""
        if self.__installing_server:
            await self.__server_installed.wait()
            return True

        self.__installing_server = True
        try:
            if await self._install_remote_server():
                self.__server_installed.set()
                return True
        finally:
            self.__installing_server = False

        self.__server_installed.clear()
        return False

    @abstractmethod
    async def _install_remote_server(self):
        """Install remote server."""
        msg = "This method should be implemented in the derived class"
        raise NotImplementedError(msg)

    async def create_new_connection(self) -> bool:
        """Create a new connection, supporting user abort."""
        if self.connected:
            self.logger.debug(
                "Atempting to create a new connection with an existing for %s",
                self.server_name,
            )
            await self.close_connection()

        async with self.__lock:
            if self.__connection_task is not None:
                return self.connected

            self._emit_connection_status(
                ConnectionStatus.Connecting,
                _("We're establishing the connection. Please be patient"),
            )

            self.__abort_requested.clear()
            self.__connection_task = asyncio.create_task(
                self._create_new_connection()
            )
            abort_task = asyncio.create_task(self.__abort_requested.wait())

            await asyncio.wait(
                [self.__connection_task, abort_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # User aborted
            if self.__abort_requested.is_set():
                self.__connection_task.cancel()
                abort_task.cancel()
                self.__connection_task = None

                self.logger.debug("Connection attempt aborted by user")
                self._emit_connection_status(
                    ConnectionStatus.Inactive,
                    _("The connection attempt was cancelled"),
                )

                return False

            try:
                # Connection completed
                if await self.__connection_task:
                    self._emit_connection_status(
                        ConnectionStatus.Connected,
                        _("The connection was successfully established"),
                    )
                    return True
            except BaseException as error:
                # Log any error
                self.logger.error(
                    "Error creating a new connection for {}. The error was:"
                    "<br>{}".format(self.server_name, str(error))
                )

            # Cancel and reset connection tasks to allow retries after errors
            self.__connection_task.cancel()
            self.__connection_task = None
            abort_task.cancel()

            # Report that the connection failed
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("There was an error establishing the connection"),
            )

            return False

    async def abort_connection(self):
        """Abort an ongoing connection attempt."""
        if self.is_connecting:
            self.__abort_requested.set()

    @abstractmethod
    async def _create_new_connection(self) -> bool:
        """Create a new connection to the remote server machine."""
        msg = "This method should be implemented in the derived class"
        raise NotImplementedError(msg)

    async def stop_remote_server(self):
        """Close remote server."""
        if not self.server_started:
            self.logger.warning(
                f"Remote server is not running for {self.server_name}"
            )
            return False

        if not self.connected:
            self.logger.error("SSH connection is not open")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("The SSH connection is not open"),
            )
            return False

        # bug in jupyterhub, need to send SIGINT twice
        self.logger.debug(f"Stopping remote server for {self.server_name}")
        try:
            async with self.get_jupyter_api() as jupyter:
                await jupyter.shutdown_server()
        except Exception as err:
            self.logger.error(
                "Error stopping remote server. The error was:<br>{}".format(
                    str(err)
                )
            )

        self.__starting_event.clear()
        self.logger.info(
            f"Remote server process closed for {self.server_name}"
        )
        return True

    @abstractmethod
    async def close_connection(self):
        """Close SSH connection."""
        msg = "This method should be implemented in the derived class"
        raise NotImplementedError(msg)

    def _reset_connection_established(self):
        """Reset the connection status."""
        self.__connection_task = None

    @staticmethod
    def get_free_port():
        """Request a free port from the OS."""
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    # ---- API Management
    @staticmethod
    def register_api(
        kclass: type[SpyderBaseJupyterAPIType]
    ) -> type[SpyderBaseJupyterAPIType]:
        """Register a REST API class."""
        SpyderRemoteAPIManagerBase.REGISTERED_MODULE_APIS[
            kclass.__qualname__
        ] = kclass
        return kclass

    def get_api(
        self,
        api: str | type[SpyderBaseJupyterAPIType]
    ) -> typing.Callable[..., SpyderBaseJupyterAPIType]:
        """Get a registered REST API class."""
        if isinstance(api, type):
            api = api.__qualname__

        api_class = SpyderRemoteAPIManagerBase.REGISTERED_MODULE_APIS.get(api)
        if api_class is None:
            raise ValueError(f"API {api} is not registered")

        return partial(api_class, manager=self)

    def get_jupyter_api(self) -> JupyterAPI:
        return JupyterAPI(manager=self)

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

import json

import aiohttp
import yarl
from packaging.version import Version

from spyder.api.translations import _
from spyder.plugins.remoteclient import (
    SPYDER_REMOTE_MAX_VERSION,
    SPYDER_REMOTE_MIN_VERSION,
)
from spyder.plugins.remoteclient.api.manager.base import (
    SpyderRemoteAPIManagerBase,
)
from spyder.plugins.remoteclient.api.modules.base import SpyderRemoteAPIError
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionStatus,
    JupyterHubClientOptions,
)


class SpyderRemoteJupyterHubAPIManager(SpyderRemoteAPIManagerBase):
    """Class to manage a remote server and its APIs."""

    def __init__(self, conf_id, options: JupyterHubClientOptions, _plugin=None):
        super().__init__(conf_id, options, _plugin)

        self._server_url = None
        self._user_name = None
        self._session: aiohttp.ClientSession = None

    @property
    def api_token(self):
        return self.options["token"]

    @property
    def server_url(self):
        return self.hub_url / f"hub/api/user/{self._user_name}/server/spyder"

    @property
    def hub_url(self):
        return yarl.URL(self.options["url"])

    async def _start_remote_server(self):
        """Start remote server."""
        if not self.connected:
            self.logger.error("SSH connection is not open")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("JupyterHub is not connected"),
            )
            return False

        async with self._session.post(
            f"user/{self._user_name}/server/spyder",
        ) as response:
            if not response.ok:
                self.logger.error(
                    "Error starting remote server: %s", response.status,
                )
                self._emit_connection_status(
                    ConnectionStatus.Error,
                    _("Error starting the remote server"),
                )
                return False
            if response.status == 201:
                self._emit_connection_status(
                    ConnectionStatus.Active,
                    _("The connection was established successfully"),
                )
                return True

        async with self._session.get(
            f"user/{self._user_name}/server/spyder/progress",
        ) as response:
            if not response.ok:
                self.logger.error(
                    "Error getting remote server progress: %s", response.status,
                )
                self._emit_connection_status(
                    ConnectionStatus.Error,
                    _(
                        "There was an error when trying to get the remote server "
                        "information"
                    ),
                )
                return False

            async for line in response.content:
                line = line.decode("utf8", "replace")
                if line.startswith("data:"):
                    ready = json.loads(line.split(":", 1)[1])["ready"]

        if ready:
            self._emit_connection_status(
                ConnectionStatus.Active,
                _("The connection was established successfully"),
            )
            return True

        self.logger.error(
            "Error starting remote server: %s", response.status,
        )
        self._emit_connection_status(
            ConnectionStatus.Error,
            _("Error starting the remote server"),
        )
        return False

    async def ensure_server_installed(self) -> bool:
        """Check remote server version."""
        if not self.connected:
            self.logger.error("Connection is not open")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("JupyterHub is not connected"),
            )
            return False

        try:
            async with self.get_jupyter_api() as jupyter_api:
                version = await jupyter_api.get_plugin_version()
        except SpyderRemoteAPIError:
            self.logger.exception(
                "Error getting remote server version. "
                "The server might not be installed"
            )
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("Error connecting to the remote server"),
            )
            return False

        if Version(version) >= Version(SPYDER_REMOTE_MAX_VERSION):
            self.logger.error(
                f"Server version mismatch: {version} is greater than "
                f"the maximum supported version {SPYDER_REMOTE_MAX_VERSION}"
            )
            self._emit_version_mismatch(version)
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("Error connecting to the remote server"),
            )
            return False

        if Version(version) < Version(SPYDER_REMOTE_MIN_VERSION):
            self.logger.warning(
                f"Server version mismatch: {version} is lower than "
                f"the minimum supported version {SPYDER_REMOTE_MIN_VERSION}. "
                f"A more recent version will be installed."
            )
            return await self.install_remote_server()

        self.logger.info(f"Supported Server version: {version}")

        return True

    async def _install_remote_server(self):
        self.logger.error(
            "Remote server installation is not supported for JupyterHub"
        )
        return False

    async def _create_new_connection(self) -> bool:
        if self.connected:
            self.logger.debug(
                f"Atempting to create a new connection with an existing for "
                f"{self.server_name}"
            )
            await self.close_connection()

        self._emit_connection_status(
            ConnectionStatus.Connecting,
            _("We're establishing the connection. Please be patient"),
        )

        self.logger.debug("Loggin to jupyterhub at %s", self.hub_url)

        self._session = aiohttp.ClientSession(
            self.hub_url / "hub/api/",
            headers={"Authorization": f"token {self.api_token}"},
        )

        user_data = None
        try:
            async with self._session.get("user") as response:
                if response.ok:
                    user_data = await response.json()
        except aiohttp.ClientError:
            self.logger.exception("Error connecting to JupyterHub")
            return False

        if user_data is None:
            self.logger.error(
                "Error connecting to JupyterHub: %s", response.status,
            )
            return False

        if "servers" not in user_data["scopes"]:
            self.logger.error(
                "This user does not have permission to start a server. "
                "Please check your JupyterHub configuration."
            )
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("Insufficient permissions"),
            )
            return False

        self._user_name = user_data["name"]

        self.logger.info("Successfully connected to JupyterHub")
        return True

    async def close_connection(self):
        """Close SSH connection."""
        if not self.connected:
            self.logger.debug("Connection is not open")
            return

        await self._session.close()
        self._session = None
        self.logger.info("Connection closed")
        self._reset_connection_stablished()
        self._emit_connection_status(
            ConnectionStatus.Inactive,
            _("The connection was closed successfully"),
        )

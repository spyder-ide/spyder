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
    SPYDER_PLUGIN_NAME
)
from spyder.plugins.remoteclient.api.manager.base import (
    SpyderRemoteAPIManagerBase,
)
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionStatus,
    JupyterHubClientOptions,
)


class SpyderRemoteJupyterHubAPIManager(SpyderRemoteAPIManagerBase):
    """Class to manage a remote JupyterHub server and its APIs."""

    def __init__(
        self, conf_id, options: JupyterHubClientOptions, _plugin=None
    ):
        super().__init__(conf_id, options, _plugin)

        self._server_url = None
        self._user_name = None
        self._session: aiohttp.ClientSession = None

    @property
    def api_token(self):
        return self.options["token"]

    @property
    def server_url(self):
        return self.hub_url / f"user/{self._user_name}/spyder/"

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
            f"hub/api/users/{self._user_name}/servers/spyder",
        ) as response:
            if response.status in {201, 400}:
                if await self.check_server_version():
                    self._emit_connection_status(
                        ConnectionStatus.Active,
                        _("Spyder remote services are active"),
                    )
                    return True
                return False

            if not response.ok:
                try:
                    jupyter_error = await response.json()
                    self.logger.error(
                        "Unexpected jupyterhub response when starting "
                        "spyder's jupyter server: [%s]: %s",
                        jupyter_error["status"],
                        jupyter_error["message"],
                    )
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    self.logger.exception(
                        "Unexpected jupyterhub response when starting "
                        "spyder's jupyter server: [%s]: %s",
                        response.status,
                        await response.text(),
                    )
                self._emit_connection_status(
                    ConnectionStatus.Error,
                    _("Error starting the remote server"),
                )
                return False

        async with self._session.get(
            f"hub/api/users/{self._user_name}/servers/spyder/progress",
        ) as response:
            if not response.ok:
                self.logger.error(
                    "Error getting remote server progress: %s",
                    response.status,
                )
                self._emit_connection_status(
                    ConnectionStatus.Error,
                    _(
                        "There was an error when trying to get the remote "
                        "server information"
                    ),
                )
                return False

            async for line in response.content:
                line = line.decode("utf8", "replace")
                if line.startswith("data:"):
                    ready = json.loads(line.split(":", 1)[1])["ready"]

        if ready and await self.check_server_version():
            self._emit_connection_status(
                ConnectionStatus.Active,
                _("Spyder remote services are active"),
            )
            return True

        self.logger.error(
            "Spyder remote server was unable to start, please check the "
            "JupyterHub logs for more information",
        )
        self._emit_connection_status(
            ConnectionStatus.Error, _("Error starting the remote server"),
        )
        return False

    async def ensure_server_installed(self) -> bool:
        """Assume the server is installed."""
        return True

    async def check_server_version(self) -> bool:
        """Check remote server version."""
        if not self.connected:
            self.logger.error("Connection is not open")
            self._emit_connection_status(
                ConnectionStatus.Error,
                _("JupyterHub is not connected"),
            )
            return False

        async with self._session.get(
            f"user/{self._user_name}/spyder/{SPYDER_PLUGIN_NAME}/version",
        ) as response:
            if not response.ok:
                try:
                    jupyter_error = await response.json()
                    self.logger.error(
                        "Unexpected jupyterhub response when getting "
                        "%s version: [%s]: %s",
                        SPYDER_PLUGIN_NAME,
                        jupyter_error["status"],
                        jupyter_error["message"],
                    )
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    self.logger.exception(
                        "Error starting remote server: [%s]: %s",
                        response.status,
                        await response.text(),
                    )

                self._emit_connection_status(
                    ConnectionStatus.Error,
                    _("Error starting the remote server"),
                )
                return False

            version = await response.text()

        if Version(version) >= Version(SPYDER_REMOTE_MAX_VERSION):
            self.logger.error(
                "Server version mismatch: %s is greater than the maximum "
                "supported version %s",
                version,
                SPYDER_REMOTE_MAX_VERSION,
            )
            self._emit_version_mismatch(version)
            self._emit_connection_status(
                status=ConnectionStatus.Error,
                message=_("Error staring the remote server"),
            )
            return False

        if Version(version) < Version(SPYDER_REMOTE_MIN_VERSION):
            self.logger.warning(
                "Server version mismatch: %s is lower than the minimum "
                "supported version %s. A more recent version will be "
                "installed.",
                version,
                SPYDER_REMOTE_MIN_VERSION,
            )
            return await self.install_remote_server()

        self.logger.info("Supported Server version: %s", version)

        return True

    async def _install_remote_server(self):
        self.logger.error(
            "Remote server installation is not supported for JupyterHub",
        )
        return False

    async def _create_new_connection(self) -> bool:
        """Create a new SSH connection."""
        self.logger.debug("Connecting to jupyterhub at %s", self.hub_url)

        self._session = aiohttp.ClientSession(
            self.hub_url,
            headers={"Authorization": f"token {self.api_token}"},
        )

        user_data = None
        response = None
        try:
            async with self._session.get("hub/api/user") as response:
                if response.ok:
                    user_data = await response.json()
        except aiohttp.client_exceptions.ClientConnectionError as error:
            self.logger.error(
                "Error connecting to JupyterHub. The error was:<br>{}".format(
                    str(error)
                )
            )

        if user_data is None:
            if response is not None:
                self.logger.error(
                    "Error connecting to JupyterHub with code {}, which "
                    "corresponds to a {} reason".format(
                        response.status, response.reason
                    ),
                )

            # Close and reset sessions for discarded connections to allow
            # retries after connection info errors
            await self._session.close()
            self._session = None

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
        self._reset_connection_established()
        self._emit_connection_status(
            ConnectionStatus.Inactive,
            _("The connection was closed successfully"),
        )

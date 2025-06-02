# -*- coding: utf-8 -*-
#
# Copyright © 2025 Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations

from http import HTTPStatus

import aiohttp

from spyder.plugins.remoteclient import SPYDER_PLUGIN_NAME
from spyder.plugins.remoteclient.api.manager.base import (
    SpyderRemoteAPIManagerBase,
)
from spyder.plugins.remoteclient.api.modules.base import (
    SpyderBaseJupyterAPI,
    SpyderRemoteAPIError,
)


@SpyderRemoteAPIManagerBase.register_api
class SpyderRemoteEnvironAPI(SpyderBaseJupyterAPI):
    """
    API for managing the environment variables on the remote server.

    Raises
    ------
    SpyderRemoteAPIError
        If the API call fails.
    aiohttp.ClientResponseError
        If the API call fails with a client error.
    """

    base_url = SPYDER_PLUGIN_NAME + "/environ"

    async def _raise_for_status(self, response: aiohttp.ClientResponse):
        return response.raise_for_status()

    async def get(self, name: str, default: str | None = None) -> str | None:
        """
        Get the environment variable value for the given name.

        Parameters
        ----------
        name : str
            The name of the environment variable.

        Returns
        -------
        str
            The value of the environment variable.

        Raises
        ------
        SpyderRemoteAPIError
            If the API call fails.
        """
        try:
            async with self.session.get(self.api_url / name) as response:
                return await response.text()
        except aiohttp.ClientResponseError as e:
            if e.status == HTTPStatus.NOT_FOUND:
                return default
            msg = f"Failed to get environment variable '{name}': {e}"
            raise SpyderRemoteAPIError(msg) from e

    async def set(self, name: str, value: str) -> None:
        """
        Set the environment variable value for the given name.

        Parameters
        ----------
        name : str
            The name of the environment variable.
        value : str
            The value of the environment variable.
        """
        await self.session.post(self.api_url / name, data={"value": value})

    async def delete(self, name: str) -> None:
        """
        Delete the environment variable for the given name.

        Parameters
        ----------
        name : str
            The name of the environment variable.
        """
        await self.session.delete(self.api_url / name)

    async def to_dict(self) -> dict[str, str]:
        """
        Get the environment variables as a dictionary.

        Returns
        -------
        dict[str, str]
            The environment variables as a dictionary.
        """
        async with self.session.get(self.api_url) as response:
            return await response.json()

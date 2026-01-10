# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations

import asyncio
import logging
import typing
from abc import abstractmethod

import aiohttp
import yarl

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.utils import ABCMeta, abstract_attribute
from spyder.plugins.remoteclient import SPYDER_PLUGIN_NAME

if typing.TYPE_CHECKING:
    from spyder.plugins.remoteclient.api.manager.base import (
        SpyderRemoteAPIManagerBase,
    )


SpyderBaseJupyterAPIType = typing.TypeVar(
    "SpyderBaseJupyterAPIType", bound="SpyderBaseJupyterAPI"
)


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60  # seconds
VERIFY_SSL = True


class SpyderRemoteAPIError(Exception):
    """
    Exception for errors related to Spyder remote client API.
    """
    ...


class SpyderRemoteSessionClosed(SpyderRemoteAPIError):
    """
    Exception for errors related to a closed session.
    """
    ...


class SpyderBaseJupyterAPI(metaclass=ABCMeta):
    """
    Base class for Jupyter API plugins.

    This class must be subclassed to implement the API for a specific
    Jupyter extension. It provides a connection method and context manager.
    """

    request_timeout = REQUEST_TIMEOUT
    verify_ssl = VERIFY_SSL

    @abstract_attribute
    def base_url(self) -> str: ...

    @property
    def server_id(self):
        """Server ID or configuration ID of the remote server."""
        return self.manager.config_id

    @property
    def server_name(self):
        """Server name of the remote server."""
        return self.manager.server_name

    def __init__(self, manager: SpyderRemoteAPIManagerBase):
        self.manager = manager
        self._session: typing.Optional[aiohttp.ClientSession] = None

    @property
    def session(self) -> aiohttp.ClientSession:
        error_message = (
            "Session is closed, please ensure that an active session is open "
            "before calling this method.\n\n"
            "You can open a session using a context manager:\n"
            f"with {type(self).__name__}() as api:\n"
            "    ...\n\n"
            "Or by calling the connect method:\n"
            f"api = {type(self).__name__}()\n"
            "await api.connect()"
        )
        if self._session is None or self._session.closed:
            raise SpyderRemoteSessionClosed(error_message)

        return self._session

    @session.setter
    def session(self, session: aiohttp.ClientSession):
        self._session = session

    @property
    def server_url(self) -> yarl.URL:
        return yarl.URL(self.manager.server_url)

    @property
    def api_url(self) -> yarl.URL:
        return self.server_url / self.base_url

    @property
    def closed(self):
        if self._session is None:
            return True
        return self._session.closed

    async def connect(self):
        # Default connect method which ensures a connection via the manager.
        if not await AsyncDispatcher(
            loop="asyncssh",
            return_awaitable=True,
        )(self.manager.ensure_connection_and_server)():
            raise RuntimeError("Failed to connect to the server")
        if not self.closed:
            return
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"token {self.manager.api_token}"},
            connector=aiohttp.TCPConnector(
                ssl=None if self.verify_ssl else False
            ),
            raise_for_status=self._raise_for_status,
            timeout=aiohttp.ClientTimeout(total=self.request_timeout),
        )

    async def __aenter__(self):
        await self.connect()
        return self

    async def close(self):
        await self.session.close()

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    @abstractmethod
    async def _raise_for_status(self, response: aiohttp.ClientResponse): ...

    @staticmethod
    def retry(
        num_retries=5,
        delay=1,
        check: typing.Callable[..., bool] = lambda x: bool(x),
        catch: typing.Union[type[Exception], None] = Exception,
    ):
        """
        Retry method decorator for async functions.

        Parameters
        ----------
        num_retries: int
            Number of retries to attempt.
        delay: int
            Delay in seconds between retries.
        check: callable
            Function to check if the return value is valid.
        exception: Exception, None. Defaults to Exception.
            If provided, catch this exception and retry.

        Returns
        -------
        wrapper: callable
            Decorated function.

        Example
        -------
        ```
        @retry(num_retries=5, delay=1, check=lambda x: x is not None)
        async def my_function():
            return await some_async_function()
        ```
        """
        if catch is None:

            async def run_try(tryth, func, *args, **kwargs):
                ret = await func(*args, **kwargs)
                if check(ret):
                    return ret
                logger.debug(
                    f"retry={tryth} delay={delay} invalid return={ret}"
                )
                await asyncio.sleep(delay)
        else:

            async def run_try(tryth, func, *args, **kwargs):
                try:
                    ret = await func(*args, **kwargs)
                except catch as err:
                    logger.debug(f"retry={tryth} delay={delay} error={err}")
                    await asyncio.sleep(delay)
                else:
                    if check(ret):
                        return ret
                    logger.debug(
                        f"retry={tryth} delay={delay} invalid return={ret}"
                    )
                    await asyncio.sleep(delay)

        def decorator(func):
            async def wrapper(*args, **kwargs):
                for tryth in range(num_retries - 1):
                    return await run_try(tryth, func, *args, **kwargs)

                return await func(*args, **kwargs)

            return wrapper

        return decorator


class JupyterAPI(SpyderBaseJupyterAPI):
    base_url = "api"

    def __init__(self, manager: SpyderRemoteAPIManagerBase, verify_ssl=True):
        """
        For JupyterAPI, the manager.server_url is expected to be the notebook
        URL.
        """
        super().__init__(manager)
        self.verify_ssl = verify_ssl

    async def _raise_for_status(self, response: aiohttp.ClientResponse):
        response.raise_for_status()

    # ---- Jupyter Server REST API
    @SpyderBaseJupyterAPI.retry()
    async def create_kernel(self, kernel_spec=None, spyder_kernel=True):
        data = {}
        if spyder_kernel:
            data["spyder_kernel"] = True

        if kernel_spec := (
            kernel_spec
            or self.manager.options.get("default_kernel_spec")
        ):
            data["name"] = kernel_spec

        async with self.session.post(
            self.api_url / "kernels", json=data
        ) as response:
            return await response.json()

    async def list_kernel_specs(self):
        async with self.session.get(self.api_url / "kernelspecs") as response:
            return await response.json()

    async def list_kernels(self):
        async with self.session.get(self.api_url / "kernels") as response:
            return await response.json()

    @SpyderBaseJupyterAPI.retry()
    async def get_kernel(self, kernel_id):
        try:
            async with self.session.get(
                self.api_url / "kernels" / kernel_id
            ) as response:
                return await response.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return {}
            else:
                raise e

    async def terminate_kernel(self, kernel_id):
        async with self.session.delete(
            self.api_url / "kernels" / kernel_id
        ) as response:
            if response.status == 204:
                logger.debug(f"deleted kernel={kernel_id} for jupyter")
                return True
            else:
                return False

    async def interrupt_kernel(self, kernel_id):
        async with self.session.post(
            self.api_url / "kernels" / kernel_id / "interrupt"
        ) as response:
            if response.status == 204:
                logger.debug(f"interrupted kernel={kernel_id} for jupyter")
                return True
            else:
                return False

    async def restart_kernel(self, kernel_id):
        async with self.session.post(
            self.api_url / "kernels" / kernel_id / "restart"
        ) as response:
            if response.status == 200:
                logger.debug(f"restarted kernel={kernel_id} for jupyter")
                return True
            else:
                return False

    async def shutdown_server(self):
        async with self.session.post(self.api_url / "shutdown") as response:
            if response.status == 200:
                logger.debug("shutdown jupyter server")
                return True
            else:
                return False

    async def get_plugin_version(self):
        """Get the version of the Jupyter server."""
        try:
            async with self.session.get(
                self.server_url / SPYDER_PLUGIN_NAME / "version",
            ) as response:
                return await response.text()
        except aiohttp.ClientError as e:
            msg = "Failed to get plugin version"
            raise SpyderRemoteAPIError(msg) from e

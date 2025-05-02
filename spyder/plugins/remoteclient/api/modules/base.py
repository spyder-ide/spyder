# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
from abc import abstractmethod
import logging
import time
import typing
import asyncio
import re

import yarl
import aiohttp

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.utils import ABCMeta, abstract_attribute

if typing.TYPE_CHECKING:
    from spyder.plugins.remoteclient.api.manager import SpyderRemoteAPIManager


SpyderBaseJupyterAPIType = typing.TypeVar(
    "SpyderBaseJupyterAPIType", bound="SpyderBaseJupyterAPI"
)


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 5  # seconds
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


async def token_authentication(api_token, verify_ssl=True):
    return aiohttp.ClientSession(
        headers={"Authorization": f"token {api_token}"},
        connector=aiohttp.TCPConnector(ssl=None if verify_ssl else False),
    )


async def basic_authentication(hub_url, username, password, verify_ssl=True):
    session = aiohttp.ClientSession(
        headers={"Referer": str(yarl.URL(hub_url) / "hub" / "api")},
        connector=aiohttp.TCPConnector(ssl=None if verify_ssl else False),
    )

    await session.post(
        yarl.URL(hub_url) / "hub" / "login",
        data={
            "username": username,
            "password": password,
        },
    )
    return session


async def keycloak_authentication(hub_url, username, password, verify_ssl=True):
    session = aiohttp.ClientSession(
        headers={"Referer": str(yarl.URL(hub_url) / "hub" / "api")},
        connector=aiohttp.TCPConnector(ssl=None if verify_ssl else False),
    )

    response = await session.get(yarl.URL(hub_url) / "hub" / "oauth_login")
    content = await response.content.read()
    auth_url = re.search('action="([^"]+)"', content.decode("utf8")).group(1)

    response = await session.post(
        auth_url.replace("&amp;", "&"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "username": username,
            "password": password,
            "credentialId": "",
        },
    )
    return session


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

    def __init__(self, manager: SpyderRemoteAPIManager):
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
            raise RuntimeError("Failed to connect to Jupyter server")
        if not self.closed:
            return
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"token {self.manager.api_token}"},
            connector=aiohttp.TCPConnector(
                ssl=None if self.verify_ssl else False
            ),
            raise_for_status=self._raise_for_status,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
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
        check: typing.Callable[..., bool]=lambda x: bool(x),
        catch: typing.Union[type[Exception], None]=Exception,
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


class JupyterHubAPI(SpyderBaseJupyterAPI):
    base_url = "hub/api"

    def __init__(
        self,
        auth_type="token",
        verify_ssl=True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.auth_type = auth_type
        self.verify_ssl = verify_ssl
        if auth_type == "token":
            self.api_token = kwargs.get("api_token")
        elif auth_type in ("basic", "keycloak"):
            self.username = kwargs.get("username")
            self.password = kwargs.get("password")

    async def connect(self):
        # Override connect to support different auth types
        if not await AsyncDispatcher(
            self.manager.ensure_connection_and_server,
            loop="asyncssh",
            return_awaitable=True,
        )():
            raise RuntimeError("Failed to connect to Jupyter server")
        if not self.closed:
            return
        if self.auth_type == "token":
            self.session = await token_authentication(
                self.api_token, verify_ssl=self.verify_ssl
            )
        elif self.auth_type == "basic":
            self.session = await basic_authentication(
                self.manager.server_url,
                self.username,
                self.password,
                verify_ssl=self.verify_ssl,
            )
            # Upgrade to token-based auth
            self.api_token = await self.create_token(self.username)
            await self.session.close()
            logger.debug("upgrading basic authentication to token authentication")
            self.session = await token_authentication(
                self.api_token, verify_ssl=self.verify_ssl
            )
        elif self.auth_type == "keycloak":
            self.session = await keycloak_authentication(
                self.manager.server_url,
                self.username,
                self.password,
                verify_ssl=self.verify_ssl,
            )
            self.api_token = await self.create_token(self.username)
            await self.session.close()
            logger.debug(
                "upgrading keycloak authentication to token authentication"
            )
            self.session = await token_authentication(
                self.api_token, verify_ssl=self.verify_ssl
            )

    async def _raise_for_status(self, response: aiohttp.ClientResponse):
        response.raise_for_status()

    async def create_token(self, username, token_name=None):
        token_name = token_name or "jhub-client"
        async with self.session.post(
            self.api_url / "users" / username / "tokens",
            json={"note": token_name},
        ) as response:
            logger.debug(f"created token for username={username}")
            token_json = await response.json()
            return token_json["token"]

    async def ensure_user(self, username, create_user=False):
        user = await self.get_user(username)
        if user is None:
            if create_user:
                await self.create_user(username)
            else:
                raise ValueError(
                    f"current username={username} does not exist and "
                    f"create_user={create_user}"
                )
            user = await self.get_user(username)
        return user

    async def get_user(self, username):
        async with self.session.get(
            self.api_url / "users" / username
        ) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                logger.debug(f"username={username} does not exist")
                return None

    async def create_user(self, username):
        async with self.session.post(
            self.api_url / "users" / username
        ) as response:
            if response.status == 201:
                logger.debug(f"created username={username}")
                response_json = await response.json()
                self.api_token = await self.create_token(username)
                return response_json
            elif response.status == 409:
                raise ValueError(f"username={username} already exists")

    async def delete_user(self, username):
        async with self.session.delete(
            self.api_url / "users" / username
        ) as response:
            if response.status == 204:
                logger.debug(f"deleted username={username}")
            elif response.status == 404:
                raise ValueError(
                    f"username={username} does not exist cannot delete"
                )

    async def create_server(self, username, user_options=None):
        user_options = user_options or {}
        async with self.session.post(
            self.api_url / "users" / username / "server", json=user_options
        ) as response:
            logger.debug(
                f"creating cluster username={username} "
                f"user_options={user_options}"
            )
            if response.status == 400:
                raise ValueError(
                    f"server for username={username} is already running"
                )
            elif response.status == 201:
                logger.debug(
                    f"created server for username={username} with "
                    f"user_options={user_options}"
                )
                return True

    async def delete_server(self, username):
        response = await self.session.delete(
            self.api_url / "users" / username / "server"
        )
        logger.debug(f"deleted server for username={username}")
        return response.status

    async def ensure_server(
        self, username, timeout, user_options=None, create_user=False
    ):
        user = await self.ensure_user(username, create_user=create_user)
        if not user.get("server"):
            await self.create_server(username, user_options=user_options)

        start_time = time.time()
        while True:
            user = await self.get_user(username)
            if user.get("server") and user.get("pending") is None:
                # Return a JupyterAPI instance (pointing to the user's notebook server)
                return JupyterAPI(self.manager, verify_ssl=self.verify_ssl)
            await asyncio.sleep(5)
            total_time = time.time() - start_time
            if total_time > timeout:
                logger.error(
                    f"jupyterhub server creation timeout={timeout:.0f} [s]"
                )
                raise TimeoutError(
                    f"jupyterhub server creation timeout={timeout:.0f} [s]"
                )
            logger.debug(
                f"pending spawn polling for seconds={total_time:.0f} [s]"
            )

    async def ensure_server_deleted(self, username, timeout):
        user = await self.get_user(username)
        if user is None:
            return  # user doesn't exist so server can't exist
        start_time = time.time()
        while True:
            server_status = await self.delete_server(username)
            if server_status == 204:
                return
            await asyncio.sleep(5)
            total_time = time.time() - start_time
            if total_time > timeout:
                logger.error(
                    f"jupyterhub server deletion timeout={timeout:.0f} [s]"
                )
                raise TimeoutError(
                    f"jupyterhub server deletion timeout={timeout:.0f} [s]"
                )
            logger.debug(
                f"pending deletion polling for seconds={total_time:.0f} [s]"
            )

    async def info(self):
        async with self.session.get(self.api_url / "info") as response:
            return await response.json()

    async def list_users(self):
        async with self.session.get(self.api_url / "users") as response:
            return await response.json()

    async def list_proxy(self):
        async with self.session.get(self.api_url / "proxy") as response:
            return await response.json()

    async def identify_token(self, token):
        async with self.session.get(
            self.api_url / "authorizations" / "token" / token
        ) as response:
            return await response.json()

    async def get_services(self):
        async with self.session.get(self.api_url / "services") as response:
            return await response.json()

    async def get_service(self, service_name):
        async with self.session.get(
            self.api_url / "services" / service_name
        ) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()

    async def execute_post_service(self, service_name, url="", data=None):
        async with self.session.post(
            self.server_url / "services" / service_name / url, data=data
        ) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()

    async def execute_get_service(self, service_name, url=""):
        async with self.session.get(
            self.server_url / "services" / service_name / url
        ) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()

    async def execute_delete_service(self, service_name, url=""):
        async with self.session.delete(
            self.server_url / "services" / service_name / url
        ) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()


class JupyterAPI(SpyderBaseJupyterAPI):
    base_url = "api"

    def __init__(self, manager: SpyderRemoteAPIManager, verify_ssl=True):
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
        if kernel_spec:
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

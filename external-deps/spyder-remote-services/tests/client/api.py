import uuid
import logging
import time
import asyncio

import yarl
import aiohttp

from client import auth


logger = logging.getLogger(__name__)


class JupyterHubAPI:
    def __init__(self, hub_url, auth_type="token", verify_ssl=True, **kwargs):
        self.hub_url = yarl.URL(hub_url)
        self.api_url = self.hub_url / "hub/api"
        self.auth_type = auth_type
        self.verify_ssl = verify_ssl

        if auth_type == "token":
            self.api_token = kwargs.get("api_token")
        elif auth_type == "basic" or auth_type == "keycloak":
            self.username = kwargs.get("username")
            self.password = kwargs.get("password")

    async def __aenter__(self):
        if self.auth_type == "token":
            self.session = await auth.token_authentication(
                self.api_token, verify_ssl=self.verify_ssl
            )
        elif self.auth_type == "basic":
            self.session = await auth.basic_authentication(
                self.hub_url, self.username, self.password, verify_ssl=self.verify_ssl
            )
            self.api_token = await self.create_token(self.username)
            await self.session.close()
            logger.debug("upgrading basic authentication to token authentication")
            self.session = await auth.token_authentication(
                self.api_token, verify_ssl=self.verify_ssl
            )
        elif self.auth_type == "keycloak":
            self.session = await auth.keycloak_authentication(
                self.hub_url, self.username, self.password, verify_ssl=self.verify_ssl
            )
            self.api_token = await self.create_token(self.username)
            await self.session.close()
            logger.debug("upgrading keycloak authentication to token authentication")
            self.session = await auth.token_authentication(
                self.api_token, verify_ssl=self.verify_ssl
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def ensure_user(self, username, create_user=False):
        user = await self.get_user(username)
        if user is None:
            if create_user:
                await self.create_user(username)
            else:
                raise ValueError(
                    f"current username={username} does not exist and create_user={create_user}"
                )
            user = await self.get_user(username)
        return user

    async def get_user(self, username):
        async with self.session.get(self.api_url / "users" / username) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                logger.info(f"username={username} does not exist")
                return None

    async def create_user(self, username):
        async with self.session.post(self.api_url / "users" / username) as response:
            if response.status == 201:
                logger.info(f"created username={username}")
                response = await response.json()
                self.api_token = await self.create_token(username)
                return response
            elif response.status == 409:
                raise ValueError(f"username={username} already exists")

    async def delete_user(self, username):
        async with self.session.delete(self.api_url / "users" / username) as response:
            if response.status == 204:
                logger.info(f"deleted username={username}")
            elif response.status == 404:
                raise ValueError(f"username={username} does not exist cannot delete")

    async def ensure_server(
        self, username, timeout, user_options=None, create_user=False
    ):
        user = await self.ensure_user(username, create_user=create_user)
        if user["server"] is None:
            await self.create_server(username, user_options=user_options)

        start_time = time.time()
        while True:
            user = await self.get_user(username)
            if user["server"] and user["pending"] is None:
                return JupyterAPI(
                    self.hub_url / "user" / username,
                    self.api_token,
                    verify_ssl=self.verify_ssl,
                )

            await asyncio.sleep(5)
            total_time = time.time() - start_time
            if total_time > timeout:
                logger.error(f"jupyterhub server creation timeout={timeout:.0f} [s]")
                raise TimeoutError(
                    f"jupyterhub server creation timeout={timeout:.0f} [s]"
                )

            logger.info(f"pending spawn polling for seconds={total_time:.0f} [s]")

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
                logger.error(f"jupyterhub server deletion timeout={timeout:.0f} [s]")
                raise TimeoutError(
                    f"jupyterhub server deletion timeout={timeout:.0f} [s]"
                )

            logger.info(f"pending deletion polling for seconds={total_time:.0f} [s]")

    async def create_token(self, username, token_name=None):
        token_name = token_name or "jhub-client"
        async with self.session.post(
            self.api_url / "users" / username / "tokens", json={"note": token_name}
        ) as response:
            logger.info(f"created token for username={username}")
            return (await response.json())["token"]

    async def create_server(self, username, user_options=None):
        user_options = user_options or {}
        async with self.session.post(
            self.api_url / "users" / username / "server", json=user_options
        ) as response:
            logger.info(
                f"creating cluster username={username} user_options={user_options}"
            )
            if response.status == 400:
                raise ValueError(f"server for username={username} is already running")
            elif response.status == 201:
                logger.info(
                    f"created server for username={username} with user_options={user_options}"
                )
                return True

    async def delete_server(self, username):
        response = await self.session.delete(
            self.api_url / "users" / username / "server"
        )
        logger.info(f"deleted server for username={username}")
        return response.status

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
        async with self.session.get(self.api_url / "services" / service_name) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()
            
    async def execute_post_service(self, service_name, url='', data=None):
        async with self.session.post(self.hub_url / "services" / service_name / url, data=data) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()
    
    async def execute_get_service(self, service_name, url=''):
        async with self.session.get(self.hub_url / "services" / service_name / url) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()
    
    async def execute_delete_service(self, service_name, url=''):
        async with self.session.delete(self.hub_url / "services" / service_name / url) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()
    



class JupyterAPI:
    def __init__(self, notebook_url, api_token, verify_ssl=True):
        self.api_url = yarl.URL(notebook_url) / "api"
        self.api_token = api_token
        self.verify_ssl = verify_ssl

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"token {self.api_token}"},
            connector=aiohttp.TCPConnector(ssl=None if self.verify_ssl else False),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def create_kernel(self, kernel_spec=None):
        data = {"kernel_spec": kernel_spec} if kernel_spec else None

        async with self.session.post(self.api_url / "kernels", json=data) as response:
            data = await response.json()
            logger.info(
                f'created kernel_spec={kernel_spec} kernel={data["id"]} for jupyter'
            )
            return data

    async def list_kernel_specs(self):
        async with self.session.get(self.api_url / "kernelspecs") as response:
            return await response.json()

    async def list_kernels(self):
        async with self.session.get(self.api_url / "kernels") as response:
            return await response.json()

    async def ensure_kernel(self, kernel_spec=None):
        kernel_specs = await self.list_kernel_specs()
        if kernel_spec is None:
            kernel_spec = kernel_specs["default"]
        else:
            available_kernel_specs = list(kernel_specs["kernelspecs"].keys())
            if kernel_spec not in kernel_specs["kernelspecs"]:
                logger.error(
                    f"kernel_spec={kernel_spec} not listed in available kernel specifications={available_kernel_specs}"
                )
                raise ValueError(
                    f"kernel_spec={kernel_spec} not listed in available kernel specifications={available_kernel_specs}"
                )

        kernel_id = (await self.create_kernel(kernel_spec=kernel_spec))["id"]
        return kernel_id, JupyterKernelAPI(
            self.api_url / "kernels" / kernel_id,
            self.api_token,
            verify_ssl=self.verify_ssl,
        )

    async def get_kernel(self, kernel_id):
        async with self.session.get(self.api_url / "kernels" / kernel_id) as response:
            if response.status == 404:
                return None
            elif response.status == 200:
                return await response.json()

    async def delete_kernel(self, kernel_id):
        async with self.session.delete(
            self.api_url / "kernels" / kernel_id
        ) as response:
            if response.status == 404:
                raise ValueError(
                    f"failed to delete kernel_id={kernel_id} does not exist"
                )
            elif response.status == 204:
                logger.info(f"deleted kernel={kernel_id} for jupyter")
                return True


class JupyterKernelAPI:
    def __init__(self, kernel_url, api_token, verify_ssl=True):
        self.api_url = kernel_url
        self.api_token = api_token
        self.verify_ssl = verify_ssl

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"token {self.api_token}"},
            connector=aiohttp.TCPConnector(ssl=None if self.verify_ssl else False),
        )
        self.websocket = await self.session.ws_connect(self.api_url / "channels")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    def request_execute_code(self, msg_id, username, code):
        return {
            "header": {
                "msg_id": msg_id,
                "username": username,
                "msg_type": "execute_request",
                "version": "5.2",
            },
            "metadata": {},
            "content": {
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": True,
                "stop_on_error": True,
            },
            "buffers": [],
            "parent_header": {},
            "channel": "shell",
        }

    async def send_code(self, username, code, wait=True, timeout=None):
        msg_id = str(uuid.uuid4())

        await self.websocket.send_json(
            self.request_execute_code(msg_id, username, code)
        )

        if not wait:
            return None

        async for msg_text in self.websocket:
            if msg_text.type != aiohttp.WSMsgType.TEXT:
                return False

            # TODO: timeout is ignored

            msg = msg_text.json()

            if "parent_header" in msg and msg["parent_header"].get("msg_id") == msg_id:
                # These are responses to our request
                if msg["channel"] == "iopub":
                    if msg["msg_type"] == "execute_result":
                        return msg["content"]["data"]["text/plain"]
                    elif msg["msg_type"] == "stream":
                        return msg["content"]["text"]
                    # cell did not produce output
                    elif msg["content"].get("execution_state") == "idle":
                        return ""

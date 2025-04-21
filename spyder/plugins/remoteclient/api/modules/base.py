# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import struct
import typing
from abc import abstractmethod
import uuid

import aiohttp
import yarl
import zmq.asyncio

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


class SpyderKernelWSConnector(SpyderBaseJupyterAPI):
    """Bridge a Jupyter kernel <--> WebSocket using the *default* binary protocol.

    A single binary WebSocket frame looks like:

        +------------+------------+------------+-----+---------+-----------+
        | offset_0   | offset_1   | … | offset_N | msg | buffer_0 | …       |
        +------------+------------+------------+-----+---------+-----------+

    where *offset_0* is the position (in bytes) of *msg* from the beginning
    of the frame, and so forth. *msg* itself is a UTF-8 JSON string that
    contains at least the ``"channel"`` key.
    """

    base_url = "api/kernels"

    # ---------------------------------------------------------------------
    # Construction / basic lifecycle
    # ---------------------------------------------------------------------

    def __init__(self, kernel_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kernel_id = kernel_id
        self._websocket: typing.Optional[aiohttp.ClientWebSocketResponse] = None

        self.zmq_ctx: typing.Optional[zmq.asyncio.Context] = None
        self.channel_map: dict[str, zmq.asyncio.Socket] = {}
        self._runner: asyncio.Task = None

    async def _raise_for_status(self, response: aiohttp.ClientResponse):
        response.raise_for_status()

    async def connect(self):
        """Open the HTTP session *and* the kernel WebSocket."""
        await super().connect()

        if self._websocket is not None and not self._websocket.closed:
            return

        self._websocket = await self.session.ws_connect(
            self.api_url / self.kernel_id / "channels", autoping=True
        )

    async def close(self):
        """Gracefully tear down WebSocket and ZMQ resources."""
        if self._runner is not None:
            # Wait for the runner to finish.
            await asyncio.wait_for(self._runner, timeout=1)

        if self._websocket and not self._websocket.closed:
            await self._websocket.close()

        # Close any ZMQ sockets we created.
        for sock in self.channel_map.values():
            with contextlib.suppress(Exception):
                sock.close(linger=0)

        if self.zmq_ctx is not None:
            with contextlib.suppress(Exception):
                self.zmq_ctx.term()

        await super().close()

    @property
    def closed(self) -> bool:
        ws_closed = True if self._websocket is None else self._websocket.closed
        return ws_closed and super().closed

    async def connection_info(
        self,
    ) -> dict:
        """Get the connection information for the kernel."""
        self.zmq_ctx = zmq.asyncio.Context.instance()

        socket_types = {
            "shell": zmq.DEALER,
            "control": zmq.DEALER,
            "stdin": zmq.DEALER,
            "iopub": zmq.SUB,
            "hb": zmq.REQ,
        }
        ip = uuid.uuid4().hex
        ports = {
            "shell_port": 1,
            "iopub_port": 2,
            "stdin_port": 3,
            "hb_port": 4,
            "control_port": 5,
        }

        def endpoint(channel: str) -> str:
            return f"ipc://{ip}-{ports[channel + '_port']}"

        for ch, ztype in socket_types.items():
            sock = self.zmq_ctx.socket(ztype)
            sock.linger = 1000  # ms
            sock.connect(endpoint(ch))
            if ch == "iopub":
                sock.setsockopt(zmq.SUBSCRIBE, b"")
            self.channel_map[ch] = sock

        self._runner = asyncio.create_task(self._run_forever())

        return {
            **ports,
            "ip": ip,
            "transport": "ipc",
        }

    async def _run_forever(self):
        """Bidirectional proxy between WebSocket and ZeroMQ channels."""
        if self._websocket is None or self._websocket.closed:
            raise SpyderRemoteSessionClosed("WebSocket is not open.")
        if not self.channel_map:
            raise RuntimeError("No ZMQ sockets attached - call connect_zmq() first.")

        while not self.closed:
            msg = await self._websocket.receive()

            if msg.type == aiohttp.WSMsgType.BINARY:
                try:
                    parsed = self._parse_protocol(msg.data)
                except Exception as err:
                    logger.exception("[kernel-proxy] Error parsing message: %s", err)
                    continue

                channel = parsed.get("channel")
                if channel not in self.channel_map:
                    logger.warning("[kernel-proxy] Unknown channel %s", channel)
                    continue

                zmq_socket = self.channel_map[channel]

                # Build the zmq multipart list - first part is delimiter b"", second JSON.
                zmq_msg = [b"", json.dumps(parsed).encode("utf-8")] + parsed["buffers"]

                # Channels that expect REPLY.
                if channel in {"shell", "stdin", "control", "heartbeat"}:
                    await zmq_socket.send_multipart(zmq_msg)
                    zmq_reply = await zmq_socket.recv_multipart()

                    if len(zmq_reply) < 2:
                        logger.error("[kernel-proxy] Malformed reply on %s", channel)
                        continue

                    try:
                        reply_dict = json.loads(zmq_reply[1].decode("utf-8"))
                    except json.JSONDecodeError as e:
                        logger.exception("[kernel-proxy] JSON decode error: %s", e)
                        continue

                    reply_buffers = zmq_reply[2:] if len(zmq_reply) > 2 else []

                    ws_frame = self._build_protocol(
                        channel=reply_dict.get("channel", channel),
                        header=reply_dict.get("header", {}),
                        parent_header=reply_dict.get("parent_header", {}),
                        metadata=reply_dict.get("metadata", {}),
                        content=reply_dict.get("content", {}),
                        buffers=reply_buffers,
                    )
                    await self._websocket.send_bytes(ws_frame)

                elif channel == "iopub":
                    # iopub is *publish* - nothing to send back, but still forward.
                    await zmq_socket.send_multipart(zmq_msg)

            elif msg.type == aiohttp.WSMsgType.CLOSE:
                break
            elif msg.type == aiohttp.WSMsgType.ERROR:
                msg = f"Error with Kerlen WS and ZMQ proxy, data: {msg.data}"
                raise SpyderRemoteAPIError(msg)
            elif msg.type == aiohttp.WSMsgType.TEXT:
                # Default protocol only allows binary frames - log & ignore.
                logger.debug("[kernel-proxy] Ignoring TEXT frame from client: %s", msg.data)

    @staticmethod
    def _parse_protocol(ws_message: bytes) -> dict:
        """Decode binary WebSocket frame."""
        # Read the *offset count* first (4-bytes BE) then that many offsets.
        if len(ws_message) < 4:
            raise ValueError("Frame too small - no offset count")

        offset_num = struct.unpack(">I", ws_message[0:4])[0]
        if offset_num < 1:
            raise ValueError("offset_num must be >=1")
        # Now expect (offset_num) further 4-byte ints.
        needed = 4 * (offset_num + 1)
        if len(ws_message) < needed:
            raise ValueError("Frame truncated: not enough offsets")

        offsets = [struct.unpack(">I", ws_message[i : i + 4])[0] for i in range(4, needed, 4)]
        if not offsets:
            raise ValueError("No offsets present")

        json_start = offsets[0]
        json_end = offsets[1] if len(offsets) > 1 else len(ws_message)
        json_part = ws_message[json_start:json_end]
        try:
            msg_dict = json.loads(json_part.decode("utf-8"))
        except UnicodeDecodeError as e:
            raise ValueError("Invalid UTF-8 in JSON part") from e

        buffers = []
        for idx in range(1, len(offsets)):
            start = offsets[idx]
            end = offsets[idx + 1] if (idx + 1) < len(offsets) else len(ws_message)
            buffers.append(ws_message[start:end])

        msg_dict["buffers"] = buffers
        return msg_dict

    @staticmethod
    def _build_protocol(
        *,
        channel: str,
        header: dict,
        parent_header: dict,
        metadata: dict,
        content: dict,
        buffers: list[bytes] | None = None,
    ) -> bytes:
        """Encode Python message parts."""
        if buffers is None:
            buffers = []

        msg_dict = {
            "channel": channel,
            "header": header,
            "parent_header": parent_header,
            "metadata": metadata,
            "content": content,
        }
        msg_bytes = json.dumps(msg_dict).encode("utf-8")

        # Offsets block: first 4-bytes is *offset_num* (N) then N offsets.
        offset_num = 1 + len(buffers)
        offset_values = []

        # offset_0 - start of JSON = length of offset block itself.
        offset0 = 4 + 4 * offset_num
        offset_values.append(offset0)

        # subsequent offsets: running position after JSON & each buffer.
        cursor = offset0 + len(msg_bytes)
        for buf in buffers:
            offset_values.append(cursor)
            cursor += len(buf)

        # Pack -> big-endian 32-bit unsigned ints
        frame = struct.pack(">I", offset_num)
        frame += b"".join(struct.pack(">I", off) for off in offset_values)
        frame += msg_bytes
        for buf in buffers:
            frame += buf
        return frame


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

    async def kernel_ws(self, kernel_id):
        bridger = SpyderKernelWSConnector(kernel_id=kernel_id, manager=self.manager)
        await bridger.connect()
        return bridger

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

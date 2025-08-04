# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Spyder WebSocket Kernel Client.

This module implements a WebSocket client for Spyder kernels.
"""

from __future__ import annotations

import asyncio
import logging
import os
import typing as t
from functools import wraps
from getpass import getuser
from types import MethodType

import aiohttp
from jupyter_client.adapter import adapt
from jupyter_client.channels import major_protocol_version
from jupyter_client.client import validate_string_dict
from jupyter_client.jsonutil import extract_dates
from jupyter_client.session import (
    extract_header,
    json_packer,
    json_unpacker,
    msg_header,
    new_id,
)
from qtconsole.kernel_mixins import QtKernelClientMixin
from qtconsole.util import SuperQObject
from qtpy.QtCore import Signal
from traitlets.config import Configurable

from spyder.api.asyncdispatcher import AsyncDispatcher

_LOGGER = logging.getLogger(__name__)


class _Session:
    def __init__(
        self,
        session: t.Optional[str] = None,
        username: t.Optional[str] = None,
        adapt_version: int = major_protocol_version,
        metadata: t.Optional[dict[str, t.Any]] = None,
        check_pid: bool = True,
    ):
        self.session = session or new_id()
        self.username = username or getuser()
        self.check_pid = check_pid
        self.adapt_version = adapt_version
        self.pid = os.getpid()
        self.none = self.pack({})
        self.message_count = 0
        self.metadata = metadata or {}

    @property
    def bsession(self):
        return self.session.encode("ascii")

    @staticmethod
    def pack(msg: dict[str, t.Any]) -> bytes:
        return json_packer(msg)

    @staticmethod
    def unpack(msg: bytes) -> dict[str, t.Any]:
        return json_unpacker(msg)

    async def send(
        self,
        stream: aiohttp.ClientWebSocketResponse,
        channel: str,
        msg: dict[str, t.Any],
    ) -> dict[str, t.Any] | None:
        """
        Build and send a message via websocket.

        The message format used by this function internally is as follows:

        [p_header, p_parent, p_content, buffer1, buffer2,...]

        The serialize/deserialize methods convert the nested message dict into
        this format.

        Parameters
        ----------
        stream: aiohttp.ClientWebSocketResponse
            The websocket stream to send the message to.

        msg : Message/dict
            The message to send. This should be a dict with the keys
            [header, parent_header, metadata, content, buffers].

        Returns
        -------
        msg : dict
            The constructed message.

        Raises
        ------
        TypeError
            If the buffers do not support the buffer protocol.
        ValueError
            If the buffers are not contiguous.
        """
        buffers = msg.get("buffers", [])

        if self.check_pid and os.getpid() != self.pid:
            _LOGGER.warning(
                "WARNING: attempted to send message from fork\n%s", msg
            )
            return None

        buffers = [] if buffers is None else buffers
        for idx, buf in enumerate(buffers):
            if isinstance(buf, memoryview):
                view = buf
            else:
                try:
                    # check to see if buf supports the buffer protocol.
                    view = memoryview(buf)
                except TypeError as e:
                    emsg = "Buffer objects must support the buffer protocol."
                    raise TypeError(emsg) from e

            # memoryview.contiguous is new in 3.3, just skip the check on
            # Python 2
            if hasattr(view, "contiguous") and not view.contiguous:
                # zmq requires memoryviews to be contiguous
                msge = f"Buffer {idx} ({buf}) is not contiguous"
                raise ValueError(msge)

        if self.adapt_version:
            msg = adapt(msg, self.adapt_version)

        to_send = self.serialize(msg)
        to_send.extend(buffers)

        await stream.send_bytes(
            self._serialize_components_v1_protocol(to_send, channel),
        )

        return msg

    async def recv(
        self,
        stream: aiohttp.ClientWebSocketResponse,
        timeout: t.Optional[float] = None,
    ) -> tuple[str, dict[str, t.Any]]:
        """
        Receive a message from the websocket stream.

        The message format used by this function internally is as follows:

        [p_header, p_parent, p_content, buffer1, buffer2,...]

        The serialize/deserialize methods convert the nested message dict into
        this format.

        Parameters
        ----------
        stream: aiohttp.ClientWebSocketResponse
            The websocket stream to receive the message from.

        Returns
        -------
        channel: str
            The channel name of the message.
        msg: dict
            The message dict.

        Raises
        ------
        aiohttp.WSMessageTypeError
            If the received message is not of type WSMsgType.BINARY.
        """
        msg = await stream.receive(timeout=timeout)
        if msg.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING}:
            _LOGGER.debug(
                "WebSocket connection closed with type %s and code %s",
                msg.type,
                msg.data,
            )
            return "closed", {}

        if msg.type is not aiohttp.WSMsgType.BINARY:
            msg = (
                f"Received message {msg.type}:{msg.data!r}"
                f" is not WSMsgType.BINARY"
            )
            raise aiohttp.WSMessageTypeError(msg)

        channel, components = self._deserialize_components_v1_protocol(msg.data)
        return channel, self.deserialize(components)

    def serialize(
        self,
        msg: dict[str, t.Any],
    ) -> list[bytes]:
        """
        Serialize the message components to bytes.

        This is roughly the inverse of deserialize. The serialize/deserialize
        methods work with full message lists, whereas pack/unpack work with
        the individual message parts in the message list.

        Parameters
        ----------
        msg: dict or Message
            The next message dict as returned by the self.msg method.

        Returns
        -------
        msg_list : list
            The list of bytes objects to be sent with the format::

                [p_header, p_parent, p_metadata,
                 p_content, buffer1, buffer2, ...]

            In this list, the ``p_*`` entities are the packed or serialized
            versions, so if JSON is used, these are utf8 encoded JSON strings.

        Raises
        ------
        TypeError
            If the message is malformed.
        """
        content = msg.get("content", {})
        if content is None:
            content = self.none
        elif isinstance(content, dict):
            content = self.pack(content)
        elif isinstance(content, bytes):
            # content is already packed, as in a relayed message
            pass
        elif isinstance(content, str):
            # should be bytes, but JSON often spits out unicode
            content = content.encode("utf8")
        else:
            emsg = f"Content incorrect type: {type(content)}"
            raise TypeError(emsg)

        return [
            self.pack(msg["header"]),
            self.pack(msg["parent_header"]),
            self.pack(msg["metadata"]),
            content,
        ]

    def deserialize(
        self,
        msg_list: list[bytes],
        content: bool = True,
    ) -> dict[str, t.Any]:
        """
        Unserialize a msg_list to a nested message dict.

        This is roughly the inverse of serialize. The serialize/deserialize
        methods work with full message lists, whereas pack/unpack work with
        the individual message parts in the message list.

        Parameters
        ----------
        msg_list : list of bytes or Message objects
            The list of message parts of the form [p_header,p_parent,
            p_metadata,p_content,buffer1,buffer2,...].
        content : bool (True)
            Whether to unpack the content dict (True), or leave it packed
            (False).

        Returns
        -------
        msg : dict
            The nested message dict with top-level keys [header, parent_header,
            content, buffers].  The buffers are returned as memoryviews.

        Raises
        ------
        TypeError
            If the message is malformed.
        """
        minlen = 4
        message = {}
        if not len(msg_list) >= minlen:
            msg = f"malformed message, must have at least {minlen} elements"
            raise TypeError(msg)

        header = self.unpack(msg_list[0])
        message["header"] = extract_dates(header)
        message["msg_id"] = header["msg_id"]
        message["msg_type"] = header["msg_type"]
        message["parent_header"] = extract_dates(self.unpack(msg_list[1]))
        message["metadata"] = self.unpack(msg_list[2])

        if content:
            message["content"] = self.unpack(msg_list[3])
        else:
            message["content"] = msg_list[3]

        buffers = [memoryview(b) for b in msg_list[4:]]
        message["buffers"] = buffers

        return adapt(message)

    @property
    def msg_id(self) -> str:
        message_number = self.message_count
        self.message_count += 1
        return f"{self.session}_{os.getpid()}_{message_number}"

    def msg_header(self, msg_type: str) -> dict[str, t.Any]:
        """Create a header for a message type."""
        return msg_header(self.msg_id, msg_type, self.username, self.session)

    def msg(
        self,
        msg_type: str,
        content: dict | None = None,
        parent: dict[str, t.Any] | None = None,
        header: dict[str, t.Any] | None = None,
        metadata: dict[str, t.Any] | None = None,
    ) -> dict[str, t.Any]:
        """
        Return the nested message dict.

        This format is different from what is sent over the wire. The
        serialize/deserialize methods converts this nested message dict to the
        wire format, which is a list of message parts.
        """
        msg = {}
        header = self.msg_header(msg_type) if header is None else header
        msg["header"] = header
        msg["msg_id"] = header["msg_id"]
        msg["msg_type"] = header["msg_type"]
        msg["parent_header"] = {} if parent is None else extract_header(parent)
        msg["content"] = {} if content is None else content
        msg["metadata"] = self.metadata.copy()

        if metadata is not None:
            msg["metadata"].update(metadata)

        return msg

    @staticmethod
    def _serialize_components_v1_protocol(
        components: list[bytes], channel: str
    ) -> bytes:
        echannel = channel.encode("utf-8")
        offsets = [8 * (1 + 1 + len(components) + 1)]
        offsets.append(len(echannel) + offsets[-1])

        for msg in components:
            offsets.append(len(msg) + offsets[-1])

        offset_number = len(offsets).to_bytes(8, byteorder="little")
        offsets = [
            offset.to_bytes(8, byteorder="little") for offset in offsets
        ]

        return b"".join([offset_number, *offsets, echannel, *components])

    @staticmethod
    def _deserialize_components_v1_protocol(
        ws_msg: bytes,
    ) -> tuple[str, list[bytes]]:
        offset_number = int.from_bytes(ws_msg[:8], "little")
        offsets = [
            int.from_bytes(ws_msg[8 * (i + 1) : 8 * (i + 2)], "little")
            for i in range(offset_number)
        ]
        channel = ws_msg[offsets[0] : offsets[1]].decode("utf-8")
        msg_list = [
            ws_msg[offsets[i] : offsets[i + 1]]
            for i in range(1, offset_number - 1)
        ]

        return channel, msg_list

    def send_raw(self, *args, **kwargs):
        msg = "send_raw is not implemented for WebSocket connections"
        raise NotImplementedError(msg)

    def feed_identities(self, *args, **kwargs):
        msg = "Websocket protocol does not support signing"
        raise NotImplementedError(msg)

    def sign(self, *args, **kwargs):
        msg = "Websocket protocol does not support signing"
        raise NotImplementedError(msg)


class _ChannelQueues:
    def __init__(self):
        AsyncDispatcher(loop="ipythonconsole", early_return=False)(
            self._create_queue
        )()

    async def _create_queue(self):
        self.shell = asyncio.Queue()
        self.iopub = asyncio.Queue()
        self.stdin = asyncio.Queue()
        self.control = asyncio.Queue()

    def __getitem__(self, channel: str) -> asyncio.Queue[dict[str, t.Any]]:
        return getattr(self, channel)


class _WebSocketChannel:
    def __init__(
        self,
        queue: asyncio.Queue[dict[str, t.Any]],
        websocket: aiohttp.ClientWebSocketResponse,
        session: _Session,
        channel_name: str,
    ):
        self._queue = queue
        self._websocket = websocket
        self.session = session
        self.channel_name = channel_name
        self._running: t.Optional[asyncio.Task[None]] = None
        self._inspect = None

    async def _loop(self):
        """Receive messages from the websocket stream."""
        while True:
            msg = await self._queue.get()
            self.call_handlers(msg)
            if self._inspect is not None:
                self._inspect(msg)

    def start(self):
        """Start the channel."""
        _LOGGER.debug("Starting channel %s", self.channel_name)
        self._running = asyncio.create_task(
            self._loop(), name=f"{self.session.session}-{self.channel_name}"
        )

    def stop(self) -> None:
        """Stop the channel."""
        if self._running is not None:
            self._running.cancel()
            self._running = None

        if not self._queue.empty():
            _LOGGER.warning(
                "Channel %s has messages in the queue, but is being stopped.",
                self.channel_name,
            )

    def is_alive(self) -> bool:
        """Test whether the channel is alive."""
        return self._running is not None and not self._running.done()

    @AsyncDispatcher(loop="ipythonconsole", early_return=False)
    async def send(self, msg: dict[str, t.Any]) -> None:
        """Send a message to the channel."""
        await self.session.send(self._websocket, self.channel_name, msg)

    def call_handlers(self, msg: dict[str, t.Any]):
        pass


class _WebSocketHBChannel:
    time_to_dead: float = 1.0

    def __init__(
        self,
        websocket: aiohttp.ClientWebSocketResponse,
    ):
        self._websocket = websocket
        self._websocket._handle_ping_pong_exception = MethodType(
            self._handle_heartbeat_exc(
                self._websocket._handle_ping_pong_exception
            ),
            self._websocket,
        )
        self._running = False

    def start(self):
        """Start the channel."""
        self._running = True
        self._set_heartbeat()

    def stop(self):
        """Stop the channel."""
        self._running = False
        self._unset_heartbeat()

    def is_alive(self) -> bool:
        """Test whether the channel is alive."""
        return self._running and not self._websocket.closed

    def pause(self):
        """Pause the heartbeat channel."""
        self._unset_heartbeat()

    def unpause(self):
        """Unpause the heartbeat channel."""
        self._set_heartbeat()

    def is_beating(self) -> bool:
        """Test whether the channel is beating."""
        return True

    def _set_heartbeat(self):
        """Set the heartbeat for the channel."""
        self._websocket._heartbeat = self.time_to_dead * 2
        self._websocket._pong_heartbeat = self.time_to_dead
        self._websocket._reset_heartbeat()

    def _unset_heartbeat(self):
        """Unset the heartbeat for the channel."""
        self._websocket._heartbeat = None
        self._websocket._reset_heartbeat()

    def _handle_heartbeat_exc(self, func):
        @wraps(func)
        def wrapper(ws: aiohttp.ClientWebSocketResponse, *args, **kwargs):
            self.call_handlers(ws._loop.time() - ws._heartbeat_when)
            return func(*args, **kwargs)

        return wrapper

    def call_handlers(self, since_last_heartbeat: float):
        pass


class _WebSocketKernelClient(Configurable):
    """Pure-async client for remote WS Jupyter kernels."""

    shell_channel_class = _WebSocketChannel  # type: ignore[assignment]
    iopub_channel_class = _WebSocketChannel  # type: ignore[assignment]
    hb_channel_class = _WebSocketHBChannel  # type: ignore[assignment]
    stdin_channel_class = _WebSocketChannel  # type: ignore[assignment]
    control_channel_class = _WebSocketChannel  # type: ignore[assignment]

    def __init__(
        self,
        endpoint: str,
        token: str | None = None,
        username: str | None = None,
        session_id: str | None = None,
        aiohttp_session: aiohttp.ClientSession | None = None,
    ):
        self._endpoint = endpoint
        self._token = token

        self.session = _Session(
            session=session_id,
            username=username,
        )

        self._aiohttp_session = aiohttp_session
        self._owns_session = aiohttp_session is None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._receiver: asyncio.Task[None] | None = None

        self._queues = _ChannelQueues()

        self._shell_channel: t.Optional[_WebSocketChannel] = None
        self._iopub_channel: t.Optional[_WebSocketChannel] = None
        self._stdin_channel: t.Optional[_WebSocketChannel] = None
        self._control_channel: t.Optional[_WebSocketChannel] = None
        self._hb_channel: t.Optional[_WebSocketHBChannel] = None

    @property
    def allow_stdin(self) -> bool:
        """Whether the kernel allows stdin requests."""
        return self.stdin_channel.is_alive()

    @property
    def shell_channel(self):
        if self._ws is None:
            msg = "WebSocket connection is not established."
            raise RuntimeError(msg)

        if self._shell_channel is None:
            self._shell_channel = self.shell_channel_class(
                self._queues.shell,
                self._ws,
                self.session,
                "shell",
            )
        return self._shell_channel

    @property
    def iopub_channel(self):
        if self._ws is None:
            msg = "WebSocket connection is not established."
            raise RuntimeError(msg)

        if self._iopub_channel is None:
            self._iopub_channel = self.iopub_channel_class(
                self._queues.iopub,
                self._ws,
                self.session,
                "iopub",
            )
        return self._iopub_channel

    @property
    def stdin_channel(self):
        if self._ws is None:
            msg = "WebSocket connection is not established."
            raise RuntimeError(msg)

        if self._stdin_channel is None:
            self._stdin_channel = self.stdin_channel_class(
                self._queues.stdin,
                self._ws,
                self.session,
                "stdin",
            )
        return self._stdin_channel

    @property
    def control_channel(self):
        if self._ws is None:
            msg = "WebSocket connection is not established."
            raise RuntimeError(msg)

        if self._control_channel is None:
            self._control_channel = self.control_channel_class(
                self._queues.control,
                self._ws,
                self.session,
                "control",
            )
        return self._control_channel

    @property
    def hb_channel(self):
        if self._ws is None:
            msg = "WebSocket connection is not established."
            raise RuntimeError(msg)

        if self._hb_channel is None:
            self._hb_channel = self.hb_channel_class(
                self._ws,
            )
        return self._hb_channel

    @property
    def kernel(self):
        return None  # remote kernel (no local process handle)

    @property
    def channels_running(self) -> bool:
        """Check if any of the channels created and running."""
        return (
            (bool(self._shell_channel) and self._shell_channel.is_alive())
            or (bool(self._iopub_channel) and self._iopub_channel.is_alive())
            or (bool(self._stdin_channel) and self._stdin_channel.is_alive())
            or (bool(self._hb_channel) and self._hb_channel.is_alive())
            or (
                bool(self._control_channel)
                and self._control_channel.is_alive()
            )
        )

    @AsyncDispatcher(loop="ipythonconsole", early_return=False)
    async def start_channels(
        self,
        shell: bool = True,
        iopub: bool = True,
        stdin: bool = True,
        hb: bool = True,
        control: bool = True,
    ):
        """
        Start the channels.

        Parameters
        ----------
        shell : bool, optional
            Whether to start the shell channel. Default is True.
        iopub : bool, optional
            Whether to start the iopub channel. Default is True.
        stdin : bool, optional
            Whether to start the stdin channel. Default is True.
        hb : bool, optional
            Whether to start the heartbeat channel. Default is True.
        control : bool, optional
            Whether to start the control channel. Default is True.
        """
        _LOGGER.info("Starting channels for %s", self.session.session)
        await self._connect()

        if shell:
            self.shell_channel.start()
            self.shell_channel._websocket = self._ws
            self._shell_channel._inspect = self._check_kernel_info_reply
        if iopub:
            self.iopub_channel.start()
            self.iopub_channel._websocket = self._ws
        if stdin:
            self.stdin_channel.start()
            self.stdin_channel._websocket = self._ws
        if hb:
            self.hb_channel.start()
            self.hb_channel._websocket = self._ws
        if control:
            self.control_channel.start()
            self.control_channel._websocket = self._ws

        self._receiver = asyncio.create_task(
            self._receiver_loop(), name=f"{self.session.session}-ws-receiver"
        )

        _LOGGER.debug("Websocket client started for %s", self.session.session)

    def _check_kernel_info_reply(self, msg: dict[str, t.Any]):
        if msg["msg_type"] == "kernel_info_reply":
            self._handle_kernel_info_reply(msg)
            self._shell_channel._inspect = None

    async def _connect(self):
        if self._owns_session:
            self._aiohttp_session = aiohttp.ClientSession()

        qs = {"session_id": self.session.session}
        if self._token:
            qs["token"] = self._token

        _LOGGER.info("Connecting to Websocket at: %s", self._endpoint)
        self._ws = await self._aiohttp_session.ws_connect(
            self._endpoint,
            params=qs,
            protocols=("v1.kernel.websocket.jupyter.org",),
            autoping=True,
            autoclose=True,
            max_msg_size=104857600,  # 100 MB
        )

    async def _receiver_loop(self):
        """Receive messages from the websocket stream."""
        try:
            channel = None
            while channel != "closed":
                channel, msg = await self.session.recv(self._ws)

                # TODO(@hlouzada): handle restarts on comms
                if (
                    channel == "iopub"
                    and msg["msg_type"] == "status"
                    and msg["content"].get("execution_state") == "restarting"
                ):
                    await asyncio.to_thread(
                        self.hb_channel.call_handlers,
                        self._ws._loop.time() - self._ws._heartbeat_when,
                    )

                await self._queues[channel].put(msg)
        except asyncio.CancelledError:
            _LOGGER.debug(
                "Receiver loop cancelled for %s", self.session.session
            )
        except BaseException as exc:
            await self._ws.close(code=aiohttp.WSCloseCode.INTERNAL_ERROR)
            self._handle_receiver_exception(exc)

    @staticmethod
    def _handle_receiver_exception(exc: BaseException):
        """Handle exceptions in the receiver loop."""
        raise exc

    @AsyncDispatcher(loop="ipythonconsole", early_return=False)
    async def stop_channels(self):
        """Stop the channels."""
        _LOGGER.info("Stopping channels for %s", self.session.session)

        if self._receiver is not None:
            self._receiver.cancel()
            self._receiver = None

        if self.shell_channel.is_alive():
            self.shell_channel.stop()
        if self.iopub_channel.is_alive():
            self.iopub_channel.stop()
        if self.stdin_channel.is_alive():
            self.stdin_channel.stop()
        if self.hb_channel.is_alive():
            self.hb_channel.stop()
        if self.control_channel.is_alive():
            self.control_channel.stop()

        await self._disconnect()

        _LOGGER.debug("Disconnected from %s", self.session.session)

    async def _disconnect(self):
        if self._ws is not None:
            await self._ws.close()

        if self._owns_session and self._aiohttp_session is not None:
            await self._aiohttp_session.close()

    def _handle_kernel_info_reply(self, msg: t.Dict[str, t.Any]) -> None:
        """
        Handle kernel info reply.

        It sets protocol adaptation version. This might be run from a separate
        thread.
        """
        adapt_version = int(msg["content"]["protocol_version"].split(".")[0])
        if adapt_version != major_protocol_version:
            self.session.adapt_version = adapt_version

    def is_alive(self) -> bool:
        """Test whether the kernel is alive."""
        return self._ws is not None and not self._ws.closed

    def execute(
        self,
        code: str,
        silent: bool = False,
        store_history: bool = True,
        user_expressions: t.Optional[t.Dict[str, t.Any]] = None,
        allow_stdin: t.Optional[bool] = None,
        stop_on_error: bool = True,
    ) -> str:
        """
        Execute code in the kernel.

        Parameters
        ----------
        code : str
            A string of code in the kernel's language.
        silent : bool, optional (default False)
            If set, the kernel will execute the code as quietly possible, and
            will force store_history to be False.
        store_history : bool, optional (default True)
            If set, the kernel will store command history. This is forced
            to be False if silent is True.
        user_expressions : dict, optional
            A dict mapping names to expressions to be evaluated in the user's
            dict. The expression values are returned as strings formatted using
            :func:`repr`.
        allow_stdin : bool, optional (default self.allow_stdin)
            Flag for whether the kernel can send stdin requests to frontends.
            Some frontends (e.g. the Notebook) do not support stdin requests.
            If raw_input is called from code executed from such a frontend, a
            StdinNotImplementedError will be raised.
        stop_on_error: bool, optional (default True)
            Flag whether to abort the execution queue, if an exception is
            encountered.

        Returns
        -------
        The msg_id of the message sent.

        Raises
        ------
        ValueError
            If the code is not a string.
        """
        if user_expressions is None:
            user_expressions = {}
        if allow_stdin is None:
            allow_stdin = self.allow_stdin

        # Don't waste network traffic if inputs are invalid
        if not isinstance(code, str):
            raise ValueError("code %r must be a string" % code)
        validate_string_dict(user_expressions)

        # Create class for content/msg creation. Related to, but possibly
        # not in Session.
        content = {
            "code": code,
            "silent": silent,
            "store_history": store_history,
            "user_expressions": user_expressions,
            "allow_stdin": allow_stdin,
            "stop_on_error": stop_on_error,
        }
        msg = self.session.msg("execute_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def complete(self, code: str, cursor_pos: t.Optional[int] = None) -> str:
        """
        Tab complete text in the kernel's namespace.

        Parameters
        ----------
        code : str
            The context in which completion is requested. It can be anything
            between a variable name and an entire cell.
        cursor_pos : int, optional
            The position of the cursor in the block of code where the
            completion was requested. The default is ``len(code)``.

        Returns
        -------
        The msg_id of the message sent.
        """
        if cursor_pos is None:
            cursor_pos = len(code)
        content = {"code": code, "cursor_pos": cursor_pos}
        msg = self.session.msg("complete_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def inspect(
        self,
        code: str,
        cursor_pos: t.Optional[int] = None,
        detail_level: int = 0,
    ) -> str:
        """
        Get metadata information about an object in the kernel's namespace.

        It is up to the kernel to determine the appropriate object to inspect.

        Parameters
        ----------
        code : str
            The context in which info is requested. It can be anything between
            a variable name and an entire cell.
        cursor_pos : int, optional
            The position of the cursor in the block of code where the info was
            requested. The default is ``len(code)``.
        detail_level : int, optional
            The level of detail for the introspection (0-2).

        Returns
        -------
        The msg_id of the message sent.
        """
        if cursor_pos is None:
            cursor_pos = len(code)
        content = {
            "code": code,
            "cursor_pos": cursor_pos,
            "detail_level": detail_level,
        }
        msg = self.session.msg("inspect_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def history(
        self,
        raw: bool = True,
        output: bool = False,
        hist_access_type: str = "range",
        **kwargs: t.Any,
    ) -> str:
        """
        Get entries from the kernel's history list.

        Parameters
        ----------
        raw : bool
            If True, return the raw input.
        output : bool
            If True, then return the output as well.
        hist_access_type : str
            'range' (fill in session, start and stop params), 'tail' (fill in
             n) or 'search' (fill in pattern param).

        session : int
            For a range request, the session from which to get lines. Session
            numbers are positive integers; negative ones count back from the
            current session.
        start : int
            The first line number of a history range.
        stop : int
            The final (excluded) line number of a history range.
        n : int
            The number of lines of history to get for a tail request.
        pattern : str
            The glob-syntax pattern for a search request.

        Returns
        -------
        The ID of the message sent.
        """
        if hist_access_type == "range":
            kwargs.setdefault("session", 0)
            kwargs.setdefault("start", 0)
        content = dict(
            raw=raw, output=output, hist_access_type=hist_access_type, **kwargs
        )
        msg = self.session.msg("history_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def kernel_info(self) -> str:
        """
        Request kernel info.

        Returns
        -------
        The msg_id of the message sent.
        """
        msg = self.session.msg("kernel_info_request")
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def comm_info(self, target_name: t.Optional[str] = None) -> str:
        """
        Request comm info.

        Returns
        -------
        The msg_id of the message sent.
        """
        content = {} if target_name is None else {"target_name": target_name}
        msg = self.session.msg("comm_info_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def is_complete(self, code: str) -> str:
        """
        Ask the kernel whether some code is complete and ready to execute.

        Returns
        -------
        The ID of the message sent.
        """
        msg = self.session.msg("is_complete_request", {"code": code})
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def input(self, string: str) -> None:
        """
        Send a string of raw input to the kernel.

        This should only be called in response to the kernel sending an
        ``input_request`` message on the stdin channel.

        Returns
        -------
        The ID of the message sent.
        """
        content = {"value": string}
        msg = self.session.msg("input_reply", content)
        self.stdin_channel.send(msg)

    def shutdown(self, restart: bool = False) -> str:
        """
        Request an immediate kernel shutdown on the control channel.

        Upon receipt of the (empty) reply, client code can safely assume that
        the kernel has shut down and it's safe to forcefully terminate it if
        it's still alive.

        The kernel will send the reply via a function registered with Python's
        atexit module, ensuring it's truly done as the kernel is done with all
        normal operation.

        Returns
        -------
        The msg_id of the message sent
        """
        # Send quit message to kernel. Once we implement kernel-side setattr,
        # this should probably be done that way, but for now this will do.
        msg = self.session.msg("shutdown_request", {"restart": restart})
        self.control_channel.send(msg)
        return msg["header"]["msg_id"]


class QtWSHBChannel(_WebSocketHBChannel, SuperQObject):
    """A heartbeat channel emitting a Qt signal when a message is received."""

    # Emitted when the kernel has died.
    kernel_died = Signal(float)

    def call_handlers(self, since_last_heartbeat):
        """Reimplemented to emit signal."""
        # Emit the generic signal.
        self.kernel_died.emit(since_last_heartbeat)


class QtWSChannel(_WebSocketChannel, SuperQObject):
    """A channel emitting a Qt signal when a message is received."""

    # Emitted when a message is received.
    message_received = Signal(object)

    def call_handlers(self, msg):
        """
        This method is called in the ioloop thread when a message arrives.

        It is important to remember that this method is called in the thread
        so that some logic must be done to ensure that the application level
        handlers are called in the application thread.
        """
        # Emit the generic signal.
        self.message_received.emit(msg)

    def closed(self):
        """Check if the channel is closed."""
        return not self.is_alive()

    def flush(self):
        pass


class SpyderWSKernelClient(QtKernelClientMixin, _WebSocketKernelClient):
    """A KernelClient that provides signals and slots."""

    iopub_channel_class = QtWSChannel
    shell_channel_class = QtWSChannel
    stdin_channel_class = QtWSChannel
    hb_channel_class = QtWSHBChannel
    control_channel_class = QtWSChannel

    sig_spyder_kernel_info = Signal(object)

    sig_ws_msg_size_overflow = Signal(int)

    def _handle_kernel_info_reply(self, rep):
        """Check spyder-kernels version."""
        super()._handle_kernel_info_reply(rep)
        spyder_kernels_info = rep["content"].get("spyder_kernels_info", None)
        self.sig_spyder_kernel_info.emit(spyder_kernels_info)

    def _handle_receiver_exception(self, exc: BaseException):
        """Handle exceptions in the receiver loop."""
        if (
            isinstance(exc, aiohttp.WebSocketError)
            and exc.code == aiohttp.WSCloseCode.MESSAGE_TOO_BIG
        ):
            _LOGGER.error(
                "WebSocket message too big for %s: %s",
                self.session.session,
                exc,
            )
            self.sig_ws_msg_size_overflow.emit(self._ws._reader._max_msg_size)
        else:
            super()._handle_receiver_exception(exc)

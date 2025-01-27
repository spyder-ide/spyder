# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
import base64
from http import HTTPStatus
from io import RawIOBase
import json
from pathlib import Path

import aiohttp

from spyder.plugins.remoteclient.api.modules.base import SpyderBaseJupyterAPI
from spyder.plugins.remoteclient.api import SpyderRemoteAPIManager

# jupyter server's extension name for spyder-remote-services
SPYDER_PLUGIN_NAME = "spyder-services"


class SpyderServicesError(Exception):
    """
    Exception for errors related to Spyder services.
    """
    ...


class RemoteFileServicesError(SpyderServicesError):
    """
    Exception for errors related to remote file services.
    """
    def __init__(self, type, message, url, tracebacks):
        self.type = type
        self.message = message
        self.url = url
        self.tracebacks = tracebacks

    def __str__(self):
        return (
            f"(type='{self.type}', message='{self.message}', url='{self.url}')"
        )


class RemoteOSError(OSError, RemoteFileServicesError):
    """
    Exception for OSErrors raised on the remote server.
    """
    def __init__(self, errno, strerror, filename, url):
        super().__init__(errno, strerror, filename)
        super(OSError, self).__init__(OSError, super().__str__(), url, [])

    @classmethod
    def from_json(cls, data, url):
        return cls(data["errno"], data["strerror"], data["filename"], url)

    def __str__(self):
        return super(OSError, self).__str__()


@SpyderRemoteAPIManager.register_api
class SpyderRemoteFileIOAPI(SpyderBaseJupyterAPI, RawIOBase):
    """
    API for remote file I/O.

    This API is a RawIOBase subclass that allows reading and writing files
    on a remote server.

    The file is open upon the websocket connection and closed when the
    connection is closed.

    If lock is True, the file will be locked on the remote server.
    And any other attempts to open the file will wait until the lock is
    released.

    If atomic is True, any operations on the file will be done on a temporary
    copy of the file, and then the file will be replaced with the copy upon
    closing.

    Parameters
    ----------
    file : str
        The path to the file to open.
    mode : str, optional
        The mode to open the file in, by default "r".
    atomic : bool, optional
        Whether to open the file atomically, by default False.
    lock : bool, optional
        Whether to lock the file, by default False.
    encoding : str, optional
        The encoding to use when reading and writing the file, by default
        "utf-8".

    Raises
    ------
    RemoteFileServicesError
        If an error occurs when opening the file.
    RemoteOSError
        If an OSError occured on the remote server.
    """
    base_url = SPYDER_PLUGIN_NAME + "/fs/open"

    def __init__(
        self,
        file,
        mode="r",
        atomic=False,
        lock=False,
        encoding="utf-8",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.name = file
        self.mode = mode
        self.encoding = encoding
        self.atomic = atomic
        self.lock = lock

        self._websocket: aiohttp.ClientWebSocketResponse = None

    async def _raise_for_status(self, response):
        response.raise_for_status()

    async def connect(self):
        await super().connect()

        if self._websocket is not None and not self._websocket.closed:
            return

        self._websocket = await self.session.ws_connect(
            self.api_url / f"file://{self.name}",
            params={
                "mode": self.mode,
                "atomic": str(self.atomic).lower(),
                "lock": str(self.lock).lower(),
                "encoding": self.encoding,
            },
        )

        try:
            await self._check_connection()
        except Exception as e:
            self._websocket = None
            raise e

    async def _check_connection(self):
        status = await self._websocket.receive()

        if status.type == aiohttp.WSMsgType.CLOSE:
            await self._websocket.close()
            if status.data == 1002:
                data = json.loads(status.extra)
                if data["status"] in (
                    HTTPStatus.LOCKED,
                    HTTPStatus.EXPECTATION_FAILED,
                ):
                    raise RemoteOSError.from_json(
                        data, url=self._websocket._response.url
                    )

                raise RemoteFileServicesError(
                    data.get("type", "UnknownError"),
                    data.get("message", "Unknown error"),
                    self._websocket._response.url,
                    data.get("tracebacks", []),
                )
            else:
                raise RemoteFileServicesError(
                    "UnknownError",
                    "Failed to open file",
                    self._websocket._response.url,
                    [],
                )

    async def close(self):
        await self._websocket.close()
        try:
            await self._websocket.receive()
        except Exception:
            pass
        await super().close()

    @property
    def closed(self):
        if self._websocket is None:
            return super().closed
        return self._websocket.closed and super().closed

    def _decode_data(self, data: str | object) -> str | bytes | object:
        """Decode data from a message."""
        if not isinstance(data, str):
            return data

        if "b" in self.mode:
            return base64.b64decode(data)

        return base64.b64decode(data).decode(self.encoding)

    def _encode_data(self, data: bytes | str | object) -> str:
        """Encode data for a message."""
        if isinstance(data, bytes):
            return base64.b64encode(data).decode("ascii")
        if isinstance(data, str):
            return base64.b64encode(data.encode(self.encoding)).decode("ascii")
        return data

    async def _send_request(self, method: str, **args):
        await self._websocket.send_json({"method": method, **args})

    async def _get_response(self, timeout=None):
        message = json.loads(
            await self._websocket.receive_bytes(timeout=timeout)
        )

        if message["status"] > 400:
            if message["status"] == HTTPStatus.EXPECTATION_FAILED:
                raise RemoteOSError.from_json(
                    message, url=self._websocket._response.url
                )

            raise RemoteFileServicesError(
                message.get("type", "UnknownError"),
                message.get("message", "Unknown error"),
                self._websocket._response.url,
                message.get("tracebacks", []),
            )

        data = message.get("data")
        if data is None:
            return None

        if isinstance(data, list):
            return [self._decode_data(d) for d in data]

        return self._decode_data(data)

    @property
    def closefd(self):
        return True

    async def __iter__(self):
        while response := await self.readline():
            yield response

    async def __next__(self):
        response = await self.readline()
        if not response:
            raise StopIteration
        return response

    async def write(self, s: bytes | str) -> int:
        """Write data to the file."""
        await self._send_request("write", data=self._encode_data(s))
        return await self._get_response()

    async def flush(self):
        """Flush the file."""
        await self._send_request("flush")
        return await self._get_response()

    async def read(self, size: int = -1) -> bytes | str:
        """Read data from the file."""
        await self._send_request("read", n=size)
        return await self._get_response()

    async def readall(self):
        """Read all data from the file."""
        return await self.read(size=-1)

    async def readinto(self, b) -> int:
        """Read data into a buffer."""
        raise NotImplementedError(
            "readinto() is not supported by the remote file API"
        )

    async def seek(self, pos: int, whence: int = 0) -> int:
        """Seek to a new position in the file."""
        await self._send_request("seek", offset=pos, whence=whence)
        return await self._get_response()

    async def tell(self) -> int:
        """Get the current file position."""
        await self._send_request("tell")
        return await self._get_response()

    async def truncate(self, size: int | None = None) -> int:
        """Truncate the file to a new size."""
        await self._send_request("truncate", size=size)
        return await self._get_response()

    async def fileno(self):
        """Flush the file to disk."""
        await self._send_request("fileno")
        return await self._get_response()

    async def readline(self, size: int = -1) -> bytes | str:
        """Read a line from the file."""
        await self._send_request("readline", size=size)
        return await self._get_response()

    async def readlines(self, hint: int = -1) -> list[bytes | str]:
        """Read lines from the file."""
        await self._send_request("readlines", hint=hint)
        return await self._get_response()

    async def writelines(self, lines: list[bytes | str]):
        """Write lines to the file."""
        await self._send_request(
            "writelines", lines=list(map(self._encode_data, lines))
        )
        return await self._get_response()

    async def isatty(self) -> bool:
        """Check if the file is a TTY."""
        await self._send_request("isatty")
        return await self._get_response()

    async def readable(self) -> bool:
        """Check if the file is readable."""
        await self._send_request("readable")
        return await self._get_response()

    async def writable(self) -> bool:
        """Check if the file is writable."""
        await self._send_request("writable")
        return await self._get_response()


@SpyderRemoteAPIManager.register_api
class SpyderRemoteFileServicesAPI(SpyderBaseJupyterAPI):
    """
    API for remote file services.

    This API allows for interacting with files on a remote server.

    Raises
    ------
    RemoteFileServicesError
        If an error occurs when interacting with the file services.
    RemoteOSError
        If an OSError occured on the remote server.
    """

    base_url = SPYDER_PLUGIN_NAME + "/fs"

    async def _raise_for_status(self, response: aiohttp.ClientResponse):
        if response.status not in (
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.EXPECTATION_FAILED,
        ):
            return response.raise_for_status()

        try:
            data = await response.json()
        except json.JSONDecodeError:
            data = {}

        # If we're in a context we can rely on __aexit__() to release as the
        # exception propagates.
        if not response._in_context:
            response.release()

        if response.status == HTTPStatus.EXPECTATION_FAILED:
            raise RemoteOSError.from_json(data, response.url)

        raise RemoteFileServicesError(
            data.get("type", "UnknownError"),
            data.get("message", "Unknown error"),
            response.url,
            data.get("tracebacks", []),
        )

    async def ls(self, path: Path, detail: bool = True):
        async with self.session.get(
            self.api_url / "ls" / f"file://{path}",
            params={"detail": str(detail).lower()},
        ) as response:
            return await response.json()

    async def info(self, path: Path):
        async with self.session.get(
            self.api_url / "info" / f"file://{path}"
        ) as response:
            return await response.json()

    async def exists(self, path: Path):
        async with self.session.get(
            self.api_url / "exists" / f"file://{path}"
        ) as response:
            return await response.json()

    async def is_file(self, path: Path):
        async with self.session.get(
            self.api_url / "isfile" / f"file://{path}"
        ) as response:
            return await response.json()

    async def is_dir(self, path: Path):
        async with self.session.get(
            self.api_url / "isdir" / f"file://{path}"
        ) as response:
            return await response.json()

    async def mkdir(
        self, path: Path, create_parents: bool = True, exist_ok: bool = False
    ):
        async with self.session.post(
            self.api_url / "mkdir" / f"file://{path}",
            params={
                "create_parents": str(create_parents).lower(),
                "exist_ok": str(exist_ok).lower(),
            },
        ) as response:
            return await response.json()

    async def rmdir(self, path: Path):
        async with self.session.delete(
            self.api_url / "rmdir" / f"file://{path}"
        ) as response:
            return await response.json()

    async def unlink(self, path: Path, missing_ok: bool = False):
        async with self.session.delete(
            self.api_url / "file" / f"file://{path}",
            params={"missing_ok": str(missing_ok).lower()},
        ) as response:
            return await response.json()

    async def copy(self, path1: Path, path2: Path):
        async with self.session.post(
            self.api_url / "copy" / f"file://{path1}",
            params={"dest": f"file://{path2}"},
        ) as response:
            return await response.json()

    async def copy2(self, path1: Path, path2: Path):
        async with self.session.post(
            self.api_url / "copy" / f"file://{path1}",
            params={"dest": f"file://{path2}", "metadata": "true"},
        ) as response:
            return await response.json()

    async def replace(self, path1: Path, path2: Path):
        async with self.session.post(
            self.api_url / "move" / f"file://{path1}",
            params={"dest": f"file://{path2}"},
        ) as response:
            return await response.json()

    async def touch(self, path: Path, truncate: bool = True):
        async with self.session.post(
            self.api_url / "touch" / f"file://{path}",
            params={"truncate": str(truncate).lower()},
        ) as response:
            return await response.json()

    async def open(
        self, path, mode="r", atomic=False, lock=False, encoding="utf-8"
    ):
        file = SpyderRemoteFileIOAPI(
            path, mode, atomic, lock, encoding, manager=self.manager
        )
        await file.connect()
        return file

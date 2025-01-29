from __future__ import annotations
import asyncio
import base64
import datetime
import errno
from http import HTTPStatus
from io import FileIO
import os
from pathlib import Path
from shutil import copy, copy2
import stat
import threading
import time
import traceback

import orjson
from tornado.websocket import WebSocketHandler


class FileWebSocketHandler(WebSocketHandler):
    """
    WebSocket handler for opening files and streaming data.

    The protocol on message receive (JSON messages):
      {
        "method": "read", # "write", "seek", etc.  (required)
        "kwargs": {...},  (optional)
        "data": "<base64-encoded chunk>",  # all data is base64-encoded  (optional)
      }

    The protocol for sending data back to the client:
      {
        "status": 200,  # HTTP status code  (required)
        "data": "<base64-encoded chunk>",  # response data if any  (optional)
        "error": {"message": "error message",  (required)
                  "traceback": ["line1", "line2", ...]  (optional)}  # if an error occurred  (optional)
      }
    """

    LOCK_TIMEOUT = 100  # seconds

    max_message_size = 5 * 1024 * 1024 * 1024  # 5 GB

    __thread_lock = threading.Lock()

    # ----------------------------------------------------------------
    # Tornado WebSocket / Handler Hooks
    # ----------------------------------------------------------------
    async def open(self, path):
        """Open file."""
        self.mode = self.get_argument("mode", default="r")
        self.atomic = self.get_argument("atomic", default="false") == "true"
        lock = self.get_argument("lock", default="false") == "true"
        self.encoding = self.get_argument("encoding", default="utf-8")

        self.file: FileIO = None
        try:
            self.path = self._load_path(path)

            if lock and not await self._acquire_lock(path):
                self.close(
                    1002,
                    self._parse_json(
                        HTTPStatus.LOCKED, message="File is locked"
                    ),
                )
                return

            self.file = await self._open_file()
        except OSError as e:
            self.log.warning("Error opening file", exc_info=e)
            self.close(1002, self._parse_os_error(e))
        except Exception as e:
            self.log.exception("Error opening file")
            self.close(1002, self._parse_error(e))
        else:
            await self._send_json(HTTPStatus.OK)

    def on_close(self):
        """Close file."""
        if self.file is not None:
            self._close_file()
        if self.__locked:
            self._release_lock()

    async def on_message(self, raw_message):
        """Handle incoming messages."""
        self.log.debug("Received message: %s", raw_message)
        try:
            await self.handle_message(raw_message)
        except Exception as e:
            self.log.exception("Error handling message")
            await self.write_message(self._parse_error(e), binary=True)

    # ----------------------------------------------------------------
    # Internal Helpers
    # ----------------------------------------------------------------
    async def handle_message(self, raw_message):
        msg = self._decode_json(raw_message)
        method, kwargs = await self._parse_message(msg)
        await self._run_method(method, kwargs)

    async def _open_file(self):
        """Open the file in the requested mode."""
        if self.atomic and ("+" in self.mode or
                            "a" in self.mode or
                            "w" in self.mode):
            if self.path.exists() and "w" not in self.mode:
                copy2(self.path, self.atomic_path)
            return self.atomic_path.open(self.mode)

        return self.path.open(self.mode)

    def _close_file(self):
        self.file.close()
        if self.atomic:
            self.atomic_path.replace(self.path)

    async def _run_method(self, method, kwargs):
        """Run a method with kwargs."""
        try:
            result = await getattr(self, f"_handle_{method}")(**kwargs)
        except OSError as e:
            self.log.warning("Error handling method: %s", method)
            await self.write_message(self._parse_os_error(e), binary=True)
        else:
            await self._send_result(result)

    async def _parse_message(self, msg):
        """Parse a message into method and kwargs."""
        method = msg.pop("method", None)

        if "data" in msg and isinstance(msg["data"], list):
            msg["data"] = [self._decode_data(d) for d in msg["data"]]
        elif "data" in msg:
            msg["data"] = self._decode_data(msg["data"])

        return method, msg

    async def _acquire_lock(self, __start_time=None):
        """Acquire a lock on the file."""
        if __start_time is None:
            __start_time = time.time()

        while self.__locked:
            await asyncio.sleep(1)
            if time.time() - __start_time > self.LOCK_TIMEOUT:
                return False

        with self.__thread_lock:
            if self.__locked:
                return await self._acquire_lock(__start_time=__start_time)
            self.lock_path.touch(exist_ok=False)

        return True

    def _release_lock(self):
        """Release the lock on the file."""
        with self.__thread_lock:
            self.lock_path.unlink(missing_ok=True)

    @property
    def atomic_path(self):
        """Get the path to the atomic file."""
        return self.path.parent / f".{self.path.name}.spyder.tmp"

    @property
    def lock_path(self):
        """Get the path to the atomic file."""
        return self.path.parent / f".{self.path.name}.spyder.lck"

    @property
    def __locked(self):
        return Path(self.lock_path).exists()

    def _decode_json(self, raw_message):
        """Decode a JSON message (non-streamed)."""
        return orjson.loads(raw_message)

    async def _send_json(self, status: HTTPStatus, **data: dict):
        """Send a single JSON message."""
        await self.write_message(self._parse_json(status, **data), binary=True)

    def _parse_json(self, status: HTTPStatus, **data: dict) -> bytes:
        """Parse a single JSON message."""
        return orjson.dumps({"status": status.value, **data})

    def _parse_error(self, error: BaseException) -> bytes:
        """Parse an error response to the client."""
        return self._parse_json(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            message=str(error),
            tracebacks=traceback.format_exception(
                type(error), error, error.__traceback__
            ),
            type=str(type(error)),
        )

    def _parse_os_error(self, e: OSError) -> bytes:
        """Parse an OSError response to the client."""
        return self._parse_json(
            HTTPStatus.EXPECTATION_FAILED,
            strerror=e.strerror,
            filename=e.filename,
            errno=e.errno,
        )

    async def _send_msg_error(self, message):
        await self._send_json(
            HTTPStatus.BAD_REQUEST, message=message,
        )

    async def _send_result(self, result):
        if result is None:
            await self._send_json(HTTPStatus.NO_CONTENT)
        elif isinstance(result, list):
            await self._send_json(
                HTTPStatus.OK, data=[self._encode_data(r) for r in result],
            )
        else:
            await self._send_json(
                HTTPStatus.OK, data=self._encode_data(result),
            )

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

    def _load_path(self, path_str: str) -> Path:
        """Convert path string to a Path object."""
        return Path(path_str).expanduser()

    # ----------------------------------------------------------------
    # File Operation
    # ----------------------------------------------------------------
    async def _handle_write(self, data: bytes | str) -> int:
        """Write data to the file."""
        return self.file.write(data)

    async def _handle_flush(self):
        """Flush the file."""
        return self.file.flush()

    async def _handle_read(self, n: int = -1) -> bytes | str:
        """Read data from the file."""
        return self.file.read(n)

    async def _handle_seek(self, offset: int, whence: int = 0) -> int:
        """Seek to a new position in the file."""
        return self.file.seek(offset, whence)

    async def _handle_tell(self) -> int:
        """Get the current file position."""
        return self.file.tell()

    async def _handle_truncate(self, size: int | None = None) -> int:
        """Truncate the file to a new size."""
        return self.file.truncate(size)

    async def _handle_fileno(self):
        """Flush the file to disk."""
        return self.file.fileno()

    async def _handle_readline(self, size: int = -1) -> bytes | str:
        """Read a line from the file."""
        return self.file.readline(size)

    async def _handle_readlines(self, hint: int = -1) -> list[bytes | str]:
        """Read lines from the file."""
        return self.file.readlines(hint)

    async def _handle_writelines(self, lines: list[bytes | str]):
        """Write lines to the file."""
        return self.file.writelines(lines)

    async def _handle_isatty(self) -> bool:
        """Check if the file is a TTY."""
        return self.file.isatty()

    async def _handle_readable(self) -> bool:
        """Check if the file is readable."""
        return self.file.readable()

    async def _handle_writable(self) -> bool:
        """Check if the file is writable."""
        return self.file.writable()


class FilesRESTMixin:
    """
    REST handler for fsspec-like filesystem operations, using pathlib.Path.

    Supports:
        - fs_ls(path_str, detail=True)
        - fs_info(path_str)
        - fs_exists(path_str)
        - fs_isfile(path_str)
        - fs_isdir(path_str)
        - fs_mkdir(path_str, create_parents=True, exist_ok=False)
        - fs_rmdir(path_str)
        - fs_rm_file(path_str, missing_ok=False)
        - fs_touch(path_str, truncate=True)
    """

    def _info_for_path(self, path: Path) -> dict:
        """Get fsspec-like info about a single path."""
        out = path.stat(follow_symlinks=False)
        link = stat.S_ISLNK(out.st_mode)
        if link:
            # If it's a link, stat the target
            out = path.stat(follow_symlinks=True)
        size = out.st_size
        if stat.S_ISDIR(out.st_mode):
            t = "directory"
        elif stat.S_ISREG(out.st_mode):
            t = "file"
        else:
            t = "other"
        result = {
            "name": str(path),
            "size": size,
            "type": t,
            "created": out.st_ctime,
            "islink": link,
        }
        for field in ["mode", "uid", "gid", "mtime", "ino", "nlink"]:
            result[field] = getattr(out, f"st_{field}", None)
        if link:
            result["destination"] = str(path.resolve())

        return result

    def _load_path(self, path_str: str) -> Path | None:
        """Convert a path string to a pathlib.Path object."""
        return Path(path_str).expanduser()

    def fs_ls(self, path_str: str, detail: bool = True):
        """List objects at path, like fsspec.ls()."""
        path = self._load_path(path_str)
        if not path.exists():
            raise FileNotFoundError(errno.ENOENT,
                                    os.strerror(errno.ENOENT),
                                    str(path))
        if path.is_file():
            # fsspec.ls of a file often returns a single entry
            if detail:
                return [self._info_for_path(path)]

            return [str(path)]

        # Otherwise, it's a directory
        results = []
        for p in path.glob("*"):
            if detail:
                results.append(self._info_for_path(p))
            else:
                results.append(str(p))
        return results

    def fs_info(self, path_str: str):
        """Get info about a single path, like fsspec.info()."""
        path = self._load_path(path_str)
        return self._info_for_path(path)

    def fs_exists(self, path_str: str) -> bool:
        """Like fsspec.exists()."""
        path = self._load_path(path_str)
        return path.exists()

    def fs_isfile(self, path_str: str) -> bool:
        """Like fsspec.isfile()."""
        path = self._load_path(path_str)
        return path.is_file()

    def fs_isdir(self, path_str: str) -> bool:
        """Like fsspec.isdir()."""
        path = self._load_path(path_str)
        return path.is_dir()

    def fs_mkdir(self, path_str: str, create_parents: bool = True, exist_ok: bool = False):
        """Like fsspec.mkdir()."""
        path = self._load_path(path_str)
        path.mkdir(parents=create_parents, exist_ok=exist_ok)
        return {"success": True}

    def fs_rmdir(self, path_str: str):
        """Like fsspec.rmdir() - remove if empty."""
        path = self._load_path(path_str)
        path.rmdir()
        return {"success": True}

    def fs_rm_file(self, path_str: str, missing_ok: bool = False):
        """Like fsspec.rm_file(), remove a single file."""
        path = self._load_path(path_str)
        path.unlink(missing_ok=missing_ok)
        return {"success": True}

    def fs_touch(self, path_str: str, truncate: bool = True):
        """
        Like fsspec.touch(path, truncate=True).
        If truncate=True, zero out file if exists. Otherwise just update mtime.
        """
        path = self._load_path(path_str)
        if path.exists() and not truncate:
            now = datetime.datetime.now().timestamp()
            os.utime(path, (now, now))
        else:
            # create or overwrite
            with path.open("wb"):
                pass
        return {"success": True}

    def fs_copy(self, src_str: str, dst_str: str, metadata: bool=False):
        """Like fsspec.copy()."""
        src = self._load_path(src_str)
        dst = self._load_path(dst_str)
        if metadata:
            copy2(src, dst)
        else:
            copy(src, dst)
        return {"success": True}

from __future__ import annotations
from contextlib import asynccontextmanager
from http import HTTPStatus
from http.client import responses
import re
import traceback
from typing import Any

from jupyter_server.auth.decorator import authorized, ws_authenticated
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.base.websocket import WebSocketMixin
import orjson
from tornado import web

from spyder_remote_services.services.files.base import (
    FilesRESTMixin,
    FileWebSocketHandler,
)


class ReadWriteWebsocketHandler(
    WebSocketMixin,
    FileWebSocketHandler,
    JupyterHandler,
):
    auth_resource = "spyder-services"

    def get_path_argument(self, name: str) -> str:
        """Get the path argument from the request.

        Args
        ----
            name (str): Name of the argument to get.

        Returns
        -------
            str: The path argument.

        Raises
        ------
            HTTPError: If the argument is missing or invalid.
        """
        path = self.get_argument(name)
        if not path:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST,
                reason=f"Missing {name} argument",
            )
        match = re.match(_path_regex, path)
        if not match:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST,
                reason=f"Missing {name} argument",
            )
        return match.group("path")

    @ws_authenticated
    async def get(self, *args, **kwargs):
        """Handle the initial websocket upgrade GET request."""
        await super().get(*args, **kwargs)


class BaseFSHandler(FilesRESTMixin, JupyterHandler):
    auth_resource = "spyder-services"

    def get_path_argument(self, name: str) -> str:
        """Get the path argument from the request.

        Args
        ----
            name (str): Name of the argument to get.

        Returns
        -------
            str: The path argument.

        Raises
        ------
            HTTPError: If the argument is missing or invalid.
        """
        path = self.get_argument(name)
        if not path:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST,
                reason=f"Missing {name} argument",
            )
        match = re.match(_path_regex, path)
        if not match:
            raise web.HTTPError(
                HTTPStatus.BAD_REQUEST,
                reason=f"Missing {name} argument",
            )
        return match.group("path")

    def write_json(self, data, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.finish(orjson.dumps(data))

    @asynccontextmanager
    async def stream_json(self, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/stream+json")
        async def write_json(data):
            self.write(orjson.dumps(data) + b"\n")
            await self.flush()
        yield write_json
        await self.finish()

    def write_error(self, status_code, **kwargs):
        """APIHandler errors are JSON, not human pages."""
        self.set_header("Content-Type", "application/json")
        reply: dict[str, Any] = {}
        exc_info = kwargs.get("exc_info")
        if exc_info:
            e = exc_info[1]
            if isinstance(e, web.HTTPError):
                reply["message"] = e.log_message or responses.get(status_code, "Unknown HTTP Error")
                reply["reason"] = e.reason
            elif isinstance(e, OSError):
                self.set_status(HTTPStatus.EXPECTATION_FAILED)
                reply["strerror"] = e.strerror
                reply["errno"] = e.errno
                reply["filename"] = e.filename
            else:
                self.set_status(HTTPStatus.INTERNAL_SERVER_ERROR)
                reply["type"] = str(type(e))
                reply["message"] = str(e)
                reply["traceback"] = traceback.format_exception(*exc_info)
        else:
            reply["message"] = responses.get(status_code, "Unknown HTTP Error")
        self.finish(orjson.dumps(reply))

    def log_exception(self, typ, value, tb):
        """Log uncaught exceptions."""
        if isinstance(value, web.HTTPError):
            if value.log_message:
                format = "%d %s: " + value.log_message
                args = [value.status_code, self._request_summary()] + list(value.args)
                self.log.warning(format, *args)
        elif isinstance(value, OSError):
            self.log.debug(
                "OSError [Errno %s] %s",
                value.errno,
                self._request_summary(),
                exc_info=(typ, value, tb),  # type: ignore
            )
        else:
            self.log.warning(
                "Uncaught exception %s\n%r",
                self._request_summary(),
                self.request,
                exc_info=(typ, value, tb),  # type: ignore
            )


class LsHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    async def get(self):
        detail_arg = self.get_argument("detail", default="true").lower()
        detail = detail_arg == "true"
        path = self.get_path_argument("path")
        async with self.stream_json() as write_json:
            for result in self.fs_ls(path, detail=detail):
                await write_json(result)

class InfoHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def get(self):
        result = self.fs_info(self.get_path_argument("path"))
        self.write_json(result)


class ExistsHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def get(self):
        result = self.fs_exists(self.get_path_argument("path"))
        self.write_json({"exists": result})


class IsFileHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def get(self):
        result = self.fs_isfile(self.get_path_argument("path"))
        self.write_json({"isfile": result})


class IsDirHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def get(self):
        result = self.fs_isdir(self.get_path_argument("path"))
        self.write_json({"isdir": result})


class MkdirHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def post(self):
        path = self.get_path_argument("path")
        create_parents = (self.get_argument("create_parents", "true").lower() == "true")
        exist_ok = (self.get_argument("exist_ok", "false").lower() == "true")
        result = self.fs_mkdir(path, create_parents=create_parents, exist_ok=exist_ok)
        self.write_json(result)


class RmdirHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def delete(self):
        result = self.fs_rmdir(
            self.get_path_argument("path"),
            non_empty=(self.get_argument("non_empty", "false").lower() == "true"),
        )
        self.write_json(result)


class RemoveFileHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def delete(self):
        path = self.get_path_argument("path")
        missing_ok = (self.get_argument("missing_ok", "false").lower() == "true")
        result = self.fs_rm_file(path, missing_ok=missing_ok)
        self.write_json(result)


class TouchHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def post(self):
        path = self.get_path_argument("path")
        truncate = (self.get_argument("truncate", "true").lower() == "true")
        result = self.fs_touch(path, truncate=truncate)
        self.write_json(result)


class CopyHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def post(self):
        path = self.get_path_argument("path")
        dest = self.get_path_argument("dest")
        metadata = (self.get_argument("metadata", "false").lower() == "true")
        result = self.fs_copy(path, dest, metadata=metadata)
        self.write_json(result)


class MoveHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def post(self):
        path = self.get_path_argument("path")
        dest = self.get_path_argument("dest")
        result = self.fs_move(path, dest)
        self.write_json(result)


class ZipHandler(BaseFSHandler):
    @web.authenticated
    @authorized
    def post(self):
        path = self.get_path_argument("path")
        compression = int(self.get_argument("compression", "0"))

        with self.fs_zip_dir(path, compression=compression) as zip_stream:
            if zip_stream is None:
                raise web.HTTPError(
                    HTTPStatus.BAD_REQUEST,
                    reason="No files to zip or invalid path",
                )

            p_path = self._load_path(path)
            self.set_header("Content-Type", "application/zip")
            self.set_header("Content-Disposition", f"attachment; filename={p_path.name}.zip")
            for chunk in zip_stream:
                self.write(chunk)
                self.flush()
            self.finish()


_path_regex = r"file://(?P<path>.+)"

handlers = [
    (r"/fs/open", ReadWriteWebsocketHandler),  # WebSocket
    (r"/fs/ls", LsHandler),                  # GET
    (r"/fs/info", InfoHandler),              # GET
    (r"/fs/exists", ExistsHandler),          # GET
    (r"/fs/isfile", IsFileHandler),          # GET
    (r"/fs/isdir", IsDirHandler),            # GET
    (r"/fs/mkdir", MkdirHandler),            # POST
    (r"/fs/rmdir", RmdirHandler),            # DELETE
    (r"/fs/file", RemoveFileHandler),        # DELETE
    (r"/fs/touch", TouchHandler),            # POST
    (r"/fs/copy", CopyHandler),              # POST
    (r"/fs/move", MoveHandler),
    (r"/fs/zip", ZipHandler),              # POST
]

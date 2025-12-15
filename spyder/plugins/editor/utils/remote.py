# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Utilities to interact with remote files through the Remote Client plugin."""

from __future__ import annotations

# Standard library imports
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.plugins.remoteclient.api.modules.file_services import (
    RemoteFileServicesError,
    RemoteOSError,
    SpyderRemoteFileServicesAPI,
)
from spyder.utils import encoding

if TYPE_CHECKING:
    from spyder.plugins.remoteclient.plugin import RemoteClient


@dataclass
class RemoteFileHandle:
    """Metadata required to operate on a remote file."""

    URI_SEP = "://"  # Used to separate client ID from path in URIs

    client_id: str
    path: PurePosixPath
    last_modified: float | None = None
    size: int | None = None

    def clone(self) -> RemoteFileHandle:
        """Return an independent copy of this handle."""
        return RemoteFileHandle(
            client_id=self.client_id,
            path=PurePosixPath(self.path),
            last_modified=self.last_modified,
            size=self.size,
        )

    @property
    def uri(self) -> str:
        """Return the canonical URI representation for this file."""
        return f"{self.client_id}{self.URI_SEP}{self.path}"

    @classmethod
    def from_uri(cls, uri: str) -> RemoteFileHandle | None:
        """Return a RemoteFileHandle if ``uri`` encodes one."""
        if not isinstance(uri, str) or cls.URI_SEP not in uri:
            return None

        prefix, remainder = uri.split(cls.URI_SEP, 1)

        if not prefix:
            return None

        normalized = f"/{remainder.lstrip('/')}"

        return RemoteFileHandle(
            client_id=prefix, path=PurePosixPath(normalized)
        )


class RemoteFileHelper:
    """Helper to bridge the Editor with Spyder remote services."""

    EVENT_LOOP_ID = "editor-remote-files"

    def __init__(self, remote_client: RemoteClient):
        self.remote_client = remote_client
        self._api_instances: dict[str, SpyderRemoteFileServicesAPI] = {}

        self._read_runner = AsyncDispatcher(
            loop=self.EVENT_LOOP_ID, early_return=False
        )(self._read_async)

        self._write_runner = AsyncDispatcher(
            loop=self.EVENT_LOOP_ID, early_return=False
        )(self._write_async)

        self._info_runner = AsyncDispatcher(
            loop=self.EVENT_LOOP_ID, early_return=False
        )(self._info_async)

        self._exists_runner = AsyncDispatcher(
            loop=self.EVENT_LOOP_ID, early_return=False
        )(self._exists_async)

        self._is_writable_runner = AsyncDispatcher(
            loop=self.EVENT_LOOP_ID, early_return=False
        )(self._is_writable_async)

        self._close_runner = AsyncDispatcher(
            loop=self.EVENT_LOOP_ID, early_return=False
        )(self._close_async)

    # -------------------------------------------------------------------------
    # ---- Public helpers
    # -------------------------------------------------------------------------
    @classmethod
    def get_handle(cls, candidate: str) -> RemoteFileHandle | None:
        """Return a RemoteFileHandle if ``candidate`` encodes one."""
        return RemoteFileHandle.from_uri(candidate)

    def get_display_name(self, handle: RemoteFileHandle) -> str:
        """Return a user-friendly representation of the remote file."""
        return (
            f"{self.remote_client.get_server_name(handle.client_id)}"
            f"{handle.URI_SEP}{handle.path}"
        )

    def read_text(
        self, handle: RemoteFileHandle
    ) -> tuple[str, str, RemoteFileHandle]:
        """Return file contents, encoding and updated metadata."""
        data, info = self._read_runner(
            handle.client_id, handle.path.as_posix()
        )
        text, detected_encoding = encoding.decode(data)
        updated = handle.clone()
        updated.last_modified = info.get("mtime")
        updated.size = info.get("size")
        return text, detected_encoding, updated

    def write_text(
        self, handle: RemoteFileHandle, text: str, encoding_name: str
    ) -> RemoteFileHandle:
        """Persist ``text`` remotely and return updated metadata."""
        info = self._write_runner(
            handle.client_id,
            handle.path.as_posix(),
            text,
            encoding_name or "utf-8",
        )
        updated = handle.clone()
        updated.last_modified = info.get("mtime")
        updated.size = info.get("size")
        return updated

    def exists(self, handle: RemoteFileHandle) -> bool:
        """Return True if the remote file exists."""
        return bool(
            self._exists_runner(handle.client_id, handle.path.as_posix())
        )

    def stat(self, handle: RemoteFileHandle) -> RemoteFileHandle | None:
        """Return updated metadata if available."""
        info = self._info_runner(handle.client_id, handle.path.as_posix())
        if info is None:
            return None
        updated = handle.clone()
        updated.last_modified = info.get("mtime")
        updated.size = info.get("size")
        return updated

    def is_writable(self, handle: RemoteFileHandle) -> bool:
        """Return True if the remote file is writable."""
        return self._is_writable_runner(
            handle.client_id, handle.path.as_posix()
        )

    def close(self) -> None:
        """Close any cached remote API sessions."""
        for api in self._api_instances.values():
            self._close_runner(api)
        self._api_instances.clear()

    # -------------------------------------------------------------------------
    # ---- Async runners
    # -------------------------------------------------------------------------
    async def _read_async(self, client_id: str, posix_path: str):
        api = await self._ensure_api_async(client_id)
        remote_file = await api.open(posix_path, mode="rb")
        try:
            data = await remote_file.read()
        finally:
            await remote_file.close()
        info = await api.info(PurePosixPath(posix_path))
        return data, info

    async def _write_async(
        self, client_id: str, posix_path: str, text: str, encoding_name: str
    ):
        encoded, coding = encoding.encode(text, encoding_name)
        api = await self._ensure_api_async(client_id)
        remote_file = await api.open(
            posix_path, mode="wb", atomic=True, encoding=coding
        )
        try:
            await remote_file.write(encoded)
        finally:
            await remote_file.close()
        return await api.info(PurePosixPath(posix_path))

    async def _info_async(self, client_id: str, posix_path: str):
        api = await self._ensure_api_async(client_id)
        try:
            return await api.info(PurePosixPath(posix_path))
        except (RemoteOSError, RemoteFileServicesError):
            return None

    async def _exists_async(self, client_id: str, posix_path: str) -> bool:
        api = await self._ensure_api_async(client_id)
        try:
            return await api.exists(PurePosixPath(posix_path))
        except (RemoteOSError, RemoteFileServicesError):
            return False

    async def _is_writable_async(
        self, client_id: str, posix_path: str
    ) -> bool:
        api = await self._ensure_api_async(client_id)
        try:
            remote_file = await api.open(posix_path, mode="ab")
        except (RemoteOSError, RemoteFileServicesError):
            return False
        else:
            return True
        finally:
            await remote_file.close()

    async def _close_async(self, api: SpyderRemoteFileServicesAPI) -> None:
        if api.closed:
            return
        await api.close()

    async def _ensure_api_async(
        self, client_id: str
    ) -> SpyderRemoteFileServicesAPI:
        api = self._api_instances.get(client_id)
        if api is None:
            api_factory = self.remote_client.get_file_api(client_id)
            api = api_factory()
            self._api_instances[client_id] = api
        if api.closed:
            await api.connect()
        return api

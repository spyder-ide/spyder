# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the language server connection."""

import asyncio

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.plugins.languageservices.providers.lsp.connection import (
    LanguageServerConnection,
)


def make_connection():
    return LanguageServerConnection(
        ServerConfig(name="test"), "/tmp", lambda *args: None
    )


def test_client_advertises_only_utf16():
    capabilities = LanguageServerConnection.client_capabilities()
    assert capabilities.general.position_encodings == [
        lsp.PositionEncodingKind.Utf16
    ]


def test_auto_languages_serve_everything_until_registration():
    connection = make_connection()
    assert connection.config.auto_languages
    assert connection.languages() == frozenset(Language)

    connection.registered_languages.add("rust")
    assert connection.languages() == Language.from_language_id("rust")


def test_initialize_sends_workspace_folders(monkeypatch):
    connection = make_connection()
    folder = lsp.WorkspaceFolder(uri="file:///proj", name="proj")
    connection.workspace_folders = {folder.uri: folder}
    sent = {}

    async def reply(method, params):
        sent["params"] = params
        return lsp.InitializeResult(capabilities=lsp.ServerCapabilities())

    monkeypatch.setattr(
        connection._client.protocol, "send_request_async", reply
    )
    monkeypatch.setattr(
        connection._client.protocol, "notify", lambda *args: None
    )

    asyncio.run(connection._initialize())
    assert sent["params"].workspace_folders == [folder]


def test_initialize_rejects_non_utf16_encoding(monkeypatch):
    connection = make_connection()

    async def reply(method, params):
        return lsp.InitializeResult(
            capabilities=lsp.ServerCapabilities(
                position_encoding=lsp.PositionEncodingKind.Utf8
            )
        )

    monkeypatch.setattr(
        connection._client.protocol, "send_request_async", reply
    )

    with pytest.raises(ValueError, match="UTF-16"):
        asyncio.run(connection._initialize())

    assert not connection.initialized

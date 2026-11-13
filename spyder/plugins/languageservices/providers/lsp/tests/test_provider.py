# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the generic language server client provider.

The tests talk to real ``pyrefly`` processes described purely by
configuration, and to small pygls servers exercising the TCP transport and
language auto-detection through registered document selectors.
"""

import asyncio
import sys

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import ProviderStatus
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.languageservices.providers.lsp import (
    provider as provider_module,
)
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.plugins.languageservices.providers.lsp.provider import (
    LanguageServerClientProvider,
    _ServerState,
)
from spyder.plugins.languageservices.services import LanguageServicesAPI


pytestmark = pytest.mark.order(3)

PYREFLY_SETTINGS = {"python": {"pythonPath": sys.executable}}


def pyrefly_config(name):
    from pyrefly.__main__ import get_pyrefly_bin

    return ServerConfig(
        name=name,
        cmd=get_pyrefly_bin(),
        args="lsp",
        stdio=True,
        languages=("python",),
        configurations=PYREFLY_SETTINGS,
    )


class ConfiguredProvider(LanguageServerClientProvider):
    """Provider whose servers come from a class attribute."""

    NAME = "lsp-test"
    SERVERS: list[ServerConfig] = []

    def get_server_configs(self):
        return list(self.SERVERS)


def make_api(servers):
    class Provider(ConfiguredProvider):
        SERVERS = servers

    api = LanguageServicesAPI()
    provider = api.register_provider(Provider)
    return api, provider


def did_open(uri, text):
    return lsp.DidOpenTextDocumentParams(
        text_document=lsp.TextDocumentItem(
            uri=uri, language_id="python", version=1, text=text
        )
    )


class Recorder:

    def __init__(self, signal):
        self.calls = []
        signal.connect(lambda *args: self.calls.append(args))


async def wait_until(predicate, timeout=30):
    for _ in range(int(timeout * 20)):
        if predicate():
            return
        await asyncio.sleep(0.05)

    raise TimeoutError("Condition not met")


def test_pyrefly_from_config(tmp_path):
    api, provider = make_api([pyrefly_config("py")])
    diagnostics = Recorder(api.sig_diagnostics)
    statuses = Recorder(provider.sig_server_status_changed)
    filename = str(tmp_path / "test.py")
    uri = path_as_uri(filename)

    async def scenario():
        await api.start_provider(provider.NAME)
        assert provider.server_status("py") is ProviderStatus.STOPPED

        await api.start_language(Language.PYTHON)
        assert provider.server_status("py") is ProviderStatus.READY
        assert [s for _, s in statuses.calls] == [
            ProviderStatus.STARTING, ProviderStatus.READY
        ]
        assert api.is_language_supported(Language.PYTHON)

        capabilities = api.capabilities(Language.PYTHON)
        assert capabilities.completion_provider is not None
        assert "." in capabilities.completion_provider.trigger_characters

        await api.open_document(did_open(uri, "import os\nos.walk(top='.')\n"))

        signature = await api.signature_help(
            lsp.SignatureHelpParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(1, 8),
            )
        )
        assert "walk" in signature.signatures[0].label

        await api.change_document(
            lsp.DidChangeTextDocumentParams(
                text_document=lsp.VersionedTextDocumentIdentifier(
                    uri=uri, version=2
                ),
                content_changes=[
                    lsp.TextDocumentContentChangeWholeDocument(
                        text="import o"
                    )
                ],
            )
        )
        items = await api.completion(
            lsp.CompletionParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(0, 8),
            )
        )
        labels = [item.label for item in items]
        assert "os" in labels
        assert items[0].data["provider"] == provider.NAME

        await api.change_document(
            lsp.DidChangeTextDocumentParams(
                text_document=lsp.VersionedTextDocumentIdentifier(
                    uri=uri, version=3
                ),
                content_changes=[
                    lsp.TextDocumentContentChangeWholeDocument(
                        text="import os\nos.walk\nundefined_name\n"
                    )
                ],
            )
        )
        location = await api.definition(
            lsp.DefinitionParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(1, 4),
            )
        )
        assert location and "os.py" in location[0].uri

        await wait_until(
            lambda: any(
                "undefined_name" in d.message
                for params in diagnostics.calls
                for d in params[0].diagnostics
            )
        )
        assert diagnostics.calls[-1][0].uri == uri

        await api.stop_provider(provider.NAME)
        assert provider.server_status("py") is ProviderStatus.STOPPED

        # Diagnostics are cleared when the server stops
        assert diagnostics.calls[-1][0].diagnostics == []

    asyncio.run(scenario())


def test_two_servers_for_one_language(tmp_path):
    """Two pyrefly instances configured under different names both serve
    Python. Their answers are merged."""
    api, provider = make_api([pyrefly_config("first"), pyrefly_config("second")])
    uri = path_as_uri(str(tmp_path / "two.py"))

    async def scenario():
        await api.start_provider(provider.NAME)
        await api.start_language(Language.PYTHON)
        assert provider.servers_for(Language.PYTHON) == ["first", "second"]

        for name in ("first", "second"):
            assert provider.server_status(name) is ProviderStatus.READY

        await api.open_document(did_open(uri, "import o"))
        items = await api.completion(
            lsp.CompletionParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(0, 8),
            )
        )
        labels = [item.label for item in items]

        # Duplicates from the second server are dropped by the merge
        assert labels.count("os") == 1

        await provider.restart_server("second")
        assert provider.server_status("second") is ProviderStatus.READY
        await api.stop_provider(provider.NAME)

    asyncio.run(scenario())


TCP_SERVER = '''
import sys
from lsprotocol import types
from pygls.lsp.server import LanguageServer

server = LanguageServer("tcp-fake", "0.1")


@server.feature(types.TEXT_DOCUMENT_HOVER)
def on_hover(params):
    return types.Hover(contents="tcp hover")


server.start_tcp(sys.argv[1], int(sys.argv[2]))
'''


def test_tcp_server(tmp_path):
    script = tmp_path / "tcp_server.py"
    script.write_text(TCP_SERVER)
    config = ServerConfig(
        name="tcp",
        cmd=sys.executable,
        args=str(script) + " {host} {port}",
        host="127.0.0.1",
        port=2087,
        languages=("python",),
    )
    api, provider = make_api([config])
    uri = path_as_uri(str(tmp_path / "main.py"))

    async def scenario():
        await api.start_provider(provider.NAME)
        await api.start_language(Language.PYTHON)
        assert provider.server_status("tcp") is ProviderStatus.READY
        await api.open_document(did_open(uri, "x = 1\n"))
        hover = await api.hover(
            lsp.HoverParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(0, 0),
            )
        )
        assert hover.contents == "tcp hover"
        await api.stop_provider(provider.NAME)
        assert provider.server_status("tcp") is ProviderStatus.STOPPED

    asyncio.run(scenario())


FAKE_SERVER = '''
from lsprotocol import types
from pygls.lsp.server import LanguageServer

server = LanguageServer("fake", "0.1")


@server.feature(types.INITIALIZED)
async def on_initialized(params):
    await server.client_register_capability_async(
        types.RegistrationParams(
            registrations=[
                types.Registration(
                    id="1",
                    method=types.TEXT_DOCUMENT_COMPLETION,
                    register_options=types.CompletionRegistrationOptions(
                        document_selector=[
                            types.TextDocumentFilterLanguage(language="rust")
                        ],
                        trigger_characters=[":"],
                    ),
                )
            ]
        )
    )


@server.feature(types.TEXT_DOCUMENT_HOVER)
def on_hover(params):
    return types.Hover(contents="fake hover")


server.start_io()
'''


def test_language_detection_from_registrations(tmp_path):
    script = tmp_path / "fake_server.py"
    script.write_text(FAKE_SERVER)
    config = ServerConfig(
        name="fake",
        cmd=sys.executable,
        args=str(script),
        stdio=True,
        languages="auto",
    )
    api, provider = make_api([config])
    capabilities = Recorder(api.sig_capabilities_changed)
    uri = path_as_uri(str(tmp_path / "main.rs"))

    async def scenario():
        # Auto servers start with the provider and serve every language
        # until a registered document selector narrows the set.
        await api.start_provider(provider.NAME)
        assert provider.server_status("fake") is ProviderStatus.READY
        await wait_until(
            lambda: api.is_language_supported(Language.RUST)
            and not api.is_language_supported(Language.PYTHON)
        )
        assert Language.RUST in {c[0] for c in capabilities.calls}

        await api.open_document(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri=uri, language_id="rust", version=1, text="fn main() {}"
                )
            )
        )
        hover = await api.hover(
            lsp.HoverParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(0, 3),
            )
        )
        assert hover.contents == "fake hover"
        await api.stop_provider(provider.NAME)

    asyncio.run(scenario())


class _FakeConnection:

    def __init__(self):
        self.name = "fake"
        self.initialized = True
        self.capabilities = lsp.ServerCapabilities()
        self.notified = []
        self.workspace_folders = {}

    def languages(self):
        return frozenset({Language.PYTHON})

    def notify(self, method, params):
        self.notified.append(method)

    async def stop(self):
        self.initialized = False


def _ready_state(name, connection):
    return _ServerState(
        config=ServerConfig(name=name, cmd="server", stdio=True, languages=("python",)),
        connection=connection,
        status=ProviderStatus.READY,
    )


def _auto_state(name, connection=None, status=ProviderStatus.STOPPED):
    return _ServerState(
        config=ServerConfig(name=name, cmd="server", stdio=True),
        connection=connection,
        status=status,
    )


def test_stop_language_keeps_auto_server_running():
    # An auto server serves every language, so stopping one language must
    # not stop it.
    _, provider = make_api([])
    connection = _FakeConnection()
    state = _auto_state("a", connection, ProviderStatus.READY)
    provider._servers["a"] = state

    asyncio.run(provider.stop_language(Language.PYTHON))
    assert state.status is ProviderStatus.READY


def test_start_language_starts_stopped_auto_server(monkeypatch):
    _, provider = make_api([])
    provider._servers["a"] = _auto_state("a")
    started = []

    async def record_start(name):
        started.append(name)

    monkeypatch.setattr(provider, "_start_server", record_start)
    asyncio.run(provider.start_language(Language.PYTHON))
    assert started == ["a"]


def test_folder_broadcast_restarts_once_per_actual_change():
    # The folders are re-broadcast every time capabilities change (the editor
    # calls the projects plugin back on each one). A server without dynamic
    # folder support restarts on a real change to pick the folders up at
    # initialize, but a broadcast of folders it already has must be a no-op
    # otherwise every restart triggers the next one.
    _, provider = make_api([])
    connection = _FakeConnection()
    connection.supports_workspace_folder_changes = False
    provider._servers["a"] = _ready_state("a", connection)
    restarts = []

    async def record_restart(name):
        restarts.append(name)
        connection.workspace_folders = dict(provider._workspace_folders)

    provider.restart_server = record_restart

    folder = lsp.WorkspaceFolder(uri="file:///proj", name="proj")
    params = lsp.DidChangeWorkspaceFoldersParams(
        event=lsp.WorkspaceFoldersChangeEvent(added=[folder], removed=[])
    )
    asyncio.run(provider.did_change_workspace_folders(params))
    assert restarts == ["a"]

    asyncio.run(provider.did_change_workspace_folders(params))
    assert restarts == ["a"]

    removal = lsp.DidChangeWorkspaceFoldersParams(
        event=lsp.WorkspaceFoldersChangeEvent(added=[], removed=[folder])
    )
    asyncio.run(provider.did_change_workspace_folders(removal))
    assert restarts == ["a", "a"]


def test_ready_server_requests_documents_after_capabilities(monkeypatch):
    # The provider keeps no document text: a server that becomes ready asks
    # the document owners for the open documents instead.
    _, provider = make_api([])
    provider._servers["a"] = _ready_state("a", _FakeConnection())
    provider._servers["b"] = _ServerState(
        config=ServerConfig(
            name="b", cmd="server", stdio=True, languages=("python",)
        )
    )
    connections = []

    class Connection(_FakeConnection):
        def __init__(self, *args, **kwargs):
            super().__init__()
            connections.append(self)

        async def start(self):
            pass

    monkeypatch.setattr(
        provider_module, "LanguageServerConnection", Connection
    )
    events = []
    provider.sig_capabilities_changed.connect(
        lambda language: events.append(("capabilities", language))
    )
    provider.sig_documents_requested.connect(
        lambda language: events.append(("documents", language))
    )

    asyncio.run(provider._start_server("b"))

    assert provider.server_status("b") is ProviderStatus.READY
    assert events == [
        ("capabilities", Language.PYTHON),
        ("documents", Language.PYTHON),
    ]
    assert connections[0].notified == []


def test_did_open_dedups_per_server_and_reaches_late_server():
    # Re-sending didOpen (as happens when capabilities change and document
    # owners re-open) must not open a document twice in a server that already
    # has it, yet must reach a server that joined afterwards.
    _, provider = make_api([])
    first = _FakeConnection()
    provider._servers["a"] = _ready_state("a", first)
    params = did_open(path_as_uri("/tmp/f.py"), "x\n")

    def opens(conn):
        return conn.notified.count(lsp.TEXT_DOCUMENT_DID_OPEN)

    asyncio.run(provider.did_open(params))
    asyncio.run(provider.did_open(params))
    assert opens(first) == 1

    second = _FakeConnection()
    provider._servers["b"] = _ready_state("b", second)
    asyncio.run(provider.did_open(params))
    assert opens(first) == 1
    assert opens(second) == 1

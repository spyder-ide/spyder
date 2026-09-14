# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the generic language server client provider.

The tests talk to real ``pylsp`` processes described purely by
configuration, and to a small pygls server that registers a document
selector to exercise language auto-detection.
"""

import asyncio
import sys

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import ProviderStatus
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.languageservices.providers.lsp.config import ServerConfig
from spyder.plugins.languageservices.providers.lsp.provider import (
    LanguageServerClientProvider,
    _ServerState,
)
from spyder.plugins.languageservices.services import LanguageServicesAPI

pytestmark = pytest.mark.order(3)

PYLSP_SETTINGS = {
    "pylsp": {
        "plugins": {
            "pyflakes": {"enabled": True},
            "jedi_completion": {"enabled": True},
            "jedi_hover": {"enabled": True},
        }
    }
}


def pylsp_config(name, stdio):
    return ServerConfig(
        name=name,
        cmd="pylsp",
        args="" if stdio else "--host {host} --port {port} --tcp",
        host="127.0.0.1",
        port=2087,
        stdio=stdio,
        languages=("python",),
        configurations=PYLSP_SETTINGS,
        python_module=True,
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


@pytest.mark.parametrize("stdio", [False, True], ids=["tcp", "stdio"])
def test_pylsp_from_config(stdio, tmp_path):
    api, provider = make_api([pylsp_config("py", stdio)])
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

        await api.open_document(did_open(uri, "import os\nos.walk(\n"))

        signature = await api.signature_help(
            lsp.SignatureHelpParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(1, 8),
            )
        )
        assert signature.signatures[0].label.startswith("walk")

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
    """Two pylsp instances configured under different names both serve
    Python. Their answers are merged."""
    api, provider = make_api(
        [pylsp_config("first", stdio=True), pylsp_config("second", stdio=True)]
    )
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
        # Auto-detected servers start with the provider
        await api.start_provider(provider.NAME)
        assert provider.server_status("fake") is ProviderStatus.READY
        await wait_until(lambda: api.is_language_supported(Language.RUST))
        assert not api.is_language_supported(Language.PYTHON)
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
        self.initialized = True
        self.capabilities = lsp.ServerCapabilities()
        self.notified = []

    def languages(self):
        return frozenset({Language.PYTHON})

    def notify(self, method, params):
        self.notified.append(method)


def _ready_state(name, connection):
    return _ServerState(
        config=pylsp_config(name, True),
        connection=connection,
        status=ProviderStatus.READY,
    )


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

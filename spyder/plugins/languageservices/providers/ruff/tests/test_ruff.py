# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the ruff provider, against a real ``ruff server``."""

import asyncio

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import ProviderStatus
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.languageservices.providers.ruff.config import (
    generate_ruff_config,
)
from spyder.plugins.languageservices.providers.ruff.provider import RuffProvider
from spyder.plugins.languageservices.services import LanguageServicesAPI

pytestmark = pytest.mark.order(3)


def make_get_conf(values):
    def get_conf(option, default=None, section=None):
        return values.get((section, option), default)

    return get_conf


def test_generate_ruff_config_defaults():
    config = generate_ruff_config(make_get_conf({}))
    assert config.stdio and config.args == "server"
    assert config.languages == ("python",)
    settings = config.initialization_options["settings"]
    assert settings["lineLength"] == 79
    assert settings["lint"] == {"enable": True, "extendSelect": [], "ignore": []}
    assert "configuration" not in settings


def test_generate_ruff_config_options():
    values = {
        (None, "lint"): False,
        (None, "extend_select"): "E501, W291",
        (None, "ignore"): "E402",
        (None, "pydocstyle"): True,
        (None, "pydocstyle/convention"): "google",
        ("editor", "line_length"): 100,
    }
    settings = generate_ruff_config(make_get_conf(values)).initialization_options[
        "settings"
    ]
    assert settings["lineLength"] == 100
    assert settings["lint"] == {
        "enable": False,
        "extendSelect": ["E501", "W291", "D"],
        "ignore": ["E402"],
    }
    assert settings["configuration"] == {
        "lint": {"pydocstyle": {"convention": "google"}}
    }


async def wait_until(predicate, timeout=30):
    for _ in range(int(timeout * 20)):
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise TimeoutError("Condition not met")


def test_ruff_lints_and_formats(tmp_path):
    api = LanguageServicesAPI()
    provider = api.register_provider(RuffProvider)
    diagnostics = []
    api.sig_diagnostics.connect(diagnostics.append)
    uri = path_as_uri(str(tmp_path / "test.py"))

    async def scenario():
        await api.start_provider(provider.NAME)
        await api.start_language(Language.PYTHON)
        assert provider.server_status("ruff") is ProviderStatus.READY
        capabilities = api.capabilities(Language.PYTHON)
        assert capabilities.document_formatting_provider
        assert capabilities.document_range_formatting_provider
        assert not capabilities.hover_provider

        await api.open_document(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri=uri,
                    language_id="python",
                    version=1,
                    text="import os\nx=undefined_name\n",
                )
            )
        )
        await wait_until(
            lambda: any(
                d.code == "F821" for params in diagnostics for d in params.diagnostics
            )
        )
        codes = {d.code for d in diagnostics[-1].diagnostics}
        assert {"F401", "F821"} <= codes
        assert all(d.source == "Ruff" for d in diagnostics[-1].diagnostics)

        edits = await api.formatting(
            lsp.DocumentFormattingParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                options=lsp.FormattingOptions(tab_size=4, insert_spaces=True),
            )
        )
        assert any("x = undefined_name" in edit.new_text for edit in edits)

        # A hover past the end of the document crashes ruff, so hovers are
        # not forwarded to it.
        messages = []
        provider.sig_show_message.connect(messages.append)
        assert await api.hover(
            lsp.HoverParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(7, 17),
            )
        ) is None
        await asyncio.sleep(0.5)
        assert messages == []
        assert provider.server_status("ruff") is ProviderStatus.READY

        await api.stop_provider(provider.NAME)
        assert provider.server_status("ruff") is ProviderStatus.STOPPED

    asyncio.run(scenario())


if __name__ == "__main__":
    pytest.main()


def test_settings_change_restarts_and_requests_documents(tmp_path):
    # Settings travel in the initialization options, so a change restarts the
    # server. The new server asks for the open documents again.
    from spyder.config.manager import CONF

    api = LanguageServicesAPI()
    provider = api.register_provider(RuffProvider)
    diagnostics = []
    api.sig_diagnostics.connect(diagnostics.append)
    requested = []
    api.sig_documents_requested.connect(requested.append)
    uri = path_as_uri(str(tmp_path / "test.py"))
    option = ("providers", "ruff", "values", "extend_select")
    CONF.set("language_services", option, "")
    params = lsp.DidOpenTextDocumentParams(
        text_document=lsp.TextDocumentItem(
            uri=uri, language_id="python", version=1, text="x = 1 \n"
        )
    )

    async def scenario():
        await api.start_provider(provider.NAME)
        await api.start_language(Language.PYTHON)
        await api.open_document(params)
        await wait_until(lambda: diagnostics)
        assert not any(d.code == "W291" for d in diagnostics[-1].diagnostics)
        first = provider._servers["ruff"].connection

        CONF.set("language_services", option, "W")
        requested.clear()
        await provider.apply_server_configs(provider.get_server_configs())
        assert provider._servers["ruff"].connection is not first
        assert uri not in provider._servers["ruff"].documents
        assert Language.PYTHON in requested

        # The document owner answers the request
        await api.open_document(params)
        assert uri in provider._servers["ruff"].documents
        await wait_until(
            lambda: any(d.code == "W291" for d in diagnostics[-1].diagnostics)
        )
        await api.stop_provider(provider.NAME)

    try:
        asyncio.run(scenario())
    finally:
        CONF.set("language_services", option, "")

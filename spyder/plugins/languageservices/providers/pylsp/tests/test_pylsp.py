# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the pylsp provider, against a real pylsp server."""

import asyncio

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import ProviderStatus
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.languageservices.providers.pylsp.config import (
    generate_pylsp_config,
)
from spyder.plugins.languageservices.providers.pylsp.provider import (
    PylspProvider,
)
from spyder.plugins.languageservices.services import LanguageServicesAPI

pytestmark = pytest.mark.order(3)


def test_generate_pylsp_config_reads_editor_line_length():
    values = {("editor", "line_length"): 100}

    def get_conf(option, default=None, section=None):
        return values.get((section, option), default)

    config = generate_pylsp_config(get_conf, "/env/bin/python")
    plugins = config.configurations["pylsp"]["plugins"]
    assert plugins["pycodestyle"]["maxLineLength"] == 100
    assert plugins["flake8"]["maxLineLength"] == 100
    assert plugins["black"]["line_length"] == 100
    assert plugins["ruff"]["lineLength"] == 100
    assert plugins["jedi"]["environment"] == "/env/bin/python"


async def wait_until(predicate, timeout=60):
    for _ in range(int(timeout * 20)):
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise TimeoutError("Condition not met")


def test_pylsp_serves_python(tmp_path):
    api = LanguageServicesAPI()
    provider = api.register_provider(PylspProvider)
    diagnostics = []
    api.sig_diagnostics.connect(diagnostics.append)
    uri = path_as_uri(str(tmp_path / "test.py"))

    async def scenario():
        await api.start_provider(provider.NAME)
        await api.start_language(Language.PYTHON)
        assert provider.server_status("pylsp") is ProviderStatus.READY
        assert api.capabilities(Language.PYTHON).completion_provider

        await api.open_document(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri=uri,
                    language_id="python",
                    version=1,
                    text="import os\nos.wa\nundefined_name\n",
                )
            )
        )
        items = await api.completion(
            lsp.CompletionParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(1, 5),
            )
        )
        assert any(item.label.startswith("walk(") for item in items)
        assert items[0].data["provider"] == provider.NAME

        await wait_until(
            lambda: any(
                "undefined_name" in d.message
                for params in diagnostics
                for d in params.diagnostics
            )
        )

        await api.stop_provider(provider.NAME)
        assert provider.server_status("pylsp") is ProviderStatus.STOPPED

    asyncio.run(scenario())


if __name__ == "__main__":
    pytest.main()

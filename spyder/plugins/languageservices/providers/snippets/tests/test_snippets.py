# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the snippets provider."""

import asyncio
import random

from lsprotocol import types as lsp
import pytest

from spyder.config.manager import CONF
from spyder.config.snippets import SNIPPETS
from spyder.plugins.languageservices.plugin import LanguageServices
from spyder.plugins.languageservices.providers.snippets.provider import (
    SnippetsProvider,
    build_trie,
    snippet_items,
)
from spyder.plugins.languageservices.services import LanguageServicesAPI

PY_SNIPPETS = SNIPPETS["python"]


@pytest.mark.parametrize("trigger", list(PY_SNIPPETS))
def test_snippet_items(trigger):
    trie = build_trie(PY_SNIPPETS)
    prefix = trigger[: random.randrange(1, len(trigger))]
    items = [i for i in snippet_items(trie, prefix) if i.filter_text == trigger]
    expected = sorted(
        (f"{trigger} ({description})", info["text"])
        for description, info in PY_SNIPPETS[trigger].items()
    )
    assert sorted((i.label, i.insert_text) for i in items) == expected
    assert all(i.insert_text_format is lsp.InsertTextFormat.Snippet for i in items)


def test_provider_completion():
    # Provider defaults must be in the configuration namespace
    configs = CONF.get("language_services", "providers", {})
    LanguageServices._merge_default_configurations(SnippetsProvider, configs)
    CONF.set("language_services", "providers", configs, notification=False)

    api = LanguageServicesAPI()
    api.register_provider(SnippetsProvider)
    uri = "file:///snippets.py"

    async def scenario():
        await api.start_provider("snippets")
        await api.open_document(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri=uri, language_id="python", version=1, text="cla\n"
                )
            )
        )
        items = await api.completion(
            lsp.CompletionParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(0, 3),
            )
        )
        assert {i.filter_text for i in items} == {"class"}
        assert all(i.data["provider"] == "snippets" for i in items)
        assert all("remove_trigger" in i.data for i in items)

        # No word under the cursor. Nothing to complete
        assert await api.completion(
            lsp.CompletionParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                position=lsp.Position(1, 0),
            )
        ) is None

    asyncio.run(scenario())

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the fallback provider."""

import asyncio
import json
import os.path as osp

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.providers.fallback.provider import (
    FallbackProvider,
    TokenIndex,
)
from spyder.plugins.languageservices.providers.fallback.tokenizer import (
    get_words,
)
from spyder.plugins.languageservices.services import LanguageServicesAPI

DATA_PATH = osp.join(osp.dirname(osp.abspath(__file__)), "data")
TOKENS_FILE = osp.join(DATA_PATH, "tokens.json")

# Extension -> Pygments lexer name of the sample files
EXTENSION_MAP = {
    "c": "C", "cpp": "C++", "css": "CSS", "erl": "Erlang", "ex": "Elixir",
    "html": "HTML", "java": "Java", "jl": "Julia", "md": "Markdown",
    "py": "Python", "R": "R",
}

TEST_FILE = """
# This is a test file
a = 2
"""


@pytest.fixture
def expected_tokens():
    with open(TOKENS_FILE) as f:
        return json.load(f)


def test_get_words():
    tokens = get_words("foo bar123 baz car456", 5, "python")
    assert set(tokens) == {"foo", "baz", "car456"}


@pytest.mark.parametrize("ext", list(EXTENSION_MAP))
def test_tokenize(expected_tokens, ext):
    filename = f"example.{ext}"
    with open(osp.join(DATA_PATH, filename)) as f:
        contents = f.read()
    index = TokenIndex(contents, EXTENSION_MAP[ext])
    tokens = {item.insert_text for item in index.completions(len(contents), "")}
    assert set(expected_tokens[filename]) <= tokens


def did_open(uri, text):
    return lsp.DidOpenTextDocumentParams(
        text_document=lsp.TextDocumentItem(
            uri=uri, language_id="python", version=1, text=text
        )
    )


def completion_at(uri, line, character):
    return lsp.CompletionParams(
        text_document=lsp.TextDocumentIdentifier(uri),
        position=lsp.Position(line, character),
    )


def test_provider_tracks_documents():
    api = LanguageServicesAPI()
    provider = api.register_provider(FallbackProvider)
    uri = "file:///test.py"

    async def scenario():
        await api.start_provider("fallback")
        assert provider.supported_languages() == frozenset(Language)
        await api.open_document(did_open(uri, TEST_FILE))
        assert uri in provider._documents

        # After "a = " there is no word under the cursor: every token
        items = await api.completion(completion_at(uri, 2, 4))
        labels = {item.label for item in items}
        assert "args" not in labels
        assert "file" in labels  # word from the comment

        new_text = "\ndef func(args):\n    pass\n"
        await api.change_document(
            lsp.DidChangeTextDocumentParams(
                text_document=lsp.VersionedTextDocumentIdentifier(
                    uri=uri, version=2
                ),
                content_changes=[
                    lsp.TextDocumentContentChangePartial(
                        range=lsp.Range(lsp.Position(3, 0), lsp.Position(3, 0)),
                        text=new_text,
                    )
                ],
            )
        )
        items = await api.completion(completion_at(uri, 6, 0))
        assert "args" in {item.label for item in items}
        assert all(item.data["provider"] == "fallback" for item in items)

        # Only words containing the word under the cursor are returned
        items = await api.completion(completion_at(uri, 2, 1))
        assert items is None or all("a" in i.label.lower() for i in items)

        await api.close_document(
            lsp.DidCloseTextDocumentParams(lsp.TextDocumentIdentifier(uri))
        )
        assert uri not in provider._documents

    asyncio.run(scenario())

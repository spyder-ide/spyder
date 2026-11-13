# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the black provider."""

import asyncio

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.languageservices.providers.black import BlackProvider

UGLY = "import os\ndef f( a,b ):\n    return a+b\nx = [1,2,\n  3]\n"

FORMATTING_OPTIONS = lsp.FormattingOptions(tab_size=4, insert_spaces=True)


def format_text(text, path, line_length, line_range=None):
    return asyncio.run(
        BlackProvider(None).format_text(text, path, line_length, line_range)
    )


def test_format_text(tmp_path):
    path = str(tmp_path / "ugly.py")
    result = format_text(UGLY, path, 79)
    assert "def f(a, b):" in result
    assert "x = [1, 2, 3]" in result
    # Already formatted text comes back unchanged
    assert format_text(result, path, 79) == result


def test_project_line_length_wins(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.black]\nline-length = 30\n")
    path = str(tmp_path / "long.py")
    text = "value = function_name(argument_one, argument_two, argument_three)\n"
    result = format_text(text, path, 120)
    assert result.count("\n") > 1, result


def test_range_formatting(tmp_path):
    path = str(tmp_path / "ugly.py")
    result = format_text(UGLY, path, 79, (2, 3))
    assert "def f(a, b):" in result
    assert "x = [1,2," in result  # outside the range, untouched


def test_syntax_error_raises(tmp_path):
    path = str(tmp_path / "broken.py")
    with pytest.raises(RuntimeError, match="black exited"):
        format_text("def (:\n", path, 79)


def test_provider_formats_open_documents(tmp_path):
    provider = BlackProvider(None)
    assert Language.PYTHON in provider.supported_languages()
    capabilities = provider.capabilities(Language.PYTHON)
    assert capabilities.document_formatting_provider
    assert capabilities.document_range_formatting_provider
    uri = path_as_uri(str(tmp_path / "doc.py"))

    async def scenario():
        formatting = lsp.DocumentFormattingParams(
            text_document=lsp.TextDocumentIdentifier(uri),
            options=FORMATTING_OPTIONS,
        )
        assert await provider.formatting(formatting) is None

        await provider.did_open(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri=uri, language_id="python", version=1, text=UGLY
                )
            )
        )
        edits = await provider.formatting(formatting)
        assert len(edits) == 1 and "def f(a, b):" in edits[0].new_text
        edits = await provider.range_formatting(
            lsp.DocumentRangeFormattingParams(
                text_document=lsp.TextDocumentIdentifier(uri),
                range=lsp.Range(lsp.Position(1, 0), lsp.Position(3, 0)),
                options=FORMATTING_OPTIONS,
            )
        )
        assert "def f(a, b):" in edits[0].new_text
        assert "x = [1,2," in edits[0].new_text

    asyncio.run(scenario())


if __name__ == "__main__":
    pytest.main()

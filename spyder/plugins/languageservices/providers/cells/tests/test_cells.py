# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the cells provider."""

import asyncio

from lsprotocol import types as lsp
import pytest

from spyder.config.manager import CONF
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.symbols import SpyderSymbolKind
from spyder.plugins.languageservices.providers.cells.provider import (
    CellsProvider,
    cell_folding_ranges,
    cell_symbols,
)

TEXT = """# %% Cell 1
a = 1
# %%% Nested
b = 2
# ---- Block one
# %%
c = 3
#### Block two
# <codecell> Code cell
d = 4
"""
URI = "file:///cells.py"


def summary(symbols):
    return [
        (s.name, int(s.kind), s.location.range.start.line, s.location.range.end.line)
        for s in symbols
    ]


def test_grouped_symbols():
    assert summary(cell_symbols(TEXT, URI, True, True)) == [
        ("Cell 1", SpyderSymbolKind.Cell, 0, 4),
        ("Nested", SpyderSymbolKind.Cell, 2, 4),
        ("Block one", SpyderSymbolKind.BlockComment, 4, 4),
        ("Unnamed cell 1", SpyderSymbolKind.Cell, 5, 9),
        ("Block two", SpyderSymbolKind.BlockComment, 7, 7),
        ("Code cell", SpyderSymbolKind.Cell, 8, 8),
    ]
    assert all(s.location.uri == URI for s in cell_symbols(TEXT, URI, True, True))


def test_ungrouped_symbols_without_comments():
    assert summary(cell_symbols(TEXT, URI, False, False)) == [
        ("Cell 1", SpyderSymbolKind.Cell, 0, 0),
        ("Nested", SpyderSymbolKind.Cell, 2, 2),
        ("Unnamed cell 1", SpyderSymbolKind.Cell, 5, 5),
        ("Code cell", SpyderSymbolKind.Cell, 8, 8),
    ]


def test_in_cells_and_unnamed_comments():
    text = "# In[3]\nx\n# In[]\n#----\n# ----\n"
    assert summary(cell_symbols(text, URI, True, True)) == [
        ("3", SpyderSymbolKind.Cell, 0, 0),
        ("Unnamed cell 1", SpyderSymbolKind.Cell, 2, 2),
        ("Unnamed comment 1", SpyderSymbolKind.BlockComment, 3, 3),
        ("Unnamed comment 2", SpyderSymbolKind.BlockComment, 4, 4),
    ]


def test_empty_and_plain_documents():
    assert cell_symbols("", URI, True, True) == []
    assert cell_symbols("x = 1\n", URI, True, True) == []
    assert cell_folding_ranges("") == []


def test_folding_ranges():
    ranges = [(r.start_line, r.end_line) for r in cell_folding_ranges(TEXT)]
    assert ranges == [(0, 4), (2, 4), (5, 9), (8, 9)]


def test_provider_answers_from_document_text():
    provider = CellsProvider(None)
    assert Language.PYTHON in provider.supported_languages()
    assert provider.capabilities(Language.PYTHON).document_symbol_provider
    CONF.set("outline_explorer", "group_cells", True)
    CONF.set("outline_explorer", "show_comments", False)

    async def scenario():
        await provider.did_open(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri=URI, language_id="python", version=1, text=TEXT
                )
            )
        )
        symbols = await provider.document_symbol(
            lsp.DocumentSymbolParams(text_document=lsp.TextDocumentIdentifier(URI))
        )
        assert [s.name for s in symbols] == [
            "Cell 1", "Nested", "Unnamed cell 1", "Code cell"
        ]
        folds = await provider.folding_range(
            lsp.FoldingRangeParams(text_document=lsp.TextDocumentIdentifier(URI))
        )
        assert len(folds) == 4
        await provider.did_change(
            lsp.DidChangeTextDocumentParams(
                text_document=lsp.VersionedTextDocumentIdentifier(uri=URI, version=2),
                content_changes=[lsp.TextDocumentContentChangeWholeDocument(text="x\n")],
            )
        )
        assert await provider.document_symbol(
            lsp.DocumentSymbolParams(text_document=lsp.TextDocumentIdentifier(URI))
        ) == []
        await provider.did_close(
            lsp.DidCloseTextDocumentParams(text_document=lsp.TextDocumentIdentifier(URI))
        )
        assert await provider.document_symbol(
            lsp.DocumentSymbolParams(text_document=lsp.TextDocumentIdentifier(URI))
        ) is None

    asyncio.run(scenario())


if __name__ == "__main__":
    pytest.main()

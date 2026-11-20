# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Code cells and block comments of Python documents.

Reports cells (``# %%``, ``# <codecell>``, ``# In[...]``) and block comments
(``# ----`` or ``####`` headers) as document symbols with Spyder's extended
symbol kinds, so the Outline pane shows them, and cells as folding ranges.
"""

from __future__ import annotations

# Standard library imports
import asyncio
import re

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.plugins.languageservices.api.documents import TextStore
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
)
from spyder.plugins.languageservices.api.symbols import SpyderSymbolKind

CELL_PERCENTAGE = re.compile(r"^[\t ]*# ?(%%+)(.*)?$")
CELL_CODECELL = re.compile(r"^[\t ]*# ?(<codecell>)(.*)?$")
CELL_IN = re.compile(r"^[\t ]*# ?(In\[)([^\]\r\n]*)?\]?$")
CELL_REGEXES = (CELL_PERCENTAGE, CELL_CODECELL, CELL_IN)

BLOCK_DASH = re.compile(r"^[\t ]*# ?-{4}([^-\n\r].*)?$")
BLOCK_HASH = re.compile(r"^[\t ]*##{3}([^\#\n\r].*)?$")
BLOCK_REGEXES = (BLOCK_DASH, BLOCK_HASH)

_NO_CELL = (None, 0, "")
"""Bottom of the cell stack: ``# %%`` has level 1, so level 0 never pops."""


def _match(regexes, line):
    for regex in regexes:
        match = regex.match(line)
        if match is not None:
            return regex, match
    return None, None


def _symbol(name, uri, start_line, end_line, kind) -> lsp.SymbolInformation:
    return lsp.SymbolInformation(
        name=name,
        kind=kind,
        container_name="",
        location=lsp.Location(
            uri=uri,
            range=lsp.Range(
                start=lsp.Position(line=start_line, character=0),
                end=lsp.Position(line=max(end_line - 1, 0), character=0),
            ),
        ),
    )


def cell_symbols(
    text: str, uri: str, group_cells: bool, block_comments: bool
) -> list[lsp.SymbolInformation]:
    """Cells and block comments of ``text``, sorted by starting line.

    With ``group_cells``, a ``# %%`` cell spans until the next cell of the
    same or a lower level (``# %%%`` is one level deeper than ``# %%``).
    Other cells and block comments span their own line.
    """
    lines = text.splitlines()
    cells: list[lsp.SymbolInformation] = []
    blocks: list[lsp.SymbolInformation] = []
    stack: list[tuple[int, int, str]] = []
    unnamed_cell = 1
    unnamed_block = 1

    for line_num, line in enumerate(lines):
        cell_rule, cell_match = _match(CELL_REGEXES, line)
        _, block_match = _match(BLOCK_REGEXES, line)
        if cell_match is not None:
            name = (cell_match.group(2) or "").strip()
            if not name:
                name = f"Unnamed cell {unnamed_cell}"
                unnamed_cell += 1
            if not group_cells or cell_rule is not CELL_PERCENTAGE:
                cells.append(
                    _symbol(name, uri, line_num, line_num + 1, SpyderSymbolKind.Cell)
                )
                continue
            level = len(cell_match.group(1)) - 1
            current_line, current_level, current_name = stack[0] if stack else _NO_CELL
            while current_level >= level:
                stack.pop(0)
                cells.append(
                    _symbol(
                        current_name, uri, current_line, line_num, SpyderSymbolKind.Cell
                    )
                )
                current_line, current_level, current_name = (
                    stack[0] if stack else _NO_CELL
                )
            stack.insert(0, (line_num, level, name))
        elif block_match is not None and block_comments:
            name = (block_match.group(1) or "").strip()
            if not name:
                name = f"Unnamed comment {unnamed_block}"
                unnamed_block += 1
            blocks.append(
                _symbol(
                    name, uri, line_num, line_num + 1, SpyderSymbolKind.BlockComment
                )
            )

    for line_num, _, name in stack:
        cells.append(_symbol(name, uri, line_num, len(lines), SpyderSymbolKind.Cell))

    return sorted(cells + blocks, key=lambda s: s.location.range.start.line)


def cell_folding_ranges(text: str) -> list[lsp.FoldingRange]:
    """Folding regions of the cells of ``text``, sorted by starting line.

    Cells other than ``# %%`` ones nest one level below the current cell.
    """
    lines = text.splitlines()
    stack: list[tuple[int, int]] = []
    regions: list[lsp.FoldingRange] = []
    for line_num, line in enumerate(lines):
        cell_rule, cell_match = _match(CELL_REGEXES, line)
        if cell_match is None:
            continue
        current_line, current_level = stack[0] if stack else _NO_CELL[:2]
        if cell_rule is CELL_PERCENTAGE:
            level = len(cell_match.group(1)) - 1
        else:
            level = current_level + 1
        while current_level >= level:
            stack.pop(0)
            regions.append(
                lsp.FoldingRange(start_line=current_line, end_line=line_num - 1)
            )
            current_line, current_level = stack[0] if stack else _NO_CELL[:2]
        stack.insert(0, (line_num, level))
    for line_num, _ in stack:
        regions.append(lsp.FoldingRange(start_line=line_num, end_line=len(lines) - 1))
    return sorted(regions, key=lambda r: r.start_line)


class CellsProvider(LanguageServicesProvider):
    """Cells and block comments as symbols and folding ranges."""

    NAME = "cells"
    PRIORITY = 5

    def __init__(self, plugin, config=None):
        super().__init__(plugin, config)
        self._documents = TextStore()

    def supported_languages(self) -> frozenset[Language]:
        return Language.from_language_id("python")

    def capabilities(self, language: Language) -> lsp.ServerCapabilities:
        return lsp.ServerCapabilities(
            document_symbol_provider=True, folding_range_provider=True
        )

    async def stop(self) -> None:
        self._documents.clear()

    # ---- Document sync ---------------------------------------------------
    async def did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
        self._documents.open(params)

    async def did_change(self, params: lsp.DidChangeTextDocumentParams) -> None:
        self._documents.change(params)

    async def did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
        self._documents.close(params)

    # ---- Features --------------------------------------------------------
    async def document_symbol(self, params: lsp.DocumentSymbolParams):
        uri = params.text_document.uri
        text = self._documents.text(uri)
        if text is None:
            return None
        group_cells = self.get_conf("group_cells", True, section="outline_explorer")
        block_comments = self.get_conf(
            "show_comments", True, section="outline_explorer"
        )
        return await asyncio.to_thread(
            cell_symbols, text, uri, group_cells, block_comments
        )

    async def folding_range(self, params: lsp.FoldingRangeParams):
        text = self._documents.text(params.text_document.uri)
        if text is None:
            return None
        return await asyncio.to_thread(cell_folding_ranges, text)

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Fallback completion provider.

Completes with the words already written in the document and the keywords
Pygments knows for its language. Serves every language.
"""

from __future__ import annotations

# Standard library imports
import asyncio
import logging

# Third party imports
from lsprotocol import types as lsp
from pygments.lexers import get_lexer_by_name

# Local imports
from spyder.plugins.languageservices.api.documents import (
    apply_content_change,
    utf16_len,
)
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
)
from spyder.plugins.languageservices.providers.fallback.tokenizer import (
    get_keywords,
    get_words,
    is_prefix_valid,
)

logger = logging.getLogger(__name__)

FALLBACK_COMPLETION = "Fallback"
"""``data["provider"]`` marker kept on items for the completion widget."""


def _offset_in_utf16(text: str, position: lsp.Position) -> int:
    """UTF-16 offset of ``position`` in ``text`` (Qt cursor semantics)."""
    lines = text.splitlines(keepends=True)
    offset = sum(utf16_len(line) for line in lines[: position.line])
    return offset + position.character


class TokenIndex:
    """Words and keywords of one document (pure computation)."""

    def __init__(self, text: str, language_id: str):
        self.text = text
        self.language_id = language_id

    def keywords(self) -> list[str]:
        try:
            return list(get_keywords(get_lexer_by_name(self.language_id)))
        except Exception:  # noqa: BLE001 - unknown lexer or lexer quirk
            return []

    def completions(
        self, offset: int, current_word: str | None
    ) -> list[lsp.CompletionItem]:
        """Items for the word at ``offset`` (UTF-16 units)."""
        if not is_prefix_valid(self.text, offset, self.language_id):
            return []

        seen: set[str] = set()
        items = []

        def add(token: str, kind: lsp.CompletionItemKind):
            if token in seen:
                return
            seen.add(token)
            items.append(
                lsp.CompletionItem(
                    label=token,
                    kind=kind,
                    insert_text=token,
                    sort_text=token,
                    filter_text=token,
                    data={"provider": FALLBACK_COMPLETION},
                )
            )

        for keyword in self.keywords():
            add(keyword, lsp.CompletionItemKind.Keyword)
        for token in get_words(self.text, offset, self.language_id):
            add(token, lsp.CompletionItemKind.Text)

        if current_word:
            needle = current_word.lower()
            items = [item for item in items if needle in item.label.lower()]
        return items


class FallbackProvider(LanguageServicesProvider):
    """Document words and Pygments keywords as completions."""

    NAME = "fallback"
    PRIORITY = 200

    def __init__(self, plugin, config=None):
        super().__init__(plugin, config)
        self._documents: dict[str, TokenIndex] = {}

    def supported_languages(self) -> frozenset[Language]:
        return frozenset(Language)

    def capabilities(self, language: Language) -> lsp.ServerCapabilities:
        return lsp.ServerCapabilities(completion_provider=lsp.CompletionOptions())

    async def stop(self) -> None:
        self._documents.clear()

    # ---- Document sync ---------------------------------------------------
    async def did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
        item = params.text_document
        self._documents[item.uri] = TokenIndex(item.text, item.language_id)

    async def did_change(self, params: lsp.DidChangeTextDocumentParams) -> None:
        index = self._documents.get(params.text_document.uri)
        if index is None:
            return
        text = index.text
        for change in params.content_changes:
            text = apply_content_change(text, change)
        index.text = text

    async def did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
        self._documents.pop(params.text_document.uri, None)

    # ---- Completion ------------------------------------------------------
    async def completion(self, params: lsp.CompletionParams):
        index = self._documents.get(params.text_document.uri)
        if index is None:
            return None
        offset = _offset_in_utf16(index.text, params.position)
        current_word = _word_before(index.text, params.position)
        return await asyncio.to_thread(index.completions, offset, current_word)


def _word_before(text: str, position: lsp.Position) -> str:
    lines = text.splitlines()
    line = lines[position.line] if position.line < len(lines) else ""
    prefix = line[: position.character]
    end = len(prefix)
    start = end
    # Like the editor's "current word" for completions, dots are part of
    # the word: "math.hy" only matches tokens containing that text.
    while start > 0 and (prefix[start - 1].isalnum() or prefix[start - 1] in "_."):
        start -= 1
    return prefix[start:end]

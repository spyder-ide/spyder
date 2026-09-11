# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Registry of open documents and their diagnostics.

Positions follow the LSP default. Lines are zero-based and characters are
UTF-16 code units.
"""

from __future__ import annotations

# Standard library imports
from dataclasses import dataclass, field
from typing import Iterable

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.plugins.languageservices.api.errors import (
    DocumentNotOpenError,
    UnknownLanguageError,
)
from spyder.plugins.languageservices.api.languages import Language


# ---- Positions -------------------------------------------------------------
def utf16_len(text: str) -> int:
    """Number of UTF-16 code units needed to encode ``text``."""
    return len(text) + sum(1 for ch in text if ord(ch) > 0xFFFF)


def utf16_offset_to_index(line: str, character: int) -> int:
    """Index in ``line`` of the UTF-16 code unit offset ``character``.

    Offsets past the end of the line clamp to its length.
    """
    units = 0
    for index, ch in enumerate(line):
        if units >= character:
            return index
        units += 2 if ord(ch) > 0xFFFF else 1
    return len(line)


def _split_lines(text: str) -> list[str]:
    """Split keeping line terminators, always yielding at least one line."""
    lines = text.splitlines(keepends=True)
    if not lines or text.endswith(("\n", "\r")):
        lines.append("")
    return lines


def offset_at(text: str, position: lsp.Position) -> int:
    """Character index in ``text`` of the UTF-16 ``position``."""
    lines = _split_lines(text)
    if position.line >= len(lines):
        return len(text)
    line = lines[position.line]
    content = line.rstrip("\r\n")
    start = sum(len(prev) for prev in lines[: position.line])
    return start + utf16_offset_to_index(content, position.character)


def apply_content_change(
    text: str, change: lsp.TextDocumentContentChangeEvent
) -> str:
    """Return ``text`` after applying one LSP content change event."""
    change_range = getattr(change, "range", None)
    if change_range is None:
        return change.text
    start = offset_at(text, change_range.start)
    end = offset_at(text, change_range.end)
    if end < start:
        raise ValueError(
            f"Change range ends before it starts: {change_range}"
        )
    return text[:start] + change.text + text[end:]


# ---- Documents -------------------------------------------------------------
@dataclass
class OpenDocument:
    """State of a document opened through the language services plugin.

    Content is not stored: the editor owns the text and re-sends ``didOpen``
    when the set of providers changes.
    """

    uri: str
    language: Language
    version: int


@dataclass
class DocumentRegistry:
    """Open documents keyed by uri and diagnostics keyed by (uri, provider).

    The registry is not thread-safe. The plugin only touches it from the
    language services loop.
    """

    documents: dict[str, OpenDocument] = field(default_factory=dict)
    diagnostics: dict[tuple[str, str], list[lsp.Diagnostic]] = field(
        default_factory=dict
    )

    # ---- Document sync ---------------------------------------------------
    def open(
        self,
        params: lsp.DidOpenTextDocumentParams,
        language: Language | None = None,
    ) -> OpenDocument:
        """Track a document.

        ``language`` disambiguates languages sharing a ``language_id``
        (IPython and Python). When omitted, the language whose name equals
        the id wins.

        Raises
        ------
        UnknownLanguageError
            If ``language_id`` matches no :class:`Language`.
        """
        item = params.text_document
        if language is None:
            language = Language.find(language_id=item.language_id)
        if language is None:
            raise UnknownLanguageError(
                f"Cannot open {item.uri!r}: unknown language_id "
                f"{item.language_id!r}"
            )
        if language.language_id != item.language_id:
            raise ValueError(
                f"{language!r} does not use language_id "
                f"{item.language_id!r}"
            )
        document = OpenDocument(item.uri, language, item.version)
        self.documents[item.uri] = document
        return document

    def change(self, params: lsp.DidChangeTextDocumentParams) -> OpenDocument:
        document = self.get(params.text_document.uri)
        document.version = params.text_document.version
        return document

    def save(self, params: lsp.DidSaveTextDocumentParams) -> OpenDocument:
        return self.get(params.text_document.uri)

    def close(self, params: lsp.DidCloseTextDocumentParams) -> OpenDocument:
        """Forget a document and every diagnostic recorded for it."""
        uri = params.text_document.uri
        document = self.get(uri)
        del self.documents[uri]
        for key in [key for key in self.diagnostics if key[0] == uri]:
            del self.diagnostics[key]
        return document

    def get(self, uri: str) -> OpenDocument:
        """Return the open document at ``uri``.

        Raises
        ------
        DocumentNotOpenError
            If ``uri`` was not opened.
        """
        try:
            return self.documents[uri]
        except KeyError:
            raise DocumentNotOpenError(
                f"Document {uri!r} is not open. Call open_document first"
            ) from None

    def language_of(self, uri: str) -> Language:
        return self.get(uri).language

    # ---- Diagnostics -----------------------------------------------------
    def set_diagnostics(
        self, uri: str, provider: str, diagnostics: list[lsp.Diagnostic]
    ) -> None:
        """Replace the diagnostics of ``provider`` for ``uri``."""
        if diagnostics:
            self.diagnostics[(uri, provider)] = list(diagnostics)
        else:
            self.diagnostics.pop((uri, provider), None)

    def diagnostics_for(self, uri: str) -> list[tuple[str, list[lsp.Diagnostic]]]:
        """``[(provider NAME, diagnostics)]`` recorded for ``uri``."""
        return [
            (provider, diagnostics)
            for (doc_uri, provider), diagnostics in self.diagnostics.items()
            if doc_uri == uri
        ]

    def clear_provider_diagnostics(
        self, provider: str, languages: Iterable[Language] | None = None
    ) -> list[str]:
        """Drop the diagnostics of ``provider`` (optionally only for some
        languages) and return the uris that had some."""
        wanted = None if languages is None else frozenset(languages)
        cleared = []
        for key in list(self.diagnostics):
            uri, name = key
            if name != provider:
                continue
            if wanted is not None:
                document = self.documents.get(uri)
                if document is None or document.language not in wanted:
                    continue
            del self.diagnostics[key]
            cleared.append(uri)
        return cleared

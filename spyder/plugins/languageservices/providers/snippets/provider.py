# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""User-defined text snippets completion provider."""

from __future__ import annotations

# Standard library imports
import logging
from dataclasses import dataclass

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.config.snippets import SNIPPETS
from spyder.plugins.languageservices.api.documents import (
    apply_content_change,
)
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
)
from spyder.plugins.languageservices.providers.snippets.conftabs import (
    SnippetsConfigTab,
)
from spyder.plugins.languageservices.providers.snippets.trie import Trie

logger = logging.getLogger(__name__)

SNIPPETS_COMPLETION = "Snippets"
"""``data["provider"]`` marker kept on items for the completion widget."""


@dataclass
class _Document:
    language_id: str
    text: str


def build_trie(snippets: dict) -> Trie:
    """Trie of ``trigger -> (trigger, descriptions)``."""
    trie = Trie()
    for trigger, descriptions in snippets.items():
        trie[trigger] = (trigger, descriptions)
    return trie


def snippet_items(trie: Trie, prefix: str) -> list[lsp.CompletionItem]:
    """Completion items of every snippet whose trigger starts with
    ``prefix``."""
    items = []
    node = trie[prefix] if prefix else None
    for entry in node or ():
        trigger, descriptions = entry.value
        for description, info in descriptions.items():
            items.append(
                lsp.CompletionItem(
                    label=f"{trigger} ({description})",
                    kind=lsp.CompletionItemKind.Snippet,
                    insert_text=info["text"],
                    insert_text_format=lsp.InsertTextFormat.Snippet,
                    sort_text=f"zzz{trigger}",
                    filter_text=trigger,
                    data={
                        "provider": SNIPPETS_COMPLETION,
                        "remove_trigger": info["remove_trigger"],
                    },
                )
            )
    return items


class SnippetsProvider(LanguageServicesProvider):
    """Snippets configured per language (option = lowercase language name)."""

    NAME = "snippets"
    PRIORITY = 300
    CONF_DEFAULTS = [(language, SNIPPETS[language]) for language in SNIPPETS]
    CONF_VERSION = "0.1.0"
    CONF_TABS = [SnippetsConfigTab]

    def __init__(self, plugin, config=None):
        super().__init__(plugin, config)
        self._tries: dict[str, Trie] = {}
        self._documents: dict[str, _Document] = {}

    def supported_languages(self) -> frozenset[Language]:
        return frozenset(Language)

    def capabilities(self, language: Language) -> lsp.ServerCapabilities:
        return lsp.ServerCapabilities(completion_provider=lsp.CompletionOptions())

    async def start(self) -> None:
        self.reload_snippets()

    def reload_snippets(self) -> None:
        """Rebuild the tries from the configuration."""
        self._tries = {}
        for language in Language:
            key = language.name.lower()
            snippets = self.get_conf(key, {}) or {}
            if snippets:
                self._tries[key] = build_trie(snippets)

    @on_conf_change(option="__section")
    def _on_snippets_changed(self, value):
        self.reload_snippets()

    # ---- Document sync ---------------------------------------------------
    async def did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
        item = params.text_document
        self._documents[item.uri] = _Document(item.language_id, item.text)

    async def did_change(self, params: lsp.DidChangeTextDocumentParams) -> None:
        document = self._documents.get(params.text_document.uri)
        if document is None:
            return
        for change in params.content_changes:
            document.text = apply_content_change(document.text, change)

    async def did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
        self._documents.pop(params.text_document.uri, None)

    # ---- Completion ------------------------------------------------------
    async def completion(self, params: lsp.CompletionParams):
        document = self._documents.get(params.text_document.uri)
        if document is None:
            return None
        language_id = document.language_id
        lines = document.text.splitlines()
        line = lines[params.position.line] if params.position.line < len(lines) else ""
        prefix = line[: params.position.character]
        end = len(prefix)
        start = end
        # Dots belong to the word, as in the editor's completion prefix
        while start > 0 and (prefix[start - 1].isalnum() or prefix[start - 1] in "_."):
            start -= 1
        word = prefix[start:end]
        if not word:
            return None
        items = []
        for language in Language.from_language_id(language_id):
            trie = self._tries.get(language.name.lower())
            if trie is not None:
                items.extend(snippet_items(trie, word))
        return items or None

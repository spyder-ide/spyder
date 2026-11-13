# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Base of the providers that format documents with an external command."""

from __future__ import annotations

# Standard library imports
import asyncio
import os.path as osp

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.plugins.languageservices.api.documents import TextStore
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
)
from spyder.plugins.languageservices.api.uri import uri_as_path


def whole_document_edit(text: str, formatted: str) -> list[lsp.TextEdit]:
    """Edits replacing ``text`` with ``formatted`` (none when equal)."""
    if formatted == text:
        return []
    return [
        lsp.TextEdit(
            range=lsp.Range(
                start=lsp.Position(line=0, character=0),
                end=lsp.Position(line=len(text.splitlines()), character=0),
            ),
            new_text=formatted,
        )
    ]


def line_range_of(selection: lsp.Range) -> tuple[int, int]:
    """One-based inclusive lines covered by ``selection``.

    A selection ending at the start of a line does not include that line.
    """
    start = selection.start.line + 1
    end = selection.end.line + 1
    if selection.end.character == 0 and end > start:
        end -= 1
    return start, end


class SubprocessFormatterProvider(LanguageServicesProvider):
    """Formats Python documents by piping their text through a command.

    Subclasses build the command with :meth:`command`. The command runs in
    the directory of the document, reads the text on standard input and
    writes the formatted text on standard output. The result replaces the
    whole document.
    """

    PRIORITY = 2
    CONF_VERSION = "0.1.0"

    def __init__(self, plugin, config=None):
        super().__init__(plugin, config)
        self._documents = TextStore()
        self._locks: dict[str, asyncio.Lock] = {}

    def command(
        self, path: str, line_length: int, line_range: tuple[int, int] | None
    ) -> list[str]:
        """Command formatting the text of the file at ``path``.

        ``line_range`` is one-based and inclusive, ``None`` formats the
        whole text.
        """
        raise NotImplementedError

    async def format_text(
        self,
        text: str,
        path: str,
        line_length: int,
        line_range: tuple[int, int] | None = None,
    ) -> str:
        """Return ``text`` formatted by :meth:`command`.

        ``path`` locates the project configuration the formatter reads.

        Raises
        ------
        RuntimeError
            If the command exits with a non-zero status. The message holds
            its standard error output.
        """
        process = await asyncio.create_subprocess_exec(
            *self.command(path, line_length, line_range),
            cwd=osp.dirname(path) or None,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await process.communicate(text.encode("utf-8"))
        except BaseException:
            process.kill()
            await process.wait()
            raise
        if process.returncode != 0:
            raise RuntimeError(
                f"{self.NAME} exited with status {process.returncode}:\n"
                + stderr.decode("utf-8", errors="replace")
            )
        return stdout.decode("utf-8")

    def supported_languages(self) -> frozenset[Language]:
        return Language.from_language_id("python")

    def capabilities(self, language: Language) -> lsp.ServerCapabilities:
        return lsp.ServerCapabilities(
            document_formatting_provider=True,
            document_range_formatting_provider=True,
        )

    async def stop(self) -> None:
        self._documents.clear()
        self._locks.clear()

    # ---- Document sync ---------------------------------------------------
    async def did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
        self._documents.open(params)

    async def did_change(self, params: lsp.DidChangeTextDocumentParams) -> None:
        self._documents.change(params)

    async def did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
        self._documents.close(params)
        self._locks.pop(params.text_document.uri, None)

    # ---- Features --------------------------------------------------------
    async def _format(self, uri: str, line_range) -> list[lsp.TextEdit] | None:
        text = self._documents.text(uri)
        if text is None:
            return None
        line_length = self.get_conf("line_length", section="editor")
        lock = self._locks.setdefault(uri, asyncio.Lock())
        async with lock:
            formatted = await self.format_text(
                text, uri_as_path(uri), line_length, line_range
            )
        return whole_document_edit(text, formatted)

    async def formatting(self, params: lsp.DocumentFormattingParams):
        return await self._format(params.text_document.uri, None)

    async def range_formatting(self, params: lsp.DocumentRangeFormattingParams):
        return await self._format(
            params.text_document.uri, line_range_of(params.range)
        )

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language services provider wrapping the legacy completion plugin.

:class:`LegacyCompletionsProvider` exposes every
:class:`~spyder.plugins.completion.api.SpyderCompletionProvider` loaded by
:class:`~spyder.plugins.completion.plugin.CompletionPlugin` as a single
:class:`~spyder.plugins.languageservices.api.provider.LanguageServicesProvider`.
Typed ``lsprotocol`` params are translated to the string-keyed dicts of the
legacy request API and answers are translated back.

The legacy plugin and its providers only work on the Qt main thread, so
every call into them is posted there and awaited from the language
services loop.
"""

from __future__ import annotations

# Standard library imports
import asyncio
import logging
import re
from collections.abc import Callable
from typing import Any

# Third party imports
from lsprotocol import types as lsp
from qtpy.QtCore import QCoreApplication, QEvent, QObject, Slot

# Local imports
from spyder.plugins.completion.api import WorkspaceUpdateKind
from spyder.plugins.languageservices.api.documents import (
    apply_content_change,
    offset_at,
)
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    LanguageServicesProvider,
)
from spyder.plugins.languageservices.api.uri import uri_as_path as process_uri

logger = logging.getLogger(__name__)


# ---- Main thread execution -------------------------------------------------
class _CallEvent(QEvent):
    TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, func: Callable[[], Any], future: asyncio.Future):
        super().__init__(self.TYPE)
        self.func = func
        self.future = future


class _MainThreadExecutor(QObject):
    """Runs callables posted from other threads on the Qt main thread."""

    def customEvent(self, event: QEvent):  # noqa: N802
        if not isinstance(event, _CallEvent):
            return
        future, loop = event.future, event.future.get_loop()
        try:
            result = event.func()
        except BaseException as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(_set_future, future, None, exc)
        else:
            loop.call_soon_threadsafe(_set_future, future, result, None)


def _set_future(future: asyncio.Future, result, exc):
    if future.cancelled():
        return
    if exc is not None:
        future.set_exception(exc)
    else:
        future.set_result(result)


_executor: _MainThreadExecutor | None = None


def _main_thread_executor() -> _MainThreadExecutor:
    global _executor
    if _executor is None:
        _executor = _MainThreadExecutor()
        _executor.moveToThread(QCoreApplication.instance().thread())
    return _executor


async def run_in_main_thread(func: Callable[[], Any]) -> Any:
    """Await ``func()`` executed on the Qt main thread."""
    future = asyncio.get_running_loop().create_future()
    QCoreApplication.postEvent(_main_thread_executor(), _CallEvent(func, future))
    return await future


# ---- Legacy response plumbing ----------------------------------------------
class _Responder(QObject):
    """Receives one legacy ``handle_response`` call and resolves a future."""

    def __init__(self, future: asyncio.Future):
        super().__init__()
        self.future = future

    @Slot(str, object)
    def handle_response(self, method: str, params: Any) -> None:
        self.future.get_loop().call_soon_threadsafe(
            _set_future, self.future, params, None
        )


class _DocumentProxy(QObject):
    """Stand-in for the ``CodeEditor`` legacy providers register per file.

    The legacy LSP client pushes ``publishDiagnostics`` straight to the
    registered editor. The proxy turns them into the provider's
    :attr:`sig_diagnostics`.
    """

    def __init__(self, provider: LegacyCompletionsProvider, uri: str):
        # The proxy has no Qt parent. It is created on the services thread
        # and only called (never owned) from the main thread.
        super().__init__()
        self.provider = provider
        self.uri = uri
        self.filename = process_uri(uri)
        self.text = ""
        """Current content, tracked for legacy providers' offsets and
        prefixes. Legacy providers receive the text anyway."""

    @Slot(str, object)
    def handle_response(self, method: str, params: Any) -> None:
        if method == lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS:
            self.provider.sig_diagnostics.emit(
                lsp.PublishDiagnosticsParams(
                    uri=self.uri, diagnostics=list(params or [])
                )
            )


def _position_params(params, offset: int) -> dict[str, Any]:
    return {
        "file": process_uri(params.text_document.uri),
        "line": params.position.line,
        "column": params.position.character,
        "offset": offset,
        "selection_start": offset,
        "selection_end": offset,
    }


def _formatting_options(options: lsp.FormattingOptions) -> dict[str, Any]:
    data = {
        "tab_size": options.tab_size,
        "insert_spaces": options.insert_spaces,
    }
    for key in (
        "trim_trailing_whitespace",
        "insert_final_newline",
        "trim_final_newlines",
    ):
        value = getattr(options, key, None)
        if value is not None:
            data[key] = value
    return data


class LegacyCompletionsProvider(LanguageServicesProvider):
    """Every ``spyder.completions`` provider, seen as one language services
    provider named ``"completions"``.

    Diagnostics reach the plugin only for documents opened through it. The
    legacy providers' own merge and priority settings still apply among
    themselves before the merged answer joins the other language services
    providers.
    """

    NAME = "completions"
    PRIORITY = 150

    def __init__(self, plugin, completion_plugin):
        super().__init__(plugin)
        self.completion_plugin = completion_plugin
        self._capabilities: dict[Language, lsp.ServerCapabilities] = {}
        self._languages: set[Language] = set()
        self._documents: dict[str, _DocumentProxy] = {}
        self._pending: set[_Responder] = set()

        completion_plugin.sig_language_completions_available.connect(
            self._on_language_available
        )
        completion_plugin.sig_stop_completions.connect(
            self._on_language_stopped
        )
        completion_plugin.sig_open_file.connect(self.sig_open_file_requested)

    # ---- Languages -------------------------------------------------------
    @staticmethod
    def _legacy_name(language: Language) -> str:
        return language.name.lower()

    def _language_from_legacy(self, name: str) -> Language | None:
        language = Language.find(name=name)
        if language is None:
            logger.warning("Legacy completions use unknown language %r", name)
        return language

    def supported_languages(self) -> frozenset[Language]:
        return frozenset(self._languages)

    COMPLETION_ONLY = lsp.ServerCapabilities(
        completion_provider=lsp.CompletionOptions()
    )
    """Capabilities of legacy providers that never announce theirs
    (fallback, snippets). They only answer completion requests."""

    def capabilities(self, language: Language) -> lsp.ServerCapabilities | None:
        return self._capabilities.get(language, self.COMPLETION_ONLY)

    @Slot(object, str)
    def _on_language_available(self, capabilities, name: str):
        language = self._language_from_legacy(name)
        if language is None:
            return
        self._capabilities[language] = capabilities
        self._languages.add(language)
        self.sig_capabilities_changed.emit(language, capabilities)

    @Slot(str)
    def _on_language_stopped(self, name: str):
        language = self._language_from_legacy(name)
        if language is None:
            return
        self._capabilities.pop(language, None)
        if self.completion_plugin.is_fallback_only(name):
            self._languages.discard(language)
        self.sig_capabilities_changed.emit(
            language, self._capabilities.get(language)
        )

    def _running_capabilities(self, name: str):
        """Capabilities of a legacy language server already running for
        ``name``. They were announced before this provider existed."""
        for info in self.completion_plugin.providers.values():
            clients = getattr(info["instance"], "clients", None) or {}
            client = (clients.get(name) or {}).get("instance")
            capabilities = getattr(client, "server_capabilites", None)
            if capabilities is not None:
                return capabilities
        return None

    async def start_language(self, language: Language) -> None:
        name = self._legacy_name(language)

        def start():
            started = (
                self.completion_plugin.start_completion_services_for_language(
                    name
                )
            )
            if started:
                self._languages.add(language)
                if language not in self._capabilities:
                    capabilities = self._running_capabilities(name)
                    if capabilities is not None:
                        self._capabilities[language] = capabilities
                        self.sig_capabilities_changed.emit(
                            language, capabilities
                        )
            return started

        await run_in_main_thread(start)

    async def stop_language(self, language: Language) -> None:
        name = self._legacy_name(language)

        def stop():
            if name in self.completion_plugin.language_status:
                self.completion_plugin.stop_completion_services_for_language(
                    name
                )
            self._languages.discard(language)
            self._capabilities.pop(language, None)

        await run_in_main_thread(stop)

    async def stop(self) -> None:
        for language in list(self._languages):
            await self.stop_language(language)

    # ---- Legacy calls ----------------------------------------------------
    def _language_of(self, uri: str) -> str:
        return self._documents[uri].language

    async def _notify(self, uri: str, method: str, params: dict) -> None:
        """Send a document notification to the legacy providers.

        Legacy providers receive document notifications through
        ``send_request`` (the only entry point for document notifications),
        which needs a ``response_instance``. The document proxy plays that
        role.
        """
        proxy = self._documents.get(uri)
        if proxy is None:
            return
        params["response_instance"] = proxy
        params["requires_response"] = False
        await run_in_main_thread(
            lambda: self.completion_plugin.send_request(
                proxy.language, method, params
            )
        )

    async def _request(self, uri: str, method: str, params: dict) -> Any:
        language = self._language_of(uri)
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        responder = _Responder(future)
        self._pending.add(responder)
        params["response_instance"] = responder
        params["requires_response"] = True
        try:
            await run_in_main_thread(
                lambda: self.completion_plugin.send_request(
                    language, method, params
                )
            )
            return await future
        finally:
            self._pending.discard(responder)

    # ---- Document sync ---------------------------------------------------
    async def did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
        item = params.text_document
        language = self.plugin.services_api.documents.language_of(item.uri)
        proxy = _DocumentProxy(self, item.uri)
        proxy.language = self._legacy_name(language)
        proxy.text = item.text
        self._documents[item.uri] = proxy
        legacy = {
            "file": proxy.filename,
            "language": item.language_id,
            "version": item.version,
            "text": item.text,
            "codeeditor": proxy,
            "offset": 0,
            "selection_start": 0,
            "selection_end": 0,
        }

        await run_in_main_thread(
            lambda: self.completion_plugin.register_file(
                proxy.language, proxy.filename, proxy
            )
        )
        await self._notify(item.uri, lsp.TEXT_DOCUMENT_DID_OPEN, legacy)

    async def did_change(
        self, params: lsp.DidChangeTextDocumentParams
    ) -> None:
        uri = params.text_document.uri
        proxy = self._documents.get(uri)
        if proxy is not None:
            for change in params.content_changes:
                proxy.text = apply_content_change(proxy.text, change)
        await self._notify(
            uri,
            lsp.TEXT_DOCUMENT_DID_CHANGE,
            {
                "file": process_uri(uri),
                "version": params.text_document.version,
                "content_changes": list(params.content_changes),
            },
        )

    async def did_save(self, params: lsp.DidSaveTextDocumentParams) -> None:
        uri = params.text_document.uri
        legacy = {"file": process_uri(uri)}
        if params.text is not None:
            legacy["text"] = params.text
            proxy = self._documents.get(uri)
            if proxy is not None:
                proxy.text = params.text
        await self._notify(uri, lsp.TEXT_DOCUMENT_DID_SAVE, legacy)

    async def did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
        uri = params.text_document.uri
        if uri not in self._documents:
            return
        proxy = self._documents[uri]
        await self._notify(
            uri,
            lsp.TEXT_DOCUMENT_DID_CLOSE,
            {"file": proxy.filename, "codeeditor": proxy},
        )
        del self._documents[uri]

    # ---- Features --------------------------------------------------------
    async def completion(self, params: lsp.CompletionParams):
        uri = params.text_document.uri
        proxy = self._documents.get(uri)
        if proxy is None:
            return None
        lines = proxy.text.splitlines()
        line = (
            lines[params.position.line]
            if params.position.line < len(lines)
            else ""
        )
        prefix = line[: params.position.character]
        current_word = re.search(r"\w*$", prefix).group()
        legacy = self._position_params(params)
        legacy["current_word"] = current_word
        result = await self._request(uri, lsp.TEXT_DOCUMENT_COMPLETION, legacy)
        return list(result) if result else None

    async def resolve_completion_item(self, item: lsp.CompletionItem):
        data = item.data if isinstance(item.data, dict) else {}
        uri = data.get("uri")
        if uri is None:
            return None
        return await self._request(
            uri,
            lsp.COMPLETION_ITEM_RESOLVE,
            {"file": process_uri(uri), "completion_item": item},
        )

    def _position_params(self, params) -> dict[str, Any]:
        proxy = self._documents[params.text_document.uri]
        offset = offset_at(proxy.text, params.position)
        return _position_params(params, offset)

    async def hover(self, params: lsp.HoverParams):
        result = await self._request(
            params.text_document.uri,
            lsp.TEXT_DOCUMENT_HOVER,
            self._position_params(params),
        )
        if not result:
            return None
        if isinstance(result, lsp.Hover):
            return result
        return lsp.Hover(contents=str(result))

    async def signature_help(self, params: lsp.SignatureHelpParams):
        return await self._request(
            params.text_document.uri,
            lsp.TEXT_DOCUMENT_SIGNATURE_HELP,
            self._position_params(params),
        )

    async def definition(self, params: lsp.DefinitionParams):
        result = await self._request(
            params.text_document.uri,
            lsp.TEXT_DOCUMENT_DEFINITION,
            self._position_params(params),
        )
        if result is None:
            return None
        return result if isinstance(result, list) else [result]

    async def document_symbol(self, params: lsp.DocumentSymbolParams):
        uri = params.text_document.uri
        return await self._request(
            uri, lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL, {"file": process_uri(uri)}
        )

    async def folding_range(self, params: lsp.FoldingRangeParams):
        uri = params.text_document.uri
        return await self._request(
            uri, lsp.TEXT_DOCUMENT_FOLDING_RANGE, {"file": process_uri(uri)}
        )

    async def formatting(self, params: lsp.DocumentFormattingParams):
        uri = params.text_document.uri
        return await self._request(
            uri,
            lsp.TEXT_DOCUMENT_FORMATTING,
            {
                "file": process_uri(uri),
                "options": _formatting_options(params.options),
            },
        )

    async def range_formatting(self, params: lsp.DocumentRangeFormattingParams):
        uri = params.text_document.uri
        rng = params.range
        return await self._request(
            uri,
            lsp.TEXT_DOCUMENT_RANGE_FORMATTING,
            {
                "file": process_uri(uri),
                "options": _formatting_options(params.options),
                "range": {
                    "start": {
                        "line": rng.start.line,
                        "character": rng.start.character,
                    },
                    "end": {
                        "line": rng.end.line,
                        "character": rng.end.character,
                    },
                },
            },
        )

    # ---- Workspace -------------------------------------------------------
    async def did_change_workspace_folders(
        self, params: lsp.DidChangeWorkspaceFoldersParams
    ) -> None:
        def update():
            plugin = self.completion_plugin
            for folder in params.event.added:
                plugin.project_path_update(
                    process_uri(folder.uri), WorkspaceUpdateKind.ADDITION
                )
            for folder in params.event.removed:
                plugin.project_path_update(
                    process_uri(folder.uri), WorkspaceUpdateKind.DELETION
                )

        await run_in_main_thread(update)

    async def did_change_watched_files(
        self, params: lsp.DidChangeWatchedFilesParams
    ) -> None:
        legacy = {
            "params": [
                {"file": process_uri(change.uri), "kind": int(change.type)}
                for change in params.changes
            ]
        }
        await run_in_main_thread(
            lambda: self.completion_plugin.broadcast_notification(
                lsp.WORKSPACE_DID_CHANGE_WATCHED_FILES, legacy
            )
        )


# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Provider registry, request fan-out and response merging.

:class:`LanguageServicesAPI` holds the providers and the open documents and
implements every feature as a coroutine that asks the providers serving the
document's language and merges their answers according to the request
policies. Its coroutines run on the language services event loop. The
plugin wraps them for Qt callers.
"""

from __future__ import annotations

# Standard library imports
import asyncio
import logging
import threading
import traceback
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

# Third party imports
import attrs
from lsprotocol import types as lsp
from qtpy.QtCore import QObject, Qt, Signal

# Local imports
from spyder.plugins.languageservices.api.documents import DocumentRegistry
from spyder.plugins.languageservices.api.errors import (
    ProviderAlreadyRegisteredError,
    ProviderError,
    ProviderNotFoundError,
)
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.policies import (
    DEFAULT_FEATURE_POLICIES,
    RequestMode,
    RequestPolicy,
    feature_name,
    merge_strategy,
)
from spyder.plugins.languageservices.api.provider import (
    CAPABILITY_ATTRIBUTES,
    FEATURE_METHODS,
    LanguageServicesProvider,
    ProviderConfigAccessor,
    ProviderStatus,
    supports_method,
)

logger = logging.getLogger(__name__)

LANGUAGE_SERVICES_LOOP = "language_services"
"""Identifier of the :class:`~spyder.api.asyncdispatcher.AsyncDispatcher`
loop running provider coroutines."""

DEFAULT_REQUEST_TIMEOUT_MS = 5000

SHORT_FEATURE_DEBOUNCE_S = 0.010
LONG_FEATURE_DEBOUNCE_S = 0.050

_NO_DOCUMENT_METHODS = frozenset(
    {
        lsp.COMPLETION_ITEM_RESOLVE,
        lsp.WORKSPACE_SYMBOL,
        lsp.WORKSPACE_EXECUTE_COMMAND,
    }
)


def exception_report(
    provider: str, method: str, exc: BaseException
) -> dict[str, Any]:
    """Error data for ``sig_exception_occurred`` (see the error dialog)."""
    text = "".join(traceback.format_exception(exc))
    return {
        "text": text,
        "is_traceback": True,
        "repo": "spyder-ide/spyder",
        "title": f"Language services provider {provider!r} failed ({method})",
        "label": "",
        "steps": "",
    }


# ---- Capabilities ----------------------------------------------------------
def _union_lists(values: Iterable[list | None]) -> list | None:
    merged: list = []
    found = False
    for value in values:
        if value is None:
            continue
        found = True
        for item in value:
            if item not in merged:
                merged.append(item)
    return merged if found else None


def _merge_option(attribute: str, values: list[Any]) -> Any:
    """Union of one ``ServerCapabilities`` attribute across providers."""
    truthy = [value for value in values if value]
    if not truthy:
        return None
    objects = [value for value in truthy if not isinstance(value, bool)]
    if not objects:
        return True
    first = objects[0]
    if attribute == "completion_provider":
        return attrs.evolve(
            first,
            trigger_characters=_union_lists(
                getattr(o, "trigger_characters", None) for o in objects
            ),
            all_commit_characters=_union_lists(
                getattr(o, "all_commit_characters", None) for o in objects
            ),
            resolve_provider=any(
                getattr(o, "resolve_provider", False) for o in objects
            ),
        )
    if attribute == "signature_help_provider":
        return attrs.evolve(
            first,
            trigger_characters=_union_lists(
                getattr(o, "trigger_characters", None) for o in objects
            ),
            retrigger_characters=_union_lists(
                getattr(o, "retrigger_characters", None) for o in objects
            ),
        )
    return first


def _sync_kind(value: Any) -> lsp.TextDocumentSyncKind | None:
    if value is None:
        return None
    if isinstance(value, lsp.TextDocumentSyncOptions):
        return value.change
    return lsp.TextDocumentSyncKind(value)


def merge_capabilities(
    capabilities: list[lsp.ServerCapabilities | None],
) -> lsp.ServerCapabilities | None:
    """Union of several providers' capabilities for one language.

    A feature is enabled if any provider enables it. Option objects are
    unioned field-wise. ``text_document_sync`` is the strictest kind among
    providers (``Incremental`` wins over ``Full``). ``position_encoding``
    is always UTF-16.
    """
    known = [c for c in capabilities if c is not None]
    if not known:
        return None
    merged: dict[str, Any] = {}
    for attribute in set(CAPABILITY_ATTRIBUTES.values()):
        merged[attribute] = _merge_option(
            attribute, [getattr(c, attribute, None) for c in known]
        )
    kinds = [_sync_kind(c.text_document_sync) for c in known]
    kinds = [k for k in kinds if k is not None]
    sync = None
    if lsp.TextDocumentSyncKind.Incremental in kinds:
        sync = lsp.TextDocumentSyncKind.Incremental
    elif lsp.TextDocumentSyncKind.Full in kinds:
        sync = lsp.TextDocumentSyncKind.Full
    elif kinds:
        sync = lsp.TextDocumentSyncKind.None_
    return lsp.ServerCapabilities(
        position_encoding=lsp.PositionEncodingKind.Utf16,
        text_document_sync=sync,
        **merged,
    )


# ---- Registry --------------------------------------------------------------
@dataclass
class _ProviderState:
    provider: LanguageServicesProvider
    started: bool = False
    languages: frozenset[Language] = frozenset()
    """Languages announced to consumers (capabilities emitted)."""


class LanguageServicesAPI(QObject):
    """Providers, open documents and the request coroutines.

    Parameters
    ----------
    get_conf: Callable[[option, default], Any]
        Reads options of the ``language_services`` section (request
        policies and the default timeout).
    plugin: QObject | None
        Owner passed to providers at instantiation.
    """

    sig_diagnostics = Signal(object)
    """Merged diagnostics of a document (``PublishDiagnosticsParams``)."""

    sig_apply_edit = Signal(object)
    sig_show_message = Signal(object)
    sig_log_message = Signal(object)
    sig_open_file_requested = Signal(str)
    sig_exception_occurred = Signal(dict)

    sig_capabilities_changed = Signal(object, object)
    """``(Language, merged ServerCapabilities | None)``.

    Also emitted, with unchanged capabilities, when a provider starts serving
    the language: document owners re-send ``didOpen`` so the new provider
    receives the open documents.
    """

    sig_language_stopped = Signal(object)
    """No provider serves the ``Language`` any more."""

    sig_provider_status_changed = Signal(str, object, str)
    """``(provider NAME, Language, ProviderStatus)``."""

    def __init__(
        self,
        get_conf: Callable[[Any, Any], Any] | None = None,
        plugin: QObject | None = None,
    ):
        super().__init__(plugin)
        self.plugin = plugin
        self._get_conf = get_conf or (lambda option, default: default)
        self._providers: dict[str, _ProviderState] = {}
        self.documents = DocumentRegistry()
        self._lock = threading.RLock()
        self._capabilities_cache: dict[Language, lsp.ServerCapabilities | None] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    # ---- Providers -------------------------------------------------------
    def register_provider(
        self,
        provider: LanguageServicesProvider | type[LanguageServicesProvider],
    ) -> LanguageServicesProvider:
        """Add a provider (not yet started).

        Raises
        ------
        ProviderAlreadyRegisteredError
            If a provider with the same NAME exists.
        """
        if isinstance(provider, type):
            provider = provider(
                self.plugin, ProviderConfigAccessor(provider.NAME)
            )
        if provider.NAME in self._providers:
            raise ProviderAlreadyRegisteredError(
                f"Provider {provider.NAME!r} is already registered"
            )
        self._providers[provider.NAME] = _ProviderState(provider)
        self._connect_provider(provider)
        return provider

    def unregister_provider(self, name: str) -> LanguageServicesProvider:
        """Remove a provider. It must be stopped first."""
        state = self._state(name)
        if state.started:
            raise ProviderError(
                f"Provider {name!r} must be stopped before unregistering"
            )
        self._disconnect_provider(state.provider)
        del self._providers[name]
        return state.provider

    def get_provider(self, name: str) -> LanguageServicesProvider:
        return self._state(name).provider

    def provider_names(self) -> list[str]:
        """Registered provider NAMEs in priority order."""
        return [state.provider.NAME for state in self._sorted_states()]

    def is_started(self, name: str) -> bool:
        return self._state(name).started

    def _state(self, name: str) -> _ProviderState:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ProviderNotFoundError(
                f"No provider named {name!r}"
            ) from exc

    def _sorted_states(self) -> list[_ProviderState]:
        return sorted(
            self._providers.values(),
            key=lambda state: (state.provider.PRIORITY, state.provider.NAME),
        )

    def _connect_provider(self, provider: LanguageServicesProvider) -> None:
        # These are direct connections. Handlers run on the emitting thread
        # and guard shared state with ``self._lock``. Consumers of this
        # object's own signals get queued delivery to their thread as usual.
        direct = Qt.DirectConnection
        provider.sig_diagnostics.connect(
            lambda params, p=provider: self._on_provider_diagnostics(p, params),
            direct,
        )
        provider.sig_capabilities_changed.connect(
            lambda language, caps, p=provider: (
                self._on_provider_capabilities(p, language, caps)
            ),
            direct,
        )
        provider.sig_status_changed.connect(
            lambda language, status, p=provider: (
                self.sig_provider_status_changed.emit(p.NAME, language, status)
            ),
            direct,
        )
        provider.sig_apply_edit.connect(self.sig_apply_edit, direct)
        provider.sig_show_message.connect(self.sig_show_message, direct)
        provider.sig_log_message.connect(self.sig_log_message, direct)
        provider.sig_open_file_requested.connect(
            self.sig_open_file_requested, direct
        )
        provider.sig_exception_occurred.connect(
            self.sig_exception_occurred, direct
        )

    def _disconnect_provider(self, provider: LanguageServicesProvider) -> None:
        for signal in (
            provider.sig_diagnostics,
            provider.sig_capabilities_changed,
            provider.sig_status_changed,
            provider.sig_apply_edit,
            provider.sig_show_message,
            provider.sig_log_message,
            provider.sig_open_file_requested,
            provider.sig_exception_occurred,
        ):
            try:
                signal.disconnect()
            except (TypeError, RuntimeError):
                pass

    # ---- Lifecycle -------------------------------------------------------
    async def start_provider(self, name: str) -> None:
        """Start a registered provider and announce the languages it serves.

        ``sig_capabilities_changed`` fires for each language the provider
        serves, so document owners re-send ``didOpen`` to it.

        Exceptions raised by ``provider.start()`` are reported through
        :attr:`sig_exception_occurred` and re-raised. The provider stays
        stopped.
        """
        state = self._state(name)
        if state.started:
            return
        self._loop = asyncio.get_running_loop()
        provider = state.provider
        try:
            await provider.start()
        except Exception as exc:
            logger.exception("Provider %r failed to start", name)
            self.sig_exception_occurred.emit(
                exception_report(name, "start", exc)
            )
            raise
        state.started = True
        self._announce_languages(state)

    async def stop_provider(self, name: str) -> None:
        """Stop a provider, clearing its diagnostics and capabilities."""
        state = self._state(name)
        if not state.started:
            return
        provider = state.provider
        state.started = False
        try:
            await provider.stop()
        finally:
            self._clear_provider_diagnostics(provider.NAME, None)
            self._announce_languages(state)

    async def start_language(self, language: Language) -> None:
        """Ask every started provider of ``language`` to serve it."""
        for state in self._sorted_states():
            if not state.started:
                continue
            await state.provider.start_language(language)
            self._announce_languages(state)

    async def stop_language(self, language: Language) -> None:
        """Ask every started provider to stop serving ``language``."""
        for state in self._sorted_states():
            if not state.started:
                continue
            await state.provider.stop_language(language)
            self._clear_provider_diagnostics(state.provider.NAME, {language})
            self._announce_languages(state)

    def _announce_languages(self, state: _ProviderState) -> frozenset[Language]:
        """Refresh merged capabilities of the languages ``state`` gained or
        lost, emit the corresponding signals and return the gained ones.

        A newly served language emits ``sig_capabilities_changed`` even when
        the merged capabilities are unchanged, so document owners re-send
        ``didOpen`` to the provider that just started serving it.
        """
        provider = state.provider
        current = provider.supported_languages() if state.started else frozenset()
        gained = frozenset(current) - state.languages
        changed = set(state.languages) | set(current)
        state.languages = frozenset(current)
        for language in changed:
            self._refresh_capabilities(language, force=language in gained)
        return gained

    # ---- Queries ---------------------------------------------------------
    def supported_languages(self) -> frozenset[Language]:
        """Languages served by at least one started provider."""
        languages: set[Language] = set()
        for state in self._providers.values():
            if state.started:
                languages |= state.provider.supported_languages()
        return frozenset(languages)

    def is_language_supported(self, language: Language) -> bool:
        return any(
            state.started and language in state.provider.supported_languages()
            for state in self._providers.values()
        )

    def providers_for(
        self, language: Language, method: str | None = None
    ) -> list[LanguageServicesProvider]:
        """Started providers serving ``language`` (and ``method``), in
        priority order."""
        providers = []
        for state in self._sorted_states():
            provider = state.provider
            if not state.started:
                continue
            if language not in provider.supported_languages():
                continue
            if method is not None and not supports_method(
                provider.capabilities(language), method
            ):
                continue
            providers.append(provider)
        return providers

    def capabilities(self, language: Language) -> lsp.ServerCapabilities | None:
        """Merged capabilities of the providers serving ``language``.

        ``None`` only when no started provider serves the language. Served
        languages whose providers report nothing get empty capabilities.
        """
        with self._lock:
            if language not in self._capabilities_cache:
                providers = self.providers_for(language)
                merged = merge_capabilities(
                    [p.capabilities(language) for p in providers]
                )
                if merged is None and providers:
                    merged = lsp.ServerCapabilities(
                        position_encoding=lsp.PositionEncodingKind.Utf16
                    )
                self._capabilities_cache[language] = merged
            return self._capabilities_cache[language]

    def _refresh_capabilities(
        self, language: Language, force: bool = False
    ) -> None:
        with self._lock:
            served = self.is_language_supported(language)
            was_cached = language in self._capabilities_cache
            previous = self._capabilities_cache.pop(language, None)
            current = self.capabilities(language) if served else None
        if served:
            if force or not was_cached or current != previous:
                self.sig_capabilities_changed.emit(language, current)
        else:
            self.sig_capabilities_changed.emit(language, None)
            self.sig_language_stopped.emit(language)

    # ---- Policies --------------------------------------------------------
    def request_timeout(self) -> float:
        """Default per-provider timeout, in seconds."""
        ms = self._get_conf("request_timeout_ms", DEFAULT_REQUEST_TIMEOUT_MS)
        return ms / 1000

    def policy_for(self, method: str) -> RequestPolicy:
        """Effective policy of an LSP request ``method``."""
        default = DEFAULT_FEATURE_POLICIES.get(method, RequestPolicy())
        data = self._get_conf(("request_policies", feature_name(method)), None)
        return RequestPolicy.from_conf(data, default)

    def _select_providers(
        self, method: str, providers: list[LanguageServicesProvider]
    ) -> list[LanguageServicesProvider]:
        policy = self.policy_for(method)
        if not policy.enabled:
            return []
        if policy.providers:
            by_name = {p.NAME: p for p in providers}
            providers = [by_name[n] for n in policy.providers if n in by_name]
        if policy.mode is RequestMode.EXCLUSIVE:
            return providers[:1]
        return providers

    # ---- Requests --------------------------------------------------------
    async def _call(
        self, provider: LanguageServicesProvider, method: str, params: Any
    ) -> Any:
        policy = self.policy_for(method)
        timeout = (
            policy.timeout_ms / 1000
            if policy.timeout_ms is not None
            else self.request_timeout()
        )
        handler = getattr(provider, FEATURE_METHODS[method])
        return await asyncio.wait_for(handler(params), timeout)

    async def _request(
        self,
        method: str,
        params: Any,
        providers: list[LanguageServicesProvider],
    ) -> Any:
        providers = self._select_providers(method, providers)
        if not providers:
            return None
        results = await asyncio.gather(
            *(self._call(p, method, params) for p in providers),
            return_exceptions=True,
        )
        good: list[tuple[str, Any]] = []
        for provider, result in zip(providers, results):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, asyncio.TimeoutError):
                logger.warning(
                    "Provider %r timed out answering %s", provider.NAME, method
                )
            elif isinstance(result, BaseException):
                logger.error(
                    "Provider %r failed answering %s",
                    provider.NAME,
                    method,
                    exc_info=result,
                )
                self.sig_exception_occurred.emit(
                    exception_report(provider.NAME, method, result)
                )
            elif result is not None:
                good.append((provider.NAME, result))
        return merge_strategy(method)(good) if good else None

    async def request(self, method: str, params: Any) -> Any:
        """Answer the LSP ``method`` with the merged providers' results.

        Document requests resolve the language from
        ``params.text_document.uri`` (the document must be open).
        ``completionItem/resolve`` goes to the provider recorded in
        ``item.data["provider"]``. Workspace requests go to every provider.
        """
        if method == lsp.COMPLETION_ITEM_RESOLVE:
            data = params.data if isinstance(params.data, dict) else {}
            name = data.get("provider")
            if (
                not data.get("resolve") or
                name is None or
                name not in self._providers
            ):
                return None
            state = self._providers[name]
            if not state.started:
                return None
            return await self._request(method, params, [state.provider])
        if method in _NO_DOCUMENT_METHODS:
            providers = [s.provider for s in self._sorted_states() if s.started]
            return await self._request(method, params, providers)
        language = self.documents.language_of(params.text_document.uri)
        return await self._request(
            method, params, self.providers_for(language, method)
        )

    # Feature coroutines ---------------------------------------------------
    async def completion(self, params: lsp.CompletionParams):
        """Merged completion items, each stamped with ``data["provider"]``,
        ``data["uri"]`` and ``data["resolve"]``. ``uri`` lets a provider resolve
        against the right document; ``resolve`` is true only for items whose
        provider supports ``completionItem/resolve``"""
        uri = params.text_document.uri
        language = self.documents.language_of(uri)
        items = await self.request(lsp.TEXT_DOCUMENT_COMPLETION, params)
        resolving = {
            provider.NAME
            for provider in self.providers_for(
                language, lsp.COMPLETION_ITEM_RESOLVE
            )
        }
        for item in items or ():
            data = item.data if isinstance(item.data, dict) else {}
            name = data.get("provider")
            item.data = {**data, "uri": uri, "resolve": name in resolving}
        return items

    async def resolve_completion_item(self, item: lsp.CompletionItem):
        return await self.request(lsp.COMPLETION_ITEM_RESOLVE, item)

    async def hover(self, params: lsp.HoverParams):
        return await self.request(lsp.TEXT_DOCUMENT_HOVER, params)

    async def signature_help(self, params: lsp.SignatureHelpParams):
        return await self.request(lsp.TEXT_DOCUMENT_SIGNATURE_HELP, params)

    async def definition(self, params: lsp.DefinitionParams):
        return await self.request(lsp.TEXT_DOCUMENT_DEFINITION, params)

    async def references(self, params: lsp.ReferenceParams):
        return await self.request(lsp.TEXT_DOCUMENT_REFERENCES, params)

    async def document_symbol(self, params: lsp.DocumentSymbolParams):
        return await self.request(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL, params)

    async def folding_range(self, params: lsp.FoldingRangeParams):
        return await self.request(lsp.TEXT_DOCUMENT_FOLDING_RANGE, params)

    async def formatting(self, params: lsp.DocumentFormattingParams):
        return await self.request(lsp.TEXT_DOCUMENT_FORMATTING, params)

    async def range_formatting(self, params: lsp.DocumentRangeFormattingParams):
        return await self.request(lsp.TEXT_DOCUMENT_RANGE_FORMATTING, params)

    async def code_action(self, params: lsp.CodeActionParams):
        return await self.request(lsp.TEXT_DOCUMENT_CODE_ACTION, params)

    async def rename(self, params: lsp.RenameParams):
        return await self.request(lsp.TEXT_DOCUMENT_RENAME, params)

    async def workspace_symbol(self, params: lsp.WorkspaceSymbolParams):
        return await self.request(lsp.WORKSPACE_SYMBOL, params)

    async def execute_command(self, params: lsp.ExecuteCommandParams):
        return await self.request(lsp.WORKSPACE_EXECUTE_COMMAND, params)

    # ---- Document sync ---------------------------------------------------
    def _started_providers(self, language: Language):
        return self.providers_for(language)

    async def open_document(
        self,
        params: lsp.DidOpenTextDocumentParams,
        language: Language | None = None,
    ) -> None:
        """Track a document and send ``didOpen`` to its providers.

        Raises
        ------
        UnknownLanguageError
            If the document's ``language_id`` matches no ``Language``.
        """
        document = self.documents.open(params, language)
        for provider in self._started_providers(document.language):
            await provider.did_open(params)

    async def change_document(
        self, params: lsp.DidChangeTextDocumentParams
    ) -> None:
        document = self.documents.change(params)
        for provider in self._started_providers(document.language):
            await provider.did_change(params)

    async def save_document(self, params: lsp.DidSaveTextDocumentParams) -> None:
        document = self.documents.save(params)
        for provider in self._started_providers(document.language):
            await provider.did_save(params)

    async def close_document(
        self, params: lsp.DidCloseTextDocumentParams
    ) -> None:
        """Send ``didClose`` and drop the document and its diagnostics."""
        with self._lock:
            document = self.documents.close(params)
        for provider in self._started_providers(document.language):
            await provider.did_close(params)

    # ---- Workspace -------------------------------------------------------
    async def notify_workspace_folders(
        self, params: lsp.DidChangeWorkspaceFoldersParams
    ) -> None:
        for state in self._sorted_states():
            if state.started:
                await state.provider.did_change_workspace_folders(params)

    async def notify_watched_files(
        self, params: lsp.DidChangeWatchedFilesParams
    ) -> None:
        for state in self._sorted_states():
            if state.started:
                await state.provider.did_change_watched_files(params)

    async def notify_interpreter_changed(self, interpreter: str) -> None:
        for state in self._sorted_states():
            if state.started:
                await state.provider.on_interpreter_changed(interpreter)

    async def notify_pythonpath_changed(
        self, paths: list[str], prioritize: bool
    ) -> None:
        for state in self._sorted_states():
            if state.started:
                await state.provider.on_pythonpath_changed(paths, prioritize)

    async def stop_all(self) -> None:
        for name in list(self._providers):
            try:
                await self.stop_provider(name)
            except Exception:
                logger.exception("Provider %r failed to stop", name)

    # ---- Provider pushes -------------------------------------------------
    def _on_provider_diagnostics(
        self,
        provider: LanguageServicesProvider,
        params: lsp.PublishDiagnosticsParams,
    ) -> None:
        with self._lock:
            if params.uri not in self.documents.documents:
                return
            self.documents.set_diagnostics(
                params.uri, provider.NAME, params.diagnostics
            )
            merged = self._merged_diagnostics(params.uri, params.version)
        self.sig_diagnostics.emit(merged)

    def _merged_diagnostics(
        self, uri: str, version: int | None = None
    ) -> lsp.PublishDiagnosticsParams:
        sources = dict(self.documents.diagnostics_for(uri))
        ordered = [
            (name, sources[name])
            for name in self.provider_names()
            if name in sources
        ]
        diagnostics = merge_strategy(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)(
            ordered
        )
        return lsp.PublishDiagnosticsParams(
            uri=uri, diagnostics=diagnostics, version=version
        )

    def _clear_provider_diagnostics(
        self, name: str, languages: Iterable[Language] | None
    ) -> None:
        with self._lock:
            uris = self.documents.clear_provider_diagnostics(name, languages)
            merged = [self._merged_diagnostics(uri) for uri in uris]
        for params in merged:
            self.sig_diagnostics.emit(params)

    def _on_provider_capabilities(
        self,
        provider: LanguageServicesProvider,
        language: Language,
        capabilities: lsp.ServerCapabilities | None,
    ) -> None:
        state = self._state(provider.NAME)
        if not state.started:
            return
        self._announce_languages(state)
        self._refresh_capabilities(language)

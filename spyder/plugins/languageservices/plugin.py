# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language services plugin.

Hosts :class:`~spyder.plugins.languageservices.api.provider.LanguageServicesProvider`
instances and exposes a typed, asynchronous, ``lsprotocol``-based API to
other plugins. Every public request method returns a
:class:`~spyder.api.asyncdispatcher.DispatcherFuture`. The coroutine
versions are available on :attr:`LanguageServices.services_api` for asyncio
callers.
"""

from __future__ import annotations

# Standard library imports
import logging
import time
from importlib.metadata import entry_points
from typing import Any

# Third-party imports
from lsprotocol import types as lsp
from packaging.version import parse
from qtpy.QtCore import QCoreApplication, QEventLoop, Signal, Slot

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher, DispatcherFuture
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown,
)
from spyder.api.plugins import Plugins, SpyderPluginV2
from spyder.api.translations import _
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import (
    PROVIDERS_ENTRYPOINT,
    LanguageServicesProvider,
    ProviderConfigAccessor,
)
from spyder.plugins.languageservices.confpage import (
    LanguageServicesConfigPage,
)
from spyder.plugins.languageservices.container import (
    LanguageServicesContainer,
)
from spyder.plugins.languageservices.services import (
    LANGUAGE_SERVICES_LOOP,
    LanguageServicesAPI,
)

logger = logging.getLogger(__name__)

dispatch = AsyncDispatcher(loop=LANGUAGE_SERVICES_LOOP)
"""Runs a coroutine on the language services loop, returning a future."""

FALLBACK_PROVIDERS = frozenset({"fallback", "snippets"})
"""Providers that serve every language without a language server."""


def wait_for(future: DispatcherFuture, timeout: float = 10.0):
    """Block on ``future`` from the Qt main thread while processing events.

    Providers may need the main thread to answer (e.g. to run Qt code), so
    a plain ``future.result()`` from the main thread can deadlock.

    Raises
    ------
    TimeoutError
        If the future is not done after ``timeout`` seconds.
    """
    deadline = time.monotonic() + timeout
    while not future.done():
        if time.monotonic() > deadline:
            future.cancel()
            raise TimeoutError(
                f"Language services call did not finish in {timeout} s"
            )
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)
        time.sleep(0.005)
    return future.result()


class LanguageServices(SpyderPluginV2):
    """Typed language services (completion, hover, diagnostics, ...) merged
    from several providers."""

    NAME = "language_services"
    CONF_SECTION = "language_services"
    CONF_FILE = False
    REQUIRES = [Plugins.Preferences, Plugins.MainInterpreter]
    OPTIONAL = [
        Plugins.IPythonConsole,
        Plugins.PythonpathManager,
        Plugins.StatusBar,
    ]
    CONTAINER_CLASS = LanguageServicesContainer
    CONF_WIDGET_CLASS = LanguageServicesConfigPage

    # ---- Signals ---------------------------------------------------------
    sig_diagnostics = Signal(object)
    """Merged diagnostics of a document.

    Parameters
    ----------
    params: lsprotocol.types.PublishDiagnosticsParams
    """

    sig_apply_edit = Signal(object)
    """A provider asks to apply a workspace edit.

    Parameters
    ----------
    params: lsprotocol.types.ApplyWorkspaceEditParams
    """

    sig_capabilities_changed = Signal(object, object)
    """Merged capabilities of a language changed.

    Parameters
    ----------
    language: Language
    capabilities: lsprotocol.types.ServerCapabilities | None
    """

    sig_language_stopped = Signal(object)
    """No provider serves a language any more.

    Parameters
    ----------
    language: Language
    """

    sig_provider_status_changed = Signal(str, object, str)
    """Lifecycle status of a provider for a language changed.

    Parameters
    ----------
    provider: str
    language: Language
    status: ProviderStatus
    """

    sig_open_file_requested = Signal(str)
    """A provider asks the editor to open a file.

    Parameters
    ----------
    path: str
    """

    sig_current_language_changed = Signal(object)
    """The language of the document focused in the editor changed.

    Parameters
    ----------
    language: Language | None
    """

    def __init__(self, parent, configuration=None):
        super().__init__(parent, configuration)
        self.services_api = LanguageServicesAPI(self._api_conf, self)
        self.statusbar = None
        self.current_language: Language | None = None
        self._start_futures: dict[str, DispatcherFuture] = {}

        api = self.services_api
        api.sig_diagnostics.connect(self.sig_diagnostics)
        api.sig_apply_edit.connect(self.sig_apply_edit)
        api.sig_capabilities_changed.connect(self.sig_capabilities_changed)
        api.sig_language_stopped.connect(self.sig_language_stopped)
        api.sig_provider_status_changed.connect(
            self.sig_provider_status_changed
        )
        api.sig_open_file_requested.connect(self.sig_open_file_requested)
        api.sig_exception_occurred.connect(self.sig_exception_occurred)
        api.sig_show_message.connect(self._on_show_message)
        api.sig_log_message.connect(self._on_log_message)

        for entry_point in entry_points(group=PROVIDERS_ENTRYPOINT):
            logger.debug("Loading language services provider %s", entry_point)
            self.register_provider(entry_point.load())

    # ---- SpyderPluginV2 API ----------------------------------------------
    @staticmethod
    def get_name() -> str:
        return _("Language Services")

    @staticmethod
    def get_description() -> str:
        return _(
            "Provides language services (completion, hover, diagnostics, ...) to other plugins."
        )

    @classmethod
    def get_icon(cls):
        return cls.create_icon("completions")

    def on_initialize(self):
        for name in self.provider_names():
            if self.is_provider_enabled(name):
                self.start_provider(name)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        self.get_plugin(Plugins.Preferences).register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        self.get_plugin(Plugins.Preferences).deregister_plugin_preferences(
            self
        )

    @on_plugin_available(plugin=Plugins.MainInterpreter)
    def on_maininterpreter_available(self):
        # The IPython console reports interpreter changes when enabled.
        if not self.is_plugin_enabled(Plugins.IPythonConsole):
            self.get_plugin(
                Plugins.MainInterpreter
            ).sig_interpreter_changed.connect(self._on_interpreter_changed)

    @on_plugin_teardown(plugin=Plugins.MainInterpreter)
    def on_maininterpreter_teardown(self):
        if not self.is_plugin_enabled(Plugins.IPythonConsole):
            self.get_plugin(
                Plugins.MainInterpreter
            ).sig_interpreter_changed.disconnect(self._on_interpreter_changed)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        self.get_plugin(
            Plugins.IPythonConsole
        ).sig_interpreter_changed.connect(self._on_interpreter_changed)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self):
        self.get_plugin(
            Plugins.IPythonConsole
        ).sig_interpreter_changed.disconnect(self._on_interpreter_changed)

    @on_plugin_available(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_available(self):
        self.get_plugin(
            Plugins.PythonpathManager
        ).sig_pythonpath_changed.connect(self._on_pythonpath_changed)

    @on_plugin_teardown(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_teardown(self):
        self.get_plugin(
            Plugins.PythonpathManager
        ).sig_pythonpath_changed.disconnect(self._on_pythonpath_changed)

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        self.statusbar = self.get_plugin(Plugins.StatusBar)
        for name in self.provider_names():
            if self.is_provider_enabled(name):
                self._register_statusbar_widgets(name)

    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        for widget in self.get_container().all_statusbar_widgets():
            self.statusbar.remove_status_widget(widget.ID)
        self.statusbar = None

    def on_close(self, cancelable=False) -> bool:
        for future in self._start_futures.values():
            future.cancel()
        wait_for(dispatch(self.services_api.stop_all)())
        return True

    def after_configuration_update(self, options):
        for option in options:
            if not isinstance(option, tuple) or len(option) < 2:
                continue
            if option[0] != "providers":
                continue
            name = option[1]
            if name not in self.services_api.provider_names():
                continue
            if len(option) == 2 or option[2] == "enable":
                if self.is_provider_enabled(name):
                    self.start_provider(name)
                else:
                    self.stop_provider(name)

    # ---- Providers -------------------------------------------------------
    def register_provider(
        self,
        provider: type[LanguageServicesProvider] | LanguageServicesProvider,
    ) -> LanguageServicesProvider:
        """Register a provider class or instance.

        The provider's defaults are merged into the configuration under
        ``("providers", NAME)``. The provider is started right away when
        the plugin is already initialized and the provider is enabled.
        """
        Provider = provider if isinstance(provider, type) else type(provider)
        self._merge_provider_configuration(Provider)
        if isinstance(provider, type):
            provider = provider(self, ProviderConfigAccessor(provider.NAME))
        instance = self.services_api.register_provider(provider)
        if self._is_initialized() and self.is_provider_enabled(instance.NAME):
            self.start_provider(instance.NAME)
        return instance

    def unregister_provider(self, name: str) -> LanguageServicesProvider:
        """Stop (if needed) and remove a provider."""
        if self.services_api.is_started(name):
            wait_for(dispatch(self.services_api.stop_provider)(name))
        self._unregister_statusbar_widgets(name)
        return self.services_api.unregister_provider(name)

    def get_provider(self, name: str) -> LanguageServicesProvider:
        return self.services_api.get_provider(name)

    def provider_names(self) -> list[str]:
        """Registered provider names in priority order."""
        return self.services_api.provider_names()

    def is_provider_enabled(self, name: str) -> bool:
        return bool(self.get_conf(("providers", name, "enable"), True))

    def is_provider_started(self, name: str) -> bool:
        return self.services_api.is_started(name)

    def start_provider(self, name: str) -> DispatcherFuture:
        """Start a provider on the services loop."""
        if name in self._start_futures and not self._start_futures[name].done():
            return self._start_futures[name]
        future = dispatch(self.services_api.start_provider)(name)
        self._start_futures[name] = future
        future.connect(self._on_provider_started)
        return future

    @AsyncDispatcher.QtSlot
    def _on_provider_started(self, future: DispatcherFuture):
        if future.cancelled():
            return
        exc = future.exception()
        if exc is not None:
            # Already reported through sig_exception_occurred by the API.
            logger.debug("Provider start failed: %r", exc)
            return
        for name, pending in list(self._start_futures.items()):
            if pending is future:
                self._register_statusbar_widgets(name)

    def stop_provider(self, name: str) -> DispatcherFuture:
        """Stop a provider on the services loop."""
        self._unregister_statusbar_widgets(name)
        return dispatch(self.services_api.stop_provider)(name)

    def _is_initialized(self) -> bool:
        return bool(self.is_registered)

    # ---- Queries ---------------------------------------------------------
    def supported_languages(self) -> frozenset[Language]:
        return self.services_api.supported_languages()

    def is_language_supported(self, language: Language) -> bool:
        return self.services_api.is_language_supported(language)

    def providers_for(
        self, language: Language, method: str | None = None
    ) -> list[str]:
        """Names of the started providers serving ``language``."""
        return [p.NAME for p in self.services_api.providers_for(language, method)]

    def capabilities(self, language: Language) -> lsp.ServerCapabilities | None:
        return self.services_api.capabilities(language)

    def set_current_language(self, language: Language | None) -> None:
        """Record the language of the document focused in the editor (shown
        by status bar widgets)."""
        if language != self.current_language:
            self.current_language = language
            self.sig_current_language_changed.emit(language)

    # ---- Requests (each returns a DispatcherFuture) ----------------------
    @dispatch
    async def completion(self, params: lsp.CompletionParams):
        return await self.services_api.completion(params)

    @dispatch
    async def resolve_completion_item(self, item: lsp.CompletionItem):
        return await self.services_api.resolve_completion_item(item)

    @dispatch
    async def hover(self, params: lsp.HoverParams):
        return await self.services_api.hover(params)

    @dispatch
    async def signature_help(self, params: lsp.SignatureHelpParams):
        return await self.services_api.signature_help(params)

    @dispatch
    async def definition(self, params: lsp.DefinitionParams):
        return await self.services_api.definition(params)

    @dispatch
    async def references(self, params: lsp.ReferenceParams):
        return await self.services_api.references(params)

    @dispatch
    async def document_symbol(self, params: lsp.DocumentSymbolParams):
        return await self.services_api.document_symbol(params)

    @dispatch
    async def folding_range(self, params: lsp.FoldingRangeParams):
        return await self.services_api.folding_range(params)

    @dispatch
    async def formatting(self, params: lsp.DocumentFormattingParams):
        return await self.services_api.formatting(params)

    @dispatch
    async def range_formatting(self, params: lsp.DocumentRangeFormattingParams):
        return await self.services_api.range_formatting(params)

    @dispatch
    async def code_action(self, params: lsp.CodeActionParams):
        return await self.services_api.code_action(params)

    @dispatch
    async def rename(self, params: lsp.RenameParams):
        return await self.services_api.rename(params)

    @dispatch
    async def workspace_symbol(self, params: lsp.WorkspaceSymbolParams):
        return await self.services_api.workspace_symbol(params)

    @dispatch
    async def execute_command(self, params: lsp.ExecuteCommandParams):
        return await self.services_api.execute_command(params)

    # ---- Document sync ---------------------------------------------------
    @dispatch
    async def open_document(
        self,
        params: lsp.DidOpenTextDocumentParams,
        language: Language | None = None,
    ):
        return await self.services_api.open_document(params, language)

    @dispatch
    async def change_document(self, params: lsp.DidChangeTextDocumentParams):
        return await self.services_api.change_document(params)

    @dispatch
    async def save_document(self, params: lsp.DidSaveTextDocumentParams):
        return await self.services_api.save_document(params)

    @dispatch
    async def close_document(self, params: lsp.DidCloseTextDocumentParams):
        return await self.services_api.close_document(params)

    # ---- Languages and workspace -----------------------------------------
    @dispatch
    async def start_language(self, language: Language):
        return await self.services_api.start_language(language)

    @dispatch
    async def stop_language(self, language: Language):
        return await self.services_api.stop_language(language)

    @dispatch
    async def notify_workspace_folders(
        self, params: lsp.DidChangeWorkspaceFoldersParams
    ):
        return await self.services_api.notify_workspace_folders(params)

    @dispatch
    async def notify_watched_files(
        self, params: lsp.DidChangeWatchedFilesParams
    ):
        return await self.services_api.notify_watched_files(params)

    # ---- Private ---------------------------------------------------------
    def _api_conf(self, option, default):
        return self.get_conf(option, default)

    @Slot(str)
    def _on_interpreter_changed(self, interpreter: str):
        dispatch(self.services_api.notify_interpreter_changed)(interpreter)

    @Slot(object, bool)
    def _on_pythonpath_changed(self, paths, prioritize):
        dispatch(self.services_api.notify_pythonpath_changed)(list(paths), prioritize)

    @Slot(object)
    def _on_show_message(self, params: lsp.ShowMessageParams):
        self.get_container().show_message(params)

    @Slot(object)
    def _on_log_message(self, params: lsp.LogMessageParams):
        level = {
            lsp.MessageType.Error: logging.ERROR,
            lsp.MessageType.Warning: logging.WARNING,
            lsp.MessageType.Info: logging.INFO,
        }.get(params.type, logging.DEBUG)
        logger.log(level, "%s", params.message)

    def _register_statusbar_widgets(self, name: str):
        if self.statusbar is None:
            return
        container = self.get_container()
        if container.get_provider_statusbar_keys(name):
            return
        provider = self.get_provider(name)
        for id_ in container.register_statusbar_widgets(
            provider.STATUS_BAR_CLASSES, provider
        ):
            if id_ not in self.statusbar.get_status_widgets():
                self.statusbar.add_status_widget(container.statusbar_widgets[id_])

    def _unregister_statusbar_widgets(self, name: str):
        container = self.get_container()
        for id_ in list(container.get_provider_statusbar_keys(name)):
            container.remove_statusbar_widget(id_)
            if self.statusbar is not None:
                self.statusbar.remove_status_widget(id_)
        container.provider_statusbars.pop(name, None)

    # ---- Configuration merge ---------------------------------------------
    @staticmethod
    def _merge_default_configurations(
        Provider: type[LanguageServicesProvider],
        provider_configurations: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Merge ``Provider.CONF_DEFAULTS`` into the stored configuration.

        New options are added with their defaults. A minor version bump
        overwrites values whose default changed. A major version bump also
        drops options no longer declared. The stored entry has the keys
        ``version``, ``values``, ``defaults`` and ``enable``.
        """
        defaults = dict(Provider.CONF_DEFAULTS)
        entry = provider_configurations.get(Provider.NAME)
        if entry is None:
            entry = {
                "version": Provider.CONF_VERSION,
                "values": dict(defaults),
                "defaults": dict(defaults),
                "enable": True,
            }
            provider_configurations[Provider.NAME] = entry
            return entry

        entry.setdefault("enable", True)
        values = entry.setdefault("values", {})
        current_defaults = entry.setdefault("defaults", {})
        for key in defaults.keys() - values.keys():
            values[key] = defaults[key]
            current_defaults[key] = defaults[key]

        new_version = parse(Provider.CONF_VERSION)
        current_version = parse(entry.get("version", "0.0.0"))
        if new_version > current_version:
            for key in current_defaults.keys() & defaults.keys():
                if current_defaults[key] != defaults[key]:
                    current_defaults[key] = defaults[key]
                    values[key] = defaults[key]
            if new_version.major != current_version.major:
                for key in current_defaults.keys() - defaults.keys():
                    current_defaults.pop(key)
                    values.pop(key, None)
        entry["version"] = str(new_version)
        return entry

    def _merge_provider_configuration(
        self, Provider: type[LanguageServicesProvider]
    ) -> None:
        configurations = self.get_conf("providers", {})
        self._merge_default_configurations(Provider, configurations)
        self.set_conf("providers", configurations)

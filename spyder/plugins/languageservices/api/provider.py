# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Base class for language services providers.

A provider answers typed :mod:`lsprotocol` requests for a set of
:class:`~spyder.plugins.languageservices.api.languages.Language`s. The
plugin fans every request out to all providers of the document's language
and merges their answers (see :mod:`.policies`).
"""

from __future__ import annotations

# Standard library imports
import enum
import inspect
from collections.abc import Callable
from typing import Any, TYPE_CHECKING

# Third party imports
from lsprotocol import types as lsp
from qtpy.QtCore import QObject, Signal

# Local imports
from spyder.api.config.mixins import (
    SpyderConfigurationAccessor,
    SpyderConfigurationObserver,
)
from spyder.config.manager import CONF
from spyder.config.user import NoDefault

if TYPE_CHECKING:
    from spyder.api.preferences import SpyderPreferencesTab
    from spyder.api.widgets.status import StatusBarWidget
    from spyder.plugins.languageservices.api.languages import Language


CONF_SECTION = "language_services"
"""Configuration section holding the plugin and provider options."""

PROVIDERS_ENTRYPOINT = "spyder.language_services"
"""Entry point group providers are discovered from."""

FEATURE_METHODS: dict[str, str] = {
    lsp.TEXT_DOCUMENT_COMPLETION: "completion",
    lsp.COMPLETION_ITEM_RESOLVE: "resolve_completion_item",
    lsp.TEXT_DOCUMENT_HOVER: "hover",
    lsp.TEXT_DOCUMENT_SIGNATURE_HELP: "signature_help",
    lsp.TEXT_DOCUMENT_DEFINITION: "definition",
    lsp.TEXT_DOCUMENT_REFERENCES: "references",
    lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL: "document_symbol",
    lsp.TEXT_DOCUMENT_FOLDING_RANGE: "folding_range",
    lsp.TEXT_DOCUMENT_FORMATTING: "formatting",
    lsp.TEXT_DOCUMENT_RANGE_FORMATTING: "range_formatting",
    lsp.TEXT_DOCUMENT_CODE_ACTION: "code_action",
    lsp.TEXT_DOCUMENT_RENAME: "rename",
    lsp.WORKSPACE_SYMBOL: "workspace_symbol",
    lsp.WORKSPACE_EXECUTE_COMMAND: "execute_command",
}
"""LSP request method name -> provider method (and feature) name."""

FEATURE_NAMES: dict[str, str] = {
    name: method for method, name in FEATURE_METHODS.items()
}
"""Feature name -> LSP request method name."""

CAPABILITY_ATTRIBUTES: dict[str, str] = {
    lsp.TEXT_DOCUMENT_COMPLETION: "completion_provider",
    lsp.COMPLETION_ITEM_RESOLVE: "completion_provider",
    lsp.TEXT_DOCUMENT_HOVER: "hover_provider",
    lsp.TEXT_DOCUMENT_SIGNATURE_HELP: "signature_help_provider",
    lsp.TEXT_DOCUMENT_DEFINITION: "definition_provider",
    lsp.TEXT_DOCUMENT_REFERENCES: "references_provider",
    lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL: "document_symbol_provider",
    lsp.TEXT_DOCUMENT_FOLDING_RANGE: "folding_range_provider",
    lsp.TEXT_DOCUMENT_FORMATTING: "document_formatting_provider",
    lsp.TEXT_DOCUMENT_RANGE_FORMATTING: "document_range_formatting_provider",
    lsp.TEXT_DOCUMENT_CODE_ACTION: "code_action_provider",
    lsp.TEXT_DOCUMENT_RENAME: "rename_provider",
    lsp.WORKSPACE_SYMBOL: "workspace_symbol_provider",
    lsp.WORKSPACE_EXECUTE_COMMAND: "execute_command_provider",
}
"""LSP request method name -> ``lsp.ServerCapabilities`` attribute."""


def supports_method(
    capabilities: lsp.ServerCapabilities | None, method: str
) -> bool:
    """Tell whether ``capabilities`` enable the LSP request ``method``.

    ``None`` capabilities mean "unknown" and count as supporting everything,
    so providers that do not report capabilities receive every request.
    """
    if capabilities is None:
        return True
    attribute = CAPABILITY_ATTRIBUTES.get(method)
    if attribute is None:
        return True
    value = getattr(capabilities, attribute, None)
    if method == lsp.COMPLETION_ITEM_RESOLVE:
        return bool(value and getattr(value, "resolve_provider", False))
    return bool(value)


class ProviderStatus(str, enum.Enum):
    """Lifecycle state of a provider for one language."""

    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DOWN = "down"


class ProviderConfigAccessor(SpyderConfigurationAccessor):
    """Configuration accessor rooted at a provider's own option namespace.

    Options are stored under ``("providers", <NAME>, "values", ...)`` of the
    ``language_services`` section. The methods mirror
    :class:`~spyder.api.plugins.SpyderPluginV2`, so preference tabs accept an
    accessor as their ``plugin`` argument.
    """

    CONF_SECTION = CONF_SECTION

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def wrap_option(self, option) -> tuple:
        """Prefix ``option`` with the provider's namespace."""
        if isinstance(option, tuple):
            return ("providers", self.provider_name, "values", *option)
        return ("providers", self.provider_name, "values", option)

    def _resolve(self, option, section):
        """Provider options (``section=None``) live in the provider
        namespace. ``section="language_services"`` names plugin options."""
        if section is None:
            return self.wrap_option(option), CONF_SECTION
        return option, section

    def get_conf(self, option, default=NoDefault, section=None, secure=False):
        option, section = self._resolve(option, section)
        return CONF.get(section, option, default, secure=secure)

    def set_conf(
        self,
        option,
        value,
        section=None,
        recursive_notification=True,
        secure=False,
    ):
        option, section = self._resolve(option, section)
        CONF.set(
            section,
            option,
            value,
            recursive_notification=recursive_notification,
            secure=secure,
        )

    def remove_conf(self, option, section=None, secure=False):
        option, section = self._resolve(option, section)
        CONF.remove_option(section, option, secure=secure)

    def get_conf_default(self, option, section=None):
        option, section = self._resolve(option, section)
        return CONF.get_default(section, option)

    def get_conf_options(self, section=None):
        if section is None:
            values = CONF.get(
                CONF_SECTION, ("providers", self.provider_name, "values"), {}
            )
            return list(values)
        return CONF.options(section)


class LanguageServicesProvider(SpyderConfigurationObserver, QObject):
    """Base class of every language services provider.

    Subclasses set :attr:`NAME`, implement :meth:`supported_languages` and
    override the feature coroutines they can answer. The default
    implementation of each feature returns ``None``, meaning "not provided".

    Every coroutine runs on the language services event loop thread, while
    the instance itself lives in the main (Qt) thread: providers must not
    touch widgets directly and instead emit signals, whose connections are
    queued by Qt to the receiver's thread.

    Configuration options declared in :attr:`CONF_DEFAULTS` are accessed
    with :attr:`config` (a :class:`ProviderConfigAccessor`) and observed
    with :func:`~spyder.api.config.decorators.on_conf_change`. Option names
    given to the decorator without a section are rewritten to the
    provider's namespace.
    """

    NAME: str = ""
    """Unique provider name. Required."""

    PRIORITY: int = 100
    """Merge order of the provider's responses. Lower values merge first."""

    CONF_DEFAULTS: list[tuple[Any, Any]] = []
    """``(option, default)`` pairs stored in the provider's namespace."""

    CONF_VERSION: str = "0.1.0"
    """Version of :attr:`CONF_DEFAULTS`, using semantic versioning. Bump the
    minor version when a default changes. Bump the major version when an
    option is removed or renamed."""

    CONF_TABS: list[type[SpyderPreferencesTab]] = []
    """Preference tabs shown in the plugin's configuration page."""

    STATUS_BAR_CLASSES: list[
        type[StatusBarWidget] | Callable[[QObject], StatusBarWidget]
    ] = []
    """Status bar widgets created while the provider is enabled."""

    CONF_SECTION = CONF_SECTION

    sig_diagnostics = Signal(object)
    """Diagnostics pushed by the provider.

    Parameters
    ----------
    params: lsprotocol.types.PublishDiagnosticsParams
        Complete set of diagnostics of this provider for ``params.uri``.
    """

    sig_apply_edit = Signal(object)
    """Workspace edit requested by the provider.

    Parameters
    ----------
    params: lsprotocol.types.ApplyWorkspaceEditParams
    """

    sig_show_message = Signal(object)
    """Message to show to the user.

    Parameters
    ----------
    params: lsprotocol.types.ShowMessageParams
    """

    sig_log_message = Signal(object)
    """Message to log.

    Parameters
    ----------
    params: lsprotocol.types.LogMessageParams
    """

    sig_capabilities_changed = Signal(object, object)
    """Capabilities of the provider for a language changed.

    Parameters
    ----------
    language: Language
    capabilities: lsprotocol.types.ServerCapabilities | None
        ``None`` when the provider stopped serving ``language``.
    """

    sig_status_changed = Signal(object, str)
    """Lifecycle status of the provider for a language changed.

    Parameters
    ----------
    language: Language
    status: ProviderStatus
    """

    sig_exception_occurred = Signal(dict)
    """Report an exception to the user (see the main window error dialog).

    Parameters
    ----------
    error_data: dict
        ``{"text", "is_traceback", "repo", "title", "label", "steps"}``.
    """

    sig_open_file_requested = Signal(str)
    """Ask the editor to open a file.

    Parameters
    ----------
    path: str
    """

    def __init__(
        self,
        plugin: QObject | None,
        config: ProviderConfigAccessor | None = None,
    ):
        """
        Parameters
        ----------
        plugin: spyder.plugins.languageservices.plugin.LanguageServices | None
            Plugin owning the provider (``None`` in tests).
        config: ProviderConfigAccessor | None
            Custom configuration accessor, defaults to ``ProviderConfigAccessor(self.NAME)``.
        """
        if not self.NAME:
            raise TypeError(f"{type(self).__name__} must define NAME")
        QObject.__init__(self, plugin)
        self.plugin = plugin
        self.config = (
            config if config is not None else ProviderConfigAccessor(self.NAME)
        )
        SpyderConfigurationObserver.__init__(self)

    # ---- Configuration observer namespace --------------------------------
    def _gather_observers(self):
        """Rewrite section-less observed options to the provider namespace."""
        for method_name in dir(self):
            static_attr = inspect.getattr_static(self, method_name, None)
            if not hasattr(static_attr, "_conf_listen"):
                continue
            method = getattr(self, method_name, None)
            if not hasattr(method, "_conf_listen"):
                continue
            info = method._conf_listen
            if len(info) > 1:
                self._multi_option_listeners |= {method_name}
            for section, option in info:
                if section is None:
                    section = CONF_SECTION
                    if option == "__section":
                        option = ("providers", self.NAME, "values")
                    else:
                        option = self.config.wrap_option(option)
                self._add_listener(method_name, option, section)

    # ---- Convenience -----------------------------------------------------
    def get_conf(self, option, default=NoDefault, section=None):
        """Shortcut for ``self.config.get_conf``."""
        return self.config.get_conf(option, default, section)

    def set_conf(self, option, value, section=None):
        """Shortcut for ``self.config.set_conf``."""
        self.config.set_conf(option, value, section)

    # ---- Lifecycle -------------------------------------------------------
    def supported_languages(self) -> frozenset[Language]:
        """Languages the provider currently serves. Required.

        The result may change while the provider runs (e.g. once a language
        server reports the languages it handles). Emit
        :attr:`sig_capabilities_changed` when it does.
        """
        raise NotImplementedError

    def capabilities(self, language: Language) -> lsp.ServerCapabilities | None:
        """Capabilities for ``language``. ``None`` means unknown."""
        return None

    async def start(self) -> None:
        """Start the provider. Awaited once after registration."""

    async def stop(self) -> None:
        """Stop the provider and release its resources."""

    async def start_language(self, language: Language) -> None:
        """Start serving ``language`` (no-op by default)."""

    async def stop_language(self, language: Language) -> None:
        """Stop serving ``language`` (no-op by default)."""

    # ---- Document synchronization ----------------------------------------
    async def did_open(self, params: lsp.DidOpenTextDocumentParams) -> None:
        """A document of a supported language was opened."""

    async def did_change(
        self, params: lsp.DidChangeTextDocumentParams
    ) -> None:
        """An open document changed."""

    async def did_save(self, params: lsp.DidSaveTextDocumentParams) -> None:
        """An open document was saved."""

    async def did_close(self, params: lsp.DidCloseTextDocumentParams) -> None:
        """An open document was closed."""

    # ---- Features --------------------------------------------------------
    async def completion(
        self, params: lsp.CompletionParams
    ) -> list[lsp.CompletionItem] | lsp.CompletionList | None:
        return None

    async def resolve_completion_item(
        self, item: lsp.CompletionItem
    ) -> lsp.CompletionItem | None:
        return None

    async def hover(self, params: lsp.HoverParams) -> lsp.Hover | None:
        return None

    async def signature_help(
        self, params: lsp.SignatureHelpParams
    ) -> lsp.SignatureHelp | None:
        return None

    async def definition(
        self, params: lsp.DefinitionParams
    ) -> lsp.Location | list[lsp.Location] | list[lsp.LocationLink] | None:
        return None

    async def references(
        self, params: lsp.ReferenceParams
    ) -> list[lsp.Location] | None:
        return None

    async def document_symbol(
        self, params: lsp.DocumentSymbolParams
    ) -> list[lsp.DocumentSymbol] | list[lsp.SymbolInformation] | None:
        return None

    async def folding_range(
        self, params: lsp.FoldingRangeParams
    ) -> list[lsp.FoldingRange] | None:
        return None

    async def formatting(
        self, params: lsp.DocumentFormattingParams
    ) -> list[lsp.TextEdit] | None:
        return None

    async def range_formatting(
        self, params: lsp.DocumentRangeFormattingParams
    ) -> list[lsp.TextEdit] | None:
        return None

    async def code_action(
        self, params: lsp.CodeActionParams
    ) -> list[lsp.Command | lsp.CodeAction] | None:
        return None

    async def rename(
        self, params: lsp.RenameParams
    ) -> lsp.WorkspaceEdit | None:
        return None

    async def workspace_symbol(
        self, params: lsp.WorkspaceSymbolParams
    ) -> list[lsp.SymbolInformation | lsp.WorkspaceSymbol] | None:
        return None

    async def execute_command(
        self, params: lsp.ExecuteCommandParams
    ) -> Any:
        return None

    # ---- Workspace notifications -----------------------------------------
    async def did_change_workspace_folders(
        self, params: lsp.DidChangeWorkspaceFoldersParams
    ) -> None:
        """Workspace folders were added or removed."""

    async def did_change_watched_files(
        self, params: lsp.DidChangeWatchedFilesParams
    ) -> None:
        """Watched files changed on disk."""

    async def did_change_configuration(
        self, params: lsp.DidChangeConfigurationParams
    ) -> None:
        """Provider configuration changed."""

    # ---- Environment hooks -----------------------------------------------
    async def on_interpreter_changed(self, interpreter: str) -> None:
        """The main Python interpreter changed."""

    async def on_pythonpath_changed(
        self, paths: list[str], prioritize: bool
    ) -> None:
        """The PYTHONPATH manager paths changed."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.NAME!r}>"

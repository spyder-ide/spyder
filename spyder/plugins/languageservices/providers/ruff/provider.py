# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Language services provider running the ruff server for Python."""

from __future__ import annotations

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.api.asyncdispatcher import AsyncDebounce
from spyder.api.config.decorators import on_conf_change
from spyder.plugins.languageservices.plugin import dispatch
from spyder.plugins.languageservices.providers.lsp.provider import (
    LanguageServerClientProvider,
)
from spyder.plugins.languageservices.providers.ruff.config import (
    generate_ruff_config,
)
from spyder.plugins.languageservices.providers.ruff.conftabs import (
    LintingConfigTab,
)


class RuffProvider(LanguageServerClientProvider):
    """Linting, code actions and formatting of Python documents with ruff.

    Formatting is always offered. It answers when the formatting request
    policies select ruff, that is when ruff is the chosen formatter. Hover is
    not forwarded: ruff only explains ``noqa`` codes with it and panics on a
    position past the end of the document, which the editor sends when the
    mouse is below the last line.
    """

    NAME = "ruff"
    PRIORITY = 3
    CONF_DEFAULTS = [
        ("lint", True),
        ("extend_select", ""),
        ("ignore", ""),
        ("pydocstyle", False),
        ("pydocstyle/convention", "numpy"),
        ("show_lsp_down_warning", True),
    ]
    CONF_VERSION = "0.1.0"
    CONF_TABS = [LintingConfigTab]
    STATUS_BAR_CLASSES = []

    def get_server_configs(self):
        return [generate_ruff_config(self.get_conf)]

    def capabilities(self, language):
        capabilities = super().capabilities(language)
        if capabilities is not None:
            capabilities.hover_provider = None
        return capabilities

    async def hover(self, params: lsp.HoverParams):
        return None

    @on_conf_change(option="__section")
    def _on_options_changed(self, options):
        self._reconfigure()

    @on_conf_change(section="editor", option="line_length")
    def _on_line_length_changed(self, value):
        self._reconfigure()

    def _reconfigure(self):
        if self._started:
            dispatch(self._debounced_apply)()

    @AsyncDebounce(time=0.3, replace=True)
    async def _debounced_apply(self):
        """Applying the preferences notifies one option at a time. Each
        would restart the server."""
        await self.apply_server_configs(self.get_server_configs())

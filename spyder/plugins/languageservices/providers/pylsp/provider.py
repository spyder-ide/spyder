# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Language services provider running python-lsp-server for Python."""

from __future__ import annotations

# Standard library imports
import logging

# Local imports
from spyder.api.asyncdispatcher import debounce
from spyder.api.config.decorators import on_conf_change
from spyder.config.base import running_under_pytest
from spyder.plugins.languageservices.api.provider import ProviderStatus
from spyder.plugins.languageservices.plugin import dispatch
from spyder.plugins.languageservices.providers.lsp.provider import (
    LanguageServerClientProvider,
)
from spyder.plugins.languageservices.providers.pylsp.config import (
    PRELOAD_MODULES,
    PYLSP_SERVER_NAME,
    generate_pylsp_config,
)
from spyder.plugins.languageservices.providers.pylsp.conftabs import TABS

logger = logging.getLogger(__name__)


class PylspProvider(LanguageServerClientProvider):
    """pylsp (with ``pyls_spyder``) preconfigured from Spyder's Python
    preferences.

    The single server is named ``"pylsp"``. The ``advanced/*`` options
    replace the generic servers table.
    """

    NAME = "pylsp"
    PRIORITY = 0
    CONF_DEFAULTS = [
        ("enable_hover_hints", True),
        ("show_lsp_down_warning", True),
        ("code_completion", True),
        ("jedi_definition", True),
        ("jedi_definition/follow_imports", True),
        ("jedi_signature_help", True),
        ("preload_modules", PRELOAD_MODULES),
        ("pyflakes", True),
        ("mccabe", False),
        ("flake8", False),
        ("ruff", False),
        ("no_linting", False),
        ("formatting", "black"),
        ("format_on_save", False),
        ("flake8/filename", ""),
        ("flake8/exclude", ""),
        ("flake8/extendSelect", ""),
        ("flake8/extendIgnore", "E,W,C90"),
        ("flake8/max_line_length", 79),
        ("ruff/exclude", ""),
        ("ruff/extendSelect", ""),
        ("ruff/extendIgnore", "E"),
        ("pydocstyle", False),
        ("pydocstyle/convention", "numpy"),
        ("pydocstyle/select", ""),
        ("pydocstyle/ignore", ""),
        ("pydocstyle/match", "(?!test_).*\\.py"),
        ("pydocstyle/match_dir", "[^\\.].*"),
        ("advanced/enabled", False),
        ("advanced/module", "pylsp"),
        ("advanced/host", "127.0.0.1"),
        ("advanced/port", 2087),
        ("advanced/external", False),
        ("advanced/stdio", False),
    ]
    CONF_VERSION = "1.1.0"
    CONF_TABS = TABS

    def get_server_configs(self):
        return [generate_pylsp_config(self.get_conf, self._interpreter)]

    def running_server_address(self) -> tuple[str, int] | None:
        """``(host, port)`` of the pylsp server Spyder started, if any."""
        state = self._servers.get(PYLSP_SERVER_NAME)
        if state is None or state.connection is None or state.config.external:
            return None
        if state.status is not ProviderStatus.READY:
            return None
        return (state.config.host, state.connection.port)

    # ---- Configuration updates -------------------------------------------
    def _reconfigure(self):
        if not self._started:
            return

        dispatch(self.apply_server_configs)(self.get_server_configs())

    @on_conf_change(option="__section")
    def _on_options_changed(self, options):
        self._reconfigure()

    @on_conf_change(section="outline_explorer", option=["group_cells", "show_comments"])
    def _on_outline_options_changed(self, option, value):
        self._reconfigure()

    @on_conf_change(section="language_services", option="enable_code_snippets")
    def _on_code_snippets_changed(self, value):
        self._reconfigure()

    @on_conf_change(
        section="pythonpath_manager", option=["spyder_pythonpath", "prioritize"]
    )
    def _on_pythonpath_options_changed(self, option, value):
        # The plugin forwards the change through on_pythonpath_changed. The
        # option observer only matters for self-contained tests.
        if running_under_pytest():
            self._reconfigure()

    async def on_pythonpath_changed(self, paths, prioritize):
        await self.apply_server_configs(self.get_server_configs())

    async def on_interpreter_changed(self, interpreter: str) -> None:
        if interpreter == self._interpreter:
            return
        logger.debug("pylsp interpreter changed to %s", interpreter)
        self._interpreter = interpreter
        await self._debounced_reconfigure()

    @debounce(time=0.6, replace=True)
    async def _debounced_reconfigure(self):
        """Switching consoles of different environments in quick succession
        would otherwise restart the server for each of them."""
        await self.apply_server_configs(self.get_server_configs())

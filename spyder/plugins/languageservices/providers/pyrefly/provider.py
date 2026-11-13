# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Language services provider running the pyrefly server for Python."""

from __future__ import annotations

# Standard library imports
import html
import logging
import re

# Third party imports
from lsprotocol import types as lsp

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.config.base import running_under_pytest
from spyder.plugins.languageservices.plugin import dispatch
from spyder.plugins.languageservices.providers.lsp.provider import (
    LanguageServerClientProvider,
)
from spyder.plugins.languageservices.providers.pyrefly.config import (
    generate_pyrefly_config,
)
from spyder.plugins.languageservices.providers.pyrefly.conftabs import (
    IntrospectionConfigTab,
)

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^[ \t]*```.*$", re.MULTILINE)
_RULE = re.compile(r"^[ \t]*-{3,}[ \t]*$", re.MULTILINE)
_HARD_BREAK = re.compile(r" {2,}\n")
_ESCAPED = re.compile(r"\\([\\`*_{}\[\]()#+.!-])")


def markdown_to_plain(text: str) -> str:
    """Plain text of the Markdown pyrefly writes in documentation.

    pyrefly ignores the plain text format the client asks for. Code fences
    and horizontal rules are dropped, hard line breaks and non-breaking
    spaces become ordinary ones and Markdown escapes are removed.
    """
    text = _FENCE.sub("", text)
    text = _RULE.sub("", text)
    text = _HARD_BREAK.sub("\n", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = _ESCAPED.sub(r"\1", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _plain(content):
    if isinstance(content, lsp.MarkupContent) and content.kind == lsp.MarkupKind.Markdown:
        return lsp.MarkupContent(
            kind=lsp.MarkupKind.PlainText, value=markdown_to_plain(content.value)
        )
    return content


def _plain_item(item: lsp.CompletionItem) -> lsp.CompletionItem:
    item.documentation = _plain(item.documentation)
    # The LSP fallback for a missing insert text, made explicit for the
    # editor widgets that read the field.
    if item.insert_text is None and item.text_edit is None:
        item.insert_text = item.label
    return item


class PyreflyProvider(LanguageServerClientProvider):
    """Completion, hover, navigation, symbols and type checking of Python
    documents with pyrefly, analyzing against the main interpreter."""

    NAME = "pyrefly"
    PRIORITY = 0
    CONF_DEFAULTS = [
        ("type_checking_mode", "auto"),
        ("show_lsp_down_warning", True),
    ]
    CONF_VERSION = "0.1.0"
    CONF_TABS = [IntrospectionConfigTab]

    def get_server_configs(self):
        return [generate_pyrefly_config(self.get_conf, self._interpreter)]

    # ---- Features --------------------------------------------------------
    # Documentation comes back as Markdown whatever the client asks for. The
    # editor and the Help pane expect plain text.
    async def hover(self, params):
        hover = await super().hover(params)
        if hover is not None:
            contents = hover.contents
            if isinstance(contents, list):
                hover.contents = [_plain(c) for c in contents]
            else:
                hover.contents = _plain(contents)
        return hover

    async def signature_help(self, params):
        help_ = await super().signature_help(params)
        if help_ is not None:
            for signature in help_.signatures:
                signature.documentation = _plain(signature.documentation)
        return help_

    async def completion(self, params):
        result = await super().completion(params)
        if isinstance(result, lsp.CompletionList):
            result.items = [_plain_item(item) for item in result.items]
        elif result is not None:
            result = [_plain_item(item) for item in result]
        return result

    async def resolve_completion_item(self, item):
        resolved = await super().resolve_completion_item(item)
        return None if resolved is None else _plain_item(resolved)

    def _reconfigure(self):
        if self._started:
            dispatch(self.apply_server_configs)(self.get_server_configs())

    @on_conf_change(option="__section")
    def _on_options_changed(self, options):
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
        logger.debug("pyrefly interpreter changed to %s", interpreter)
        self._interpreter = interpreter
        await self.apply_server_configs(self.get_server_configs())

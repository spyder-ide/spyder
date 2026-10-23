# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the legacy completions adapter registered with LanguageServices."""

import os.path as osp

from lsprotocol import types as lsp
import pytest

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.config.manager import CONF
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.editor.widgets.codeeditor.lsp_mixin import LSPMixin
from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.plugin import (
    LanguageServices,
    wait_for,
)
from spyder.plugins.languageservices.services import LANGUAGE_SERVICES_LOOP


def run(coro_func, *args, timeout=30):
    """Await a services-loop coroutine while the Qt loop keeps running."""
    future = AsyncDispatcher(loop=LANGUAGE_SERVICES_LOOP)(coro_func)(*args)
    return wait_for(future, timeout)


@pytest.fixture
def language_services(language_services_all_started):
    plugin, _, _ = language_services_all_started
    return plugin


def test_completion_reaches_pylsp(language_services, qtbot, tmp_path):
    filename = str(tmp_path / "adapter_test.py")
    uri = path_as_uri(filename)
    text = "import math\nmath.hyp"
    diagnostics = []
    language_services.sig_diagnostics.connect(
        lambda params: diagnostics.append(params)
    )

    run(
        language_services.services_api.open_document,
        lsp.DidOpenTextDocumentParams(
            text_document=lsp.TextDocumentItem(
                uri=uri, language_id="python", version=1, text=text
            )
        ),
    )
    # The legacy adapter serves no language. No third-party providers here
    assert language_services.providers_for(Language.PYTHON) == [
        "pylsp", "fallback", "snippets"
    ]

    items = run(
        language_services.services_api.completion,
        lsp.CompletionParams(
            text_document=lsp.TextDocumentIdentifier(uri),
            position=lsp.Position(1, len("math.hyp")),
        ),
    )
    labels = [item.label for item in items]
    assert any(label.startswith("hypot") for label in labels)
    providers = {item.data["provider"] for item in items}
    assert "pylsp" in providers
    assert all(item.data["uri"] == uri for item in items)

    hover = run(
        language_services.services_api.hover,
        lsp.HoverParams(
            text_document=lsp.TextDocumentIdentifier(uri),
            position=lsp.Position(0, len("import ma")),
        ),
    )
    assert isinstance(hover, lsp.Hover)
    assert "math" in LSPMixin.hover_text(hover)

    # Diagnostics pushed by pylsp are routed through the plugin
    run(
        language_services.services_api.change_document,
        lsp.DidChangeTextDocumentParams(
            text_document=lsp.VersionedTextDocumentIdentifier(
                uri=uri, version=2
            ),
            content_changes=[
                lsp.TextDocumentContentChangeWholeDocument(
                    text="import math\nundefined_name\n"
                )
            ],
        ),
    )
    qtbot.waitUntil(
        lambda: any(
            "undefined_name" in d.message
            for p in diagnostics for d in p.diagnostics
        ),
        timeout=30000,
    )
    assert diagnostics[-1].uri == uri

    run(
        language_services.services_api.close_document,
        lsp.DidCloseTextDocumentParams(lsp.TextDocumentIdentifier(uri)),
    )
    assert osp.basename(filename) == "adapter_test.py"

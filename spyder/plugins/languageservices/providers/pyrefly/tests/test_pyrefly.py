# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the pyrefly provider, against a real ``pyrefly lsp``."""

import asyncio
import sys

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.plugins.languageservices.api.provider import ProviderStatus
from spyder.plugins.languageservices.api.uri import path_as_uri
from spyder.plugins.languageservices.providers.pyrefly.config import (
    generate_pyrefly_config,
)
from spyder.plugins.languageservices.providers.pyrefly.provider import (
    PyreflyProvider,
    markdown_to_plain,
)
from spyder.plugins.languageservices.services import LanguageServicesAPI

pytestmark = pytest.mark.order(3)


def test_generate_pyrefly_config():
    values = {
        ("pythonpath_manager", "spyder_pythonpath"): ["/extra"],
        (None, "type_checking_mode"): "strict",
    }

    def get_conf(option, default=None, section=None):
        return values.get((section, option), default)

    config = generate_pyrefly_config(get_conf, "/env/bin/python")
    assert config.stdio and config.args == "lsp"
    assert config.languages == ("python",)
    assert config.configurations == {
        "python": {
            "pythonPath": "/env/bin/python",
            "pyrefly": {"extraSearchPaths": ["/extra"], "typeCheckingMode": "strict"},
        }
    }
    default = generate_pyrefly_config(lambda o, d=None, section=None: d, "/py")
    assert default.configurations["python"]["pyrefly"] == {
        "extraSearchPaths": [],
        "typeCheckingMode": "auto",
    }


def test_markdown_to_plain():
    markdown = (
        "```python\n(function) def walk(top) -> Iterator\n```\n\n---\n\n"
        "Directory tree generator.  \n  \nFor each directory  \n"
        "&nbsp;&nbsp;&nbsp;&nbsp;dirpath, dirnames  \n\\_private\n"
    )
    assert markdown_to_plain(markdown) == (
        "(function) def walk(top) -> Iterator\n\n"
        "Directory tree generator.\n\nFor each directory\n"
        "    dirpath, dirnames\n_private"
    )
    assert markdown_to_plain("plain") == "plain"


async def wait_until(predicate, timeout=60):
    for _ in range(int(timeout * 20)):
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise TimeoutError("Condition not met")


def test_pyrefly_serves_python(tmp_path):
    api = LanguageServicesAPI()
    provider = api.register_provider(PyreflyProvider)
    diagnostics = []
    api.sig_diagnostics.connect(diagnostics.append)
    uri = path_as_uri(str(tmp_path / "test.py"))

    def ident():
        return lsp.TextDocumentIdentifier(uri)

    async def scenario():
        await api.start_provider(provider.NAME)
        await api.start_language(Language.PYTHON)
        assert provider.server_status("pyrefly") is ProviderStatus.READY
        assert provider.get_server_configs()[0].configurations["python"][
            "pythonPath"
        ] == sys.executable
        capabilities = api.capabilities(Language.PYTHON)
        assert capabilities.completion_provider is not None
        assert capabilities.hover_provider
        assert capabilities.document_symbol_provider

        await api.open_document(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri=uri,
                    language_id="python",
                    version=1,
                    text="import os\nos.walk(top='.')\nx: int = 'a'\ny = o",
                )
            )
        )
        items = await api.completion(
            lsp.CompletionParams(text_document=ident(), position=lsp.Position(3, 5))
        )
        labels = [item.label for item in items]
        assert "os" in labels
        assert items[0].data["provider"] == provider.NAME
        assert all(item.insert_text or item.text_edit for item in items)

        hover = await api.hover(
            lsp.HoverParams(text_document=ident(), position=lsp.Position(0, 8))
        )
        assert hover is not None
        contents = hover.contents
        contents = contents if isinstance(contents, list) else [contents]
        for content in contents:
            if isinstance(content, lsp.MarkupContent):
                assert content.kind == lsp.MarkupKind.PlainText
                assert "```" not in content.value

        signature = await api.signature_help(
            lsp.SignatureHelpParams(text_document=ident(), position=lsp.Position(1, 8))
        )
        assert signature.signatures and "walk" in signature.signatures[0].label
        doc = signature.signatures[0].documentation
        assert isinstance(doc, lsp.MarkupContent)
        assert doc.kind == lsp.MarkupKind.PlainText
        assert "&nbsp;" not in doc.value

        location = await api.definition(
            lsp.DefinitionParams(text_document=ident(), position=lsp.Position(1, 4))
        )
        assert location and "os.py" in location[0].uri

        # Loose files get the automatic mode, which reports names but not
        # the assignment type error.
        await wait_until(
            lambda: any(
                d.code == "unknown-name"
                for params in diagnostics
                for d in params.diagnostics
            )
        )
        assert diagnostics[-1].diagnostics[0].source == "Pyrefly"

        # Interpreter changes travel through the configuration, without a
        # restart of the server.
        connection = provider._servers["pyrefly"].connection
        await provider.on_interpreter_changed("/other/python")
        assert provider._servers["pyrefly"].connection is connection
        assert connection.configurations["python"]["pythonPath"] == "/other/python"

        await api.stop_provider(provider.NAME)
        assert provider.server_status("pyrefly") is ProviderStatus.STOPPED

    asyncio.run(scenario())


if __name__ == "__main__":
    pytest.main()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the document registry."""

from lsprotocol import types as lsp
import pytest

from spyder.plugins.languageservices.api.documents import (
    DocumentRegistry,
    apply_content_change,
    utf16_len,
)
from spyder.plugins.languageservices.api.errors import (
    DocumentNotOpenError,
    UnknownLanguageError,
)
from spyder.plugins.languageservices.api.languages import Language


def did_open(uri="file:///a.py", language_id="python", text="x = 1\n"):
    return lsp.DidOpenTextDocumentParams(
        text_document=lsp.TextDocumentItem(
            uri=uri, language_id=language_id, version=1, text=text
        )
    )


def change(uri, version, *changes):
    return lsp.DidChangeTextDocumentParams(
        text_document=lsp.VersionedTextDocumentIdentifier(
            uri=uri, version=version
        ),
        content_changes=list(changes),
    )


def partial(start, end, text):
    return lsp.TextDocumentContentChangePartial(
        range=lsp.Range(lsp.Position(*start), lsp.Position(*end)), text=text
    )


def test_apply_content_change_incremental_utf16():
    text = "a😀b\ncd\n"
    assert utf16_len("😀") == 2
    # Replace "b" (after the two-unit emoji) with "X"
    assert apply_content_change(text, partial((0, 3), (0, 4), "X")) == (
        "a😀X\ncd\n"
    )
    # Join the two lines
    assert apply_content_change(text, partial((0, 4), (1, 0), "")) == "a😀bcd\n"
    # Insert at end of document
    assert apply_content_change(text, partial((2, 0), (2, 0), "e")) == (
        "a😀b\ncd\ne"
    )
    whole = lsp.TextDocumentContentChangeWholeDocument(text="new")
    assert apply_content_change(text, whole) == "new"
    with pytest.raises(ValueError):
        apply_content_change(text, partial((1, 0), (0, 0), ""))


def test_open_change_save_close():
    registry = DocumentRegistry()
    document = registry.open(did_open())
    assert document.language is Language.PYTHON
    assert registry.language_of("file:///a.py") is Language.PYTHON

    registry.change(change("file:///a.py", 2, partial((0, 4), (0, 5), "2")))
    assert registry.get("file:///a.py").version == 2

    registry.save(
        lsp.DidSaveTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier("file:///a.py"),
            text="saved",
        )
    )
    assert registry.get("file:///a.py").version == 2

    registry.set_diagnostics("file:///a.py", "p", [
        lsp.Diagnostic(range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0)),
                       message="m")
    ])
    registry.close(
        lsp.DidCloseTextDocumentParams(
            text_document=lsp.TextDocumentIdentifier("file:///a.py")
        )
    )
    assert registry.documents == {}
    assert registry.diagnostics == {}
    with pytest.raises(DocumentNotOpenError):
        registry.get("file:///a.py")


def test_open_language_override_and_errors():
    registry = DocumentRegistry()
    assert registry.open(did_open(language_id="python")).language is (
        Language.PYTHON
    )
    doc = registry.open(did_open("file:///b.ipy"), language=Language.IPYTHON)
    assert doc.language is Language.IPYTHON
    with pytest.raises(UnknownLanguageError):
        registry.open(did_open("file:///c", language_id="klingon"))
    with pytest.raises(ValueError):
        registry.open(did_open("file:///d"), language=Language.RUST)


def test_diagnostics_bookkeeping():
    registry = DocumentRegistry()
    registry.open(did_open("file:///a.py"))
    registry.open(did_open("file:///b.rs", language_id="rust"))
    diag = lsp.Diagnostic(
        range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0)), message="m"
    )
    registry.set_diagnostics("file:///a.py", "p1", [diag])
    registry.set_diagnostics("file:///a.py", "p2", [diag])
    registry.set_diagnostics("file:///b.rs", "p1", [diag])
    assert dict(registry.diagnostics_for("file:///a.py")) == {
        "p1": [diag], "p2": [diag]
    }
    assert registry.clear_provider_diagnostics("p1", {Language.RUST}) == [
        "file:///b.rs"
    ]
    assert registry.clear_provider_diagnostics("p1") == ["file:///a.py"]
    assert dict(registry.diagnostics_for("file:///a.py")) == {"p2": [diag]}
    registry.set_diagnostics("file:///a.py", "p2", [])
    assert registry.diagnostics == {}

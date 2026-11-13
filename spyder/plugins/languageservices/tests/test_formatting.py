# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the shared code of the formatting providers."""

from lsprotocol import types as lsp

from spyder.plugins.languageservices.api.formatting import (
    line_range_of,
    whole_document_edit,
)


def test_whole_document_edit():
    assert whole_document_edit("a\n", "a\n") == []
    edits = whole_document_edit("a\nb\n", "a\n\nb\n")
    assert len(edits) == 1
    assert edits[0].range == lsp.Range(lsp.Position(0, 0), lsp.Position(2, 0))
    assert edits[0].new_text == "a\n\nb\n"
    # Without a trailing newline the last line still counts
    assert whole_document_edit("a\nb", "a\n\nb")[0].range.end.line == 2


def test_line_range_of():
    assert line_range_of(lsp.Range(lsp.Position(1, 3), lsp.Position(3, 5))) == (2, 4)
    # Selection ending at the start of a line leaves that line out
    assert line_range_of(lsp.Range(lsp.Position(1, 0), lsp.Position(3, 0))) == (2, 3)
    assert line_range_of(lsp.Range(lsp.Position(1, 0), lsp.Position(1, 0))) == (2, 2)

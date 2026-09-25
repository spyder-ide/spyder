# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for CodeEditor.set_language resolving languages via the registry."""

import pytest

from spyder.plugins.languageservices.api.languages import Language
from spyder.utils import syntaxhighlighters as sh


@pytest.fixture
def restore_language_registry():
    """Undo any ``Language.register`` done during the test."""
    before = set(Language._member_map_)
    yield
    added = [name for name in list(Language._member_map_)
             if name not in before]
    for name in added:
        member = Language._member_map_.pop(name)
        Language._member_names_.remove(name)
        Language._value2member_map_.pop(member.value, None)
        type.__delattr__(Language, name)
    if added:
        try:
            type.__delattr__(Language, "_Language__index_cache")
        except AttributeError:
            pass


@pytest.mark.parametrize(
    "given, language, highlighter, comment_string",
    [
        ("py", "Python", sh.PythonSH, "#"),
        ("Python", "Python", sh.PythonSH, "#"),
        ("python", "Python", sh.PythonSH, "#"),
        ("c", "Cpp", sh.CppSH, "//"),
        ("Cpp", "Cpp", sh.CppSH, "//"),
        ("f90", "Fortran", sh.FortranSH, "!"),
        ("md", "Markdown", sh.MarkdownSH, "#"),
    ],
)
def test_set_language_resolves_highlighted_languages(
    codeeditor, given, language, highlighter, comment_string
):
    editor = codeeditor
    editor.set_language(given)
    assert editor.supported_language
    assert editor.language == language
    assert editor.highlighter_class is highlighter
    assert editor.comment_string == comment_string


def test_ipython_reports_python(codeeditor):
    editor = codeeditor
    editor.set_language("ipy")
    assert editor.supported_language
    assert editor.language == "Python"
    assert editor.highlighter_class is sh.IPythonSH


def test_python_enables_cells(codeeditor):
    editor = codeeditor
    editor.supported_cell_language = False
    editor.set_language("py")
    assert editor.supported_cell_language


def test_cython_is_highlighted_without_cells(codeeditor):
    editor = codeeditor
    editor.supported_cell_language = False
    editor.set_language("pyx")
    assert editor.supported_language
    assert editor.language == "Cython"
    assert not editor.supported_cell_language


def test_language_without_spyder_highlighter_keeps_registry_name(codeeditor):
    # JSON is in the registry but Spyder ships no highlighter for it.
    editor = codeeditor
    editor.set_language("json")
    assert not editor.supported_language
    assert editor.language == "JSON"
    assert editor.highlighter_class is sh.TextSH


@pytest.mark.parametrize(
    "filename, language",
    [
        ("page.tsx", "TypeScript"),
        ("main.ts", "TypeScript"),
        ("widget.jsx", "JavaScript"),
        ("index.js", "JavaScript"),
    ],
)
def test_registry_name_wins_over_pygments_lexer_name(
    codeeditor, filename, language
):
    # Pygments names the tsx/jsx lexers "TSX"/"JSX"; language services
    # look languages up by the registry name, so that one must win.
    editor = codeeditor
    ext = filename.rsplit(".", 1)[1]
    editor.set_language(ext, filename)
    assert not editor.supported_language
    assert editor.language == language
    assert editor.highlighter_class is not sh.TextSH


def test_unknown_language_is_text(codeeditor):
    editor = codeeditor
    editor.set_language("not-a-language")
    assert not editor.supported_language
    assert editor.language == "Text"


def test_dynamically_registered_language(
    codeeditor, restore_language_registry
):
    member = Language.register("ZZ Test Lang", ("zzq",), "zztest")
    assert Language.find(extension="zzq") is member

    editor = codeeditor
    editor.set_language("zzq")
    # A registered language carries no Spyder highlighter, so the editor
    # falls back to plain text rather than failing on the unknown member.
    assert not editor.supported_language
    assert editor.highlighter_class is sh.TextSH

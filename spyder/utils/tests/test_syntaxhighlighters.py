# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for syntaxhighlighters.py"""

import cProfile
import os
from pathlib import Path
import subprocess
import sys

import pytest
from qtpy.QtGui import QTextCharFormat, QTextDocument

from spyder.utils.syntaxhighlighters import (
    CythonSH, EnamlSH, HtmlSH, IPythonSH, PythonSH, MarkdownSH)


@pytest.mark.parametrize('letter, length', [('a', 100000), ('中', 200000)])
def test_link_scan_handles_long_nonlinks_in_bounded_time(letter, length, tmp_path):
    """Do not backtrack over every suffix of a long identifier/comment."""
    environment = dict(os.environ, SPYDER_CONFDIR=str(tmp_path))
    environment['PYTHONPATH'] = str(Path(__file__).resolve().parents[3])
    subprocess.run([sys.executable, '-c',
        'import sys; from qtpy.QtWidgets import QApplication; '
        'from qtpy.QtGui import QTextDocument; '
        'from spyder.utils.syntaxhighlighters import PythonSH; '
        'app = QApplication([]); document = QTextDocument(); '
        'highlighter = PythonSH(document); '
        'highlighter.highlight_patterns(sys.argv[1] * int(sys.argv[2]))',
        letter, str(length)], env=environment, timeout=30, check=True)


def test_python_tokens_do_not_allocate_group_dictionaries(qapp):
    document = QTextDocument('def example(value):\n    return value + 42\n')
    highlighter = PythonSH(document)
    profiler = cProfile.Profile()
    profiler.runcall(highlighter.rehighlightBlock, document.firstBlock())
    assert not any('groupdict' in str(entry.code) for entry in profiler.getstats())


@pytest.mark.parametrize('text, expected', [
    ('# owner/repo#42 next', [('issue', 'owner/repo#42')]),
    ('abcgh:owner/repo#42', [('issue', 'gh:owner/repo#42')]),
    ('some/path/owner/repo#2', [('issue', 'owner/repo#2')]),
    ('a-b/c_d#42', [('issue', 'a-b/c_d#42')]),
    ('/repo#42 owner/#3', [('issue', '/repo#42'), ('issue', 'owner/#3')]),
    ('xgh-12 gl-3 bb-4', [('issue', 'gh-12'), ('issue', 'gl-3'), ('issue', 'bb-4')]),
    ('amailto:bob@example.com', [('mail', 'mailto:bob@example.com')]),
    ('Abob@example.com', [('mail', 'bob@example.com')]),
    ('mailto: bob@example.com', [('mail', 'mailto: bob@example.com')]),
    ('jane.doe+tag@example.com', [('mail', 'tag@example.com')]),
    ('中foo@bar.com', [('mail', 'foo@bar.com')]),
    ('https://example.com/path', [('url', 'https://example.com/path')]),
    ('file:///D:/note.md', [('file', 'file:///D:/note.md')]),
    ('X2/中2#1YXbowner/no-number#0',
     [('issue', 'X2/中2#1'), ('issue', 'YXbowner/no-number#0')]),
    ('BUG-42', [('ticket', 'BUG-42')]),
])
def test_pattern_prescreen_keeps_native_link_underlines(qapp, text, expected):
    document = QTextDocument(text)
    highlighter = PythonSH(document)
    if text == 'BUG-42':
        highlighter.update_patterns({'ticket': r'BUG-\d+'})
    highlighter.rehighlightBlock(document.firstBlock())
    expected_positions = {position for _, value in expected
                          for position in range(text.index(value), text.index(value) + len(value))}
    actual_positions = {position for region in document.firstBlock().layout().formats()
                        if region.format.underlineStyle() == QTextCharFormat.SingleUnderline
                        for position in range(region.start, region.start + region.length)}
    assert actual_positions == expected_positions


@pytest.mark.parametrize('highlighter_class, text, token, length', [
    (PythonSH, 'match value:', 'keyword', 5),
    (PythonSH, 'case value:', 'keyword', 4),
    (IPythonSH, '%time value', 'symbol', 1),
    (CythonSH, 'cdef int value', 'keyword', 4),
    (EnamlSH, 'enamldef View(Window):', 'keyword', 8),
])
def test_python_family_token_formats(qapp, highlighter_class, text, token, length):
    document = QTextDocument(text)
    highlighter = highlighter_class(document)
    highlighter.rehighlightBlock(document.firstBlock())
    start = 1 if token == 'magic' else 0
    assert any(region.start == start and region.length == length
               and region.format.foreground() == highlighter.formats[token].foreground()
               for region in document.firstBlock().layout().formats())

def compare_formats(actualFormats, expectedFormats, sh):
    assert len(actualFormats) == len(expectedFormats)
    for actual, expected in zip(actualFormats, expectedFormats):
        assert actual.start == expected[0]
        assert actual.length == expected[1]
        # compare formats by looking at foreground colours only
        assert (actual.format.foreground().color().name()
                == sh.formats[expected[2]].foreground().color().name())

def test_HtmlSH_basic():
    txt = '<p style="color:red;">Foo <!--comment--> bar.</p>'
    doc = QTextDocument(txt)
    sh = HtmlSH(doc, color_scheme='Spyder')
    sh.rehighlightBlock(doc.firstBlock())

    # Expected result as list of tuples (begin, length, format)
    res = [(0, 2, 'builtin'),    # |<p|
           (2, 6, 'keyword'),    # | style|
           (8, 1, 'normal'),     # | |
           (9, 12, 'string'),    # |"color:red;"|
           (21, 1, 'builtin'),   # |>|
           (22, 4, 'normal'),    # |Foo |
           (26, 14, 'comment'),  # |<!--comment-->|
           (40, 5, 'normal'),    # | bar.|
           (45, 4, 'builtin')]   # |</p>|
    compare_formats(doc.firstBlock().layout().formats(), res, sh)

def test_HtmlSH_unclosed_commend():
    txt = '-->'
    doc = QTextDocument(txt)
    sh = HtmlSH(doc, color_scheme='Spyder')
    sh.rehighlightBlock(doc.firstBlock())
    res = [(0, 3, 'normal')]
    compare_formats(doc.firstBlock().layout().formats(), res, sh)


def test_PythonSH_UTF16_number():
    """UTF16 string"""
    txt = '𨭎𨭎𨭎𨭎 = 100000000'
    doc = QTextDocument(txt)
    sh = PythonSH(doc, color_scheme='Spyder')
    sh.rehighlightBlock(doc.firstBlock())
    res = [(0, 9, 'normal'),
           (9, 1, 'symbol'),
           (10, 1, 'normal'),
           (11, 9, 'number')]
    compare_formats(doc.firstBlock().layout().formats(), res, sh)


def test_PythonSH_UTF16_string():
    """UTF16 string"""
    txt = '𨭎𨭎𨭎𨭎 = "𨭎𨭎𨭎𨭎"'
    doc = QTextDocument(txt)
    sh = PythonSH(doc, color_scheme='Spyder')
    sh.rehighlightBlock(doc.firstBlock())
    res = [(0, 9, 'normal'),
           (9, 1, 'symbol'),
           (10, 1, 'normal'),
           (11, 10, 'string')]
    compare_formats(doc.firstBlock().layout().formats(), res, sh)


def test_python_string_prefix():
    prefixes = ("r", "u", "R", "U", "f", "F", "fr", "Fr", "fR", "FR",
                "rf", "rF", "Rf", "RF", "b", "B", "br", "Br", "bR", "BR",
                "rb", "rB", "Rb", "RB")
    for prefix in prefixes:
        txt = "[%s'test', %s'''test''']" % (prefix, prefix)

        doc = QTextDocument(txt)
        sh = PythonSH(doc, color_scheme='Spyder')
        sh.rehighlightBlock(doc.firstBlock())

        offset = len(prefix)
        res = [(0, 1, 'symbol'),                     # |[|
               (1, 6 + offset, 'string'),            # |{prefix}'test'|
               (7 + offset, 1, 'symbol'),
               (8 + offset, 1, 'normal'),            # |, |
               (9 + offset, 10 + offset, 'string'),  # |{prefix}'''test'''|
               (19 + 2*offset, 1, 'symbol')]         # | |

        compare_formats(doc.firstBlock().layout().formats(), res, sh)


def test_Markdown_basic():
    txt = "Some __random__ **text** with ~~different~~ [styles](link_url)"

    doc = QTextDocument(txt)
    sh = MarkdownSH(doc, color_scheme='Spyder')
    sh.rehighlightBlock(doc.firstBlock())

    res = [(0, 5, 'normal'),  # |Some|
           (5, 10, 'italic'),  # |__random__|
           (15, 1, 'normal'),  # | |
           (16, 8, 'strong'),  # |**text**|
           (24, 6, 'normal'),  # |with|
           (30, 13, 'italic'),  # |~~diferents~~|
           (43, 1, 'normal'),  # | |
           (44, 8, 'string'),  # |[styles]|
           (52, 1, 'normal'),  # |(|
           (53, 8, 'string'),  # |(link_url)|
           (61, 1, 'normal'),  # ||
           ]

    compare_formats(doc.firstBlock().layout().formats(), res, sh)


@pytest.mark.parametrize('line', ['# --- First variant',
                                  '#------ 2nd variant',
                                  '### 3rd variant'])
def test_python_outline_explorer_comment(line):
    assert PythonSH.OECOMMENT.match(line)

@pytest.mark.parametrize('line', ['#---', '#--------', '#---   ', '# -------'])
def test_python_not_an_outline_explorer_comment(line):
    assert not PythonSH.OECOMMENT.match(line)


if __name__ == '__main__':
    pytest.main()

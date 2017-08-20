# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for syntaxhighlighters.py"""

import pytest
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QTextDocument

from spyder.utils.syntaxhighlighters import HtmlSH, PythonSH, MarkdownSH
from spyder.py3compat import PY3

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
    compare_formats(doc.firstBlock().layout().additionalFormats(), res, sh)

def test_HtmlSH_unclosed_commend():
    txt = '-->'
    doc = QTextDocument(txt)
    sh = HtmlSH(doc, color_scheme='Spyder')
    sh.rehighlightBlock(doc.firstBlock())
    res = [(0, 3, 'normal')]
    compare_formats(doc.firstBlock().layout().additionalFormats(), res, sh)


def test_python_string_prefix():
    if PY3:
        prefixes = ("r", "u", "R", "U", "f", "F", "fr", "Fr", "fR", "FR", 
                    "rf", "rF", "Rf", "RF", "b", "B", "br", "Br", "bR", "BR",
                    "rb", "rB", "Rb", "RB")
    else:
        prefixes = ("r", "u", "ur", "R", "U", "UR", "Ur", "uR", "b", "B",
                    "br", "Br", "bR", "BR")
    for prefix in prefixes:
        txt = "[%s'test', %s'''test''']" % (prefix, prefix)

        doc = QTextDocument(txt)
        sh = PythonSH(doc, color_scheme='Spyder')
        sh.rehighlightBlock(doc.firstBlock())

        offset = len(prefix)
        res = [(0, 1, 'normal'),                     # |[|
               (1, 6 + offset, 'string'),            # |{prefix}'test'|
               (7 + offset, 2, 'normal'),            # |, |
               (9 + offset, 10 + offset, 'string'),  # |{prefix}'''test'''|
               (19 + 2*offset, 1, 'normal')]         # | |

        compare_formats(doc.firstBlock().layout().additionalFormats(), res, sh)


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

    compare_formats(doc.firstBlock().layout().additionalFormats(), res, sh)


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

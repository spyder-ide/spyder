# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor widget export helper functions for rich text
"""

from __future__ import annotations

# Standard library imports
import html
from inspect import cleandoc
from io import StringIO

# Third party imports
import rtfunicode  # noqa F401 this registers a new encoding for str.encode
from qtpy.QtGui import QTextCharFormat, QTextCursor


HTML_TEMPLATE = cleandoc("""
     <!DOCTYPE html>
     <html>
     <head></head>
     <body>
     <pre><code>{}</code></pre>
     </body>
     </html>
""")


class NewL: pass  # NewLine flag


def yield_spans(
    cursor: QTextCursor,
) -> tuple[QTextCharFormat | None, str | NewL]:
    """
    Generator to break up text into spans of equal formatting.

    Handle partial spans at beginning and end of the selection.
    Emit newline flags separately (between blocks) from text.
    """

    if not cursor.hasSelection():
        return
    selection_start = cursor.selectionStart()
    selection_end = cursor.selectionEnd()
    document = cursor.document()
    first_block = True  # for emitting NewL between blocks
    block = document.findBlock(selection_start)
    while block.isValid():
        rel_start = selection_start - block.position()
        rel_end = selection_end - block.position()
        block_text = block.text()
        if not first_block:
            yield None, NewL()
        first_block = False
        for f_range in block.layout().formats():
            range_end = f_range.start + f_range.length
            if rel_start > range_end:
                continue  # skip ranges until start of selection
            s_start = max(f_range.start, rel_start)
            s_end = min(range_end, rel_end)
            s_text = block_text[s_start:s_end]
            if s_text:
                yield f_range.format, s_text
            if s_end == rel_end: #last span
                return
        block = block.next()


def format_to_style(char_format: QTextCharFormat) -> str:
    """
	Convert the style properties of a :class:`QTextCharFormat` to CSS.

    Gather the foreground color, font-style, and font-weight from a
    QTextCharFormat, and generate the contents of a CSS ``style=`` tag
    for a ``<span>`` HTML element.
    """

    color = char_format.foreground().color().name()
    font = char_format.font()
    style = "italic" if font.italic() else "normal"
    weight = "bold" if font.bold() else "normal"
    return f"color:{color};font-style: {style};font-weight: {weight}"


def selection_to_html(cursor: QTextCursor) -> str:
    """
    Create an HTML document from a QTextCursor selection.
    
    Includes rich-text syntax highlighting.
    """

    sio = StringIO()
    for s_format, span in yield_spans(cursor):
        if isinstance(span, NewL):
            sio.write("\n")
        else:
            s_text = html.escape(span)
            style = format_to_style(s_format)
            sio.write(f"<span style=\"{style}\">{s_text}</span>")
    _html = HTML_TEMPLATE.format(sio.getvalue())
    return _html


"""
# notes on rtf format
# https://latex2rtf.sourceforge.net/rtfspec.html

#header:
    {\rtf1\ansi\ansicpg1252
    {
#   ^ start enclosing group of whole document
     \rtf1
#    ^ rft magic and major version
          \ansi
#         ^ charset

#font table:
    {\fonttbl\f0\fmodern\fcharset0 CourierNewPSMT;\f1\fmod...}
             \f0
#            ^ font 0
                \fmodern
#               ^ font family: Fixed-pitch serif and sans serif fonts
                        \fcharset0
#                       ^ optional maybe? charset 0 is ANSI
                                   CourierNewPSMT
#                                  ^ font name
                                                  \f1
#                                                 ^ font 1
                                                          ...}

#   separate fonts for bold and italic don't seem to be necessary?
#   use only one font? use \b and \i control words to apply style?

#   apple textedit is picky about semicolon terminating a list not only a
#   separator. MS word is less picky.
#color table:
    {\colortbl;\redN\greenN\blueN;\redN\greenN\blueN}
#   implied color 0 is "Auto"
               \redN\greenN\blueN
#              ^ color 1
                                  \redN\greenN\blueN
#                                 ^ color 2 .. etc
    \viewkind0\pard
    \viewkind0
#   ^ 0 - None, 1 - page layout, 2 - outline, 3 - master document view,
#     4 - normal, 5 - online layout view
              \pard
#             ^ reset paragraph style to default properties

#document:
    \f0\fs24\cf0 this is some text\
    \f0
#   ^  font 0 from \fonttbl
       \fs24
#      ^ font size 12 (24 half points)
            \cf0
#           ^ foreground color 0
                 this is some text
#                ^ body text
                                  \<CR>|<LF>|<CRLF>|<line>
#                                 ^ indicates newline (needs literal backslash)
    \b     this is bold indented text\
    \b
#   ^ turn bold on
           this is bold indented text\
#      ^ body text starts after single space which delimits control word \b
"""


def format_to_rtf(char_format: QTextCharFormat) -> tuple[str, str]:
    """
	Gather style from a :class:`QTextCharFormat` and convert it to RTF.

    Gathers the foreground color, font-style, and font-weight from a
    :class:`QTextCharFormat`, and generate the correct RTF control words.
    """

    color = char_format.foreground().color()
    r, g, b = color.red(), color.green(), color.blue()
    color_string = f"\\red{r}\\green{g}\\blue{b};"
    font = char_format.font()
    style = "\\i" if font.italic() else "\\i0"
    weight = "\\b" if font.bold() else "\\b0"
    return color_string, f"{style}{weight}"


def selection_to_rtf(cursor: QTextCursor) -> bytes:
    """
    Create an RTF document from a :class:`QTextCursor` selection.
    
    Includes rich text syntax highlighting.
    """

    color_table = []
    font_table = None
    font_size = None
    sio = StringIO()
    for s_format, span in yield_spans(cursor):
        if font_size is None and s_format is not None:
            font = s_format.font()
            font_size = font.pointSize()
            font_name = font.family()
            font_table = f"{{\\fonttbl\\f0\\fmodern\\fcharset0 {font_name};}}"
        if isinstance(span, NewL):
            sio.write("\\\n")
        else:
            s_text = span.encode("rtfunicode").decode("ansi")
            s_text.replace("\t", "\\tab ")
            color, style = format_to_rtf(s_format)
            if color not in color_table:
                color_table.append(color)
            color_index = color_table.index(color) + 1
            sio.write(f"{style}\\cf{color_index} {s_text}")
    color_table = f"{{\\colortbl;{''.join(color_table)}}}"
    header = f"{{\\rtf1{font_table}{color_table}\n\\f0\\fs{font_size*2} "
    sio.write("}") #footer
    return (header + sio.getvalue()).encode("ansi")

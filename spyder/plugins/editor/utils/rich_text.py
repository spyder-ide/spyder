# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor widget export helper functions for rich text
"""

# Standard library imports
import html
from inspect import cleandoc
from io import BytesIO, StringIO

# Third party imports
from qtpy.QtGui import QTextCharFormat, QTextCursor
import rtfunicode  # TODO for later


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


def yield_spans(cursor: QTextCursor) -> tuple[QTextCharFormat|None, str|NewL]:
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
        for f_range in block.layout().additionalFormats():
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
    Gather the foreground color, font-style, and font-weight from a
    QTextCharFormat, and generate the contents of a 'style' tag for a <span>
    html element.
    """
    color = char_format.foreground().color().name()
    font = char_format.font()
    style = "italic" if font.italic() else "normal"
    weight = "bold" if font.bold() else "normal"
    return f"color:{color};font-style: {style};font-weight: {weight}"


def selection_to_html(cursor: QTextCursor) -> str:
    """
    Create an html document from a QTextCursor selection
    to capture syntax highlighting.
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
    print(_html)
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


def format_to_rtf(char_format: QTextCharFormat) -> tuple[bytes, str]:
    """
    Gather the foreground color, font-style, and font-weight from a
    QTextCharFormat, and generate the correct RFT control words.
    """
    color = char_format.foreground().color()
    r, g, b = color.red(), color.green(), color.blue()
    color_string = f"\\red{r}\\green{g}\\blue{b};".encode("ascii")
    font = char_format.font()
    style = "\\i" if font.italic() else "\\i0"
    weight = "\\b" if font.bold() else "\\b0"
    return color_string, f"{style}{weight}"


def selection_to_rtf(cursor: QTextCursor) -> bytes:
    """
    Create an rtf document from a QTextCursor selection
    to capture syntax highlighting.
    """

    # TODO spaces between spans are sometimes swallowed? always?
    # TODO bold and italic working? some sources reference binary switch \b0 others don't \b
    color_table = []
    bio = BytesIO()
    for s_format, span in yield_spans(cursor):
        if isinstance(span, NewL):
            bio.write(b"\\\n")
        else:
            s_text = span.encode("rtfunicode").decode("ascii")
            color, style = format_to_rtf(s_format)  # TODO write out style characters
            if color not in color_table:
                color_table.append(color)
            color_index = color_table.index(color) + 1
            bio.write(f"{style}\\cf{color_index} {s_text}".encode("ascii"))
    header = b"{\\rtf1{\\colortbl " + b" ".join(color_table) + b"}"
    bio.write(b"}") #footer
    return header + bio.getvalue()



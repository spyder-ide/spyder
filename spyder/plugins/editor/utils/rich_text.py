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
# import rtfunicode  # TODO for later


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


def format_to_rtf_controls(char_format: QTextCharFormat) -> bytes:
    """
    Gather the foreground color, font-style, and font-weight from a
    QTextCharFormat, and generate the correct RFT control words.
    """
    return b""  # TODO write this


def selection_to_rtf(cursor: QTextCursor) -> bytes:
    """
    Create an rtf document from a QTextCursor selection
    to capture syntax highlighting.
    """

    header = rb"{\rtf1\ansi{\fonttbl\f0\fswiss Helvetica;}\f0\pard"
    footer = rb"}"
    bio = BytesIO()
    bio.write(header)
    for s_format, span in yield_spans(cursor):
        if isinstance(span, NewL):
            bio.write(b"\n")
        else:
            s_text = span.encode("rtfunicode")
            style = format_to_rtf_controls(s_format)  # TODO write out style characters
            bio.write(s_text)
    bio.write(footer)
    return bio.getvalue()



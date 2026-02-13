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
from qtpy.QtGui import QColor, QTextCharFormat, QTextCursor


HTML_TEMPLATE = cleandoc("""
     <!DOCTYPE html>
     <html>
     <head></head>
     <body>
     <pre{}><code>{}</code></pre>
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


def selection_to_html(cursor: QTextCursor, bg_color: str = "") -> str:
    """
    Create an HTML document from a QTextCursor selection.
    
    Includes rich-text syntax highlighting.
    """

    sio = StringIO()
    if bg_color:
        pre_style = f" style=\"background-color:{bg_color};\""
    else:
        pre_style = ""
    for s_format, span in yield_spans(cursor):
        if isinstance(span, NewL):
            sio.write("\n")
        else:
            s_text = html.escape(span)
            style = format_to_style(s_format)
            sio.write(f"<span style=\"{style}\">{s_text}</span>")
    _html = HTML_TEMPLATE.format(pre_style, sio.getvalue())
    return _html


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


def selection_to_rtf(cursor: QTextCursor, bg_color: str = "") -> bytes:
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
            s_text = span.encode("rtfunicode").decode("ascii")
            s_text.replace("\t", "\\tab ")
            color, style = format_to_rtf(s_format)
            if color not in color_table:
                color_table.append(color)
            color_index = color_table.index(color) + 1
            sio.write(f"{style}\\cf{color_index} {s_text}")
    # notes on rtf format
    # https://latex2rtf.sourceforge.net/rtfspec.html
    color = QColor(bg_color)
    r,g,b = color.red(), color.green(), color.blue()
    color_table.append(f"\\red{r}\\green{g}\\blue{b};")
    bg_color_index = len(color_table)
    color_table = f"{{\\colortbl;{''.join(color_table)}}}"
    header = (f"{{\\rtf1{font_table}{color_table}\n"
              f"\\f0\\fs{font_size*2}\\shading\\cbpat{bg_color_index} ")
    sio.write("}") #footer
    return (header + sio.getvalue()).encode("ascii")

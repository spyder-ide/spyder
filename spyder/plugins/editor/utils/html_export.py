# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor widget html export helper functions
"""

# Standard library imports
import html
from inspect import cleandoc

# Third party imports
from qtpy.QtGui import QTextCharFormat, QTextCursor


HTML_TEMPLATE = cleandoc("""
     <!DOCTYPE html>
     <html>
     <head></head>
     <body>
     <pre>{}</pre>
     </body>
     </html>
""")


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
    if not cursor.hasSelection():
        return

    spans = []
    selection_start = cursor.selectionStart()
    selection_end = cursor.selectionEnd()
    document = cursor.document()
    block = document.findBlock(selection_start)
    while block.isValid():
        rel_start = selection_start - block.position()
        rel_end = selection_end - block.position()
        block_text = block.text()
        for f_range in block.layout().additionalFormats():
            range_end = f_range.start + f_range.length
            if rel_start > range_end:
                continue  # skip ranges until start of selection
            s_start = max(f_range.start, rel_start)
            s_end = min(range_end, rel_end)
            s_text = html.escape(block_text[s_start:s_end])
            style = format_to_style(f_range.format)
            spans.append(f"<span style=\"{style}\">{s_text}</span>")
            if s_end == rel_end: #last span
                return HTML_TEMPLATE.format("\n".join(spans))
        block = block.next()

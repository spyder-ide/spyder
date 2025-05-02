# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Mix-in classes

These classes were created to be able to provide Spyder's regular text and
console widget features to an independent widget based on QTextEdit for the
IPython console plugin.
"""

# Standard library imports
from io import StringIO
import os
import os.path as osp
import re
import sys
import textwrap
from token import NUMBER
from tokenize import generate_tokens, TokenError

# Third party imports
from packaging.version import parse
from qtpy import QT_VERSION
from qtpy.QtCore import QPoint, QRegularExpression, Qt, QUrl
from qtpy.QtGui import (
    QDesktopServices, QFontMetrics, QTextCursor, QTextDocument)
from qtpy.QtWidgets import QApplication, QPlainTextEdit, QTextEdit
from spyder_kernels.utils.dochelpers import (getargspecfromtext, getobj,
                                             getsignaturefromtext)

# Local imports
from spyder.py3compat import to_text_string
from spyder.utils import encoding, sourcecode
from spyder.utils import syntaxhighlighters as sh
from spyder.utils.misc import get_error_match
from spyder.utils.palette import SpyderPalette
from spyder.widgets.arraybuilder import ArrayBuilderDialog


# ---- Constants
# -----------------------------------------------------------------------------

# List of possible EOL symbols
EOL_SYMBOLS = [
    # Put first as it correspond to a single line return
    "\r\n",  # Carriage Return + Line Feed
    "\r",  # Carriage Return
    "\n",  # Line Feed
    "\v",  # Line Tabulation
    "\x0b",  # Line Tabulation
    "\f",  # Form Feed
    "\x0c",   # Form Feed
    "\x1c",   # File Separator
    "\x1d",   # Group Separator
    "\x1e",   # Record Separator
    "\x85",   # Next Line (C1 Control Code)
    "\u2028",   # Line Separator
    "\u2029",   # Paragraph Separator
]

# Tips style
TIP_TEXT_COLOR = SpyderPalette.COLOR_TEXT_2
TIP_PARAMETER_HIGHLIGHT_COLOR = SpyderPalette.COLOR_TEXT_1

# Tips content
TIP_DEFAULT_LANGUAGE = 'python'
TIP_MAX_LINES = 10
TIP_MAX_WIDTH = 55
COMPLETION_HINT_MAX_WIDTH = 50
HINT_MAX_LINES = 7
HINT_MAX_WIDTH = 55
SIGNATURE_MAX_LINES = 4
BUILTINS_DOCSTRING_MAP = {
    int.__doc__: 'integer',
    list.__doc__: 'list',
    dict.__doc__: 'dictionary',
    set.__doc__: 'set',
    float.__doc__: 'float',
    tuple.__doc__: 'tuple',
    str.__doc__: 'string',
    bool.__doc__: 'bool',
    bytes.__doc__: 'bytes string',
    range.__doc__: 'range object',
    iter.__doc__: 'iterator',
}


# ---- Mixins
# -----------------------------------------------------------------------------
class BaseEditMixin(object):

    # The following signals are used to indicate text changes on the editor.
    sig_will_insert_text = None
    sig_will_remove_selection = None
    sig_text_was_inserted = None

    def __init__(self):
        self.eol_chars = None

    # ---- Line number area
    # -------------------------------------------------------------------------
    def get_linenumberarea_width(self):
        """Return line number area width"""
        # Implemented in CodeEditor, but needed for calltip/completion widgets
        return 0

    def calculate_real_position(self, point):
        """
        Add offset to a point, to take into account the Editor panels.

        This is reimplemented in CodeEditor, in other widgets it returns
        the same point.
        """
        return point

    # ---- Tooltips and Calltips
    # -------------------------------------------------------------------------
    def _calculate_position(self, at_line=None, at_point=None):
        """
        Calculate a global point position `QPoint(x, y)`, for a given
        line, local cursor position, or local point.
        """
        if at_point is not None:
            # Showing tooltip at point position
            cx = at_point.x()
            cy = at_point.y()
        elif at_line is not None:
            # Showing tooltip at line
            cx = 5
            line = at_line - 1
            cursor = QTextCursor(self.document().findBlockByNumber(line))
            cy = int(self.cursorRect(cursor).top())
        else:
            # Showing tooltip at cursor position
            cx, cy = self.get_coordinates('cursor')

            # Ubuntu Mono has a strange behavior regarding its height that we
            # need to account for. Other monospaced fonts behave as expected.
            if self.font().family() == 'Ubuntu Mono':
                padding = 5
            else:
                padding = 1 if sys.platform == "darwin" else 3

            # This is necessary because the point Qt returns for the cursor is
            # much below the line's bottom position.
            cy = int(cy - QFontMetrics(self.font()).capHeight() + padding)

        # Map to global coordinates
        point = self.mapToGlobal(QPoint(cx, cy))
        point = self.calculate_real_position(point)

        return point

    @property
    def _tip_text_size(self):
        """Text size for tooltips and calltips."""
        font = self.font()
        font_size = font.pointSize()
        return (font_size - 1) if font_size > 9 else font_size

    def _tip_width_in_pixels(self, max_width):
        """
        Get width for tooltips and calltips in pixels.

        Parameters
        ----------
        max_width: int
            Max width in numbers of characters that the widget can show.
        """
        # Get max width using the current font and text size
        font = self.font()
        font.setPointSize(self._tip_text_size)
        max_width_in_pixels = QFontMetrics(font).size(
            Qt.TextSingleLine,
            'M' * max_width
        )

        # We add a bit more pixels to the previous value to account for cases
        # in which the textwrap algorithm can't break text exactly at
        # `max_width`.
        return max_width_in_pixels.width() + 20

    def _format_text(self, title=None, signature=None, text=None,
                     inspect_word=None, max_lines=None,
                     max_width=TIP_MAX_WIDTH, display_link=False,
                     text_new_line=False,  with_html_format=False):
        """
        Create HTML template for calltips and tooltips.

        This will display title and text as separate sections and add `...`

        ----------------------------------------
        | `title` (with `title_color`)         |
        ----------------------------------------
        | `signature`                          |
        |                                      |
        | `text` (ellided to `max_lines`)      |
        |                                      |
        ----------------------------------------
        | Help message                         |
        ----------------------------------------
        """

        BASE_TEMPLATE = """
            <div style='font-family: "{font_family}";
                        font-size: {size}pt;
                        color: {color};'>
                {main_text}
            </div>
        """

        # Get current font properties
        font_family = self.font().family()
        text_size = self._tip_text_size
        text_color = TIP_TEXT_COLOR

        template = ''
        if title:
            template += BASE_TEMPLATE.format(
                font_family=font_family,
                size=text_size,
                color=SpyderPalette.TIP_TITLE_COLOR,
                main_text=title,
            )

            if text or signature:
                template += '<hr>'

        if signature:
            signature = signature.strip('\r\n')
            template += BASE_TEMPLATE.format(
                font_family=font_family,
                size=text_size,
                color=text_color,
                main_text=signature,
            )

        # Documentation/text handling
        if (text is None or not text.strip() or
                text.strip() == '<no docstring>'):
            text = '<i>No documentation available</i>'
        else:
            text = text.strip()

        if not with_html_format:
            # All these replacements are need to properly divide the
            # text in actual paragraphs and wrap the text on each one
            paragraphs = (text
                          .replace(u"\xa0", u" ")
                          .replace("\n\n", "<!DOUBLE_ENTER!>")
                          .replace(".\n", ".<!SINGLE_ENTER!>")
                          .replace("\n-", "<!SINGLE_ENTER!>-")
                          .replace("-\n", "-<!SINGLE_ENTER!>")
                          .replace("\n=", "<!SINGLE_ENTER!>=")
                          .replace("=\n", "=<!SINGLE_ENTER!>")
                          .replace("\n*", "<!SINGLE_ENTER!>*")
                          .replace("*\n", "*<!SINGLE_ENTER!>")
                          .replace("\n ", "<!SINGLE_ENTER!> ")
                          .replace(" \n", " <!SINGLE_ENTER!>")
                          .replace("\n", " ")
                          .replace("<!DOUBLE_ENTER!>", "\n\n")
                          .replace("<!SINGLE_ENTER!>", "\n").splitlines())
            new_paragraphs = []
            for paragraph in paragraphs:
                # Wrap text
                new_paragraph = textwrap.wrap(paragraph, width=max_width)

                # Remove empty lines at the beginning
                new_paragraph = [l for l in new_paragraph if l.strip()]

                # Merge paragraph text
                new_paragraph = '\n'.join(new_paragraph)

                # Add new paragraph
                new_paragraphs.append(new_paragraph)

            # Join paragraphs and split in lines for max_lines check
            paragraphs = '\n'.join(new_paragraphs)
            paragraphs = paragraphs.strip('\r\n')
            lines = paragraphs.splitlines()

            # Check that the first line is not empty
            if len(lines) > 0 and not lines[0].strip():
                lines = lines[1:]
        else:
            lines = [l for l in text.split('\n') if l.strip()]

        # Limit max number of text displayed
        if max_lines:
            if len(lines) > max_lines:
                text = '\n'.join(lines[:max_lines])

                # Add ellipsis in a new line if necessary
                if text[-1] == '\n':
                    text = text + '...'
                else:
                    text = text + '\n...'
            else:
                text = '\n'.join(lines)

        text = text.replace('\n', '<br>')
        if text_new_line and signature:
            # If there's enough content in the docstring or signature, then we
            # add an hr to separate them.
            if len(lines) > 2 or signature.count('<br>') > 2:
                separator = '<hr>'
            else:
                separator = '<br>'
            text = separator + text

        template += BASE_TEMPLATE.format(
            font_family=font_family,
            size=text_size,
            color=text_color,
            main_text=text,
        )

        help_text = ''
        if inspect_word and display_link:
            help_text = (
                f'<span style="font-family: \'{font_family}\';'
                f'font-size:{text_size}pt;">'
                f'Click on this tooltip for additional help'
                f'</span>'
            )

        if help_text and inspect_word:
            if display_link:
                template += (
                    f'<hr>'
                    f'<div align="left">'
                    f'<span style="color: {SpyderPalette.TIP_TITLE_COLOR};'
                    f'text-decoration:none;'
                    f'font-family:"{font_family}";font-size:{text_size}pt;>'
                ) + help_text + '</span></div>'
            else:
                template += (
                    '<hr>'
                    '<div align="left">'
                    '<span style="color:white;text-decoration:none;">'
                    '' + help_text + '</span></div>'
                )

        return template

    def _format_signature(self, signatures, parameter=None,
                          max_width=TIP_MAX_WIDTH):
        """
        Create HTML template for signature.

        This template will include indent after the method name, a highlight
        color for the active parameter and highlights for special chars.

        Special chars depend on the language.
        """
        language = getattr(self, 'language', TIP_DEFAULT_LANGUAGE).lower()
        active_parameter_template = (
            '<span style=\'font-family:"{font_family}";'
            'font-size:{font_size}pt;'
            'color:{color}\'>'
            '<b>{parameter}</b>'
            '</span>'
        )
        chars_template = (
            '<span style="color:{0};'.format(
                SpyderPalette.TIP_CHAR_HIGHLIGHT_COLOR
            ) +
            'font-weight:bold"><b>{char}</b>'
            '</span>'
        )

        def handle_sub(matchobj):
            """
            Handle substitution of active parameter template.

            This ensures the correct highlight of the active parameter.
            """
            match = matchobj.group(0)
            new = match.replace(parameter, active_parameter_template)
            return new

        if not isinstance(signatures, list):
            signatures = [signatures]

        new_signatures = []
        for signature in signatures:
            # Remove duplicate spaces
            signature = ' '.join(signature.split())

            # Replace initial spaces
            signature = signature.replace('( ', '(')

            # Process signature template
            if parameter and language == 'python':
                # Escape all possible regex characters
                # ( ) { } | [ ] . ^ $ * +
                escape_regex_chars = ['|', '.', '^', '$', '*', '+']
                remove_regex_chars = ['(', ')', '{', '}', '[', ']']
                regex_parameter = parameter
                for regex_char in escape_regex_chars + remove_regex_chars:
                    if regex_char in escape_regex_chars:
                        escape_char = r'\{char}'.format(char=regex_char)
                        regex_parameter = regex_parameter.replace(regex_char,
                                                                  escape_char)
                    else:
                        regex_parameter = regex_parameter.replace(regex_char,
                                                                  '')
                        parameter = parameter.replace(regex_char, '')

                pattern = (r'[\*|\(|\[|\s](' + regex_parameter +
                           r')[,|\)|\]|\s|=]')

            formatted_lines = []
            name = signature.split('(')[0]
            indent = ' ' * (len(name) + 1)
            rows = textwrap.wrap(signature, width=max_width,
                                 subsequent_indent=indent)
            for row in rows[:SIGNATURE_MAX_LINES]:
                if parameter and language == 'python':
                    # Add template to highlight the active parameter
                    row = re.sub(pattern, handle_sub, row)

                row = row.replace(' ', '&nbsp;')
                row = row.replace('span&nbsp;', 'span ')
                row = row.replace('{}', '{{}}')

                if language and language == 'python':
                    for char in ['(', ')', ',', '*', '**']:
                        new_char = chars_template.format(char=char)
                        row = row.replace(char, new_char)

                formatted_lines.append(row)
            title_template = '<br>'.join(formatted_lines)

            # Get current font properties
            font = self.font()
            font_family = font.family()

            # Format title to display active parameter
            if parameter and language == 'python':
                title = title_template.format(
                    font_size=self._tip_text_size,
                    font_family=font_family,
                    color=TIP_PARAMETER_HIGHLIGHT_COLOR,
                    parameter=parameter,
                )
            else:
                title = title_template
            new_signatures.append(title)

        return '<br>'.join(new_signatures)

    def _check_signature_and_format(self, signature_or_text, parameter=None,
                                    inspect_word=None,
                                    max_width=TIP_MAX_WIDTH):
        """
        LSP hints might provide docstrings instead of signatures.

        This method will check for signatures (dict, type etc...) and format
        the text accordingly.
        """
        has_signature = False
        language = getattr(self, 'language', TIP_DEFAULT_LANGUAGE).lower()
        signature_or_text = signature_or_text.replace('\\*', '*')

        # Remove special symbols that could interfere with ''.format
        signature_or_text = signature_or_text.replace('{', '&#123;')
        signature_or_text = signature_or_text.replace('}', '&#125;')

        # Remove 'ufunc' signature if needed. See spyder-ide/spyder#11821
        lines = [line for line in signature_or_text.split('\n')
                 if 'ufunc' not in line]
        signature_or_text = '\n'.join(lines)

        if language == 'python':
            open_func_char = '('
            if inspect_word:
                has_signature = signature_or_text.startswith(
                    inspect_word + open_func_char)
            else:
                # Trying to find signature on first line
                idx = lines[0].find(open_func_char)
                if idx > 0:
                    inspect_word = lines[0][:idx]
                    has_signature = True

        if has_signature:
            for i, line in enumerate(lines):
                if line.strip() == '':
                    break

            if i == 0:
                signature = lines[0]
                extra_text = None
            else:
                signature = '\n'.join(lines[:i])
                extra_text = '\n'.join(lines[i:])
                if extra_text == '\n':
                    extra_text = None

            if signature:
                new_signature = self._format_signature(
                    signatures=signature,
                    parameter=parameter,
                    max_width=max_width
                )
        else:
            new_signature = None
            extra_text = signature_or_text

        return new_signature, extra_text, inspect_word

    def _check_python_builtin(self, text):
        """Check if `text` matches a builtin docstring."""
        builtin = ''

        if BUILTINS_DOCSTRING_MAP.get(text):
            builtin = BUILTINS_DOCSTRING_MAP[text]

        # Another possibility is that the text after the signature matches
        # a buitin docstring (e.g. that's the case for Numpy objects).
        text_after_signature = '\n\n'.join(text.split('\n\n')[1:])
        if BUILTINS_DOCSTRING_MAP.get(text_after_signature):
            builtin = BUILTINS_DOCSTRING_MAP[text_after_signature]

        if builtin:
            return (
                # This makes the text appear centered
                "&nbsp;" +
                "This is " +
                # Use the right article in case we got an integer
                ("an " if builtin == 'integer' else "a ") +
                builtin
            )

    def show_calltip(
        self,
        signature,
        parameter=None,
        documentation=None,
        language=TIP_DEFAULT_LANGUAGE,
        max_lines=TIP_MAX_LINES,
        text_new_line=True
    ):
        """
        Show calltip.

        Calltips look like tooltips but will not disappear if mouse hovers
        them. They are useful for displaying signature information on methods
        and functions.
        """
        # Find position of calltip
        point = self._calculate_position()
        signature = signature.strip()
        inspect_word = None
        language = getattr(self, 'language', TIP_DEFAULT_LANGUAGE).lower()
        if language == 'python' and signature:
            inspect_word = signature.split('(')[0]
            # Check if documentation is better than signature, sometimes
            # signature has \n stripped for functions like print, type etc
            check_doc = ' '
            if documentation:
                check_doc.join(documentation.split()).replace('\\*', '*')
            check_sig = ' '.join(signature.split())
            if check_doc == check_sig:
                signature = documentation
                documentation = ''

        # Remove duplicate signature inside documentation
        if documentation:
            documentation = documentation.replace('\\*', '*')
            if signature.strip():
                documentation = documentation.replace(signature + '\n', '')

        # Format
        res = self._check_signature_and_format(signature, parameter,
                                               inspect_word=inspect_word,
                                               max_width=TIP_MAX_WIDTH)
        new_signature, text, inspect_word = res
        text = self._format_text(
            signature=new_signature,
            inspect_word=inspect_word,
            display_link=False,
            text=documentation,
            max_lines=max_lines,
            max_width=TIP_MAX_WIDTH,
            text_new_line=text_new_line
        )

        # Set a max width so the widget doesn't show up too large due to its
        # content, which looks bad.
        self.calltip_widget.setMaximumWidth(
            self._tip_width_in_pixels(TIP_MAX_WIDTH)
        )

        # Show calltip
        self.calltip_widget.show_tip(point, text, [])
        self.calltip_widget.show()

    def show_tooltip(
        self,
        text,
        title=None,
        at_line=None,
        at_point=None,
        with_html_format=False,
    ):
        """Show a tooltip."""
        # Prevent to hide the widget when used as a completion hint to reuse it
        # as a tooltip
        if self.tooltip_widget.is_hint():
            return

        # Find position
        point = self._calculate_position(at_line=at_line, at_point=at_point)

        # Format text
        tiptext = self._format_text(
            title=title,
            text=text,
            max_lines=TIP_MAX_LINES,
            with_html_format=with_html_format,
            text_new_line=True
        )

        # Set a max width so the widget doesn't show up too large due to its
        # content, which looks bad.
        self.tooltip_widget.setMaximumWidth(
            self._tip_width_in_pixels(TIP_MAX_WIDTH)
        )

        # Display tooltip
        self.tooltip_widget.set_as_tooltip()
        self.tooltip_widget.show_tip(point, tiptext)

    def show_hint(
        self,
        text,
        inspect_word,
        at_point,
        completion_doc=None,
        vertical_position="bottom",
        as_hover=False
    ):
        """Show code completion hint or hover."""
        # Max lines and width
        if as_hover:
            # Prevent to hide the widget when used as a completion hint to
            # reuse as a hover
            if self.tooltip_widget.is_hint():
                return

            self.tooltip_widget.set_as_hover()
            max_lines = HINT_MAX_LINES
            max_width = HINT_MAX_WIDTH
        else:
            self.tooltip_widget.set_as_hint()
            max_lines = TIP_MAX_LINES
            max_width = COMPLETION_HINT_MAX_WIDTH

        # Don't show full docstring for Python builtins, just its type
        display_link = True
        show_help_on_click = True
        language = getattr(self, 'language', TIP_DEFAULT_LANGUAGE).lower()

        if language == 'python':
            builtin_text = self._check_python_builtin(text)
            if builtin_text is not None:
                text = builtin_text
                display_link = False
                show_help_on_click = False
                completion_doc = None

        # Get signature and extra text from text
        res = self._check_signature_and_format(text, max_width=max_width,
                                               inspect_word=inspect_word)
        html_signature, extra_text, _ = res

        # Only display hint if there is documentation for it
        if extra_text is not None:
            # This is needed to show help when clicking on hover hints
            cursor = self.cursorForPosition(at_point)
            cursor.movePosition(QTextCursor.StartOfWord,
                                QTextCursor.MoveAnchor)
            self._last_hover_cursor = cursor

            # Get position and text for the hint
            point = self._calculate_position(
                at_point=self.get_word_start_pos(at_point)
            )

            tiptext = self._format_text(
                signature=html_signature,
                text=extra_text,
                inspect_word=inspect_word,
                display_link=display_link,
                max_lines=max_lines,
                max_width=max_width,
                text_new_line=True
            )

            # Adjust width
            self.tooltip_widget.setMaximumWidth(
                self._tip_width_in_pixels(max_width)
            )

            # Show hint
            self.tooltip_widget.show_tip(
                point,
                tiptext,
                completion_doc=completion_doc,
                vertical_position=vertical_position,
                show_help_on_click=show_help_on_click
            )

    def hide_tooltip(self):
        """
        Hide the tooltip widget.

        The tooltip widget is a special QLabel that looks like a tooltip,
        this method is here so it can be hidden as necessary. For example,
        when the user leaves the Linenumber area when hovering over lint
        warnings and errors.
        """
        self._last_hover_cursor = None
        self._last_hover_word = None
        self._last_point = None
        self.tooltip_widget.hide()

    def hide_calltip(self):
        """Hide the calltip widget."""
        self.calltip_widget.hide()

    # ---- Required methods for the LSP
    # -------------------------------------------------------------------------
    def document_did_change(self, text=None):
        pass

    # ---- EOL characters
    # -------------------------------------------------------------------------
    def set_eol_chars(self, text=None, eol_chars=None):
        """
        Set widget end-of-line (EOL) characters.

        Parameters
        ----------
        text: str
            Text to detect EOL characters from.
        eol_chars: str
            EOL characters to set.

        Notes
        -----
        If `text` is passed, then `eol_chars` has no effect.
        """
        if text is not None:
            detected_eol_chars = sourcecode.get_eol_chars(text)
            is_document_modified = (
                detected_eol_chars is not None and self.eol_chars is not None
            )
            self.eol_chars = detected_eol_chars
        elif eol_chars is not None:
            is_document_modified = eol_chars != self.eol_chars
            self.eol_chars = eol_chars

        if is_document_modified:
            self.document().setModified(True)
            if self.sig_eol_chars_changed is not None:
                self.sig_eol_chars_changed.emit(eol_chars)

    def get_line_separator(self):
        """Return line separator based on current EOL mode"""
        if self.eol_chars is not None:
            return self.eol_chars
        else:
            return os.linesep

    def get_text_with_eol(self):
        """
        Same as 'toPlainText', replacing '\n' by correct end-of-line
        characters.
        """
        text = self.toPlainText()
        linesep = self.get_line_separator()
        for symbol in EOL_SYMBOLS:
            text = text.replace(symbol, linesep)
        return text

    # ---- Positions, coordinates (cursor, EOF, ...)
    # -------------------------------------------------------------------------
    def get_position(self, subject):
        """Get offset in character for the given subject from the start of
           text edit area"""
        cursor = self.textCursor()
        if subject == 'cursor':
            pass
        elif subject == 'sol':
            cursor.movePosition(QTextCursor.StartOfBlock)
        elif subject == 'eol':
            cursor.movePosition(QTextCursor.EndOfBlock)
        elif subject == 'eof':
            cursor.movePosition(QTextCursor.End)
        elif subject == 'sof':
            cursor.movePosition(QTextCursor.Start)
        else:
            # Assuming that input argument was already a position
            return subject
        return cursor.position()

    def get_coordinates(self, position):
        position = self.get_position(position)
        cursor = self.textCursor()
        cursor.setPosition(position)
        point = self.cursorRect(cursor).center()
        return point.x(), point.y()

    def _is_point_inside_word_rect(self, point):
        """
        Check if the mouse is within the rect of the cursor current word.
        """
        cursor = self.cursorForPosition(point)
        cursor.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
        start_rect = self.cursorRect(cursor)
        cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.MoveAnchor)
        end_rect = self.cursorRect(cursor)
        bounding_rect = start_rect.united(end_rect)
        return bounding_rect.contains(point)

    def get_word_start_pos(self, position):
        """
        Find start position (lower bottom) of a word being hovered by mouse.
        """
        cursor = self.cursorForPosition(position)
        cursor.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
        rect = self.cursorRect(cursor)
        pos = QPoint(rect.left() + 4, rect.top())
        return pos

    def get_last_hover_word(self):
        """Return the last (or active) hover word."""
        return self._last_hover_word

    def get_last_hover_cursor(self):
        """Return the last (or active) hover cursor."""
        return self._last_hover_cursor

    def get_cursor_line_column(self, cursor=None):
        """
        Return `cursor` (line, column) numbers.

        If no `cursor` is provided, use the current text cursor.
        """
        if cursor is None:
            cursor = self.textCursor()

        return cursor.blockNumber(), cursor.columnNumber()

    def get_cursor_line_number(self):
        """Return cursor line number"""
        return self.textCursor().blockNumber()+1

    def get_position_line_number(self, line, col):
        """Get position offset from (line, col) coordinates."""
        block = self.document().findBlockByNumber(line)
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor,
                            n=col + 1)
        return cursor.position()

    def set_cursor_position(self, position):
        """Set cursor position"""
        position = self.get_position(position)
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def move_cursor(self, chars=0):
        """Move cursor to left or right (unit: characters)"""
        direction = QTextCursor.Right if chars > 0 else QTextCursor.Left
        for _i in range(abs(chars)):
            self.moveCursor(direction, QTextCursor.MoveAnchor)

    def is_cursor_on_first_line(self):
        """Return True if cursor is on the first line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        return cursor.atStart()

    def is_cursor_on_last_line(self):
        """Return True if cursor is on the last line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.EndOfBlock)
        return cursor.atEnd()

    def is_cursor_at_end(self):
        """Return True if cursor is at the end of the text"""
        return self.textCursor().atEnd()

    def is_cursor_before(self, position, char_offset=0):
        """Return True if cursor is before *position*"""
        position = self.get_position(position) + char_offset
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        if position < cursor.position():
            cursor.setPosition(position)
            return self.textCursor() < cursor

    def __move_cursor_anchor(self, what, direction, move_mode):
        assert what in ('character', 'word', 'line')
        if what == 'character':
            if direction == 'left':
                self.moveCursor(QTextCursor.PreviousCharacter, move_mode)
            elif direction == 'right':
                self.moveCursor(QTextCursor.NextCharacter, move_mode)
        elif what == 'word':
            if direction == 'left':
                self.moveCursor(QTextCursor.PreviousWord, move_mode)
            elif direction == 'right':
                self.moveCursor(QTextCursor.NextWord, move_mode)
        elif what == 'line':
            if direction == 'down':
                self.moveCursor(QTextCursor.NextBlock, move_mode)
            elif direction == 'up':
                self.moveCursor(QTextCursor.PreviousBlock, move_mode)

    def move_cursor_to_next(self, what='word', direction='left'):
        """
        Move cursor to next *what* ('word' or 'character')
        toward *direction* ('left' or 'right')
        """
        self.__move_cursor_anchor(what, direction, QTextCursor.MoveAnchor)

    # ---- Selection
    # -------------------------------------------------------------------------
    def extend_selection_to_next(self, what='word', direction='left'):
        """
        Extend selection to next *what* ('word' or 'character')
        toward *direction* ('left' or 'right')
        """
        self.__move_cursor_anchor(what, direction, QTextCursor.KeepAnchor)

    # ---- Text: get, set, ...
    # -------------------------------------------------------------------------
    def _select_text(self, position_from, position_to):
        """Select text and return cursor."""
        position_from = self.get_position(position_from)
        position_to = self.get_position(position_to)
        cursor = self.textCursor()
        cursor.setPosition(position_from)
        cursor.setPosition(position_to, QTextCursor.KeepAnchor)
        return cursor

    def get_text_line(self, line_nb):
        """Return text line at line number *line_nb*"""
        block = self.document().findBlockByNumber(line_nb)
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, mode=QTextCursor.KeepAnchor)
        return to_text_string(cursor.selectedText())

    def get_text_region(self, start_line, end_line, lines=None):
        """
        Return text in a given region.

        Parameters
        ----------
        start_line: int
            Start line of the region.
        end_line: int
            End line of the region.
        lines: list, optional (default None)
            File lines.
        """
        if lines is None:
            lines = self.toPlainText().splitlines()

        lines_in_region = lines[start_line:end_line + 1]
        return self.get_line_separator().join(lines_in_region)

    def get_text(self, position_from, position_to, remove_newlines=True):
        """Returns text between *position_from* and *position_to*.

        Positions may be integers or 'sol', 'eol', 'sof', 'eof' or 'cursor'.

        Unless position_from='sof' and position_to='eof' any trailing newlines
        in the string are removed. This was added as a workaround for
        spyder-ide/spyder#1546 and later caused spyder-ide/spyder#14374.
        The behaviour can be overridden by setting the optional parameter
        *remove_newlines* to False.

        TODO: Evaluate if this is still a problem and if the workaround can
              be moved closer to where the problem occurs.
        """
        cursor = self._select_text(position_from, position_to)
        text = to_text_string(cursor.selectedText())
        if remove_newlines:
            remove_newlines = position_from != 'sof' or position_to != 'eof'
        if text and remove_newlines:
            while text and text[-1] in EOL_SYMBOLS:
                text = text[:-1]
        return text

    def get_character(self, position, offset=0):
        """Return character at *position* with the given offset."""
        position = self.get_position(position) + offset
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        if position < cursor.position():
            cursor.setPosition(position)
            cursor.movePosition(QTextCursor.Right,
                                QTextCursor.KeepAnchor)
            return to_text_string(cursor.selectedText())
        else:
            return ''

    def insert_text(self, text, will_insert_text=True):
        """Insert text at cursor position"""
        if not self.isReadOnly():
            if will_insert_text and self.sig_will_insert_text is not None:
                self.sig_will_insert_text.emit(text)
            self.textCursor().insertText(text)
            if self.sig_text_was_inserted is not None:
                self.sig_text_was_inserted.emit()

    def replace_text(self, position_from, position_to, text):
        cursor = self._select_text(position_from, position_to)
        if self.sig_will_remove_selection is not None:
            start, end = self.get_selection_start_end(cursor)
            self.sig_will_remove_selection.emit(start, end)
        cursor.removeSelectedText()
        if self.sig_will_insert_text is not None:
            self.sig_will_insert_text.emit(text)
        cursor.insertText(text)
        if self.sig_text_was_inserted is not None:
            self.sig_text_was_inserted.emit()

    def remove_text(self, position_from, position_to):
        cursor = self._select_text(position_from, position_to)
        if self.sig_will_remove_selection is not None:
            start, end = self.get_selection_start_end(cursor)
            self.sig_will_remove_selection.emit(start, end)
        cursor.removeSelectedText()

    def get_current_object(self):
        """
        Return current object under cursor.

        Get the text of the current word plus all the characters
        to the left until a space is found. Used to get text to inspect
        for Help of elements following dot notation for example
        np.linalg.norm
        """
        cursor = self.textCursor()
        cursor_pos = cursor.position()
        current_word = self.get_current_word(help_req=True)

        # Get max position to the left of cursor until space or no more
        # characters are left
        cursor.movePosition(QTextCursor.PreviousCharacter)
        while self.get_character(cursor.position()).strip():
            cursor.movePosition(QTextCursor.PreviousCharacter)
            if cursor.atBlockStart():
                break
        cursor_pos_left = cursor.position()

        # Get max position to the right of cursor until space or no more
        # characters are left
        cursor.setPosition(cursor_pos)
        while self.get_character(cursor.position()).strip():
            cursor.movePosition(QTextCursor.NextCharacter)
            if cursor.atBlockEnd():
                break
        cursor_pos_right = cursor.position()

        # Get text of the object under the cursor
        current_text = self.get_text(
            cursor_pos_left, cursor_pos_right).strip()
        current_object = current_word

        if current_text and current_word is not None:
            if current_word != current_text and current_word in current_text:
                current_object = (
                    current_text.split(current_word)[0] + current_word)

        return current_object

    def get_current_word_and_position(self, completion=False, help_req=False,
                                      valid_python_variable=True):
        """
        Return current word, i.e. word at cursor position, and the start
        position.
        """
        cursor = self.textCursor()
        cursor_pos = cursor.position()

        if cursor.hasSelection():
            # Removes the selection and moves the cursor to the left side
            # of the selection: this is required to be able to properly
            # select the whole word under cursor (otherwise, the same word is
            # not selected when the cursor is at the right side of it):
            cursor.setPosition(min([cursor.selectionStart(),
                                    cursor.selectionEnd()]))
        else:
            # Checks if the first character to the right is a white space
            # and if not, moves the cursor one word to the left (otherwise,
            # if the character to the left do not match the "word regexp"
            # (see below), the word to the left of the cursor won't be
            # selected), but only if the first character to the left is not a
            # white space too.
            def is_space(move):
                curs = self.textCursor()
                curs.movePosition(move, QTextCursor.KeepAnchor)
                return not to_text_string(curs.selectedText()).strip()

            def is_special_character(move):
                """Check if a character is a non-letter including numbers."""
                curs = self.textCursor()
                curs.movePosition(move, QTextCursor.KeepAnchor)
                text_cursor = to_text_string(curs.selectedText()).strip()
                return len(
                    re.findall(r'([^\d\W]\w*)', text_cursor, re.UNICODE)) == 0

            if help_req:
                if is_special_character(QTextCursor.PreviousCharacter):
                    cursor.movePosition(QTextCursor.NextCharacter)
                elif is_special_character(QTextCursor.NextCharacter):
                    cursor.movePosition(QTextCursor.PreviousCharacter)
            elif not completion:
                if is_space(QTextCursor.NextCharacter):
                    if is_space(QTextCursor.PreviousCharacter):
                        return
                    cursor.movePosition(QTextCursor.WordLeft)
            else:
                if is_space(QTextCursor.PreviousCharacter):
                    return
                if (is_special_character(QTextCursor.NextCharacter)):
                    cursor.movePosition(QTextCursor.WordLeft)

        cursor.select(QTextCursor.WordUnderCursor)
        text = to_text_string(cursor.selectedText())
        startpos = cursor.selectionStart()

        # Find a valid Python variable name
        if valid_python_variable:
            match = re.findall(r'([^\d\W]\w*)', text, re.UNICODE)
            if not match:
                # This is assumed in several places of our codebase,
                # so please don't change this return!
                return None
            else:
                text = match[0]

        if completion:
            text = text[:cursor_pos - startpos]

        return text, startpos

    def get_current_word(self, completion=False, help_req=False,
                         valid_python_variable=True):
        """Return current word, i.e. word at cursor position."""
        ret = self.get_current_word_and_position(
            completion=completion,
            help_req=help_req,
            valid_python_variable=valid_python_variable
        )

        if ret is not None:
            return ret[0]

    def get_hover_word(self):
        """Return the last hover word that requested a hover hint."""
        return self._last_hover_word

    def get_current_line(self):
        """Return current line's text."""
        cursor = self.textCursor()
        cursor.select(QTextCursor.BlockUnderCursor)
        return to_text_string(cursor.selectedText())

    def get_current_line_bounds(self):
        """Return the (line, column) bounds for the current line."""
        cursor = self.textCursor()
        cursor.select(QTextCursor.BlockUnderCursor)
        return self.get_selection_start_end(cursor)

    def get_current_line_offsets(self):
        """Return the start and end offset positions for the current line."""
        cursor = self.textCursor()
        cursor.select(QTextCursor.BlockUnderCursor)
        return self.get_selection_offsets()

    def get_current_line_to_cursor(self):
        """Return text from prompt to cursor."""
        return self.get_text(self.current_prompt_pos, 'cursor')

    def get_line_number_at(self, coordinates):
        """Return line number at *coordinates* (QPoint)."""
        cursor = self.cursorForPosition(coordinates)
        return cursor.blockNumber() + 1

    def get_line_at(self, coordinates):
        """Return line at *coordinates* (QPoint)."""
        cursor = self.cursorForPosition(coordinates)
        cursor.select(QTextCursor.BlockUnderCursor)
        return to_text_string(cursor.selectedText()).replace(u'\u2029', '')

    def get_word_at(self, coordinates):
        """Return word at *coordinates* (QPoint)."""
        cursor = self.cursorForPosition(coordinates)
        cursor.select(QTextCursor.WordUnderCursor)
        if self._is_point_inside_word_rect(coordinates):
            word = to_text_string(cursor.selectedText())
        else:
            word = ''

        return word

    def get_line_indentation(self, text):
        """Get indentation for given line."""
        text = text.replace("\t", " "*self.tab_stop_width_spaces)
        return len(text)-len(text.lstrip())

    def get_block_indentation(self, block_nb):
        """Return line indentation (character number)."""
        text = to_text_string(self.document().findBlockByNumber(block_nb).text())
        return self.get_line_indentation(text)

    def get_selection_bounds(self, cursor=None):
        """Return selection bounds (block numbers)."""
        if cursor is None:
            cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        block_start = self.document().findBlock(start)
        block_end = self.document().findBlock(end)
        return sorted([block_start.blockNumber(), block_end.blockNumber()])

    def get_selection_start_end(self, cursor=None):
        """Return selection start and end (line, column) positions."""
        if cursor is None:
            cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        start_cursor = QTextCursor(cursor)
        start_cursor.setPosition(start)
        start_position = self.get_cursor_line_column(start_cursor)
        end_cursor = QTextCursor(cursor)
        end_cursor.setPosition(end)
        end_position = self.get_cursor_line_column(end_cursor)
        return start_position, end_position

    # ---- Text selection
    # -------------------------------------------------------------------------
    def get_selection_offsets(self, cursor=None):
        """Return selection start and end offset positions."""
        if cursor is None:
            cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        return start, end

    def has_selected_text(self):
        """Returns True if some text is selected."""
        return bool(to_text_string(self.textCursor().selectedText()))

    def get_selected_text(self, cursor=None):
        """
        Return text selected by current text cursor, converted in unicode.

        Replace the unicode line separator character \u2029 by
        the line separator characters returned by get_line_separator
        """
        if cursor is None:
            cursor = self.textCursor()
        return to_text_string(cursor.selectedText()).replace(
            u"\u2029", self.get_line_separator()
        )

    def remove_selected_text(self):
        """Delete selected text."""
        self.textCursor().removeSelectedText()
        # The next three lines are a workaround for a quirk of
        # QTextEdit on Linux with Qt < 5.15, MacOs and Windows.
        # See spyder-ide/spyder#12663 and
        # https://bugreports.qt.io/browse/QTBUG-35861
        if (
            parse(QT_VERSION) < parse('5.15')
            or os.name == 'nt' or sys.platform == 'darwin'
        ):
            cursor = self.textCursor()
            cursor.setPosition(cursor.position())
            self.setTextCursor(cursor)

    def replace(self, text, pattern=None):
        """Replace selected text by *text*.

        If *pattern* is not None, replacing selected text using regular
        expression text substitution."""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if pattern is not None:
            seltxt = to_text_string(cursor.selectedText())
        if self.sig_will_remove_selection is not None:
            start, end = self.get_selection_start_end(cursor)
            self.sig_will_remove_selection.emit(start, end)
        cursor.removeSelectedText()
        if pattern is not None:
            text = re.sub(to_text_string(pattern),
                          to_text_string(text), to_text_string(seltxt))
        if self.sig_will_insert_text is not None:
            self.sig_will_insert_text.emit(text)
        cursor.insertText(text)
        if self.sig_text_was_inserted is not None:
            self.sig_text_was_inserted.emit()
        cursor.endEditBlock()

    # ---- Find/replace
    # -------------------------------------------------------------------------
    def find_multiline_pattern(self, regexp, cursor, findflag):
        """Reimplement QTextDocument's find method.

        Add support for *multiline* regular expressions."""
        pattern = to_text_string(regexp.pattern())
        text = to_text_string(self.toPlainText())
        try:
            regobj = re.compile(pattern)
        except re.error:
            return
        if findflag & QTextDocument.FindBackward:
            # Find backward
            offset = min([cursor.selectionEnd(), cursor.selectionStart()])
            text = text[:offset]
            matches = [_m for _m in regobj.finditer(text, 0, offset)]
            if matches:
                match = matches[-1]
            else:
                return
        else:
            # Find forward
            offset = max([cursor.selectionEnd(), cursor.selectionStart()])
            match = regobj.search(text, offset)
        if match:
            pos1, pos2 = sh.get_span(match)
            fcursor = self.textCursor()
            fcursor.setPosition(pos1)
            fcursor.setPosition(pos2, QTextCursor.KeepAnchor)
            return fcursor

    def find_text(self, text, changed=True, forward=True, case=False,
                  word=False, regexp=False):
        """Find text."""
        cursor = self.textCursor()
        findflag = QTextDocument.FindFlag(0)

        # Get visible region to center cursor in case it's necessary.
        if getattr(self, 'get_visible_block_numbers', False):
            current_visible_region = self.get_visible_block_numbers()
        else:
            current_visible_region = None

        if not forward:
            findflag = findflag | QTextDocument.FindBackward

        if case:
            findflag = findflag | QTextDocument.FindCaseSensitively

        moves = [QTextCursor.NoMove]
        if forward:
            moves += [QTextCursor.NextWord, QTextCursor.Start]
            if changed:
                if to_text_string(cursor.selectedText()):
                    new_position = min([cursor.selectionStart(),
                                        cursor.selectionEnd()])
                    cursor.setPosition(new_position)
                else:
                    cursor.movePosition(QTextCursor.PreviousWord)
        else:
            moves += [QTextCursor.End]

        if regexp:
            text = to_text_string(text)
        else:
            text = re.escape(to_text_string(text))

        pattern = QRegularExpression(u"\\b{}\\b".format(text) if word else
                                     text)
        if case:
            pattern.setPatternOptions(QRegularExpression.CaseInsensitiveOption)

        for move in moves:
            cursor.movePosition(move)
            if regexp and '\\n' in text:
                # Multiline regular expression
                found_cursor = self.find_multiline_pattern(pattern, cursor,
                                                           findflag)
            else:
                # Single line find: using the QTextDocument's find function,
                # probably much more efficient than ours
                found_cursor = self.document().find(pattern, cursor, findflag)
            if found_cursor is not None and not found_cursor.isNull():
                self.setTextCursor(found_cursor)

                # Center cursor if we move out of the visible region.
                if current_visible_region is not None:
                    found_visible_region = self.get_visible_block_numbers()
                    if current_visible_region != found_visible_region:
                        current_visible_region = found_visible_region
                        self.centerCursor()

                return True

        return False

    def is_editor(self):
        """Needs to be overloaded in the codeeditor where it will be True"""
        return False

    def get_number_matches(self, pattern, source_text='', case=False,
                           regexp=False, word=False):
        """Get the number of matches for the searched text."""
        pattern = to_text_string(pattern)
        if not pattern:
            return 0

        if not regexp:
            pattern = re.escape(pattern)

        if not source_text:
            source_text = to_text_string(self.toPlainText())

        if word:  # match whole words only
            pattern = r'\b{pattern}\b'.format(pattern=pattern)
        try:
            re_flags = re.MULTILINE if case else re.IGNORECASE | re.MULTILINE
            regobj = re.compile(pattern, flags=re_flags)
        except re.error:
            return None

        number_matches = 0
        for match in regobj.finditer(source_text):
            number_matches += 1

        return number_matches

    def get_match_number(self, pattern, case=False, regexp=False, word=False):
        """Get number of the match for the searched text."""
        position = self.textCursor().position()
        source_text = self.get_text(position_from='sof', position_to=position)
        match_number = self.get_number_matches(pattern,
                                               source_text=source_text,
                                               case=case, regexp=regexp,
                                               word=word)
        return match_number

    # ---- Array builder helper methods
    # -------------------------------------------------------------------------
    def enter_array_inline(self):
        """Enter array builder inline mode."""
        self._enter_array(True)

    def enter_array_table(self):
        """Enter array builder table mode."""
        self._enter_array(False)

    def _enter_array(self, inline):
        """Enter array builder mode."""
        offset = self.get_position('cursor') - self.get_position('sol')
        rect = self.cursorRect()
        dlg = ArrayBuilderDialog(self, inline, offset)

        # TODO: adapt to font size
        x = rect.left()
        x = int(x - 14)
        y = rect.top() + (rect.bottom() - rect.top())/2
        y = int(y - dlg.height()/2 - 3)

        pos = QPoint(x, y)
        pos = self.calculate_real_position(pos)
        dlg.move(self.mapToGlobal(pos))

        # called from editor
        if self.is_editor():
            python_like_check = self.is_python_like()
            suffix = '\n'
        # called from a console
        else:
            python_like_check = True
            suffix = ''

        if python_like_check and dlg.exec_():
            text = dlg.text() + suffix
            if text != '':
                cursor = self.textCursor()
                cursor.beginEditBlock()
                if self.sig_will_insert_text is not None:
                    self.sig_will_insert_text.emit(text)
                cursor.insertText(text)
                if self.sig_text_was_inserted is not None:
                    self.sig_text_was_inserted.emit()
                cursor.endEditBlock()

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def mouseDoubleClickEvent(self, event):
        """Select NUMBER tokens to select numeric literals on double click."""
        cursor = self.cursorForPosition(event.pos())
        block = cursor.block()
        text = block.text()
        pos = block.position()
        pos_in_block = cursor.positionInBlock()

        # Strip quotes to prevent tokenizer from trying to emit STRING tokens
        #   because we want to interpret numbers inside strings. This solves
        #   an EOF error trying to double click a line with opening or closing
        #   triple quotes as well.
        text = text.replace('"', ' ').replace("'", ' ')
        readline = StringIO(text).read

        try:
            for t_type, _, start, end, _ in generate_tokens(readline):
                if t_type == NUMBER and start[1] <= pos_in_block <= end[1]:
                    cursor.setPosition(pos + start[1])
                    cursor.setPosition(
                        pos + end[1], QTextCursor.MoveMode.KeepAnchor
                    )
                    self.setTextCursor(cursor)
                    return
                elif start[1] > pos_in_block:
                    break
        except TokenError:
            # Ignore 'EOF in multi-line statement' from tokenize._tokenize
            # IndentationError should be impossible from tokenizing one line
            pass

        if isinstance(self, QPlainTextEdit):
            QPlainTextEdit.mouseDoubleClickEvent(self, event)
        elif isinstance(self, QTextEdit):
            QTextEdit.mouseDoubleClickEvent(self, event)

    def inputMethodQuery(self, query):
        """
        Prevent Chinese input method to block edit input area.

        Notes
        -----
        This was suggested by a user in spyder-ide/spyder#23313. So, it's not
        tested by us.
        """
        if query == Qt.ImInputItemClipRectangle:
            cursor_rect = self.cursorRect()
            margins = self.viewportMargins()
            cursor_rect.moveTopLeft(
                cursor_rect.topLeft() + QPoint(margins.left(), margins.top())
            )
            return cursor_rect

        if isinstance(self, QPlainTextEdit):
            QPlainTextEdit.inputMethodQuery(self, query)
        elif isinstance(self, QTextEdit):
            QTextEdit.inputMethodQuery(self, query)


class TracebackLinksMixin(object):
    """Mixin to make file names in tracebacks and anchors clickable."""
    QT_CLASS = None

    # This signal emits a parsed error traceback text so we can then
    # request opening the file that traceback comes from in the Editor.
    sig_go_to_error_requested = None

    def __init__(self):
        self.__cursor_changed = False
        self.anchor = None
        self.setMouseTracking(True)

    def mouseReleaseEvent(self, event):
        """Go to error or link in anchor."""
        self.QT_CLASS.mouseReleaseEvent(self, event)
        text = self.get_line_at(event.pos())

        if get_error_match(text) and not self.has_selected_text():
            if self.sig_go_to_error_requested is not None:
                self.sig_go_to_error_requested.emit(text)
        elif self.anchor:
            QDesktopServices.openUrl(QUrl(self.anchor))
            QApplication.restoreOverrideCursor()
            self.anchor = None

    def mouseMoveEvent(self, event):
        """Show pointing hand cursor on error messages and anchors."""
        text = self.get_line_at(event.pos())
        self.anchor = self.anchorAt(event.pos())

        if get_error_match(text) or self.anchor:
            if not self.__cursor_changed:
                QApplication.setOverrideCursor(Qt.PointingHandCursor)
                self.__cursor_changed = True
            event.accept()
            return

        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False

        self.QT_CLASS.mouseMoveEvent(self, event)

    def leaveEvent(self, event):
        """If cursor has not been restored yet, do it now"""
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False

        self.QT_CLASS.leaveEvent(self, event)


class GetHelpMixin(object):

    def __init__(self):
        self.help_enabled = False

    def set_help_enabled(self, state):
        self.help_enabled = state

    def inspect_current_object(self):
        current_object = self.get_current_object()
        if current_object is not None:
            self.show_object_info(current_object, force=True)

    def show_object_info(self, text, call=False, force=False):
        """Show signature calltip and/or docstring in the Help plugin"""
        text = to_text_string(text)

        # Show docstring
        help_enabled = self.help_enabled or force
        if help_enabled:
            doc = {
                'name': text,
                'ignore_unknown': False,
            }
            self.sig_help_requested.emit(doc)

        # Show calltip
        if call and getattr(self, 'calltips', None):
            # Display argument list if this is a function call
            iscallable = self.iscallable(text)
            if iscallable is not None:
                if iscallable:
                    arglist = self.get_arglist(text)
                    name =  text.split('.')[-1]
                    argspec = signature = ''
                    if isinstance(arglist, bool):
                        arglist = []
                    if arglist:
                        argspec = '(' + ''.join(arglist) + ')'
                    else:
                        doc = self.get__doc__(text)
                        if doc is not None:
                            # This covers cases like np.abs, whose docstring is
                            # the same as np.absolute and because of that a
                            # proper signature can't be obtained correctly
                            argspec = getargspecfromtext(doc)
                            if not argspec:
                                signature = getsignaturefromtext(doc, name)
                    if argspec or signature:
                        if argspec:
                            tiptext = name + argspec
                        else:
                            tiptext = signature
                        # TODO: Select language and pass it to call
                        self.show_calltip(tiptext)

    def get_last_obj(self, last=False):
        """
        Return the last valid object on the current line
        """
        return getobj(self.get_current_line_to_cursor(), last=last)


class SaveHistoryMixin(object):

    INITHISTORY = None
    SEPARATOR = None
    HISTORY_FILENAMES = []

    sig_append_to_history_requested = None

    def __init__(self, history_filename=''):
        self.history_filename = history_filename
        self.create_history_filename()

    def create_history_filename(self):
        """Create history_filename with INITHISTORY if it doesn't exist."""
        if self.history_filename and not osp.isfile(self.history_filename):
            try:
                encoding.writelines(self.INITHISTORY, self.history_filename)
            except EnvironmentError:
                pass

    def add_to_history(self, command):
        """Add command to history"""
        command = to_text_string(command)
        if command in ['', '\n'] or command.startswith('Traceback'):
            return
        if command.endswith('\n'):
            command = command[:-1]
        self.histidx = None
        if len(self.history) > 0 and self.history[-1] == command:
            return
        self.history.append(command)
        text = os.linesep + command

        # When the first entry will be written in history file,
        # the separator will be append first:
        if self.history_filename not in self.HISTORY_FILENAMES:
            self.HISTORY_FILENAMES.append(self.history_filename)
            text = self.SEPARATOR + text
        # Needed to prevent errors when writing history to disk
        # See spyder-ide/spyder#6431.
        try:
            encoding.write(text, self.history_filename, mode='ab')
        except EnvironmentError:
            pass
        if self.sig_append_to_history_requested is not None:
            self.sig_append_to_history_requested.emit(
                self.history_filename, text)


class BrowseHistory(object):

    def __init__(self):
        self.history = []
        self.histidx = None
        self.hist_wholeline = False

    def browse_history(self, line, cursor_pos, backward):
        """
        Browse history.

        Return the new text and wherever the cursor should move.
        """
        if cursor_pos < len(line) and self.hist_wholeline:
            self.hist_wholeline = False
        tocursor = line[:cursor_pos]
        text, self.histidx = self.find_in_history(tocursor, self.histidx,
                                                  backward)
        if text is not None:
            text = text.strip()
            if self.hist_wholeline:
                return text, True
            else:
                return tocursor + text, False
        return None, False

    def find_in_history(self, tocursor, start_idx, backward):
        """Find text 'tocursor' in history, from index 'start_idx'"""
        if start_idx is None:
            start_idx = len(self.history)
        # Finding text in history
        step = -1 if backward else 1
        idx = start_idx
        if len(tocursor) == 0 or self.hist_wholeline:
            idx += step
            if idx >= len(self.history) or len(self.history) == 0:
                return "", len(self.history)
            elif idx < 0:
                idx = 0
            self.hist_wholeline = True
            return self.history[idx], idx
        else:
            for index in range(len(self.history)):
                idx = (start_idx+step*(index+1)) % len(self.history)
                entry = self.history[idx]
                if entry.startswith(tocursor):
                    return entry[len(tocursor):], idx
            else:
                return None, start_idx

    def reset_search_pos(self):
        """Reset the position from which to search the history"""
        self.histidx = None


class BrowseHistoryMixin(BrowseHistory):

    def clear_line(self):
        """Clear current line (without clearing console prompt)"""
        self.remove_text(self.current_prompt_pos, 'eof')

    def browse_history(self, backward):
        """Browse history"""
        line = self.get_text(self.current_prompt_pos, 'eof')
        old_pos = self.get_position('cursor')
        cursor_pos = self.get_position('cursor') - self.current_prompt_pos
        if cursor_pos < 0:
            cursor_pos = 0
            self.set_cursor_position(self.current_prompt_pos)
        text, move_cursor = super(BrowseHistoryMixin, self).browse_history(
            line, cursor_pos, backward)
        if text is not None:
            self.clear_line()
            self.insert_text(text)
            if not move_cursor:
                self.set_cursor_position(old_pos)

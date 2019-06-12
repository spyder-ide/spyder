# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Mix-in classes

These classes were created to be able to provide Spyder's regular text and
console widget features to an independant widget based on QTextEdit for the
IPython console plugin.
"""

# Standard library imports
from __future__ import print_function
from xml.sax.saxutils import escape
import os
import os.path as osp
import re
import sre_constants
import sys
import textwrap

# Third party imports
import qdarkstyle
from qtpy.QtCore import QPoint, Qt, QCoreApplication
from qtpy.QtGui import QCursor, QTextCursor, QTextDocument
from qtpy.QtWidgets import QApplication, QToolTip
from qtpy import QT_VERSION
from spyder_kernels.utils.dochelpers import (getargspecfromtext, getobj,
                                             getsignaturefromtext)

# Local imports
from spyder.config.base import _
from spyder.config.gui import is_dark_interface
from spyder.config.main import CONF
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding, sourcecode, programs
from spyder.utils.misc import get_error_match
from spyder.widgets.arraybuilder import NumpyArrayDialog

QT55_VERSION = programs.check_version(QT_VERSION, "5.5", ">=")

if QT55_VERSION:
    from qtpy.QtCore import QRegularExpression
else:
    from qtpy.QtCore import QRegExp


class BaseEditMixin(object):

    _PARAMETER_HIGHLIGHT_COLOR = '#DAA520'
    _DEFAULT_TITLE_COLOR = '#2D62FF'
    _CHAR_HIGHLIGHT_COLOR = 'red'
    _DEFAULT_TEXT_COLOR = '#999999'
    _DEFAULT_LANGUAGE = 'python'

    def __init__(self):
        self.eol_chars = None
        self.calltip_size = 600

    #------Line number area
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

    # --- Tooltips and Calltips
    def _calculate_position(self, at_line=None, at_point=None):
        """
        Calculate a global point position `QPoint(x, y)`, for a given
        line, local cursor position, or local point.
        """
        font = self.font()

        if at_point is not None:
            # Showing tooltip at point position
            cx, cy = at_point.x(), at_point.y()
        elif at_line is not None:
            # Showing tooltip at line
            cx = 5
            line = at_line - 1
            cursor = QTextCursor(self.document().findBlockByNumber(line))
            cy = self.cursorRect(cursor).top()
        else:
            # Showing tooltip at cursor position
            cx, cy = self.get_coordinates('cursor')
            cy = cy - font.pointSize() / 2

        # Calculate vertical delta
        # The needed delta changes with font size, so we use a power law
        if sys.platform == 'darwin':
            delta = int((font.pointSize() * 1.20) ** 0.98) + 4.5
        elif os.name == 'nt':
            delta = int((font.pointSize() * 1.20) ** 1.05) + 7
        else:
            delta = int((font.pointSize() * 1.20) ** 0.98) + 7
        # delta = font.pointSize() + 5

        # Map to global coordinates
        point = self.mapToGlobal(QPoint(cx, cy))
        point = self.calculate_real_position(point)
        point.setY(point.y() + delta)

        return point

    def _update_stylesheet(self, widget):
        """Update the background stylesheet to make it lighter."""
        if is_dark_interface():
            css = qdarkstyle.load_stylesheet_from_environment()
            widget.setStyleSheet(css)
            palette = widget.palette()
            background = palette.color(palette.Window).lighter(150).name()
            border = palette.color(palette.Window).lighter(200).name()
            name = widget.__class__.__name__
            widget.setObjectName(name)
            extra_css = '''
                {0}#{0} {{
                    background-color:{1};
                    border: 1px solid {2};
                }}'''.format(name, background, border)
            widget.setStyleSheet(css + extra_css)

    def _get_inspect_shortcut(self):
        """
        Queries the editor's config to get the current "Inspect" shortcut.
        """
        value = CONF.get('shortcuts', 'editor/inspect current object')
        if value:
            if sys.platform == "darwin":
                value = value.replace('Ctrl', 'Cmd')
        return value

    def _format_text(self, title=None, signature=None, text=None,
                     inspect_word=None, title_color=None, max_lines=None,
                     display_link=False):
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
        | Link or shortcut with `inspect_word` |
        ----------------------------------------
        """
        BASE_TEMPLATE = '''
            <div style=\'font-family: "{font_family}";
                        font-size: {size}pt;
                        color: {color}\'>
                {main_text}
            </div>
        '''
        # Get current font properties
        font = self.font()
        font_family = font.family()
        title_size = font.pointSize()
        text_size = title_size - 1 if title_size > 9 else title_size
        text_color = self._DEFAULT_TEXT_COLOR

        template = ''
        if title:
            template += BASE_TEMPLATE.format(
                font_family=font_family,
                size=title_size,
                color=title_color,
                main_text=title,
            )

            if text or signature:
                template += '<hr>'

        if signature:
            template += BASE_TEMPLATE.format(
                font_family=font_family,
                size=text_size,
                color=text_color,
                main_text=signature,
            )

        # Documentation/text handling
        if not text:
            text = '\n<i>No documentation available</i>\n'

        # Remove empty lines at the beginning
        lines = [l for l in text.split('\n') if l.strip()]

        # Limit max number of text displayed
        if max_lines:
            lines = text.split('\n')
            if len(lines) > max_lines:
                text = '\n'.join(lines[:max_lines]) + ' ...'

        text = text.replace('\n', '<br>')
        template += BASE_TEMPLATE.format(
            font_family=font_family,
            size=text_size,
            color=text_color,
            main_text=text,
        )

        help_text = ''
        if inspect_word:
            if display_link:
                help_text = (
                    '<span style="font-family: \'{font_family}\';'
                    'font-size:{font_size}pt;">'
                    'Click anywhere in this tooltip for additional help'
                    '</span>'.format(
                        font_size=text_size,
                        font_family=font_family,
                    )
                )
            else:
                shortcut = self._get_inspect_shortcut()
                if shortcut:
                    base_style = (
                        'background-color:#fafbfc;color:#444d56;'
                        'font-size:11px;'
                    )
                    help_text = ''
                    # (
                    #     'Press '
                    #     '<kbd style="{1}">[</kbd>'
                    #     '<kbd style="{1}text-decoration:underline;">'
                    #     '{0}</kbd><kbd style="{1}">]</kbd> for aditional '
                    #     'help'.format(shortcut, base_style)
                    # )

        if help_text and inspect_word:
            if display_link:
                template += (
                    '<hr>'
                    '<div align="left">'
                    '<span style="color:#148CD2;text-decoration:none;'
                    'font-family:"{font_family}";font-size:{size}pt;><i>'
                    ''.format(font_family=font_family,
                              size=text_size)
                    ) + help_text + '</i></span></div>'
            else:
                template += (
                    '<hr>'
                    '<div align="left">'
                    '<span style="color:white;text-decoration:none;">'
                    '' + help_text + '</span></div>'
                )

        return template

    def _format_signature(self, signatures, parameter=None,
                          parameter_color=_PARAMETER_HIGHLIGHT_COLOR,
                          char_color=_CHAR_HIGHLIGHT_COLOR,
                          language=_DEFAULT_LANGUAGE):
        """
        Create HTML template for signature.

        This template will include indent after the method name, a highlight
        color for the active parameter and highlights for special chars.

        Special chars depend on the language.
        """
        active_parameter_template = (
            '<span style=\'font-family:"{font_family}";'
            'font-size:{font_size}pt;'
            'color:{color}\'>'
            '<b>{parameter}</b>'
            '</span>'
        )
        chars_template = (
            '<span style="color:{0};'.format(self._CHAR_HIGHLIGHT_COLOR) +
            'font-weight:bold">{char}'
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
            if parameter:
                # '*' has a meaning in regex so needs to be escaped
                if '*' in parameter:
                    parameter = parameter.replace('*', '\\*')
                pattern = r'[\*|(|\s](' + parameter + r')[,|)|\s|=]'

            formatted_lines = []
            name = signature.split('(')[0]
            indent = ' ' * (len(name) + 1)
            rows = textwrap.wrap(signature, width=60, subsequent_indent=indent)
            for row in rows:
                if parameter:
                    # Add template to highlight the active parameter
                    row = re.sub(pattern, handle_sub, row)

                row = row.replace(' ', '&nbsp;')
                row = row.replace('span&nbsp;', 'span ')

                language = getattr(self, 'language', language)
                if language and 'python' == language.lower():
                    for char in ['(', ')', ',', '*', '**']:
                        new_char = chars_template.format(char=char)
                        row = row.replace(char, new_char)

                formatted_lines.append(row)
            title_template = '<br>'.join(formatted_lines)

            # Get current font properties
            font = self.font()
            font_size = font.pointSize()
            font_family = font.family()

            # Format title to display active parameter
            if parameter:
                title = title_template.format(
                    font_size=font_size,
                    font_family=font_family,
                    color=parameter_color,
                    parameter=parameter,
                )
            else:
                title = title_template
            new_signatures.append(title)

        return '<br><br>'.join(new_signatures)

    def _check_signature_and_format(self, signature_or_text, parameter=None,
                                    language=_DEFAULT_LANGUAGE):
        """
        LSP hints might provide docstrings instead of signatures.

        This method will check for multiple signatures (dict, type etc...) and
        format the text accordingly.
        """
        open_func_char = ''
        has_signature = False
        has_multisignature = False
        language = getattr(self, 'language', language).lower()
        signature_or_text = signature_or_text.replace('\\*', '*')

        # Remove special symbols that could itefere with ''.format
        signature_or_text = signature_or_text.replace('{', '&#123;')
        signature_or_text = signature_or_text.replace('}', '&#125;')

        lines = signature_or_text.split('\n')
        inspect_word = None

        if language == 'python':
            open_func_char = '('
            idx = signature_or_text.find(open_func_char)
            inspect_word = signature_or_text[:idx]
            name_plus_char = inspect_word + open_func_char

            # Signature type
            count = signature_or_text.count(name_plus_char)
            has_signature = open_func_char in lines[0]
            if len(lines) > 1:
                has_multisignature = count > 1 and name_plus_char in lines[1]
            else:
                has_multisignature = False

        if has_signature and not has_multisignature:
            for i, line in enumerate(lines):
                if line.strip() == '':
                    break

            if i == 0:
                signature = lines[0]
                extra_text = None
            else:
                signature = '\n'.join(lines[:i])
                extra_text = '\n'.join(lines[i:])

            if signature:
                new_signature = self._format_signature(
                    signatures=signature,
                    parameter=parameter,
                )
        elif has_multisignature:
            signature = signature_or_text.replace(name_plus_char,
                                                  '<br>' + name_plus_char)
            signature = signature[4:]  # Remove the first line break
            signature = signature.replace('\n', ' ')
            signature = signature.replace(r'\\*', '*')
            signature = signature.replace(r'\*', '*')
            signature = signature.replace('<br>', '\n')
            signatures = signature.split('\n')
            signatures = [sig for sig in signatures if sig]  # Remove empty

            new_signature = self._format_signature(
                signatures=signatures,
                parameter=parameter,
            )
            extra_text = None
        else:
            new_signature = None
            extra_text = signature_or_text

        return new_signature, extra_text, inspect_word

    def show_calltip(self, signature, parameter=None, documentation=None,
                     language=_DEFAULT_LANGUAGE, max_lines=10):
        """
        Show calltip.

        Calltips look like tooltips but will not disappear if mouse hovers
        them. They are useful for displaying signature information on methods
        and functions.
        """
        # Find position of calltip
        point = self._calculate_position()

        language = getattr(self, 'language', language).lower()
        if language == 'python':
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
            documentation = documentation.replace(signature + '\n', '')

        # Format
        res = self._check_signature_and_format(signature, parameter,
                                               language=language)
        new_signature, text, inspect_word = res
        text = self._format_text(
            signature=new_signature,
            inspect_word=inspect_word,
            display_link=False,
            text=documentation,
            max_lines=max_lines,
        )

        self._update_stylesheet(self.calltip_widget)

        # Show calltip
        self.calltip_widget.show_tip(point, text, [])
        self.calltip_widget.show()

    def show_tooltip(self, title=None, signature=None, text=None,
                     inspect_word=None, title_color=_DEFAULT_TITLE_COLOR,
                     at_line=None, at_point=None, display_link=False,
                     max_lines=10, cursor=None):
        """Show tooltip."""
        # Find position of calltip
        point = self._calculate_position(
            at_line=at_line,
            at_point=at_point,
        )

        # Format text
        tiptext = self._format_text(
            title=title,
            signature=signature,
            text=text,
            title_color=title_color,
            inspect_word=inspect_word,
            display_link=display_link,
            max_lines=max_lines,
        )

        self._update_stylesheet(self.tooltip_widget)

        # Display tooltip
        self.tooltip_widget.show_tip(point, tiptext, cursor=cursor)

    def show_hint(self, text, inspect_word, at_point):
        """Show code hint and crop text as needed."""
        # Check if signature and format
        res = self._check_signature_and_format(text)
        html_signature, extra_text, _ = res
        point = self.get_word_start_pos(at_point)

        # This is needed to get hover hints
        cursor = self.cursorForPosition(at_point)
        cursor.movePosition(QTextCursor.StartOfWord, QTextCursor.MoveAnchor)
        self._last_hover_cursor = cursor

        self.show_tooltip(signature=html_signature, text=extra_text,
                          at_point=point, inspect_word=inspect_word,
                          display_link=True, max_lines=10, cursor=cursor)

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

    #------EOL characters
    def set_eol_chars(self, text):
        """Set widget end-of-line (EOL) characters from text (analyzes text)"""
        if not is_text_string(text): # testing for QString (PyQt API#1)
            text = to_text_string(text)
        eol_chars = sourcecode.get_eol_chars(text)
        is_document_modified = eol_chars is not None and self.eol_chars is not None
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
        """Same as 'toPlainText', replace '\n'
        by correct end-of-line characters"""
        utext = to_text_string(self.toPlainText())
        lines = utext.splitlines()
        linesep = self.get_line_separator()
        txt = linesep.join(lines)
        if utext.endswith('\n'):
            txt += linesep
        return txt

    #------Positions, coordinates (cursor, EOF, ...)
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


    #------Selection
    def clear_selection(self):
        """Clear current selection"""
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def extend_selection_to_next(self, what='word', direction='left'):
        """
        Extend selection to next *what* ('word' or 'character')
        toward *direction* ('left' or 'right')
        """
        self.__move_cursor_anchor(what, direction, QTextCursor.KeepAnchor)


    #------Text: get, set, ...
    def __select_text(self, position_from, position_to):
        position_from = self.get_position(position_from)
        position_to = self.get_position(position_to)
        cursor = self.textCursor()
        cursor.setPosition(position_from)
        cursor.setPosition(position_to, QTextCursor.KeepAnchor)
        return cursor

    def get_text_line(self, line_nb):
        """Return text line at line number *line_nb*"""
        # Taking into account the case when a file ends in an empty line,
        # since splitlines doesn't return that line as the last element
        # TODO: Make this function more efficient
        try:
            return to_text_string(self.toPlainText()).splitlines()[line_nb]
        except IndexError:
            return self.get_line_separator()

    def get_text(self, position_from, position_to):
        """
        Return text between *position_from* and *position_to*
        Positions may be positions or 'sol', 'eol', 'sof', 'eof' or 'cursor'
        """
        cursor = self.__select_text(position_from, position_to)
        text = to_text_string(cursor.selectedText())
        all_text = position_from == 'sof' and position_to == 'eof'
        if text and not all_text:
            while text.endswith("\n"):
                text = text[:-1]
            while text.endswith(u"\u2029"):
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

    def insert_text(self, text):
        """Insert text at cursor position"""
        if not self.isReadOnly():
            self.textCursor().insertText(text)

    def replace_text(self, position_from, position_to, text):
        cursor = self.__select_text(position_from, position_to)
        cursor.removeSelectedText()
        cursor.insertText(text)

    def remove_text(self, position_from, position_to):
        cursor = self.__select_text(position_from, position_to)
        cursor.removeSelectedText()

    def get_current_word_and_position(self, completion=False):
        """Return current word, i.e. word at cursor position,
            and the start position"""
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
            if not completion:
                if is_space(QTextCursor.NextCharacter):
                    if is_space(QTextCursor.PreviousCharacter):
                        return
                    cursor.movePosition(QTextCursor.WordLeft)
            else:
                def is_special_character(move):
                    curs = self.textCursor()
                    curs.movePosition(move, QTextCursor.KeepAnchor)
                    text_cursor = to_text_string(curs.selectedText()).strip()
                    return len(re.findall(r'([^\d\W]\w*)',
                                          text_cursor, re.UNICODE)) == 0
                if is_space(QTextCursor.PreviousCharacter):
                    return
                if (is_special_character(QTextCursor.NextCharacter)):
                    cursor.movePosition(QTextCursor.WordLeft)

        cursor.select(QTextCursor.WordUnderCursor)
        text = to_text_string(cursor.selectedText())
        # find a valid python variable name
        match = re.findall(r'([^\d\W]\w*)', text, re.UNICODE)
        if match:
            text, startpos = match[0], cursor.selectionStart()
            if completion:
                text = text[:cursor_pos - startpos]
            return text, startpos

    def get_current_word(self, completion=False):
        """Return current word, i.e. word at cursor position"""
        ret = self.get_current_word_and_position(completion)
        if ret is not None:
            return ret[0]

    def get_hover_word(self):
        """Return the last hover word that requested a hover hint."""
        return self._last_hover_word

    def get_current_line(self):
        """Return current line's text"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.BlockUnderCursor)
        return to_text_string(cursor.selectedText())

    def get_current_line_to_cursor(self):
        """Return text from prompt to cursor"""
        return self.get_text(self.current_prompt_pos, 'cursor')

    def get_line_number_at(self, coordinates):
        """Return line number at *coordinates* (QPoint)"""
        cursor = self.cursorForPosition(coordinates)
        return cursor.blockNumber() + 1

    def get_line_at(self, coordinates):
        """Return line at *coordinates* (QPoint)"""
        cursor = self.cursorForPosition(coordinates)
        cursor.select(QTextCursor.BlockUnderCursor)
        return to_text_string(cursor.selectedText()).replace(u'\u2029', '')

    def get_word_at(self, coordinates):
        """Return word at *coordinates* (QPoint)"""
        cursor = self.cursorForPosition(coordinates)
        cursor.select(QTextCursor.WordUnderCursor)
        if self._is_point_inside_word_rect(coordinates):
            word = to_text_string(cursor.selectedText())
        else:
            word = ''

        return word

    def get_block_indentation(self, block_nb):
        """Return line indentation (character number)"""
        text = to_text_string(self.document().findBlockByNumber(block_nb).text())
        text = text.replace("\t", " "*self.tab_stop_width_spaces)
        return len(text)-len(text.lstrip())

    def get_selection_bounds(self):
        """Return selection bounds (block numbers)"""
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        block_start = self.document().findBlock(start)
        block_end = self.document().findBlock(end)
        return sorted([block_start.blockNumber(), block_end.blockNumber()])

    def get_selection_first_block(self):
        """Return the first block of the selection."""
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if start > 0:
            start = start - 1
        return self.document().findBlock(start)


    #------Text selection
    def has_selected_text(self):
        """Returns True if some text is selected"""
        return bool(to_text_string(self.textCursor().selectedText()))

    def get_selected_text(self):
        """
        Return text selected by current text cursor, converted in unicode

        Replace the unicode line separator character \u2029 by
        the line separator characters returned by get_line_separator
        """
        return to_text_string(self.textCursor().selectedText()).replace(u"\u2029",
                                                     self.get_line_separator())

    def remove_selected_text(self):
        """Delete selected text"""
        self.textCursor().removeSelectedText()

    def replace(self, text, pattern=None):
        """Replace selected text by *text*
        If *pattern* is not None, replacing selected text using regular
        expression text substitution"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if pattern is not None:
            seltxt = to_text_string(cursor.selectedText())
        cursor.removeSelectedText()
        if pattern is not None:
            text = re.sub(to_text_string(pattern),
                          to_text_string(text), to_text_string(seltxt))
        cursor.insertText(text)
        cursor.endEditBlock()


    #------Find/replace
    def find_multiline_pattern(self, regexp, cursor, findflag):
        """Reimplement QTextDocument's find method

        Add support for *multiline* regular expressions"""
        pattern = to_text_string(regexp.pattern())
        text = to_text_string(self.toPlainText())
        try:
            regobj = re.compile(pattern)
        except sre_constants.error:
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
            pos1, pos2 = match.span()
            fcursor = self.textCursor()
            fcursor.setPosition(pos1)
            fcursor.setPosition(pos2, QTextCursor.KeepAnchor)
            return fcursor

    def find_text(self, text, changed=True, forward=True, case=False,
                  words=False, regexp=False):
        """Find text"""
        cursor = self.textCursor()
        findflag = QTextDocument.FindFlag()

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

        if QT55_VERSION:
            pattern = QRegularExpression(u"\\b{}\\b".format(text) if words else
                                         text)
            if case:
                pattern.setPatternOptions(
                    QRegularExpression.CaseInsensitiveOption)
        else:
            pattern = QRegExp(u"\\b{}\\b".format(text)
                              if words else text, Qt.CaseSensitive if case else
                              Qt.CaseInsensitive, QRegExp.RegExp2)

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
                return True

        return False

    def is_editor(self):
        """Needs to be overloaded in the codeeditor where it will be True"""
        return False

    def get_number_matches(self, pattern, source_text='', case=False,
                           regexp=False):
        """Get the number of matches for the searched text."""
        pattern = to_text_string(pattern)
        if not pattern:
            return 0

        if not regexp:
            pattern = re.escape(pattern)

        if not source_text:
            source_text = to_text_string(self.toPlainText())

        try:
            if case:
                regobj = re.compile(pattern)
            else:
                regobj = re.compile(pattern, re.IGNORECASE)
        except sre_constants.error:
            return None

        number_matches = 0
        for match in regobj.finditer(source_text):
            number_matches += 1

        return number_matches

    def get_match_number(self, pattern, case=False, regexp=False):
        """Get number of the match for the searched text."""
        position = self.textCursor().position()
        source_text = self.get_text(position_from='sof', position_to=position)
        match_number = self.get_number_matches(pattern,
                                               source_text=source_text,
                                               case=case, regexp=regexp)
        return match_number

    # --- Numpy matrix/array helper / See 'spyder/widgets/arraybuilder.py'
    def enter_array_inline(self):
        """ """
        self._enter_array(True)

    def enter_array_table(self):
        """ """
        self._enter_array(False)

    def _enter_array(self, inline):
        """ """
        offset = self.get_position('cursor') - self.get_position('sol')
        rect = self.cursorRect()
        dlg = NumpyArrayDialog(self, inline, offset)

        # TODO: adapt to font size
        x = rect.left()
        x = x - 14
        y = rect.top() + (rect.bottom() - rect.top())/2
        y = y - dlg.height()/2 - 3

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
                cursor.insertText(text)
                cursor.endEditBlock()


class TracebackLinksMixin(object):
    """ """
    QT_CLASS = None
    go_to_error = None

    def __init__(self):
        self.__cursor_changed = False
        self.setMouseTracking(True)

    #------Mouse events
    def mouseReleaseEvent(self, event):
        """Go to error"""
        self.QT_CLASS.mouseReleaseEvent(self, event)
        text = self.get_line_at(event.pos())
        if get_error_match(text) and not self.has_selected_text():
            if self.go_to_error is not None:
                self.go_to_error.emit(text)

    def mouseMoveEvent(self, event):
        """Show Pointing Hand Cursor on error messages"""
        text = self.get_line_at(event.pos())
        if get_error_match(text):
            if not self.__cursor_changed:
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
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
        self.help = None
        self.help_enabled = False

    def set_help(self, help_plugin):
        """Set Help DockWidget reference"""
        self.help = help_plugin

    def set_help_enabled(self, state):
        self.help_enabled = state

    def inspect_current_object(self):
        text = ''
        text1 = self.get_text('sol', 'cursor')
        tl1 = re.findall(r'([a-zA-Z_]+[0-9a-zA-Z_\.]*)', text1)
        if tl1 and text1.endswith(tl1[-1]):
            text += tl1[-1]
        text2 = self.get_text('cursor', 'eol')
        tl2 = re.findall(r'([0-9a-zA-Z_\.]+[0-9a-zA-Z_\.]*)', text2)
        if tl2 and text2.startswith(tl2[0]):
            text += tl2[0]
        if text:
            self.show_object_info(text, force=True)

    def show_object_info(self, text, call=False, force=False):
        """Show signature calltip and/or docstring in the Help plugin"""
        text = to_text_string(text)

        # Show docstring
        help_enabled = self.help_enabled or force
        if force and self.help is not None:
            self.help.dockwidget.setVisible(True)
            self.help.dockwidget.raise_()
        if help_enabled and (self.help is not None) and \
           (self.help.dockwidget.isVisible()):
            # Help widget exists and is visible
            if hasattr(self, 'get_doc'):
                self.help.set_shell(self)
            else:
                self.help.set_shell(self.parent())
            self.help.set_object_text(text, ignore_unknown=False)
            self.setFocus() # if help was not at top level, raising it to
                            # top will automatically give it focus because of
                            # the visibility_changed signal, so we must give
                            # focus back to shell

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

    append_to_history = None

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
        # See issue 6431
        try:
            encoding.write(text, self.history_filename, mode='ab')
        except EnvironmentError:
            pass
        if self.append_to_history is not None:
            self.append_to_history.emit(self.history_filename, text)


class BrowseHistoryMixin(object):

    def __init__(self):
        self.history = []
        self.histidx = None
        self.hist_wholeline = False

    def clear_line(self):
        """Clear current line (without clearing console prompt)"""
        self.remove_text(self.current_prompt_pos, 'eof')

    def browse_history(self, backward):
        """Browse history"""
        if self.is_cursor_before('eol') and self.hist_wholeline:
            self.hist_wholeline = False
        tocursor = self.get_current_line_to_cursor()
        text, self.histidx = self.find_in_history(tocursor, self.histidx,
                                                  backward)
        if text is not None:
            if self.hist_wholeline:
                self.clear_line()
                self.insert_text(text)
            else:
                cursor_position = self.get_position('cursor')
                # Removing text from cursor to the end of the line
                self.remove_text('cursor', 'eol')
                # Inserting history text
                self.insert_text(text)
                self.set_cursor_position(cursor_position)

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

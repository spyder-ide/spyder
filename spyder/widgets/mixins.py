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
from __future__ import print_function
import os
import os.path as osp
import re
import sre_constants
import sys
import textwrap

# Third party imports
import qdarkstyle
from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QCursor, QTextCursor, QTextDocument
from qtpy.QtWidgets import QApplication
from qtpy import QT_VERSION
from spyder_kernels.utils.dochelpers import (getargspecfromtext, getobj,
                                             getsignaturefromtext)

# Local imports
from spyder.config.gui import is_dark_interface
from spyder.config.manager import CONF
from spyder.py3compat import is_text_string, to_text_string
from spyder.utils import encoding, sourcecode, programs
from spyder.utils import syntaxhighlighters as sh
from spyder.utils.misc import get_error_match
from spyder.widgets.arraybuilder import ArrayBuilderDialog

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
    _DEFAULT_MAX_LINES = 10
    _DEFAULT_MAX_WIDTH = 60
    _DEFAULT_COMPLETION_HINT_MAX_WIDTH = 52
    _DEFAULT_MAX_HINT_LINES = 20
    _DEFAULT_MAX_HINT_WIDTH = 85

    # The following signals are used to indicate text changes on the editor.
    sig_will_insert_text = None
    sig_will_remove_selection = None
    sig_text_was_inserted = None

    _styled_widgets = set()

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
            margin = (self.document().documentMargin() / 2) + 1
            cx = int(at_point.x() - margin)
            cy = int(at_point.y() - margin)
        elif at_line is not None:
            # Showing tooltip at line
            cx = 5
            line = at_line - 1
            cursor = QTextCursor(self.document().findBlockByNumber(line))
            cy = int(self.cursorRect(cursor).top())
        else:
            # Showing tooltip at cursor position
            cx, cy = self.get_coordinates('cursor')
            cx = int(cx)
            cy = int(cy - font.pointSize() / 2)

        # Calculate vertical delta
        # The needed delta changes with font size, so we use a power law
        if sys.platform == 'darwin':
            delta = int((font.pointSize() * 1.20) ** 0.98 + 4.5)
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
        # Update the stylesheet for a given widget at most once
        # because Qt is slow to repeatedly parse & apply CSS
        if id(widget) in self._styled_widgets:
            return
        self._styled_widgets.add(id(widget))

        if is_dark_interface():
            css = qdarkstyle.load_stylesheet(qt_api='')
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
                     max_width=_DEFAULT_MAX_WIDTH, display_link=False,
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
        | Link or shortcut with `inspect_word` |
        ----------------------------------------
        """
        BASE_TEMPLATE = u'''
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
                text = '\n'.join(lines[:max_lines]) + ' ...'
            else:
                text = '\n'.join(lines)

        text = text.replace('\n', '<br>')
        if text_new_line and signature:
            text = '<br>' + text

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
                          max_width=_DEFAULT_MAX_WIDTH,
                          parameter_color=_PARAMETER_HIGHLIGHT_COLOR,
                          char_color=_CHAR_HIGHLIGHT_COLOR,
                          language=_DEFAULT_LANGUAGE):
        """
        Create HTML template for signature.

        This template will include indent after the method name, a highlight
        color for the active parameter and highlights for special chars.

        Special chars depend on the language.
        """
        language = getattr(self, 'language', language).lower()
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
            for row in rows:
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
            font_size = font.pointSize()
            font_family = font.family()

            # Format title to display active parameter
            if parameter and language == 'python':
                title = title_template.format(
                    font_size=font_size,
                    font_family=font_family,
                    color=parameter_color,
                    parameter=parameter,
                )
            else:
                title = title_template
            new_signatures.append(title)

        return '<br>'.join(new_signatures)

    def _check_signature_and_format(self, signature_or_text, parameter=None,
                                    inspect_word=None,
                                    max_width=_DEFAULT_MAX_WIDTH,
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

        # Remove 'ufunc' signature if needed. See spyder-ide/spyder#11821
        lines = [line for line in signature_or_text.split('\n')
                 if 'ufunc' not in line]
        signature_or_text = '\n'.join(lines)

        if language == 'python':
            open_func_char = '('
            has_multisignature = False

            if inspect_word:
                has_signature = signature_or_text.startswith(inspect_word)
            else:
                idx = signature_or_text.find(open_func_char)
                inspect_word = signature_or_text[:idx]
                has_signature = True

            if has_signature:
                name_plus_char = inspect_word + open_func_char

                all_lines = []
                for line in lines:
                    if (line.startswith(name_plus_char)
                            and line.count(name_plus_char) > 1):
                        sublines = line.split(name_plus_char)
                        sublines = [name_plus_char + l for l in sublines]
                        sublines = [l.strip() for l in sublines]
                    else:
                        sublines = [line]

                    all_lines = all_lines + sublines

                lines = all_lines
                count = 0
                for line in lines:
                    if line.startswith(name_plus_char):
                        count += 1

                # Signature type
                has_signature = count == 1
                has_multisignature = count > 1 and len(lines) > 1

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
                    max_width=max_width
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
                max_width=max_width
            )
            extra_text = None
        else:
            new_signature = None
            extra_text = signature_or_text

        return new_signature, extra_text, inspect_word

    def show_calltip(self, signature, parameter=None, documentation=None,
                     language=_DEFAULT_LANGUAGE, max_lines=_DEFAULT_MAX_LINES,
                     max_width=_DEFAULT_MAX_WIDTH, text_new_line=True):
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
        language = getattr(self, 'language', language).lower()
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
                                               language=language,
                                               max_width=max_width)
        new_signature, text, inspect_word = res
        text = self._format_text(
            signature=new_signature,
            inspect_word=inspect_word,
            display_link=False,
            text=documentation,
            max_lines=max_lines,
            max_width=max_width,
            text_new_line=text_new_line
        )

        self._update_stylesheet(self.calltip_widget)

        # Show calltip
        self.calltip_widget.show_tip(point, text, [])
        self.calltip_widget.show()

    def show_tooltip(self, title=None, signature=None, text=None,
                     inspect_word=None, title_color=_DEFAULT_TITLE_COLOR,
                     at_line=None, at_point=None, display_link=False,
                     max_lines=_DEFAULT_MAX_LINES,
                     max_width=_DEFAULT_MAX_WIDTH,
                     cursor=None,
                     with_html_format=False,
                     text_new_line=True,
                     completion_doc=None):
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
            max_width=max_width,
            with_html_format=with_html_format,
            text_new_line=text_new_line
        )

        self._update_stylesheet(self.tooltip_widget)

        # Display tooltip
        self.tooltip_widget.show_tip(point, tiptext, cursor=cursor,
                                     completion_doc=completion_doc)

    def show_hint(self, text, inspect_word, at_point,
                  max_lines=_DEFAULT_MAX_HINT_LINES,
                  max_width=_DEFAULT_MAX_HINT_WIDTH,
                  text_new_line=True, completion_doc=None):
        """Show code hint and crop text as needed."""
        res = self._check_signature_and_format(text, max_width=max_width,
                                               inspect_word=inspect_word)
        html_signature, extra_text, _ = res
        point = self.get_word_start_pos(at_point)

        # Only display hover hint if there is documentation
        if extra_text is not None:
            # This is needed to get hover hints
            cursor = self.cursorForPosition(at_point)
            cursor.movePosition(QTextCursor.StartOfWord,
                                QTextCursor.MoveAnchor)
            self._last_hover_cursor = cursor

            self.show_tooltip(signature=html_signature, text=extra_text,
                              at_point=point, inspect_word=inspect_word,
                              display_link=True, max_lines=max_lines,
                              max_width=max_width, cursor=cursor,
                              text_new_line=text_new_line,
                              completion_doc=completion_doc)

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

    # ----- Required methods for the LSP
    def document_did_change(self, text=None):
        pass

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
            self.document_did_change(text)

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
        block = self.document().findBlockByNumber(line_nb)
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, mode=QTextCursor.KeepAnchor)
        return to_text_string(cursor.selectedText())

    def get_text_region(self, start_line, end_line):
        """Return text lines spanned from *start_line* to *end_line*."""
        start_block = self.document().findBlockByNumber(start_line)
        end_block = self.document().findBlockByNumber(end_line)

        start_cursor = QTextCursor(start_block)
        start_cursor.movePosition(QTextCursor.StartOfBlock)
        end_cursor = QTextCursor(end_block)
        end_cursor.movePosition(QTextCursor.EndOfBlock)
        end_position = end_cursor.position()
        start_cursor.setPosition(end_position, mode=QTextCursor.KeepAnchor)
        return self.get_selected_text(start_cursor)

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

    def insert_text(self, text, will_insert_text=True):
        """Insert text at cursor position"""
        if not self.isReadOnly():
            if will_insert_text and self.sig_will_insert_text is not None:
                self.sig_will_insert_text.emit(text)
            self.textCursor().insertText(text)
            if self.sig_text_was_inserted is not None:
                self.sig_text_was_inserted.emit()
            self.document_did_change()

    def replace_text(self, position_from, position_to, text):
        cursor = self.__select_text(position_from, position_to)
        if self.sig_will_remove_selection is not None:
            start, end = self.get_selection_start_end(cursor)
            self.sig_will_remove_selection.emit(start, end)
        cursor.removeSelectedText()
        if self.sig_will_insert_text is not None:
            self.sig_will_insert_text.emit(text)
        cursor.insertText(text)
        if self.sig_text_was_inserted is not None:
            self.sig_text_was_inserted.emit()
        self.document_did_change()

    def remove_text(self, position_from, position_to):
        cursor = self.__select_text(position_from, position_to)
        if self.sig_will_remove_selection is not None:
            start, end = self.get_selection_start_end(cursor)
            self.sig_will_remove_selection.emit(start, end)
        cursor.removeSelectedText()
        self.document_did_change()

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
        # charaters are left
        cursor.movePosition(QTextCursor.PreviousCharacter)
        while self.get_character(cursor.position()).strip():
            cursor.movePosition(QTextCursor.PreviousCharacter)
            if cursor.atBlockStart():
                break
        cursor_pos_left = cursor.position()

        # Get max position to the right of cursor until space or no more
        # charaters are left
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

    def get_block_indentation(self, block_nb):
        """Return line indentation (character number)."""
        text = to_text_string(self.document().findBlockByNumber(block_nb).text())
        text = text.replace("\t", " "*self.tab_stop_width_spaces)
        return len(text)-len(text.lstrip())

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

    #------Text selection
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
        return to_text_string(cursor.selectedText()).replace(u"\u2029",
                                                     self.get_line_separator())

    def remove_selected_text(self):
        """Delete selected text."""
        self.textCursor().removeSelectedText()
        self.document_did_change()

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
        self.document_did_change()


    #------Find/replace
    def find_multiline_pattern(self, regexp, cursor, findflag):
        """Reimplement QTextDocument's find method.

        Add support for *multiline* regular expressions."""
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
            pos1, pos2 = sh.get_span(match)
            fcursor = self.textCursor()
            fcursor.setPosition(pos1)
            fcursor.setPosition(pos2, QTextCursor.KeepAnchor)
            return fcursor

    def find_text(self, text, changed=True, forward=True, case=False,
                  word=False, regexp=False):
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
            pattern = QRegularExpression(u"\\b{}\\b".format(text) if word else
                                         text)
            if case:
                pattern.setPatternOptions(
                    QRegularExpression.CaseInsensitiveOption)
        else:
            pattern = QRegExp(u"\\b{}\\b".format(text)
                              if word else text, Qt.CaseSensitive if case else
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
        except sre_constants.error:
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

    # --- Array builder helper / See 'spyder/widgets/arraybuilder.py'
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
                self.document_did_change()


class TracebackLinksMixin(object):
    """ """
    QT_CLASS = None

    # This signal emits a parsed error traceback text so we can then
    # request opening the file that traceback comes from in the Editor.
    sig_go_to_error_requested = None

    def __init__(self):
        self.__cursor_changed = False
        self.setMouseTracking(True)

    #------Mouse events
    def mouseReleaseEvent(self, event):
        """Go to error"""
        self.QT_CLASS.mouseReleaseEvent(self, event)
        text = self.get_line_at(event.pos())
        if get_error_match(text) and not self.has_selected_text():
            if self.sig_go_to_error_requested is not None:
                self.sig_go_to_error_requested.emit(text)

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
        # See spyder-ide/spyder#6431.
        try:
            encoding.write(text, self.history_filename, mode='ab')
        except EnvironmentError:
            pass
        if self.append_to_history is not None:
            self.append_to_history.emit(self.history_filename, text)


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

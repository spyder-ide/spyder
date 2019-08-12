# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Console base class"""

import re

from qtconsole.styles import dark_color
from qtpy.QtCore import Signal
from qtpy.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from qtpy.QtWidgets import QApplication

from spyder.config.gui import is_dark_interface
from spyder.plugins.editor.widgets.base import TextEditBaseWidget
from spyder.plugins.console.utils.ansihandler import ANSIEscapeCodeHandler


if is_dark_interface():
    MAIN_BG_COLOR = '#19232D'
    MAIN_DEFAULT_FG_COLOR = '#ffffff'
    MAIN_ERROR_FG_COLOR = '#FF0000'
    MAIN_TB_FG_COLOR = '#2980b9'
    MAIN_PROMPT_FG_COLOR = '#00AA00'
else:
    MAIN_BG_COLOR = 'white'
    MAIN_DEFAULT_FG_COLOR = '#000000'
    MAIN_ERROR_FG_COLOR = '#FF0000'
    MAIN_TB_FG_COLOR = '#0000FF'
    MAIN_PROMPT_FG_COLOR = '#00AA00'


def insert_text_to(cursor, text, fmt):
    """Helper to print text, taking into account backspaces"""
    while True:
        index = text.find(chr(8))  # backspace
        if index == -1:
            break
        cursor.insertText(text[:index], fmt)
        if cursor.positionInBlock() > 0:
            cursor.deletePreviousChar()
        text = text[index+1:]
    cursor.insertText(text, fmt)


class QtANSIEscapeCodeHandler(ANSIEscapeCodeHandler):
    def __init__(self):
        ANSIEscapeCodeHandler.__init__(self)
        self.base_format = None
        self.current_format = None

    def set_color_scheme(self, foreground_color, background_color):
        """Set color scheme (foreground and background)."""
        if dark_color(foreground_color):
            self.default_foreground_color = 30
        else:
            self.default_foreground_color = 37

        if dark_color(background_color):
            self.default_background_color = 47
        else:
            self.default_background_color = 40

    def set_base_format(self, base_format):
        self.base_format = base_format

    def get_format(self):
        return self.current_format

    def set_style(self):
        """
        Set font style with the following attributes:
        'foreground_color', 'background_color', 'italic',
        'bold' and 'underline'
        """
        if self.current_format is None:
            assert self.base_format is not None
            self.current_format = QTextCharFormat(self.base_format)
        # Foreground color
        if self.foreground_color is None:
            qcolor = self.base_format.foreground()
        else:
            cstr = self.ANSI_COLORS[self.foreground_color-30][self.intensity]
            qcolor = QColor(cstr)
        self.current_format.setForeground(qcolor)
        # Background color
        if self.background_color is None:
            qcolor = self.base_format.background()
        else:
            cstr = self.ANSI_COLORS[self.background_color-40][self.intensity]
            qcolor = QColor(cstr)
        self.current_format.setBackground(qcolor)

        font = self.current_format.font()
        # Italic
        if self.italic is None:
            italic = self.base_format.fontItalic()
        else:
            italic = self.italic
        font.setItalic(italic)
        # Bold
        if self.bold is None:
            bold = self.base_format.font().bold()
        else:
            bold = self.bold
        font.setBold(bold)
        # Underline
        if self.underline is None:
            underline = self.base_format.font().underline()
        else:
            underline = self.underline
        font.setUnderline(underline)
        self.current_format.setFont(font)


def inverse_color(color):
    color.setHsv(color.hue(), color.saturation(), 255-color.value())


class ConsoleFontStyle(object):
    def __init__(self, foregroundcolor, backgroundcolor,
                 bold, italic, underline):
        self.foregroundcolor = foregroundcolor
        self.backgroundcolor = backgroundcolor
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.format = None

    def apply_style(self, font, is_default):
        self.format = QTextCharFormat()
        self.format.setFont(font)
        foreground = QColor(self.foregroundcolor)
        self.format.setForeground(foreground)
        background = QColor(self.backgroundcolor)
        self.format.setBackground(background)
        font = self.format.font()
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)
        self.format.setFont(font)


class ConsoleBaseWidget(TextEditBaseWidget):
    """Console base widget"""
    BRACE_MATCHING_SCOPE = ('sol', 'eol')
    COLOR_PATTERN = re.compile(r'\x01?\x1b\[(.*?)m\x02?')
    exception_occurred = Signal(str, bool)
    userListActivated = Signal(int, str)
    completion_widget_activated = Signal(str)

    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)

        # We use an object name to set the right background
        # color when changing interface theme. This seems to
        # be a Qt bug.
        # Fixes spyder-ide/spyder#8072.
        self.setObjectName('console')

        self.setMaximumBlockCount(300)

        # ANSI escape code handler
        self.ansi_handler = QtANSIEscapeCodeHandler()

        # Disable undo/redo (nonsense for a console widget...):
        self.setUndoRedoEnabled(False)

        self.userListActivated.connect(
            lambda user_id, text: self.completion_widget_activated.emit(text))

        background_color = MAIN_BG_COLOR
        default_foreground_color = MAIN_DEFAULT_FG_COLOR
        error_foreground_color = MAIN_ERROR_FG_COLOR
        traceback_foreground_color = MAIN_TB_FG_COLOR
        prompt_foreground_color = MAIN_PROMPT_FG_COLOR

        self.default_style = ConsoleFontStyle(
                            foregroundcolor=default_foreground_color,
                            backgroundcolor=background_color,
                            bold=False, italic=False, underline=False)
        self.error_style = ConsoleFontStyle(
                            foregroundcolor=error_foreground_color,
                            backgroundcolor=background_color,
                            bold=False, italic=False, underline=False)
        self.traceback_link_style = ConsoleFontStyle(
                            foregroundcolor=traceback_foreground_color,
                            backgroundcolor=background_color,
                            bold=True, italic=False, underline=True)
        self.prompt_style = ConsoleFontStyle(
                            foregroundcolor=prompt_foreground_color,
                            backgroundcolor=background_color,
                            bold=True, italic=False, underline=False)
        self.font_styles = (self.default_style, self.error_style,
                            self.traceback_link_style, self.prompt_style)

        self.set_color_scheme(default_foreground_color, background_color)
        self.setMouseTracking(True)

    def set_color_scheme(self, foreground_color, background_color):
        """Set color scheme of the console (foreground and background)."""
        self.ansi_handler.set_color_scheme(foreground_color, background_color)

        background_color = QColor(background_color)
        foreground_color = QColor(foreground_color)

        self.set_palette(background=background_color,
                         foreground=foreground_color)

        self.set_pythonshell_font()

    # ----- Python shell
    def insert_text(self, text):
        """Reimplement TextEditBaseWidget method"""
        # Eventually this maybe should wrap to insert_text_to if
        # backspace-handling is required
        self.textCursor().insertText(text, self.default_style.format)

    def paste(self):
        """Reimplement Qt method"""
        if self.has_selected_text():
            self.remove_selected_text()
        self.insert_text(QApplication.clipboard().text())

    def append_text_to_shell(self, text, error, prompt):
        """
        Append text to Python shell
        In a way, this method overrides the method 'insert_text' when text is
        inserted at the end of the text widget for a Python shell

        Handles error messages and show blue underlined links
        Handles ANSI color sequences
        Handles ANSI FF sequence
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        if '\r' in text:    # replace \r\n with \n
            text = text.replace('\r\n', '\n')
            text = text.replace('\r', '\n')
        while True:
            index = text.find(chr(12))
            if index == -1:
                break
            text = text[index+1:]
            self.clear()
        if error:
            is_traceback = False
            for text in text.splitlines(True):
                if (text.startswith('  File')
                        and not text.startswith('  File "<')):
                    is_traceback = True
                    # Show error links in blue underlined text
                    cursor.insertText('  ', self.default_style.format)
                    cursor.insertText(text[2:],
                                      self.traceback_link_style.format)
                else:
                    # Show error/warning messages in red
                    cursor.insertText(text, self.error_style.format)
                self.exception_occurred.emit(text, is_traceback)
        elif prompt:
            # Show prompt in green
            insert_text_to(cursor, text, self.prompt_style.format)
        else:
            # Show other outputs in black
            last_end = 0
            for match in self.COLOR_PATTERN.finditer(text):
                insert_text_to(cursor, text[last_end:match.start()],
                               self.default_style.format)
                last_end = match.end()
                try:
                    for code in [int(_c) for _c in match.group(1).split(';')]:
                        self.ansi_handler.set_code(code)
                except ValueError:
                    pass
                self.default_style.format = self.ansi_handler.get_format()
            insert_text_to(cursor, text[last_end:], self.default_style.format)
#            # Slower alternative:
#            segments = self.COLOR_PATTERN.split(text)
#            cursor.insertText(segments.pop(0), self.default_style.format)
#            if segments:
#                for ansi_tags, text in zip(segments[::2], segments[1::2]):
#                    for ansi_tag in ansi_tags.split(';'):
#                        self.ansi_handler.set_code(int(ansi_tag))
#                    self.default_style.format = self.ansi_handler.get_format()
#                    cursor.insertText(text, self.default_style.format)
        self.set_cursor_position('eof')
        self.setCurrentCharFormat(self.default_style.format)

    def set_pythonshell_font(self, font=None):
        """Python Shell only"""
        if font is None:
            font = QFont()
        for style in self.font_styles:
            style.apply_style(font=font,
                              is_default=style is self.default_style)
        self.ansi_handler.set_base_format(self.default_style.format)

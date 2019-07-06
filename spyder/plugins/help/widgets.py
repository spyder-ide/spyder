# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Help plugin widgets.
"""

# Standard library imports
import re
import socket

# Third party imports
from qtpy.QtCore import  Signal
from qtpy.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from qtpy.QtGui import QColor
from qtpy.QtWebEngineWidgets import WEBENGINE

# Local imports
from spyder.config.gui import is_dark_interface
from spyder.py3compat import to_text_string
from spyder.widgets.browser import FrameWebView
from spyder.widgets.comboboxes import EditableComboBox
from spyder.widgets.findreplace import FindReplace
from spyder.plugins.editor.widgets import codeeditor

if is_dark_interface():
    MAIN_BG_COLOR = '#19232D'
else:
    MAIN_BG_COLOR = 'white'


class ObjectComboBox(EditableComboBox):
    """
    QComboBox handling object names
    """
    # Signals
    valid = Signal(bool, bool)

    def __init__(self, parent):
        EditableComboBox.__init__(self, parent)
        self.help = parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: '', False: ''}

    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if not self.help.source_is_console():
            return True
        if qstr is None:
            qstr = self.currentText()
        if not re.search(r'^[a-zA-Z0-9_\.]*$', str(qstr), 0):
            return False
        objtxt = to_text_string(qstr)
        shell_is_defined = False
        if self.help.get_option('automatic_import'):
            shell = self.help.internal_shell
            if shell is not None:
                shell_is_defined = shell.is_defined(objtxt, force_import=True)
        if not shell_is_defined:
            shell = self.help.get_shell()
            if shell is not None:
                try:
                    shell_is_defined = shell.is_defined(objtxt)
                except socket.error:
                    shell = self.help.get_shell()
                    try:
                        shell_is_defined = shell.is_defined(objtxt)
                    except socket.error:
                        # Well... too bad!
                        pass
        return shell_is_defined

    def validate_current_text(self):
        self.validate(self.currentText())

    def validate(self, qstr, editing=True):
        """Reimplemented to avoid formatting actions"""
        valid = self.is_valid(qstr)
        if self.hasFocus() and valid is not None:
            if editing and not valid:
                # Combo box text is being modified: invalidate the entry
                self.show_tip(self.tips[valid])
                self.valid.emit(False, False)
            else:
                # A new item has just been selected
                if valid:
                    self.selected()
                    # See spyder-ide/spyder#9542.
                    self.lineEdit().cursorWordForward(False)
                else:
                    self.valid.emit(False, False)


class RichText(QWidget):
    """
    WebView widget with find dialog
    """
    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.webview = FrameWebView(self)
        if WEBENGINE:
            self.webview.web_widget.page().setBackgroundColor(
                QColor(MAIN_BG_COLOR))
        else:
            self.webview.web_widget.setStyleSheet(
                "background:{}".format(MAIN_BG_COLOR))
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.webview.web_widget)
        self.find_widget.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.webview)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

    def set_font(self, font, fixed_font=None):
        """Set font"""
        self.webview.set_font(font, fixed_font=fixed_font)

    def set_html(self, html_text, base_url):
        """Set html text"""
        self.webview.setHtml(html_text, base_url)

    def clear(self):
        self.set_html('', self.webview.url())


class PlainText(QWidget):
    """
    Read-only editor widget with find dialog
    """
    # Signals
    focus_changed = Signal()

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        self.editor = None

        # Read-only editor
        self.editor = codeeditor.CodeEditor(self)
        self.editor.setup_editor(linenumbers=False, language='py',
                                 scrollflagarea=False, edge_line=False)
        self.editor.focus_changed.connect(lambda: self.focus_changed.emit())
        self.editor.setReadOnly(True)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.set_editor(self.editor)
        self.find_widget.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

    def set_font(self, font, color_scheme=None):
        """Set font"""
        self.editor.set_font(font, color_scheme=color_scheme)

    def set_color_scheme(self, color_scheme):
        """Set color scheme"""
        self.editor.set_color_scheme(color_scheme)

    def set_text(self, text, is_code):
        self.editor.set_highlight_current_line(is_code)
        self.editor.set_occurrence_highlighting(is_code)
        if is_code:
            self.editor.set_language('py')
        else:
            self.editor.set_language(None)
        self.editor.set_text(text)
        self.editor.set_cursor_position('sof')

    def clear(self):
        self.editor.clear()


# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Report Error Dialog"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtWidgets import (QApplication, QCheckBox, QDialog, QHBoxLayout,
                            QLabel, QPlainTextEdit, QPushButton, QVBoxLayout)
from qtpy.QtCore import Qt, Signal

# Local Imports
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.utils.qthelpers import restore_keyevent
from spyder.widgets.sourcecode.codeeditor import CodeEditor
from spyder.widgets.mixins import BaseEditMixin, TracebackLinksMixin
from spyder.widgets.sourcecode.base import ConsoleBaseWidget


# Minimum number of characters to introduce in the description field
# before being able to send the report to Github.
MIN_CHARS = 20


class DescriptionWidget(CodeEditor):
    """Widget to enter error description."""

    def __init__(self, parent=None):
        CodeEditor.__init__(self, parent)

        # Editor options
        self.setup_editor(
            language='md',
            color_scheme='Scintilla',
            linenumbers=False,
            scrollflagarea=False,
            wrap=True,
            edge_line=False,
            highlight_current_line=False,
            highlight_current_cell=False,
            occurrence_highlighting=False,
            auto_unindent=False)

        # Set font
        self.set_font(get_font())

        # Header
        self.header = (
            "**What steps will reproduce your problem?**\n\n"
            "<!--- You can use Markdown here --->\n\n")
        self.set_text(self.header)
        self.move_cursor(len(self.header))
        self.header_end_pos = self.get_position('eof')

    def remove_text(self):
        """Remove text."""
        self.truncate_selection(self.header_end_pos)
        self.remove_selected_text()

    def cut(self):
        """Cut text"""
        self.truncate_selection(self.header_end_pos)
        if self.has_selected_text():
            CodeEditor.cut(self)

    def keyPressEvent(self, event):
        """Reimplemented Qt Method to avoid removing the header."""
        event, text, key, ctrl, shift = restore_keyevent(event)
        cursor_position = self.get_position('cursor')

        if cursor_position < self.header_end_pos:
            self.restrict_cursor_position(self.header_end_pos, 'eof')
        elif key == Qt.Key_Delete:
            if self.has_selected_text():
                self.remove_text()
            else:
                self.stdkey_clear()
        elif key == Qt.Key_Backspace:
            if self.has_selected_text():
                self.remove_text()
            elif self.header_end_pos == cursor_position:
                return
            else:
                self.stdkey_backspace()
        elif key == Qt.Key_X and ctrl:
            self.cut()
        else:
            CodeEditor.keyPressEvent(self, event)

    def contextMenuEvent(self, event):
        """Reimplemented Qt Method to not show the context menu."""
        pass


class ShowErrorWidget(TracebackLinksMixin, ConsoleBaseWidget, BaseEditMixin):
    """Widget to show errors as they appear in the Internal console."""
    QT_CLASS = QPlainTextEdit
    go_to_error = Signal(str)

    def __init__(self, parent=None):
        ConsoleBaseWidget.__init__(self, parent)
        BaseEditMixin.__init__(self)
        TracebackLinksMixin.__init__(self)
        self.setReadOnly(True)


class SpyderErrorDialog(QDialog):
    """Custom error dialog for error reporting."""

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Spyder internal error"))
        self.setModal(True)

        # To save the traceback sent to the internal console
        self.error_traceback = ""

        # Dialog main label
        self.main_label = QLabel(
            _("""<b>Spyder has encountered an internal problem</b><hr>
              Please enter below a step-by-step description of 
              your problem (in English). Issue reports without 
              a clear way to reproduce them will be closed.
              <br><br>
              <b>Note</b>: You need a Github account for this.
              """))
        self.main_label.setWordWrap(True)
        self.main_label.setAlignment(Qt.AlignJustify)

        # Field to input the description of the problem
        self.input_description = DescriptionWidget(self)

        # Only allow to submit to Github if we have a long enough description
        self.input_description.textChanged.connect(self._description_changed)

        # Widget to show errors
        self.details = ShowErrorWidget(self)
        self.details.set_pythonshell_font(get_font())
        self.details.hide()

        # Label to show missing chars
        self.initial_chars = len(self.input_description.toPlainText())
        self.chars_label = QLabel(_("Enter at least {} "
                                    "characters".format(MIN_CHARS)))

        # Checkbox to dismiss future errors
        self.dismiss_box = QCheckBox()
        self.dismiss_box.setText(_("Don't show again during this session"))

        # Labels layout
        labels_layout = QHBoxLayout()
        labels_layout.addWidget(self.chars_label)
        labels_layout.addWidget(self.dismiss_box, 0, Qt.AlignRight)

        # Dialog buttons
        self.submit_btn = QPushButton(_('Submit to Github'))
        self.submit_btn.setEnabled(False)
        self.submit_btn.clicked.connect(self._submit_to_github)

        self.details_btn = QPushButton(_('Show details'))
        self.details_btn.clicked.connect(self._show_details)

        self.close_btn = QPushButton(_('Close'))

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.submit_btn)
        buttons_layout.addWidget(self.details_btn)
        buttons_layout.addWidget(self.close_btn)

        # Main layout
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.main_label)
        vlayout.addWidget(self.input_description)
        vlayout.addWidget(self.details)
        vlayout.addLayout(labels_layout)
        vlayout.addLayout(buttons_layout)
        self.setLayout(vlayout)

        self.resize(600, 420)
        self.input_description.setFocus()

    def _submit_to_github(self):
        """Action to take when pressing the submit button."""
        main = self.parent().main

        # Getting description and traceback
        description = self.input_description.toPlainText()
        traceback = self.error_traceback[:-1]  # Remove last EOL

        # Render issue
        issue_text = main.render_issue(description=description,
                                       traceback=traceback)

        # Copy issue to clipboard
        QApplication.clipboard().setText(issue_text)

        # Submit issue to Github
        issue_body = ("<!--- "
                      "Please paste the contents of your clipboard "
                      "below to complete reporting your problem. "
                      "--->\n\n")
        main.report_issue(body=issue_body,
                          title="Automatic error report")

    def append_traceback(self, text):
        """Append text to the traceback, to be displayed in details."""
        self.error_traceback += text

    def _show_details(self):
        """Show traceback on its own dialog"""
        if self.details.isVisible():
            self.details.hide()
            self.details_btn.setText(_('Show details'))
        else:
            self.resize(600, 550)
            self.details.document().setPlainText('')
            self.details.append_text_to_shell(self.error_traceback,
                                              error=True,
                                              prompt=False)
            self.details.show()
            self.details_btn.setText(_('Hide details'))

    def _description_changed(self):
        """Activate submit_btn if we have a long enough description."""
        chars = len(self.input_description.toPlainText()) - self.initial_chars
        if chars < MIN_CHARS:
            self.chars_label.setText(
                u"{} {}".format(MIN_CHARS - chars,
                                _("more characters to go...")))
        else:
            self.chars_label.setText(_("Ready to submit! Thanks!"))
        self.submit_btn.setEnabled(chars >= MIN_CHARS)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = SpyderErrorDialog()
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

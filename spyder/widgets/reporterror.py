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
from qtpy.QtWidgets import (QApplication, QCheckBox, QDialog, QFormLayout,
                            QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                            QPushButton, QSpacerItem, QVBoxLayout)
from qtpy.QtCore import Qt, Signal

# Local imports
from spyder import __project_url__, __trouble_url__
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.utils.qthelpers import restore_keyevent
from spyder.widgets.sourcecode.codeeditor import CodeEditor
from spyder.widgets.mixins import BaseEditMixin, TracebackLinksMixin
from spyder.widgets.sourcecode.base import ConsoleBaseWidget


# Minimum number of characters to introduce in the title and
#description fields before being able to send the report to Github.
TITLE_MIN_CHARS = 15
DESC_MIN_CHARS = 50


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
            "### What steps will reproduce the problem?\n\n"
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
        self.setWindowTitle(_("Issue reporter"))
        self.setModal(True)

        # To save the traceback sent to the internal console
        self.error_traceback = ""

        # Dialog main label
        self.main_label = QLabel(
            _("""<h3>Spyder has encountered an internal problem!</h3>
              Before reporting it, <i>please</i> consult our comprehensive 
              <b><a href=\"{0!s}\">Troubleshooting Guide</a></b> 
              which should help solve most issues, and search for 
              <b><a href=\"{1!s}\">known bugs</a></b> matching your error 
              message or problem description for a quicker solution.
              """).format(__trouble_url__, __project_url__))
        self.main_label.setOpenExternalLinks(True)
        self.main_label.setWordWrap(True)
        self.main_label.setAlignment(Qt.AlignJustify)
        self.main_label.setStyleSheet('font-size: 12px;')

        # Issue title
        self.title = QLineEdit()
        self.title.textChanged.connect(self._contents_changed)
        self.title_chars_label = QLabel(_("{} more characters "
                                          "to go...").format(TITLE_MIN_CHARS))
        form_layout = QFormLayout()
        red_asterisk = '<font color="Red">*</font>'
        title_label = QLabel(_("<b>Title</b> {}").format(red_asterisk))
        form_layout.setWidget(0, QFormLayout.LabelRole, title_label)
        form_layout.setWidget(0, QFormLayout.FieldRole, self.title)

        # Description
        steps_header = QLabel(
            _("<b>Steps to reproduce</b> {}").format(red_asterisk))
        steps_text = QLabel(_("Please enter below a detailed step-by-step "
                              "description (in English) of what led up to "
                              "the problem. Issue reports without a clear "
                              "way to reproduce them will be closed."))
        steps_text.setWordWrap(True)

        # Field to input the description of the problem
        self.input_description = DescriptionWidget(self)

        # Only allow to submit to Github if we have a long enough description
        self.input_description.textChanged.connect(self._contents_changed)

        # Widget to show errors
        self.details = ShowErrorWidget(self)
        self.details.set_pythonshell_font(get_font())
        self.details.hide()

        # Label to show missing chars
        self.initial_chars = len(self.input_description.toPlainText())
        self.desc_chars_label = QLabel(_("{} more characters "
                                         "to go...").format(DESC_MIN_CHARS))

        # Checkbox to dismiss future errors
        self.dismiss_box = QCheckBox()
        self.dismiss_box.setText(_("Hide all future errors during this session"))

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
        layout = QVBoxLayout()
        layout.addWidget(self.main_label)
        layout.addSpacing(20)
        layout.addLayout(form_layout)
        layout.addWidget(self.title_chars_label)
        layout.addSpacing(12)
        layout.addWidget(steps_header)
        layout.addSpacing(-1)
        layout.addWidget(steps_text)
        layout.addSpacing(1)
        layout.addWidget(self.input_description)
        layout.addWidget(self.details)
        layout.addWidget(self.desc_chars_label)
        layout.addSpacing(15)
        layout.addWidget(self.dismiss_box)
        layout.addSpacing(15)
        layout.addLayout(buttons_layout)
        layout.setContentsMargins(25, 20, 25, 10)
        self.setLayout(layout)

        self.resize(570, 600)
        self.title.setFocus()

    def _submit_to_github(self):
        """Action to take when pressing the submit button."""
        main = self.parent().main

        # Getting description and traceback
        title = self.title.text()
        description = self.input_description.toPlainText()
        traceback = self.error_traceback[:-1]  # Remove last EOL

        # Render issue
        issue_text = main.render_issue(description=description,
                                       traceback=traceback)

        # Copy issue to clipboard
        QApplication.clipboard().setText(issue_text)

        # Submit issue to Github
        main.report_issue(body=issue_text,
                          title=title, dialog=self)

    def append_traceback(self, text):
        """Append text to the traceback, to be displayed in details."""
        self.error_traceback += text

    def _show_details(self):
        """Show traceback on its own dialog"""
        if self.details.isVisible():
            self.details.hide()
            self.details_btn.setText(_('Show details'))
        else:
            self.resize(570, 650)
            self.details.document().setPlainText('')
            self.details.append_text_to_shell(self.error_traceback,
                                              error=True,
                                              prompt=False)
            self.details.show()
            self.details_btn.setText(_('Hide details'))

    def _contents_changed(self):
        """Activate submit_btn."""
        desc_chars = (len(self.input_description.toPlainText()) -
                      self.initial_chars)
        if desc_chars < DESC_MIN_CHARS:
            self.desc_chars_label.setText(
                u"{} {}".format(DESC_MIN_CHARS - desc_chars,
                                _("more characters to go...")))
        else:
            self.desc_chars_label.setText(_("Description complete; thanks!"))

        title_chars = len(self.title.text())
        if title_chars < TITLE_MIN_CHARS:
            self.title_chars_label.setText(
                u"{} {}".format(TITLE_MIN_CHARS - title_chars,
                                _("more characters to go...")))
        else:
            self.title_chars_label.setText(_("Title complete; thanks!"))

        submission_enabled = (desc_chars >= DESC_MIN_CHARS and
                              title_chars >= TITLE_MIN_CHARS)
        self.submit_btn.setEnabled(submission_enabled)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = SpyderErrorDialog()
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Repport Error Dialog"""

# Stdlib imports
import sys

# Third party imports
from qtpy.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
                            QPlainTextEdit, QPushButton, QVBoxLayout)
from qtpy.QtCore import Qt, Signal

# Local Imports
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.widgets.sourcecode.codeeditor import CodeEditor
from spyder.widgets.mixins import BaseEditMixin, TracebackLinksMixin
from spyder.widgets.sourcecode.base import ConsoleBaseWidget


class ShowErrorWidget(TracebackLinksMixin, ConsoleBaseWidget, BaseEditMixin):
    """"""
    QT_CLASS = QPlainTextEdit
    go_to_error = Signal(str)

    def __init__(self, parent=None):
        ConsoleBaseWidget.__init__(self, parent)
        BaseEditMixin.__init__(self)
        TracebackLinksMixin.__init__(self)

        self.setReadOnly(True)


class SpyderErrorDlg(QDialog):
    """Custom message box for error reporting"""

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Spyder internal error"))
        self.setModal(True)

        # Dialog main label
        self.main_label = QLabel(
            _("""<b>Spyder has encountered a problem!!</b><hr>
              Please enter below a step-by-step description 
              of your problem (in English). If you fail to 
              do it, you won't be able to send your report.
              <br><br>
              <b>Note</b>: You need a Github account for this.
              """))
        self.main_label.setWordWrap(True)
        self.main_label.setAlignment(Qt.AlignJustify)

        # Field to input the description of the problem
        self.description_header = (
            "**What steps will reproduce your problem?**\n\n"
            "<!--- You can use Markdown here --->\n\n")
        self.input_description = CodeEditor()
        self.input_description.setup_editor(
            language='md',
            color_scheme='IDLE',
            linenumbers=False,
            scrollflagarea=False,
            wrap=True,
            edge_line=False,
            highlight_current_line=False)

        # Set default text for description
        self.input_description.set_text(
            "{0}1. \n2. \n3. ".format(self.description_header))
        self.input_description.move_cursor(len(self.description_header) + 3)

        # Only allow to submit to Github if we have a long enough description
        self.input_description.textChanged.connect(self._description_changed)

        # Widget to show errors
        self.details = ShowErrorWidget(self)
        self.details.set_pythonshell_font(get_font())
        self.details.hide()

        # Dialog buttons
        self.submit_btn = QPushButton(_('Submit to Github'))
        self.submit_btn.setEnabled(False)
        self.submit_btn.clicked.connect(self._submit_to_github)

        self.details_btn = QPushButton(_('Show details'))
        self.details_btn.clicked.connect(self._show_details)

        self.dimiss_btn = QPushButton(_('Dimiss'))

        # Label to show missing chars
        self.initial_chars = len(self.input_description.toPlainText())
        self.chars_label = QLabel(_("Enter at least 15 characters"))

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.submit_btn)
        hlayout.addWidget(self.details_btn)
        hlayout.addWidget(self.dimiss_btn)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.main_label)
        vlayout.addWidget(self.input_description)
        vlayout.addWidget(self.details)
        vlayout.addWidget(self.chars_label)
        vlayout.addLayout(hlayout)
        self.resize(500, 420)

        self.setLayout(vlayout)

        self.error_traceback = ""

    def _submit_to_github(self):
        """Action to take when pressing the submit button."""
        main = self.parent().main

        # Getting description and traceback
        description = self.input_description.toPlainText()
        traceback = self.error_traceback[:-1] # Remove last eol

        # Render issue
        issue_text  = main.render_issue(description=description,
                                        traceback=traceback)

        # Copy issue to clipboard
        QApplication.clipboard().setText(issue_text)

        # Submit issue to Github
        issue_body=("<!--- "
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
            self.resize(500, 550)
            self.details.document().setPlainText('')
            self.details.append_text_to_shell(self.error_traceback,
                                              error=True,
                                              prompt=False)
            self.details.show()
            self.details_btn.setText(_('Hide details'))

    def _description_changed(self):
        """Activate submit_btn if we have a long enough description."""
        chars = len(self.input_description.toPlainText()) - self.initial_chars
        if chars < 15:
            self.chars_label.setText(
                u"{} {}".format(15 - chars, _("more characters to go...")))
        else:
            self.chars_label.setText(_("Ready to submit"))
        self.submit_btn.setEnabled(chars > 15)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = SpyderErrorDlg()
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

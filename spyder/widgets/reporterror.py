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
                            QPushButton, QVBoxLayout)
from qtpy.QtCore import Qt

# Local Imports
from spyder.config.base import _
from spyder.widgets.sourcecode.codeeditor import CodeEditor


class SpyderErrorDlg(QDialog):
    """Custom message box for error reporting"""

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Spyder internal error"))
        self.setModal(True)

        # Dialog main label
        self.label = QLabel(
            _("""<b>Spyder has encountered a problem!!</b><hr>
              Please enter below a step-by-step description 
              of your problem (in English). If you fail to 
              do it, you won't be able to send your report.
              <br><br>
              <b>Note</b>: You need a Github account for this.
              """))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignJustify)

        # Field to input the description of the problem
        self.description_header = (
            "**What steps will reproduce your problem?**\n\n"
            "You can use Markdown here\n\n")
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

        # Dialog buttons
        self.submit_btn = QPushButton(_('Submit to Github'))
        self.submit_btn.setEnabled(False)
        self.submit_btn.clicked.connect(self._press_submit_btn)

        self.details_btn = QPushButton(_('Show details'))
        self.details_btn.clicked.connect(self._show_details)

        self.dimiss_btn = QPushButton(_('Dimiss'))

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.submit_btn)
        hlayout.addWidget(self.details_btn)
        hlayout.addWidget(self.dimiss_btn)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.label)
        vlayout.addWidget(self.input_description)
        vlayout.addLayout(hlayout)
        self.resize(500, 420)

        self.setLayout(vlayout)

        self.error_traceback = ""

    def _press_submit_btn(self):
        main = self.parent().main
        issue_text  = main.render_issue(traceback=self.error_traceback)
        QApplication.clipboard().setText(issue_text)
        main.report_issue(body="", title="Spyder Error Report")
        self.accept()

    def append_traceback(self, text):
        """Append text to the traceback, to be displayed in details."""
        self.error_traceback += text

    def _show_details(self):
        """Show traceback on its own dialog"""
        pass

    def _description_changed(self):
        """Activate submit_btn if we have a long enough description."""
        ini_words = len(self.description_header.split())
        words_in_description = len(self.input_description.toPlainText().split())
        self.submit_btn.setEnabled(words_in_description - ini_words > 10)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = SpyderErrorDlg()
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

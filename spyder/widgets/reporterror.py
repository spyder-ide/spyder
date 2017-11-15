# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Repport Error Dialog"""

# Third party imports
from qtpy.QtWidgets import QMessageBox, QApplication
from qtpy.QtCore import Qt

# Local Imports
from spyder.config.base import _


class SpyderErrorMsgBox(QMessageBox):
    """Custom message box for error reporting"""

    def __init__(self, parent=None):
        QMessageBox.__init__(
            self,
            QMessageBox.Critical,
            _('Error'),
            _("<b>Spyder has encountered a problem.</b><br>"
              "Sorry for the inconvenience."
              "<br><br>"
              "You can automatically submit this error to our Github "
              "issues tracker.<br><br>"
              "<i>Note:</i> You need a Github account for that."),
            QMessageBox.Ok,
            parent=parent)

        self.submit_btn = self.addButton(
            _('Submit to Github'), QMessageBox.YesRole)
        self.submit_btn.pressed.connect(self._press_submit_btn)
        self.dimiss_btn = self.addButton(
            _('Dimiss'), QMessageBox.RejectRole)

        self.setWindowModality(Qt.NonModal)
        self.error_traceback = ""
        self.setDetailedText(' ')

        # open show details (iterate over all buttons and click it)
        for button in self.buttons():
            if self.buttonRole(button) == QMessageBox.ActionRole:
                button.click()
                break
        self.show()

    def _press_submit_btn(self):
        main = self.parent().main
        issue_text  = main.render_issue(traceback=self.error_traceback)
        QApplication.clipboard().setText(issue_text)
        main.report_issue(body="", title="Spyder Error Report")
        self.accept()

    def append_traceback(self, text):
        """Append text to the traceback, to be displayed in show details."""
        self.error_traceback += text
        self.setDetailedText(self.error_traceback)

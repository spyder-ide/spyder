# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Repport Error Dialog"""

# Third party imports
from qtpy.QtWidgets import (QMessageBox, QVBoxLayout, QHBoxLayout, QDialog,
                            QPlainTextEdit, QLabel, QPushButton)
from qtpy.QtCore import Qt, Signal

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
        filldescription = FillDescription()
        filldescription.sig_accepted.connect(self.report_issue)
        if filldescription.exec_():
            self.accept()

    def report_issue(self, description):
        self.parent().main.report_issue(self.error_traceback, description)

    def append_traceback(self, text):
        """Append text to the traceback, to be displayed in show details."""
        self.error_traceback += text
        self.setDetailedText(self.error_traceback)


class FillDescription(QDialog):

    sig_accepted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Error Description"))

        self.label_description = QLabel(
            "What steps will reproduce the problem")
        self.input_description = QPlainTextEdit()
        self.input_description.textChanged.connect(self.text_changed)

        self.ok_button = QPushButton("Ok")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.close)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)

        layout = QVBoxLayout()
        layout.addWidget(self.label_description)
        layout.addWidget(self.input_description)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def text_changed(self):
        words_description = len(self.input_description.toPlainText().split())
        self.ok_button.setEnabled(words_description > 10)

    def accept(self):
        text_description = self.input_description.toPlainText()
        self.sig_accepted.emit(text_description)
        super().accept()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite message boxes."""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.base import _
from spyder.widgets.helperwidgets import MessageCheckBox


class KiteInstallationErrorMessage(MessageCheckBox):
    def __init__(self, parent, err_str, set_option):
        super().__init__(icon=QMessageBox.Critical, parent=parent)
        self.set_option = set_option

        self.setWindowTitle(_("Kite installation error"))
        self.set_checkbox_text(_("Don't show again."))
        self.setStandardButtons(QMessageBox.Ok)
        self.setDefaultButton(QMessageBox.Ok)

        self.set_checked(False)
        self.set_check_visible(True)
        self.setText(err_str)

    def exec_(self):
        super().exec_()
        self.set_option(
            'show_installation_error_message', not self.is_checked())

    @classmethod
    def instance(cls, err_str, set_option):
        def wrapper(parent):
            return cls(parent, err_str, set_option)
        return wrapper
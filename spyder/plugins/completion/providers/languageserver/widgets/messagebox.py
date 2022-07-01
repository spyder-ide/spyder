# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Language Server Protocol message boxes."""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.base import _
from spyder.widgets.helperwidgets import MessageCheckBox


class ServerDisabledMessageBox(MessageCheckBox):
    sig_restart_spyder = Signal()

    def __init__(self, parent, warn_str, set_conf):
        super().__init__(icon=QMessageBox.Warning, parent=parent)
        self.set_conf = set_conf

        self.setWindowTitle(_("Warning"))
        self.set_checkbox_text(_("Don't show again"))
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setDefaultButton(QMessageBox.No)
        self.set_checked(False)
        self.set_check_visible(True)
        self.setText(warn_str)

    def exec_(self):
        answer = super().exec_()
        self.set_conf('show_lsp_down_warning', not self.is_checked())
        if answer == QMessageBox.Yes:
            self.sig_restart_spyder.emit()

    @classmethod
    def instance(cls, warn_str, set_conf):
        def wrapper(parent):
            return cls(parent, warn_str, set_conf)
        return wrapper

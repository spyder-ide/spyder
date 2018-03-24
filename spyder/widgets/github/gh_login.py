# -*- coding: utf-8 -*-
# Copyright © QCrash - Colin Duquesnoy
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module contains the github login dialog.

Taken from the QCrash Project - Colin Duquesnoy
https://github.com/ColinDuquesnoy/QCrash
"""

import sys

from qtpy.QtCore import QEvent, Qt, QSize
from qtpy.QtWidgets import (QDialog, QFormLayout, QLabel, QLineEdit,
                            QPushButton, QVBoxLayout)

from spyder.config.base import _
from spyder.config.base import get_image_path

GH_MARK_NORMAL = get_image_path('GitHub-Mark.png')
GH_MARK_LIGHT = get_image_path('GitHub-Mark-Light.png')


class DlgGitHubLogin(QDialog):
    """Dialog to submit error reports to Github."""

    def __init__(self, parent, username):
        super(DlgGitHubLogin, self).__init__(parent)

        title = _("Sign in to Github")
        self.resize(366, 248)
        self.setWindowTitle(title)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Header
        html = ('<html><head/><body><p align="center"><img src="{mark}"/></p>'
                '<p align="center">{title}</p></body></html>')
        mark = GH_MARK_NORMAL
        if self.palette().base().color().lightness() < 128:
            mark = GH_MARK_LIGHT
        lbl_html = QLabel(html.format(mark=mark, title=title))

        # User and password
        form_layout = QFormLayout()
        form_layout.setContentsMargins(-1, 0, -1, -1)

        lbl_user = QLabel(_("Username:"))
        form_layout.setWidget(0, QFormLayout.LabelRole, lbl_user)
        self.le_user = QLineEdit()
        self.le_user.textChanged.connect(self.update_btn_state)
        form_layout.setWidget(0, QFormLayout.FieldRole, self.le_user)

        lbl_password = QLabel(_("Password: "))
        form_layout.setWidget(1, QFormLayout.LabelRole, lbl_password)
        self.le_password = QLineEdit()
        self.le_password.setEchoMode(QLineEdit.Password)
        self.le_password.textChanged.connect(self.update_btn_state)
        form_layout.setWidget(1, QFormLayout.FieldRole, self.le_password)

        # Sign in button
        self.bt_sign_in = QPushButton(_("Sign in"))
        self.bt_sign_in.clicked.connect(self.accept)
        self.bt_sign_in.setDisabled(True)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(lbl_html)
        layout.addLayout(form_layout)
        layout.addWidget(self.bt_sign_in)
        self.setLayout(layout)

        # Final adjustments
        if username:
            self.le_user.setText(username)
            self.le_password.setFocus()
        else:
            self.le_user.setFocus()

        self.setFixedSize(self.width(), self.height())
        self.le_password.installEventFilter(self)
        self.le_user.installEventFilter(self)

    def eventFilter(self, obj, event):
        interesting_objects = [self.le_password, self.le_user]
        if obj in interesting_objects and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return and
                    event.modifiers() & Qt.ControlModifier and
                    self.bt_sign_in.isEnabled()):
                self.accept()
                return True
        return False

    def update_btn_state(self):
        enable = str(self.le_user.text()).strip() != ''
        enable &= str(self.le_password.text()).strip() != ''
        self.bt_sign_in.setEnabled(enable)

    @classmethod
    def login(cls, parent, username):
        dlg = DlgGitHubLogin(parent, username)
        if dlg.exec_() == dlg.Accepted:
            return dlg.le_user.text(), dlg.le_password.text()
        return None, None


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = DlgGitHubLogin(None, None)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

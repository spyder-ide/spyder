# -*- coding: utf-8 -*-
# Copyright © QCrash - Colin Duquesnoy
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
This module contains the github login dialog.

Took from the QCrash Project - Colin Duquesnoy
https://github.com/ColinDuquesnoy/QCrash
"""

import sys

from qtpy.QtCore import Qt, QEvent
from qtpy.QtWidgets import QDialog

from spyder.config.base import _
from spyder.widgets.github import dlg_github_login_ui
from spyder.config.base import get_image_path

GH_MARK_NORMAL = get_image_path('GitHub-Mark.png')
GH_MARK_LIGHT = get_image_path('GitHub-Mark-Light.png')


class DlgGitHubLogin(QDialog):
    HTML = '<html><head/><body><p align="center"><img src="%s"/></p>' \
        '<p align="center">'+_('Sign in to GitHub')+'</p></body></html>'

    def __init__(self, parent, username):
        super(DlgGitHubLogin, self).__init__(parent)
        self.ui = dlg_github_login_ui.Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        mark = GH_MARK_NORMAL
        if self.palette().base().color().lightness() < 128:
            mark = GH_MARK_LIGHT
        html = self.HTML % mark
        self.ui.lbl_html.setText(html)
        self.ui.bt_sign_in.clicked.connect(self.accept)
        self.ui.le_username.textChanged.connect(self.update_btn_state)
        self.ui.le_password.textChanged.connect(self.update_btn_state)
        self.ui.bt_sign_in.setDisabled(True)
        self.ui.le_username.setText(username)
        if username:
            self.ui.le_password.setFocus()
        else:
            self.ui.le_username.setFocus()
        self.adjustSize()
        self.setFixedSize(self.width(), self.height())
        self.ui.le_password.installEventFilter(self)
        self.ui.le_username.installEventFilter(self)

    def eventFilter(self, obj, event):
        interesting_objects = [self.ui.le_password, self.ui.le_username]
        if obj in interesting_objects and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return and
                    event.modifiers() & Qt.ControlModifier and
                    self.ui.bt_sign_in.isEnabled()):
                self.accept()
                return True
        return False

    def update_btn_state(self):
        enable = str(self.ui.le_username.text()).strip() != ''
        enable &= str(self.ui.le_password.text()).strip() != ''
        self.ui.bt_sign_in.setEnabled(enable)

    @classmethod
    def login(cls, parent, username):
        dlg = DlgGitHubLogin(parent, username)
        if dlg.exec_() == dlg.Accepted:
            return dlg.ui.le_username.text(), dlg.ui.le_password.text()
        return None, None


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg = DlgGitHubLogin(None, None)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

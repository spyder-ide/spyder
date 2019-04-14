# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Colin Duquesnoy (QCrash project)
# Copyright (c) 2018- Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt in this directory for details)
# -----------------------------------------------------------------------------

"""
Login dialog to authenticate on Github.

Adapted from qcrash/_dialogs/gh_login.py of the
`QCrash Project <https://github.com/ColinDuquesnoy/QCrash>`_.
"""

import sys

from qtpy.QtCore import QEvent, Qt
from qtpy.QtWidgets import (QCheckBox, QDialog, QFormLayout, QLabel, QLineEdit,
                            QPushButton, QSizePolicy, QSpacerItem, QTabWidget,
                            QVBoxLayout, QWidget)

from spyder.config.base import _
from spyder.py3compat import PY2, to_text_string


TOKEN_URL = "https://github.com/settings/tokens/new?scopes=public_repo"


class DlgGitHubLogin(QDialog):
    """Dialog to submit error reports to Github."""

    def __init__(self, parent, username, password, token, remember=False,
                 remember_token=False):
        QDialog.__init__(self, parent)

        title = _("Sign in to Github")
        self.resize(415, 375)
        self.setWindowTitle(title)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Header
        html = ('<html><head/><body><p align="center">'
                '{title}</p></body></html>')
        lbl_html = QLabel(html.format(title=title))
        lbl_html.setStyleSheet('font-size: 16px;')

        # Tabs
        self.tabs = QTabWidget()

        # Basic form layout
        basic_form_layout = QFormLayout()
        basic_form_layout.setContentsMargins(-1, 0, -1, -1)

        basic_lbl_msg = QLabel(_("For regular users, i.e. users <b>without</b>"
                                 " two-factor authentication enabled"))
        basic_lbl_msg.setWordWrap(True)
        basic_lbl_msg.setAlignment(Qt.AlignJustify)

        lbl_user = QLabel(_("Username:"))
        basic_form_layout.setWidget(0, QFormLayout.LabelRole, lbl_user)
        self.le_user = QLineEdit()
        self.le_user.textChanged.connect(self.update_btn_state)
        basic_form_layout.setWidget(0, QFormLayout.FieldRole, self.le_user)
        basic_form_layout.addRow("", QWidget())

        lbl_password = QLabel(_("Password: "))
        basic_form_layout.setWidget(2, QFormLayout.LabelRole, lbl_password)
        self.le_password = QLineEdit()
        self.le_password.setEchoMode(QLineEdit.Password)
        self.le_password.textChanged.connect(self.update_btn_state)
        basic_form_layout.setWidget(2, QFormLayout.FieldRole, self.le_password)

        self.cb_remember = None
        # Check if we are not in Python 2 and Linux because
        # there's no keyring backend there
        valid_py_os = not (PY2 and sys.platform.startswith('linux'))
        if self.is_keyring_available() and valid_py_os:
            self.cb_remember = QCheckBox(_("Remember me"))
            self.cb_remember.setToolTip(_("Spyder will save your credentials "
                                          "safely"))
            self.cb_remember.setChecked(remember)
            basic_form_layout.setWidget(4, QFormLayout.FieldRole,
                                        self.cb_remember)

        # Basic auth tab
        basic_auth = QWidget()
        basic_layout = QVBoxLayout()
        basic_layout.addSpacerItem(QSpacerItem(QSpacerItem(0, 8)))
        basic_layout.addWidget(basic_lbl_msg)
        basic_layout.addSpacerItem(
            QSpacerItem(QSpacerItem(0, 50, vPolicy=QSizePolicy.Expanding)))
        basic_layout.addLayout(basic_form_layout)
        basic_layout.addSpacerItem(
            QSpacerItem(QSpacerItem(0, 50, vPolicy=QSizePolicy.Expanding)))
        basic_auth.setLayout(basic_layout)
        self.tabs.addTab(basic_auth, _("Password Only"))

        # Token form layout
        token_form_layout = QFormLayout()
        token_form_layout.setContentsMargins(-1, 0, -1, -1)

        token_lbl_msg = QLabel(_("For users <b>with</b> two-factor "
                                 "authentication enabled, or who prefer a "
                                 "per-app token authentication.<br><br>"
                                 "You can go <b><a href=\"{}\">here</a></b> "
                                 "and click \"Generate token\" at the bottom "
                                 "to create a new token to use for this, with "
                                 "the appropriate permissions.").format(
                                                                    TOKEN_URL))
        token_lbl_msg.setOpenExternalLinks(True)
        token_lbl_msg.setWordWrap(True)
        token_lbl_msg.setAlignment(Qt.AlignJustify)

        lbl_token = QLabel("Token: ")
        token_form_layout.setWidget(1, QFormLayout.LabelRole, lbl_token)
        self.le_token = QLineEdit()
        self.le_token.setEchoMode(QLineEdit.Password)
        self.le_token.textChanged.connect(self.update_btn_state)
        token_form_layout.setWidget(1, QFormLayout.FieldRole, self.le_token)

        self.cb_remember_token = None
        # Same validation as with cb_remember
        if self.is_keyring_available() and valid_py_os:
            self.cb_remember_token = QCheckBox(_("Remember token"))
            self.cb_remember_token.setToolTip(_("Spyder will save your "
                                                "token safely"))
            self.cb_remember_token.setChecked(remember_token)
            token_form_layout.setWidget(3, QFormLayout.FieldRole,
                                        self.cb_remember_token)

        # Token auth tab
        token_auth = QWidget()
        token_layout = QVBoxLayout()
        token_layout.addSpacerItem(QSpacerItem(QSpacerItem(0, 8)))
        token_layout.addWidget(token_lbl_msg)
        token_layout.addSpacerItem(
            QSpacerItem(QSpacerItem(0, 50, vPolicy=QSizePolicy.Expanding)))
        token_layout.addLayout(token_form_layout)
        token_layout.addSpacerItem(
            QSpacerItem(QSpacerItem(0, 50, vPolicy=QSizePolicy.Expanding)))
        token_auth.setLayout(token_layout)
        self.tabs.addTab(token_auth, _("Access Token"))

        # Sign in button
        self.bt_sign_in = QPushButton(_("Sign in"))
        self.bt_sign_in.clicked.connect(self.accept)
        self.bt_sign_in.setDisabled(True)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(lbl_html)
        layout.addWidget(self.tabs)
        layout.addWidget(self.bt_sign_in)
        self.setLayout(layout)

        # Final adjustments
        if username and password:
            self.le_user.setText(username)
            self.le_password.setText(password)
            self.bt_sign_in.setFocus()
        elif username:
            self.le_user.setText(username)
            self.le_password.setFocus()
        elif token:
            self.le_token.setText(token)
        else:
            self.le_user.setFocus()

        self.setFixedSize(self.width(), self.height())
        self.le_password.installEventFilter(self)
        self.le_user.installEventFilter(self)
        self.tabs.currentChanged.connect(self.update_btn_state)

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
        user = to_text_string(self.le_user.text()).strip() != ''
        password = to_text_string(self.le_password.text()).strip() != ''
        token = to_text_string(self.le_token.text()).strip() != ''
        enable = ((user and password and
                  self.tabs.currentIndex() == 0) or
                  (token and self.tabs.currentIndex() == 1))
        self.bt_sign_in.setEnabled(enable)

    def is_keyring_available(self):
        """Check if keyring is available for password storage."""
        try:
            import keyring  # analysis:ignore
            return True
        except Exception:
            return False

    @classmethod
    def login(cls, parent, username, password, token,
              remember, remember_token):
        dlg = DlgGitHubLogin(parent, username, password, token, remember,
                             remember_token)
        if dlg.exec_() == dlg.Accepted:
            user = dlg.le_user.text()
            password = dlg.le_password.text()
            token = dlg.le_token.text()
            if dlg.cb_remember:
                remember = dlg.cb_remember.isChecked()
            else:
                remember = False
            if dlg.cb_remember_token:
                remember_token = dlg.cb_remember_token.isChecked()
            else:
                remember_token = False

            credentials = dict(username=user,
                               password=password,
                               token=token,
                               remember=remember,
                               remember_token=remember_token)
            return credentials

        return dict(username=None,
                    password=None,
                    token=None,
                    remember=False,
                    remember_token=False)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()  # analysis:ignore
    dlg = DlgGitHubLogin(None, None, None, None)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

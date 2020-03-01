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

    def __init__(self, parent, token, remember_token=False):
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
        # Check if we are not in Python 2 and Linux because
        # there's no keyring backend there
        valid_py_os = not (PY2 and sys.platform.startswith('linux'))
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
        if token:
            self.le_token.setText(token)
        else:
            self.le_token.setFocus()

        self.setFixedSize(self.width(), self.height())

    def eventFilter(self, obj, event):
        interesting_objects = [self.le_token]
        if obj in interesting_objects and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return and
                    event.modifiers() & Qt.ControlModifier and
                    self.bt_sign_in.isEnabled()):
                self.accept()
                return True
        return False

    def update_btn_state(self):
        token = to_text_string(self.le_token.text()).strip() != ''
        self.bt_sign_in.setEnabled(token)

    def is_keyring_available(self):
        """Check if keyring is available for password storage."""
        try:
            import keyring  # analysis:ignore
            return True
        except Exception:
            return False

    @classmethod
    def login(cls, parent, token, remember_token):
        dlg = DlgGitHubLogin(parent, token, remember_token)
        if dlg.exec_() == dlg.Accepted:
            token = dlg.le_token.text()
            if dlg.cb_remember_token:
                remember_token = dlg.cb_remember_token.isChecked()
            else:
                remember_token = False

            credentials = dict(token=token,
                               remember_token=remember_token)
            return credentials

        return dict(token=None,
                    remember_token=False)


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()  # analysis:ignore
    dlg = DlgGitHubLogin(None, None)
    dlg.show()
    sys.exit(dlg.exec_())


if __name__ == "__main__":
    test()

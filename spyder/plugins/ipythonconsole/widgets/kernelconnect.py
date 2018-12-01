# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
External Kernel connection widget
"""

# Standard library imports
import os.path as osp

# Third party imports
from jupyter_core.paths import jupyter_runtime_dir
from qtpy.compat import getopenfilename
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGridLayout,
                            QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                            QPushButton, QRadioButton, QSpacerItem,
                            QVBoxLayout)

# Local imports
from spyder.config.base import _, get_home_dir
from spyder.config.main import CONF


class KernelConnectionDialog(QDialog):
    """Dialog to connect to existing kernels (either local or remote)."""

    def __init__(self, parent=None):
        super(KernelConnectionDialog, self).__init__(parent)
        self.setWindowTitle(_('Connect to an existing kernel'))

        main_label = QLabel(_(
            "<p>Please select the JSON connection file (<i>e.g.</i> "
            "<tt>kernel-1234.json</tt>) of the existing kernel, and enter "
            "the SSH information if connecting to a remote machine. "
            "To learn more about starting external kernels and connecting "
            "to them, see <a href=\"https://docs.spyder-ide.org/"
            "ipythonconsole.html#connect-to-an-external-kernel\">"
            "our documentation</a>.</p>"))
        main_label.setWordWrap(True)
        main_label.setAlignment(Qt.AlignJustify)
        main_label.setOpenExternalLinks(True)

        # Connection file
        cf_label = QLabel(_('Connection file:'))
        self.cf = QLineEdit()
        self.cf.setPlaceholderText(_('Kernel connection file path'))
        self.cf.setMinimumWidth(350)
        cf_open_btn = QPushButton(_('Browse'))
        cf_open_btn.clicked.connect(self.select_connection_file)

        cf_layout = QHBoxLayout()
        cf_layout.addWidget(cf_label)
        cf_layout.addWidget(self.cf)
        cf_layout.addWidget(cf_open_btn)

        # Remote kernel groupbox
        self.rm_group = QGroupBox(_("This is a remote kernel (via SSH)"))

        # SSH connection
        hn_label = QLabel(_('Hostname:'))
        self.hn = QLineEdit()
        pn_label = QLabel(_('Port:'))
        self.pn = QLineEdit()
        self.pn.setMaximumWidth(75)

        un_label = QLabel(_('Username:'))
        self.un = QLineEdit()

        # SSH authentication
        auth_group = QGroupBox(_("Authentication method:"))
        self.pw_radio = QRadioButton()
        pw_label = QLabel(_('Password:'))
        self.kf_radio = QRadioButton()
        kf_label = QLabel(_('SSH keyfile:'))

        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw_radio.toggled.connect(self.pw.setEnabled)
        self.kf_radio.toggled.connect(self.pw.setDisabled)

        self.kf = QLineEdit()
        kf_open_btn = QPushButton(_('Browse'))
        kf_open_btn.clicked.connect(self.select_ssh_key)
        kf_layout = QHBoxLayout()
        kf_layout.addWidget(self.kf)
        kf_layout.addWidget(kf_open_btn)

        kfp_label = QLabel(_('Passphase:'))
        self.kfp = QLineEdit()
        self.kfp.setPlaceholderText(_('Optional'))
        self.kfp.setEchoMode(QLineEdit.Password)

        self.kf_radio.toggled.connect(self.kf.setEnabled)
        self.kf_radio.toggled.connect(self.kfp.setEnabled)
        self.kf_radio.toggled.connect(kf_open_btn.setEnabled)
        self.kf_radio.toggled.connect(kfp_label.setEnabled)
        self.pw_radio.toggled.connect(self.kf.setDisabled)
        self.pw_radio.toggled.connect(self.kfp.setDisabled)
        self.pw_radio.toggled.connect(kf_open_btn.setDisabled)
        self.pw_radio.toggled.connect(kfp_label.setDisabled)

        # SSH layout
        ssh_layout = QGridLayout()
        ssh_layout.addWidget(hn_label, 0, 0, 1, 2)
        ssh_layout.addWidget(self.hn, 0, 2)
        ssh_layout.addWidget(pn_label, 0, 3)
        ssh_layout.addWidget(self.pn, 0, 4)
        ssh_layout.addWidget(un_label, 1, 0, 1, 2)
        ssh_layout.addWidget(self.un, 1, 2, 1, 3)

        # SSH authentication layout
        auth_layout = QGridLayout()
        auth_layout.addWidget(self.pw_radio, 1, 0)
        auth_layout.addWidget(pw_label, 1, 1)
        auth_layout.addWidget(self.pw, 1, 2)
        auth_layout.addWidget(self.kf_radio, 2, 0)
        auth_layout.addWidget(kf_label, 2, 1)
        auth_layout.addLayout(kf_layout, 2, 2)
        auth_layout.addWidget(kfp_label, 3, 1)
        auth_layout.addWidget(self.kfp, 3, 2)
        auth_group.setLayout(auth_layout)

        # Remote kernel layout
        rm_layout = QVBoxLayout()
        rm_layout.addLayout(ssh_layout)
        rm_layout.addSpacerItem(QSpacerItem(QSpacerItem(0, 8)))
        rm_layout.addWidget(auth_group)
        self.rm_group.setLayout(rm_layout)
        self.rm_group.setCheckable(True)
        self.rm_group.toggled.connect(self.pw_radio.setChecked)

        # Ok and Cancel buttons
        self.accept_btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        self.accept_btns.accepted.connect(self.save_connection_settings)
        self.accept_btns.accepted.connect(self.accept)
        self.accept_btns.rejected.connect(self.reject)

        # Save connection settings checkbox
        self.save_layout = QCheckBox(self)
        self.save_layout.setText(_("Save connection settings"))

        btns_layout = QHBoxLayout()
        btns_layout.addWidget(self.save_layout)
        btns_layout.addWidget(self.accept_btns)

        # Dialog layout
        layout = QVBoxLayout(self)
        layout.addWidget(main_label)
        layout.addSpacerItem(QSpacerItem(QSpacerItem(0, 8)))
        layout.addLayout(cf_layout)
        layout.addSpacerItem(QSpacerItem(QSpacerItem(0, 12)))
        layout.addWidget(self.rm_group)
        layout.addLayout(btns_layout)

        self.load_connection_settings()

    def load_connection_settings(self):
        """Load the user's previously-saved kernel connection settings."""
        existing_kernel = CONF.get("existing-kernel", "settings", {})

        connection_file_path = existing_kernel.get("json_file_path", "")
        is_remote = existing_kernel.get("is_remote", False)
        username = existing_kernel.get("username", "")
        hostname = existing_kernel.get("hostname", "")
        port = str(existing_kernel.get("port", 22))
        is_ssh_kf = existing_kernel.get("is_ssh_keyfile", False)
        ssh_kf = existing_kernel.get("ssh_key_file_path", "")

        if connection_file_path != "":
            self.cf.setText(connection_file_path)
        if username != "":
            self.un.setText(username)
        if hostname != "":
            self.hn.setText(hostname)
        if ssh_kf != "":
            self.kf.setText(ssh_kf)
        self.rm_group.setChecked(is_remote)
        self.pn.setText(port)
        self.kf_radio.setChecked(is_ssh_kf)
        self.pw_radio.setChecked(not is_ssh_kf)

        try:
            import keyring
            ssh_passphrase = keyring.get_password("spyder_remote_kernel",
                                                  "ssh_key_passphrase")
            ssh_password = keyring.get_password("spyder_remote_kernel",
                                                "ssh_password")
            if ssh_passphrase:
                self.kfp.setText(ssh_passphrase)
            if ssh_password:
                self.pw.setText(ssh_password)
        except Exception:
            pass

    def save_connection_settings(self):
        """Save user's kernel connection settings."""

        if not self.save_layout.isChecked():
            return

        is_ssh_key = bool(self.kf_radio.isChecked())
        connection_settings = {
            "json_file_path": self.cf.text(),
            "is_remote": self.rm_group.isChecked(),
            "username": self.un.text(),
            "hostname": self.hn.text(),
            "port": self.pn.text(),
            "is_ssh_keyfile": is_ssh_key,
            "ssh_key_file_path": self.kf.text()
        }
        CONF.set("existing-kernel", "settings", connection_settings)

        try:
            import keyring
            if is_ssh_key:
                keyring.set_password("spyder_remote_kernel",
                                     "ssh_key_passphrase",
                                     self.kfp.text())
            else:
                keyring.set_password("spyder_remote_kernel",
                                     "ssh_password",
                                     self.pw.text())
        except Exception:
            pass

    def select_connection_file(self):
        cf = getopenfilename(self, _('Select kernel connection file'),
                             jupyter_runtime_dir(), '*.json;;*.*')[0]
        self.cf.setText(cf)

    def select_ssh_key(self):
        kf = getopenfilename(self, _('Select SSH keyfile'),
                             get_home_dir(), '*.pem;;*')[0]
        self.kf.setText(kf)

    @staticmethod
    def get_connection_parameters(parent=None, dialog=None):
        if not dialog:
            dialog = KernelConnectionDialog(parent)
        result = dialog.exec_()
        is_remote = bool(dialog.rm_group.isChecked())
        accepted = result == QDialog.Accepted

        if is_remote:
            def falsy_to_none(arg):
                return arg if arg else None
            if dialog.hn.text() and dialog.un.text():
                port = dialog.pn.text() if dialog.pn.text() else '22'
                hostname = "{0}@{1}:{2}".format(dialog.un.text(),
                                                dialog.hn.text(),
                                                port)
            else:
                hostname = None
            if dialog.pw_radio.isChecked():
                password = falsy_to_none(dialog.pw.text())
                keyfile = None
            elif dialog.kf_radio.isChecked():
                keyfile = falsy_to_none(dialog.kf.text())
                password = falsy_to_none(dialog.kfp.text())
            else:  # imposible?
                keyfile = None
                password = None
            return (dialog.cf.text(), hostname, keyfile, password, accepted)
        else:
            path = dialog.cf.text()
            _dir, filename = osp.dirname(path), osp.basename(path)
            if _dir == '' and not filename.endswith('.json'):
                path = osp.join(jupyter_runtime_dir(), 'kernel-'+path+'.json')
            return (path, None, None, None, accepted)

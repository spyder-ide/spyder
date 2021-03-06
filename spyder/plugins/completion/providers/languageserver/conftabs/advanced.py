# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol advanced configuration tab.
"""

# Standard library imports
import re

# Third party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (QGroupBox, QGridLayout, QLabel, QMessageBox,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _
from spyder.utils.misc import check_connection_port


class AdvancedConfigTab(SpyderPreferencesTab):
    """PyLS advanced configuration tab."""

    TITLE = _('Advanced')

    def __init__(self, parent):
        super().__init__(parent)

        lsp_advanced_group = QGroupBox(_(
            'Python Language Server configuration'))
        advanced_label = QLabel(
            _("<b>Warning</b>: Only modify these values if "
              "you know what you're doing!"))
        advanced_label.setWordWrap(True)
        advanced_label.setAlignment(Qt.AlignJustify)

        # Advanced settings checkbox
        self.advanced_options_check = self.create_checkbox(
            _("Enable advanced settings"), 'advanced/enabled')

        # Advanced options
        self.advanced_module = self.create_lineedit(
            _("Module for the Python language server: "),
            'advanced/module', alignment=Qt.Horizontal,
            word_wrap=False)
        self.advanced_host = self.create_lineedit(
            _("IP Address and port to bind the server to: "),
            'advanced/host', alignment=Qt.Horizontal,
            word_wrap=False)
        self.advanced_port = self.create_spinbox(
            ":", "", 'advanced/port', min_=1, max_=65535, step=1)
        self.external_server = self.create_checkbox(
            _("This is an external server"),
            'advanced/external')
        self.use_stdio = self.create_checkbox(
            _("Use stdio pipes to communicate with server"),
            'advanced/stdio')
        self.use_stdio.stateChanged.connect(self.disable_tcp)
        self.external_server.stateChanged.connect(self.disable_stdio)

        # Advanced layout
        advanced_g_layout = QGridLayout()
        advanced_g_layout.addWidget(self.advanced_module.label, 1, 0)
        advanced_g_layout.addWidget(self.advanced_module.textbox, 1, 1)
        advanced_g_layout.addWidget(self.advanced_host.label, 2, 0)

        advanced_host_port_g_layout = QGridLayout()
        advanced_host_port_g_layout.addWidget(self.advanced_host.textbox, 1, 0)
        advanced_host_port_g_layout.addWidget(self.advanced_port.plabel, 1, 1)
        advanced_host_port_g_layout.addWidget(self.advanced_port.spinbox, 1, 2)
        advanced_g_layout.addLayout(advanced_host_port_g_layout, 2, 1)

        # External server and stdio options layout
        advanced_server_layout = QVBoxLayout()
        advanced_server_layout.addWidget(self.external_server)
        advanced_server_layout.addWidget(self.use_stdio)

        advanced_options_layout = QVBoxLayout()
        advanced_options_layout.addLayout(advanced_g_layout)
        advanced_options_layout.addLayout(advanced_server_layout)

        # Set advanced options enabled/disabled
        advanced_options_widget = QWidget()
        advanced_options_widget.setLayout(advanced_options_layout)
        advanced_options_widget.setEnabled(self.get_option('advanced/enabled'))
        self.advanced_options_check.toggled.connect(
            advanced_options_widget.setEnabled)
        self.advanced_options_check.toggled.connect(
            self.show_advanced_warning)

        # Advanced options layout
        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(advanced_label)
        advanced_layout.addWidget(self.advanced_options_check)
        advanced_layout.addWidget(advanced_options_widget)

        lsp_advanced_group.setLayout(advanced_layout)

        layout = QVBoxLayout()
        layout.addWidget(lsp_advanced_group)
        self.setLayout(layout)

    def disable_tcp(self, state):
        if state == Qt.Checked:
            self.advanced_host.textbox.setEnabled(False)
            self.advanced_port.spinbox.setEnabled(False)
            self.external_server.stateChanged.disconnect()
            self.external_server.setChecked(False)
            self.external_server.setEnabled(False)
        else:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.external_server.setChecked(False)
            self.external_server.setEnabled(True)
            self.external_server.stateChanged.connect(self.disable_stdio)

    def disable_stdio(self, state):
        if state == Qt.Checked:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.advanced_module.textbox.setEnabled(False)
            self.use_stdio.stateChanged.disconnect()
            self.use_stdio.setChecked(False)
            self.use_stdio.setEnabled(False)
        else:
            self.advanced_host.textbox.setEnabled(True)
            self.advanced_port.spinbox.setEnabled(True)
            self.advanced_module.textbox.setEnabled(True)
            self.use_stdio.setChecked(False)
            self.use_stdio.setEnabled(True)
            self.use_stdio.stateChanged.connect(self.disable_tcp)

    @Slot(bool)
    def show_advanced_warning(self, state):
        """
        Show a warning when trying to modify the PyLS advanced
        settings.
        """
        # Don't show warning if the option is already enabled.
        # This avoids showing it when the Preferences dialog
        # is created.
        if self.get_option('advanced/enabled'):
            return

        # Show warning when toggling the button state
        if state:
            QMessageBox.warning(
                self,
                _("Warning"),
                _("<b>Modifying these options can break code completion!!</b>"
                  "<br><br>"
                  "If that's the case, please reset your Spyder preferences "
                  "by going to the menu"
                  "<br><br>"
                  "<tt>Tools > Reset Spyder to factory defaults</tt>"
                  "<br><br>"
                  "instead of reporting a bug."))

    def is_valid(self):
        host = self.advanced_host.textbox.text()

        # If host is not local, the server must be external
        # and we need to automatically check the corresponding
        # option
        if host not in ['127.0.0.1', 'localhost']:
            self.external_server.setChecked(True)

        # Checks for external PyLS
        if self.external_server.isChecked():
            port = int(self.advanced_port.spinbox.text())

            # Check that host and port of the current server are
            # different from the new ones provided to connect to
            # an external server.
            lsp = self.plugin.get_provider('lsp')
            pyclient = lsp.clients.get('python')
            if pyclient is not None:
                instance = pyclient['instance']
                if (instance is not None and
                        not pyclient['config']['external']):
                    if (instance.server_host == host and
                            instance.server_port == port):
                        self.report_no_address_change()
                        return False

            # Check connection to LSP server using a TCP socket
            response = check_connection_port(host, port)
            if not response:
                self.report_no_external_server(host, port, 'python')
                return False

        return True

    def report_no_external_server(self, host, port, language):
        """
        Report that connection couldn't be established with
        an external server.
        """
        QMessageBox.critical(
            self,
            _("Error"),
            _("It appears there is no {language} language server listening "
              "at address:"
              "<br><br>"
              "<tt>{host}:{port}</tt>"
              "<br><br>"
              "Please verify that the provided information is correct "
              "and try again.").format(host=host, port=port,
                                       language=language.capitalize())
        )

    def report_no_address_change(self):
        """
        Report that server address has no changed after checking the
        external server option.
        """
        QMessageBox.critical(
            self,
            _("Error"),
            _("The address of the external server you are trying to connect "
              "to is the same as the one of the current internal server "
              "started by Spyder."
              "<br><br>"
              "Please provide a different address!")
        )

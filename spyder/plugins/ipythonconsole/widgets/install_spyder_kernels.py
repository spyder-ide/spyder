# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget for installing spyder-kernels
"""
# Standard library imports
import logging

# Third-party imports
from qtpy.QtCore import QByteArray, QProcess
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QDialogButtonBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.utils.conda import find_conda, get_conda_channel
from spyder_kernels.utils.pythonenv import is_conda_env, get_conda_env_path
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.config.base import _
from spyder.plugins.ipythonconsole import SPYDER_KERNELS_VERSION

logger = logging.getLogger(__name__)

INSTALL_TEXT = _(
    "<tt>spyder-kernels {}</tt> needs to be installed in the<br>"
    "<tt>{}</tt><br>environment in order to work with Spyder.<br><br>"
    "Do you want Spyder to install it for you?"
)
SHOW_DETAILS = _("Show details")
HIDE_DETAILS = _("Hide details")


class SpyderKernelInstallWidget(QWidget, SpyderWidgetMixin, SpyderFontsMixin):
    CONF_SECTION = "ipython_console"

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        SpyderWidgetMixin.__init__(self, class_parent=parent)

        self.ipyclient = parent

        self.info_page = None

        self.bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.bbox.button(QDialogButtonBox.Ok).setText(SHOW_DETAILS)

        # Process to run the installation scripts
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._update_details)
        self._process.readyReadStandardError.connect(
            lambda: self._update_details(error=True)
        )
        self._process.finished.connect(self._handle_process_finished)

        # Area to show stdout/stderr streams of the process that performs the
        # update
        self._streams_area = QPlainTextEdit(self)
        self._streams_area.setReadOnly(True)
        self._streams_area.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._streams_area.setFont(self.get_font(SpyderFontType.Monospace))
        self._streams_area.hide()

        layout = QVBoxLayout()
        layout.addWidget(self._streams_area)
        layout.addWidget(self.bbox)
        self.setLayout(layout)

        self.bbox.accepted.connect(self.accepted)
        self.bbox.rejected.connect(self.rejected)

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def accepted(self):
        if self._streams_area.isVisible():
            self._hide_details()
        else:
            self._show_details()

    def rejected(self):
        self._process.terminate()
        logger.info("Install spyder-kernels cancelled by user.")
        # Note: QProcess.finished is still emitted

    # ---- Private API
    # -------------------------------------------------------------------------
    def _add_text_to_streams_area(self, text):
        self._streams_area.moveCursor(QTextCursor.End)
        # Note appendPlainText starts new paragraph, so strip \n.
        self._streams_area.appendPlainText(text.strip("\n"))
        self._streams_area.moveCursor(QTextCursor.End)

    def _update_details(self, error=False):
        if error:
            self._process.setReadChannel(QProcess.StandardError)
        else:
            self._process.setReadChannel(QProcess.StandardOutput)

        qba = QByteArray()
        while self._process.bytesAvailable():
            if error:
                qba += self._process.readAllStandardError()
            else:
                qba += self._process.readAllStandardOutput()

        text = str(qba.data(), "utf-8")
        self._add_text_to_streams_area(text)

    def _show_details(self):
        self.ipyclient.infowidget.hide()
        self._streams_area.show()
        self.bbox.button(QDialogButtonBox.Ok).setText(HIDE_DETAILS)

    def _hide_details(self):
        self._streams_area.hide()
        self.ipyclient.infowidget.show()
        self.bbox.button(QDialogButtonBox.Ok).setText(SHOW_DETAILS)

    def _handle_process_finished(self, exit_code, exit_status):
        output = self._streams_area.toPlainText()
        logger.info(
            "Install spyder-kernels QProcess finished. "
            f"Exit code: {exit_code}; exit status: {exit_status}"
        )
        logger.debug(
            "Install spyder-kernels output:\n"
            f"{output}"
        )

        self.ipyclient.process_kernel_install(exit_code, exit_status, output)

    # ---- Public API
    # -------------------------------------------------------------------------
    def install_spyder_kernels(self, pyexec):
        """Install spyder-kernels"""

        if is_conda_env(pyexec=pyexec):
            conda = find_conda()
            env_path = get_conda_env_path(pyexec)
            channel, channel_url = get_conda_channel(pyexec, "python")
            cmd = [
                conda,
                "install",
                "--quiet",
                "--yes",
                "--prefix",
                env_path,
                "-c",
                channel,
                "-c",
                "conda-forge/label/spyder_kernels_rc",
                "-c",
                "conda-forge/label/spyder_kernels_dev",
                "--override-channels",
                f"spyder-kernels{SPYDER_KERNELS_VERSION}",
            ]
        else:
            # Pip environment
            cmd = [
                pyexec,
                "-m",
                "pip",
                "install",
                f"spyder-kernels{SPYDER_KERNELS_VERSION}",
            ]

        logger.info("Installing spyder-kernels...")
        logger.info(f"Command: {' '.join(cmd)}")

        self._process.start(cmd[0], cmd[1:])

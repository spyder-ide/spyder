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
    QLabel,
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
from spyder.plugins.ipythonconsole import (
    SpyderKernelError,
    SpyderKernelVersionError,
    SPYDER_KERNELS_VERSION,
)

logger = logging.getLogger(__name__)

INSTALL_TEXT = _(
    "<tt>spyder-kernels {}</tt> needs to be installed in the<br>"
    "<tt>{}</tt><br>environment in order to work with Spyder.<br><br>"
    "Do you want Spyder to install it for you?"
)


class SpyderKernelInstallWidget(QWidget, SpyderWidgetMixin, SpyderFontsMixin):
    CONF_SECTION = "ipython_console"

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        SpyderWidgetMixin.__init__(self, class_parent=parent)

        self.ipyclient = parent

        self._kernel_error = None

        self.bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        self._text_label = QLabel()
        self._text_label.setWordWrap(True)

        # Process to run the installation scripts
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._update_details)
        self._process.readyReadStandardError.connect(
            lambda: self._update_details(error=True)
        )
        self._process.finished.connect(self._handle_process_finished)
        self._process.errorOccurred.connect(self._handle_error)

        # Area to show stdout/stderr streams of the process that performs the
        # update
        self._streams_area = QPlainTextEdit(self)
        self._streams_area.setMinimumHeight(300)
        self._streams_area.setReadOnly(True)
        self._streams_area.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._streams_area.setFont(self.get_font(SpyderFontType.Monospace))
        self._streams_area.hide()

        layout = QVBoxLayout()
        layout.addWidget(self._text_label)
        layout.addWidget(self._streams_area)
        layout.addWidget(self.bbox)
        self.setLayout(layout)

        self.bbox.accepted.connect(self.accepted)
        self.bbox.rejected.connect(self.rejected)

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def accepted(self):
        self._text_label.hide()
        self.bbox.hide()
        self._streams_area.show()

        # Install spyder kernels...
        self.install_spyder_kernels(self.kernel_error.pyexec)

    def rejected(self):
        # pass through kernel error
        if isinstance(self.kernel_error, SpyderKernelVersionError):
            # Recast to avoid recursion.
            self.kernel_error.__class__ = SpyderKernelError

        self.ipyclient.show_kernel_error(self.kernel_error)

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

    def _handle_process_finished(self, exit_code, exit_status):
        logger.info(
            "Install spyder-kernels QProcess finished. "
            f"Exit code: {exit_code}; exit status: {exit_status}"
        )
        logger.debug(
            "Install spyder-kernels output:\n"
            f"{self._streams_area.toPlainText()}"
        )

        if exit_code != 0:
            return

        self._streams_area.hide()
        self._streams_area.clear()
        self._text_label.show()
        self.bbox.show()

        self.ipyclient.connect_after_kernel_install()

    def _handle_error(self, error):
        if error == QProcess.FailedToStart:
            text = "The process failed to start."
        elif error == QProcess.Crashed:
            text = "The process crashed."
        else:
            text = "Unknown error."

        self._add_text_to_streams_area(text)

    # ---- Public API
    # -------------------------------------------------------------------------
    @property
    def kernel_error(self):
        return self._kernel_error

    @kernel_error.setter
    def kernel_error(self, kernel_error):
        self._kernel_error = kernel_error
        self._text_label.setText(
            INSTALL_TEXT.format(
                SPYDER_KERNELS_VERSION.replace(">", "&gt;").replace(
                    "<", "&lt;"
                ),
                kernel_error.pyexec,
            )
        )

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

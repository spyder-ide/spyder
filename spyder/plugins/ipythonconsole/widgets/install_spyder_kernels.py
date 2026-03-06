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
import re

# Third-party imports
from qtpy.QtCore import QByteArray, QProcess
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
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
    SPYDER_KERNELS_CONDA,
    SPYDER_KERNELS_PIP,
    _d,
)

logger = logging.getLogger(__name__)

INSTALL_TEXT = _(
    "<tt>spyder-kernels {}</tt> needs to be installed in the<br>"
    "<tt>{}</tt><br>environment in order to work with Spyder.<br><br>"
    "Do you want Spyder to install it for you?"
)
PROMPTS = (
    "Confirm changes: [Y/n] ",
    "Proceed ([y]/n)? ",
)

# Use suggested install commands
SPYDER_KERNELS_CONDA = SPYDER_KERNELS_CONDA.replace(_d, "-").split()
SPYDER_KERNELS_PIP = SPYDER_KERNELS_PIP.replace(_d, "-").split()


class InstallSpyderKernelsDialog(
    QDialog,
    SpyderWidgetMixin,
    SpyderFontsMixin
):
    CONF_SECTION = "ipython_console"

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        SpyderWidgetMixin.__init__(self, class_parent=parent)

        self.ipyclient = parent

        if hasattr(parent, "container"):
            self.setWindowTitle(parent.container._plugin.get_name())
        self.text = QLabel(_("Inspecting environment..."))

        # Progress bar
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedHeight(15)
        self._progress_bar.setRange(0, 0)

        # Area to show stdout/stderr streams of the process that performs the
        # update
        self._streams_area = QPlainTextEdit(self)
        self._streams_area.setReadOnly(True)
        self._streams_area.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._streams_area.setFont(self.get_font(SpyderFontType.Monospace))
        self._streams_area.setMinimumSize(600, 400)

        self.bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        self.accept_button = self.bbox.button(QDialogButtonBox.Ok)
        self.accept_button.setText(_("Proceed"))
        self.accept_button.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.text)
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._streams_area)
        layout.addWidget(self.bbox)
        self.setLayout(layout)

        # Process to run the installation scripts
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._update_details)
        self._process.readyReadStandardError.connect(
            lambda: self._update_details(error=True)
        )
        self._process.finished.connect(self._handle_process_finished)

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def accept(self):
        self.accept_button.setEnabled(False)
        self._process.write(b"\n")
        self._progress_bar.show()

    def reject(self):
        logger.info("Install spyder-kernels cancelled by user.")
        super().reject()
        self._process.terminate()
        # Note: QProcess.finished is still emitted

    # ---- Private API
    # -------------------------------------------------------------------------
    def _add_text_to_streams_area(self, text):
        self._streams_area.moveCursor(QTextCursor.End)
        # Note appendPlainText starts new paragraph, so strip \n.
        self._streams_area.appendPlainText(text.strip("\n"))
        self._streams_area.moveCursor(QTextCursor.End)

        if text.endswith(PROMPTS):
            self._progress_bar.hide()
            self.accept_button.setEnabled(True)
            self.text.setText(_(
                "Spyder will make the following changes to "
                "your environment. Do you want to proceed?"
            ))
            self.raise_()

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
            "Exit code: {}; exit status: {}",
            exit_code,
            exit_status,
        )
        logger.debug(f"Install spyder-kernels output:\n{self.output()}")

        if exit_status == QProcess.CrashExit:
            # Cancelled by user
            return
        else:
            # Error or successful install, pass up to client
            super().reject()
            self.ipyclient.process_kernel_install(exit_code, exit_status)

    # ---- Public API
    # -------------------------------------------------------------------------
    def install(self):
        """Install spyder-kernels"""
        pyexec = self.ipyclient._pyexec

        if is_conda_env(pyexec=pyexec):
            exe = find_conda(mamba=True)
            env_path = get_conda_env_path(pyexec)

            channel, channel_url = get_conda_channel(pyexec, "python")

            install_options = ["--prefix", env_path]
            if re.search("conda(.bat|.exe)?$", exe):
                install_options.append("--quiet")
            if channel is not None:
                install_options.extend(["-c", channel])

            cmd = SPYDER_KERNELS_CONDA.copy()
            cmd[0] = exe  # Replace with full path to found mamba

            cmd[2:2] = install_options
        else:
            # Pip environment
            cmd = [pyexec, "-m"] + SPYDER_KERNELS_PIP

        logger.info("Installing spyder-kernels: {' '.join(cmd)} ...")

        self._process.start(cmd[0], cmd[1:])

    def is_running(self):
        return self._process.state() == QProcess.Running

    def output(self):
        return self._streams_area.toPlainText()

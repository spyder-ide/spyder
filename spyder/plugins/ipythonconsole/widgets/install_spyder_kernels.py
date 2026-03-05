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
SHOW_DETAILS = _("Show details")
HIDE_DETAILS = _("Hide details")

# Use suggested install commands
SPYDER_KERNELS_CONDA = SPYDER_KERNELS_CONDA.replace(_d, "-").split()
SPYDER_KERNELS_PIP = SPYDER_KERNELS_PIP.replace(_d, "-").split()


class SpyderKernelInstallBaseWidget(
    QWidget,
    SpyderWidgetMixin,
    SpyderFontsMixin
):
    CONF_SECTION = "ipython_console"

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        SpyderWidgetMixin.__init__(self, class_parent=parent)

        self.ipyclient = parent

        self.text = QLabel()

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

        self.bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

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

    def _install(self, pyexec, dryrun=False):
        """Install spyder-kernels"""

        if is_conda_env(pyexec=pyexec):
            exe = find_conda(mamba=True)
            env_path = get_conda_env_path(pyexec)

            channel, channel_url = get_conda_channel(pyexec, "python")

            install_options = ["--yes", "--prefix", env_path]
            if re.search("conda(.bat|.exe)?$", exe):
                install_options.append("--quiet")
            if dryrun:
                install_options.append("--dry-run")
            if channel is not None:
                install_options.extend(["-c", channel])

            cmd = SPYDER_KERNELS_CONDA.copy()
            cmd[0] = exe  # Replace with full path to found mamba

            cmd[2:2] = install_options
        else:
            # Pip environment
            cmd = [pyexec, "-m"] + SPYDER_KERNELS_PIP
            if dryrun:
                cmd.insert(-1, "--dry-run")

        logger.info(f"Installing spyder-kernels: {' '.join(cmd)} ...")

        self._process.start(cmd[0], cmd[1:])

    # ---- Public API
    # -------------------------------------------------------------------------
    def is_running(self):
        return self._process.state() == QProcess.Running

    def output(self):
        return self._streams_area.toPlainText()


class SpyderKernelInstallWidget(SpyderKernelInstallBaseWidget):

    def __init__(self, parent=None):
        super().__init__(self, parent)

        self.info_page = None

        self.text.hide()
        self._progress_bar.hide()
        self._streams_area.hide()
        self.bbox.button(QDialogButtonBox.Ok).setText(SHOW_DETAILS)

        self._process.finished.connect(self._handle_process_finished)

        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)

        self.setResult(QDialog.Rejected)

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def accept(self):
        if self._streams_area.isVisible():
            self._hide_details()
        else:
            self._show_details()

    def reject(self):
        logger.info("Install spyder-kernels cancelled by user.")
        self._process.terminate()
        # Note: QProcess.finished is still emitted

    # ---- Private API
    # -------------------------------------------------------------------------
    def _show_details(self):
        self.ipyclient.infowidget.hide()
        self._streams_area.show()
        self.bbox.button(QDialogButtonBox.Ok).setText(HIDE_DETAILS)

    def _hide_details(self):
        self._streams_area.hide()
        self.ipyclient.infowidget.show()
        self.bbox.button(QDialogButtonBox.Ok).setText(SHOW_DETAILS)

    def _handle_process_finished(self, exit_code, exit_status):
        output = self.output()
        logger.info(
            "Install spyder-kernels QProcess finished. "
            f"Exit code: {exit_code}; exit status: {exit_status}"
        )
        logger.debug(
            "Install spyder-kernels output:\n"
            f"{output}"
        )

        self.ipyclient.process_kernel_install(exit_code, exit_status)

    # ---- Public API
    # -------------------------------------------------------------------------
    def install(self, pyexec):
        self._install(pyexec, dryrun=False)


class DryRunDialog(QDialog, SpyderKernelInstallBaseWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        if hasattr(parent, "container"):
            self.setWindowTitle(parent.container._plugin.get_name())
        self.text = QLabel(_("Inspecting environment..."))

        self.accept_button = self.bbox.button(QDialogButtonBox.Ok)
        self.accept_button.setText(_("Proceed"))
        self.accept_button.setEnabled(False)

        self._process.finished.connect(self._handle_process_finished)

        self._streams_area.setMinimumSize(600, 400)

        self.bbox.rejected.connect(self.reject)

        # TODO: Set status bar to "Inspecting spyder-kernels..." with spinner

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def reject(self):
        logger.info("Install spyder-kernels dry-run cancelled by user.")
        QDialog.reject(self)
        self._process.terminate()
        # Note: QProcess.finished is still emitted

    # ---- Private API
    # -------------------------------------------------------------------------
    def _handle_process_finished(self, exit_code, exit_status):
        output = self.output()
        logger.info(
            "Install spyder-kernels dry-run QProcess finished. "
            f"Exit code: {exit_code}; exit status: {exit_status}"
        )
        logger.debug(
            "Install spyder-kernels dry-run output:\n"
            f"{output}"
        )

        # TODO: Reset status bar

        if exit_status == QProcess.CrashExit:
            # Cancelled by user
            return

        if exit_code == 0:
            # Success!
            self.text.setText(_(
                "Spyder will make the following changes to "
                "your environment. Do you want to proceed?"
            ))
            self._progress_bar.hide()
            self.accept_button.setEnabled(True)
        else:
            self.ipyclient.show_kernel_error(
                f"<tt>{output}</tt>",
                install=True
            )

    # ---- Public API
    # -------------------------------------------------------------------------
    def install(self, pyexec):
        self._install(pyexec, dryrun=True)

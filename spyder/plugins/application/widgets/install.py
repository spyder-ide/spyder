# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Update installation widgets."""

# Standard library imports
import logging
import os
import subprocess

# Third-party imports
from qtpy.QtCore import Qt, QThread, Signal
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QMessageBox,
                            QLabel, QProgressBar, QPushButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder import __version__
from spyder.api.translations import _
from spyder.config.base import is_pynsist
from spyder.utils.icon_manager import ima
from spyder.workers.updates import WorkerDownloadInstaller

# Logger setup
logger = logging.getLogger(__name__)

# Update installation process statuses
NO_STATUS = __version__
DOWNLOADING_INSTALLER = _("Downloading update")
DOWNLOAD_FINISHED = _("Download finished")
INSTALLING = _("Installing update")
FINISHED = _("Installation finished")
PENDING = _("Update available")
CHECKING = _("Checking for updates")
CANCELLED = _("Cancelled update")

INSTALL_INFO_MESSAGES = {
    DOWNLOADING_INSTALLER: _("Downloading Spyder {version}"),
    DOWNLOAD_FINISHED: _("Finished downloading Spyder {version}"),
    INSTALLING: _("Installing Spyder {version}"),
    FINISHED: _("Finished installing Spyder {version}"),
    PENDING: _("Spyder {version} available to download"),
    CHECKING: _("Checking for new Spyder version"),
    CANCELLED: _("Spyder update cancelled")
}


class UpdateInstallation(QWidget):
    """Update progress installation widget."""

    def __init__(self, parent):
        super().__init__(parent)
        action_layout = QVBoxLayout()
        progress_layout = QHBoxLayout()
        self._progress_widget = QWidget(self)
        self._progress_widget.setFixedHeight(50)
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedWidth(180)
        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(ima.icon('DialogCloseButton'))
        self.cancel_button.setFixedHeight(25)
        self.cancel_button.setFixedWidth(25)
        progress_layout.addWidget(self._progress_bar, alignment=Qt.AlignLeft)
        progress_layout.addWidget(self.cancel_button)
        progress_layout.setAlignment(Qt.AlignVCenter)
        self._progress_widget.setLayout(progress_layout)

        self._progress_label = QLabel(_('Downloading'))

        self.install_info = QLabel(
            _("Downloading Spyder update <br>"))

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton(_('OK'))
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addStretch()
        action_layout.addStretch()
        action_layout.addWidget(self._progress_label)
        action_layout.addWidget(self._progress_widget)
        action_layout.addWidget(self.install_info)
        action_layout.addSpacing(10)
        action_layout.addLayout(button_layout)
        action_layout.addStretch()

        # Layout
        general_layout = QHBoxLayout()
        general_layout.addLayout(action_layout)

        self.setLayout(general_layout)

    def update_installation_status(self, status, latest_version):
        """Update installation status (downloading, installing, finished)."""
        self._progress_label.setText(status)
        self.install_info.setText(INSTALL_INFO_MESSAGES[status].format(
            version=latest_version))
        if status == INSTALLING:
            self._progress_bar.setRange(0, 0)
            self.cancel_button.setEnabled(False)

    def update_installation_progress(self, current_value, total):
        """Update installation progress bar."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current_value)


class UpdateInstallerDialog(QDialog):
    """Update installer dialog."""

    sig_download_progress = Signal(int, int)
    """
    Signal to get the download progress.

    Parameters
    ----------
    current_value: int
        Size of the data downloaded until now.
    total: int
        Total size of the file expected to be downloaded.
    """

    sig_installation_status = Signal(str, str)
    """
    Signal to get the current status of the update installation.

    Parameters
    ----------
    status: str
        Status string.
    latest_release: str
        Latest release version detected.
    """

    sig_install_on_close_requested = Signal(str)
    """
    Signal to request running the downloaded installer on close.

    Parameters
    ----------
    installer_path: str
        Path to the installer executable.
    """

    def __init__(self, parent):
        self.cancelled = False
        self.status = NO_STATUS
        self.download_thread = None
        self.download_worker = None
        self.installer_path = None

        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._parent = parent
        self._installation_widget = UpdateInstallation(self)
        self.latest_release_version = ""

        # Layout
        installer_layout = QVBoxLayout()
        installer_layout.addWidget(self._installation_widget)
        self.setLayout(installer_layout)

        # Signals
        self.sig_download_progress.connect(
            self._installation_widget.update_installation_progress)
        self.sig_installation_status.connect(
            self._installation_widget.update_installation_status)

        self._installation_widget.ok_button.clicked.connect(
            self.close_installer)
        self._installation_widget.cancel_button.clicked.connect(
            self.cancel_installation)

        # Show installation widget
        self.setup()

    def reject(self):
        """Reimplemented Qt method."""
        on_installation_widget = self._installation_widget.isVisible()
        if on_installation_widget:
            self.close_installer()
        else:
            super().reject()

    def setup(self):
        """Setup visibility of widgets."""
        self._installation_widget.setVisible(True)
        self.adjustSize()

    def save_latest_release(self, latest_release_version):
        self.latest_release_version = latest_release_version

    def start_installation(self, latest_release_version):
        """Start downloading the update and set downloading status."""
        self.latest_release_version = latest_release_version
        self.cancelled = False
        self._change_update_installation_status(
            status=DOWNLOADING_INSTALLER)
        self.download_thread = QThread(None)
        self.download_worker = WorkerDownloadInstaller(
            self, self.latest_release_version)
        self.download_worker.sig_ready.connect(self.confirm_installation)
        self.download_worker.sig_ready.connect(self.download_thread.quit)
        self.download_worker.sig_download_progress.connect(
            self.sig_download_progress.emit)
        self.download_worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.download_worker.start)
        self.download_thread.start()

    def cancel_installation(self):
        """Cancel the installation in progress."""
        reply = QMessageBox.critical(
            self._parent, 'Spyder',
            _('Do you really want to cancel the Spyder update installation?'),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cancelled = True
            self._cancel_download()
            self.finish_installation()
            return True
        return False

    def continue_installation(self):
        """
        Continue the installation in progress.

        Download the installer if needed or prompt to install.
        """
        reply = QMessageBox(icon=QMessageBox.Question,
                            text=_("Would you like to update Spyder to "
                                   "the latest version?"
                                   "<br><br>"),
                            parent=self._parent)
        reply.setWindowTitle("Spyder")
        reply.setAttribute(Qt.WA_ShowWithoutActivating)
        reply.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply.exec_()
        if reply.result() == QMessageBox.Yes:
            self.start_installation(self.latest_release_version)
        else:
            self._change_update_installation_status(status=PENDING)

    def confirm_installation(self, installer_path):
        """
        Ask users if they want to proceed with the installer execution.
        """
        if self.cancelled:
            return
        self._change_update_installation_status(status=DOWNLOAD_FINISHED)
        self.installer_path = installer_path
        msg_box = QMessageBox(
            icon=QMessageBox.Question,
            text=_("Would you like to proceed with the installation?<br><br>"),
            parent=self._parent
        )
        msg_box.setWindowTitle(_("Spyder update"))
        msg_box.setAttribute(Qt.WA_ShowWithoutActivating)
        if is_pynsist():
            # Only add yes button for Windows installer
            # since it has the logic to restart Spyder
            yes_button = msg_box.addButton(QMessageBox.Yes)
        else:
            yes_button = None
        after_closing_button = msg_box.addButton(
            _("After closing"), QMessageBox.YesRole)
        msg_box.addButton(QMessageBox.No)
        msg_box.exec_()

        if msg_box.clickedButton() == yes_button:
            self._change_update_installation_status(status=INSTALLING)
            cmd = ('start' if os.name == 'nt' else 'open')
            if self.installer_path:
                subprocess.Popen(
                    ' '.join([cmd, self.installer_path]),
                    shell=True
                )
            self._change_update_installation_status(status=PENDING)
        elif msg_box.clickedButton() == after_closing_button:
            self.sig_install_on_close_requested.emit(self.installer_path)
            self._change_update_installation_status(status=PENDING)
        else:
            self._change_update_installation_status(status=PENDING)

    def finish_installation(self):
        """Handle finished installation."""
        self.setup()
        self.accept()

    def close_installer(self):
        """Close the installation dialog."""
        if (
            self.status == FINISHED
            or self.status == CANCELLED
        ):
            self.finish_installation()
        else:
            self.hide()

    def _change_update_installation_status(self, status=NO_STATUS):
        """Set the installation status."""
        logger.debug(f"Installation status: {status}")
        self.status = status
        if status == DOWNLOAD_FINISHED:
            self.close_installer()
        elif status == FINISHED or status == PENDING:
            self.finish_installation()
        self.sig_installation_status.emit(
            self.status, self.latest_release_version)

    def _cancel_download(self):
        self._change_update_installation_status(status=CANCELLED)
        self.download_worker.cancelled = True
        self.download_thread.quit()
        self.download_thread.wait()
        self._change_update_installation_status(status=PENDING)

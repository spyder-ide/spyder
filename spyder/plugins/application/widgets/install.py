# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Update installation widgets."""

# Standard library imports
import logging
import os
import subprocess
import tempfile
import threading
from urllib.request import urlretrieve

# Third-party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QMessageBox,
                            QLabel, QProgressBar, QPushButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder import __version__
from spyder.api.translations import get_translation
from spyder.utils.icon_manager import ima
from spyder.utils.programs import is_module_installed

logger = logging.getLogger(__name__)

# Localization
_ = get_translation('spyder')

# Update installation process statuses
NO_STATUS = __version__
DOWNLOADING_INSTALLER = _("Downloading update")
INSTALLING = _("Installing update")
FINISHED = _("Installation finished")
PENDING = _("Update available")
CHECKING = _("Checking for updates")
CANCELLED = _("Cancelled update")

INSTALL_INFO_MESSAGES = {
    DOWNLOADING_INSTALLER: _("Downloading latest Spyder update"),
    INSTALLING: _("Installing Spyder update"),
    FINISHED: _("Spyder update installation finished"),
    PENDING: _("Spyder update available to download"),
    CHECKING: _("Checking for Spyder updates"),
    CANCELLED: _("Spyder update cancelled")
}


class UpdateInstallationCancelledException(Exception):
    """Update installation was cancelled."""
    pass


class UpdateInstallation(QWidget):
    """Update progress installation widget."""

    def __init__(self, parent):
        super().__init__(parent)

        # Left side
        action_layout = QVBoxLayout()
        progress_layout = QHBoxLayout()
        self._progress_widget = QWidget(self)
        self._progress_widget.setFixedHeight(50)
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedWidth(180)
        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(ima.icon('DialogCloseButton'))
        progress_layout.addWidget(self._progress_bar, alignment=Qt.AlignLeft)
        progress_layout.addWidget(self.cancel_button)
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

    def update_installation_status(self, status):
        """Update installation status (downloading, installing, finished)."""
        self._progress_label.setText(status)
        self.install_info.setText(INSTALL_INFO_MESSAGES[status])
        if status == INSTALLING:
            self._progress_bar.setRange(0, 0)
            self.cancel_button.setEnabled(False)

    def update_installation_progress(self, current_value, total):
        """Update installation progress bar."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current_value)


class UpdateInstallerDialog(QDialog):
    """Update installer dialog."""

    # Signal to get the download progress
    # int: Download progress
    # int: Total download size
    sig_download_progress = Signal(int, int)

    # Signal to get the current status of the update installation
    # str: Status string
    sig_installation_status = Signal(str)

    def __init__(self, parent):

        self.cancelled = False
        self.status = NO_STATUS
        self.thread_install_update = None
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
        self.sig_installation_status.connect(
            self.finished_installation)

        self._installation_widget.ok_button.clicked.connect(
            self.close_installer)
        self._installation_widget.cancel_button.clicked.connect(
            self.cancel_install)

        # Show installation widget
        self.setup()

    def setup(self):
        """Setup visibility of widgets."""
        self._installation_widget.setVisible(True)
        self.adjustSize()

    def cancel_install(self):
        """Cancel the installation in progress."""
        reply = QMessageBox.critical(
            self._parent, 'Spyder',
            _('Do you really want to cancel the Spyder update installation?'),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cancelled = True
            self.cancel_thread_install_update()
            self.setup()
            self.accept()
            return True
        return False

    def continue_install(self):
        """
        Continue the installation in progress by downloading the installer.
        """
        reply = QMessageBox(icon=QMessageBox.Question,
                            text=_("Would you like to automatically download "
                                   "and install the latest version of Spyder?"
                                   "<br><br>"),
                            parent=self._parent)
        reply.setWindowTitle("Spyder")
        reply.setAttribute(Qt.WA_ShowWithoutActivating)
        reply.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply.exec_()
        if reply.result() == QMessageBox.Yes:
            self.start_installation_update()
        else:
            self._change_update_installation_status(status=PENDING)

    def finished_installation(self, status):
        """Handle finished installation."""
        if status == FINISHED or status == PENDING:
            self.setup()
            self.accept()

    def close_installer(self):
        """Close the installation dialog."""
        if (self.status == FINISHED
                or self.status == CANCELLED):
            self.setup()
            self.accept()
        else:
            self.hide()

    def reject(self):
        """Reimplemented Qt method."""
        on_installation_widget = self._installation_widget.isVisible()
        if on_installation_widget:
            self.close_installer()
        else:
            super(UpdateInstallerDialog, self).reject()

    def _change_update_installation_status(self, status=NO_STATUS):
        """Set the installation status."""
        logger.debug(f"Installation status: {status}")
        self.status = status
        self.sig_installation_status.emit(self.status)

    def _progress_reporter(self, block_number, read_size, total_size):
        progress = 0
        if total_size > 0:
            progress = block_number * read_size
        if self.cancelled:
            raise UpdateInstallationCancelledException()
        else:
            self.sig_download_progress.emit(progress, total_size)

    def cancel_thread_install_update(self):
        self._change_update_installation_status(status=CANCELLED)
        self.thread_install_update.join()

    def _download_install(self):
        try:
            logger.debug("Downloading installer executable")
            tmpdir = tempfile.gettempdir()
            is_full_installer = (is_module_installed('numpy') or
                                 is_module_installed('pandas'))
            if os.name == 'nt':
                name = 'Spyder_64bit_{}.exe'.format('full' if is_full_installer
                                                    else 'lite')
            else:
                name = 'Spyder{}.dmg'.format('' if is_full_installer
                                             else '-Lite')

            url = ('https://github.com/spyder-ide/spyder/releases/latest/'
                   f'download/{name}')
            installer_dir_path = os.path.join(tmpdir, 'spyder', 'updates',
                                              self.latest_release_version)
            os.makedirs(installer_dir_path, exist_ok=True)
            installer_path = os.path.join(installer_dir_path, name)
            if (not os.path.isfile(installer_path)):
                logger.debug(
                    f"Downloading installer from {url} to {installer_path}")
                download = urlretrieve(url,
                                       installer_path,
                                       reporthook=self._progress_reporter)
            self._change_update_installation_status(status=INSTALLING)
            cmd = ('start' if os.name == 'nt' else 'open')
            subprocess.run(' '.join([cmd, installer_path]), shell=True)

        except UpdateInstallationCancelledException:
            self._change_update_installation_status(status=CANCELLED)
        finally:
            self._change_update_installation_status(status=PENDING)

    def start_installation_update(self, latest_release_version):
        """Start the installation update thread and set downloading status."""
        self.latest_release_version = latest_release_version
        self.cancelled = False
        self._change_update_installation_status(
            status=DOWNLOADING_INSTALLER)
        self.thread_install_update = threading.Thread(
            target=self._download_install)
        self.thread_install_update.start()

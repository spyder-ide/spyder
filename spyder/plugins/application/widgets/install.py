# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Update installation widget."""

# Standard library imports
import sys
import os
import subprocess
from urllib.request import urlretrieve
from tempfile import TemporaryDirectory
import threading

# Third-party imports
from qtpy.QtCore import QEvent, QObject, Qt, Signal
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QMessageBox,
                            QLabel, QProgressBar, QPushButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder import __version__
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette


# Update installation process statuses
NO_STATUS = __version__
DOWNLOADING_INSTALLER = _("Downloading installer")
INSTALLING = _("Installing")
FINISHED = _("Installation finished")
PENDING = _("Pending update")
CHECKING = _("Checking for updates")
CANCELLED = _("Cancelled")


class UpdateInstallation(QWidget):
    """Update progress installation widget."""

    def __init__(self, parent):
        super(UpdateInstallation, self).__init__(parent)

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
            _("Downloading the latest Spyder version <br>"))

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
        self.install_info.setText(status + _(" the latest version of Spyder."))
        if status == INSTALLING:
            self._progress_bar.setRange(0, 0)
            self.cancel_button.hide()

    def update_installation_progress(self, current_value, total):
        """Update installation progress bar."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current_value)


class UpdateInstallerDialog(QDialog):
    """Spyder installer."""

    # Signal to get the download progress
    # int: Download progress
    # int: Total download size
    sig_download_progress = Signal(int, int)

    # Signals
    # Signal to get the current status of the update installation
    # str: Status string
    sig_installation_status = Signal(str)

    def __init__(self, parent):

        self.cancelled = False
        self.status = NO_STATUS
        self.thread_install_update = None
        super(UpdateInstallerDialog, self).__init__(parent)
        self.setStyleSheet(
            f"background-color: {QStylePalette.COLOR_BACKGROUND_2}")
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._parent = parent
        self._installation_widget = UpdateInstallation(self)

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

        # Show integration widget
        self.setup()

    def setup(self, installation=False):
        """Setup visibility of widgets."""
        self._installation_widget.setVisible(True)
        self.adjustSize()

    def cancel_install(self):
        """Cancel the installation in progress."""
        reply = QMessageBox.critical(
            self._parent, 'Spyder',
            _('Do you really want to cancel installing the Spyder update?'),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cancelled = True
            self.cancell_thread_install_update()
            self.setup()
            self.accept()
            return True
        return False

    def continue_install(self):
        """Continue the installation in progress
        by downloading the installer."""
        reply = QMessageBox(icon=QMessageBox.Question,
                            text=_('Do you want to download and'
                                   ' install the latest version of'
                                   ' spyder?<br>'),
                            parent=self._parent)
        reply.setWindowTitle("Spyder")
        reply.setAttribute(Qt.WA_ShowWithoutActivating)
        reply.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply.show()
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
        """Reimplement Qt method."""
        on_installation_widget = self._installation_widget.isVisible()
        if on_installation_widget:
            self.close_installer()
        else:
            super(UpdateInstallerDialog, self).reject()

    def _change_update_installation_status(self, status=NO_STATUS):
        """Set the installation status."""
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

    def cancell_thread_install_update(self):
        self._change_update_installation_status(status=CANCELLED)
        self.thread_install_update.join()

    def _download_install(self):
        try:
            with TemporaryDirectory(prefix="Spyder-") as tmpdir:
                destination = os.path.join(tmpdir, 'updateSpyder.exe')
                download = urlretrieve(
                    ('https://github.com/spyder-ide/spyder/releases/latest/'
                        'download/Spyder_64bit_full.exe'),
                    destination,
                    reporthook=self._progress_reporter)
                self._change_update_installation_status(status=INSTALLING)
                install = subprocess.Popen(destination, shell=True)
                install.communicate()
        except UpdateInstallationCancelledException:
            self._change_update_installation_status(status=CANCELLED)
        finally:
            self._change_update_installation_status(status=PENDING)

    def start_installation_update(self):
        self.cancelled = False
        self._change_update_installation_status(
            status=DOWNLOADING_INSTALLER)
        """call a function in a simple thread, to prevent blocking"""
        self.thread_install_update = threading.Thread(
            target=self._download_install)
        self.thread_install_update.start()


class UpdateInstallationCancelledException(Exception):
    """Update installation was cancelled."""
    pass

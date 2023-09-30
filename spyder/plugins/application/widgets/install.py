# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Update installation widgets."""

# Standard library imports
import logging
import os
import sys
import subprocess
from tempfile import gettempdir

# Third-party imports
from packaging.version import parse
from qtpy.QtCore import Qt, QThread, Signal
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QMessageBox,
                            QLabel, QProgressBar, QPushButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder import __version__
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.translations import _
from spyder.config.base import is_conda_based_app
from spyder.config.utils import is_anaconda
from spyder.utils.conda import find_conda, is_anaconda_pkg
from spyder.utils.icon_manager import ima
from spyder.widgets.helperwidgets import MessageCheckBox
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
INSTALL_ON_CLOSE = _("Install on close")

INSTALL_INFO_MESSAGES = {
    DOWNLOADING_INSTALLER: _("Downloading Spyder {version}"),
    DOWNLOAD_FINISHED: _("Finished downloading Spyder {version}"),
    INSTALLING: _("Installing Spyder {version}"),
    FINISHED: _("Finished installing Spyder {version}"),
    PENDING: _("Spyder {version} available to download"),
    CHECKING: _("Checking for new Spyder version"),
    CANCELLED: _("Spyder update cancelled"),
    INSTALL_ON_CLOSE: _("Install Spyder {version} on close")
}

header = _("<b>Spyder {} is available!</b> "
           "<i>(you&nbsp;have&nbsp;{})</i><br><br>")


class UpdateDownload(QWidget):
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
        if status in INSTALL_INFO_MESSAGES:
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


class UpdateInstallerDialog(QDialog, SpyderConfigurationAccessor):
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

    sig_install_on_close_requested = Signal(bool)
    """
    Signal to request running the downloaded installer on close.

    Parameters
    ----------
    install_on_close: bool
        Whether to install on close.
    """

    sig_quit_requested = Signal()
    """
    This signal can be emitted to request the main application to quit.
    """

    def __init__(self, parent):
        self.CONF_SECTION = parent.CONF_SECTION
        self.cancelled = False
        self.status = NO_STATUS
        self.download_thread = None
        self.download_worker = None
        self.latest_release = None
        self.major_update = None
        self.installer_path = None

        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._parent = parent
        self._download_widget = UpdateDownload(self)

        # Layout
        installer_layout = QVBoxLayout()
        installer_layout.addWidget(self._download_widget)
        self.setLayout(installer_layout)

        # Signals
        self.sig_download_progress.connect(
            self._download_widget.update_installation_progress)
        self.sig_installation_status.connect(
            self._download_widget.update_installation_status)

        self._download_widget.ok_button.clicked.connect(
            self.close_installer)
        self._download_widget.cancel_button.clicked.connect(
            self.cancel_download)

        # Show installation widget
        self.setup()

    def reject(self):
        """Reimplemented Qt method."""
        if self._download_widget.isVisible():
            self.close_installer()
        else:
            super().reject()

    def setup(self):
        """Setup visibility of widgets."""
        self._download_widget.setVisible(True)
        self.adjustSize()

    def set_latest_release(self, latest_release):
        self.latest_release = latest_release
        self.major_update = (
            parse(__version__).major < parse(latest_release).major
        )

    def start_update(self):
        # Define the custom QMessageBox
        box = MessageCheckBox(icon=QMessageBox.Information,
                              parent=self)
        box.setWindowTitle(_("New Spyder version"))
        box.setAttribute(Qt.WA_ShowWithoutActivating)
        box.set_checkbox_text(_("Check for updates at startup"))
        box.setTextFormat(Qt.RichText)

        # Adjust the checkbox depending on the stored configuration
        option = 'check_updates_on_startup'
        box.set_checked(self.get_conf(option))

        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.Yes)

        # ---- conda-based application
        if is_conda_based_app():
            if not self.major_update:
                # Update with conda
                self.confirm_installation()
                return

            # Update using our installers
            box.setText(
                header.format(self.latest_release, __version__) +
                _("Would you like to download and install it?<br><br>")
            )
            box.exec_()
            if box.result() == QMessageBox.Yes:
                self.start_download()
            return

        # ---- Not conda-based, nudge installers
        url_i = 'https://docs.spyder-ide.org/current/installation.html'

        installers_url = url_i + "#standalone-installers"
        msg = (
            header.format(self.latest_release, __version__) +
            _("Would you like to automatically download and "
              "install it using Spyder's installer?"
              "<br><br>"
              "We <a href='{}'>recommend our own installer</a> "
              "because it's more stable and makes updating easy. "
              "This will leave your existing Spyder installation "
              "untouched.").format(installers_url)
        )
        box.setText(msg)
        box.exec_()
        if box.result() == QMessageBox.Yes:
            self.start_download()
            return

        # ---- Not conda-based, manual update
        box.setStandardButtons(QMessageBox.Ok)
        box.setDefaultButton(QMessageBox.Ok)

        terminal = _("terminal")
        if os.name == "nt":
            if is_anaconda():
                terminal = "Anaconda prompt"
            else:
                terminal = _("cmd prompt")
        msg = _("Run the following commands in the {} to update "
                "manually:<br><br>").format(terminal)

        if is_anaconda():
            if is_anaconda_pkg():
                msg += _("<code>conda update anaconda</code><br>")
            msg += _("<code>conda install spyder={}"
                     "</code><br><br>").format(self.latest_release)
            msg += _("<b>Important note:</b> Since you installed "
                     "Spyder with Anaconda, please <b>don't</b> use "
                     "<code>pip</code> to update it as that will "
                     "break your installation.")
        else:
            msg += _("<code>pip install --upgrade spyder"
                     "</code>")

        msg += _(
            "<br><br>For more information, visit our "
            "<a href=\"{}\">installation guide</a>."
        ).format(url_i)

        box.setText(msg)
        box.exec_()

    def start_download(self):
        """Start downloading the update and set downloading status."""
        self.cancelled = False
        self._change_update_download_status(
            status=DOWNLOADING_INSTALLER)
        self.download_thread = QThread(None)
        self.download_worker = WorkerDownloadInstaller(
            self, self.latest_release)
        self.download_worker.sig_ready.connect(
            lambda: self._change_update_download_status(DOWNLOAD_FINISHED))
        self.download_worker.sig_ready.connect(self.confirm_installation)
        self.download_worker.sig_ready.connect(self.download_thread.quit)
        self.download_worker.sig_download_progress.connect(
            self.sig_download_progress.emit)
        self.download_worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.download_worker.start)
        self.download_thread.start()

    def cancel_download(self):
        """Cancel the installation in progress."""
        reply = QMessageBox.critical(
            self._parent, 'Spyder',
            _('Do you really want to cancel the download?'),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cancelled = True
            self._cancel_download()
            self.finish_installation()
            return True
        return False

    def confirm_installation(self):
        """
        Ask users if they want to proceed with the installer execution.
        """
        if self.cancelled:
            return

        msg = (
            header.format(self.latest_release, __version__) +
            _("Would you like to proceed with the installation?<br><br>")
        )

        msg_box = QMessageBox(
            icon=QMessageBox.Question,
            text=msg,
            parent=self._parent
        )
        msg_box.setWindowTitle(_("Spyder update"))
        msg_box.setAttribute(Qt.WA_ShowWithoutActivating)

        self.installer_path = None
        # Get data from WorkerDownload
        if self.download_worker:
            if self.download_worker.error:
                # If download error, do not proceed with install
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(self.download_worker.error)
                msg_box.addButton(QMessageBox.Ok)
                msg_box.exec_()
                return
            self.installer_path = self.download_worker.installer_path

        yes_button = msg_box.addButton(QMessageBox.Yes)
        after_closing_button = msg_box.addButton(
            _("After closing"), QMessageBox.YesRole)
        msg_box.addButton(QMessageBox.No)
        msg_box.exec_()

        if msg_box.clickedButton() == yes_button:
            self.sig_install_on_close_requested.emit(True)
            self.sig_quit_requested.emit()
        elif msg_box.clickedButton() == after_closing_button:
            self.sig_install_on_close_requested.emit(True)
            self._change_update_download_status(INSTALL_ON_CLOSE)

    def start_installation(self):
        """Install from downloaded installer or update through conda."""

        # Install script
        script = os.path.abspath(__file__ + '/../../scripts/install.' +
                                 ('bat' if os.name == 'nt' else 'sh'))

        # Sub command
        sub_cmd = [script, '-p', sys.prefix]
        if self.installer_path and os.path.exists(self.installer_path):
            # Run downloaded installer
            sub_cmd.extend(['-i', self.installer_path])
        elif self.latest_release is not None:
            # Update with conda
            sub_cmd.extend(['-c', find_conda(), '-v', self.latest_release])

        # Final command assembly
        if os.name == 'nt':
            cmd = ['start', '"Update Spyder"'] + sub_cmd
        elif sys.platform == 'darwin':
            # Terminal cannot accept a command with arguments therefore
            # create a temporary script
            tmpdir = os.path.join(gettempdir(), 'spyder')
            tmpscript = os.path.join(tmpdir, 'tmp_install.sh')
            os.makedirs(tmpdir, exist_ok=True)
            with open(tmpscript, 'w') as f:
                f.write(' '.join(sub_cmd))
            os.chmod(tmpscript, 0o711)  # set executable permissions

            cmd = ['open', '-b', 'com.apple.terminal', tmpscript]
        else:
            cmd = ['gnome-terminal', '--window', '--'] + sub_cmd

        subprocess.Popen(' '.join(cmd), shell=True)

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

    def _change_update_download_status(self, status=NO_STATUS):
        """Set the installation status."""
        logger.debug(f"Installation status: {status}")
        self.status = status
        if status == DOWNLOAD_FINISHED:
            self.close_installer()
        elif status == FINISHED or status == PENDING:
            self.finish_installation()
        self.sig_installation_status.emit(
            self.status, self.latest_release)

    def _cancel_download(self):
        self._change_update_download_status(status=CANCELLED)
        self.download_worker.cancelled = True
        self.download_thread.quit()
        self.download_thread.wait()
        self._change_update_download_status(status=PENDING)

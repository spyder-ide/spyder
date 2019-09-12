# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite installation functions."""

# Standard library imports
import os
import os.path as osp
from urllib.request import urlretrieve
import sys
from tempfile import gettempdir

# Third party imports
from qtpy.QtCore import QThread, Signal

# Local imports
from spyder.py3compat import to_text_string
from spyder.plugins.completion.kite.utils.status import check_if_kite_installed


class KiteInstallationThread(QThread):
    """Thread to handle the installation process of kite."""
    # Installer URLs
    WINDOWS_URL = "https://release.kite.com/dls/windows/current"
    LINUX_URL = "https://release.kite.com/dls/linux/current"
    MAC_URL = "https://release.kite.com/dls/mac/current"

    # Process status
    NO_STATUS = "No status"
    DOWNLOADING_SCRIPT = "Downloading Kite script installer"
    DOWNLOADING_INSTALLER = "Downloading Kite installer"
    INSTALLING = "Installing Kite"
    FINISHED = "Install finished"
    ERRORED = "Error"

    # Signals
    # Signal to get the current status of the installation
    # str: Status string
    sig_installation_status = Signal(str)
    # Signal to get the download progress
    # str: Download progress
    sig_download_progress = Signal(str)
    # Signal to get error messages
    # str: Error string
    sig_error_msg = Signal(str)

    def __init__(self, parent):
        super(KiteInstallationThread).__init__()
        if os.name == 'nt':
            self._download_url = self.WINDOWS_URL
            self._installer_name = 'kiteSetup.exe'
            self._install_commands = [
                'KiteSetup.exe --plugin-launch-with-copilot --channel=spyder']
        elif sys.platform == 'darwin':
            self._download_url = self.MAC_URL
            self._installer_name = 'Kite.dmg'
            self._install_commands = [
                'hdiutil attach -nobrowse Kite.dmg',
                'cp -r /Volumes/Kite/Kite.app /Applications/',
                'hdiutil detach /Volumes/Kite/',
                'open -a /Applications/Kite.app --args --plugin-launch-with-copilot --channel=spyder']
        else:
            self._download_url = self.LINUX_URL
            self._installer_name = 'kite_installer.sh'
            self._install_commands = [
                'kite_installer.sh --download',
                '~/.local/share/kite/kited --plugin-launch-with-copilot --channel=spyder' ]

    def _change_installation_status(self, status=NO_STATUS):
        """Set the installation status."""
        self._status = status
        self.sig_installation_status.emit(self._status)

    def _progress_reporter(self, block_number, read_size, total_size):
        progress = 0
        if total_size > 0:
            progress = block_number * read_size
        progress_message = '{0}/{1}'.format(progress, total_size)
        self.sig_download_progress.emit(progress_message)

    def _download_installer_or_script(self):
        """
        Download the installer or installation script in a temporary directory.
        """
        temp_dir = gettempdir()
        path = osp.join(temp_dir, self._installer_name)
        if sys.platform.startswith('linux'):
            self._change_installation_status(status=self.DOWNLOADING_SCRIPT)
        else:
            self._change_installation_status(status=self.DOWNLOADING_INSTALLER)

        return urlretrieve(
            self._download_url,
            path,
            reporthook=self._progress_reporter)

    def _execute_installer_or_script(self, installer_path):
        """Execute the installer."""
        self._install_commands
        if sys.platform.startswith('linux'):
            self._change_installation_status(status=self.DOWNLOADING_INSTALLER)
        self._change_installation_status(status=self.INSTALLING)

    def _remove_installer_or_script(self, installer_path):
        """Remove installer or script file."""
        pass

    def run(self):
        """Execute the installation task."""
        try:
            path, _ = self._download_installer_or_script()
            path = osp.dirname(path)
            self._execute_installer_or_script(path)
            self._remove_installer_or_script(path)
            self._change_installation_status(status=self.FINISHED)
        except Exception as error:
            self.sig_installation_status.emit(self.ERROR)
            self.sig_error_msg.emit(to_text_string(error))

    def install(self):
        """Install Kite."""
        # If already running wait for it to finish
        if self.wait():
            if not check_if_kite_installed():
                self.start()
            else:
                self._change_installation_status(status=self.FINISHED)


if __name__ == '__main__':
    install_manager = KiteInstallationThread(None)

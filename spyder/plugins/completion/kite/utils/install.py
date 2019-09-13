# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite installation functions."""

# Standard library imports
import os
import os.path as osp
import re
import subprocess
import sys
from tempfile import gettempdir
from urllib.request import urlretrieve

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
        super(KiteInstallationThread, self).__init__()
        if os.name == 'nt':
            self._download_url = self.WINDOWS_URL
            self._installer_name = 'kiteSetup.exe'
        elif sys.platform == 'darwin':
            self._download_url = self.MAC_URL
            self._installer_name = 'Kite.dmg'
        else:
            self._download_url = self.LINUX_URL
            self._installer_name = 'kite_installer.sh'

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
        """Download the installer or installation script."""
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

    def _execute_windows_installation(self, installer_path):
        """Installation on Windows."""
        self._change_installation_status(status=self.INSTALLING)
        install_command = [
            installer_path,
            '--plugin-launch-with-copilot',
            '--channel=spyder']
        subprocess.call(install_command, shell=True)

    def _execute_mac_installation(self, installer_path):
        """Installation on MacOS."""
        self._change_installation_status(status=self.INSTALLING)
        install_commands = [
            ['hdiutil', 'attach', '-nobrowse', installer_path],
            ['cp', '-r', '/Volumes/Kite/Kite.app', '/Applications/'],
            ['hdiutil', 'detach', '/Volumes/Kite/'],
            ['open',
             '-a',
             '/Applications/Kite.app',
             '--args',
             '--plugin-launch-with-copilot',
             '--channel=spyder']
        ]
        for command in install_commands:
            subprocess.call(command)

    def _execute_linux_installation(self, installer_path):
        """Installation on Linux."""
        self._change_installation_status(status=self.DOWNLOADING_INSTALLER)
        download_command = [installer_path, '--download']
        with subprocess.Popen(
                download_command,
                stdout=subprocess.PIPE,
                universal_newlines=True) as download_process:
            for progress in iter(download_process.stdout.readline, ""):
                if re.match(r'Download: (\d+)/(\d+)', progress):
                    download_progress = progress.split(':')[-1].strip()
                    self.sig_download_progress.emit(download_progress)

        install_commands = [
            [installer_path, '--install'],
            ['~/.local/share/kite/kited',
             '--plugin-launch-with-copilot',
             '--channel=spyder']
        ]
        self._change_installation_status(status=self.INSTALLING)
        for command in install_commands:
            subprocess.call(command)

    def _execute_installer_or_script(self, installer_path):
        """Execute the installer."""
        if os.name == 'nt':
            self._execute_windows_installation(installer_path)
        elif sys.platform == 'darwin':
            self._execute_mac_installation(installer_path)
        else:
            self._execute_linux_installation(installer_path)
        os.remove(installer_path)

    def run(self):
        """Execute the installation task."""
        try:
            path, _ = self._download_installer_or_script()
            self._execute_installer_or_script(path)
            self._change_installation_status(status=self.FINISHED)
        except Exception as error:
            self._change_installation_status(status=self.ERRORED)
            self.sig_error_msg.emit(to_text_string(error))
            return

    def install(self):
        """Install Kite."""
        # If already running wait for it to finish
        if self.wait():
            is_kite_installed, _ = check_if_kite_installed()
            if is_kite_installed:
                self._change_installation_status(status=self.FINISHED)
            else:
                self.start()


if __name__ == '__main__':
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    install_manager = KiteInstallationThread(None)
    install_manager.sig_installation_status.connect(
        lambda status: print(status))
    install_manager.sig_error_msg.connect(
        lambda error: print(error))
    install_manager.sig_download_progress.connect(
        lambda progress: print(progress))
    install_manager.install()
    app.exec_()

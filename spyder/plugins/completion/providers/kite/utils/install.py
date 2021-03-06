# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite installation functions."""

# Standard library imports
from __future__ import print_function
import logging
import os
import os.path as osp
import re
import stat
import subprocess
import sys
from tempfile import gettempdir
from urllib.request import urlretrieve

# Third party imports
from qtpy.QtCore import QThread, Signal

# Local imports
from spyder.config.base import _
from spyder.py3compat import PY2, to_text_string
from spyder.plugins.completion.providers.kite.utils.status import (
    check_if_kite_installed)

# Installation process statuses
NO_STATUS = _("No status")
DOWNLOADING_SCRIPT = _("Downloading script installer")
DOWNLOADING_INSTALLER = _("Downloading installer")
INSTALLING = _("Installing")
FINISHED = _("Installation finished")
ERRORED = _("Installation errored")
CANCELLED = _("Cancelled")

logger = logging.getLogger(__name__)


class KiteInstallationCancelledException(Exception):
    """Kite installation was cancelled."""
    pass


class KiteInstallationThread(QThread):
    """Thread to handle the installation process of kite."""

    # Installer URLs
    WINDOWS_URL = "https://release.kite.com/dls/windows/current"
    LINUX_URL = "https://release.kite.com/dls/linux/current"
    MAC_URL = "https://release.kite.com/dls/mac/current"

    # Signals
    # Signal to get the current status of the installation
    # str: Status string
    sig_installation_status = Signal(str)

    # Signal to get the download progress
    # str: Download progress
    # str: Total download size
    sig_download_progress = Signal(int, int)

    # Signal to get error messages
    # str: Error string
    sig_error_msg = Signal(str)

    def __init__(self, parent):
        super(KiteInstallationThread, self).__init__()
        self.status = NO_STATUS
        self.cancelled = False
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
        self.status = status
        self.sig_installation_status.emit(self.status)

    def _progress_reporter(self, block_number, read_size, total_size):
        progress = 0
        if total_size > 0:
            progress = block_number * read_size
        if self.cancelled:
            raise KiteInstallationCancelledException()
        else:
            self.sig_download_progress.emit(progress, total_size)

    def _download_installer_or_script(self):
        """Download the installer or installation script."""
        temp_dir = gettempdir()
        path = osp.join(temp_dir, self._installer_name)
        if sys.platform.startswith('linux'):
            self._change_installation_status(status=DOWNLOADING_SCRIPT)
        else:
            self._change_installation_status(status=DOWNLOADING_INSTALLER)

        return urlretrieve(
            self._download_url,
            path,
            reporthook=self._progress_reporter)

    def _execute_windows_installation(self, installer_path):
        """Installation on Windows."""
        self._change_installation_status(status=INSTALLING)
        install_command = [
            installer_path,
            '--plugin-launch-with-copilot',
            '--channel=spyder']
        subprocess.check_call(install_command, shell=True)

    def _execute_mac_installation(self, installer_path):
        """Installation on MacOS."""
        self._change_installation_status(status=INSTALLING)
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
            subprocess.check_call(command)

    def _execute_linux_installation(self, installer_path):
        """Installation on Linux."""
        self._change_installation_status(status=DOWNLOADING_INSTALLER)
        stat_file = os.stat(installer_path)
        os.chmod(installer_path, stat_file.st_mode | stat.S_IEXEC)
        download_command = '{} --download'.format(installer_path)
        download_process = subprocess.Popen(
            download_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
            )
        while not self.cancelled:
            progress = download_process.stdout.readline()
            progress = to_text_string(progress, "utf-8")
            if progress == '' and download_process.poll() is not None:
                break
            if re.match(r'Download: (\d+)/(\d+)', progress):
                download_progress = progress.split(':')[-1].strip()
                current_progress = download_progress.split('/')[0]
                total_size = download_progress.split('/')[1]
                self.sig_download_progress.emit(current_progress, total_size)

        if self.cancelled:
            raise KiteInstallationCancelledException()

        download_process.stdout.close()
        return_code = download_process.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, download_command)

        install_command = [installer_path, '--install']
        run_command = [
            '~/.local/share/kite/kited',
            '--plugin-launch-with-copilot',
            '--channel=spyder']

        self._change_installation_status(status=INSTALLING)
        subprocess.check_call(install_command)
        subprocess.Popen(run_command, shell=True)

    def _execute_installer_or_script(self, installer_path):
        """Execute the installer."""
        if os.name == 'nt':
            self._execute_windows_installation(installer_path)
        elif sys.platform == 'darwin':
            self._execute_mac_installation(installer_path)
        else:
            self._execute_linux_installation(installer_path)
        try:
            os.remove(installer_path)
        except Exception:
            # Handle errors while removing installer file
            pass
        self._change_installation_status(status=FINISHED)

    def run(self):
        """Execute the installation task."""
        is_kite_installed, installation_path = check_if_kite_installed()
        if is_kite_installed:
            self._change_installation_status(status=FINISHED)
        else:
            try:
                path, http_response = self._download_installer_or_script()
                self._execute_installer_or_script(path)
            except KiteInstallationCancelledException:
                self._change_installation_status(status=CANCELLED)
            except Exception as error:
                self._change_installation_status(status=ERRORED)
                logger.debug(
                    "Installation error: {0}".format(to_text_string(error)))
                self.sig_error_msg.emit(to_text_string(error))
        return

    def install(self):
        """Install Kite."""
        # If already running wait for it to finish
        if self.wait():
            self.start()

    def cancelled_or_errored(self):
        """Return if the installation was cancelled or failed."""
        return self.status in [ERRORED, CANCELLED]


if __name__ == '__main__':
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    install_manager = KiteInstallationThread(None)
    install_manager.sig_installation_status.connect(
        lambda status: print(status))
    install_manager.sig_error_msg.connect(
        lambda error: print(error))
    install_manager.sig_download_progress.connect(
        lambda progress, total: print('{0}/{1}'.format(progress, total)))
    install_manager.install()
    install_manager.finished.connect(app.quit)
    app.exec_()

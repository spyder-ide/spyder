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
from qtpy.QtCore import QObject


class KiteInstallationManager(QObject):
    WINDOWS_URL = "https://release.kite.com/dls/windows/current"
    LINUX_URL = "https://release.kite.com/dls/linux/current"
    MAC_URL = "https://release.kite.com/dls/mac/current"

    """Manager instance of the installation process of kite."""
    def __init__(self, parent):
        QObject.__init__(self, parent)
        if os.name == 'nt':
            self._download_url = self.WINDOWS_URL
            self._installer_name = 'kiteSetup.exe'
        elif sys.platform == 'darwin':
            self._download_url = self.MAC_URL
            self._installer_name = 'Kite.dmg'
        else:
            self._download_url = self.LINUX_URL
            self._installer_name = 'kite_installer.sh'

    def download_installer(self, progress_reporter=None):
        """Download the installer in a temporary directory."""
        temp_dir = gettempdir()
        path = osp.join(temp_dir, self._installer_name)
        return urlretrieve(self._download_url, path,
                           reporthook=progress_reporter)


if __name__ == '__main__':
    install_manager = KiteInstallationManager(None)

    def progress_reporter(block_number, read_size, total_size):
        print(block_number, read_size, total_size)

    print(install_manager.download_installer(
        progress_reporter=progress_reporter))

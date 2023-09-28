# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import json
import logging
import os
import os.path as osp
import platform
import shutil
import ssl
import sys
import tempfile
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError, HTTPError

# Third party imports
from packaging.version import parse
from qtpy.QtCore import QObject, Signal

# Local imports
from spyder import __version__
from spyder.config.base import (_, is_stable_version, is_conda_based_app,
                                running_under_pytest)
from spyder.py3compat import is_text_string
from spyder.utils.conda import find_conda
from spyder.utils.programs import check_version, run_shell_command

# Logger setup
logger = logging.getLogger(__name__)

context = {}
if hasattr(ssl, '_create_unverified_context'):
    # Fix for spyder-ide/spyder#2685.
    # [Works only with Python >=2.7.9]
    # More info: https://www.python.org/dev/peps/pep-0476/#opting-out
    context = {'context': ssl._create_unverified_context()}


class UpdateDownloadCancelledException(Exception):
    """Download for installer to update was cancelled."""
    pass


class WorkerUpdates(QObject):
    """
    Worker that checks for releases using either the Anaconda
    default channels or the Github Releases page without
    blocking the Spyder user interface, in case of connection
    issues.
    """
    sig_ready = Signal()

    def __init__(self, parent):
        QObject.__init__(self)
        self._parent = parent
        self.error = None
        self.releases = []
        self.version = __version__

        self.update_available = None
        self.latest_release = None
        self.update_from_github = True

    def check_update_available(self):
        """Checks if there is an update available from releases."""
        logger.debug("Checking releases for available updates.")

        self.update_available = False

        # Filter releases
        releases = self.releases
        if is_stable_version(self.version):
            # If current version is stable, only use stable releases
            releases = [r for r in releases if is_stable_version(r)]
        logger.debug(f"Available versions: {releases}")

        # If releases is empty, default to current version
        self.latest_release = releases[-1] if releases else self.version

        self.update_available = check_version(self.version,
                                              self.latest_release, '<')

        logger.debug(f"Update available: {self.update_available}")
        logger.debug(f"Latest release: {self.latest_release}")

    def get_releases(self):
        releases = []
        self.error = None

        if self.update_from_github:
            # Get releases from GitHub
            url = 'https://api.github.com/repos/spyder-ide/spyder/releases'
            logger.debug(f"Getting releases from {url}.")
            data = urlopen(url, **context).read()
        else:
            # Get releases from conda
            logger.debug("Getting releases from conda-forge.")
            if os.name == "nt":
                platform = "win-64"
            elif sys.platform == "darwin":
                platform = "osx-64"
            else:
                platform = "linux-64"
            cmd = f"{find_conda()} search "
            cmd += f"'spyder[channel=conda-forge, subdir={platform}]'"
            cmd += " --json"

            proc = run_shell_command(cmd)
            try:
                data, err = proc.communicate(timeout=20)
            except TimeoutError:
                pass
        try:
            # Needed step for python3 compatibility
            if not is_text_string(data):
                data = data.decode()
            data = json.loads(data)

            if running_under_pytest() and self.releases:
                # If releases set in pytest, don't overwrite
                return

            if self.update_from_github:
                releases = set(item['tag_name'].replace('v', '')
                               for item in data)
            else:
                releases = set(v['version'] for v in data['spyder'])
        except Exception:
            self.error = _('Unable to retrieve Spyder version information.')
        finally:
            # Always reset self.releases
            self.releases = sorted(releases)

    def start(self):
        """Main method of the WorkerUpdates worker"""
        logger.debug("Starting WorkerUpdates.")

        try:
            # First check major version update for conda-based app
            self.update_from_github = True
            self.get_releases()
            self.check_update_available()
            current_major = parse(self.version).major
            latest_major = parse(self.latest_release).major
            download = is_conda_based_app() and current_major < latest_major
            if self.update_available and not download:
                # Check for available update from conda
                self.update_from_github = False
                self.get_releases()
                self.check_update_available()
        except HTTPError as exc:
            logger.debug(exc, stack_info=True)
            self.error = _('Unable to retrieve information.')
        except URLError as exc:
            logger.debug(exc, stack_info=True)
            self.error = _('Unable to connect to the internet. <br><br>Make '
                           'sure the connection is working properly.')
        except Exception as exc:
            logger.debug(exc, stack_info=True)
            self.error = _('Unable to check for updates.')

        try:
            self.sig_ready.emit()
        except RuntimeError:
            pass


class WorkerDownloadInstaller(QObject):
    """
    Worker that donwloads standalone installers for Windows, macOS,
    and Linux without blocking the Spyder user interface.
    """

    sig_ready = Signal()
    """Signal to inform that the worker has finished successfully."""

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

    def __init__(self, parent, latest_release_version):
        QObject.__init__(self)
        self._parent = parent
        self.latest_release_version = latest_release_version
        self.error = None
        self.cancelled = False
        self.installer_path = None

    def _progress_reporter(self, block_number, read_size, total_size):
        """Calculate download progress and notify."""
        progress = 0
        if total_size > 0:
            progress = block_number * read_size
        if self.cancelled:
            raise UpdateDownloadCancelledException()
        self.sig_download_progress.emit(progress, total_size)

    def _download_installer(self):
        """Donwload latest Spyder standalone installer executable."""
        logger.debug("Downloading installer executable")
        tmpdir = tempfile.gettempdir()
        if os.name == 'nt':
            plat, ext = 'Windows', 'exe'
        if sys.platform == 'darwin':
            plat, ext = 'macOS', 'pkg'
        if sys.platform.startswith('linux'):
            plat, ext = 'Linux', 'sh'
        mach = platform.machine().lower().replace("amd64", "x86_64")
        fname = f'Spyder-{self.latest_release_version}-{plat}-{mach}.{ext}'

        url = ('https://github.com/spyder-ide/spyder/releases/download/'
               f'v{self.latest_release_version}/{fname}')
        dir_path = osp.join(tmpdir, 'spyder', 'updates')
        os.makedirs(dir_path, exist_ok=True)
        installer_dir_path = osp.join(
            dir_path, self.latest_release_version)
        os.makedirs(installer_dir_path, exist_ok=True)
        for file in os.listdir(dir_path):
            if file not in [__version__, self.latest_release_version]:
                shutil.rmtree(osp.join(dir_path, file))

        installer_path = osp.join(installer_dir_path, fname)
        self.installer_path = installer_path
        if not osp.isfile(installer_path):
            logger.debug(
                f"Downloading installer from {url} to {installer_path}")
            urlretrieve(
                url, installer_path, reporthook=self._progress_reporter)
        else:
            self._progress_reporter(1, 1, 1)

    def start(self):
        """Main method of the WorkerDownloadInstaller worker."""
        logger.debug("Starting WorkerDownloadInstaller.")
        error_msg = None
        try:
            self._download_installer()
        except UpdateDownloadCancelledException:
            if self.installer_path:
                os.remove(self.installer_path)
            return
        except HTTPError as exc:
            logger.debug(exc, stack_info=True)
            error_msg = _('Unable to retrieve installer information.')
        except URLError as exc:
            logger.debug(exc, stack_info=True)
            error_msg = _('Unable to connect to the internet. <br><br>'
                          'Make sure the connection is working properly.')
        except Exception as exc:
            logger.debug(exc, stack_info=True)
            error_msg = _('Unable to download the installer.')
        self.error = error_msg

        try:
            self.sig_ready.emit()
        except RuntimeError:
            pass

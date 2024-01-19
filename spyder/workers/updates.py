# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import logging
import os
import os.path as osp
import tempfile
import traceback

# Third party imports
from qtpy.QtCore import QObject, Signal
import requests
from requests.exceptions import ConnectionError, HTTPError, SSLError

# Local imports
from spyder import __version__
from spyder.config.base import (
    _, is_stable_version, is_pynsist, running_in_mac_app)
from spyder.config.utils import is_anaconda
from spyder.utils.conda import get_spyder_conda_channel
from spyder.utils.programs import check_version, is_module_installed

# Logger setup
logger = logging.getLogger(__name__)

CONNECT_ERROR_MSG = _(
    'Unable to connect to the Spyder update service.'
    '<br><br>Make sure your connection is working properly.'
)

HTTP_ERROR_MSG = _(
    'HTTP error {status_code} when checking for updates.'
    '<br><br>Make sure your connection is working properly,'
    'and try again later.'
)

SSL_ERROR_MSG = _(
    'SSL certificate verification failed while checking for Spyder updates.'
    '<br><br>Please contact your network administrator for assistance.'
)


class UpdateDownloadCancelledException(Exception):
    """Download for installer to update was cancelled."""
    pass


class UpdateDownloadIncompleteError(Exception):
    """Error occured while downloading file"""
    pass


class WorkerUpdates(QObject):
    """
    Worker that checks for releases using either the Anaconda
    default channels or the Github Releases page without
    blocking the Spyder user interface, in case of connection
    issues.
    """
    sig_ready = Signal()

    def __init__(self, parent, startup, version="", releases=None):
        QObject.__init__(self)
        self._parent = parent
        self.error = None
        self.latest_release = None
        self.startup = startup
        self.releases = releases

        if not version:
            self.version = __version__
        else:
            self.version = version

    def check_update_available(self):
        """
        Check if there is an update available.

        It takes as parameters the current version of Spyder and a list of
        valid cleaned releases in chronological order.
        Example: ['2.3.2', '2.3.3' ...] or with github ['2.3.4', '2.3.3' ...]
        """
        # Don't perform any check for development versions or we were unable to
        # detect releases.
        if 'dev' in self.version or not self.releases:
            return (False, self.latest_release)

        # Filter releases
        if is_stable_version(self.version):
            releases = [r for r in self.releases if is_stable_version(r)]
        else:
            releases = [r for r in self.releases
                        if not is_stable_version(r) or r in self.version]

        latest_release = releases[-1]

        return (check_version(self.version, latest_release, '<'),
                latest_release)

    def start(self):
        """Main method of the worker."""
        self.update_available = False
        self.latest_release = __version__

        error_msg = None
        pypi_url = "https://pypi.org/pypi/spyder/json"

        if is_pynsist() or running_in_mac_app():
            self.url = ('https://api.github.com/repos/'
                        'spyder-ide/spyder/releases')
        elif is_anaconda():
            channel, channel_url = get_spyder_conda_channel()

            if channel is None or channel_url is None:
                return
            elif channel == "pypi":
                self.url = pypi_url
            else:
                self.url = channel_url + '/channeldata.json'
        else:
            self.url = pypi_url

        try:
            logger.debug(f"Checking for updates from {self.url}")
            page = requests.get(self.url)
            page.raise_for_status()
            data = page.json()

            if is_pynsist() or running_in_mac_app():
                if self.releases is None:
                    self.releases = [
                        item['tag_name'].replace('v', '') for item in data
                    ]
                    self.releases = list(reversed(self.releases))
            elif is_anaconda() and self.url != pypi_url:
                if self.releases is None:
                    spyder_data = data['packages'].get('spyder')
                    if spyder_data:
                        self.releases = [spyder_data["version"]]
            else:
                if self.releases is None:
                    self.releases = [data['info']['version']]

            result = self.check_update_available()
            self.update_available, self.latest_release = result
        except SSLError as err:
            error_msg = SSL_ERROR_MSG
            logger.debug(err, stack_info=True)
        except ConnectionError as err:
            error_msg = CONNECT_ERROR_MSG
            logger.debug(err, stack_info=True)
        except HTTPError as err:
            error_msg = HTTP_ERROR_MSG.format(status_code=page.status_code)
            logger.debug(err, stack_info=True)
        except Exception as err:
            error = traceback.format_exc()
            formatted_error = error.replace('\n', '<br>').replace(' ', '&nbsp;')

            error_msg = _(
                'It was not possible to check for Spyder updates due to the '
                'following error:'
                '<br><br>'
                '<tt>{}</tt>'
            ).format(formatted_error)
            logger.debug(err, stack_info=True)

        # Don't show dialog when starting up spyder and an error occur
        if not (self.startup and error_msg is not None):
            self.error = error_msg
            try:
                self.sig_ready.emit()
            except RuntimeError:
                pass


class WorkerDownloadInstaller(QObject):
    """
    Worker that donwloads standalone installers for Windows
    and MacOS without blocking the Spyder user interface.
    """

    sig_ready = Signal(str)
    """
    Signal to inform that the worker has finished successfully.

    Parameters
    ----------
    installer_path: str
        Path where the downloaded installer is located.
    """

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
        tmpdir = tempfile.gettempdir()
        is_full_installer = (is_module_installed('numpy') or
                             is_module_installed('pandas'))
        if os.name == 'nt':
            name = 'Spyder_64bit_{}.exe'.format('full' if is_full_installer
                                                else 'lite')
        else:
            name = 'Spyder{}.dmg'.format('' if is_full_installer else '-Lite')

        url = ('https://github.com/spyder-ide/spyder/releases/latest/'
               f'download/{name}')
        dir_path = osp.join(tmpdir, 'spyder', 'updates')
        os.makedirs(dir_path, exist_ok=True)
        installer_dir_path = osp.join(
            dir_path, self.latest_release_version)
        os.makedirs(installer_dir_path, exist_ok=True)
        for file in os.listdir(dir_path):
            if file not in [__version__, self.latest_release_version]:
                remove = osp.join(dir_path, file)
                os.remove(remove)

        installer_path = osp.join(installer_dir_path, name)
        self.installer_path = installer_path

        if osp.isfile(installer_path):
            # Installer already downloaded
            logger.info(f"{installer_path} already downloaded")
            self._progress_reporter(1, 1, 1)
            return

        logger.debug(f"Downloading installer from {url} to {installer_path}")
        with requests.get(url, stream=True) as r:
            with open(installer_path, 'wb') as f:
                chunk_size = 8 * 1024
                size = -1
                size_read = 0
                chunk_num = 0

                if "content-length" in r.headers:
                    size = int(r.headers["content-length"])

                self._progress_reporter(chunk_num, chunk_size, size)

                for chunk in r.iter_content(chunk_size=chunk_size):
                    size_read += len(chunk)
                    f.write(chunk)
                    chunk_num += 1
                    self._progress_reporter(chunk_num, chunk_size, size)

                if size >= 0 and size_read < size:
                    raise UpdateDownloadIncompleteError(
                        "Download incomplete: retrieved only "
                        f"{size_read} out of {size} bytes."
                    )

    def start(self):
        """Main method of the WorkerDownloadInstaller worker."""
        error_msg = None
        try:
            self._download_installer()
        except UpdateDownloadCancelledException:
            if self.installer_path:
                os.remove(self.installer_path)
            return
        except SSLError as err:
            error_msg = SSL_ERROR_MSG
            logger.debug(err, stack_info=True)
        except ConnectionError as err:
            error_msg = CONNECT_ERROR_MSG
            logger.debug(err, stack_info=True)
        except Exception as err:
            error = traceback.format_exc()
            formatted_error = error.replace('\n', '<br>').replace(' ', '&nbsp;')

            error_msg = _(
                'It was not possible to download the installer due to the '
                'following error:'
                '<br><br>'
                '<tt>{}</tt>'
            ).format(formatted_error)
            logger.debug(err, stack_info=True)
        self.error = error_msg
        try:
            self.sig_ready.emit(self.installer_path)
        except RuntimeError:
            pass

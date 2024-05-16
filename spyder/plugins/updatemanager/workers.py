# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import logging
import os
import os.path as osp
import shutil
from time import sleep
import traceback

# Third party imports
from packaging.version import parse
from qtpy.QtCore import QObject, Signal
import requests
from requests.exceptions import ConnectionError, HTTPError, SSLError

# Local imports
from spyder import __version__
from spyder.config.base import _, is_stable_version, is_conda_based_app
from spyder.config.utils import is_anaconda
from spyder.utils.conda import get_spyder_conda_channel
from spyder.utils.programs import check_version

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


class BaseWorker(QObject):
    """Base worker class for the updater"""

    sig_ready = Signal()
    """Signal to inform that the worker has finished."""

    sig_exception_occurred = Signal(dict)
    """
    Send untracked exceptions to the error reporter

    Parameters
    ----------
    error_data: dict
        The dictionary containing error data. The allowed keys are:
        text: str
            Error text to display. This may be a translated string or
            formatted exception string.
        is_traceback: bool
            Whether `text` is plain text or an error traceback.
        repo: str
            Customized display of repo in GitHub error submission report.
        title: str
            Customized display of title in GitHub error submission report.
        label: str
            Customized content of the error dialog.
        steps: str
            Customized content of the error dialog.
    """


class WorkerUpdate(BaseWorker):
    """
    Worker that checks for releases using either the Anaconda
    default channels or the Github Releases page without
    blocking the Spyder user interface, in case of connection
    issues.
    """

    def __init__(self, stable_only):
        super().__init__()
        self.stable_only = stable_only
        self.latest_release = None
        self.releases = None
        self.update_available = False
        self.error = None
        self.channel = None

    def _check_update_available(self):
        """Checks if there is an update available from releases."""
        # Filter releases
        releases = self.releases.copy()
        if self.stable_only:
            # Only use stable releases
            releases = [r for r in releases if is_stable_version(r)]
        logger.debug(f"Available versions: {self.releases}")

        self.latest_release = releases[-1] if releases else __version__
        self.update_available = check_version(
            __version__,
            self.latest_release,
            '<'
        )

        logger.debug(f"Update available: {self.update_available}")
        logger.debug(f"Latest release: {self.latest_release}")

    def start(self):
        """Main method of the worker."""
        self.error = None
        self.latest_release = None
        self.update_available = False
        error_msg = None
        pypi_url = "https://pypi.org/pypi/spyder/json"
        github_url = 'https://api.github.com/repos/spyder-ide/spyder/releases'

        if is_conda_based_app():
            url = github_url
        elif is_anaconda():
            self.channel, channel_url = get_spyder_conda_channel()

            if self.channel is None or channel_url is None:
                logger.debug(
                    f"channel = {self.channel}; channel_url = {channel_url}. "
                )

                # Spyder installed in development mode, use GitHub
                url = github_url
            elif self.channel == "pypi":
                url = pypi_url
            else:
                url = channel_url + '/channeldata.json'
        else:
            url = pypi_url

        logger.info(f"Checking for updates from {url}")
        try:
            page = requests.get(url)
            page.raise_for_status()
            data = page.json()

            if self.releases is None:
                if url == github_url:
                    self.releases = [
                        item['tag_name'].replace('v', '') for item in data
                    ]
                elif url == pypi_url:
                    self.releases = [data['info']['version']]
                else:
                    # Conda type url
                    spyder_data = data['packages'].get('spyder')
                    if spyder_data:
                        self.releases = [spyder_data["version"]]
            self.releases.sort(key=parse)

            self._check_update_available()
        except SSLError as err:
            error_msg = SSL_ERROR_MSG
            logger.warning(err, exc_info=err)
        except ConnectionError as err:
            error_msg = CONNECT_ERROR_MSG
            logger.warning(err, exc_info=err)
        except HTTPError as err:
            error_msg = HTTP_ERROR_MSG.format(status_code=page.status_code)
            logger.warning(err, exc_info=err)
        except Exception as err:
            # Send untracked errors to our error reporter
            error_data = dict(
                text=traceback.format_exc(),
                is_traceback=True,
                title="Error when checking for updates",
            )
            self.sig_exception_occurred.emit(error_data)
            logger.error(err, exc_info=err)
        finally:
            self.error = error_msg

            # At this point we **must** emit the signal below so that the
            # "Check for updates" action in the Help menu is enabled again
            # after the check has finished (it's disabled while the check is
            # running).
            try:
                self.sig_ready.emit()
            except RuntimeError:
                pass


class WorkerDownloadInstaller(BaseWorker):
    """
    Worker that donwloads standalone installers for Windows, macOS,
    and Linux without blocking the Spyder user interface.
    """

    sig_download_progress = Signal(int, int)
    """
    Signal to send the download progress.

    Parameters
    ----------
    current_value: int
        Size of the data downloaded until now.
    total: int
        Total size of the file expected to be downloaded.
    """

    def __init__(self, latest_release, installer_path, installer_size_path):
        super().__init__()
        self.latest_release = latest_release
        self.installer_path = installer_path
        self.installer_size_path = installer_size_path
        self.error = None
        self.cancelled = False
        self.paused = False

    def _progress_reporter(self, progress, total_size):
        """Calculate download progress and notify."""
        self.sig_download_progress.emit(progress, total_size)

        while self.paused and not self.cancelled:
            sleep(0.5)

        if self.cancelled:
            raise UpdateDownloadCancelledException()

    def _download_installer(self):
        """Donwload Spyder installer."""
        url = (
            'https://github.com/spyder-ide/spyder/releases/download/'
            f'v{self.latest_release}/{osp.basename(self.installer_path)}'
        )
        logger.info(f"Downloading installer from {url} "
                    f"to {self.installer_path}")

        dirname = osp.dirname(self.installer_path)
        os.makedirs(dirname, exist_ok=True)

        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            size = -1
            if "content-length" in r.headers:
                size = int(r.headers["content-length"])
            self._progress_reporter(0, size)

            with open(self.installer_path, 'wb') as f:
                chunk_size = 8 * 1024
                size_read = 0
                for chunk in r.iter_content(chunk_size=chunk_size):
                    size_read += len(chunk)
                    f.write(chunk)
                    self._progress_reporter(size_read, size)

        if size_read == size:
            logger.info('Download successfully completed.')
            with open(self.installer_size_path, "w") as f:
                f.write(str(size))
        else:
            raise UpdateDownloadIncompleteError(
                "Download incomplete: retrieved only "
                f"{size_read} out of {size} bytes."
            )

    def _clean_installer_path(self):
        """Remove downloaded file"""
        installer_dir = osp.dirname(self.installer_path)
        if osp.exists(installer_dir):
            try:
                shutil.rmtree(installer_dir)
            except OSError as err:
                logger.debug(err, stack_info=True)

    def start(self):
        """Main method of the worker."""
        error_msg = None
        try:
            self._download_installer()
        except UpdateDownloadCancelledException:
            logger.info("Download cancelled")
            self._clean_installer_path()
        except SSLError as err:
            error_msg = SSL_ERROR_MSG
            logger.warning(err, exc_info=err)
        except ConnectionError as err:
            error_msg = CONNECT_ERROR_MSG
            logger.warning(err, exc_info=err)
        except Exception as err:
            error = traceback.format_exc()
            formatted_error = (
                error.replace('\n', '<br>')
                .replace(' ', '&nbsp;')
            )

            error_msg = _(
                'It was not possible to download the installer due to the '
                'following error:'
                '<br><br>'
                '<tt>{}</tt>'
            ).format(formatted_error)
            logger.warning(err, exc_info=err)
            self._clean_installer_path()
        finally:
            self.error = error_msg

            try:
                self.sig_ready.emit()
            except RuntimeError:
                pass

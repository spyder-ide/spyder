# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from __future__ import annotations  # noqa; required for typing in Python 3.8
from datetime import datetime as dt
import logging
import os
import os.path as osp
import platform
import shutil
import sys
from time import sleep
import traceback
from typing import TypedDict
from zipfile import ZipFile

# Third party imports
from packaging.version import parse, Version
from qtpy.QtCore import QObject, Signal
import requests
from requests.exceptions import ConnectionError, HTTPError, SSLError
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
from spyder import __version__
from spyder.config.base import _, is_conda_based_app, running_in_ci
from spyder.utils.conda import get_spyder_conda_channel

# Logger setup
logger = logging.getLogger(__name__)

CURRENT_VERSION = parse(__version__)

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

OS_ERROR_MSG = _(
    "An error occurred while checking for Spyder updates, possibly related to "
    "your operating system configuration or file access.<br><br>If you're not "
    "sure what to do about it, you can disable checking for updates below. "
    "<br><br>The error was:<br><br><i>{error}</i>"
)

def _rate_limits(page):
    """Log rate limits for GitHub.com"""
    if page.headers.get('Server') != 'GitHub.com':
        return

    xrlr = dt.utcfromtimestamp(int(page.headers['X-RateLimit-Reset']))
    msg_items = [
        "Rate Limits:",
        f"Resource:  {page.headers['X-RateLimit-Resource']}",
        f"Reset:     {xrlr}",
        f"Limit:     {page.headers['X-RateLimit-Limit']:>5s}",
        f"Used:      {page.headers['X-RateLimit-Used']:>5s}",
        f"Remaining: {page.headers['X-RateLimit-Remaining']:>5s}",
    ]
    logger.debug("\n\t".join(msg_items))


class UpdateType:
    """Enum with the different update types."""

    Major = "major"
    Minor = "minor"
    Micro = "micro"


class AssetInfo(TypedDict):
    """Schema for asset information."""

    # Filename with extension of the release asset to download.
    filename: str

    # Type of update
    update_type: UpdateType

    # Download URL for the asset.
    url: str


def get_asset_info(release: str | Version) -> AssetInfo:
    """
    Get the name, update type, and download URL for the asset of the given
    release.

    Parameters
    ----------
    release: str | packaging.version.Version
        Release version

    Returns
    -------
    asset_info: AssetInfo
        Information about the asset.
    """
    if isinstance(release, str):
        release = parse(release)

    if CURRENT_VERSION.major < release.major:
        update_type = UpdateType.Major
    elif CURRENT_VERSION.minor < release.minor:
        update_type = UpdateType.Minor
    else:
        update_type = UpdateType.Micro

    mach = platform.machine().lower().replace("amd64", "x86_64")

    if update_type == UpdateType.Major or not is_conda_based_app():
        if os.name == 'nt':
            plat, ext = 'Windows', 'exe'
        if sys.platform == 'darwin':
            plat, ext = 'macOS', 'pkg'
        if sys.platform.startswith('linux'):
            plat, ext = 'Linux', 'sh'
        name = f'Spyder-{plat}-{mach}.{ext}'
    else:
        name = 'spyder-conda-lock.zip'

    url = (
        'https://github.com/spyder-ide/spyder/releases/download/'
        f'v{release}/{name}'
    )

    return AssetInfo(filename=name, update_type=update_type, url=url)


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
        self.update_available = False
        self.error = None
        self.checkbox = False
        self.channel = None

    def _check_update_available(
        self,
        releases: list[Version],
        github: bool = True
    ):
        """Checks if there is an update available from releases."""
        if self.stable_only:
            # Only use stable releases
            releases = [r for r in releases if not r.is_prerelease]
        logger.debug(f"Available versions: {releases}")

        latest_release = max(releases) if releases else CURRENT_VERSION
        update_available = CURRENT_VERSION < latest_release

        logger.debug(f"Latest release: {latest_release}")
        logger.debug(f"Update available: {update_available}")

        # Check if the asset is available for download.
        # If the asset is not available, then check the next latest
        # release, and so on until either a new asset is available or there
        # is no update available.
        if github:
            asset_available = False
            while update_available and not asset_available:
                asset_info = get_asset_info(latest_release)
                page = requests.head(asset_info['url'])
                if page.status_code == 302:
                    # The asset is found
                    logger.debug(f"Asset available for url: {page.url}")
                    asset_available = True
                else:
                    # The asset is not available
                    logger.debug(
                        "Asset not available: "
                        f"{page.status_code} Client Error: {page.reason} "
                        f"for url: {page.url}"
                    )
                    asset_available = False
                    releases.remove(latest_release)

                    latest_release = max(releases) if releases else CURRENT_VERSION
                    update_available = CURRENT_VERSION < latest_release

                    logger.debug(f"Latest release: {latest_release}")
                    logger.debug(f"Update available: {update_available}")

        self.latest_release = latest_release
        self.update_available = update_available

    def start(self):
        """Main method of the worker."""
        self.error = None
        self.latest_release = None
        self.update_available = False
        error_msg = None
        url = 'https://api.github.com/repos/spyder-ide/spyder/releases'

        if not is_conda_based_app():
            self.channel = "pypi"  # Default channel if not conda
            if is_conda_env(sys.prefix):
                self.channel, channel_url = get_spyder_conda_channel()

            # If Spyder is installed from defaults channel (pkgs/main), then
            # use that channel to get updates. The defaults channel can be far
            # behind our latest release.
            if self.channel == "pkgs/main":
                url = channel_url + '/channeldata.json'
        github = "api.github.com" in url

        headers = {}
        token = os.getenv('GITHUB_TOKEN')
        if running_in_ci() and token:
            headers.update(Authorization=f"Bearer {token}")

        logger.info(f"Checking for updates from {url}")
        try:
            page = requests.get(url, headers=headers)
            _rate_limits(page)
            page.raise_for_status()

            data = page.json()
            if github:
                # Github url
                releases = [parse(item['tag_name']) for item in data]
            else:
                # Conda pkgs/main url
                spyder_data = data['packages'].get('spyder')
                if spyder_data:
                    releases = [parse(spyder_data["version"])]
            releases.sort()

            self._check_update_available(releases, github)

        except SSLError as err:
            error_msg = SSL_ERROR_MSG
            logger.warning(err, exc_info=err)
        except ConnectionError as err:
            error_msg = CONNECT_ERROR_MSG
            logger.warning(err, exc_info=err)
        except HTTPError as err:
            error_msg = HTTP_ERROR_MSG.format(status_code=page.status_code)
            logger.warning(err, exc_info=err)
        except OSError as err:
            error_msg = OS_ERROR_MSG.format(error=err)
            self.checkbox = True
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
        asset_info = get_asset_info(self.latest_release)
        url = asset_info['url']
        logger.info(f"Downloading {url} to {self.installer_path}")

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

            if self.installer_path.endswith('.zip'):
                with ZipFile(self.installer_path, 'r') as f:
                    f.extractall(dirname)
        else:
            raise UpdateDownloadIncompleteError(
                "Download incomplete: retrieved only "
                f"{size_read} out of {size} bytes."
            )

    def _clean_installer_dir(self):
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
            self._clean_installer_dir()
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
            self._clean_installer_dir()
        finally:
            self.error = error_msg

            try:
                self.sig_ready.emit()
            except RuntimeError:
                pass

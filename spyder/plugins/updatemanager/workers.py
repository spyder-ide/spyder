# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from __future__ import annotations  # noqa; required for typing in Python 3.8
from glob import glob
from hashlib import sha256
import logging
import os
import os.path as osp
import platform
import shutil
import subprocess
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
from spyder.config.base import (
    _,
    is_conda_based_app,
    running_in_ci,
    running_under_pytest,
)
from spyder.plugins.updatemanager.utils import get_updater_info
from spyder.utils.conda import get_spyder_conda_channel, find_conda
from spyder.utils.programs import get_temp_dir

# Logger setup
logger = logging.getLogger(__name__)

CURRENT_VERSION = parse(__version__)

UPDATER_PATH, UPDATER_VERSION = get_updater_info()
UPDATER_VERSION = parse(UPDATER_VERSION)

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

GH_HEADERS = {"Accept": "application/vnd.github+json"}
_token = os.getenv('GITHUB_TOKEN')
if running_in_ci() and _token:
    GH_HEADERS.update(Authorization=f"Bearer {_token}")


class UpdateType:
    """Enum with the different update types."""

    Major = "major"
    Minor = "minor"
    Micro = "micro"


class AssetInfo(TypedDict):
    """Schema for asset information."""

    # Version
    version: Version

    # Filename with extension of the release asset to download.
    filename: str

    # Type of update
    update_type: UpdateType

    # Download URL for the asset.
    url: str

    # Checksum url
    checksum_url: str

    # File sha256 checksum
    checksum: str


def get_github_releases(
    tags: str | tuple[str] | None = None,
    updater: bool = False
) -> dict[Version, dict]:
    """
    Get Github release information

    Parameters
    ----------
    tags : str | tuple[str] | (None)
        If tags is provided, only release information for the requested tags
        is retrieved. Otherwise, the most recent 20 releases are retrieved.
        This is only used to retrieve a known set of releases for unit testing.
    updater : bool (False)
        Whether to get Spyder-updater releases (True) or Spyder releases
        (False).

    Returns
    -------
    releases : dict[packaging.version.Version, dict]
        Dictionary of release information.
    """
    url = "https://api.github.com/repos/{}/releases".format(
        "spyder-ide/spyder-updater" if updater else "spyder-ide/spyder"
    )

    if tags is None:
        # Get the most recent releases
        url += f"?per_page={100 if running_under_pytest() else 20}&page=1"
        logger.info(f"Getting release info from {url}")
        page = requests.get(url, headers=GH_HEADERS)
        page.raise_for_status()
        data = page.json()
    else:
        # Get specified releases
        tags = [tags] if isinstance(tags, str) else tags
        url += "/tags/"

        data = []
        with requests.Session() as session:
            session.headers = GH_HEADERS
            logger.info(f"Getting release info for {tags}")
            for tag in tags:
                _url = url + tag
                page = session.get(_url)
                page.raise_for_status()
                data.append(page.json())

    return {parse(item['tag_name']): item for item in data}


def get_asset_checksum(url: str, name: str) -> str | None:
    """
    Get the checksum for the provided asset.

    Parameters
    ----------
    url : str
        Url to the checksum asset
    name : str
        Name of the asset for which to obtain the checksum

    Returns
    -------
    checksum : str | None
        Checksum for the provided asset. None is returned if the checksum is
        not available for the provided asset name.
    """
    logger.info(f"Getting checksum from {url}")
    page = requests.get(url, headers=GH_HEADERS)
    page.raise_for_status()

    digest = page.text.strip().split("\n")
    data = {k: v for v, k in [item.split() for item in digest]}
    checksum = data.get(name, None)

    logger.info(f"Checksum for {name}: {checksum}")

    return checksum


def get_asset_info(release_info: dict) -> AssetInfo | None:
    """
    Get the version, name, update type, download URL, and size for the asset
    of the given release.

    Parameters
    ----------
    release_info: dict
        Release information from Github for a single release

    Returns
    -------
    asset_info: AssetInfo | None
        Information about the asset.
    """
    current_version = CURRENT_VERSION
    checksum_name = "Spyder-checksums.txt"

    updater = "spyder-updater" in release_info["url"]
    if updater:
        current_version = UPDATER_VERSION
        checksum_name = "Spyder-Updater-checksums.txt"

    release = parse(release_info["tag_name"])

    if current_version.major < release.major or not is_conda_based_app():
        update_type = UpdateType.Major
    elif current_version.minor < release.minor:
        update_type = UpdateType.Minor
    else:
        update_type = UpdateType.Micro

    if updater or update_type != UpdateType.Major:
        ext = ".zip"
    else:
        ext = platform.machine().lower().replace("amd64", "x86_64")
        if os.name == 'nt':
            ext += '.exe'
        if sys.platform == 'darwin':
            ext += '.pkg'
        if sys.platform.startswith('linux'):
            ext += '.sh'

    asset_info = AssetInfo(version=release, update_type=update_type)
    for asset in release_info["assets"]:
        if asset["name"].endswith(ext):
            asset_info.update(
                filename=asset["name"],
                url=asset["browser_download_url"]
            )
        if asset["name"] == checksum_name:
            asset_info.update(
                checksum_url=asset["browser_download_url"]
            )
        if asset_info.get("url") and asset_info.get("checksum_url"):
            break

    if asset_info.get("url") is None or asset_info.get("checksum_url") is None:
        # Both assets are required
        asset_info = None

    return asset_info


def _check_asset_available(
    releases: dict[Version, dict], updater: bool = False
) -> AssetInfo | None:
    current_version = UPDATER_VERSION if updater else CURRENT_VERSION

    latest_release = max(releases) if releases else current_version
    update_available = current_version < latest_release
    asset_info = None

    logger.debug(f"Latest release: {latest_release}")
    logger.debug(f"Update available: {update_available}")

    # Check if the asset is available for download.
    # If the asset is not available, then check the next latest
    # release, and so on until either a new asset is available or there
    # is no update available.
    while update_available:
        asset_info = get_asset_info(releases.get(latest_release))

        if asset_info is not None:
            # The asset is available, now get checksum.
            checksum = get_asset_checksum(
                asset_info["checksum_url"], asset_info["filename"]
            )
            if checksum is not None:
                asset_info.update(checksum=checksum)
                logger.debug(f"Asset available: {latest_release}")
                break
            else:
                asset_info = None

        # The asset is not available
        logger.debug(f"Asset not available: {latest_release}")
        releases.pop(latest_release)

        latest_release = max(releases) if releases else current_version
        update_available = current_version < latest_release

        logger.debug(f"Latest release: {latest_release}")
        logger.debug(f"Update available: {update_available}")

    return asset_info


def validate_download(file: str, checksum: str) -> bool:
    """
    Compute the sha256 checksum of the provided file and compare against
    the provided checksum.

    Parameters
    ----------
    file : str
        Full path to the file to be verified.
    checksum : str
        sha256 checksum to match against the computed checksum.

    Returns
    -------
    valid : bool
        True if the file's computed checksum matches the provided checksum,
        False otherwise.
    """
    with open(file, "rb") as f:
        _checksum = sha256()
        while chunk := f.read(8192):
            _checksum.update(chunk)

    valid = checksum == _checksum.hexdigest()
    logger.debug(f"Valid {file}: {valid}")

    return valid


class UpdateDownloadCancelledException(Exception):
    """Download for installer to update was cancelled."""
    pass


class UpdateDownloadError(Exception):
    """Error occured while downloading file"""
    pass


class BaseWorker(QObject):
    """Base worker class for the updater"""

    sig_ready = Signal(bool)
    """
    Signal to inform that the worker has finished.

    Parameters
    ----------
    success : bool
        Whether the worker was successful (True) or not (False).
    """

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
        self.asset_info = None
        self.error = None
        self.checkbox = False
        self.channel = None

    def _check_update_available(self, release: Version | None = None):
        """
        Check if there is an update available.

        Releases are obtained from Github and compared to the current Spyder
        version to determine if an update is available. The Github release
        asset and checksum must be available in order for the release to be
        considered.

        Parameters
        ----------
        release : packaging.version.Version | (None)
            If provided, limit possible releases on Github to this release
            or less.
        """

        # Get asset info from Github
        releases = get_github_releases()

        if release is not None:
            # Limit Github releases to consider
            releases = {k: v for k, v in releases.items() if k <= release}

        if self.stable_only:
            # Only consider stable releases
            releases = {
                k: v for k, v in releases.items() if not k.is_prerelease
            }
        logger.debug(f"Available releases: {sorted(releases)}")

        self.asset_info = _check_asset_available(releases)

    def start(self):
        """Main method of the worker."""
        url = None
        if not is_conda_based_app():
            self.channel = "pypi"  # Default channel if not conda
            if is_conda_env(sys.prefix):
                self.channel, url = get_spyder_conda_channel()

            if self.channel == "pypi":
                url = "https://pypi.python.org/pypi/spyder/json"
            else:
                url += '/channeldata.json'

        try:
            release = None
            if url is not None:
                # Limit the releases on Github that we consider to those less
                # than or equal to what is also available on the conda/pypi
                # channel
                logger.info(f"Getting release from {url}")
                page = requests.get(url)
                page.raise_for_status()
                data = page.json()

                if self.channel == "pypi":
                    releases = [
                        parse(k) for k in data["releases"].keys()
                        if not parse(k).is_prerelease
                    ]
                    release = max(releases)
                else:
                    # Conda pkgs/main or conda-forge url
                    spyder_data = data['packages'].get('spyder')
                    if spyder_data:
                        release = parse(spyder_data["version"])

            self._check_update_available(release)

        except SSLError as err:
            self.error = SSL_ERROR_MSG
            logger.warning(err, exc_info=err)
        except ConnectionError as err:
            self.error = CONNECT_ERROR_MSG
            logger.warning(err, exc_info=err)
        except HTTPError as err:
            status_code = err.response.status_code
            self.error = HTTP_ERROR_MSG.format(status_code=status_code)
            logger.warning(err, exc_info=err)
        except OSError as err:
            self.error = OS_ERROR_MSG.format(error=err)
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
            # At this point we **must** emit the signal below so that the
            # "Check for updates" action in the Help menu is enabled again
            # after the check has finished (it's disabled while the check is
            # running).
            try:
                self.sig_ready.emit(self.error is None)
            except RuntimeError:
                pass


class WorkerUpdateUpdater(BaseWorker):
    """
    Worker that checks and updates Spyder-updater without blocking
    the Spyder user interface.
    """

    def __init__(self, stable_only):
        super().__init__()
        self.stable_only = stable_only
        self.asset_info = None
        self.installer_path = None
        self.error = None

    def _check_asset_available(self):
        """Checks if there is an update available for the Updater."""

        # Get release info from Github
        releases = get_github_releases(updater=True)

        if self.stable_only:
            # Only use stable releases
            releases = {
                k: v for k, v in releases.items() if not k.is_prerelease
            }
        logger.debug(f"Available releases: {sorted(releases)}")

        self.asset_info = _check_asset_available(releases, updater=True)

    def _clean_installer_dir(self):
        """Remove downloaded file"""
        installer_dir = osp.dirname(self.installer_path)
        if osp.exists(installer_dir):
            try:
                shutil.rmtree(installer_dir)
            except OSError as err:
                logger.debug(err, stack_info=True)

    def _download_asset(self):
        """Download Updater lock file"""
        self.installer_path = osp.join(
            get_temp_dir(),
            "updates",
            "spyder-updater",
            str(self.asset_info["version"]),
            self.asset_info["filename"],
        )

        if (
            osp.exists(self.installer_path)
            and validate_download(
                self.installer_path, self.asset_info["checksum"]
            )
        ):
            logger.debug(f"{self.installer_path} already downloaded.")
            return

        self._clean_installer_dir()
        dirname = osp.dirname(self.installer_path)
        os.makedirs(dirname, exist_ok=True)

        url = self.asset_info["url"]
        logger.info(f"Downloading {url} to {self.installer_path}")

        page = requests.get(url, headers=GH_HEADERS)
        page.raise_for_status()
        with open(self.installer_path, 'wb') as f:
            f.write(page.content)

        if validate_download(self.installer_path, self.asset_info["checksum"]):
            logger.info('Download successfully completed.')
            with ZipFile(self.installer_path, 'r') as f:
                f.extractall(dirname)
        else:
            raise UpdateDownloadError("Download failed!")

    def _install_update(self):
        """Install or update Spyder-updater environment."""
        dirname = osp.dirname(self.installer_path)

        if os.name == "nt":
            plat = "win-64"
        elif sys.platform == "darwin":
            plat = "osx-arm64" if platform.machine() == "arm64" else "osx-64"
        else:
            plat = "linux-64"
        spy_updater_lock = osp.join(dirname, f"conda-updater-{plat}.lock")
        spy_updater_conda = glob(osp.join(dirname, "spyder-updater*.conda"))[0]

        conda_exe = find_conda()
        conda_cmd = "update" if UPDATER_VERSION > parse("0.0.0") else "create"
        env_path = osp.join(osp.dirname(sys.prefix), "spyder-updater")
        cmd = [
            # Update spyder-updater environment
            conda_exe,
            conda_cmd, "--yes",
            "--prefix", env_path,
            "--file", spy_updater_lock,
            "&&",
            # Update spyder-updater
            conda_exe,
            "install", "--yes",
            "--prefix", env_path,
            "--no-deps",
            "--force-reinstall",
            spy_updater_conda
        ]

        logger.debug(f"""Conda command for the updater: '{" ".join(cmd)}'""")
        proc = subprocess.run(
            " ".join(cmd), shell=True, capture_output=True, text=True
        )
        proc.check_returncode()

    def start(self):
        """Main method of the worker."""
        try:
            self._check_asset_available()
            if self.asset_info is None and UPDATER_VERSION == parse("0.0.0"):
                raise RuntimeError(
                    "Spyder-updater is not installed and "
                    "not available for download!"
                )
            elif self.asset_info is not None:
                self._download_asset()
                self._install_update()
        except Exception as err:
            # Send untracked errors to our error reporter
            self.error = str(err)
            error_data = dict(
                text=traceback.format_exc(),
                is_traceback=True,
                title=_("Error when updating Spyder-updater"),
            )
            self.sig_exception_occurred.emit(error_data)
            logger.error(err, exc_info=err)
        finally:
            # At this point we **must** emit the signal below so that the
            # "Check for updates" action in the Help menu is enabled again
            # after the check has finished (it's disabled while the check is
            # running).
            try:
                self.sig_ready.emit(self.error is None)
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

    def __init__(self, asset_info, installer_path):
        super().__init__()
        self.asset_info = asset_info
        self.installer_path = installer_path
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
        url = self.asset_info["url"]
        logger.info(f"Downloading {url} to {self.installer_path}")

        self._clean_installer_dir()
        dirname = osp.dirname(self.installer_path)
        os.makedirs(dirname, exist_ok=True)

        with requests.get(url, stream=True) as r:
            r.raise_for_status()

            size = int(r.headers["content-length"])
            self._progress_reporter(0, size)

            with open(self.installer_path, 'wb') as f:
                chunk_size = 8 * 1024
                size_read = 0
                for chunk in r.iter_content(chunk_size=chunk_size):
                    size_read += len(chunk)
                    f.write(chunk)
                    self._progress_reporter(size_read, size)

        if validate_download(self.installer_path, self.asset_info["checksum"]):
            logger.info('Download successfully completed.')

            if self.installer_path.endswith('.zip'):
                with ZipFile(self.installer_path, 'r') as f:
                    f.extractall(dirname)
        else:
            raise UpdateDownloadError("Download failed!")

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
        try:
            self._download_installer()
        except UpdateDownloadCancelledException:
            logger.info("Download cancelled")
            self._clean_installer_dir()
        except SSLError as err:
            self.error = SSL_ERROR_MSG
            logger.warning(err, exc_info=err)
        except ConnectionError as err:
            self.error = CONNECT_ERROR_MSG
            logger.warning(err, exc_info=err)
        except Exception as err:
            error = traceback.format_exc()
            formatted_error = (
                error.replace('\n', '<br>')
                .replace(' ', '&nbsp;')
            )

            self.error = _(
                'It was not possible to download the installer due to the '
                'following error:'
                '<br><br>'
                '<tt>{}</tt>'
            ).format(formatted_error)
            logger.warning(err, exc_info=err)
            self._clean_installer_dir()
        finally:
            try:
                self.sig_ready.emit(self.error is None)
            except RuntimeError:
                pass

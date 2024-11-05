# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
import logging
from packaging.version import parse

import pytest

from spyder.config.base import running_in_ci
from spyder.plugins.updatemanager import workers
from spyder.plugins.updatemanager.workers import (
    UpdateType, get_asset_info, WorkerUpdate, HTTP_ERROR_MSG
)
from spyder.plugins.updatemanager.widgets import update
from spyder.plugins.updatemanager.widgets.update import UpdateManagerWidget

logging.basicConfig()


@pytest.fixture(autouse=True)
def capture_logging(caplog):
    caplog.set_level(10, "spyder.plugins.updatemanager")


@pytest.fixture
def worker():
    return WorkerUpdate(None)


# ---- Test WorkerUpdate

@pytest.mark.parametrize("version", ["1.0.0", "1000.0.0"])
@pytest.mark.parametrize(
    "channel", [
        ("pkgs/main", "https://repo.anaconda.com/pkgs/main"),
        ("conda-forge", "https://conda.anaconda.org/conda-forge"),
    ]
)
def test_updates(qtbot, mocker, caplog, version, channel):
    """
    Test whether or not we offer updates according to the current Spyder
    version and package installation channel.

    Uses UpdateManagerWidget in order to also test QThread.
    """
    mocker.patch.object(update, "__version__", new=version)
    # Do not execute start_update after check_update completes.
    mocker.patch.object(
        UpdateManagerWidget, "start_update", new=lambda x: None
    )
    mocker.patch.object(workers, "CURRENT_VERSION", new=parse(version))
    mocker.patch.object(
        workers, "get_spyder_conda_channel", return_value=channel
    )

    with caplog.at_level(logging.DEBUG, logger='spyder.plugins.updatemanager'):
        # Capture >=DEBUG logging messages for spyder.plugins.updatemanager
        # while checking for updates. Messages will be reported at the end
        # of the pytest run, and only if this test fails.
        um = UpdateManagerWidget(None)
        um.start_check_update()
        qtbot.waitUntil(um.update_thread.isFinished)

    if um.update_worker.error:
        # Possible 403 error - rate limit error, was encountered while doing
        # the tests
        # Check error message corresponds to the status code and exit early to
        # prevent failing the test
        assert um.update_worker.error == HTTP_ERROR_MSG.format(status_code="403")
        return

    assert not um.update_worker.error

    update_available = um.update_worker.update_available
    if version.split('.')[0] == '1':
        assert update_available
    else:
        assert not update_available


@pytest.mark.parametrize("release", ["6.0.0", "6.0.0b3"])
@pytest.mark.parametrize("version", ["4.0.0a1", "4.0.0"])
@pytest.mark.parametrize("stable_only", [True, False])
def test_update_non_stable(qtbot, mocker, version, release, stable_only):
    """Test we offer unstable updates."""
    mocker.patch.object(workers, "CURRENT_VERSION", new=parse(version))

    release = parse(release)
    worker = WorkerUpdate(stable_only)
    worker._check_update_available([release])

    if release.is_prerelease and stable_only:
        assert not worker.update_available
    else:
        assert worker.update_available


@pytest.mark.parametrize("version", ["4.0.0", "6.0.0"])
def test_update_no_asset(qtbot, mocker, version):
    """Test update availability when asset is not available"""
    mocker.patch.object(workers, "CURRENT_VERSION", new=parse(version))

    releases = [parse("6.0.1"), parse("6.100.0")]
    worker = WorkerUpdate(True)
    worker._check_update_available(releases)

    # For both values of version, there should be an update available
    # However, the available version should be 6.0.1, since there is
    # no asset for 6.100.0
    assert worker.update_available
    assert worker.latest_release == releases[0]


@pytest.mark.parametrize(
    "release,update_type",
    [
        ("6.0.1", UpdateType.Micro),
        ("6.1.0", UpdateType.Minor),
        ("7.0.0", UpdateType.Major)
    ]
)
@pytest.mark.parametrize("app", [True, False])
def test_get_asset_info(qtbot, mocker, release, update_type, app):
    mocker.patch.object(workers, "CURRENT_VERSION", new=parse("6.0.0"))
    mocker.patch.object(workers, "is_conda_based_app", return_value=app)

    info = get_asset_info(release)
    assert info['update_type'] == update_type

    if update_type == "major" or not app:
        assert info['url'].endswith(('.exe', '.pkg', '.sh'))
        assert info['filename'].endswith(('.exe', '.pkg', '.sh'))
    else:
        assert info['url'].endswith(".zip")
        assert info['filename'].endswith(".zip")


# ---- Test WorkerDownloadInstaller

@pytest.mark.skip(reason="Re-enable when alternate repo is available")
@pytest.mark.skipif(not running_in_ci(), reason="Download only in CI")
def test_download(qtbot, mocker):
    """
    Test download spyder installer.

    Uses UpdateManagerWidget in order to also test QThread.
    """
    um = UpdateManagerWidget(None)
    um.latest_release = "6.0.0a2"
    um._set_installer_path()

    # Do not execute _start_install after download completes.
    mocker.patch.object(
        UpdateManagerWidget, "_confirm_install", new=lambda x: None
    )

    um._start_download()
    qtbot.waitUntil(um.download_thread.isFinished, timeout=60000)

    assert os.path.exists(um.installer_path)


if __name__ == "__main__":
    pytest.main()

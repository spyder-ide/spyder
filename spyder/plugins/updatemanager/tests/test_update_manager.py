# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
from functools import lru_cache
import logging
from packaging.version import parse

import pytest

from spyder.config.base import running_in_ci
from spyder.plugins.updatemanager import workers
from spyder.plugins.updatemanager.workers import (
    UpdateType, get_asset_info, WorkerUpdate
)
from spyder.plugins.updatemanager.widgets import update
from spyder.plugins.updatemanager.widgets.update import UpdateManagerWidget

logging.basicConfig()

__get_github_releases = workers.get_github_releases


@lru_cache()
def _get_github_releases():
    return __get_github_releases(
        ("v6.0.0b3", "v6.0.0rc1", "v6.0.7", "v6.1.0a3")
    )


workers.get_github_releases = _get_github_releases
workers.get_github_releases()  # Run once to cache result for tests


@pytest.fixture(autouse=True)
def capture_logging(caplog):
    # Capture >=DEBUG logging messages for spyder.plugins.updatemanager.
    # Messages will be reported at the end of the pytest run for failed tests.
    caplog.set_level(10, "spyder.plugins.updatemanager")


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

    um = UpdateManagerWidget(None)
    um.start_check_update()
    qtbot.waitUntil(um.update_thread.isFinished, timeout=10000)

    if version.split('.')[0] == '1':
        assert um.update_worker.asset_info is not None
    else:
        assert um.update_worker.asset_info is None


@pytest.mark.parametrize("version", ["5.5.6", "6.0.0a1"])
@pytest.mark.parametrize(
    "stable_only,release,expected",
    [
        (True, "6.0.7", "6.0.7"),
        (True, "6.1.0a3", "6.0.7"),
        (True, "6.0.0rc1", None),
        (False, "6.0.7", "6.0.7"),
        (False, "6.0.0rc1", "6.0.0rc1")
    ]
)
def test_update_non_stable(
    qtbot, mocker, version, stable_only, release, expected
):
    """Test we offer unstable updates."""
    mocker.patch.object(workers, "CURRENT_VERSION", new=parse(version))

    worker = WorkerUpdate(stable_only)
    release = parse(release)

    worker._check_update_available(release)

    if expected is not None:
        expected = parse(expected)
        assert worker.asset_info["version"] == expected
    else:
        assert worker.asset_info is None


def test_update_no_asset(qtbot, mocker):
    """Test update availability when asset is not available"""
    mocker.patch.object(workers, "CURRENT_VERSION", new=parse("6.0.0b2"))
    mocker.patch.object(workers, "is_conda_based_app", return_value=True)

    worker = WorkerUpdate(False)

    # 6.0.0b3 does not have correct minor/micro update asset
    worker._check_update_available(parse("6.0.0b3"))
    assert worker.asset_info is None

    # 6.0.0rc1 is first release to have correct minor/micro update asset
    worker._check_update_available(parse("6.0.0rc1"))
    assert worker.asset_info is not None
    assert worker.asset_info["version"] == parse("6.0.0rc1")


@pytest.mark.parametrize(
    "app,version,release,update_type",
    [
        (True, "6.0.0", "6.0.7", UpdateType.Micro),
        (True, "6.0.0b3", "6.0.0rc1", UpdateType.Minor),
        (True, "6.0.0", "6.1.0a3", UpdateType.Minor),
        (True, "5.0.0", "6.0.7", UpdateType.Major),
        (False, "6.0.0", "6.0.7", UpdateType.Major),
        (False, "6.0.0", "6.1.0a3", UpdateType.Major),
        (False, "5.0.0", "6.0.7", UpdateType.Major)
    ]
)
def test_get_asset_info(qtbot, mocker, app, version, release, update_type):
    mocker.patch.object(workers, "CURRENT_VERSION", new=parse(version))
    mocker.patch.object(workers, "is_conda_based_app", return_value=app)

    worker = WorkerUpdate(False)
    worker._check_update_available(parse(release))
    info = worker.asset_info

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
@pytest.mark.parametrize("version", ["5.5.6", "6.0.0"])
def test_download(qtbot, mocker, version):
    """
    Test download spyder installer.

    Uses UpdateManagerWidget in order to also test QThread.
    """
    version = parse(version)
    mocker.patch.object(workers, "CURRENT_VERSION", new=version)

    releases = workers.get_github_releases()
    release_info = releases[parse("6.1.0a1")]

    um = UpdateManagerWidget(None)
    um.asset_info = get_asset_info(release_info, version, False)
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

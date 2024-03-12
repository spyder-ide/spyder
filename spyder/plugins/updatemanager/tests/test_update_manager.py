# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os
import logging

import pytest

from spyder.config.base import running_in_ci
from spyder.plugins.updatemanager import workers
from spyder.plugins.updatemanager.workers import WorkerUpdate
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
def test_updates_appenv(qtbot, mocker, version):
    """
    Test whether or not we offer updates for our installers according to the
    current Spyder version.

    Uses UpdateManagerWidget in order to also test QThread.
    """
    mocker.patch.object(update, "__version__", new=version)
    # Do not execute start_update after check_update completes.
    mocker.patch.object(
        UpdateManagerWidget, "start_update", new=lambda x: None
    )
    mocker.patch.object(workers, "__version__", new=version)
    mocker.patch.object(workers, "is_anaconda", return_value=True)
    mocker.patch.object(workers, "is_conda_based_app", return_value=True)
    mocker.patch.object(
        workers, "get_spyder_conda_channel",
        return_value=("conda-forge", "https://conda.anaconda.org/conda-forge")
    )

    um = UpdateManagerWidget(None)
    um.start_check_update()
    qtbot.waitUntil(um.update_thread.isFinished)

    update_available = um.update_worker.update_available
    if version.split('.')[0] == '1':
        assert update_available
    else:
        assert not update_available
    assert len(um.update_worker.releases) > 1


@pytest.mark.parametrize("version", ["1.0.0", "1000.0.0"])
@pytest.mark.parametrize(
    "channel", [
        ("pkgs/main", "https://repo.anaconda.com/pkgs/main"),
        ("conda-forge", "https://conda.anaconda.org/conda-forge"),
        ("pypi", "https://conda.anaconda.org/pypi")
    ]
)
def test_updates_condaenv(qtbot, worker, mocker, version, channel):
    """
    Test whether or not we offer updates for conda installed Spyder according
    to the current version.
    """
    mocker.patch.object(workers, "__version__", new=version)
    mocker.patch.object(workers, "is_anaconda", return_value=True)
    mocker.patch.object(workers, "is_conda_based_app", return_value=False)
    mocker.patch.object(
        workers, "get_spyder_conda_channel", return_value=channel
    )

    with qtbot.waitSignal(worker.sig_ready, timeout=5000):
        worker.start()

    update_available = worker.update_available
    if version.split('.')[0] == '1':
        assert update_available
    else:
        assert not update_available
    assert len(worker.releases) == 1


@pytest.mark.parametrize("version", ["1.0.0", "1000.0.0"])
def test_updates_pipenv(qtbot, worker, mocker, version):
    """Test updates for pip installed Spyder."""
    mocker.patch.object(workers, "__version__", new=version)
    mocker.patch.object(workers, "is_anaconda", return_value=False)
    mocker.patch.object(workers, "is_conda_based_app", return_value=False)
    mocker.patch.object(
        workers, "get_spyder_conda_channel",
        return_value=("pypi", "https://conda.anaconda.org/pypi")
    )

    with qtbot.waitSignal(worker.sig_ready, timeout=5000):
        worker.start()

    update_available = worker.update_available
    if version.split('.')[0] == '1':
        assert update_available
    else:
        assert not update_available
    assert len(worker.releases) == 1


@pytest.mark.parametrize("release", ["4.0.1", "4.0.1a1"])
@pytest.mark.parametrize("version", ["4.0.0a1", "4.0.0"])
@pytest.mark.parametrize("stable_only", [True, False])
def test_update_non_stable(qtbot, mocker, version, release, stable_only):
    """Test we offer unstable updates."""
    mocker.patch.object(workers, "__version__", new=version)

    worker = WorkerUpdate(stable_only)
    worker.releases = [release]
    worker._check_update_available()

    update_available = worker.update_available
    if "a" in release and stable_only:
        assert not update_available
    else:
        assert update_available


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

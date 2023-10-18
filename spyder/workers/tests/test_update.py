# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import sys

import pytest

from spyder.workers.updates import WorkerUpdates


@pytest.mark.parametrize("is_anaconda", [True, False])
@pytest.mark.parametrize("is_pypi", [True, False])
@pytest.mark.parametrize("version", ["1.0.0", "1000.0.0"])
@pytest.mark.parametrize(
    "spyder_conda_channel", [
        ("pkgs/main", "https://repo.anaconda.com/pkgs/main"),
        ("conda-forge", "https://conda.anaconda.org/conda-forge")
    ]
)
def test_updates(qtbot, mocker, is_anaconda, is_pypi, version,
                 spyder_conda_channel):
    """
    Test whether or not we offer updates for Anaconda and PyPI according to the
    current Spyder version.
    """
    mocker.patch(
        "spyder.workers.updates.is_anaconda",
        return_value=is_anaconda
    )

    if is_anaconda:
        if is_pypi:
            channel = ("pypi", "https://conda.anaconda.org/pypi")
        else:
            channel = spyder_conda_channel

        mocker.patch(
            "spyder.workers.updates.get_spyder_conda_channel",
            return_value=channel
        )

    worker = WorkerUpdates(None, False, version=version)
    worker.start()

    update = worker.update_available
    assert update if version.split('.')[0] == '1' else not update
    assert len(worker.releases) == 1


@pytest.mark.skipif(sys.platform == 'darwin', reason="Fails frequently on Mac")
@pytest.mark.parametrize("version", ["1.0.0", "1000.0.0"])
def test_updates_for_installers(qtbot, mocker, version):
    """
    Test whether or not we offer updates for our installers according to the
    current Spyder version.
    """
    mocker.patch("spyder.workers.updates.is_anaconda", return_value=False)
    mocker.patch("spyder.workers.updates.is_pynsist", return_value=True)

    worker = WorkerUpdates(None, False, version=version)
    worker.start()

    update = worker.update_available
    assert update if version.split('.')[0] == '1' else not update
    assert len(worker.releases) > 1


def test_no_update_development(qtbot, mocker):
    """Test we don't offer updates for development versions."""
    mocker.patch(
        "spyder.workers.updates.get_spyder_conda_channel",
        return_value=("pypi", "https://conda.anaconda.org/pypi")
    )

    worker = WorkerUpdates(None, False, version="3.3.2.dev0",
                           releases=['3.3.1'])
    worker.start()
    assert not worker.update_available


def test_update_pre_to_pre(qtbot, mocker):
    """Test we offer updates between prereleases."""
    mocker.patch(
        "spyder.workers.updates.get_spyder_conda_channel",
        return_value=("pypi", "https://conda.anaconda.org/pypi")
    )

    worker = WorkerUpdates(None, False, version="4.0.0a1",
                           releases=['4.0.0b5'])
    worker.start()
    assert worker.update_available


def test_update_pre_to_final(qtbot, mocker):
    """Test we offer updates from prereleases to the final versions."""
    mocker.patch(
        "spyder.workers.updates.get_spyder_conda_channel",
        return_value=("pypi", "https://conda.anaconda.org/pypi")
    )

    worker = WorkerUpdates(None, False, version="4.0.0b3",
                           releases=['4.0.0'])
    worker.start()
    assert worker.update_available


if __name__ == "__main__":
    pytest.main()

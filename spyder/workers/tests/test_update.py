# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import pytest

from spyder.utils.programs import check_version
from spyder.workers.updates import WorkerUpdates

# Max time to wait for the update check
# (in miliseconds)
UPDATE_TIMEOUT = 20000


def test_update(qtbot):
    """Test the update checking for a version that needs an update."""
    worker = WorkerUpdates(None, False, version="1.0.0")
    worker.start()
    assert worker.update_available
    assert check_version("1.0.0", worker.latest_release, '<')


def test_no_update(qtbot):
    """Test the update checking for a version that don't needs an update."""
    worker = WorkerUpdates(None, False, version="1000.0.0")
    worker.start()
    assert not worker.update_available
    assert not check_version("1000.0.0", worker.latest_release, '<')


def test_no_update_development(qtbot):
    """Test we don't offer updates for development versions."""
    worker = WorkerUpdates(None, False, version="3.3.2.dev0")
    worker.start()
    assert not worker.update_available


if __name__ == "__main__":
    pytest.main()

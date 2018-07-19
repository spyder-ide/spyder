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
    assert check_version("1.0.0", worker.latest_release, '>')


def test_not_update(self, qtbot):
    """Test the update checking for a version that don't needs an update."""
    worker = WorkerUpdates(None, False, version="10.0.0")
    worker.start()
    assert not worker.update_available
    assert check_version("10.0.0", worker.latest_release, '<')


if __name__ == "__main__":
    pytest.main()

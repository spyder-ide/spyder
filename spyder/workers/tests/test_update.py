# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import pytest

from spyder.config.utils import is_anaconda
from spyder.workers.updates import WorkerUpdates


@pytest.fixture
def worker():
    return WorkerUpdates(None)


def test_update(qtbot, worker):
    """Test we offer updates for lower versions."""
    worker.version = "1.0.0"
    worker.start()
    assert worker.update_available


def test_no_update(qtbot, worker):
    """Test we don't offer updates for very high versions."""
    worker.version = "1000.0.0"
    worker.start()
    assert not worker.update_available


def test_update_pre_to_pre(qtbot, worker):
    """Test we offer updates between prereleases."""
    worker.version = "4.0.0a1"
    worker.releases = ['4.0.0b5']
    worker.start()
    assert worker.update_available


def test_update_pre_to_final(qtbot, worker):
    """Test we offer updates from prereleases to the final versions."""
    worker.version = "4.0.0b3"
    worker.releases = ['4.0.0']
    worker.start()
    assert worker.update_available


@pytest.mark.skipif(not is_anaconda(),
                    reason='It only makes sense for Anaconda.')
def test_releases_anaconda(qtbot, worker):
    """Test we don't include spyder-kernels releases in detected releases."""
    worker.version = "3.3.1"
    worker.start()
    assert '0.2.4' not in worker.releases


if __name__ == "__main__":
    pytest.main()

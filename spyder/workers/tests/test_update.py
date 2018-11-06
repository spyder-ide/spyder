# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import pytest

from spyder.config.utils import is_anaconda
from spyder.workers.updates import WorkerUpdates


@pytest.mark.slow
def test_update(qtbot):
    """Test we offer updates for lower versions."""
    worker = WorkerUpdates(None, False, version="1.0.0")
    worker.start()
    assert worker.update_available


@pytest.mark.slow
def test_no_update(qtbot):
    """Test we don't offer updates for very high versions."""
    worker = WorkerUpdates(None, False, version="1000.0.0")
    worker.start()
    assert not worker.update_available


@pytest.mark.slow
def test_no_update_development(qtbot):
    """Test we don't offer updates for development versions."""
    worker = WorkerUpdates(None, False, version="3.3.2.dev0",
                           releases=['3.3.1'])
    worker.start()
    assert not worker.update_available


@pytest.mark.slow
def test_update_pre_to_pre(qtbot):
    """Test we offer updates between prereleases."""
    worker = WorkerUpdates(None, False, version="4.0.0a1",
                           releases=['4.0.0b5'])
    worker.start()
    assert worker.update_available


@pytest.mark.slow
def test_update_pre_to_final(qtbot):
    """Test we offer updates from prereleases to the final versions."""
    worker = WorkerUpdates(None, False, version="4.0.0b3",
                           releases=['4.0.0'])
    worker.start()
    assert worker.update_available


@pytest.mark.slow
@pytest.mark.skipif(not is_anaconda(),
                    reason='It only makes sense for Anaconda.')
def test_releases_anaconda(qtbot):
    """Test we don't include spyder-kernels releases in detected releases."""
    worker = WorkerUpdates(None, False, version="3.3.1")
    worker.start()
    assert '0.2.4' not in worker.releases


if __name__ == "__main__":
    pytest.main()

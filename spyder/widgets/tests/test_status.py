# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for status.py
"""

# Test library imports
import pytest

# Local imports
from spyder.utils.fixtures import setup_status_bar
from spyder.widgets.status import (ReadWriteStatus, EOLStatus, EncodingStatus,
                                   CursorPositionStatus, MemoryStatus,
                                   CPUStatus)

def test_status_bar(qtbot):
    """Run StatusBarWidget."""
    win, statusbar = setup_status_bar(qtbot)
    swidgets = []
    for klass in (ReadWriteStatus, EOLStatus, EncodingStatus,
                  CursorPositionStatus, MemoryStatus, CPUStatus):
        swidget = klass(win, statusbar)
        swidgets.append(swidget)
    assert win
    assert len(swidgets) == 6


if __name__ == "__main__":
    pytest.main()

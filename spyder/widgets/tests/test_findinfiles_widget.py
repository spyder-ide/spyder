# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for findinfiles.py
"""

# Test library imports
import pytest

# Local imports
from spyder.widgets.findinfiles import FindInFilesWidget

@pytest.fixture
def setup_findinfiles(qtbot):
    """Set up find in files widget."""
    widget = FindInFilesWidget(None)
    qtbot.addWidget(widget)
    return widget

def test_findinfiles(qtbot):
    """Run find in files widget."""
    find_in_files = setup_findinfiles(qtbot)
    find_in_files.resize(640, 480)
    find_in_files.show()
    assert find_in_files


if __name__ == "__main__":
    pytest.main()

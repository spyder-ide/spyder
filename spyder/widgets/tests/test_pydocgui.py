# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for pydocgui.py
"""

# Test library imports
import pytest

# Local imports
from spyder.widgets.pydocgui import PydocBrowser

@pytest.fixture
def setup_pydocbrowser(qtbot):
    """Set up pydocbrowser."""
    widget = PydocBrowser(None)
    qtbot.addWidget(widget)
    return widget

def test_pydocbrowser(qtbot):
    """Run Pydoc Browser."""
    browser = setup_pydocbrowser(qtbot)
    assert browser


if __name__ == "__main__":
    pytest.main()

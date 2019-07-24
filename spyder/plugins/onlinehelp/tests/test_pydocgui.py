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
from spyder.plugins.onlinehelp.widgets import PydocBrowser


@pytest.fixture
def pydocbrowser(qtbot):
    """Set up pydocbrowser."""
    widget = PydocBrowser(None)
    qtbot.addWidget(widget)
    return widget


def test_pydocbrowser(pydocbrowser):
    """Run Pydoc Browser."""
    assert pydocbrowser


if __name__ == "__main__":
    pytest.main()

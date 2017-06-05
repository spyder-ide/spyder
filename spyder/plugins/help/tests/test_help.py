# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Tests for help plugin.
"""

# Test library imports
import pytest

# Local imports
from spyder.plugins.help.widgets import RichText, PlainText


@pytest.fixture
def setup_richtext(qtbot):
    """Set up richtext widget."""
    widget = RichText(None)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def setup_plaintext(qtbot):
    """Set up plaintext widget."""
    widget = PlainText(None)
    qtbot.addWidget(widget)
    return widget


def test_richtext(qtbot):
    """Run RichText."""
    richtext = setup_richtext(qtbot)
    assert richtext


def test_plaintext(qtbot):
    """Run PlainText."""
    plaintext = setup_plaintext(qtbot)
    assert plaintext


if __name__ == "__main__":
    pytest.main()

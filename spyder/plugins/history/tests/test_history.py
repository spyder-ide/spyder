# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Tests for history widget.
"""

# Test library imports
import pytest

# Local imports
from spyder.plugins.history.widgets import History
from spyder.config.gui import get_font
from spyder.py3compat import to_text_string


@pytest.fixture
def setup_history(qtbot):
    """Set up history."""
    widget = History(None)
    qtbot.addWidget(widget)
    return widget


def test_history(qtbot):
    """Run History."""
    history = setup_history(qtbot)
    assert history


def test_add_history(qtbot, tmpdir):
    """Test adding and updating a history log."""
    history = setup_history(qtbot)

    f = tmpdir.mkdir("sub").join("history.py")
    f.write("print('a test')\n")
    filename = str(f)
    font = get_font()
    history.add_history(filename, None, font, False)
    assert len(history.editors) == 1

    command = "print('another test')\n"
    history.append_to_history(filename, command, True)
    text = to_text_string(history.editors[0].toPlainText())
    assert text == "print('a test')\nprint('another test')\n"


if __name__ == "__main__":
    pytest.main()

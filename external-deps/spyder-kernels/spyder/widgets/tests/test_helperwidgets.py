# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for helperwidgets.py
"""

# Test library imports
import pytest

# Third party imports
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.widgets.helperwidgets import MessageCheckBox


@pytest.fixture
def messagecheckbox(qtbot):
    """Set up MessageCheckBox."""
    widget = MessageCheckBox()
    qtbot.addWidget(widget)
    return widget


def test_messagecheckbox(messagecheckbox, qtbot):
    """Run Message Checkbox."""
    box = messagecheckbox
    box.setWindowTitle("Spyder updates")
    box.setText("Testing checkbox")
    box.set_checkbox_text("Check for updates on startup?")
    box.setStandardButtons(QMessageBox.Ok)
    box.setDefaultButton(QMessageBox.Ok)
    box.setIcon(QMessageBox.Information)
    box.show()
    assert box


if __name__ == "__main__":
    pytest.main()

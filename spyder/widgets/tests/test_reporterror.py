# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the report error dialog."""

# Third party imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.widgets.reporterror import (DESC_MIN_CHARS, TITLE_MIN_CHARS,
                                        SpyderErrorDialog)


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def error_dialog(qtbot):
    """Set up error report dialog."""
    widget = SpyderErrorDialog(None)
    qtbot.addWidget(widget)
    widget.show()
    return widget


# =============================================================================
# Tests
# =============================================================================
def test_dialog(error_dialog, qtbot):
    """Test that error report dialog UI behaves properly."""
    dlg = error_dialog
    desc_text = "1" * DESC_MIN_CHARS
    title_text = "1" * TITLE_MIN_CHARS

    # Assert Submit button is disabled at first
    assert not dlg.submit_btn.isEnabled()

    # Introduce MIN_CHARS to input_description
    qtbot.keyClicks(dlg.input_description, desc_text)
    qtbot.keyClicks(dlg.title, title_text)

    # Assert Submit button is now enabled
    assert dlg.submit_btn.isEnabled()

    # Assert cut leaves the header
    dlg.input_description.selectAll()
    dlg.input_description.cut()
    assert dlg.input_description.toPlainText() == dlg.input_description.header

    # Assert delete leaves the header
    qtbot.keyClicks(dlg.input_description, desc_text)
    dlg.input_description.selectAll()
    dlg.input_description.delete()
    assert dlg.input_description.toPlainText() == dlg.input_description.header

    # Assert delete doesn't remove characters on the header
    ini_pos = dlg.input_description.get_position('sof')
    dlg.input_description.set_cursor_position(ini_pos)
    dlg.input_description.delete()
    assert dlg.input_description.toPlainText() == dlg.input_description.header

    # Assert backspace works as expected
    qtbot.keyClicks(dlg.input_description, desc_text)
    qtbot.keyPress(dlg.input_description, Qt.Key_Backspace)
    assert not dlg.submit_btn.isEnabled()

    dlg.input_description.selectAll()
    qtbot.keyPress(dlg.input_description, Qt.Key_Backspace)
    assert dlg.input_description.toPlainText() == dlg.input_description.header

    ini_pos = dlg.input_description.get_position('sof')
    dlg.input_description.set_cursor_position(ini_pos)
    dlg.input_description.set_cursor_position('eol')
    qtbot.keyPress(dlg.input_description, Qt.Key_Backspace)
    assert dlg.input_description.toPlainText() == dlg.input_description.header

    # Assert chars label works as expected
    assert dlg.desc_chars_label.text() == '{} more characters to go...'.format(DESC_MIN_CHARS)
    qtbot.keyClicks(dlg.input_description, desc_text)
    assert dlg.desc_chars_label.text() == 'Description complete; thanks!'


if __name__ == "__main__":
    pytest.main()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for shortcuts.py
"""

import os
import sys

# Test library imports
import pytest
from qtpy.QtCore import Qt

# Local imports
from spyder.config.main import CONF
from spyder.preferences.shortcuts import (
    ShortcutsTable, ShortcutEditor, NO_WARNING, SEQUENCE_CONFLICT,
    INVALID_KEY, SEQUENCE_EMPTY)


# ---- Qt Test Fixtures
@pytest.fixture
def shorcut_table(qtbot):
    """Set up shortcuts."""
    shorcut_table = ShortcutsTable()
    qtbot.addWidget(shorcut_table)
    return shorcut_table


@pytest.fixture
def create_shortcut_editor(shorcut_table, qtbot):
    shortcuts = shorcut_table.source_model.shortcuts

    def _create_bot(context, name):
        sequence = CONF.get('shortcuts', "{}/{}".format(context, name))
        shortcut_editor = ShortcutEditor(
            shorcut_table, context, name, sequence, shortcuts)
        qtbot.addWidget(shortcut_editor)
        shortcut_editor.show()
        return shortcut_editor
    return _create_bot


# ---- Tests ShortcutsTable
@pytest.mark.skipif(
    sys.platform.startswith('linux') and os.environ.get('CI') is not None,
    reason="It fails on Linux due to the lack of a proper X server.")
def test_shortcuts(shorcut_table):
    """Run shortcuts table."""
    shorcut_table.show()
    shorcut_table.check_shortcuts()
    assert shorcut_table


# ---- Tests ShortcutEditor
def test_clear_shortcut(create_shortcut_editor, qtbot):
    """
    Test that pressing on the 'Clear' button to unbind the command from a
    shortcut is working as expected.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')
    qtbot.mouseClick(shortcut_editor.button_clear, Qt.LeftButton)
    assert shortcut_editor.new_sequence == ''


def test_press_new_sequence(create_shortcut_editor, qtbot):
    """
    Test that pressing a key sequence with modifier keys is registered as
    expected by the Shortcut Editor.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')
    modifiers = Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier
    qtbot.keyClick(shortcut_editor, Qt.Key_D, modifier=modifiers)
    assert shortcut_editor.new_sequence == 'Ctrl+Alt+Shift+D'
    assert shortcut_editor.warning == NO_WARNING
    assert shortcut_editor.button_ok.isEnabled()


def test_press_new_compound_sequence(create_shortcut_editor, qtbot):
    """
    Test that pressing a compund of key sequences is registered as
    expected by the Shortcut Editor.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')
    qtbot.keyClick(shortcut_editor, Qt.Key_D, modifier=Qt.ControlModifier)
    qtbot.keyClick(shortcut_editor, Qt.Key_A)
    qtbot.keyClick(shortcut_editor, Qt.Key_B, modifier=Qt.ControlModifier)
    qtbot.keyClick(shortcut_editor, Qt.Key_C)
    qtbot.keyClick(shortcut_editor, Qt.Key_D)
    assert shortcut_editor.new_sequence == 'Ctrl+D, A, Ctrl+B, C'
    # The 'D' key press event is discarted because a compound sequence
    # cannot be composed of more than 4 sub sequences.
    assert shortcut_editor.warning == NO_WARNING
    assert shortcut_editor.button_ok.isEnabled()


def test_clear_back_new_sequence(create_shortcut_editor, qtbot):
    """
    Test that removing the last key sequence entered and clearing all entered
    key sequence from the Shortcut Editor is working as expected.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')
    qtbot.keyClick(shortcut_editor, Qt.Key_X, modifier=Qt.ControlModifier)
    qtbot.keyClick(shortcut_editor, Qt.Key_A)
    qtbot.keyClick(shortcut_editor, Qt.Key_B, modifier=Qt.ControlModifier)
    qtbot.keyClick(shortcut_editor, Qt.Key_C)
    qtbot.keyClick(shortcut_editor, Qt.Key_D)

    # Remove last key sequence entered.
    qtbot.mouseClick(shortcut_editor.button_back_sequence, Qt.LeftButton)
    assert shortcut_editor.new_sequence == 'Ctrl+X, A, Ctrl+B'
    assert shortcut_editor.warning == SEQUENCE_CONFLICT
    assert shortcut_editor.button_ok.isEnabled()

    # Remove second to last key sequence entered.
    qtbot.mouseClick(shortcut_editor.button_back_sequence, Qt.LeftButton)
    assert shortcut_editor.new_sequence == 'Ctrl+X, A'
    assert shortcut_editor.warning == SEQUENCE_CONFLICT
    assert shortcut_editor.button_ok.isEnabled()

    # Clear all entered key sequences.
    qtbot.mouseClick(shortcut_editor.btn_clear_sequence, Qt.LeftButton)
    assert shortcut_editor.new_sequence == ''
    assert shortcut_editor.warning == SEQUENCE_EMPTY
    assert not shortcut_editor.button_ok.isEnabled()


def test_sequence_conflict(create_shortcut_editor, qtbot):
    """
    Test that the Shortcut Editor is able to detect key sequence conflict
    with other shortcuts.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')

    # Check that the conflict is detected for a single key sequence.
    qtbot.keyClick(shortcut_editor, Qt.Key_X, modifier=Qt.ControlModifier)
    assert shortcut_editor.new_sequence == 'Ctrl+X'
    assert shortcut_editor.warning == SEQUENCE_CONFLICT
    assert shortcut_editor.button_ok.isEnabled()

    # Check that the conflict is detected for a compound of key sequences.
    qtbot.keyClick(shortcut_editor, Qt.Key_X)
    assert shortcut_editor.new_sequence == 'Ctrl+X, X'
    assert shortcut_editor.warning == SEQUENCE_CONFLICT
    assert shortcut_editor.button_ok.isEnabled()


def test_sequence_single_key(create_shortcut_editor, qtbot):
    """
    Test that the Shortcut Editor raise a warning when the first key
    sequence entered is composed of a single key with no modifier and this
    single key is not in the list of supported single key sequence.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')

    # Check this is working as expected for a single key sequence.
    qtbot.keyClick(shortcut_editor, Qt.Key_D)
    assert shortcut_editor.new_sequence == 'D'
    assert shortcut_editor.warning == INVALID_KEY
    assert not shortcut_editor.button_ok.isEnabled()

    # Check this is working as expected for a compound of key sequences.
    qtbot.keyClick(shortcut_editor, Qt.Key_D, modifier=Qt.ControlModifier)
    assert shortcut_editor.new_sequence == 'D, Ctrl+D'
    assert shortcut_editor.warning == INVALID_KEY
    assert not shortcut_editor.button_ok.isEnabled()

    # Check this is working as expected when a valid single key is pressed.
    qtbot.mouseClick(shortcut_editor.btn_clear_sequence, Qt.LeftButton)
    qtbot.keyClick(shortcut_editor, Qt.Key_Home)
    assert shortcut_editor.new_sequence == 'Home'
    assert shortcut_editor.warning == NO_WARNING
    assert shortcut_editor.button_ok.isEnabled()


def test_set_sequence_to_default(create_shortcut_editor, qtbot):
    """
    Test that clicking on the button 'Default' set the sequence in the
    Shortcut Editor to the default value as espected.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')
    default_sequence = CONF.get(
        'shortcuts', "{}/{}".format('editor', 'delete line'))

    qtbot.mouseClick(shortcut_editor.button_default, Qt.LeftButton)
    assert shortcut_editor.new_sequence == default_sequence
    assert shortcut_editor.warning == NO_WARNING
    assert shortcut_editor.button_ok.isEnabled()


def test_invalid_char_in_sequence(create_shortcut_editor, qtbot):
    """
    Test that the key sequence is rejected and a warning is shown if an
    invalid character is present in the new key sequence.
    """
    shortcut_editor = create_shortcut_editor('editor', 'delete line')

    # Check this is working as expected for a single key sequence.
    qtbot.keyClick(shortcut_editor, Qt.Key_Odiaeresis,
                   modifier=Qt.ControlModifier | Qt.AltModifier)
    assert shortcut_editor.warning == INVALID_KEY
    assert not shortcut_editor.button_ok.isEnabled()


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-vv', '-rw'])

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for gotoline.py"""

# Third party imports
from qtpy.QtWidgets import QDialogButtonBox, QLineEdit

# Local imports
from spyder.plugins.editor.widgets.gotoline import GoToLineDialog


def test_gotolinedialog_has_cancel_button(codeeditor, qtbot, tmpdir):
    """
    Test that GoToLineDialog has a Cancel button.

    Test that a GoToLineDialog has a button in a dialog button box and that
    this button cancels the dialog window.
    """
    editor = codeeditor
    dialog = GoToLineDialog(editor)
    qtbot.addWidget(dialog)
    ok_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok)
    cancel_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Cancel)
    assert not ok_button.isEnabled()
    with qtbot.waitSignal(dialog.rejected):
        cancel_button.click()


def test_gotolinedialog_enter_plus(codeeditor, qtbot):
    """
    Regression test for spyder-ide/spyder#12693
    """
    editor = codeeditor
    dialog = GoToLineDialog(editor)
    qtbot.addWidget(dialog)
    ok_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok)
    cancel_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Cancel)
    lineedit = dialog.findChild(QLineEdit)
    lineedit.setText('+')

    # Check + sign being cleared and ok button still is disabled
    lineedit.setText("+")
    assert lineedit.text() == ""
    assert not ok_button.isEnabled()

def test_gotolinedialog_check_valid(codeeditor, qtbot):
    """
    Check ok button enabled if valid text entered
    """
    editor = codeeditor
    dialog = GoToLineDialog(editor)
    qtbot.addWidget(dialog)
    ok_button = dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok)
    lineedit = dialog.findChild(QLineEdit)
    lineedit.setText("1")
    assert lineedit.text() == "1"
    assert ok_button.isEnabled()
    with qtbot.waitSignal(dialog.accepted):
        ok_button.click()
    assert dialog.get_line_number() == 1
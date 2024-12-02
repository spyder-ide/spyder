# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Standard library imports

# Third party imports
from qtpy.QtCore import Qt, QPoint

# Local imports


def test_add_cursor(codeeditor, qtbot):
    code_editor = codeeditor
    # enabled by default arg on CodeEditor.setup_editor (which is called in the
    #    pytest fixture creation in conftest.py)
    assert code_editor.multi_cursor_enabled
    code_editor.set_text("0123456789")
    qtbot.wait(1000)
    x, y = code_editor.get_coordinates(4)
    point = code_editor.calculate_real_position(QPoint(x, y))

    qtbot.mousePress(code_editor,
                     Qt.MouseButton.LeftButton,
                     (Qt.KeyboardModifier.ControlModifier |
                      Qt.KeyboardModifier.AltModifier),
                     pos=point,
                     delay=1000)

    # A cursor was added
    assert bool(code_editor.extra_cursors)
    qtbot.keyClick(code_editor, "a")
    # Text was inserted correctly from two cursors
    assert code_editor.toPlainText() == "a0123a456789"

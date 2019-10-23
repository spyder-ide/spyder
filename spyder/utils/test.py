# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests utilities."""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMessageBox, QApplication

def close_message_box(qtbot):
    """
    Closes QMessageBox's that can appear when testing.

    You can use this with QTimer to close a QMessageBox.
    Before calling anything that may show a QMessageBox call:
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    """
    top_level_widgets = QApplication.topLevelWidgets()
    for w in top_level_widgets:
        if isinstance(w, QMessageBox):
            qtbot.keyClick(w, Qt.Key_Enter)

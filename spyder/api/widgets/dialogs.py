# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder dialog widgets.
"""

# Third-party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QDialogButtonBox


class SpyderDialogButtonBox(QDialogButtonBox):
    """
    QDialogButtonBox widget for Spyder that doesn't display icons on its
    standard buttons.
    """

    def __init__(self, buttons=None, orientation=Qt.Horizontal, parent=None):
        if buttons:
            super().__init__(buttons, orientation, parent)
        elif orientation:
            super().__init__(orientation=orientation, parent=parent)
        else:
            super().__init__(parent=parent)

        button_constants = [
            QDialogButtonBox.Ok,
            QDialogButtonBox.Open,
            QDialogButtonBox.Save,
            QDialogButtonBox.Cancel,
            QDialogButtonBox.Close,
            QDialogButtonBox.Discard,
            QDialogButtonBox.Apply,
            QDialogButtonBox.Reset,
            QDialogButtonBox.RestoreDefaults,
            QDialogButtonBox.Help,
            QDialogButtonBox.SaveAll,
            QDialogButtonBox.Yes,
            QDialogButtonBox.YesToAll,
            QDialogButtonBox.No,
            QDialogButtonBox.NoToAll,
            QDialogButtonBox.Abort,
            QDialogButtonBox.Retry,
            QDialogButtonBox.Ignore,
        ]

        for constant in button_constants:
            button = self.button(constant)
            if button is not None:
                button.setIcon(QIcon())

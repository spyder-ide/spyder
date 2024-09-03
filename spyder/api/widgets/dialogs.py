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
from qtpy.QtWidgets import QDialogButtonBox, QProxyStyle, QStyle

# Local imports
from spyder.utils.stylesheet import AppStyle


class _SpyderButtonsProxyStyle(QProxyStyle):
    """Style adjustments for SpyderDialogButtonBox."""

    def styleHint(self, hint, option=None, widget=None, return_data=None):
        if hint == QStyle.SH_DialogButtonLayout:
            # Use the Windows buttons layout to have a uniform layout in all
            # platforms. We selected that layout because Windows is our most
            # popular platform.
            # Solution found in https://stackoverflow.com/a/35907926/438386
            return QDialogButtonBox.WinLayout

        return super().styleHint(hint, option, widget, return_data)


class SpyderDialogButtonBox(QDialogButtonBox):
    """QDialogButtonBox widget for Spyder."""

    def __init__(self, buttons=None, orientation=Qt.Horizontal, parent=None):
        if buttons:
            super().__init__(buttons, orientation, parent)
        elif orientation:
            super().__init__(orientation=orientation, parent=parent)
        else:
            super().__init__(parent=parent)

        # Don't display icons on standard buttons. This is a problem on Linux
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

        # Set a reasonable spacing between buttons. This is a problem on Mac
        self.layout().setSpacing(2 * AppStyle.MarginSize)

        # Set style
        style = _SpyderButtonsProxyStyle(None)
        style.setParent(self)
        self.setStyle(style)

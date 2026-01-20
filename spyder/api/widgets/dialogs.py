# -----------------------------------------------------------------------------
# Copyright (c) 2024- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Spyder dialog widgets.
"""

from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
from qtpy import QT6
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QDialogButtonBox, QProxyStyle, QStyle

# Local imports
from spyder.utils.stylesheet import AppStyle

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget


class _SpyderButtonsProxyStyle(QProxyStyle):
    """Style adjustments for :class:`SpyderDialogButtonBox`."""

    def styleHint(self, hint, option=None, widget=None, return_data=None):
        if hint == QStyle.SH_DialogButtonLayout:
            # Use the Windows buttons layout to have a uniform layout in all
            # platforms. We selected that layout because Windows is our most
            # popular platform.
            # Solution found in https://stackoverflow.com/a/35907926/438386
            if QT6:  # PySide6/PyQt6
                return QDialogButtonBox.ButtonLayout.WinLayout.value
            else:  # PySide2/PyQt5
                return int(QDialogButtonBox.ButtonLayout.WinLayout)

        return super().styleHint(hint, option, widget, return_data)


class SpyderDialogButtonBox(QDialogButtonBox):
    """Action button section (OK, Cancel, etc) widget for dialog boxes."""

    def __init__(
        self,
        buttons: QDialogButtonBox.StandardButton | None = None,
        orientation: Qt.Orientation = Qt.Horizontal,
        parent: QWidget | None = None,
    ):
        """
        Create a new group of dialog box buttons.

        Parameters
        ----------
        buttons : QDialogButtonBox.StandardButton | None, optional
            The standard buttons to include in the dialog box button group,
            such as "OK", "Cancel" or "Apply", passed as a single argument
            composed of Qt enum members bitwise or-ed (``|``) together.
            For example, ``QDialogButtonBox.Ok | QDialogButtonBox.Cancel``.
            If ``None``, the default, is an empty button box with no buttons.
        orientation : Qt.Orientation, optional
            Whether the button box is laid out horizontally, with buttons
            side by side, or vertically, with buttons on top of one another.
            By default, horizontal (``Qt.Horizontal``).
        parent : QWidget | None, optional
            The parent widget of this button box, ``None`` by default.

        Returns
        -------
        None
        """
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

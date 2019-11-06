# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.panes
==================

Here, 'panes' are Qt main windows that should be used to encapsulate the
main interface of Spyder plugins.
"""

# ---- Standard library imports
import uuid

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QToolBar

# ---- Local imports
from spyder.config.gui import is_dark_interface
from spyder.utils.qthelpers import create_toolbar_stretcher


class SpyderPaneToolbar(QToolBar):
    """
    Spyder pane toolbar class.

    A toolbar class that is used by the spyder pane widget class.
    """

    def __init__(self, parent=None, areas=Qt.TopToolBarArea,
                 corner_widget=None):
        super().__init__(parent)
        self._set_corner_widget(corner_widget)
        self.setObjectName("pane_toolbar_{}".format(str(uuid.uuid4())[:8]))
        self.setFloatable(False)
        self.setMovable(False)
        self.setAllowedAreas(areas)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self._set_style()

    def addWidget(self, widget):
        """
        Override Qt method to take into account the existence of a corner
        widget when adding a new widget in this toolbar.
        """
        if self._corner_widget is not None:
            super().insertWidget(self._corner_separator_action, widget)
        else:
            super().addWidget(widget)

    def addAction(self, action):
        """
        Override Qt method to take into account the existence of a corner
        widget when adding a new action in this toolbar.
        """
        if self._corner_widget is not None:
            super().insertAction(self._corner_separator_action, action)
        else:
            super().addAction(action)

    def _set_corner_widget(self, corner_widget):
        """
        Add the given corner widget to this toolbar.

        A stretcher widget is added before the corner widget so that
        its position is forced to the right side of the toolbar when the
        toolbar is resized.
        """
        self._corner_widget = corner_widget
        if corner_widget is not None:
            self._corner_separator_action = super().addWidget(
                create_toolbar_stretcher())
            super().addWidget(self._corner_widget)
        else:
            self._corner_separator_action = None

    def _set_style(self):
        """
        Set the style of this toolbar with a stylesheet.
        """
        if is_dark_interface():
            self.setStyleSheet(
                "QToolButton {background-color: transparent;} "
                "QToolButton:!hover:!pressed {border-color: transparent} "
                "QToolBar {border: 0px;  background: rgb(25, 35, 45);}")
        else:
            self.setStyleSheet("QToolBar {border: 0px;}")


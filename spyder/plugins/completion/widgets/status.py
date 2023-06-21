# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widget."""

# Standard imports
import os

# Third party imports
from qtpy.QtCore import QPoint, Signal
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.status import StatusBarWidget
from spyder.utils.qthelpers import add_actions, create_action


class CompletionStatus(StatusBarWidget):
    """Status bar widget for displaying the current conda environment."""
    ID = 'completion_status'

    sig_open_preferences_requested = Signal()
    """
    Signal to open the main interpreter preferences.
    """

    def __init__(self, parent, icon=None):
        """Status bar widget for displaying the current completions status."""
        self._tool_tip = ''
        super().__init__(parent)
        self.main = parent
        self.value = ''

        self.menu = QMenu(self)
        self.sig_clicked.connect(self.show_menu)

    def update_status(self, value, tool_tip):
        """Update status bar text"""
        super().set_value(value)
        self._tool_tip = tool_tip
        self.update_tooltip()

    def get_tooltip(self):
        """Override api method."""
        return self._tool_tip if self._tool_tip else ''

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        menu = self.menu
        menu.clear()
        text = _("Change default environment in Preferences...")
        change_action = create_action(
            self,
            text=text,
            triggered=self.open_interpreter_preferences,
        )
        add_actions(menu, [change_action])
        rect = self.contentsRect()
        os_height = 7 if os.name == 'nt' else 12
        pos = self.mapToGlobal(
            rect.topLeft() + QPoint(-40, -rect.height() - os_height))
        menu.popup(pos)

    def open_interpreter_preferences(self):
        """Request to open the main interpreter preferences."""
        self.sig_open_preferences_requested.emit()

    def get_icon(self):
        return self.create_icon('completions')

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main interpreter status widget."""


# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.widgets.status import StatusBarWidget


class InterpreterStatus(StatusBarWidget):
    """Status bar widget for displaying the current conda environment."""
    ID = 'interpreter_status'
    CONF_SECTION = 'main_interpreter'

    sig_open_preferences_requested = Signal()
    """
    Signal to open the main interpreter preferences.
    """

    def open_interpreter_preferences(self):
        """Request to open the main interpreter preferences."""
        self.sig_open_preferences_requested.emit()

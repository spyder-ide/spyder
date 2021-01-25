# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Status bar container.
"""

# Third-party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.widgets import PluginMainContainer
from spyder.plugins.statusbar.widgets.status import (
    ClockStatus, CPUStatus, MemoryStatus
)


class StatusBarContainer(PluginMainContainer):
    DEFAULT_OPTIONS = {
        'show_status_bar': True,
        'memory_usage/enable': True,
        'memory_usage/timeout': 2000,
        'cpu_usage/enable': False,
        'cpu_usage/timeout': 2000,
        'clock/enable': False,
        'clock/timeout': 1000,
    }

    sig_show_status_bar_requested = Signal(bool)
    """
    This signal is emmitted when the user wants to show/hide the
    status bar.
    """

    def setup(self, options):
        # Basic status widgets
        self.mem_status = MemoryStatus(parent=self)
        self.cpu_status = CPUStatus(parent=self)
        self.clock_status = ClockStatus(parent=self)

    def on_option_update(self, option, value):
        if option == 'memory_usage/enable':
            self.mem_status.setVisible(value)
        elif option == 'memory_usage/timeout':
            self.mem_status.set_interval(value)
        elif option == 'cpu_usage/enable':
            self.cpu_status.setVisible(value)
        elif option == 'cpu_usage/timeout':
            self.cpu_status.set_interval(value)
        elif option == 'clock/enable':
            self.clock_status.setVisible(value)
        elif option == 'clock/timeout':
            self.clock_status.set_interval(value)
        elif option == 'show_status_bar':
            self.sig_show_status_bar_requested.emit(value)

    def update_actions(self):
        pass

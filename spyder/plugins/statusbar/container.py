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
from spyder.api.config.decorators import on_conf_change
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.statusbar.widgets.status import (
    ClockStatus, CPUStatus, MemoryStatus
)


class StatusBarContainer(PluginMainContainer):

    sig_show_status_bar_requested = Signal(bool)
    """
    This signal is emmitted when the user wants to show/hide the
    status bar.
    """

    def setup(self):
        # Basic status widgets
        self.mem_status = MemoryStatus(parent=self)
        self.cpu_status = CPUStatus(parent=self)
        self.clock_status = ClockStatus(parent=self)

    @on_conf_change(option='memory_usage/enable')
    def enable_mem_status(self, value):
        self.mem_status.setVisible(value)

    @on_conf_change(option='memory_usage/timeout')
    def set_mem_interval(self, value):
        self.mem_status.set_interval(value)

    @on_conf_change(option='cpu_usage/enable')
    def enable_cpu_status(self, value):
        self.cpu_status.setVisible(value)

    @on_conf_change(option='cpu_usage/timeout')
    def set_cpu_interval(self, value):
        self.cpu_status.set_interval(value)

    @on_conf_change(option='clock/enable')
    def enable_clock_status(self, value):
        self.clock_status.setVisible(value)

    @on_conf_change(option='clock/timeout')
    def set_clock_interval(self, value):
        self.clock_status.set_interval(value)

    @on_conf_change(option='show_status_bar')
    def show_status_bar(self, value):
        self.sig_show_status_bar_requested.emit(value)

    def update_actions(self):
        pass

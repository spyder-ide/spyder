# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Core Widget.
"""

import sys

# Local imports
from spyder.api.widgets import PluginMainContainer
from spyder.config.utils import is_anaconda
from spyder.plugins.core.widgets.status import ClockStatus
from spyder.plugins.core.widgets.status import CondaStatus
from spyder.plugins.core.widgets.status import CPUStatus
from spyder.plugins.core.widgets.status import MemoryStatus


class StatusBarContainer(PluginMainContainer):
    DEFAULT_OPTIONS = {
        'memory_usage/enable': True,
        'memory_usage/timeout': 2000,
        'cpu_usage/enable': False,
        'cpu_usage/timeout': 2000,
        'clock/enable': False,
        'clock/timeout': 1000,
        'show_status_bar': True,  # FIXME: trigger signal from within
        'use_default_interpreter': True,
        'custom_interpreter': None,
    }

    def __init__(self, name, plugin, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent=parent, options=options)

        # Widgets
        self.mem_status = MemoryStatus(parent=self)
        self.cpu_status = CPUStatus(parent=self)
        self.clock_status = ClockStatus(parent=self)
        self.conda_status = CondaStatus(parent=self)
        # , icon=ima.icon('environment')

    def setup(self, options=DEFAULT_OPTIONS):
        for option, value in options.items():
            self.on_option_update(option, value)

        self.conda_status.update_interpreter(self.get_main_interpreter())

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
        elif option in ['use_default_interpreter']:
            self.conda_status.update_interpreter(self.get_main_interpreter())

    def update_actions(self):
        pass

    def get_main_interpreter(self):
        if self.get_option('use_default_interpreter'):
            return sys.executable
        else:
            return self.get_option('custom_interpreter')

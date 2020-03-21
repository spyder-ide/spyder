# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Core Plugin.
"""

# Local imports
from spyder.api.plugins import SpyderPluginV2
from spyder.api.translations import get_translation
from spyder.plugins.core.container import StatusBarContainer

# Localization
_ = get_translation('spyder')


# --- Constants
class StatusWidgets:
    Conda = 'conda_status_widget'
    Memory = 'memory_status_widget'
    CPU = 'cpu_status_widget'
    Clock = 'clock_status_widget'
    

class StatusBar(SpyderPluginV2):
    NAME = 'statusbar'
    CONTAINER_CLASS = StatusBarContainer
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_FROM_OPTIONS = {
        'memory_usage/enable': ('main', 'memory_usage/enable'),
        'memory_usage/timeout': ('main', 'memory_usage/timeout'),
        'cpu_usage/enable': ('main', 'cpu_usage/enable'),
        'cpu_usage/timeout': ('main', 'cpu_usage/timeout'),
        'clock/enable': ('main', 'clock/enable'),
        'clock/timeout': ('main', 'clock/timeout'),
        # FIXME: trigger signal from within
        'show_status_bar': ('main', 'show_status_bar'),
        'use_default_interpreter': ('main', 'use_default_interpreter'),
        'custom_interpreter': ('main', 'custom_interpreter'),
    }

    def get_name(self):
        return _('General')

    def get_icon(self):
        return self.create_icon('genprefs')

    def get_description(self):
        return _('Provide Core user interface management')

    def register(self):
        # --- Status widgets
        self.add_application_status_widget(
            CoreStatusWidgets.Conda,
            self.conda_status,
            -1,
        )
        self.add_application_status_widget(
            CoreStatusWidgets.Memory,
            self.mem_status,
            -1,
        )
        self.add_application_status_widget(
            CoreStatusWidgets.CPU,
            self.cpu_status,
            -1,
        )
        self.add_application_status_widget(
            CoreStatusWidgets.Clock,
            self.clock_status,
            -1,
        )

    # --- Public API
    # ------------------------------------------------------------------------
    def add_application_status_widget(self, name, widget, index=None):
        """
        Add status widget to main application status bar.
        """
        if name in self._main._STATUS_WIDGETS:
            raise SpyderAPIError('Status widget `{}` already added!'.format(
                name))

        # Check widget class
        if not isinstance(widget, StatusBarWidget):
            raise SpyderAPIError(
                'Status widget must subclass StatusBarWidget!')

        self._main._STATUS_WIDGETS[name] = widget
        count = len(self._main._STATUS_WIDGETS)
        statusbar = self._main.statusBar()
        statusbar.setStyleSheet('QStatusBar::item {border: None;}')
        statusbar.addPermanentWidget(widget)
        statusbar.layout().setContentsMargins(0, 0, 0, 0)
        statusbar.layout().setSpacing(0)

    def get_application_status_widget(self, name):
        """
        Return an application status widget by name.
        """
        if name in self._main._STATUS_WIDGETS:
            return self._main._STATUS_WIDGETS[name]
        else:
            raise SpyderAPIError('Status widget "{}" not found!'.format(name))

    def get_application_status_widgets(self):
        """
        Return all application status widgets created.
        """
        return self._main._STATUS_WIDGETS

    # --- API Application Status Widgets
    # ------------------------------------------------------------------------
    @property
    def mem_status(self):
        return self.get_container().mem_status

    @property
    def cpu_status(self):
        return self.get_container().cpu_status

    @property
    def clock_status(self):
        return self.get_container().cpu_status

    @property
    def conda_status(self):
        return self.get_container().conda_status

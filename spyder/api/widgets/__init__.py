# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widgets to extend Spyder through its API.
"""


class PluginMainWidgetWidgets:
    CornerWidget = 'corner_widget'
    MainToolbar = 'main_toolbar_widget'
    OptionsToolButton = 'options_button_widget'
    Spinner = 'spinner_widget'


class PluginMainWidgetActions:
    ClosePane = 'close_pane'
    DockPane = 'dock_pane'
    UndockPane = 'undock_pane'
    LockUnlockPosition = 'lock_unlock_position'

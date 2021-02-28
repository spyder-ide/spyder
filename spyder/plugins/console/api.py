# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Console Plugin API.
"""

# Local imports
from spyder.plugins.console.widgets.main_widget import (
    ConsoleWidgetActions, ConsoleWidgetInternalSettingsSubMenuSections,
    ConsoleWidgetMenus, ConsoleWidgetOptionsMenuSections)


class ConsoleActions:
    SpyderReportAction = "spyder_report_action"

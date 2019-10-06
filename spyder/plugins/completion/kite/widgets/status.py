# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Status widget for Kite completions.
"""

# Standard library imports
import logging

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.widgets.calltip import ToolTipWidget
from spyder.widgets.status import StatusBarWidget
from spyder.plugins.completion.kite.utils.status import NOT_INSTALLED

logger = logging.getLogger(__name__)


class KiteStatusWidget(StatusBarWidget):
    """Status bar widget for Kite completions status."""
    BASE_TOOLTIP = _("Kite completions status")
    DEFAULT_STATUS = _('not reacheable')

    def __init__(self, parent, statusbar, plugin):
        self.plugin = plugin
        self.tooltip = self.BASE_TOOLTIP
        super(KiteStatusWidget, self).__init__(parent, statusbar,
                                               icon=ima.get_kite_icon())
        self.tooltipWidget = ToolTipWidget(self, as_tooltip=True)
        self.set_value(None)

    def set_value(self, value):
        """Return Kite completions state."""
        kite_enabled = self.plugin.get_option('enable')
        if (value is not None and 'short' in value):
            self.tooltip = value['long']
            value = value['short']
        elif value is not None and self.plugin.is_installing():
            self.tooltip = _('Kite is being installed')
            if value == NOT_INSTALLED:
                return
        elif value is None:
            value = self.DEFAULT_STATUS
            self.tooltip = self.BASE_TOOLTIP

        self.update_tooltip()
        self.setVisible(value != NOT_INSTALLED or kite_enabled)

        super(KiteStatusWidget, self).set_value(value)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return self.tooltip

    def show_tooltip(self, text=None):
        """Show tooltip for a period of time."""
        if not text:
            text = self.tooltip
        pos = self.parent().mapToGlobal(self.pos())
        self.tooltipWidget.show_basic_tip(pos, text)

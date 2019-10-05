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
from spyder.widgets.status import BaseTimerStatus
from spyder.plugins.completion.kite.utils.status import NOT_INSTALLED

logger = logging.getLogger(__name__)


class KiteStatus(BaseTimerStatus):
    """Status bar widget for Kite completions status."""
    BASE_TOOLTIP = _("Kite completions status")

    def __init__(self, parent, statusbar, plugin):
        self.plugin = plugin
        self.tooltip = self.BASE_TOOLTIP
        super(KiteStatus, self).__init__(parent, statusbar,
                                         icon=ima.get_kite_icon())
        self.tooltipWidget = ToolTipWidget(self, as_tooltip=True)

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        try:
            self.plugin.get_kite_status()
        except Exception as e:
            logger.debug('Error while fetching Kite status: {0}'.format(e))
            raise ImportError

    def get_value(self):
        """Return Kite completions state."""
        kite_status = self.plugin.get_kite_status()
        kite_enabled = self.plugin.get_option('enable')
        if (kite_status is not None and 'short' in kite_status):
            self.tooltip = kite_status['long']
            kite_status = kite_status['short']
        elif kite_status is not None and self.plugin.is_installing():
            self.tooltip = _('Kite is being installed')
        elif kite_status is None:
            kite_status = _('not reacheable')
            self.tooltip = self.BASE_TOOLTIP
        else:
            self.tooltip = self.BASE_TOOLTIP

        self.update_tooltip()
        self.setVisible(kite_status != NOT_INSTALLED or kite_enabled)

        return kite_status

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return self.tooltip

    def show_tooltip(self, text=None):
        """Show tooltip for a period of time."""
        if not text:
            text = self.tooltip
        pos = self.parent().mapToGlobal(self.pos())
        self.tooltipWidget.show_basic_tip(pos, text)

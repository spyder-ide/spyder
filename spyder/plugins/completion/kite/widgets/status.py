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
from spyder.widgets.status import StatusBarWidget
from spyder.plugins.completion.kite.utils.status import (
    check_if_kite_installed, NOT_INSTALLED)

logger = logging.getLogger(__name__)


class KiteStatusWidget(StatusBarWidget):
    """Status bar widget for Kite completions status."""
    BASE_TOOLTIP = _("Kite completions status")
    DEFAULT_STATUS = _('not reachable')

    def __init__(self, parent, statusbar, plugin):
        self.plugin = plugin
        self.tooltip = self.BASE_TOOLTIP
        super(KiteStatusWidget, self).__init__(parent, statusbar,
                                               icon=ima.get_kite_icon())
        is_installed, _ = check_if_kite_installed()
        self.setVisible(is_installed)

    def set_value(self, value):
        """Return Kite completions state."""
        kite_enabled = self.plugin.get_option('enable')
        is_installing = self.plugin.is_installing()
        cancelled_or_errored = self.plugin.installation_cancelled_or_errored()

        if (value is not None and 'short' in value):
            self.tooltip = value['long']
            value = value['short']
        elif value is not None and (is_installing or cancelled_or_errored):
            self.setVisible(True)
            if value == NOT_INSTALLED:
                return
            elif is_installing:
                self.tooltip = _("Kite installation will continue in the "
                                 "background.\n"
                                 "Click here to show the installation "
                                 "dialog again")
            elif cancelled_or_errored:
                self.tooltip = _("Click here to show the\n"
                                 "installation dialog again")
        elif value is None:
            value = self.DEFAULT_STATUS
            self.tooltip = self.BASE_TOOLTIP
        self.update_tooltip()
        self.setVisible(value != NOT_INSTALLED and kite_enabled)
        value = "Kite: {0}".format(value)
        super(KiteStatusWidget, self).set_value(value)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

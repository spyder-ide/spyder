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
from spyder.widgets.status import BaseTimerStatus

logger = logging.getLogger(__name__)


class KiteStatus(BaseTimerStatus):
    """Status bar widget for Kite completions status."""

    def __init__(self, parent, statusbar, plugin):
        self.plugin = plugin
        self.tooltip = _("Kite completions status")
        self.open_file_updated = True
        super(KiteStatus, self).__init__(parent, statusbar,
                                         icon=ima.get_kite_icon())

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        try:
            from spyder.plugins.completion.kite.utils.status import status
        except Exception as e:
            logger.debug('Error while fetching Kite status: {0}'.format(e))
            raise ImportError

    def get_value(self, filename=None, saved=False):
        """Return Kite completions state."""
        from spyder.plugins.completion.kite.utils.status import (
            status, NOT_INSTALLED, RUNNING)
        kite_status = status()
        if kite_status == RUNNING and self.open_file_updated:
            client_status = self.plugin.get_kite_status()
            if client_status:
                kite_status = client_status['short']
                self.tooltip = client_status['long']
                if (client_status['status'] == 'ready'
                        or client_status['status'] == 'unsupported'):
                    self.open_file_updated = False
            else:
                kite_status = 'not reacheable'
                self.open_file_updated = False
        text = '𝕜𝕚𝕥𝕖: {}'.format(kite_status)
        kite_enabled = self.plugin.get_option('enable', True)
        self.setVisible(kite_status != NOT_INSTALLED or kite_enabled)

        return text

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return self.tooltip

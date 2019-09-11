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

    def __init__(self, parent, statusbar, status_handler):
        self._status_handler = status_handler
        super(KiteStatus, self).__init__(parent, statusbar,
                                         icon=ima.get_kite_icon())

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        try:
            self._status_handler.status()
        except Exception as e:
            logger.debug('Error while fetching Kite status: {0}'.format(e))
            raise ImportError

    def get_value(self):
        """Return Kite completions state."""
        status = self._status_handler.status()
        self.setVisible(status != self._status_handler.NOT_INSTALLED)
        text = '𝕜𝕚𝕥𝕖: {}'.format(status)
        return text

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Kite completions status")

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

    def __init__(self, parent, statusbar):
        super(KiteStatus, self).__init__(parent, statusbar,
                                         icon=ima.get_kite_icon())

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        try:
            from spyder.plugins.completion.kite.utils.status import status
        except Exception as e:
            logger.debug('Error while fetching Kite status: {0}'.format(e))
            raise ImportError

    def get_value(self):
        """Return Kite completions state."""
        from spyder.plugins.completion.kite.utils.status import (
            status, NOT_INSTALLED)
        kite_status = status()
        # TODO: Use enable preference to update visibility of the status bar
        self.setVisible(kite_status != NOT_INSTALLED)
        text = '𝕜𝕚𝕥𝕖: {}'.format(kite_status)
        return text

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Kite completions status")

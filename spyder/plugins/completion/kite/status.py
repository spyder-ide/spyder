# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Status widget for Kite completion.
"""

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.widgets.status import BaseTimerStatus


class KiteStatus(BaseTimerStatus):
    """Status bar widget for Kite completion state."""

    def __init__(self, parent, statusbar):
        super(KiteStatus, self).__init__(parent, statusbar,
                                         icon=ima.get_kite_icon())

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        try:
            from spyder.plugins.completion.kite.plugin import (
                KiteCompletionPlugin)
            KiteCompletionPlugin.kite_status()
        except Exception as e:
            print(e)
            raise ImportError

    def get_value(self):
        """Return Kite completions state."""
        from spyder.plugins.completion.kite.plugin import (
            KiteCompletionPlugin, NOT_INSTALLED)
        status = KiteCompletionPlugin.kite_status()
        self.setVisible(status != NOT_INSTALLED)
        text = 'Kite: {}'.format(status)
        return text

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Kite completion status")

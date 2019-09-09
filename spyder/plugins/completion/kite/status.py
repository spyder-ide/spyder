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
from spyder.widgets.status import StatusBarWidget


class KiteStatus(StatusBarWidget):
    """Status bar widget for Kite completion state."""

    def __init__(self, parent, statusbar):
        super(KiteStatus, self).__init__(parent, statusbar,
                                         icon=ima.get_kite_icon())

    def update_kite_status(self, kite_enabled):
        """Update kite completion status."""
        self.set_value(_("Kite: enabled"))
        self.setVisible(bool(kite_enabled))

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Kite completion status")

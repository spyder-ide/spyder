# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import datetime

# Local imports
from spyder.api.widgets.status import BaseTimerStatus
from spyder.api.translations import _


class InAppAppealStatus(BaseTimerStatus):
    """Status bar widget for current file read/write mode."""

    ID = "inapp_appeal_status"
    CONF_SECTION = "main"
    INTERACT_ON_CLICK = True

    DAYS_TO_SHOW_AGAIN = 15

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_shown = False

        # We don't need to show a label for this widget
        self.label_value.setVisible(False)

        # Update status every hour
        self.set_interval(60 * 60 * 1000)

    # ---- StatusBarWidget API
    # -------------------------------------------------------------------------
    def get_icon(self):
        return self.create_icon("inapp_appeal")

    def update_status(self):
        """
        Show widget for a day after a certain number of days, then hide it.
        """
        today = datetime.date.today()
        last_date = self.get_conf("last_inapp_appeal", default="")

        if last_date:
            delta = today - datetime.date.fromisoformat(last_date)
            if 0 < delta.days < self.DAYS_TO_SHOW_AGAIN:
                self.setVisible(False)
            else:
                self.setVisible(True)
                self.set_conf("last_inapp_appeal", str(today))
        else:
            self.set_conf("last_inapp_appeal", str(today))

    def get_tooltip(self):
        return _("Help Spyder!")

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)

        # Hide widget if necessary at startup
        if not self._is_shown:
            self.update_status()
            self._is_shown = True

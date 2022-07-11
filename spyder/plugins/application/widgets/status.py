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

# Third party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import _, running_under_pytest
#from spyder.plugins.application.container import INSTALLING
#from spyder.plugins.application.container import (
#    ApplicationContainer)
from spyder.plugins.application.widgets.install import (
    UpdateInstallerDialog)
from spyder.utils.icon_manager import ima

logger = logging.getLogger(__name__)


class ApplicationUpdateStatus(StatusBarWidget):
    """Status bar widget for Application update status."""
    BASE_TOOLTIP = _("Application update status")
    DEFAULT_STATUS = _('not reachable')
    ID = 'application_update_status'

    def __init__(self, parent):
        self.tooltip = self.BASE_TOOLTIP
        self.installation_thread = parent
        super().__init__(parent)

        # Installation dialog
        self.installer = UpdateInstallerDialog(
            self,
            self.installation_thread)

        self.installation_thread.sig_installation_status.connect(
            self.set_value)
        self.sig_clicked.connect(self.show_installation_dialog)

    def set_value(self, value):
        """Return update installation state."""


        if value == "Installing":
            self.tooltip = _("Update installation will continue in the "
                             "background.\n"
                             "Click here to show the installation "
                             "dialog again")
        elif value is None:
            value = self.DEFAULT_STATUS
            self.tooltip = self.BASE_TOOLTIP
        self.update_tooltip()
        value = "Update: {0}".format(value)
        super(ApplicationUpdateStatus, self).set_value(value)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def get_icon(self):
        return ima.icon('spyder')

    @Slot()
    def show_installation_dialog(self):
        """Show installation dialog."""
        self.installer.show()

   

    

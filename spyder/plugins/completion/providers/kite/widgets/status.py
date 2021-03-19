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
from spyder.plugins.completion.providers.kite.utils.status import (
    check_if_kite_installed, NOT_INSTALLED)
from spyder.plugins.completion.providers.kite.utils.install import (
    KiteInstallationThread)
from spyder.plugins.completion.providers.kite.widgets.install import (
    KiteInstallerDialog)
from spyder.utils.icon_manager import ima

logger = logging.getLogger(__name__)


class KiteStatusWidget(StatusBarWidget):
    """Status bar widget for Kite completions status."""
    BASE_TOOLTIP = _("Kite completions status")
    DEFAULT_STATUS = _('not reachable')
    ID = 'kite_status'

    def __init__(self, parent, provider):
        self.provider = provider
        self.tooltip = self.BASE_TOOLTIP
        self.installation_thread = KiteInstallationThread(self)
        super().__init__(parent)
        is_installed, _ = check_if_kite_installed()
        self.setVisible(is_installed)

        # Installation dialog
        self.installer = KiteInstallerDialog(
            self,
            self.installation_thread)

        self.installation_thread.sig_installation_status.connect(
            self.set_value)
        self.sig_clicked.connect(self.show_installation_dialog)

    def set_value(self, value):
        """Return Kite completions state."""
        kite_enabled = self.provider.get_conf(('enabled_providers', 'kite'),
                                              default=True,
                                              section='completions')
        is_installing = self.is_installing()
        cancelled_or_errored = self.installation_cancelled_or_errored()

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

    def get_icon(self):
        return ima.icon('kite')

    @Slot()
    def show_installation_dialog(self):
        """Show installation dialog."""
        installed, path = check_if_kite_installed()
        if not installed and not running_under_pytest():
            self.installer.show()

    def is_installing(self):
        """Check if an installation is taking place."""
        return (self.installation_thread.isRunning()
                and not self.installation_thread.cancelled)

    def installation_cancelled_or_errored(self):
        """Check if an installation was cancelled or failed."""
        return self.installation_thread.cancelled_or_errored()

    @Slot()
    def mainwindow_setup_finished(self):
        """
        This is called after the main window setup finishes, and the
        third time Spyder is started, to show Kite's installation dialog
        and onboarding if necessary.
        """
        spyder_runs = self.provider.get_conf('spyder_runs')
        if spyder_runs == 3:
            self.provider._kite_onboarding()

            show_dialog = self.provider.get_conf('show_installation_dialog')
            if show_dialog:
                # Only show the dialog once at startup
                self.provider.set_conf('show_installation_dialog', False)
                self.show_installation_dialog()
        else:
            if spyder_runs < 3:
                self.provider.set_conf('spyder_runs', spyder_runs + 1)

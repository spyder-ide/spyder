# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language server Status widget.
"""

# Standard library imports
import logging
import os

# Third party imports
from qtpy.QtCore import QPoint, Slot
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import _
from spyder.utils.qthelpers import add_actions, create_action

logger = logging.getLogger(__name__)


# Main constants
class ClientStatus:
    STARTING = 'starting'
    READY = 'ready'
    RESTARTING = 'restarting'
    DOWN = 'down'

    STRINGS_FOR_TRANSLATION = {
        STARTING: _("starting"),
        READY: _("ready"),
        RESTARTING: _("restarting"),
        DOWN: _("down")
    }


class LSPStatusWidget(StatusBarWidget):
    """Status bar widget for LSP  status."""
    ID = 'lsp_status'

    BASE_TOOLTIP = _(
        "Completions, linting, code\n"
        "folding and symbols status."
    )

    STATUS = "LSP {}: {}"

    def __init__(self, parent, provider):
        self.tooltip = self.BASE_TOOLTIP
        super().__init__(parent, show_spinner=True)

        self.provider = provider
        self.current_language = None
        self.menu = QMenu(self)

        # Setup
        self.set_status(status=ClientStatus.STARTING)

        # Signals
        self.sig_clicked.connect(self.show_menu)

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        menu = self.menu
        language = self.current_language.lower()

        if language is not None:
            menu.clear()
            text = _(
                "Restart {} Language Server").format(language.capitalize())
            restart_action = create_action(
                self,
                text=text,
                triggered=lambda: self.provider.restart_lsp(language,
                                                            force=True),
            )
            add_actions(menu, [restart_action])
            rect = self.contentsRect()
            os_height = 7 if os.name == 'nt' else 12
            pos = self.mapToGlobal(
                rect.topLeft() + QPoint(-40, -rect.height() - os_height))
            menu.popup(pos)

    def set_status(self, lsp_language=None, status=None):
        """Set LSP status."""
        if status in [ClientStatus.STARTING, ClientStatus.RESTARTING]:
            self.spinner.show()
            self.spinner.start()
        else:
            self.spinner.hide()
            self.spinner.stop()

        if status is None:
            status = ClientStatus.STRINGS_FOR_TRANSLATION[
                ClientStatus.STARTING]
        else:
            status = ClientStatus.STRINGS_FOR_TRANSLATION[status]

        if lsp_language is not None:
            status = self.STATUS.format(lsp_language.capitalize(), status)
        self.set_value(status)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def get_icon(self):
        return self.create_icon('lspserver')

    @Slot()
    def update_status(self, lsp_language=None, status=None):
        """Update status message."""
        # This case can only happen when switching files in the editor
        if lsp_language is None and status is None:
            lsp_language = self.current_language.lower()
            if not self.provider.clients.get(lsp_language, None):
                self.setVisible(False)
            else:
                status = self.provider.clients_statusbar.get(
                    lsp_language,
                    ClientStatus.STARTING
                )
                self.set_status(lsp_language, status)
                self.setVisible(True)
            return

        # Don't update the status in case the editor and LSP languages
        # are different.
        if (self.current_language is None or
                self.current_language.lower() != lsp_language):
            return
        else:
            self.set_status(self.current_language, status)
            self.setVisible(True)

    def set_current_language(self, language):
        self.current_language = language
        self.update_status()

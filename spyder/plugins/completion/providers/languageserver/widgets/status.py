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
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import add_actions, create_action
from spyder.widgets.status import StatusBarWidget

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

    BASE_TOOLTIP = _(
        "Completions, linting, code\n"
        "folding and symbols status."
    )

    STATUS = "LSP {}: {}"

    def __init__(self, parent, statusbar, plugin):
        self.tooltip = self.BASE_TOOLTIP
        super(LSPStatusWidget, self).__init__(
            parent, statusbar,
            icon=ima.icon('lspserver'),
            spinner=True
        )

        self.plugin = plugin
        self.menu = QMenu(self)

        # Setup
        self.set_status(status=ClientStatus.STARTING)

        # Signals
        self.sig_clicked.connect(self.show_menu)

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        menu = self.menu
        language = self.get_current_editor_language().lower()

        if language is not None:
            menu.clear()
            text = _(
                "Restart {} Language Server").format(language.capitalize())
            restart_action = create_action(
                self,
                text=text,
                triggered=lambda: self.plugin.restart_lsp(language, force=True),
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
            status = self.STATUS.format(lsp_language, status)
        self.set_value(status)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    @Slot()
    def update_status(self, lsp_language=None, status=None):
        """Update status message."""
        editor_language = self.get_current_editor_language()

        # This case can only happen when switching files in the editor
        if lsp_language is None and status is None:
            lsp_language = editor_language.lower()
            if not self.plugin.clients.get(lsp_language, None):
                self.setVisible(False)
            else:
                status = self.plugin.clients_statusbar.get(
                    lsp_language,
                    ClientStatus.STARTING
                )
                self.set_status(editor_language, status)
                self.setVisible(True)
            return

        # Don't update the status in case the editor and LSP languages
        # are different.
        if editor_language.lower() != lsp_language:
            return
        else:
            self.set_status(editor_language, status)
            self.setVisible(True)

    def get_current_editor_language(self):
        """Get current LSP language."""
        main = self.plugin.main
        language = _('Unknown')

        if main and main.editor:
            codeeditor = main.editor.get_current_editor()
            if codeeditor is not None:
                language = codeeditor.language
        return language

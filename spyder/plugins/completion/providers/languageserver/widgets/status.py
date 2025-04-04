# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language server Status widget.
"""

# Third party imports
from qtpy.QtCore import QPoint, Slot
from qtpy.QtGui import QFontMetrics

# Local imports
from spyder.api.widgets.menus import SpyderMenu
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import _
from spyder.utils.stylesheet import MAC, WIN


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
    INTERACT_ON_CLICK = True

    BASE_TOOLTIP = _(
        "Completions, linting, code\n"
        "folding and symbols status."
    )

    STATUS = "LSP: {}"

    def __init__(self, parent, provider):
        self.tooltip = self.BASE_TOOLTIP
        super().__init__(parent, show_spinner=True)

        self.provider = provider
        self.current_language = None
        self.menu = SpyderMenu(self)

        # Setup
        self.set_status(status=ClientStatus.STARTING)

        # Signals
        self.sig_clicked.connect(self.show_menu)

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        
        if self.current_language is None:
            return

        self.menu.clear_actions()
        language = self.current_language.lower()
        text = _("Restart {} Language Server").format(language.capitalize())
        restart_action = self.create_action(
            "restart_server",
            text=text,
            triggered=lambda: self.provider.restart_lsp(language, force=True),
            register_action=False,
        )
        self.add_item_to_menu(restart_action, self.menu)

        x_offset = (
            # Margin of menu items to left and right
            2 * SpyderMenu.HORIZONTAL_MARGIN_FOR_ITEMS
            # Padding of menu items to left and right
            + 2 * SpyderMenu.HORIZONTAL_PADDING_FOR_ITEMS
        )
        y_offset = 4 if MAC else (3 if WIN else 2)

        metrics = QFontMetrics(self.font())
        rect = self.contentsRect()
        pos = self.mapToGlobal(
            rect.topLeft()
            + QPoint(
                -metrics.width(text) // 2 + x_offset,
                -2 * self.parent().height() + y_offset,
            )
        )

        self.menu.popup(pos)

    def set_status(self, lsp_language=None, status=None):
        """Set LSP status."""
        # Spinner
        if status in [ClientStatus.STARTING, ClientStatus.RESTARTING]:
            self.spinner.show()
            self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.hide()

        # Icon
        if status == ClientStatus.READY:
            self._icon = self.create_icon('lspserver.ready')
        elif status in [ClientStatus.DOWN, ClientStatus.STARTING,
                        ClientStatus.RESTARTING]:
            self._icon = self.create_icon('lspserver.down')
        self.set_icon()

        # Language
        if lsp_language is not None:
            self.set_value(self.STATUS.format(lsp_language.capitalize()))

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def get_icon(self):
        return self.create_icon('lspserver.down')

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

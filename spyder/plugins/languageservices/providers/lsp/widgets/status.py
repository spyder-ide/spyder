# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widget showing the language server state of the current
file's language."""

from __future__ import annotations

# Third party imports
from qtpy.QtCore import QPoint, Slot
from qtpy.QtGui import QFontMetrics

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.menus import SpyderMenu
from spyder.api.widgets.status import StatusBarWidget
from spyder.plugins.languageservices.api.provider import ProviderStatus
from spyder.utils.stylesheet import MAC, WIN

STATUS_LABELS = {
    ProviderStatus.STARTING: _("starting"),
    ProviderStatus.READY: _("ready"),
    ProviderStatus.DOWN: _("down"),
    ProviderStatus.STOPPED: _("stopped"),
}


class LSPStatusWidget(StatusBarWidget):
    """Status of the language servers serving the current file."""

    ID = "lsp_status"
    INTERACT_ON_CLICK = True

    BASE_TOOLTIP = _("Completions, linting, code\nfolding and symbols status.")
    STATUS = "LSP: {}"

    def __init__(self, parent, provider):
        self.tooltip = self.BASE_TOOLTIP
        super().__init__(parent, show_spinner=True)

        self.provider = provider
        self.current_language = None
        self.menu = SpyderMenu(self)
        self._statuses = {}

        self.set_status(ProviderStatus.STARTING)
        self.setVisible(False)

        self.sig_clicked.connect(self.show_menu)
        provider.sig_status_changed.connect(self.update_status)
        if provider.plugin is not None:
            provider.plugin.sig_current_language_changed.connect(
                self.set_current_language
            )

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        language = self.current_language
        if language is None:
            return

        from spyder.plugins.languageservices.plugin import dispatch

        self.menu.clear_actions()
        text = _("Restart {} Language Server").format(language.name)
        restart_action = self.create_action(
            "restart_server",
            text=text,
            triggered=lambda: dispatch(self.provider.restart_language)(language),
            register_action=False,
        )
        self.add_item_to_menu(restart_action, self.menu)

        x_offset = (
            2 * SpyderMenu.HORIZONTAL_MARGIN_FOR_ITEMS
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

    def set_status(self, status, language=None):
        """Show ``status`` (and the language name)."""
        if status is ProviderStatus.STARTING:
            self.spinner.show()
            self.spinner.start()
        else:
            self.spinner.stop()
            self.spinner.hide()

        if status is ProviderStatus.READY:
            self._icon = self.create_icon("lspserver.ready")
        else:
            self._icon = self.create_icon("lspserver.down")
        self.set_icon()

        if language is not None:
            self.set_value(self.STATUS.format(language.name))
        self.tooltip = "{}\n{}".format(
            self.BASE_TOOLTIP, STATUS_LABELS.get(status, status)
        )

    def get_tooltip(self):
        return self.tooltip

    def get_icon(self):
        return self.create_icon("lspserver.down")

    @Slot(object, str)
    def update_status(self, language, status):
        """Record the status of ``language`` and show it if current."""
        status = ProviderStatus(status)
        self._statuses[language] = status
        if language == self.current_language:
            self.set_status(status, language)
            self.setVisible(True)

    @Slot(object)
    def set_current_language(self, language):
        self.current_language = language
        if language is None or not self.provider.servers_for(language):
            self.setVisible(False)
            return
        status = self._statuses.get(language, ProviderStatus.STARTING)
        self.set_status(status, language)
        self.setVisible(True)

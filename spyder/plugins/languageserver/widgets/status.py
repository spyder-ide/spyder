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


class LSPStatusWidget(StatusBarWidget):
    """Status bar widget for LSP  status."""

    BASE_TOOLTIP = _(
        "Completions, linting, code\n"
        "folding and symbols status."
    )
    STATUS = "LSP {}: {}"

    def __init__(self, parent, statusbar, container):
        self.tooltip = self.BASE_TOOLTIP
        super(LSPStatusWidget, self).__init__(
            parent, statusbar, icon=ima.icon('lspserver'))

        self.current_editor_language = _("Unknown")
        self.container = container
        self.menu = QMenu(self)

        # Setup
        self.set_value('starting...')

        # Signals
        self.sig_clicked.connect(self.show_menu)

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        menu = self.menu
        language = self.current_editor_language

        if language is not None:
            menu.clear()
            text = _(
                "Restart {} Language Server").format(language.capitalize())
            restart_action = create_action(
                self,
                text=text,
                triggered=lambda: self.container.provider.restart_lsp(
                    language, force=True),
            )
            add_actions(menu, [restart_action])
            rect = self.contentsRect()
            os_height = 7 if os.name == 'nt' else 12
            pos = self.mapToGlobal(
                rect.topLeft() + QPoint(-40, -rect.height() - os_height))
            menu.popup(pos)

    def set_value(self, value):
        """Return lsp state."""
        super(LSPStatusWidget, self).set_value(value)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    @Slot()
    def update_status(self, lsp_language=None, status=None):
        """Update status message."""
        editor_language = self.current_editor_language

        # This case can only happen when switching files in the editor
        if lsp_language is None and status is None:
            lsp_language = editor_language
            if not self.container.provider.clients.get(lsp_language, None):
                self.setVisible(False)
            else:
                status = self.container.provider.clients_status.get(
                    lsp_language, _("starting..."))
                self.set_value(self.STATUS.format(editor_language, status))
                self.setVisible(True)
            return

        # Don't update the status in case the editor and LSP languages
        # are different.
        if editor_language != lsp_language:
            return
        else:
            self.set_value(self.STATUS.format(editor_language, status))
            self.setVisible(True)

    def update_current_editor_language(self, language):
        self.current_editor_language = language.lower()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language server Status widget for pyls completions.
"""

# Standard library imports
import logging

# Third party imports
from qtpy.QtCore import QPoint
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
    DEFAULT_STATUS = _('off')

    def __init__(self, parent, statusbar, plugin):
        self.tooltip = self.BASE_TOOLTIP
        super(LSPStatusWidget, self).__init__(
            parent, statusbar, icon=ima.icon('lspserver'))

        self.plugin = plugin
        self.menu = QMenu(self)

        # Setup
        self.set_value('starting...')

        # Signals
        self.sig_clicked.connect(self.show_menu)

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        menu = self.menu
        language = self.get_current_language()

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
            pos = self.mapToGlobal(
                rect.topLeft() + QPoint(-40, -rect.height() - 12))
            menu.popup(pos)

    def set_value(self, value):
        """Return lsp state."""
        super(LSPStatusWidget, self).set_value(value)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

    def update_status(self):
        """
        Check language of current editor file to hide/show status widget.
        """
        language = self.get_current_language()
        if self.plugin.clients.get(language, False):
            self.setVisible(True)
        else:
            self.setVisible(False)

    def get_current_language(self):
        """Get current LSP language."""
        main = self.plugin.main
        lsp_language = None

        if main and main.editor:
            codeeditor = main.editor.get_current_editor()
            lsp_language = codeeditor.language.lower()
        return lsp_language

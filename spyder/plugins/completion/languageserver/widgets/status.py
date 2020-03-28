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

    BASE_TOOLTIP = _("PyLS completions status")
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
        """
        Display a PyLS status bar widget menu, if pyls is down.
        """
        plugin = self.plugin
        menu = self.menu
        client = plugin.clients['python']

        if (client['status'] != plugin.RUNNING
                or client['instance'].lsp_server.poll() is not None):
            menu.clear()
            restart_action = create_action(
                self,
                text=_("Restart python language server"),
                triggered=lambda: self.plugin.restart_lsp('python', force=True),
            )
            add_actions(menu, [restart_action])
            rect = self.contentsRect()
            pos = self.mapToGlobal(
                rect.topLeft() + QPoint(0, -rect.height()))
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
        main = self.plugin.main
        if main:
            if main.editor:
                filename = main.editor.get_current_filename()
                self.setVisible(filename.endswith('.py'))

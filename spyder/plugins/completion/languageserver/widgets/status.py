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
from qtpy.QtWidgets import QMenu

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
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

    def set_value(self, value):
        """Return lsp state."""
        super(LSPStatusWidget, self).set_value(value)

    def get_tooltip(self):
        """Reimplementation to get a dynamic tooltip."""
        return self.tooltip

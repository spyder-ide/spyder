# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Help Plugin Configuration Page."""

# Third party imports
from qtpy.QtWidgets import QGroupBox, QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.api.preferences import PluginConfigPage


class HistoryConfigPage(PluginConfigPage):
    """Configuration page for History plugin."""

    def get_icon(self):
        """Get icon to use in Configurations dialog."""
        return ima.icon('history')

    def setup_page(self):
        """Setup config page widgets and options."""
        sourcecode_group = QGroupBox(_("Display"))
        wrap_mode_box = self.create_checkbox(_("Wrap lines"), 'wrap')
        linenumbers_mode_box = self.create_checkbox(_("Show line numbers"),
                                                    'line_numbers')
        go_to_eof_box = self.create_checkbox(
                        _("Scroll automatically to last entry"), 'go_to_eof')

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_layout.addWidget(linenumbers_mode_box)
        sourcecode_layout.addWidget(go_to_eof_box)
        sourcecode_group.setLayout(sourcecode_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

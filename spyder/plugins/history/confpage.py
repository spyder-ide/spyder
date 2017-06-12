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
from spyder.utils import icon_manager as ima
from spyder.api.preferences import PluginConfigPage


class HistoryConfigPage(PluginConfigPage):
    def get_icon(self):
        return ima.icon('history')
    
    def setup_page(self):
        settings_group = QGroupBox(_("Settings"))
        hist_spin = self.create_spinbox(
                            _("History depth: "), _(" entries"),
                            'max_entries', min_=10, max_=10000, step=10,
                            tip=_("Set maximum line count"))

        sourcecode_group = QGroupBox(_("Source code"))
        wrap_mode_box = self.create_checkbox(_("Wrap lines"), 'wrap')
        go_to_eof_box = self.create_checkbox(
                        _("Scroll automatically to last entry"), 'go_to_eof')

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(hist_spin)
        settings_group.setLayout(settings_layout)

        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_layout.addWidget(go_to_eof_box)
        sourcecode_group.setLayout(sourcecode_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(settings_group)
        vlayout.addWidget(sourcecode_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

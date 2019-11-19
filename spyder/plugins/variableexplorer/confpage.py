# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Variable Explorer Plugin Configuration Page."""

# Third party imports
from qtpy.QtWidgets import QGroupBox, QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.api.preferences import PluginConfigPage

class VariableExplorerConfigPage(PluginConfigPage):

    def setup_page(self):
        filter_group = QGroupBox(_("Filter"))
        filter_data = [
            ('exclude_private', _("Exclude private references")),
            ('exclude_capitalized', _("Exclude capitalized references")),
            ('exclude_uppercase', _("Exclude all-uppercase references")),
            ('exclude_unsupported', _("Exclude unsupported data types")),
            ('exclude_callables_and_modules',
             _("Exclude callables and modules"))
        ]
        filter_boxes = [self.create_checkbox(text, option)
                        for option, text in filter_data]

        display_group = QGroupBox(_("Display"))
        display_data = [('minmax', _("Show arrays min/max"), '')]
        display_boxes = [self.create_checkbox(text, option, tip=tip)
                         for option, text, tip in display_data]

        filter_layout = QVBoxLayout()
        for box in filter_boxes:
            filter_layout.addWidget(box)
        filter_group.setLayout(filter_layout)

        display_layout = QVBoxLayout()
        for box in display_boxes:
            display_layout.addWidget(box)
        display_group.setLayout(display_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(filter_group)
        vlayout.addWidget(display_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

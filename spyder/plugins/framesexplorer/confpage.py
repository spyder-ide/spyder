# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Frames Explorer Plugin Configuration Page."""

# Third party imports
from qtpy.QtWidgets import QGroupBox, QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.api.preferences import PluginConfigPage


class FramesExplorerConfigPage(PluginConfigPage):

    def setup_page(self):
        filter_group = QGroupBox(_("Filter"))
        filter_data = [
            ('exclude_internal', _("Exclude internal threads and frames")),
            ('capture_locals', _("Capture frames locals")),
            ('show_locals_on_click',
             _("Show locals in Variable explorer when frame is selected")),
        ]
        filter_boxes = [self.create_checkbox(text, option)
                        for option, text in filter_data]

        filter_layout = QVBoxLayout()
        for box in filter_boxes:
            filter_layout.addWidget(box)
        filter_group.setLayout(filter_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(filter_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

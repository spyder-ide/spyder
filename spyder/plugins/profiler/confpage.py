# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Profiler config page."""

from qtpy.QtWidgets import QVBoxLayout

from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _


class ProfilerConfigPage(PluginConfigPage):
    def setup_page(self):
        switch_to_plugin_cb = self.create_checkbox(
            _("Open profiler when profiling finishes"),
            "switch_to_plugin",
            tip=_(
                "This option switches to the profiler plugin "
                "when a profiling has ended."
            ),
        )

        slow_spin = self.create_spinbox(
            _("Maximum number of items displayed with large local time"),
            "",
            'n_slow_children',
            min_=1,
            max_=1000,
            step=1
        )

        vlayout = QVBoxLayout()
        vlayout.addWidget(switch_to_plugin_cb)
        vlayout.addWidget(slow_spin)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

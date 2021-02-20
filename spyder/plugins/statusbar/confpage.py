# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Status bar entry in Preferences.
"""

from qtpy.QtWidgets import QGridLayout, QGroupBox, QVBoxLayout

from spyder.api.translations import get_translation
from spyder.api.preferences import PluginConfigPage


_ = get_translation('spyder')


class StatusBarConfigPage(PluginConfigPage):

    def setup_page(self):
        newcb = self.create_checkbox

        # --- Status bar
        sbar_group = QGroupBox(_("Display"))
        show_status_bar = newcb(_("Show status bar"), 'show_status_bar')

        memory_box = newcb(_("Show memory usage every"), 'memory_usage/enable',
                           tip=self.plugin.mem_status.toolTip())
        memory_spin = self.create_spinbox("", _(" ms"), 'memory_usage/timeout',
                                          min_=100, max_=1000000, step=100)
        memory_box.toggled.connect(memory_spin.setEnabled)
        memory_spin.setEnabled(self.get_option('memory_usage/enable'))

        cpu_box = newcb(_("Show CPU usage every"), 'cpu_usage/enable',
                        tip=self.plugin.cpu_status.toolTip())
        cpu_spin = self.create_spinbox("", _(" ms"), 'cpu_usage/timeout',
                                       min_=100, max_=1000000, step=100)
        cpu_box.toggled.connect(cpu_spin.setEnabled)
        cpu_spin.setEnabled(self.get_option('cpu_usage/enable'))

        clock_box = newcb(_("Show clock"), 'clock/enable')

        status_bar_o = self.get_option('show_status_bar')
        show_status_bar.toggled.connect(memory_box.setEnabled)
        show_status_bar.toggled.connect(memory_spin.setEnabled)
        show_status_bar.toggled.connect(cpu_box.setEnabled)
        show_status_bar.toggled.connect(cpu_spin.setEnabled)
        show_status_bar.toggled.connect(clock_box.setEnabled)

        memory_box.setEnabled(status_bar_o)
        memory_spin.setEnabled(status_bar_o)
        cpu_box.setEnabled(status_bar_o)
        cpu_spin.setEnabled(status_bar_o)
        clock_box.setEnabled(status_bar_o)

        # Layout status bar
        cpu_memory_layout = QGridLayout()
        cpu_memory_layout.addWidget(memory_box, 0, 0)
        cpu_memory_layout.addWidget(memory_spin, 0, 1)
        cpu_memory_layout.addWidget(cpu_box, 1, 0)
        cpu_memory_layout.addWidget(cpu_spin, 1, 1)
        cpu_memory_layout.addWidget(clock_box, 2, 0)

        sbar_layout = QVBoxLayout()
        sbar_layout.addWidget(show_status_bar)
        sbar_layout.addLayout(cpu_memory_layout)
        sbar_group.setLayout(sbar_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(sbar_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

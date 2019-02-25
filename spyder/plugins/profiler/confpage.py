# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Profiler config page."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _
from spyder.plugins.profiler.widgets.profilergui import ProfilerWidget


class ProfilerConfigPage(PluginConfigPage):
    def setup_page(self):
        results_group = QGroupBox(_("Results"))
        results_label1 = QLabel(_("Profiler plugin results "
                                  "(the output of python's profile/cProfile)\n"
                                  "are stored here:"))
        results_label1.setWordWrap(True)

        # Warning: do not try to regroup the following QLabel contents with
        # widgets above -- this string was isolated here in a single QLabel
        # on purpose: to fix Issue 863
        results_label2 = QLabel(ProfilerWidget.DATAPATH)

        results_label2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        results_label2.setWordWrap(True)

        results_layout = QVBoxLayout()
        results_layout.addWidget(results_label1)
        results_layout.addWidget(results_label2)
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

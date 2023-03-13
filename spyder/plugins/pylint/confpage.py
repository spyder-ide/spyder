# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pylint config page."""

# Third-party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import get_translation
from spyder.plugins.pylint.main_widget import (MAX_HISTORY_ENTRIES,
                                               MIN_HISTORY_ENTRIES,
                                               PylintWidget)

# Localization
_ = get_translation("spyder")


class PylintConfigPage(PluginConfigPage):

    def setup_page(self):
        hist_group = QGroupBox(_("History"))
        hist_label1 = QLabel(_("Choose how many results you want to store in "
                               "the history results, pick a number between "
                               "1-100."))
        hist_label1.setWordWrap(True)
        hist_spin = self.create_spinbox(
            _("History: "),
            _(" results"),
            "max_entries",
            self.get_option('max_entries'),
            min_=MIN_HISTORY_ENTRIES,
            max_=MAX_HISTORY_ENTRIES,
            step=1,
        )

        results_group = QGroupBox(_("Results"))

        # Warning: do not try to regroup the following QLabel contents with
        # widgets above -- this string was isolated here in a single QLabel
        # on purpose: to fix spyder-ide/spyder#863.
        results_label2 = QLabel(PylintWidget.DATAPATH)

        results_label2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        results_label2.setWordWrap(True)

        hist_layout = QVBoxLayout()
        hist_layout.addWidget(hist_label1)
        hist_layout.addWidget(hist_spin)
        hist_group.setLayout(hist_layout)

        results_layout = QVBoxLayout()
        results_layout.addWidget(results_label2)
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hist_group)
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

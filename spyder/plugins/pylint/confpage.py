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
        settings_group = QGroupBox(_("Settings"))
        save_box = self.create_checkbox(_("Save file before analyzing it"),
                                        'save_before', default=True)

        hist_group = QGroupBox(_("History"))
        hist_label1 = QLabel(_("The following option will be applied at next "
                               "startup."))
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
        results_label1 = QLabel(_("Results are stored here:"))
        results_label1.setWordWrap(True)

        # Warning: do not try to regroup the following QLabel contents with
        # widgets above -- this string was isolated here in a single QLabel
        # on purpose: to fix spyder-ide/spyder#863.
        results_label2 = QLabel(PylintWidget.DATAPATH)

        results_label2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        results_label2.setWordWrap(True)

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(save_box)
        settings_group.setLayout(settings_layout)

        hist_layout = QVBoxLayout()
        hist_layout.addWidget(hist_label1)
        hist_layout.addWidget(hist_spin)
        hist_group.setLayout(hist_layout)

        results_layout = QVBoxLayout()
        results_layout.addWidget(results_label1)
        results_layout.addWidget(results_label2)
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(settings_group)
        vlayout.addWidget(hist_group)
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

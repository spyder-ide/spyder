# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pylint config page."""

# Third-party imports
from qtpy.QtWidgets import QGroupBox, QVBoxLayout

# Local imports
from .linters import LINTERS
from spyder.api.preferences import PluginConfigPage
from spyder.api.translations import _


class PylintConfigPage(PluginConfigPage):
    def setup_page(self) -> None:
        linters_group = QGroupBox(_("Tool selection"))
        linters_layout = QVBoxLayout(linters_group)

        for linter in LINTERS:
            checkbox = self.create_checkbox(
                linter.name,
                f"use_{linter.name.lower()}",
            )
            available = linter.is_available()
            checkbox.setEnabled(available)
            if not available:
                checkbox.setToolTip(_("Tool is not available"))
            linters_layout.addWidget(checkbox)

        layout = QVBoxLayout(self)
        layout.addWidget(linters_group)
        layout.addStretch(1)

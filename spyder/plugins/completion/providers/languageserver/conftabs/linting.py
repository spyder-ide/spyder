# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol linting configuration tab.
"""

# Third party imports
from qtpy.QtWidgets import QButtonGroup, QGroupBox, QLabel, QVBoxLayout

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _


class LintingConfigTab(SpyderPreferencesTab):
    """Linting configuration tab."""

    TITLE = _('Linting')

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        linting_label = QLabel(_("Spyder can optionally highlight syntax "
                                 "errors and possible problems with your "
                                 "code in the editor."))
        linting_label.setOpenExternalLinks(True)
        linting_label.setWordWrap(True)

        linting_select_group = QGroupBox(_("Linting"))
        linting_select_label = QLabel(
            _("Choose the linting:")
        )
        linting_select_label.setWordWrap(True)
        linting_bg = QButtonGroup(linting_select_group)
        basic_linting_radio = self.create_radiobutton(
            _("Basic linting"),
            'pyflakes',
            button_group=linting_bg
        )
        flake_linting_radio = self.create_radiobutton(
            _("Flake8 linting"),
            'flake8',
            button_group=linting_bg
        )
        """
        disable_linting_radio = self.create_radiobutton(
            _("No linting"),
            'pyflakes',
            button_group=linting_bg
        )
        """
        linting_select_layout = QVBoxLayout()
        linting_select_layout.addWidget(linting_select_label)
        linting_select_layout.addWidget(basic_linting_radio)
        linting_select_layout.addWidget(flake_linting_radio)
        #linting_select_layout.addWidget(disable_linting_radio)
        linting_select_group.setLayout(linting_select_layout)


        linting_check = self.create_checkbox(
            _("Enable basic linting"),
            'pyflakes')
        underline_errors_box = newcb(
            _("Underline errors and warnings"),
            'underline_errors',
            section='editor')
        linting_complexity_box = self.create_checkbox(
            _("Enable complexity linting with the Mccabe package"),
            'mccabe')

        # Linting layout
        linting_layout = QVBoxLayout()
        linting_layout.addWidget(linting_label)
        linting_layout.addWidget(linting_select_group)
        linting_layout.addWidget(underline_errors_box)
        linting_layout.addWidget(linting_complexity_box)
        self.setLayout(linting_layout)

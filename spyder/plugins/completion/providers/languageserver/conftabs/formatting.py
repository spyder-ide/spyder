# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol configuration tabs.
"""

# Third party imports
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _


class FormattingConfigTab(SpyderPreferencesTab):
    """Code formatting tab."""

    TITLE = _('Code formatting')

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        pep_url = (
            '<a href="https://www.python.org/dev/peps/pep-0008">PEP 8</a>'
        )

        self.code_style_max_line_length = self.create_spinbox(
            _("Maximum allowed line length:"), None,
            'flake8/max_line_length', min_=10, max_=500, step=1,
            tip=_("Default is 79"))

        vertical_line_box = newcb(
            _("Show vertical line at that length"), 'edge_line',
            section='editor')

        # Maximum allowed line length layout
        line_length_group = QGroupBox(_("Line length"))
        line_length_layout = QVBoxLayout()
        line_length_layout.addWidget(self.code_style_max_line_length)
        line_length_layout.addWidget(vertical_line_box)
        line_length_group.setLayout(line_length_layout)

        # Code formatting label
        autopep8_url = (
            "<a href='https://github.com/hhatto/autopep8'>Autopep8</a>"
        )
        yapf_url = (
            "<a href='https://github.com/google/yapf'>Yapf</a>"
        )
        black_url = (
            "<a href='https://black.readthedocs.io/en/stable'>Black</a>"
        )
        code_fmt_label = QLabel(
            _("Spyder can use {0} or {1} to format your code for "
              "conformance to the {2} convention.").format(
                  autopep8_url, black_url, pep_url))
        code_fmt_label.setOpenExternalLinks(True)
        code_fmt_label.setWordWrap(True)

        # Code formatting providers
        code_fmt_provider = self.create_combobox(
            _("Choose the code formatting provider: "),
            (("autopep8", 'autopep8'),
             ("black", 'black')),
            'formatting')

        # Autoformat on save
        format_on_save_box = newcb(
            _("Autoformat files on save"),
            'format_on_save',
            tip=_("If enabled, autoformatting will take place when "
                  "saving a file"))

        # Code formatting layout
        code_fmt_group = QGroupBox(_("Code formatting"))
        code_fmt_layout = QVBoxLayout()
        code_fmt_layout.addWidget(code_fmt_label)
        code_fmt_layout.addWidget(code_fmt_provider)
        code_fmt_layout.addWidget(format_on_save_box)
        code_fmt_group.setLayout(code_fmt_layout)

        code_style_fmt_layout = QVBoxLayout()
        code_style_fmt_layout.addWidget(code_fmt_group)
        code_style_fmt_layout.addWidget(line_length_group)
        self.setLayout(code_style_fmt_layout)

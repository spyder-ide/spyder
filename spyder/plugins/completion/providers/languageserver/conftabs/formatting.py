# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol configuration tabs.
"""

# Standard library imports
import re

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QGroupBox, QGridLayout, QLabel, QMessageBox,
                            QVBoxLayout, QWidget)

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _


class FormattingStyleConfigTab(SpyderPreferencesTab):
    """Code style and formatting tab."""

    TITLE = _('Code style and formatting')

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        pep_url = (
            '<a href="https://www.python.org/dev/peps/pep-0008">PEP 8</a>')
        code_style_codes_url = _(
            "<a href='http://pycodestyle.pycqa.org/en/stable"
            "/intro.html#error-codes'>pycodestyle error codes</a>")
        code_style_label = QLabel(
            _("Spyder can use pycodestyle to analyze your code for "
              "conformance to the {} convention. You can also "
              "manually show or hide specific warnings by their "
              "{}.").format(pep_url, code_style_codes_url))
        code_style_label.setOpenExternalLinks(True)
        code_style_label.setWordWrap(True)

        # Code style checkbox
        self.code_style_check = self.create_checkbox(
            _("Enable code style linting"),
            'pycodestyle')

        # Code style options
        self.code_style_filenames_match = self.create_lineedit(
            _("Only check filenames matching these patterns:"),
            'pycodestyle/filename', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Check Python files: *.py"))
        self.code_style_exclude = self.create_lineedit(
            _("Exclude files or directories matching these patterns:"),
            'pycodestyle/exclude', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Exclude all test files: (?!test_).*\\.py"))
        code_style_select = self.create_lineedit(
            _("Show the following errors or warnings:").format(
                code_style_codes_url),
            'pycodestyle/select', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: E113, W391"))
        code_style_ignore = self.create_lineedit(
            _("Ignore the following errors or warnings:"),
            'pycodestyle/ignore', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: E201, E303"))
        self.code_style_max_line_length = self.create_spinbox(
            _("Maximum allowed line length:"), None,
            'pycodestyle/max_line_length', min_=10, max_=500, step=1,
            tip=_("Default is 79"))

        vertical_line_box = newcb(
            _("Show vertical line at that length"), 'edge_line',
            section='editor')

        # Code style layout
        code_style_g_layout = QGridLayout()
        code_style_g_layout.addWidget(
            self.code_style_filenames_match.label, 1, 0)
        code_style_g_layout.addWidget(
            self.code_style_filenames_match.textbox, 1, 1)
        code_style_g_layout.addWidget(self.code_style_exclude.label, 2, 0)
        code_style_g_layout.addWidget(self.code_style_exclude.textbox, 2, 1)
        code_style_g_layout.addWidget(code_style_select.label, 3, 0)
        code_style_g_layout.addWidget(code_style_select.textbox, 3, 1)
        code_style_g_layout.addWidget(code_style_ignore.label, 4, 0)
        code_style_g_layout.addWidget(code_style_ignore.textbox, 4, 1)

        # Set Code style options enabled/disabled
        code_style_g_widget = QWidget()
        code_style_g_widget.setLayout(code_style_g_layout)
        code_style_g_widget.setEnabled(self.get_option('pycodestyle'))
        self.code_style_check.toggled.connect(code_style_g_widget.setEnabled)

        # Code style layout
        code_style_group = QGroupBox(_("Code style"))
        code_style_layout = QVBoxLayout()
        code_style_layout.addWidget(code_style_label)
        code_style_layout.addWidget(self.code_style_check)
        code_style_layout.addWidget(code_style_g_widget)
        code_style_group.setLayout(code_style_layout)

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
            _("Spyder can use {0}, {1} or {2} to format your code for "
              "conformance to the {3} convention.").format(
                  autopep8_url, yapf_url, black_url, pep_url))
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
        code_style_fmt_layout.addWidget(code_style_group)
        code_style_fmt_layout.addWidget(code_fmt_group)
        code_style_fmt_layout.addWidget(line_length_group)
        self.setLayout(code_style_fmt_layout)

    def report_invalid_regex(self, files=True):
        """
        Report that excluded files/directories should be valid regular
        expressions.
        """
        msg = _('Directory patterns listed for exclusion should be valid '
                'regular expressions')
        if files:
            msg = _('File patterns listed for exclusion should be valid '
                    'regular expressions')

        QMessageBox.critical(self, _("Error"), msg)

    def is_valid(self):
        # Check regex of code style options
        try:
            code_style_filenames_matches = (
                self.code_style_filenames_match.textbox.text().split(","))
            for match in code_style_filenames_matches:
                re.compile(match.strip())
        except re.error:
            self.report_invalid_regex()
            return False

        try:
            code_style_excludes = (
                self.code_style_exclude.textbox.text().split(","))
            for match in code_style_excludes:
                re.compile(match.strip())
        except re.error:
            self.report_invalid_regex(files=False)
            return False
        return True

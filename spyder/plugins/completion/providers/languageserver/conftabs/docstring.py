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
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (QGridLayout, QLabel, QMessageBox, QVBoxLayout,
                            QWidget)

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _


class DocstringConfigTab(SpyderPreferencesTab):
    """Docstring style configuration tab."""

    TITLE = _('Docstring style')

    def __init__(self, parent):
        super().__init__(parent)

        numpy_url = (
            "<a href='https://numpydoc.readthedocs.io/en/"
            "latest/format.html'>Numpy</a>")
        pep257_url = (
            "<a href='https://www.python.org/dev/peps/pep-0257/'>PEP 257</a>")
        docstring_style_codes = _(
            "<a href='http://www.pydocstyle.org/en/stable"
            "/error_codes.html'>page</a>")
        docstring_style_label = QLabel(
            _("Here you can decide if you want to perform style analysis on "
              "your docstrings according to the {} or {} conventions. You can "
              "also decide if you want to show or ignore specific errors, "
              "according to the codes found on this {}.").format(
                  numpy_url, pep257_url, docstring_style_codes))
        docstring_style_label.setOpenExternalLinks(True)
        docstring_style_label.setWordWrap(True)

        # Docstring style checkbox
        self.docstring_style_check = self.create_checkbox(
            _("Enable docstring style linting"),
            'pydocstyle')

        # Docstring style options
        docstring_style_convention = self.create_combobox(
            _("Choose the convention used to lint docstrings: "),
            (("Numpy", 'numpy'),
             ("PEP 257", 'pep257'),
             ("Custom", 'custom')),
            'pydocstyle/convention')
        self.docstring_style_select = self.create_lineedit(
            _("Show the following errors:"),
            'pydocstyle/select', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: D413, D414"))
        self.docstring_style_ignore = self.create_lineedit(
            _("Ignore the following errors:"),
            'pydocstyle/ignore', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Example codes: D107, D402"))
        self.docstring_style_match = self.create_lineedit(
            _("Only check filenames matching these patterns:"),
            'pydocstyle/match', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Skip test files: (?!test_).*\\.py"))
        self.docstring_style_match_dir = self.create_lineedit(
            _("Only check in directories matching these patterns:"),
            'pydocstyle/match_dir', alignment=Qt.Horizontal, word_wrap=False,
            placeholder=_("Skip dot directories: [^\\.].*"))

        # Custom option handling
        docstring_style_convention.combobox.currentTextChanged.connect(
                self.setup_docstring_style_convention)
        current_convention = docstring_style_convention.combobox.currentText()
        self.setup_docstring_style_convention(current_convention)

        # Docstring style layout
        docstring_style_g_layout = QGridLayout()
        docstring_style_g_layout.addWidget(
            docstring_style_convention.label, 1, 0)
        docstring_style_g_layout.addWidget(
            docstring_style_convention.combobox, 1, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_select.label, 2, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_select.textbox, 2, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_ignore.label, 3, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_ignore.textbox, 3, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match.label, 4, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match.textbox, 4, 1)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match_dir.label, 5, 0)
        docstring_style_g_layout.addWidget(
            self.docstring_style_match_dir.textbox, 5, 1)

        # Set Docstring style options enabled/disabled
        docstring_style_g_widget = QWidget()
        docstring_style_g_widget.setLayout(docstring_style_g_layout)
        docstring_style_g_widget.setEnabled(self.get_option('pydocstyle'))
        self.docstring_style_check.toggled.connect(
            docstring_style_g_widget.setEnabled)

        # Docstring style layout
        docstring_style_layout = QVBoxLayout()
        docstring_style_layout.addWidget(docstring_style_label)
        docstring_style_layout.addWidget(self.docstring_style_check)
        docstring_style_layout.addWidget(docstring_style_g_widget)

        self.setLayout(docstring_style_layout)

    @Slot(str)
    def setup_docstring_style_convention(self, text):
        """Handle convention changes."""
        if text == 'Custom':
            self.docstring_style_select.label.setText(
                _("Show the following errors:"))
            self.docstring_style_ignore.label.setText(
                _("Ignore the following errors:"))
        else:
            self.docstring_style_select.label.setText(
                _("Show the following errors in addition "
                  "to the specified convention:"))
            self.docstring_style_ignore.label.setText(
                _("Ignore the following errors in addition "
                  "to the specified convention:"))

    def report_invalid_regex(self, files=True):
        """
        Report that matching files/directories should be valid regular
        expressions.
        """
        msg = _('Directory patterns listed for matching should be valid '
                'regular expressions')
        if files:
            msg = _('File patterns listed for matching should be valid '
                    'regular expressions')

        QMessageBox.critical(self, _("Error"), msg)

    def is_valid(self):
        # Check regex of docstring style options
        try:
            docstring_style_match = (
                self.docstring_style_match.textbox.text())
            re.compile(docstring_style_match)
        except re.error:
            self.report_invalid_regex()
            return False

        try:
            docstring_style_match_dir = (
                self.docstring_style_match_dir.textbox.text())
            re.compile(docstring_style_match_dir)
        except re.error:
            self.report_invalid_regex(files=False)
            return False
        return True

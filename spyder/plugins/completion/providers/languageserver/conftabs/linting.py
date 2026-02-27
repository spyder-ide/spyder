# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol linting configuration tab.
"""

# Standard library imports
import re

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QGridLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.api.translations import _
from spyder.utils.stylesheet import AppStyle


class LintingConfigTab(SpyderPreferencesTab):
    """Linting configuration tab."""

    TITLE = _('Linting')

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        linting_label = QLabel(
            _(
                "Spyder can highlight syntax errors and possible problems "
                "with your code in the editor by using one of the providers "
                "below"
            )
        )
        linting_label.setOpenExternalLinks(True)
        linting_label.setWordWrap(True)

        linting_select_group = QGroupBox(_("Provider"))

        linting_bg = QButtonGroup(linting_select_group)
        basic_linting_radio = self.create_radiobutton(
            _("Pyflakes (Basic)"),
            'pyflakes',
            button_group=linting_bg
        )
        flake_linting_radio = self.create_radiobutton(
            _("Flake8 (Intermediate)"),
            'flake8',
            button_group=linting_bg
        )
        ruff_linting_radio = self.create_radiobutton(
            _("Ruff (Advanced)"),
            'ruff',
            button_group=linting_bg
        )
        disable_linting_radio = self.create_radiobutton(
            _("Disable linting"),
            'no_linting',
            button_group=linting_bg
        )

        linting_select_layout = QVBoxLayout()
        linting_select_layout.addSpacing(3 * AppStyle.MarginSize)
        linting_select_layout.addWidget(basic_linting_radio)
        linting_select_layout.addWidget(flake_linting_radio)
        linting_select_layout.addWidget(ruff_linting_radio)
        linting_select_layout.addWidget(disable_linting_radio)
        linting_select_group.setLayout(linting_select_layout)

        additional_options_group = QGroupBox(_("Additional options"))

        underline_errors_box = newcb(
            _("Underline errors and warnings"),
            'underline_errors',
            section='editor')

        additional_options_layout = QVBoxLayout()
        additional_options_layout.addWidget(underline_errors_box)
        additional_options_group.setLayout(additional_options_layout)

        configuration_options_group = QGroupBox(_("Provider options"))
        configuration_options_layout = QVBoxLayout()

        # ruff options
        # This needs to be an attribute of the config page since it is used
        # for `test_mainwindow.py::test_preferences_checkboxes_not_checked_regression`
        self.docstring_style_check = self.create_checkbox(
            _("Enable docstring style linting"), "pydocstyle"
        )
        docstring_style_convention = self.create_combobox(
            _("Convention used to lint docstrings: "),
            (
                ("Numpy", "numpy"),
                ("PEP 257", "pep257"),
                ("Google", "google"),
            ),
            "pydocstyle/convention",
        )
        docstring_style_convention.label.setEnabled(
            self.get_option('pydocstyle')
        )
        docstring_style_convention.combobox.setEnabled(
            self.get_option('pydocstyle')
        )
        self.docstring_style_check.checkbox.toggled.connect(
            docstring_style_convention.label.setEnabled
        )
        self.docstring_style_check.checkbox.toggled.connect(
            docstring_style_convention.combobox.setEnabled
        )

        self.ruff_exclude = self.create_lineedit(
            _("Exclude these files or directories:"),
            'ruff/exclude',
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Exclude test files: (?!test_).*\\.py"),
        )

        ruff_select = self.create_lineedit(
            _("Show these errors or warnings:"),
            'ruff/extendSelect',
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Example codes: E113, W391"),
        )

        ruff_ignore = self.create_lineedit(
            _("Ignore these errors or warnings:"),
            'ruff/extendIgnore',
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Default is: E"),
        )

        ruff_layout = QGridLayout()
        ruff_layout.addWidget(self.docstring_style_check)
        ruff_layout.addWidget(docstring_style_convention.label, 1, 0)
        ruff_layout.addWidget(docstring_style_convention.combobox, 1, 1)
        ruff_layout.addWidget(self.ruff_exclude.label, 2, 0)
        ruff_layout.addWidget(self.ruff_exclude.textbox, 2, 1)
        ruff_layout.addWidget(ruff_select.label, 3, 0)
        ruff_layout.addWidget(ruff_select.textbox, 3, 1)
        ruff_layout.addWidget(ruff_ignore.label, 4, 0)
        ruff_layout.addWidget(ruff_ignore.textbox, 4, 1)

        ruff_grid_widget = QWidget()
        ruff_grid_widget.setLayout(ruff_layout)

        # Flake8 options
        self.flake8_filenames_match = self.create_lineedit(
            _("Only check these filenames:"),
            'flake8/filename',
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Check test files: test_.*\\.py"),
        )

        self.flake8_exclude = self.create_lineedit(
            _("Exclude these files or directories:"),
            'flake8/exclude',
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Exclude test files: (?!test_).*\\.py"),
        )

        flake8_select = self.create_lineedit(
            _("Show these errors or warnings:"),
            'flake8/extendSelect',
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Example codes: E113, W391"),
        )

        flake8_ignore = self.create_lineedit(
            _("Ignore these errors or warnings:"),
            'flake8/extendIgnore',
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Default is: E,W,C90"),
        )

        flake8_layout = QGridLayout()
        flake8_layout.addWidget(self.flake8_filenames_match.label, 1, 0)
        flake8_layout.addWidget(self.flake8_filenames_match.textbox, 1, 1)
        flake8_layout.addWidget(self.flake8_exclude.label, 2, 0)
        flake8_layout.addWidget(self.flake8_exclude.textbox, 2, 1)
        flake8_layout.addWidget(flake8_select.label, 3, 0)
        flake8_layout.addWidget(flake8_select.textbox, 3, 1)
        flake8_layout.addWidget(flake8_ignore.label, 4, 0)
        flake8_layout.addWidget(flake8_ignore.textbox, 4, 1)
        flake8_grid_widget = QWidget()
        flake8_grid_widget.setLayout(flake8_layout)

        # pyflakes options
        pyflakes_conf_options = QLabel(
            _("There are no configuration options for Pyflakes")
        )

        # Disabled linting options
        not_select_conf_options = QLabel(_("Linting is disabled"))

        configuration_options_layout.addWidget(ruff_grid_widget)
        configuration_options_layout.addWidget(flake8_grid_widget)
        configuration_options_layout.addWidget(pyflakes_conf_options)
        configuration_options_layout.addWidget(not_select_conf_options)

        ruff_linting_radio.radiobutton.toggled.connect(
            lambda checked: (
                ruff_grid_widget.setVisible(checked),
                flake8_grid_widget.setVisible(False),
                pyflakes_conf_options.setVisible(False),
                not_select_conf_options.setVisible(False)
            ) if checked else None
        )

        flake_linting_radio.radiobutton.toggled.connect(
            lambda checked: (
                ruff_grid_widget.setVisible(False),
                flake8_grid_widget.setVisible(checked),
                pyflakes_conf_options.setVisible(False),
                not_select_conf_options.setVisible(False)
            ) if checked else None
        )

        basic_linting_radio.radiobutton.toggled.connect(
            lambda checked: (
                ruff_grid_widget.setVisible(False),
                flake8_grid_widget.setVisible(False),
                pyflakes_conf_options.setVisible(checked),
                not_select_conf_options.setVisible(False)
            ) if checked else None
        )

        disable_linting_radio.radiobutton.toggled.connect(
            lambda checked: (
                ruff_grid_widget.setVisible(False),
                flake8_grid_widget.setVisible(False),
                pyflakes_conf_options.setVisible(False),
                not_select_conf_options.setVisible(checked)
            ) if checked else None
        )

        configuration_options_group.setLayout(configuration_options_layout)

        # Linting layout
        linting_layout = QVBoxLayout()
        linting_layout.addWidget(linting_label)
        linting_layout.addWidget(linting_select_group)
        linting_layout.addWidget(configuration_options_group)
        linting_layout.addWidget(additional_options_group)
        self.setLayout(linting_layout)

    def report_invalid_regex(self, files=True):
        """
        Report that excluded files/directories should be valid regular
        expressions.
        """
        msg = _(
            "Directory patterns listed for exclusion should be valid regular "
            "expressions"
        )
        if files:
            msg = _(
                "File patterns listed for inclusion should be valid regular "
                "expressions"
            )

        QMessageBox.critical(self, _("Error"), msg)

    def is_valid(self):
        # Check regexs
        try:
            flake8_filenames_matches = (
                self.flake8_filenames_match.textbox.text().split(",")
            )
            for match in flake8_filenames_matches:
                re.compile(match.strip())
        except re.error:
            self.report_invalid_regex()
            return False

        try:
            # flake8 check
            flake8_excludes = self.flake8_exclude.textbox.text().split(",")
            for match in flake8_excludes:
                re.compile(match.strip())

            # ruff check
            ruff_excludes = self.ruff_exclude.textbox.text().split(",")
            for match in ruff_excludes:
                re.compile(match.strip())

        except re.error:
            self.report_invalid_regex(files=False)
            return False

        return True

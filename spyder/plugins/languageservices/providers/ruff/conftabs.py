# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Preference tab of the ruff provider."""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGridLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.api.translations import _


class LintingConfigTab(SpyderPreferencesTab):
    """Linting options."""

    TITLE = _("Linting")

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        linting_label = QLabel(
            _(
                "Spyder highlights syntax errors and possible problems with "
                "your code in the editor with "
                "<a href='https://docs.astral.sh/ruff/'>Ruff</a>."
            )
        )
        linting_label.setOpenExternalLinks(True)
        linting_label.setWordWrap(True)

        lint_box = newcb(_("Enable linting"), "lint")
        underline_errors_box = newcb(
            _("Underline errors and warnings"), "underline_errors", section="editor"
        )

        # The attribute name is relied upon by the main window tests.
        self.docstring_style_check = newcb(
            _("Enable docstring style linting"), "pydocstyle"
        )
        docstring_style_convention = self.create_combobox(
            _("Convention used to lint docstrings: "),
            (("Numpy", "numpy"), ("PEP 257", "pep257"), ("Google", "google")),
            "pydocstyle/convention",
        )
        for widget in (
            docstring_style_convention.label,
            docstring_style_convention.combobox,
        ):
            widget.setEnabled(self.get_option("pydocstyle"))
            self.docstring_style_check.checkbox.toggled.connect(widget.setEnabled)

        select = self.create_lineedit(
            _("Show these errors or warnings:"),
            "extend_select",
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Example codes: E501, W291"),
        )
        ignore = self.create_lineedit(
            _("Ignore these errors or warnings:"),
            "ignore",
            alignment=Qt.Horizontal,
            word_wrap=False,
            placeholder=_("Example codes: E402, F401"),
        )

        options_layout = QGridLayout()
        options_layout.addWidget(self.docstring_style_check, 0, 0, 1, 2)
        options_layout.addWidget(docstring_style_convention.label, 1, 0)
        options_layout.addWidget(docstring_style_convention.combobox, 1, 1)
        options_layout.addWidget(select.label, 2, 0)
        options_layout.addWidget(select.textbox, 2, 1)
        options_layout.addWidget(ignore.label, 3, 0)
        options_layout.addWidget(ignore.textbox, 3, 1)
        options_widget = QWidget()
        options_widget.setLayout(options_layout)
        options_widget.setEnabled(self.get_option("lint"))
        lint_box.checkbox.toggled.connect(options_widget.setEnabled)

        linting_group = QGroupBox(_("Linting"))
        linting_layout = QVBoxLayout()
        linting_layout.addWidget(linting_label)
        linting_layout.addWidget(lint_box)
        linting_layout.addWidget(options_widget)
        linting_group.setLayout(linting_layout)

        additional_group = QGroupBox(_("Additional options"))
        additional_layout = QVBoxLayout()
        additional_layout.addWidget(underline_errors_box)
        additional_group.setLayout(additional_layout)

        layout = QVBoxLayout()
        layout.addWidget(linting_group)
        layout.addWidget(additional_group)
        layout.addStretch(1)
        self.setLayout(layout)

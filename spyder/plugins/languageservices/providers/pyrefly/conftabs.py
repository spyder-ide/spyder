# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Preference tab of the pyrefly provider."""

# Third party imports
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.api.translations import _


class IntrospectionConfigTab(SpyderPreferencesTab):
    """Type checking and hover options."""

    TITLE = _("Introspection")

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        label = QLabel(
            _(
                "Spyder uses <a href='https://pyrefly.org'>Pyrefly</a> to "
                "provide code completion, hover hints, go to definition and "
                "type checking for Python files."
            )
        )
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        type_checking_mode = self.create_combobox(
            _("Type checking mode: "),
            (
                (_("Automatic (full checks only inside projects)"), "auto"),
                (_("Off"), "off"),
                (_("Basic"), "basic"),
                (_("Default"), "default"),
                (_("Strict"), "strict"),
            ),
            "type_checking_mode",
            tip=_(
                "Which type errors Pyrefly reports for files without a "
                "Pyrefly configuration of their own."
            ),
        )
        hover_hints_box = newcb(
            _("Enable hover hints"),
            "enable_hover_hints",
            section="editor",
            tip=_(
                "If enabled, hovering the mouse pointer over an object name "
                "will display that object's signature and/or docstring (if "
                "present)."
            ),
        )

        group = QGroupBox(_("Basic features"))
        group_layout = QVBoxLayout()
        group_layout.addWidget(label)
        group_layout.addWidget(type_checking_mode)
        group_layout.addWidget(hover_hints_box)
        group.setLayout(group_layout)

        layout = QVBoxLayout()
        layout.addWidget(group)
        layout.addStretch(1)
        self.setLayout(layout)

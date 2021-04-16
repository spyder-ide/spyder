# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Language Server Protocol introspection configuration tab.
"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtWidgets import QGroupBox, QVBoxLayout

# Local imports
from spyder.api.preferences import SpyderPreferencesTab
from spyder.config.base import _
from spyder.utils.palette import QStylePalette


class IntrospectionConfigTab(SpyderPreferencesTab):
    """Introspection settings tab."""

    TITLE = _('Introspection')
    CTRL = "Cmd" if sys.platform == 'darwin' else "Ctrl"

    def __init__(self, parent):
        super().__init__(parent)
        newcb = self.create_checkbox

        introspection_group = QGroupBox(_("Basic features"))
        goto_definition_box = newcb(
            _("Enable Go to definition"),
            'jedi_definition',
            tip=_("If enabled, left-clicking on an object name while \n"
                  "pressing the {} key will go to that object's definition\n"
                  "(if resolved).").format(self.CTRL))
        follow_imports_box = newcb(_("Follow imports when going to a "
                                     "definition"),
                                   'jedi_definition/follow_imports')
        show_signature_box = newcb(_("Show calltips"), 'jedi_signature_help')
        enable_hover_hints_box = newcb(
            _("Enable hover hints"),
            'enable_hover_hints',
            tip=_("If enabled, hovering the mouse pointer over an object\n"
                  "name will display that object's signature and/or\n"
                  "docstring (if present)."))
        introspection_layout = QVBoxLayout()
        introspection_layout.addWidget(goto_definition_box)
        introspection_layout.addWidget(follow_imports_box)
        introspection_layout.addWidget(show_signature_box)
        introspection_layout.addWidget(enable_hover_hints_box)
        introspection_group.setLayout(introspection_layout)

        goto_definition_box.toggled.connect(follow_imports_box.setEnabled)

        # Advanced group
        advanced_group = QGroupBox(_("Advanced"))
        modules_textedit = self.create_textedit(
            _("Preload the following modules to make completion faster "
              "and more accurate:"),
            'preload_modules'
        )
        modules_textedit.textbox.setStyleSheet(
            f"border: 1px solid {QStylePalette.COLOR_BACKGROUND_2};"
        )

        advanced_layout = QVBoxLayout()
        advanced_layout.addWidget(modules_textedit)
        advanced_group.setLayout(advanced_layout)

        layout = QVBoxLayout()
        layout.addWidget(introspection_group)
        layout.addWidget(advanced_group)
        layout.addStretch(1)
        self.setLayout(layout)

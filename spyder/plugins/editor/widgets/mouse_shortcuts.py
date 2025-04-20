# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Mouse shortcut editor dialog"""

# Standard library imports
from itertools import combinations
import sys

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.widgets.helperwidgets import TipWidget


class MouseShortcutEditor(QDialog, SpyderConfigurationAccessor):
    """A dialog to edit the modifier keys for CodeEditor mouse interactions."""

    CONF_SECTION = "editor"

    def __init__(self, parent):
        super().__init__(parent)
        mouse_shortcuts = self.get_conf('mouse_shortcuts')
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout()

        description = QLabel(
            "Here you can configure shortcuts that are triggered by one or "
            "more key modifiers and a left mouse click"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.scrollflag_shortcut = ShortcutSelector(
            self,
            _("Jump within the document in the scroll flags area"),
            mouse_shortcuts['jump_to_position']
        )
        self.scrollflag_shortcut.sig_changed.connect(self.validate)
        layout.addWidget(self.scrollflag_shortcut)

        self.goto_def_shortcut = ShortcutSelector(
            self,
            _("Go to a code definition"),
            mouse_shortcuts['goto_definition']
        )
        self.goto_def_shortcut.sig_changed.connect(self.validate)
        layout.addWidget(self.goto_def_shortcut)

        self.add_cursor_shortcut = ShortcutSelector(
            self,
            _("Add/remove an additional cursor"),
            mouse_shortcuts['add_remove_cursor']
        )
        self.add_cursor_shortcut.sig_changed.connect(self.validate)
        layout.addWidget(self.add_cursor_shortcut)

        self.column_cursor_shortcut = ShortcutSelector(
            self,
            _("Add a column of cursors"),
            mouse_shortcuts['column_cursor']
        )
        self.column_cursor_shortcut.sig_changed.connect(self.validate)
        layout.addWidget(self.column_cursor_shortcut)
        
        buttons = (
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box = SpyderDialogButtonBox(buttons, parent=self)
        apply_b = button_box.button(QDialogButtonBox.StandardButton.Apply)
        apply_b.clicked.connect(self.apply_mouse_shortcuts)
        apply_b.setEnabled(False)
        self.apply_button = apply_b

        ok_b = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_b.clicked.connect(self.accept)
        self.ok_button = ok_b

        cancel_b = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_b.clicked.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

    def apply_mouse_shortcuts(self):
        """Set new config to CONF"""
        self.set_conf('mouse_shortcuts', self.mouse_shortcuts)
        self.scrollflag_shortcut.apply_modifiers()
        self.goto_def_shortcut.apply_modifiers()
        self.add_cursor_shortcut.apply_modifiers()
        self.column_cursor_shortcut.apply_modifiers()
        self.apply_button.setEnabled(False)

    def accept(self):
        """Apply new settings and close dialog."""
        self.apply_mouse_shortcuts()
        super().accept()

    def validate(self):
        """
        Detect conflicts between shortcuts, and detect if current selection is
        different from current config. Set Ok and Apply buttons enabled or
        disabled accordingly, as well as set visibility of the warning for
        shortcut conflict.
        """
        shortcut_selectors = (
            self.scrollflag_shortcut,
            self.goto_def_shortcut,
            self.add_cursor_shortcut,
            self.column_cursor_shortcut
        )

        for selector in shortcut_selectors:
            selector.warning.setVisible(False)

        conflict = False
        for a, b in combinations(shortcut_selectors, 2):
            if a.modifiers() and a.modifiers() == b.modifiers():
                conflict = True
                a.warning.setVisible(True)
                b.warning.setVisible(True)

        self.ok_button.setEnabled(not conflict)

        self.apply_button.setEnabled(
            not conflict and (
                self.scrollflag_shortcut.is_changed() or
                self.goto_def_shortcut.is_changed() or
                self.add_cursor_shortcut.is_changed() or
                self.column_cursor_shortcut.is_changed()
            )
        )

    @property
    def mouse_shortcuts(self):
        """Format shortcuts dict for CONF."""
        return {
            'jump_to_position': self.scrollflag_shortcut.modifiers(),
            'goto_definition': self.goto_def_shortcut.modifiers(),
            'add_remove_cursor': self.add_cursor_shortcut.modifiers(),
            'column_cursor': self.column_cursor_shortcut.modifiers()
        }


class ShortcutSelector(QWidget):
    """Line representing an editor for a single mouse shortcut."""

    sig_changed = Signal()

    def __init__(self, parent, label, modifiers):
        super().__init__(parent)

        layout = QHBoxLayout()

        label = QLabel(label)
        layout.addWidget(label)

        spacer = QWidget(self)
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(spacer)

        self.ctrl_check = QCheckBox(
            "Cmd" if sys.platform == "darwin" else "Ctrl"
        )
        self.ctrl_check.setChecked("ctrl" in modifiers.lower())
        self.ctrl_check.toggled.connect(self.validate)
        layout.addWidget(self.ctrl_check)

        self.alt_check = QCheckBox("Alt")
        self.alt_check.setChecked("alt" in modifiers.lower())
        self.alt_check.toggled.connect(self.validate)
        layout.addWidget(self.alt_check)

        self.meta_check = QCheckBox("Meta")
        self.meta_check.setChecked("meta" in modifiers.lower())
        self.meta_check.toggled.connect(self.validate)
        layout.addWidget(self.meta_check)

        self.shift_check = QCheckBox("Shift")
        self.shift_check.setChecked("shift" in modifiers.lower())
        self.shift_check.toggled.connect(self.validate)
        layout.addWidget(self.shift_check)

        warning_icon = ima.icon("MessageBoxWarning")
        self.warning = TipWidget(
            _("Shortcut Conflicts With Another"),
            warning_icon,
            warning_icon
        )

        # Thanks to https://stackoverflow.com/a/34663079/3220135
        sp_retain = self.warning.sizePolicy()
        sp_retain.setRetainSizeWhenHidden(True)
        self.warning.setSizePolicy(sp_retain)
        self.warning.setVisible(False)
        layout.addWidget(self.warning)

        self.setLayout(layout)

        self.apply_modifiers()

    def validate(self):
        """
        Cannot have shortcut of Shift alone as that conflicts with setting the
        cursor position without moving the anchor. Enable/Disable the Shift
        checkbox accordingly. (Re)Emit a signal to MouseShortcutEditor which
        will perform other validation.
        """
        if (
            self.ctrl_check.isChecked() or
            self.alt_check.isChecked() or
            self.meta_check.isChecked()
        ):
            self.shift_check.setEnabled(True)
        else:
            self.shift_check.setEnabled(False)
            self.shift_check.setChecked(False)

        self.sig_changed.emit()

    def modifiers(self):
        """Get the current modifiers string."""
        modifiers = []
        if self.ctrl_check.isChecked():
            modifiers.append("Ctrl")
        if self.alt_check.isChecked():
            modifiers.append("Alt")
        if self.meta_check.isChecked():
            modifiers.append("Meta")
        if self.shift_check.isChecked():
            modifiers.append("Shift")
        return "+".join(modifiers)

    def is_changed(self):
        """Is the current selection different from when last applied?"""
        return self.current_modifiers != self.modifiers()

    def apply_modifiers(self):
        """Informs ShortcutSelector that settings have been applied."""
        self.current_modifiers = self.modifiers()

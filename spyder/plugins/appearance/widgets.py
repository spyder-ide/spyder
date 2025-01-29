# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Appearance entry in Preferences."""

import re

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.utils import syntaxhighlighters


class SchemeEditor(QDialog):
    """A color scheme editor dialog."""

    def __init__(self, parent=None, stack=None):
        super(SchemeEditor, self).__init__(parent)
        self.parent = parent
        self.stack = stack
        self.order = []    # Uses scheme names

        # Needed for self.get_edited_color_scheme()
        self.widgets = {}
        self.scheme_name_textbox = {}
        self.last_edited_color_scheme = None
        self.last_used_scheme = None

        # Widgets
        bbox = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        layout.addWidget(bbox)
        self.setLayout(layout)

        # Signals
        bbox.accepted.connect(self.validate_colors)
        bbox.accepted.connect(self.get_edited_color_scheme)
        bbox.rejected.connect(self.reject)

    # Helpers
    # -------------------------------------------------------------------------
    def set_scheme(self, scheme_name):
        """Set the current stack by 'scheme_name'."""
        self.stack.setCurrentIndex(self.order.index(scheme_name))
        self.last_used_scheme = scheme_name

    def get_scheme_name(self):
        """
        Returns the edited scheme name, needed to update the combobox on
        scheme creation.
        """
        return self.scheme_name_textbox[self.last_used_scheme].text()

    def validate_colors(self):
        """
        Validate the current color scheme and display a message box listing
        any invalid colors.
        """
        invalid_colors = {}
        scheme_name = self.last_used_scheme
        pattern = (
            r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3}|[A-Fa-f0-9]{8}|[A-Fa-f0-9]{4})$"
        )
        for key in self.widgets[scheme_name]:
            items = self.widgets[scheme_name][key]

            if not bool(re.match(pattern, items[0].text())):
                invalid_colors[key] = items[0].text()

        if invalid_colors:
            message = _("The following properties have invalid colors:\n\n")
            for property_name, color in invalid_colors.items():
                name = syntaxhighlighters.COLOR_SCHEME_KEYS[property_name]
                clean_name = name[:-1].replace("<br>", "")
                message += _(
                    "The property <b>{}</b> has an invalid color: {}\n"
                ).format(clean_name, color)

            msgbox = QMessageBox(
                QMessageBox.Warning,
                _('Error setting colors'),
                message,
                QMessageBox.Ok,
                self
            )
            msgbox.exec_()
        else:
            self.accept()


    def get_edited_color_scheme(self):
        """
        Get the values of the last edited color scheme to be used in an instant
        preview in the preview editor, without using `apply`.
        """
        color_scheme = {}
        scheme_name = self.last_used_scheme

        for key in self.widgets[scheme_name]:
            items = self.widgets[scheme_name][key]

            if len(items) == 1:
                # ColorLayout
                value = items[0].text()
            else:
                # ColorLayout + checkboxes
                value = (items[0].text(), items[1].isChecked(),
                         items[2].isChecked())

            color_scheme[key] = value

        return color_scheme

    # Actions
    # -------------------------------------------------------------------------
    def add_color_scheme_stack(self, scheme_name, custom=False):
        """Add a stack for a given scheme and connects the CONF values."""
        color_scheme_groups = [
            (_('Text'), ["normal", "comment", "string", "number", "keyword",
                         "builtin", "definition", "instance", ]),
            (_('Highlight'), ["currentcell", "currentline", "occurrence",
                              "matched_p", "unmatched_p", "ctrlclick"]),
            (_('Background'), ["background", "sideareas"])
            ]

        parent = self.parent
        line_edit = parent.create_lineedit(_("Scheme name:"),
                                           '{0}/name'.format(scheme_name))

        self.widgets[scheme_name] = {}

        # Widget setup
        line_edit.label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setWindowTitle(_('Color scheme editor'))

        # Layout
        name_layout = QHBoxLayout()
        name_layout.addWidget(line_edit.label)
        name_layout.addWidget(line_edit.textbox)
        self.scheme_name_textbox[scheme_name] = line_edit.textbox

        if not custom:
            line_edit.textbox.setDisabled(True)
        if not self.isVisible():
            line_edit.setVisible(False)

        cs_layout = QVBoxLayout()
        cs_layout.addLayout(name_layout)

        h_layout = QHBoxLayout()
        v_layout = QVBoxLayout()

        for index, item in enumerate(color_scheme_groups):
            group_name, keys = item
            group_layout = QGridLayout()

            for row, key in enumerate(keys):
                option = "{0}/{1}".format(scheme_name, key)
                value = self.parent.get_option(option)
                name = syntaxhighlighters.COLOR_SCHEME_KEYS[key]

                if isinstance(value, str):
                    label, clayout = parent.create_coloredit(
                        name,
                        option,
                        without_layout=True,
                        )
                    label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    group_layout.addWidget(label, row+1, 0)
                    group_layout.addLayout(clayout, row+1, 1)

                    # Needed to update temp scheme to obtain instant preview
                    self.widgets[scheme_name][key] = [clayout]
                else:
                    label, clayout, cb_bold, cb_italic = parent.create_scedit(
                        name,
                        option,
                        without_layout=True,
                        )
                    label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    group_layout.addWidget(label, row+1, 0)
                    group_layout.addLayout(clayout, row+1, 1)
                    group_layout.addWidget(cb_bold, row+1, 2)
                    group_layout.addWidget(cb_italic, row+1, 3)

                    # Needed to update temp scheme to obtain instant preview
                    self.widgets[scheme_name][key] = [clayout, cb_bold,
                                                      cb_italic]

            group_box = QGroupBox(group_name)
            group_box.setLayout(group_layout)

            if index == 0:
                h_layout.addWidget(group_box)
            else:
                v_layout.addWidget(group_box)

        h_layout.addLayout(v_layout)
        cs_layout.addLayout(h_layout)

        stackitem = QWidget()
        stackitem.setLayout(cs_layout)
        self.stack.addWidget(stackitem)
        self.order.append(scheme_name)

    def delete_color_scheme_stack(self, scheme_name):
        """Remove stack widget by 'scheme_name'."""
        self.set_scheme(scheme_name)
        widget = self.stack.currentWidget()
        self.stack.removeWidget(widget)
        index = self.order.index(scheme_name)
        self.order.pop(index)

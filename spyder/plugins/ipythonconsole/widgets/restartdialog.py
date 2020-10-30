# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console restart dialog for preferences.
"""

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QLabel,
                            QPushButton, QVBoxLayout)

# Local imports
from spyder.config.base import _


class ConsoleRestartDialog(QDialog):
    """
    Dialog to apply preferences that need a restart of the console kernel.
    """

    # Constants for actions when Preferences require a kernel restart
    NO_RESTART = 1
    RESTART_CURRENT = 2
    RESTART_ALL = 3

    def __init__(self, parent):
        super(ConsoleRestartDialog, self).__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self._parent = parent
        self._action = self.NO_RESTART
        self._action_string = {
            self.NO_RESTART: _("Keep Existing Kernels"),
            self.RESTART_CURRENT: _("Restart Current Kernel"),
            self.RESTART_ALL: _("Restart All Kernels")
            }
        # Dialog widgets
        # Text
        self._text_label = QLabel(
            _("By default, some IPython console preferences will be "
              "applied to new consoles only. To apply preferences to "
              "existing consoles, select from the options below.<br><br>"
              "Please note: applying changes to running consoles will force"
              " a kernel restart and all current work will be lost."),
            self)
        self._text_label.setWordWrap(True)
        self._text_label.setFixedWidth(450)

        # Checkboxes
        self._restart_current = QCheckBox(
            _("Apply to current console and restart kernel"), self)
        self._restart_all = QCheckBox(
            _("Apply to all existing consoles and restart all kernels"), self)
        self._checkbox_group = QButtonGroup(self)
        self._checkbox_group.setExclusive(False)
        self._checkbox_group.addButton(
            self._restart_current, id=self.RESTART_CURRENT)
        self._checkbox_group.addButton(
            self._restart_all, id=self.RESTART_ALL)

        self._action_button = QPushButton(
            self._action_string[self.NO_RESTART], parent=self)

        # Dialog Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self._text_label)
        layout.addSpacing(5)
        layout.addWidget(self._restart_current)
        layout.addWidget(self._restart_all)
        layout.addSpacing(10)
        layout.addWidget(self._action_button, 0, Qt.AlignRight)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Signals
        self._checkbox_group.buttonToggled.connect(
            self.update_action_button_text)
        self._action_button.clicked.connect(self.accept)

    def update_action_button_text(self, checkbox, is_checked):
        """
        Update action button text.

        Takes into account the given checkbox to update the text.
        """
        checkbox_id = self._checkbox_group.id(checkbox)
        if is_checked:
            text = self._action_string[checkbox_id]
            self._checkbox_group.buttonToggled.disconnect(
                self.update_action_button_text)
            self._restart_current.setChecked(False)
            self._restart_all.setChecked(False)
            checkbox.setChecked(True)
            self._checkbox_group.buttonToggled.connect(
                self.update_action_button_text)
        else:
            text = self._action_string[self.NO_RESTART]
        self._action_button.setText(text)

    def get_action_value(self):
        """
        Return tuple indicating True or False for the available actions.
        """
        restart_current = self._restart_current.isChecked()
        restart_all = self._restart_all.isChecked()
        no_restart = not any([restart_all, restart_current])
        return restart_all, restart_current, no_restart

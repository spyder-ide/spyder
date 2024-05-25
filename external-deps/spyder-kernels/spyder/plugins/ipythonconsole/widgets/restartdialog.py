# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console restart dialog for preferences.
"""

# Third party imports
import qstylizer.style
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QButtonGroup,
    QDialog,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

# Local imports
from spyder.config.base import _
from spyder.utils.stylesheet import AppStyle, MAC


class ConsoleRestartDialog(QDialog):
    """
    Dialog to apply preferences that need a restart of the console kernel.
    """

    # Constants for actions when Preferences require a kernel restart
    NO_RESTART = 1
    RESTART_CURRENT = 2
    RESTART_ALL = 3

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self._parent = parent
        self.setWindowTitle(_("Restart kernels"))

        self._action = self.NO_RESTART
        self._action_string = {
            self.NO_RESTART: _("Keep existing kernels"),
            self.RESTART_CURRENT: _("Restart current kernel"),
            self.RESTART_ALL: _("Restart all kernels")
        }

        # Initial option values
        self.restart_all = False
        self.restart_current = False
        self.no_restart = True

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

        # Radio buttons
        self._no_restart_btn = QRadioButton(
            _("Don't apply changes to existing consoles"), self
        )
        self._restart_current_btn = QRadioButton(
            _("Apply to current console and restart kernel"), self
        )
        self._restart_all_btn = QRadioButton(
            _("Apply to all existing consoles and restart all kernels"), self
        )

        self._radio_group = QButtonGroup(self)
        self._radio_group.setExclusive(True)
        self._radio_group.addButton(
            self._no_restart_btn, id=self.NO_RESTART
        )
        self._radio_group.addButton(
            self._restart_current_btn, id=self.RESTART_CURRENT
        )
        self._radio_group.addButton(
            self._restart_all_btn, id=self.RESTART_ALL
        )

        self._action_button = QPushButton(
            self._action_string[self.NO_RESTART], parent=self
        )

        # Dialog Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self._text_label)
        layout.addSpacing(2 * AppStyle.MarginSize)
        layout.addWidget(self._no_restart_btn)
        layout.addWidget(self._restart_current_btn)
        layout.addWidget(self._restart_all_btn)
        layout.addSpacing(
            2 * AppStyle.MarginSize if MAC else 3 * AppStyle.MarginSize
        )
        layout.addWidget(self._action_button, 0, Qt.AlignRight)
        layout.setContentsMargins(*((7 * AppStyle.MarginSize,) * 4))
        self.setLayout(layout)

        # Signals
        self._no_restart_btn.setChecked(True)
        self._radio_group.buttonToggled.connect(
            self.update_action_button_text)
        self._action_button.clicked.connect(self.accept)

        # Stylesheet
        self._set_stylesheet()

    def update_action_button_text(self, radiobutton, is_checked):
        """
        Update action button text.

        Takes into account the given radio button to update the text.
        """
        radiobutton_id = self._radio_group.id(radiobutton)
        if is_checked:
            text = self._action_string[radiobutton_id]
            self._radio_group.buttonToggled.disconnect(
                self.update_action_button_text)

            self._no_restart_btn.setChecked(False)
            self._restart_current_btn.setChecked(False)
            self._restart_all_btn.setChecked(False)
            radiobutton.setChecked(True)

            self._radio_group.buttonToggled.connect(
                self.update_action_button_text)
        else:
            text = self._action_string[self.NO_RESTART]
        self._action_button.setText(text)

    def get_action_value(self):
        """
        Return tuple indicating True or False for the available actions.
        """
        self.restart_current = self._restart_current_btn.isChecked()
        self.restart_all = self._restart_all_btn.isChecked()
        self.no_restart = not any([self.restart_all, self.restart_current])
        return self.restart_all, self.restart_current, self.no_restart

    def _set_stylesheet(self):
        radiobuttons_css = qstylizer.style.StyleSheet()
        radiobuttons_css.setValues(
            marginLeft=f"{5 * AppStyle.MarginSize}px"
        )
        for label in [
            self._no_restart_btn,
            self._restart_current_btn,
            self._restart_all_btn,
        ]:
            label.setStyleSheet(radiobuttons_css.toString())

    def exec_(self):
        # Give focus to the last selected button
        if self.restart_all:
            self._restart_all_btn.setFocus()
        elif self.restart_current:
            self._restart_current_btn.setFocus()
        else:
            self._no_restart_btn.setFocus()

        super().exec_()

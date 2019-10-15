# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QLabel, QVBoxLayout, QFrame,
                            QHBoxLayout, QPushButton)

from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.plugins.completion.kite.bloomfilter import KiteBloomFilter
from spyder.plugins.completion.kite.parsing import find_returning_function_path
from spyder.plugins.completion.kite.utils.status import check_if_kite_installed
from spyder.plugins.completion.fallback.actor import FALLBACK_COMPLETION
from spyder.utils.icon_manager import is_dark_interface

COVERAGE_MESSAGE = (
    _("No completions found."
      " Get completions for this case and more by installing Kite.")
)


class KiteCallToAction(QFrame):
    def __init__(self, textedit, ancestor):
        super(KiteCallToAction, self).__init__(ancestor)
        self.textedit = textedit

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setAutoFillBackground(True)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.NoFocus)
        if is_dark_interface():
            self.setObjectName("kite-call-to-action")
            self.setStyleSheet(self.styleSheet() +
                               ("#kite-call-to-action "
                                "{ border: 1px solid; "
                                "  border-color: #32414B; "
                                "  border-radius: 4px;} "
                                "#kite-call-to-action:hover "
                                "{ border:1px solid #148CD2; }"))

        # sub-layout: horizontally aligned links
        actions = QFrame(self)
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(5, 5, 5, 5)
        actions_layout.setSpacing(10)
        actions_layout.addStretch()
        actions.setLayout(actions_layout)

        self._install_button = QPushButton(_("Install Kite"))
        self._learn_button = QPushButton(_("Learn More"))
        self._dismiss_button = QPushButton(_("Dismiss Forever"))
        self._install_button.clicked.connect(self._install_kite)
        self._learn_button.clicked.connect(self._learn_more)
        self._dismiss_button.clicked.connect(self._dismiss_forever)
        actions_layout.addWidget(self._install_button)
        actions_layout.addWidget(self._learn_button)
        actions_layout.addWidget(self._dismiss_button)

        # main layout: message + horizontally aligned links
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(main_layout)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        main_layout.addWidget(self.label)
        main_layout.addWidget(actions)
        main_layout.addStretch()

        self._enabled = CONF.get('kite', 'call_to_action')
        self._escaped = False
        self.hide()

        is_kite_installed, __ = check_if_kite_installed()
        if is_kite_installed:
            self._dismiss_forever()

    def handle_key_press(self, event):
        key = event.key()
        if not self._is_valid_ident_key(key):
            self.hide()
        self._escaped = key == Qt.Key_Escape

    def handle_mouse_press(self, event):
        self.hide()

    def handle_processed_completions(self, completions):
        if not self._enabled:
            return
        if self._escaped:
            return
        if not self.textedit.completion_widget.isHidden():
            return
        if any(c['provider'] != FALLBACK_COMPLETION for c in completions):
            return

        # check if we should show the CTA, based on Kite support
        text = self.textedit.get_text('sof', 'eof')
        offset = self.textedit.get_position('cursor')

        fn_path = find_returning_function_path(text, offset, u'\u2029')
        if fn_path is None:
            return
        if not KiteBloomFilter.is_valid_path(fn_path):
            return

        self.label.setText(COVERAGE_MESSAGE)
        self.resize(self.sizeHint())
        self.show()
        self.textedit.position_widget_at_cursor(self)
        self.raise_()

    def _is_valid_ident_key(self, key):
        is_upper = ord('A') <= key <= ord('Z')
        is_lower = ord('a') <= key <= ord('z')
        is_digit = ord('0') <= key <= ord('9')
        is_under = key == ord('_')
        is_dot = key == ord('.')
        return is_upper or is_lower or is_digit or is_under

    def _dismiss_forever(self):
        self.hide()
        self._enabled = False
        CONF.set('kite', 'call_to_action', False)

    def _learn_more(self):
        self.hide()
        self._enabled = False
        kite = self.parent().completions.get_client('kite')
        kite.installer.welcome()
        kite.installer.show()

    def _install_kite(self):
        self.hide()
        self._enabled = False
        kite = self.parent().completions.get_client('kite')
        kite.installer.install()
        kite.installer.show()

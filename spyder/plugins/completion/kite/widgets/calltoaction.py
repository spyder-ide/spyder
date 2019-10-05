# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from qtpy.QtCore import Qt, QTimer, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QLabel, QApplication,
                            QVBoxLayout, QFrame, QHBoxLayout,
                            QPushButton)
from spyder.utils.syntaxhighlighters import get_color_scheme

from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.config.manager import CONF
from spyder.plugins.completion.kite.bloomfilter import KiteBloomFilter
from spyder.plugins.completion.kite.parsing import find_returning_function_path
from spyder.plugins.completion.kite.utils.status import check_if_kite_installed
from spyder.plugins.completion.fallback.actor import FALLBACK_COMPLETION

COVERAGE_MESSAGE = (
    _("No completions found."
      " Get completions for this case and more by installing Kite.")
)


class KiteCallToAction(QFrame):
    def __init__(self, textedit, ancestor):
        super(KiteCallToAction, self).__init__(ancestor)
        self.textedit = textedit

        self.setObjectName("kite-call-to-action")
        self.set_color_scheme(CONF.get('appearance', 'selected'))
        # Reuse completion window size
        # self.setFont(get_font())
        self.setFocusPolicy(Qt.NoFocus)

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

    def set_color_scheme(self, color_scheme):
        if not isinstance(color_scheme, dict):
            color_scheme = get_color_scheme(color_scheme)
        bg_color = color_scheme['background']
        border_color = color_scheme['sideareas']
        text_color, __, __ = color_scheme['normal']
        button_color = color_scheme['currentline']
        hover_color = color_scheme['currentcell']
        self.setStyleSheet("""
* {{ background-color: {background}; color: {color}; border: 0; }}
#kite-call-to-action {{ border: 2px solid {border}; }}
QPushButton {{ background-color: {button}; border: 1px solid {border}; }}
QPushButton:hover {{ background-color: {hover}; }}
""".format(background=bg_color, border=border_color, color=text_color,
           button=button_color, hover=hover_color))

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
        kite.kite_installer.welcome()
        kite.kite_installer.show()

    def _install_kite(self):
        self.hide()
        self._enabled = False
        kite = self.parent().completions.get_client('kite')
        kite.kite_installer.install()
        kite.kite_installer.show()

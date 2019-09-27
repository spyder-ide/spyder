# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from qtpy.QtCore import Qt, QTimer, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QLabel, QApplication,
                            QVBoxLayout, QFrame, QHBoxLayout)

from spyder.config.base import get_translation
from spyder.config.gui import get_font
from spyder.config.manager import CONF
from spyder.plugins.completion.kite.bloomfilter import KiteBloomFilter
from spyder.plugins.completion.kite.parsing import find_returning_function_path
from spyder.plugins.completion.fallback.actor import FALLBACK_COMPLETION

# Translation callback
_ = get_translation("spyder")

COVERAGE_MESSAGE = (
    _("No completions found."
      " Get completions for this case and more by installing Kite.")
)


class KiteCTA(QFrame):
    def __init__(self, textedit, ancestor):
        super().__init__(ancestor)
        self.textedit = textedit
        self.setObjectName("kite_cta")
        # fixme retrieve color from theme
        self.setStyleSheet('#kite_cta:active {  border: 1px solid #6a6ea9; }')

        # Reuse completion window size
        self.setFont(get_font())
        self.setFocusPolicy(Qt.NoFocus)

        # sub-layout: horizontally aligned links
        labels = QFrame(self)
        labels_layout = QHBoxLayout()
        labels_layout.setContentsMargins(5, 5, 5, 5)
        labels_layout.setSpacing(15)
        labels_layout.addStretch()
        labels.setLayout(labels_layout)
        labels_layout.addWidget(self._create_link_label(
            _("Install Kite"), "https://kite.com/download/"))
        labels_layout.addWidget(self._create_link_label(
            _("Learn more"), "https://kite.com"))
        dismissal_link = self._create_link_label(_("Dismiss forever"), "#")
        dismissal_link.linkActivated.connect(self._dismiss)
        labels_layout.addWidget(dismissal_link)

        # main layout: message + horizontally aligned links
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        labels_layout.setSpacing(10)
        self.setLayout(main_layout)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        main_layout.addWidget(self.label)
        main_layout.addWidget(labels)
        main_layout.addStretch()

        self._enabled = CONF.get('main', 'show_kite_cta')
        self._escaped = False
        self.hide()

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
        self._position()
        self.raise_()

    def _is_valid_ident_key(self, key):
        is_upper = ord('A') <= key <= ord('Z')
        is_lower = ord('a') <= key <= ord('z')
        is_digit = ord('0') <= key <= ord('9')
        is_under = key == ord('_')
        is_dot = key == ord('.')
        return is_upper or is_lower or is_digit or is_under

    def _dismiss(self):
        self._enabled = False
        CONF.set('main', 'show_kite_cta', False)

    def _create_link_label(self, text, link):
        text = '<p><a href="{link}">{text}</a></p>'.format(
            text=text, link=link)
        label = QLabel(text, self)
        label.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        label.linkActivated.connect(self.hide)
        if link.startswith("http"):
            url = QUrl(link)
            label.linkActivated.connect(lambda: QDesktopServices.openUrl(url))
        return label

    # Taken from spyder/plugins/editor/widgets/base.py
    # Places CTA next to cursor
    def _position(self):
        # Retrieve current screen height
        desktop = QApplication.desktop()
        srect = desktop.availableGeometry(desktop.screenNumber(self))
        screen_right = srect.right()
        screen_bottom = srect.bottom()

        point = self.textedit.cursorRect().bottomRight()
        point = self.textedit.calculate_real_position(point)
        point = self.textedit.mapToGlobal(point)

        # Computing completion widget and its parent right positions
        comp_right = point.x() + self.width()
        ancestor = self.parent()
        if ancestor is None:
            anc_right = screen_right
        else:
            anc_right = min([ancestor.x() + ancestor.width(), screen_right])

        # Moving completion widget to the left
        # if there is not enough space to the right
        if comp_right > anc_right:
            point.setX(point.x() - self.width())

        # Computing completion widget and its parent bottom positions
        comp_bottom = point.y() + self.height()
        ancestor = self.parent()
        if ancestor is None:
            anc_bottom = screen_bottom
        else:
            anc_bottom = min([ancestor.y() + ancestor.height(), screen_bottom])

        # Moving completion widget above if there is not enough space below
        x_position = point.x()
        if comp_bottom > anc_bottom:
            point = self.textedit.cursorRect().topRight()
            point = self.textedit.mapToGlobal(point)
            point.setX(x_position)
            point.setY(point.y() - self.height())

        if ancestor is not None:
            # Useful only if we set parent to 'ancestor' in __init__
            point = ancestor.mapFromGlobal(point)
        self.move(point)

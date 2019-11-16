# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Shortcut Summary dialog"""


# Standard library imports
from operator import itemgetter
from itertools import groupby

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QKeySequence
from qtpy.QtWidgets import (QDialog, QLabel, QGridLayout, QGroupBox,
                            QVBoxLayout, QHBoxLayout, QDesktopWidget,
                            QScrollArea, QWidget)

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF

# Constants
MAX_FONT_SIZE = 16
MIN_FONT_SIZE = 8

class ShortcutsSummaryDialog(QDialog):
    """
    Dialog window listing the spyder and plugins shortcuts.

    It contains all the shortcuts avalaible through iter_shortcuts
    function

    The shortcuts are dysplayed in different columns, and grouped by
    context (global, editor, console...)
    """
    def __init__(self, parent=None):
        QDialog.__init__(self, parent=parent)

        self._shortcuts_summary_title = _("Spyder Keyboard ShortCuts")

        # Calculate font and amount of elements in each column according screen size
        width, height = self.get_screen_resolution()
        font_size = height / 80
        font_size = max(min(font_size, MAX_FONT_SIZE), MIN_FONT_SIZE)
        shortcuts_column = (height - 8 * font_size) / (font_size +16)

        # Widgets
        style = """
            QDialog {
              margin:0px;
              padding:0px;
              border-radius: 2px;
            }"""
        self.setStyleSheet(style)

        font_names = QFont()
        font_names.setPointSize(font_size)
        font_names.setBold(True)

        font_keystr = QFont()
        font_keystr.setPointSize(font_size)

        font_title = QFont()
        font_title.setPointSize(font_size+2)
        font_title.setBold(True)

        title_label = QLabel(self._shortcuts_summary_title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(font_title)

        # iter over shortcuts and create GroupBox for each context
        # with shortcuts in a grid

        columns_layout = QHBoxLayout()
        added_shortcuts = 0
        group = None
        # group shortcuts by context
        shortcuts = groupby(sorted(CONF.iter_shortcuts()), key=itemgetter(0))

        for context, group_shortcuts in shortcuts:
            for i, (context, name, keystr) in enumerate(group_shortcuts):
                # start of every column
                if added_shortcuts == 0:
                    column_layout = QVBoxLayout()

                # at start of new context add previous context group
                if i == 0 and added_shortcuts > 0:
                    column_layout.addWidget(group)

                # create group at start of column or context
                if added_shortcuts == 0 or i == 0:
                    if context == '_': context = 'Global'

                    group = QGroupBox(context.capitalize())
                    group.setFont(font_names)

                    group_layout = QGridLayout()
                    group.setLayout(group_layout)

                    # Count space for titles
                    added_shortcuts += 1

                # Widgets
                label_name = QLabel(name.capitalize().replace('_', ' '))
                label_name.setFont(font_names)

                keystr = QKeySequence(keystr).toString(QKeySequence.NativeText)
                label_keystr = QLabel(keystr)
                label_keystr.setFont(font_keystr)

                group_layout.addWidget(label_name, i, 0)
                group_layout.addWidget(label_keystr, i, 1)

                added_shortcuts += 1

                if added_shortcuts >= shortcuts_column:
                    column_layout.addWidget(group)
                    columns_layout.addLayout(column_layout)
                    added_shortcuts = 0

        column_layout.addWidget(group)
        column_layout.addStretch()  # avoid lasts sections to appear too big
        columns_layout.addLayout(column_layout)

        # Scroll widget
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(columns_layout)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_widget)

        # widget setup
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowOpacity(0.95)

        # layout
        self._layout = QVBoxLayout()
        self._layout.addWidget(title_label)

        self._layout.addWidget(self.scroll_area)
        self.setLayout(self._layout)

        self.setGeometry(0, 0, width, height)

    def get_screen_resolution(self):
        """Return the screen resolution of the primary screen."""
        widget = QDesktopWidget()
        geometry = widget.availableGeometry(widget.primaryScreen())
        return geometry.width(), geometry.height()


def test():  # pragma: no cover
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg_shortcuts = ShortcutsSummaryDialog(None)
    dlg_shortcuts.show()
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    test()

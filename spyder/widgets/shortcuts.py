# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shortcut Summary dialog"""

# TODO:
# calculate windows size from screen size

# Standard library imports
from operator import itemgetter
from itertools import groupby

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QDialog, QLabel, QGridLayout, QGroupBox,
                            QVBoxLayout, QHBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.config.gui import iter_shortcuts

# Constants
SHORTCUT_SHOURTCUTS_SUMMARY = "Ctrl+H"
MAX_SHOURCUTS_COLUMN = 28


class ShortCutsSummaryDialog(QDialog):
    def __init__(self, parent=None, offset=0, force_float=False):
        QDialog.__init__(self, parent=parent)

        self._shortcuts_summary_title = _("Spyder Keyboard ShortCuts")

        # Widgets
        style = """
            QDialog {
              margin:0px;
              padding:0px;
              border-radius: 2px;
            }"""
        self.setStyleSheet(style)

        groupbox_style = "QGroupBox { font-weight: bold;}"

        font_titles = QFont()
        font_titles.setBold(True)

        title_label = QLabel(self._shortcuts_summary_title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(font_titles)

        # iter over shortcuts and create GroupBox for each context
        # with shortcuts in a grid

        columns_layout = QHBoxLayout()
        added_shortcuts = 0
        # group shortcuts by context
        shortcuts = groupby(sorted(iter_shortcuts()), key=itemgetter(0))

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
                    group.setStyleSheet(groupbox_style)

                    group_layout = QGridLayout()
                    group.setLayout(group_layout)

                # Widgets
                label_name = QLabel(name.capitalize().replace('_', ' '))
                label_name.setFont(font_titles)
                label_keystr = QLabel(keystr)

                group_layout.addWidget(label_name, i, 0)
                group_layout.addWidget(label_keystr, i, 1)

                added_shortcuts += 1

                if added_shortcuts >= MAX_SHOURCUTS_COLUMN:
                    column_layout.addWidget(group)
                    columns_layout.addLayout(column_layout)
                    added_shortcuts = 0

        column_layout.addWidget(group)
        column_layout.addStretch()  # avoid lasts sections to appear too big
        columns_layout.addLayout(column_layout)

        # widget setup
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowOpacity(0.95)

        # layout
        self._layout = QVBoxLayout()
        self._layout.addWidget(title_label)
        self._layout.addLayout(columns_layout)
        self.setLayout(self._layout)


def test():  # pragma: no cover
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg_shortcuts = ShortCutsSummaryDialog(None)
    dlg_shortcuts.show()
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    test()

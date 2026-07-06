# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Shortcut summary dialog"""

# Standard library imports
from operator import itemgetter
from itertools import groupby

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QKeySequence
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.config.manager import CONF


class ShortcutsSummaryDialog(QDialog, SpyderFontsMixin):
    """
    Dialog window listing the spyder and plugins shortcuts.

    It contains all the shortcuts available through iter_shortcuts
    function

    The shortcuts are dysplayed in different columns, and grouped by
    context (global, editor, console...)
    """
    def __init__(self, parent=None):
        QDialog.__init__(self, parent=parent)

        # Attributes
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )

        # Fonts
        interface_font = self.get_font(SpyderFontType.Interface)

        font_context = QFont(interface_font)
        font_context.setBold(True)

        font_names = interface_font
        font_names.setBold(False)

        font_keystr = self.get_font(SpyderFontType.MonospaceInterface)

        font_title = QFont(interface_font)
        font_title.setPointSize(font_title.pointSize() + 1)

        title_label = QLabel(_("Spyder keyboard shortcuts"))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(font_title)

        # iter over shortcuts and create GroupBox for each context
        # with shortcuts in a grid
        main_layout = QVBoxLayout()
        group = None

        # group shortcuts by context
        shortcuts = groupby(sorted(CONF.iter_shortcuts()), key=itemgetter(0))

        for __, group_shortcuts in shortcuts:

            group_shortcuts = list(group_shortcuts)
            context = group_shortcuts[0][0]

            if context == '_': context = 'Global'

            group = QGroupBox(context.capitalize())
            group.setFont(font_context)

            group_layout = QGridLayout()
            group.setLayout(group_layout)

            for i, (context, name, keystr) in enumerate(group_shortcuts):

                label_name = QLabel(name.capitalize().replace('_', ' '))
                label_name.setFont(font_names)

                keystr = QKeySequence(keystr).toString(
                    QKeySequence.NativeText
                )
                if keystr == "":
                    continue

                label_keystr = QLabel(keystr)
                label_keystr.setFont(font_keystr)

                group_layout.addWidget(label_name, i, 0)
                group_layout.addWidget(label_keystr, i, 1)

            main_layout.addWidget(group)

        main_layout.addStretch()

        # Scroll widget
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(main_layout)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_widget)

        # Buttons
        ok_btn = SpyderDialogButtonBox(QDialogButtonBox.Ok)
        ok_btn.accepted.connect(self.accept)

        # layout
        self._layout = QVBoxLayout()
        self._layout.addWidget(title_label)

        self._layout.addWidget(self.scroll_area)
        self._layout.addWidget(ok_btn)
        self.setLayout(self._layout)

        width, height = self.get_screen_resolution()

        self.adjustSize()

        max_height = int(height * 0.7)
        
        if self.height() > max_height:
            self.resize(self.width(), max_height)
        
        geometry = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        
        geometry.moveCenter(screen_center)
        
        self.move(geometry.topLeft())

        #self.setGeometry(0, 0, width, height)

    def get_screen_resolution(self):
        """Return the screen resolution of the primary screen."""
        geometry = self.screen().availableGeometry()
        return geometry.width(), geometry.height()


def test():  # pragma: no cover
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    dlg_shortcuts = ShortcutsSummaryDialog(None)
    dlg_shortcuts.show()
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    test()

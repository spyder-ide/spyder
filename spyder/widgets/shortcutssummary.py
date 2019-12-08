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
        
        # Make the name of shortcut keys localizable
        shortcut_names_map = {
            'Close pane': _("Close pane"),
            'Configure': _("Configure"),
            'Debug': _("Debug"),
            'Debug continue': _("Debug continue"),
            'Debug exit': _("Debug exit"),
            'Debug step into': _("Debug step into"),
            'Debug step over': _("Debug step over"),
            'Debug step return': _("Debug step return"),
            'File switcher': _("File switcher"),
            'Fullscreen mode': _("Fullscreen mode"),
            'Layout preferences': _("Layout preferences"),
            'Lock unlock panes': _("Lock unlock panes"),
            'Maximize pane': _("Maximize pane"),
            'Preferences': _("Preferences"),
            'Quit': _("Quit"),
            'Re-run last script': _("Re-run last script"),
            'Restart': _("Restart"),
            'Run': _("Run"),
            'Save current layout': _("Save current layout"),
            'Show toolbars': _("Show toolbars"),
            'Spyder documentation': _("Spyder documentation"),
            'Switch to breakpoints': _("Switch to breakpoints"),
            'Switch to editor': _("Switch to editor"),
            'Switch to explorer': _("Switch to explorer"),
            'Switch to find in files': _("Switch to find in files"),
            'Switch to help': _("Switch to help"),
            'Switch to historylog': _("Switch to historylog"),
            'Switch to ipython console': _("Switch to ipython console"),
            'Switch to onlinehelp': _("Switch to onlinehelp"),
            'Switch to outline explorer': _("Switch to outline explorer"),
            'Switch to plots': _("Switch to plots"),
            'Switch to project explorer': _("Switch to project explorer"),
            'Switch to variable explorer': _("Switch to variable explorer"),
            'Symbol finder': _("Symbol finder"),
            'Use next layout': _("Use next layout"),
            'Use previous layout': _("Use previous layout"),
            'Enter array inline': _("Enter array inline"),
            'Enter array table': _("Enter array table"),
            'Clear line': _("Clear line"),
            'Clear shell': _("Clear shell"),
            'Inspect current object': _("Inspect current object"),
            'Blockcomment': _("Blockcomment"),
            'Breakpoint': _("Breakpoint"),
            'Close all': _("Close all"),
            'Close file 1': _("Close file 1"),
            'Close file 2': _("Close file 2"),
            'Close split panel': _("Close split panel"),
            'Code completion': _("Code completion"),
            'Conditional breakpoint': _("Conditional breakpoint"),
            'Copy': _("Copy"),
            'Copy line': _("Copy line"),
            'Cut': _("Cut"),
            'Cycle to next file': _("Cycle to next file"),
            'Cycle to previous file': _("Cycle to previous file"),
            'Debug cell': _("Debug cell"),
            'Delete': _("Delete"),
            'Delete line': _("Delete line"),
            'Docstring': _("Docstring"),
            'Duplicate line': _("Duplicate line"),
            'End of document': _("End of document"),
            'End of line': _("End of line"),
            'Go to definition': _("Go to definition"),
            'Go to line': _("Go to line"),
            'Go to new line': _("Go to new line"),
            'Go to next cell': _("Go to next cell"),
            'Go to next file': _("Go to next file"),
            'Go to previous cell': _("Go to previous cell"),
            'Go to previous file': _("Go to previous file"),
            'Indent': _("Indent"),
            'Kill next word': _("Kill next word"),
            'Kill previous word': _("Kill previous word"),
            'Kill to line end': _("Kill to line end"),
            'Kill to line start': _("Kill to line start"),
            'Last edit location': _("Last edit location"),
            'Move line down': _("Move line down"),
            'Move line up': _("Move line up"),
            'New file': _("New file"),
            'Next char': _("Next char"),
            'Next cursor position': _("Next cursor position"),
            'Next line': _("Next line"),
            'Next warning': _("Next warning"),
            'Next word': _("Next word"),
            'Open file': _("Open file"),
            'Open last closed': _("Open last closed"),
            'Paste': _("Paste"),
            'Previous char': _("Previous char"),
            'Previous cursor position': _("Previous cursor position"),
            'Previous line': _("Previous line"),
            'Previous warning': _("Previous warning"),
            'Previous word': _("Previous word"),
            'Re-run last cell': _("Re-run last cell"),
            'Redo': _("Redo"),
            'Rotate kill ring': _("Rotate kill ring"),
            'Run cell': _("Run cell"),
            'Run cell and advance': _("Run cell and advance"),
            'Run selection': _("Run selection"),
            'Save all': _("Save all"),
            'Save as': _("Save as"),
            'Save file': _("Save file"),
            'Select all': _("Select all"),
            'Split horizontally': _("Split horizontally"),
            'Split vertically': _("Split vertically"),
            'Start of document': _("Start of document"),
            'Start of line': _("Start of line"),
            'Toggle comment': _("Toggle comment"),
            'Transform to lowercase': _("Transform to lowercase"),
            'Transform to uppercase': _("Transform to uppercase"),
            'Unblockcomment': _("Unblockcomment"),
            'Undo': _("Undo"),
            'Unindent': _("Unindent"),
            'Yank': _("Yank"),
            'Zoom in 1': _("Zoom in 1"),
            'Zoom in 2': _("Zoom in 2"),
            'Zoom out': _("Zoom out"),
            'Zoom reset': _("Zoom reset"),
            'Copy absolute path': _("Copy absolute path"),
            'Copy file': _("Copy file"),
            'Copy relative path': _("Copy relative path"),
            'Paste file': _("Paste file"),
            'Find next': _("Find next"),
            'Find previous': _("Find previous"),
            'Find text': _("Find text"),
            'Hide find and replace': _("Hide find and replace"),
            'Replace text': _("Replace text"),
            'New tab': _("New tab"),
            'Reset namespace': _("Reset namespace"),
            'Restart kernel': _("Restart kernel"),
            'Next figure': _("Next figure"),
            'Previous figure': _("Previous figure"),
            'Run profiler': _("Run profiler"),
            'Run analysis': _("Run analysis"),
            'Refresh': _("Refresh"),
            'Search': _("Search"),
        }

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
                label_text = name.capitalize().replace('_', ' ')
                print(label_text)
                try:
                    label_text_localized = shortcut_names_map[label_text]
                except KeyError:
                    label_text_localized = label_text
                label_name = QLabel(label_text_localized)
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

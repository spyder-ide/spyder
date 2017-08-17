# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""History Widget."""

# Standard library imports
import os.path as osp
import sys

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (QHBoxLayout, QMenu, QWidget, QToolButton,
                            QVBoxLayout)

# Local imports
from spyder.utils import encoding
from spyder.py3compat import is_text_string, to_text_string
from spyder.plugins.editor.widgets import codeeditor
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import add_actions, create_toolbutton
from spyder.widgets.tabs import Tabs
from spyder.widgets.findreplace import FindReplace


class History(QWidget):
    """History plugin main widget."""

    focus_changed = Signal()

    def __init__(self, parent):
        """Initialize widget and create layout."""
        QWidget.__init__(self, parent)

        self.editors = []
        self.filenames = []

        self.tabwidget = None
        self.menu_actions = None

        layout = QVBoxLayout()
        self.tabwidget = Tabs(self, self.menu_actions)
        self.tabwidget.currentChanged.connect(self.refresh)
        self.tabwidget.move_data.connect(self.move_tab)

        if sys.platform == 'darwin':
            tab_container = QWidget()
            tab_container.setObjectName('tab-container')
            tab_layout = QHBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabwidget)
            layout.addWidget(tab_container)
        else:
            layout.addWidget(self.tabwidget)

        # Menu as corner widget
        options_button = create_toolbutton(self, text=_('Options'),
                                           icon=ima.icon('tooloptions'))
        options_button.setPopupMode(QToolButton.InstantPopup)
        self.menu = QMenu(self)

        options_button.setMenu(self.menu)
        self.tabwidget.setCornerWidget(options_button)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()

        layout.addWidget(self.find_widget)

        self.setLayout(layout)

    def set_menu_actions(self, menu_actions):
        """Add options to corner menu."""
        if self.menu_actions is not None:
            add_actions(self.menu, self.menu_actions)

    def refresh(self):
        """Refresh tabwidget."""
        if self.tabwidget.count():
            editor = self.tabwidget.currentWidget()
        else:
            editor = None
        self.find_widget.set_editor(editor)

    def move_tab(self, index_from, index_to):
        """
        Move tab.

        (tabs themselves have already been moved by the history.tabwidget)
        """
        filename = self.filenames.pop(index_from)
        editor = self.editors.pop(index_from)

        self.filenames.insert(index_to, filename)
        self.editors.insert(index_to, editor)

    def add_history(self, filename, color_scheme, font, wrap):
        """
        Add new history tab.

        Args:
            filename (str): file to be loaded in a new tab.
        """
        filename = encoding.to_unicode_from_fs(filename)
        if filename in self.filenames:
            return
        editor = codeeditor.CodeEditor(self)
        if osp.splitext(filename)[1] == '.py':
            language = 'py'
        else:
            language = 'bat'
        editor.setup_editor(linenumbers=False,
                            language=language,
                            scrollflagarea=False,
                            show_class_func_dropdown=False)
        editor.focus_changed.connect(lambda: self.focus_changed.emit())
        editor.setReadOnly(True)

        editor.set_font(font, color_scheme)
        editor.toggle_wrap_mode(wrap)

        text, _ = encoding.read(filename)
        editor.set_text(text)
        editor.set_cursor_position('eof')

        self.editors.append(editor)
        self.filenames.append(filename)
        index = self.tabwidget.addTab(editor, osp.basename(filename))
        self.find_widget.set_editor(editor)
        self.tabwidget.setTabToolTip(index, filename)
        self.tabwidget.setCurrentIndex(index)

    def append_to_history(self, filename, command, go_to_eof):
        """
        Append an entry to history filename.

        Args:
            filename (str): file to be updated in a new tab.
            command (str): line to be added.
            go_to_eof (bool): scroll to the end of file.
        """
        if not is_text_string(filename): # filename is a QString
            filename = to_text_string(filename.toUtf8(), 'utf-8')
        command = to_text_string(command)
        index = self.filenames.index(filename)
        self.editors[index].append(command)
        if go_to_eof:
            self.editors[index].set_cursor_position('eof')
        self.tabwidget.setCurrentIndex(index)

def test():
    """Run history widget."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=8)
    widget = History(None)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()

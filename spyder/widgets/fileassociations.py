# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
File assoaciations widget for use in global and project preferences.
"""

# Standard library imports
from __future__ import print_function
import os
import os.path as osp
import sys

# Third party imports
from qtpy.QtCore import (Signal, Slot, QEvent, QFileInfo, QObject, QRegExp,
                         QSize, Qt)
from qtpy.QtGui import (QIcon, QRegExpValidator, QTextCursor)
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QVBoxLayout,
                            QMainWindow, QListWidgetItem)

# Local imports
from spyder.config.base import _
from spyder.py3compat import iteritems, to_text_string
from spyder.config.utils import is_ubuntu
from spyder.utils import icon_manager as ima
from spyder.utils.stringmatching import get_search_scores
from spyder.widgets.helperwidgets import HelperToolButton, HTMLDelegate
from spyder.config.main import CONF


# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QGroupBox, QLabel, QVBoxLayout, QListWidget,
                            QPushButton, QHBoxLayout, QWidget, QTabWidget)

# Local imports
from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _


class FileAssociationsWidget(QWidget):
    """"""

    def __init__(self, parent=None):
        """"""
        super(FileAssociationsWidget, self).__init__(parent=parent)

        # Widgets
        self.label = QLabel(_('This is the main description of this tab.'))
        self.label_extensions = QLabel(_('File types:'))
        self.list_extensions = QListWidget()
        self.button_add = QPushButton(_('Add'))
        self.button_remove = QPushButton(_('Remove'))

        self.label_editors = QLabel(_('Associated editors:'))
        self.list_editors = QListWidget()
        self.button_add_editor = QPushButton(_('Add editor'))
        self.button_remove_editor = QPushButton(_('Remove editor'))
        self.button_default = QPushButton(_('Set default'))

        # Layout
        layout_extensions = QHBoxLayout()
        layout_extensions.addWidget(self.list_extensions, 4)

        layout_buttons_extensions = QVBoxLayout()
        layout_buttons_extensions.addWidget(self.button_add)
        layout_buttons_extensions.addWidget(self.button_remove)
        layout_buttons_extensions.addStretch()

        layout_editors = QHBoxLayout()
        layout_editors.addWidget(self.list_editors, 4)

        layout_buttons_editors = QVBoxLayout()
        layout_buttons_editors.addWidget(self.button_add_editor)
        layout_buttons_editors.addWidget(self.button_remove_editor)
        layout_buttons_editors.addWidget(self.button_default)
        layout_buttons_editors.addStretch()

        layout_extensions.addLayout(layout_buttons_extensions, 1)
        layout_editors.addLayout(layout_buttons_editors, 1)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.label_extensions)
        layout.addLayout(layout_extensions)
        layout.addWidget(self.label_editors)
        layout.addLayout(layout_editors)

        self.setLayout(layout)

        # Signals
        self.button_add.clicked.connect(self.add_association)
        self.button_remove.clicked.connect(self.remove_association)
        self.button_add_editor.clicked.connect(self.add_editor)
        self.button_remove_editor.clicked.connect(self.remove_editor)
        self.button_default.clicked.connect(self.set_as_default_editor)

        self._setup()

    def _setup(self):
        """"""
        for widget in [self.button_remove, self.button_add_editor,
                       self.button_add_editor, self.button_remove_editor,
                       self.button_default]:
            widget.setDisabled(True)

    def _check_values(self):
        """"""

    def _add_association(self):
        """"""

    def _remove_association(self, index):
        """"""

    def _add_editor(self):
        """"""

    def load_values(self, values=None):
        """"""

    def add_association(self, show_dialog=True):
        """"""

    def remove_association(self, index):
        """"""

    def add_editor(self):
        """"""

    def remove_editor(self):
        """"""

    def set_as_default_editor(self):
        """"""

    def update_list(self):
        """"""

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from qtpy.QtCore import Qt
from qtpy.QtGui import QIntValidator
from qtpy.QtWidgets import (QDialog, QLabel, QLineEdit, QGridLayout,
                            QDialogButtonBox, QVBoxLayout, QHBoxLayout)

from spyder.api.translations import _


class GoToLineDialog(QDialog):
    def __init__(self, editor):
        QDialog.__init__(self, editor, Qt.WindowTitleHint
                         | Qt.WindowCloseButtonHint)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.lineno = None
        self.editor = editor

        self.setWindowTitle(_("Editor"))
        self.setModal(True)

        label = QLabel(_("Go to line:"))
        self.lineedit = QLineEdit()
        validator = QIntValidator(self.lineedit)
        validator.setRange(1, editor.get_line_count())
        self.lineedit.setValidator(validator)
        self.lineedit.textChanged.connect(self.text_has_changed)
        cl_label = QLabel(_("Current line:"))
        cl_label_v = QLabel("<b>%d</b>" % editor.get_cursor_line_number())
        last_label = QLabel(_("Line count:"))
        last_label_v = QLabel("%d" % editor.get_line_count())

        glayout = QGridLayout()
        glayout.addWidget(label, 0, 0, Qt.AlignVCenter | Qt.AlignRight)
        glayout.addWidget(self.lineedit, 0, 1, Qt.AlignVCenter)
        glayout.addWidget(cl_label, 1, 0, Qt.AlignVCenter | Qt.AlignRight)
        glayout.addWidget(cl_label_v, 1, 1, Qt.AlignVCenter)
        glayout.addWidget(last_label, 2, 0, Qt.AlignVCenter | Qt.AlignRight)
        glayout.addWidget(last_label_v, 2, 1, Qt.AlignVCenter)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                Qt.Vertical, self)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        btnlayout = QVBoxLayout()
        btnlayout.addWidget(bbox)
        btnlayout.addStretch(1)

        ok_button = bbox.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(False)
        # QIntValidator does not handle '+' sign
        # See spyder-ide/spyder#20070
        self.lineedit.textChanged.connect(
                     lambda text: ok_button.setEnabled(len(text) > 0 and text != '+'))

        layout = QHBoxLayout()
        layout.addLayout(glayout)
        layout.addLayout(btnlayout)
        self.setLayout(layout)

        self.lineedit.setFocus()

    def text_has_changed(self, text):
        """Line edit's text has changed."""
        text = str(text)

        # QIntValidator does not handle '+' sign
        # See spyder-ide/spyder#12693
        if text and text != '+':
            self.lineno = int(text)
        else:
            self.lineno = None
            self.lineedit.clear()

    def get_line_number(self):
        """Return line number."""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.lineno

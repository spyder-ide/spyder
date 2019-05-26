# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Text editor dialog
"""

# Standard library imports
from __future__ import print_function

# Third party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QPushButton, QTextEdit,
                            QVBoxLayout)

# Local import
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.py3compat import (is_binary_string, to_binary_string,
                              to_text_string, PY3, PY2)
from spyder.utils import icon_manager as ima


class TextEditor(QDialog):
    """Array Editor Dialog"""
    def __init__(self, text, title='', font=None, parent=None,
                 readonly=False, size=(400, 300)):
        QDialog.__init__(self, parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.text = None
        self.btn_save_and_close = None

        # Display text as unicode if it comes as bytes, so users see
        # its right representation
        if is_binary_string(text):
            self.is_binary = True
            text = to_text_string(text, 'utf8')
        else:
            self.is_binary = False

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Text edit
        self.edit = QTextEdit(parent)
        self.edit.setReadOnly(readonly)
        self.edit.textChanged.connect(self.text_changed)
        self.edit.setPlainText(text)
        if font is None:
            font = get_font()
        self.edit.setFont(font)
        self.layout.addWidget(self.edit)

        # Buttons configuration
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        if not readonly:
            self.btn_save_and_close = QPushButton(_('Save and Close'))
            self.btn_save_and_close.setDisabled(True)
            self.btn_save_and_close.clicked.connect(self.accept)
            btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_('Close'))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        self.layout.addLayout(btn_layout)

        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)

        self.setWindowIcon(ima.icon('edit'))
        if title:
            try:
                unicode_title = to_text_string(title)
            except UnicodeEncodeError:
                unicode_title = u''
        else:
            unicode_title = u''

        self.setWindowTitle(_("Text editor") + \
                            u"%s" % (u" - " + unicode_title
                                     if unicode_title else u""))
        self.resize(size[0], size[1])

    @Slot()
    def text_changed(self):
        """Text has changed"""
        # Save text as bytes, if it was initially bytes
        if self.is_binary:
            self.text = to_binary_string(self.edit.toPlainText(), 'utf8')
        else:
            self.text = to_text_string(self.edit.toPlainText())
        if self.btn_save_and_close:
            self.btn_save_and_close.setEnabled(True)
            self.btn_save_and_close.setAutoDefault(True)
            self.btn_save_and_close.setDefault(True)

    def get_value(self):
        """Return modified text"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.text

    def setup_and_check(self, value):
        """Verify if TextEditor is able to display strings passed to it."""
        try:
            to_text_string(value, 'utf8')
            return True
        except:
            return False


#==============================================================================
# Tests
#==============================================================================
def test():
    """Text editor demo"""
    from spyder.utils.qthelpers import qapplication
    _app = qapplication()  # analysis:ignore

    text = """01234567890123456789012345678901234567890123456789012345678901234567890123456789
dedekdh elkd ezd ekjd lekdj elkdfjelfjk e"""
    dialog = TextEditor(text)
    dialog.exec_()

    dlg_text = dialog.get_value()
    assert text == dlg_text


if __name__ == "__main__":
    test()

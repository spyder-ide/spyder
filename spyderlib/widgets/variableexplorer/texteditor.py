# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Text editor dialog
"""

from __future__ import print_function

from spyderlib.qt.QtCore import Qt
from spyderlib.qt.QtGui import QVBoxLayout, QTextEdit, QDialog, QDialogButtonBox
import spyderlib.utils.icon_manager as ima

# Local import
from spyderlib.config.base import _
from spyderlib.config.gui import get_font
from spyderlib.py3compat import (to_text_string, to_binary_string,
                                 is_binary_string)


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
        self.edit.textChanged.connect(self.text_changed)
        self.edit.setReadOnly(readonly)
        self.edit.setPlainText(text)
        if font is None:
            font = get_font('texteditor')
        self.edit.setFont(font)
        self.layout.addWidget(self.edit)

        # Buttons configuration
        buttons = QDialogButtonBox.Ok
        if not readonly:
            buttons = buttons | QDialogButtonBox.Cancel
        bbox = QDialogButtonBox(buttons)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        self.layout.addWidget(bbox)
        
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        
        self.setWindowIcon(ima.icon('edit'))
        self.setWindowTitle(_("Text editor") + \
                            "%s" % (" - "+str(title) if str(title) else ""))
        self.resize(size[0], size[1])
    
    def text_changed(self):
        """Text has changed"""
        # Save text as bytes, if it was initially bytes
        if self.is_binary:
            self.text = to_binary_string(self.edit.toPlainText(), 'utf8')
        else:
            self.text = to_text_string(self.edit.toPlainText())
        
    def get_value(self):
        """Return modified text"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.text


#==============================================================================
# Tests
#==============================================================================
def test():
    """Text editor demo"""
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()  # analysis:ignore

    text = """01234567890123456789012345678901234567890123456789012345678901234567890123456789
dedekdh elkd ezd ekjd lekdj elkdfjelfjk e"""
    dialog = TextEditor(text)
    dialog.exec_()

    dlg_text = dialog.get_value()
    assert text == dlg_text


if __name__ == "__main__":
    test()

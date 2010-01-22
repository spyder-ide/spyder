# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Text Editor Dialog based on PyQt4
"""

from PyQt4.QtCore import Qt, SIGNAL, SLOT
from PyQt4.QtGui import QVBoxLayout, QTextEdit, QDialog, QDialogButtonBox

# Local import
from spyderlib.config import get_icon, get_font


class TextEditor(QDialog):
    """Array Editor Dialog"""
    def __init__(self, text, title='', font=None, parent=None,
                 readonly=False, size=(400, 300)):
        super(TextEditor, self).__init__(parent)
        
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Text edit
        self.edit = QTextEdit(parent)
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
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        self.layout.addWidget(bbox)
        
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        
        self.setWindowIcon(get_icon('edit.png'))
        self.setWindowTitle(self.tr("Text editor") + \
                            "%s" % (" - "+str(title) if str(title) else ""))
        self.resize(size[0], size[1])
        
    def get_copy(self):
        """Return modified text"""
        return unicode(self.edit.toPlainText())
    
    
def test():
    """Text editor demo"""
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()
    dialog = TextEditor("""
    01234567890123456789012345678901234567890123456789012345678901234567890123456789
    dedekdh elkd ezd ekjd lekdj elkdfjelfjk e
    """)
    if dialog.exec_():
        text = dialog.get_copy()
        print "Accepted:", text
        dialog = TextEditor(text)
        dialog.exec_()
    else:
        print "Canceled"

if __name__ == "__main__":
    test()
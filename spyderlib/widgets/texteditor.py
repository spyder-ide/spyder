# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Text Editor Dialog based on Qt
"""

from spyderlib.qt.QtCore import Qt, SIGNAL, SLOT
from spyderlib.qt.QtGui import QVBoxLayout, QTextEdit, QDialog, QDialogButtonBox

# Local import
from spyderlib.config import get_icon, get_font, _


class TextEditor(QDialog):
    """Array Editor Dialog"""
    def __init__(self, text, title='', font=None, parent=None,
                 readonly=False, size=(400, 300)):
        QDialog.__init__(self, parent)
        
        self._conv = str if isinstance(text, str) else unicode
        
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
        self.setWindowTitle(_("Text editor") + \
                            "%s" % (" - "+str(title) if str(title) else ""))
        self.resize(size[0], size[1])
        
    def get_value(self):
        """Return modified text"""
        return self._conv(self.edit.toPlainText())
    
    
def test():
    """Text editor demo"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    dialog = TextEditor("""
    01234567890123456789012345678901234567890123456789012345678901234567890123456789
    dedekdh elkd ezd ekjd lekdj elkdfjelfjk e
    """)
    dialog.show()
    app.exec_()
    if dialog.result():
        text = dialog.get_value()
        print "Accepted:", text
        dialog = TextEditor(text)
        dialog.exec_()
    else:
        print "Canceled"

if __name__ == "__main__":
    test()
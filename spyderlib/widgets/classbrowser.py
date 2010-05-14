# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Class browser widget

******************************** WARNING ***************************************
    This module is not used anymore in Spyder since v1.1.0.
    However, it will still be part of spyderlib module for a little while -
    we never know, it could be useful...
********************************************************************************
"""

import os.path as osp
import sys

# For debugging purpose:
STDOUT = sys.stdout

from PyQt4.QtGui import QTreeWidgetItem
from PyQt4.QtCore import SIGNAL

# Local imports
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import translate
from spyderlib.widgets import OneColumnTree
from spyderlib.utils.classparser import get_classes


class ClassBrowser(OneColumnTree):
    def __init__(self, parent):
        OneColumnTree.__init__(self, parent)
        title = translate("ClassBrowser", "Classes and functions")
        self.setWindowTitle(title)
        self.set_title(title)
        self.fname = None
        self.classes = None
        self.lines = None
        
    def clear(self):
        """Reimplemented Qt method"""
        self.set_title('')
        OneColumnTree.clear(self)
        
    def refresh(self, data=None, update=True):
        """Refresh class browser"""
        if data is not None:
            fname, self.classes, self.lines = data
            self.fname = osp.abspath(fname)
        if data is None or self.classes is None or update:
            try:
                self.classes = get_classes(self.fname)
            except (SyntaxError, IOError):
                if self.classes is None:
                    self.clear()
                return (self.fname, self.classes, self.lines)
        self.clear()
        self.populate_classes()
        self.resizeColumnToContents(0)
        self.expandAll()
        self.set_title(osp.basename(self.fname))
        return (self.fname, self.classes, self.lines)

    def activated(self, item):
        """Double-click or click event"""
        self.emit(SIGNAL('go_to_line(int)'), self.lines[item])
        
    def populate_classes(self):
        """Populate classes"""
        self.lines = {}
        for lineno, c_name, methods in self.classes:
            item = QTreeWidgetItem(self, [c_name])
            self.lines[item] = lineno
            if methods is None:
                item.setIcon(0, get_icon('function.png'))
            else:
                item.setIcon(0, get_icon('class.png'))
            if methods:
                self.populate_methods(item, c_name, methods)
            
    def populate_methods(self, parent, c_name, methods):
        """Populate methods"""
        for lineno, m_name in methods:
            decorator = m_name.startswith('@')
            if decorator:
                m_name = m_name[1:]
            item = QTreeWidgetItem(parent, [m_name])
            self.lines[item] = lineno
            if m_name.startswith('__'):
                item.setIcon(0, get_icon('private2.png'))
            elif m_name.startswith('_'):
                item.setIcon(0, get_icon('private1.png'))
            elif decorator:
                item.setIcon(0, get_icon('decorator.png'))
            else:
                item.setIcon(0, get_icon('method.png'))


def test(fname):
    """Show class browser for Python script *fname*"""
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    widget = ClassBrowser(None)
    data = (fname, None, None)
    widget.refresh(data)
    widget.show()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = "classbrowser.py"
    test(fname)
    
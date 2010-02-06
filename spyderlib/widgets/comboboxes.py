# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Customized combobox widgets"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import QComboBox, QFont, QToolTip, QSizePolicy, QCompleter
from PyQt4.QtCore import SIGNAL, Qt, QUrl

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout


class BaseComboBox(QComboBox):
    """Editable combo box base class"""
    def __init__(self, parent):
        super(BaseComboBox, self).__init__(parent)
        self.setEditable(True)
        self.setCompleter(QCompleter(self))
        
    def is_valid(self, qstr):
        """
        Return True if string is valid
        Return None if validation can't be done
        """
        pass
        
    def selected(self):
        """Action to be executed when a valid item has been selected"""
        self.emit(SIGNAL('valid(bool)'), True)
        
    def add_text(self, text):
        """Add text to combo box: add a new item if text is not found in 
        combo box items"""
        index = self.findText(text)
        while index != -1:
            self.removeItem(index)
            index = self.findText(text)
        self.insertItem(0, text)
        self.setCurrentIndex(0)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            text = self.currentText()
            valid = self.is_valid(text)
            if valid or valid is None:
                self.add_text(text)
                self.selected()
        else:
            QComboBox.keyPressEvent(self, event)
        

class PatternComboBox(BaseComboBox):
    """Search pattern combo box"""
    def __init__(self, parent, items=None, tip=None,
                 adjust_to_minimum=True):
        super(PatternComboBox, self).__init__(parent)
        if adjust_to_minimum:
            self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if items is not None:
            self.addItems(items)
        if tip is not None:
            self.setToolTip(tip)


class EditableComboBox(BaseComboBox):
    """
    Editable combo box + Validate
    """
    def __init__(self, parent):
        super(EditableComboBox, self).__init__(parent)
        self.font = QFont()
        self.connect(self, SIGNAL("editTextChanged(QString)"), self.validate)
        self.connect(self, SIGNAL("activated(QString)"),
                     lambda qstr: self.validate(qstr, editing=False))
        self.set_default_style()
        self.tips = {True: self.tr("Press enter to validate this entry"),
                     False: self.tr('This entry is incorrect')}
        
    def show_tip(self, tip=""):
        """Show tip"""
        QToolTip.showText(self.mapToGlobal(self.pos()), tip, self)
        
    def set_default_style(self):
        """Set widget style to default"""
        self.font.setBold(False)
        self.setFont(self.font)
        self.setStyleSheet("")
        self.show_tip()
        
    def selected(self):
        """Action to be executed when a valid item has been selected"""
        super(EditableComboBox, self).selected()        
        self.set_default_style()
        
    def validate(self, qstr, editing=True):
        """Validate entered path"""
        valid = self.is_valid(qstr)
        if self.hasFocus() and valid is not None:
            self.font.setBold(True)
            self.setFont(self.font)
            if valid:
                self.setStyleSheet("color:rgb(50, 155, 50);")
            else:
                self.setStyleSheet("color:rgb(200, 50, 50);")
            if editing:
                # Combo box text is being modified: invalidate the entry
                self.show_tip(self.tips[valid])
                self.emit(SIGNAL('valid(bool)'), False)
            else:
                # A new item has just been selected
                if valid:
                    self.selected()
                else:
                    self.emit(SIGNAL('valid(bool)'), False)
        else:
            self.set_default_style()
            

class PathComboBox(EditableComboBox):
    """
    QComboBox handling path locations
    """
    def __init__(self, parent, adjust_to_contents=False):
        super(PathComboBox, self).__init__(parent)
        if adjust_to_contents:
            self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        else:
            self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: self.tr("Press enter to validate this path"),
                     False: self.tr('This path is incorrect.\n'
                                    'Enter a correct directory path.\n'
                                    'Then press enter to validate')}
        
    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return osp.isdir( unicode(qstr) )
    
    def selected(self):
        """Action to be executed when a valid item has been selected"""
        EditableComboBox.selected(self)
        self.emit(SIGNAL("open_dir(QString)"), self.currentText())


class UrlComboBox(PathComboBox):
    """
    QComboBox handling urls
    """
    def __init__(self, parent, adjust_to_contents=False):
        super(UrlComboBox, self).__init__(parent, adjust_to_contents)
        self.disconnect(self, SIGNAL("editTextChanged(QString)"), self.validate)
        
    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return QUrl(qstr).isValid()


def is_module_or_package(path):
    """Return True if path is a Python module/package"""
    is_module = osp.isfile(path) and osp.splitext(path)[1] in ('.py', '.pyw')
    is_package = osp.isdir(path) and osp.isfile(osp.join(path, '__init__.py'))
    return is_module or is_package

class PythonModulesComboBox(PathComboBox):
    """
    QComboBox handling Python modules or packages path
    (i.e. .py, .pyw files *and* directories containing __init__.py)
    """
    def __init__(self, parent, adjust_to_contents=False):
        PathComboBox.__init__(self, parent, adjust_to_contents)
        
    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return is_module_or_package(unicode(qstr))
    
    def selected(self):
        """Action to be executed when a valid item has been selected"""
        EditableComboBox.selected(self)
        self.emit(SIGNAL("open(QString)"), self.currentText())

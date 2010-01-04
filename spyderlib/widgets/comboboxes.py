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
from PyQt4.QtCore import SIGNAL, Qt

import sys
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout


class PatternComboBox(QComboBox):
    """Search pattern combo box"""
    def __init__(self, parent, items=None, tip=None,
                 adjust_to_minimum=True):
        QComboBox.__init__(self, parent)
        if adjust_to_minimum:
            self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setEditable(True)
        self.setCompleter(QCompleter(self))
        if items is not None:
            self.addItems(items)
        if tip is not None:
            self.setToolTip(tip)


class EditableComboBox(QComboBox):
    """
    Editable QComboBox
    """
    def __init__(self, parent):
        super(EditableComboBox, self).__init__(parent)
        self.font = QFont()
        self.setEditable(True)
        self.setCompleter(QCompleter(self))
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
        
    def is_valid(self, qstr):
        """
        Return True if string is valid
        Return None if validation can't be done
        """
        pass
        
    def selected(self):
        """Action to be executed when a valid item has been selected"""
        self.set_default_style()
        self.emit(SIGNAL('valid(bool)'), True)
        
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

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.is_valid():
                self.selected()
                QComboBox.keyPressEvent(self, event) # Insert item in combo box
        else:
            QComboBox.keyPressEvent(self, event)


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

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.is_valid():
                self.selected()
                QComboBox.keyPressEvent(self, event) # Insert item in combo box
        else:
            QComboBox.keyPressEvent(self, event)

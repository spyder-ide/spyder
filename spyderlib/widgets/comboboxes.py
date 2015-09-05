# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Customized combobox widgets"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QComboBox, QFont, QToolTip, QSizePolicy,
                                QCompleter)
<<<<<<< HEAD
from spyderlib.qt.QtCore import SIGNAL, Qt, QUrl, QTimer
=======
from spyderlib.qt.QtCore import Signal, Qt, QUrl, QTimer
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

import os.path as osp

# Local imports
<<<<<<< HEAD
from spyderlib.baseconfig import _
=======
from spyderlib.config.base import _
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
from spyderlib.py3compat import to_text_string


class BaseComboBox(QComboBox):
    """Editable combo box base class"""
<<<<<<< HEAD
=======
    valid = Signal(bool)
    
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def __init__(self, parent):
        QComboBox.__init__(self, parent)
        self.setEditable(True)
        self.setCompleter(QCompleter(self))

    # --- overrides
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.add_current_text_if_valid():
                self.selected()
        else:
            QComboBox.keyPressEvent(self, event)

    def focusOutEvent(self, event):
        """Handle focus out event"""
        # Calling asynchronously the 'add_current_text' to avoid crash
        # https://groups.google.com/group/spyderlib/browse_thread/thread/2257abf530e210bd
        QTimer.singleShot(50, self.add_current_text_if_valid)
        QComboBox.focusOutEvent(self, event)

    # --- own methods
    def is_valid(self, qstr):
        """
        Return True if string is valid
        Return None if validation can't be done
        """
        pass
        
    def selected(self):
        """Action to be executed when a valid item has been selected"""
<<<<<<< HEAD
        self.emit(SIGNAL('valid(bool)'), True)
=======
        self.valid.emit(True)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        
    def add_text(self, text):
        """Add text to combo box: add a new item if text is not found in 
        combo box items"""
        index = self.findText(text)
        while index != -1:
            self.removeItem(index)
            index = self.findText(text)
        self.insertItem(0, text)
        index = self.findText('')
        if index != -1:
            self.removeItem(index)
            self.insertItem(0, '')
            if text != '':
                self.setCurrentIndex(1)
            else:
                self.setCurrentIndex(0)
        else:
            self.setCurrentIndex(0)
            
    def add_current_text(self):
        """Add current text to combo box history (convenient method)"""
        self.add_text(self.currentText())
            
    def add_current_text_if_valid(self):
        """Add current text to combo box history if valid"""
        valid = self.is_valid(self.currentText())
        if valid or valid is None:
            self.add_current_text()
            return True
        

class PatternComboBox(BaseComboBox):
    """Search pattern combo box"""
    def __init__(self, parent, items=None, tip=None,
                 adjust_to_minimum=True):
        BaseComboBox.__init__(self, parent)
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
        BaseComboBox.__init__(self, parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.font = QFont()
<<<<<<< HEAD
        self.connect(self, SIGNAL("editTextChanged(QString)"), self.validate)
        self.connect(self, SIGNAL("activated(QString)"),
                     lambda qstr: self.validate(qstr, editing=False))
=======
        self.editTextChanged.connect(self.validate)
        self.activated.connect(lambda qstr: self.validate(qstr, editing=False))
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        self.set_default_style()
        self.tips = {True: _("Press enter to validate this entry"),
                     False: _('This entry is incorrect')}
        
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
        BaseComboBox.selected(self)
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
<<<<<<< HEAD
                self.emit(SIGNAL('valid(bool)'), False)
=======
                self.valid.emit(False)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
            else:
                # A new item has just been selected
                if valid:
                    self.selected()
                else:
<<<<<<< HEAD
                    self.emit(SIGNAL('valid(bool)'), False)
=======
                    self.valid.emit(False)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        else:
            self.set_default_style()
            

class PathComboBox(EditableComboBox):
    """
    QComboBox handling path locations
    """
<<<<<<< HEAD
=======
    open_dir = Signal(str)
    
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    def __init__(self, parent, adjust_to_contents=False):
        EditableComboBox.__init__(self, parent)
        if adjust_to_contents:
            self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        else:
            self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.tips = {True: _("Press enter to validate this path"),
                     False: _('This path is incorrect.\n'
                                    'Enter a correct directory path,\n'
                                    'then press enter to validate')}
        
    def is_valid(self, qstr=None):
        """Return True if string is valid"""
        if qstr is None:
            qstr = self.currentText()
        return osp.isdir( to_text_string(qstr) )
    
    def selected(self):
        """Action to be executed when a valid item has been selected"""
        EditableComboBox.selected(self)
<<<<<<< HEAD
        self.emit(SIGNAL("open_dir(QString)"), self.currentText())
=======
        self.open_dir.emit(self.currentText())
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f


class UrlComboBox(PathComboBox):
    """
    QComboBox handling urls
    """
    def __init__(self, parent, adjust_to_contents=False):
        PathComboBox.__init__(self, parent, adjust_to_contents)
<<<<<<< HEAD
        self.disconnect(self, SIGNAL("editTextChanged(QString)"), self.validate)
=======
        self.editTextChanged.disconnect(self.validate)
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
        
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

<<<<<<< HEAD
=======

>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
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
        return is_module_or_package(to_text_string(qstr))
    
    def selected(self):
        """Action to be executed when a valid item has been selected"""
        EditableComboBox.selected(self)
<<<<<<< HEAD
        self.emit(SIGNAL("open(QString)"), self.currentText())
=======
        self.open_dir.emit(self.currentText())
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f

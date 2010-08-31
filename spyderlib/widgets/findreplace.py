# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Find/Replace widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QHBoxLayout, QGridLayout, QCheckBox, QLabel, QWidget,
                         QSizePolicy, QShortcut, QKeySequence)
from PyQt4.QtCore import SIGNAL, Qt

import sys

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils.qthelpers import get_std_icon, create_toolbutton
from spyderlib.widgets.comboboxes import PatternComboBox


class FindReplace(QWidget):
    """
    Find widget
    
    Signals:
        visibility_changed(bool)
    """
    STYLE = {False: "background-color:rgb(255, 175, 90);",
             True: ""}
    def __init__(self, parent, enable_replace=False):
        QWidget.__init__(self, parent)
        self.enable_replace = enable_replace
        self.editor = None
        
        glayout = QGridLayout()
        glayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(glayout)
        
        self.close_button = create_toolbutton(self, triggered=self.hide,
                                      icon=get_std_icon("DialogCloseButton"))
        glayout.addWidget(self.close_button, 0, 0)
        
        # Find layout
        self.search_text = PatternComboBox(self, tip=self.tr("Search string"),
                                           adjust_to_minimum=False)
        self.connect(self.search_text, SIGNAL("editTextChanged(QString)"),
                     self.text_has_changed)
        
        self.previous_button = create_toolbutton(self,
                                             text=self.tr("Previous"),
                                             triggered=self.find_previous,
                                             icon=get_std_icon("ArrowBack"))
        self.next_button = create_toolbutton(self,
                                             text=self.tr("Next"),
                                             triggered=self.find_next,
                                             icon=get_std_icon("ArrowForward"))
        self.connect(self.next_button, SIGNAL('clicked()'),
                     self.update_search_combo)
        self.connect(self.previous_button, SIGNAL('clicked()'),
                     self.update_search_combo)

        self.case_check = QCheckBox(self.tr("Case Sensitive"))
        self.connect(self.case_check, SIGNAL("stateChanged(int)"), self.find)
        self.words_check = QCheckBox(self.tr("Whole words"))
        self.connect(self.words_check, SIGNAL("stateChanged(int)"), self.find)

        hlayout = QHBoxLayout()
        self.widgets = [self.close_button, self.search_text, self.previous_button,
                        self.next_button, self.case_check, self.words_check]
        for widget in self.widgets[1:]:
            hlayout.addWidget(widget)
        glayout.addLayout(hlayout, 0, 1)

        # Replace layout
        replace_with = QLabel(self.tr("Replace with:"))
        self.replace_text = PatternComboBox(self, adjust_to_minimum=False,
                                            tip=self.tr("Replace string"))
        
        self.replace_button = create_toolbutton(self,
                                     text=self.tr("Replace/find"),
                                     triggered=self.replace_find,
                                     icon=get_std_icon("DialogApplyButton"))
        self.connect(self.replace_button, SIGNAL('clicked()'),
                     self.update_replace_combo)
        self.connect(self.replace_button, SIGNAL('clicked()'),
                     self.update_search_combo)
        
        self.all_check = QCheckBox(self.tr("Replace all"))
        
        self.replace_layout = QHBoxLayout()
        widgets = [replace_with, self.replace_text, self.replace_button,
                   self.all_check]
        for widget in widgets:
            self.replace_layout.addWidget(widget)
        glayout.addLayout(self.replace_layout, 1, 1)
        self.widgets.extend(widgets)
        self.replace_widgets = widgets
        self.hide_replace()
        
        self.search_text.setTabOrder(self.search_text, self.replace_text)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.findnext_sc = QShortcut(QKeySequence("F3"), parent, self.find_next)
        self.findnext_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.findprev_sc = QShortcut(QKeySequence("Shift+F3"), parent,
                                     self.find_previous)
        self.findprev_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.togglefind_sc = QShortcut(QKeySequence("Ctrl+F"), parent,
                                       self.show)
        self.togglefind_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.togglereplace_sc = QShortcut(QKeySequence("Ctrl+H"), parent,
                                          self.toggle_replace_widgets)
        self.togglereplace_sc.setContext(Qt.WidgetWithChildrenShortcut)
        
        escape_sc = QShortcut(QKeySequence("Escape"), parent, self.hide)
        escape_sc.setContext(Qt.WidgetWithChildrenShortcut)
        
    def update_search_combo(self):
        self.search_text.lineEdit().emit(SIGNAL('returnPressed()'))
        
    def update_replace_combo(self):
        self.replace_text.lineEdit().emit(SIGNAL('returnPressed()'))
    
    def toggle_replace_widgets(self):
        if self.enable_replace:
            # Toggle replace widgets
            if self.replace_widgets[0].isVisible():
                self.hide_replace()
                self.hide()
            else:
                self.show_replace()
                self.replace_text.setFocus()
        
    def show(self):
        """Overrides Qt Method"""
        QWidget.show(self)
        self.emit(SIGNAL("visibility_changed(bool)"), True)
        if self.editor is not None:
            text = self.editor.get_selected_text()
            if len(text) > 0:
                self.search_text.setEditText(text)
                self.search_text.lineEdit().selectAll()
                self.refresh()
            else:
                self.search_text.lineEdit().selectAll()
            self.search_text.setFocus()
        
    def hide(self):
        """Overrides Qt Method"""
        for widget in self.replace_widgets:
            widget.hide()
        QWidget.hide(self)
        self.emit(SIGNAL("visibility_changed(bool)"), False)
        if self.editor is not None:
            self.editor.setFocus()
        
    def show_replace(self):
        """Show replace widgets"""
        for widget in self.replace_widgets:
            widget.show()
            
    def hide_replace(self):
        """Hide replace widgets"""
        for widget in self.replace_widgets:
            widget.hide()
        
    def refresh(self):
        """Refresh widget"""
        if self.isHidden():
            return
        state = self.editor is not None
        for widget in self.widgets:
            widget.setEnabled(state)
        if state:
            self.find()
            
    def set_editor(self, editor, refresh=True):
        """
        Set associated editor/web page:
            codeeditor.base.TextEditBaseWidget
            browser.WebView
        """
        self.editor = editor
        from PyQt4.QtWebKit import QWebView
        self.words_check.setVisible(not isinstance(editor, QWebView))
        if refresh:
            self.refresh()
        
    def find_next(self):
        """Find next occurence"""
        state = self.find(changed=False, forward=True)
        self.editor.setFocus()
        return state
        
    def find_previous(self):
        """Find previous occurence"""
        state = self.find(changed=False, forward=False)
        self.editor.setFocus()
        return state
        
    def text_has_changed(self, text):
        """Find text has changed"""
        self.find(changed=True, forward=True)
        
    def find(self, changed=True, forward=True):
        """Call the find function"""
        text = self.search_text.currentText()
        if len(text) == 0:
            self.search_text.lineEdit().setStyleSheet("")
            return None
        else:
            found = self.editor.find_text(text, changed, forward,
                                          case=self.case_check.isChecked(),
                                          words=self.words_check.isChecked())
            self.search_text.lineEdit().setStyleSheet(self.STYLE[found])
            return found
            
    def replace_find(self):
        """Replace and find"""
        if (self.editor is not None):
            replace_text = self.replace_text.currentText()
            search_text = self.search_text.currentText()
            first = True
            while True:
                if first:
                    # First found
                    if self.editor.has_selected_text() and \
                       self.editor.get_selected_text() == unicode(search_text):
                        # Text was already found, do nothing
                        pass
                    else:
                        if not self.find(changed=False, forward=True):
                            break
                    first = False
                    wrapped = False
                    position = self.editor.get_position('cursor')
                    position0 = position
                else:
                    position1 = self.editor.get_position('cursor')
                    if wrapped:
                        if position1 == position or \
                           self.editor.is_position_sup(position1, position):
                            # Avoid infinite loop: replace string includes
                            # part of the search string
                            break
                    if position1 == position0:
                        # Avoid infinite loop: single found occurence
                        break
                    if self.editor.is_position_inf(position1, position0):
                        wrapped = True
                    position0 = position1
                
                self.editor.replace(replace_text)
                if not self.find_next():
                    break
                if not self.all_check.isChecked():
                    break
            self.all_check.setCheckState(Qt.Unchecked)
            
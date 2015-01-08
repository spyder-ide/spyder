# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Find/Replace widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QHBoxLayout, QGridLayout, QCheckBox, QLabel,
                                QWidget, QSizePolicy, QTextCursor)
from spyderlib.qt.QtCore import SIGNAL, Qt, QTimer

import re

# Local imports
from spyderlib.baseconfig import _
from spyderlib.guiconfig import create_shortcut, new_shortcut
from spyderlib.utils.qthelpers import (get_icon, get_std_icon,
                                       create_toolbutton)
from spyderlib.widgets.comboboxes import PatternComboBox
from spyderlib.py3compat import to_text_string


def is_position_sup(pos1, pos2):
    """Return True is pos1 > pos2"""
    return pos1 > pos2
    
def is_position_inf(pos1, pos2):
    """Return True is pos1 < pos2"""
    return pos1 < pos2


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
        self.is_code_editor = None
        
        glayout = QGridLayout()
        glayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(glayout)
        
        self.close_button = create_toolbutton(self, triggered=self.hide,
                                      icon=get_std_icon("DialogCloseButton"))
        glayout.addWidget(self.close_button, 0, 0)
        
        # Find layout
        self.search_text = PatternComboBox(self, tip=_("Search string"),
                                           adjust_to_minimum=False)
        self.connect(self.search_text, SIGNAL('valid(bool)'),
                     lambda state:
                     self.find(changed=False, forward=True, rehighlight=False))
        self.connect(self.search_text.lineEdit(),
                     SIGNAL("textEdited(QString)"), self.text_has_been_edited)
        
        self.previous_button = create_toolbutton(self,
                                             triggered=self.find_previous,
                                             icon=get_std_icon("ArrowBack"))
        self.next_button = create_toolbutton(self,
                                             triggered=self.find_next,
                                             icon=get_std_icon("ArrowForward"))
        self.connect(self.next_button, SIGNAL('clicked()'),
                     self.update_search_combo)
        self.connect(self.previous_button, SIGNAL('clicked()'),
                     self.update_search_combo)

        self.re_button = create_toolbutton(self, icon=get_icon("advanced.png"),
                                           tip=_("Regular expression"))
        self.re_button.setCheckable(True)
        self.connect(self.re_button, SIGNAL("toggled(bool)"),
                     lambda state: self.find())
        
        self.case_button = create_toolbutton(self,
                                             icon=get_icon("upper_lower.png"),
                                             tip=_("Case Sensitive"))
        self.case_button.setCheckable(True)
        self.connect(self.case_button, SIGNAL("toggled(bool)"),
                     lambda state: self.find())
                     
        self.words_button = create_toolbutton(self,
                                              icon=get_icon("whole_words.png"),
                                              tip=_("Whole words"))
        self.words_button.setCheckable(True)
        self.connect(self.words_button, SIGNAL("toggled(bool)"),
                     lambda state: self.find())
                     
        self.highlight_button = create_toolbutton(self,
                                              icon=get_icon("highlight.png"),
                                              tip=_("Highlight matches"))
        self.highlight_button.setCheckable(True)
        self.connect(self.highlight_button, SIGNAL("toggled(bool)"),
                     self.toggle_highlighting)

        hlayout = QHBoxLayout()
        self.widgets = [self.close_button, self.search_text,
                        self.previous_button, self.next_button,
                        self.re_button, self.case_button, self.words_button,
                        self.highlight_button]
        for widget in self.widgets[1:]:
            hlayout.addWidget(widget)
        glayout.addLayout(hlayout, 0, 1)

        # Replace layout
        replace_with = QLabel(_("Replace with:"))
        self.replace_text = PatternComboBox(self, adjust_to_minimum=False,
                                            tip=_("Replace string"))
        
        self.replace_button = create_toolbutton(self,
                                     text=_("Replace/find"),
                                     icon=get_std_icon("DialogApplyButton"),
                                     triggered=self.replace_find,
                                     text_beside_icon=True)
        self.connect(self.replace_button, SIGNAL('clicked()'),
                     self.update_replace_combo)
        self.connect(self.replace_button, SIGNAL('clicked()'),
                     self.update_search_combo)
        
        self.all_check = QCheckBox(_("Replace all"))
        
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
        
        self.shortcuts = self.create_shortcuts(parent)
        
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setSingleShot(True)
        self.highlight_timer.setInterval(1000)
        self.connect(self.highlight_timer, SIGNAL("timeout()"),
                     self.highlight_matches)
        
    def create_shortcuts(self, parent):
        """Create shortcuts for this widget"""
        # Configurable
        findnext = create_shortcut(self.find_next, context='Editor',
                                   name='Find next', parent=parent)
        findprev = create_shortcut(self.find_previous, context='Editor',
                                   name='Find previous', parent=parent)
        togglefind = create_shortcut(self.show, context='Editor',
                                     name='Find text', parent=parent)
        togglereplace = create_shortcut(self.toggle_replace_widgets,
                                        context='Editor', name='Replace text',
                                        parent=parent)
        # Fixed
        new_shortcut("Escape", self, self.hide)

        return [findnext, findprev, togglefind, togglereplace]
        
    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]
        
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
                
    def toggle_highlighting(self, state):
        """Toggle the 'highlight all results' feature"""
        if self.editor is not None:
            if state:
                self.highlight_matches()
            else:
                self.clear_matches()
        
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
            self.clear_matches()
        
    def show_replace(self):
        """Show replace widgets"""
        self.show()
        for widget in self.replace_widgets:
            widget.show()
            
    def hide_replace(self):
        """Hide replace widgets"""
        for widget in self.replace_widgets:
            widget.hide()
        
    def refresh(self):
        """Refresh widget"""
        if self.isHidden():
            if self.editor is not None:
                self.clear_matches()
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
        from spyderlib.qt.QtWebKit import QWebView
        self.words_button.setVisible(not isinstance(editor, QWebView))
        self.re_button.setVisible(not isinstance(editor, QWebView))
        from spyderlib.widgets.sourcecode.codeeditor import CodeEditor
        self.is_code_editor = isinstance(editor, CodeEditor)
        self.highlight_button.setVisible(self.is_code_editor)
        if refresh:
            self.refresh()
        if self.isHidden() and editor is not None:
            self.clear_matches()
        
    def find_next(self):
        """Find next occurence"""
        state = self.find(changed=False, forward=True, rehighlight=False)
        self.editor.setFocus()
        self.search_text.add_current_text()
        return state
        
    def find_previous(self):
        """Find previous occurence"""
        state = self.find(changed=False, forward=False, rehighlight=False)
        self.editor.setFocus()
        return state

    def text_has_been_edited(self, text):
        """Find text has been edited (this slot won't be triggered when 
        setting the search pattern combo box text programmatically"""
        self.find(changed=True, forward=True, start_highlight_timer=True)
        
    def highlight_matches(self):
        """Highlight found results"""
        if self.is_code_editor and self.highlight_button.isChecked():
            text = self.search_text.currentText()
            words = self.words_button.isChecked()
            regexp = self.re_button.isChecked()
            self.editor.highlight_found_results(text, words=words,
                                                regexp=regexp)
                                                
    def clear_matches(self):
        """Clear all highlighted matches"""
        if self.is_code_editor:
            self.editor.clear_found_results()
        
    def find(self, changed=True, forward=True,
             rehighlight=True, start_highlight_timer=False):
        """Call the find function"""
        text = self.search_text.currentText()
        if len(text) == 0:
            self.search_text.lineEdit().setStyleSheet("")
            return None
        else:
            case = self.case_button.isChecked()
            words = self.words_button.isChecked()
            regexp = self.re_button.isChecked()
            found = self.editor.find_text(text, changed, forward, case=case,
                                          words=words, regexp=regexp)
            self.search_text.lineEdit().setStyleSheet(self.STYLE[found])
            if self.is_code_editor and found:
                if rehighlight or not self.editor.found_results:
                    self.highlight_timer.stop()
                    if start_highlight_timer:
                        self.highlight_timer.start()
                    else:
                        self.highlight_matches()
            else:
                self.clear_matches()
            return found
            
    def replace_find(self):
        """Replace and find"""
        if (self.editor is not None):
            replace_text = to_text_string(self.replace_text.currentText())
            search_text = to_text_string(self.search_text.currentText())
            pattern = search_text if self.re_button.isChecked() else None
            case = self.case_button.isChecked()
            first = True
            cursor = None
            while True:
                if first:
                    # First found
                    seltxt = to_text_string(self.editor.get_selected_text())
                    cmptxt1 = search_text if case else search_text.lower()
                    cmptxt2 = seltxt if case else seltxt.lower()
                    if self.editor.has_selected_text() and cmptxt1 == cmptxt2:
                        # Text was already found, do nothing
                        pass
                    else:
                        if not self.find(changed=False, forward=True,
                                         rehighlight=False):
                            break
                    first = False
                    wrapped = False
                    position = self.editor.get_position('cursor')
                    position0 = position
                    cursor = self.editor.textCursor()
                    cursor.beginEditBlock()
                else:
                    position1 = self.editor.get_position('cursor')
                    if is_position_inf(position1,
                                       position0 + len(replace_text) -
                                       len(search_text) + 1):
                        # Identify wrapping even when the replace string
                        # includes part of the search string
                        wrapped = True
                    if wrapped:
                        if position1 == position or \
                           is_position_sup(position1, position):
                            # Avoid infinite loop: replace string includes
                            # part of the search string
                            break
                    if position1 == position0:
                        # Avoid infinite loop: single found occurence
                        break
                    position0 = position1
                if pattern is None:
                    cursor.removeSelectedText()
                    cursor.insertText(replace_text)
                else:
                    seltxt = to_text_string(cursor.selectedText())
                    cursor.removeSelectedText()
                    cursor.insertText(re.sub(pattern, replace_text, seltxt))
                if self.find_next():
                    found_cursor = self.editor.textCursor()
                    cursor.setPosition(found_cursor.selectionStart(),
                                       QTextCursor.MoveAnchor)
                    cursor.setPosition(found_cursor.selectionEnd(),
                                       QTextCursor.KeepAnchor)
                else:
                    break
                if not self.all_check.isChecked():
                    break
            self.all_check.setCheckState(Qt.Unchecked)
            if cursor is not None:
                cursor.endEditBlock()

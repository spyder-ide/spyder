# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Find/Replace widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import re

# Third party imports
from qtpy.QtCore import Qt, QTimer, Signal, Slot, QEvent
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (QGridLayout, QHBoxLayout, QLabel,
                            QSizePolicy, QWidget)

# Local imports
from spyder.config.base import _
from spyder.config.gui import config_shortcut
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_toolbutton, get_icon
from spyder.widgets.comboboxes import PatternComboBox


CONTROL_CHARACTERS = {
    '\\n': '\n',
    '\\r': '\r',
    '\\t': '\t',
    '\\f': '\f'
}


def is_position_sup(pos1, pos2):
    """Return True is pos1 > pos2"""
    return pos1 > pos2
    
def is_position_inf(pos1, pos2):
    """Return True is pos1 < pos2"""
    return pos1 < pos2


class FindReplace(QWidget):
    """Find widget"""
    STYLE = {False: "background-color:rgb(255, 175, 90);",
             True: "",
             None: "",
             'regexp_error': "background-color:rgb(255, 80, 80);",
             }
    TOOLTIP = {False: _("No matches"),
               True: _("Search string"),
               None: _("Search string"),
               'regexp_error': _("Regular expression error")
               }
    visibility_changed = Signal(bool)
    return_shift_pressed = Signal()
    return_pressed = Signal()

    def __init__(self, parent, enable_replace=False):
        QWidget.__init__(self, parent)
        self.enable_replace = enable_replace
        self.editor = None
        self.is_code_editor = None
        
        glayout = QGridLayout()
        glayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(glayout)
        
        self.close_button = create_toolbutton(self, triggered=self.hide,
                                      icon=ima.icon('DialogCloseButton'))
        glayout.addWidget(self.close_button, 0, 0)
        
        # Find layout
        self.search_text = PatternComboBox(self, tip=_("Search string"),
                                           adjust_to_minimum=False)

        self.return_shift_pressed.connect(
                lambda:
                self.find(changed=False, forward=False, rehighlight=False, 
                          multiline_replace_check = False))

        self.return_pressed.connect(
                     lambda:
                     self.find(changed=False, forward=True, rehighlight=False,
                               multiline_replace_check = False))

        self.search_text.lineEdit().textEdited.connect(
                                                     self.text_has_been_edited)

        self.number_matches_text = QLabel(self)
        self.previous_button = create_toolbutton(self,
                                             triggered=self.find_previous,
                                             icon=ima.icon('ArrowUp'))
        self.next_button = create_toolbutton(self,
                                             triggered=self.find_next,
                                             icon=ima.icon('ArrowDown'))
        self.next_button.clicked.connect(self.update_search_combo)
        self.previous_button.clicked.connect(self.update_search_combo)

        self.re_button = create_toolbutton(self, icon=ima.icon('advanced'),
                                           tip=_("Regular expression"))
        self.re_button.setCheckable(True)
        self.re_button.toggled.connect(lambda state: self.find())
        
        self.case_button = create_toolbutton(self,
                                             icon=get_icon("upper_lower.png"),
                                             tip=_("Case Sensitive"))
        self.case_button.setCheckable(True)
        self.case_button.toggled.connect(lambda state: self.find())
                     
        self.words_button = create_toolbutton(self,
                                              icon=get_icon("whole_words.png"),
                                              tip=_("Whole words"))
        self.words_button.setCheckable(True)
        self.words_button.toggled.connect(lambda state: self.find())
                     
        self.highlight_button = create_toolbutton(self,
                                              icon=get_icon("highlight.png"),
                                              tip=_("Highlight matches"))
        self.highlight_button.setCheckable(True)
        self.highlight_button.toggled.connect(self.toggle_highlighting)

        hlayout = QHBoxLayout()
        self.widgets = [self.close_button, self.search_text,
                        self.number_matches_text, self.previous_button,
                        self.next_button, self.re_button, self.case_button,
                        self.words_button, self.highlight_button]
        for widget in self.widgets[1:]:
            hlayout.addWidget(widget)
        glayout.addLayout(hlayout, 0, 1)

        # Replace layout
        replace_with = QLabel(_("Replace with:"))
        self.replace_text = PatternComboBox(self, adjust_to_minimum=False,
                                            tip=_('Replace string'))
        self.replace_text.valid.connect(
                    lambda _: self.replace_find(focus_replace_text=True))
        self.replace_button = create_toolbutton(self,
                                     text=_('Replace/find next'),
                                     icon=ima.icon('DialogApplyButton'),
                                     triggered=self.replace_find,
                                     text_beside_icon=True)
        self.replace_sel_button = create_toolbutton(self,
                                     text=_('Replace selection'),
                                     icon=ima.icon('DialogApplyButton'),
                                     triggered=self.replace_find_selection,
                                     text_beside_icon=True)
        self.replace_sel_button.clicked.connect(self.update_replace_combo)
        self.replace_sel_button.clicked.connect(self.update_search_combo)

        self.replace_all_button = create_toolbutton(self,
                                     text=_('Replace all'),
                                     icon=ima.icon('DialogApplyButton'),
                                     triggered=self.replace_find_all,
                                     text_beside_icon=True)
        self.replace_all_button.clicked.connect(self.update_replace_combo)
        self.replace_all_button.clicked.connect(self.update_search_combo)
        
        self.replace_layout = QHBoxLayout()
        widgets = [replace_with, self.replace_text, self.replace_button,
                   self.replace_sel_button, self.replace_all_button]
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
        self.highlight_timer.timeout.connect(self.highlight_matches)
        self.search_text.installEventFilter(self)


    def eventFilter(self, widget, event):
        """Event filter for search_text widget.

        Emits signals when presing Enter and Shift+Enter.
        This signals are used for search forward and backward.
        """
        if (event.type() == QEvent.KeyPress):
            key = event.key()
            shift = event.modifiers() & Qt.ShiftModifier

            if key == Qt.Key_Return:
                if shift:
                    self.return_shift_pressed.emit()
                else:
                    self.return_pressed.emit()

        return super(FindReplace, self).eventFilter(widget, event)


    def create_shortcuts(self, parent):
        """Create shortcuts for this widget"""
        # Configurable
        findnext = config_shortcut(self.find_next, context='_',
                                   name='Find next', parent=parent)
        findprev = config_shortcut(self.find_previous, context='_',
                                   name='Find previous', parent=parent)
        togglefind = config_shortcut(self.show, context='_',
                                     name='Find text', parent=parent)
        togglereplace = config_shortcut(self.show_replace,
                                        context='_', name='Replace text',
                                        parent=parent)
        hide = config_shortcut(self.hide, context='_', name='hide find and replace',
                               parent=self)

        return [findnext, findprev, togglefind, togglereplace, hide]

    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]
        
    def update_search_combo(self):
        self.search_text.lineEdit().returnPressed.emit()
        
    def update_replace_combo(self):
        self.replace_text.lineEdit().returnPressed.emit()
    
    def toggle_replace_widgets(self):
        if self.enable_replace:
            # Toggle replace widgets
            if self.replace_widgets[0].isVisible():
                self.hide_replace()
                self.hide()
            else:
                self.show_replace()
                if len(to_text_string(self.search_text.currentText()))>0:
                    self.replace_text.setFocus()

    @Slot(bool)
    def toggle_highlighting(self, state):
        """Toggle the 'highlight all results' feature"""
        if self.editor is not None:
            if state:
                self.highlight_matches()
            else:
                self.clear_matches()
        
    def show(self, hide_replace=True):
        """Overrides Qt Method"""
        QWidget.show(self)
        self.visibility_changed.emit(True)
        self.change_number_matches()
        if self.editor is not None:
            if hide_replace:
                if self.replace_widgets[0].isVisible():
                    self.hide_replace()
            text = self.editor.get_selected_text()
            # When selecting several lines, and replace box is activated the
            # text won't be replaced for the selection
            if hide_replace or len(text.splitlines())<=1:
                highlighted = True
                # If no text is highlighted for search, use whatever word is
                # under the cursor
                if not text:
                    highlighted = False
                    try:
                        cursor = self.editor.textCursor()
                        cursor.select(QTextCursor.WordUnderCursor)
                        text = to_text_string(cursor.selectedText())
                    except AttributeError:
                        # We can't do this for all widgets, e.g. WebView's
                        pass
    
                # Now that text value is sorted out, use it for the search
                if text and not self.search_text.currentText() or highlighted:
                    self.search_text.setEditText(text)
                    self.search_text.lineEdit().selectAll()
                    self.refresh()
                else:
                    self.search_text.lineEdit().selectAll()
            self.search_text.setFocus()

    @Slot()
    def hide(self):
        """Overrides Qt Method"""
        for widget in self.replace_widgets:
            widget.hide()
        QWidget.hide(self)
        self.visibility_changed.emit(False)
        if self.editor is not None:
            self.editor.setFocus()
            self.clear_matches()
        
    def show_replace(self):
        """Show replace widgets"""
        self.show(hide_replace=False)
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
        # Note: This is necessary to test widgets/editor.py
        # in Qt builds that don't have web widgets
        try:
            from qtpy.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QWebEngineView = type(None)
        self.words_button.setVisible(not isinstance(editor, QWebEngineView))
        self.re_button.setVisible(not isinstance(editor, QWebEngineView))
        from spyder.widgets.sourcecode.codeeditor import CodeEditor
        self.is_code_editor = isinstance(editor, CodeEditor)
        self.highlight_button.setVisible(self.is_code_editor)
        if refresh:
            self.refresh()
        if self.isHidden() and editor is not None:
            self.clear_matches()

    @Slot()
    def find_next(self):
        """Find next occurrence"""
        state = self.find(changed=False, forward=True, rehighlight=False,
                          multiline_replace_check=False)
        self.editor.setFocus()
        self.search_text.add_current_text()
        return state

    @Slot()
    def find_previous(self):
        """Find previous occurrence"""
        state = self.find(changed=False, forward=False, rehighlight=False,
                          multiline_replace_check=False)
        self.editor.setFocus()
        return state

    def text_has_been_edited(self, text):
        """Find text has been edited (this slot won't be triggered when 
        setting the search pattern combo box text programmatically)"""
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
             rehighlight=True, start_highlight_timer=False, multiline_replace_check=True):
        """Call the find function"""
        # When several lines are selected in the editor and replace box is activated, 
        # dynamic search is deactivated to prevent changing the selection. Otherwise
        # we show matching items.
        def regexp_error_msg(pattern):
            """Returns None if the pattern is a valid regular expression or
            a string describing why the pattern is invalid.
            """
            try:
                re.compile(pattern)
            except re.error as e:
                return str(e)
            return None

        if multiline_replace_check and self.replace_widgets[0].isVisible() and \
           len(to_text_string(self.editor.get_selected_text()).splitlines())>1:
            return None
        text = self.search_text.currentText()
        if len(text) == 0:
            self.search_text.lineEdit().setStyleSheet("")
            if not self.is_code_editor:
                # Clears the selection for WebEngine
                self.editor.find_text('')
            self.change_number_matches()
            return None
        else:
            case = self.case_button.isChecked()
            words = self.words_button.isChecked()
            regexp = self.re_button.isChecked()
            found = self.editor.find_text(text, changed, forward, case=case,
                                          words=words, regexp=regexp)

            stylesheet = self.STYLE[found]
            tooltip = self.TOOLTIP[found]
            if not found and regexp:
                error_msg = regexp_error_msg(text)
                if error_msg:  # special styling for regexp errors
                    stylesheet = self.STYLE['regexp_error']
                    tooltip = self.TOOLTIP['regexp_error'] + ': ' + error_msg
            self.search_text.lineEdit().setStyleSheet(stylesheet)
            self.search_text.setToolTip(tooltip)

            if self.is_code_editor and found:
                if rehighlight or not self.editor.found_results:
                    self.highlight_timer.stop()
                    if start_highlight_timer:
                        self.highlight_timer.start()
                    else:
                        self.highlight_matches()
            else:
                self.clear_matches()

            number_matches = self.editor.get_number_matches(text, case=case)
            if hasattr(self.editor, 'get_match_number'):
                match_number = self.editor.get_match_number(text, case=case)
            else:
                match_number = 0
            self.change_number_matches(current_match=match_number,
                                       total_matches=number_matches)
            return found

    @Slot()
    def replace_find(self, focus_replace_text=False, replace_all=False):
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
                    if not pattern:
                        has_selected = self.editor.has_selected_text()
                        if has_selected and cmptxt1 == cmptxt2:
                            # Text was already found, do nothing
                            pass
                        else:
                            if not self.find(changed=False, forward=True,
                                             rehighlight=False):
                                break
                    else:
                        if len(re.findall(pattern, cmptxt2)) > 0:
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
                        # Avoid infinite loop: single found occurrence
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
                if not replace_all:
                    break
            if cursor is not None:
                cursor.endEditBlock()
            if focus_replace_text:
                self.replace_text.setFocus()

    @Slot()
    def replace_find_all(self, focus_replace_text=False):
        """Replace and find all matching occurrences"""
        self.replace_find(focus_replace_text, replace_all=True)

                
    @Slot()
    def replace_find_selection(self, focus_replace_text=False):
        """Replace and find in the current selection"""
        if (self.editor is not None):
            replace_text = to_text_string(self.replace_text.currentText())
            search_text = to_text_string(self.search_text.currentText())
            pattern = search_text if self.re_button.isChecked() else None
            case = self.case_button.isChecked()
            words = self.words_button.isChecked()
            re_flags = re.MULTILINE if case else re.IGNORECASE|re.MULTILINE

            cursor = self.editor.textCursor()
            cursor.beginEditBlock()
            seltxt = to_text_string(self.editor.get_selected_text())
            if not pattern:
                pattern = re.escape(search_text)
                replace_text = re.escape(replace_text)
            if words:
                #If whole words is checked we need to check that each match
                #is actually a whole word before replacing
                try:
                    re.compile(pattern)
                except re.error:
                    return #if the pattern won't compile cancel the find/replace
                word_pattern = r'\b{pattern}\b'.format(pattern = pattern)
                replacement = re.sub(word_pattern, replace_text, seltxt, flags=re_flags)
            else:
                replacement = re.sub(pattern, replace_text, seltxt, flags=re_flags)
            if replacement != seltxt:
                cursor.removeSelectedText()
                for plain_char in CONTROL_CHARACTERS:
                    replacement = replacement.replace(
                        plain_char, CONTROL_CHARACTERS[plain_char])
                replacement = re.sub(r'\\(.)', r'\1', replacement)
                cursor.insertText(replacement)
            cursor.endEditBlock()
            if focus_replace_text:
                self.replace_text.setFocus()
            else:
                self.editor.setFocus()

    def change_number_matches(self, current_match=0, total_matches=0):
        """Change number of match and total matches."""
        if current_match and total_matches:
            matches_string = "{} {} {}".format(current_match, _("of"),
                                               total_matches)
            self.number_matches_text.setText(matches_string)
        elif total_matches:
            matches_string = "{} {}".format(total_matches, _("matches"))
            self.number_matches_text.setText(matches_string)
        else:
            self.number_matches_text.setText(_("no matches"))

# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""QPlainTextEdit base class"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

import re
import sre_constants
import string
import os

from spyderlib.qt.QtGui import (QTextCursor, QColor, QFont, QApplication,
                                QTextEdit, QTextCharFormat, QToolTip,
                                QTextDocument, QListWidget, QPlainTextEdit,
                                QPalette, QMainWindow, QTextOption)
from spyderlib.qt.QtCore import QPoint, SIGNAL, Qt, QRegExp, QEventLoop


# Local imports
from spyderlib.widgets.sourcecode.terminal import ANSIEscapeCodeHandler
from spyderlib.utils import sourcecode


class CompletionWidget(QListWidget):
    """Completion list widget"""
    def __init__(self, parent, ancestor):
        QListWidget.__init__(self, ancestor)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.textedit = parent
        self.completion_list = None
        self.case_sensitive = False
        self.show_single = None
        self.enter_select = None
        self.hide()
        self.connect(self, SIGNAL("itemActivated(QListWidgetItem*)"),
                     self.item_selected)
        
    def setup_appearance(self, size, font):
        self.resize(*size)
        self.setFont(font)
        
    def show_list(self, completion_list, automatic=True):
        if not self.show_single and len(completion_list) == 1 and not automatic:
            self.textedit.insert_completion(completion_list[0])
            return
        
        self.completion_list = completion_list
        self.clear()
        self.addItems(completion_list)
        self.setCurrentRow(0)
        
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        self.show()
        self.setFocus()
        self.raise_()
        
        # Retrieving current screen height
        desktop = QApplication.desktop()
        srect = desktop.availableGeometry(desktop.screenNumber(self))
        screen_right = srect.right()
        screen_bottom = srect.bottom()
        
        point = self.textedit.cursorRect().bottomRight()
        point.setX(point.x()+self.textedit.get_linenumberarea_width())
        point = self.textedit.mapToGlobal(point)

        # Computing completion widget and its parent right positions
        comp_right = point.x()+self.width()
        ancestor = self.parent()
        if ancestor is None:
            anc_right = screen_right
        else:
            anc_right = min([ancestor.x()+ancestor.width(), screen_right])
        
        # Moving completion widget to the left
        # if there is not enough space to the right
        if comp_right > anc_right:
            point.setX(point.x()-self.width())
        
        # Computing completion widget and its parent bottom positions
        comp_bottom = point.y()+self.height()
        ancestor = self.parent()
        if ancestor is None:
            anc_bottom = screen_bottom
        else:
            anc_bottom = min([ancestor.y()+ancestor.height(), screen_bottom])
        
        # Moving completion widget above if there is not enough space below
        x_position = point.x()
        if comp_bottom > anc_bottom:
            point = self.textedit.cursorRect().topRight()
            point = self.textedit.mapToGlobal(point)
            point.setX(x_position)
            point.setY(point.y()-self.height())
            
        if ancestor is not None:
            # Useful only if we set parent to 'ancestor' in __init__
            point = ancestor.mapFromGlobal(point)
        self.move(point)
        
        if unicode(self.textedit.completion_text):
            # When initialized, if completion text is not empty, we need 
            # to update the displayed list:
            self.update_current()
        
    def hide(self):
        QListWidget.hide(self)
        self.textedit.setFocus()
        
    def keyPressEvent(self, event):
        text, key = event.text(), event.key()
        alt = event.modifiers() & Qt.AltModifier
        shift = event.modifiers() & Qt.ShiftModifier
        ctrl = event.modifiers() & Qt.ControlModifier
        modifier = shift or ctrl or alt
        if (key in (Qt.Key_Return, Qt.Key_Enter) and self.enter_select) \
           or key == Qt.Key_Tab:
            self.item_selected()
        elif key in (Qt.Key_Return, Qt.Key_Enter,
                     Qt.Key_Left, Qt.Key_Right) or text in ('.', ':'):
            self.hide()
            self.textedit.keyPressEvent(event)
        elif key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown,
                     Qt.Key_Home, Qt.Key_End,
                     Qt.Key_CapsLock) and not modifier:
            QListWidget.keyPressEvent(self, event)
        elif len(text) or key == Qt.Key_Backspace:
            self.textedit.keyPressEvent(event)
            self.update_current()
        elif modifier:
            self.textedit.keyPressEvent(event)
        else:
            self.hide()
            QListWidget.keyPressEvent(self, event)
            
    def update_current(self):
        completion_text = unicode(self.textedit.completion_text)
        if completion_text:
            for row, completion in enumerate(self.completion_list):
                if not self.case_sensitive:
                    completion = completion.lower()
                    completion_text = completion_text.lower()
                if completion.startswith(completion_text):
                    self.setCurrentRow(row)
                    break
            else:
                self.hide()
        else:
            self.hide()
    
    def focusOutEvent(self, event):
        event.ignore()
        self.hide()
        
    def item_selected(self, item=None):
        if item is None:
            item = self.currentItem()
        self.textedit.insert_completion( unicode(item.text()) )
        self.hide()


class TextEditBaseWidget(QPlainTextEdit):
    """
    Text edit base widget
    """
    BRACE_MATCHING_SCOPE = ('sof', 'eof')
    
    def __init__(self, parent=None):
        QPlainTextEdit.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.extra_selections_dict = {}
        
        self.connect(self, SIGNAL('textChanged()'), self.changed)
        self.connect(self, SIGNAL('cursorPositionChanged()'),
                     self.cursor_position_changed)

        self.eol_chars = None
        
        self.indent_chars = " "*4
        
        # Code completion / calltips
        if parent is not None:
            mainwin = parent
            while not isinstance(mainwin, QMainWindow):
                mainwin = mainwin.parent()
                if mainwin is None:
                    break
            if mainwin is not None:
                parent = mainwin
        self.completion_widget = CompletionWidget(self, parent)
        self.codecompletion_auto = False
        self.codecompletion_case = True
        self.codecompletion_single = False
        self.codecompletion_enter = False
        self.calltips = True
        self.calltip_position = None
        self.calltip_size = 600
        self.calltip_font = QFont()
        self.completion_text = ""

        # Brace matching
        self.bracepos = None
        self.matched_p_color = QColor(Qt.green)
        self.unmatched_p_color = QColor(Qt.red)
        
    def setup_calltips(self, size=None, font=None):
        self.calltip_size = size
        self.calltip_font = font
    
    def setup_completion(self, size=None, font=None):
        self.completion_widget.setup_appearance(size, font)
        
    def set_indent_chars(self, indent_chars):
        self.indent_chars = indent_chars
        
    def set_palette(self, background, foreground):
        """
        Set text editor palette colors:
        background color and caret (text cursor) color
        """
        palette = QPalette()
        palette.setColor(QPalette.Base, background)
        palette.setColor(QPalette.Text, foreground)
        self.setPalette(palette)
        
    #------Line number area
    def get_linenumberarea_width(self):
        """Return line number area width"""
        # Implemented in CodeEditor, but needed here for completion widget
        return 0
        
    #------Extra selections
    def get_extra_selections(self, key):
        return self.extra_selections_dict.get(key, [])

    def set_extra_selections(self, key, extra_selections):
        self.extra_selections_dict[key] = extra_selections
        
    def update_extra_selections(self):
        extra_selections = []
        for _key, extra in self.extra_selections_dict.iteritems():
            extra_selections.extend(extra)
        self.setExtraSelections(extra_selections)
        
    def clear_extra_selections(self, key):
        self.extra_selections_dict[key] = []
        self.update_extra_selections()
        
        
    def changed(self):
        """Emit changed signal"""
        self.emit(SIGNAL('modificationChanged(bool)'),
                  self.document().isModified())


    #------Brace matching
    def find_brace_match(self, position, brace, forward):
        start_pos, end_pos = self.BRACE_MATCHING_SCOPE
        if forward:
            bracemap = {'(': ')', '[': ']', '{': '}'}
            text = self.get_text(position, end_pos)
            i_start_open = 1
            i_start_close = 1
        else:
            bracemap = {')': '(', ']': '[', '}': '{'}
            text = self.get_text(start_pos, position)
            i_start_open = len(text)-1
            i_start_close = len(text)-1

        while True:
            if forward:
                i_close = text.find(bracemap[brace], i_start_close)
            else:
                i_close = text.rfind(bracemap[brace], 0, i_start_close+1)
            if i_close > -1:
                if forward:
                    i_start_close = i_close+1
                    i_open = text.find(brace, i_start_open, i_close)
                else:
                    i_start_close = i_close-1
                    i_open = text.rfind(brace, i_close, i_start_open+1)
                if i_open > -1:
                    if forward:
                        i_start_open = i_open+1
                    else:
                        i_start_open = i_open-1
                else:
                    # found matching brace
                    if forward:
                        return position+i_close
                    else:
                        return position-(len(text)-i_close)
            else:
                # no matching brace
                return
    
    def __highlight(self, positions, color=None, cancel=False):
        if cancel:
            self.clear_extra_selections('brace_matching')
            return
        extra_selections = []
        for position in positions:
            if position > self.get_position('eof'):
                return
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(color)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selection.cursor.setPosition(position)
            selection.cursor.movePosition(QTextCursor.NextCharacter,
                                          QTextCursor.KeepAnchor)
            extra_selections.append(selection)
        self.set_extra_selections('brace_matching', extra_selections)
        self.update_extra_selections()

    def cursor_position_changed(self):
        """Brace matching"""
        if self.bracepos is not None:
            self.__highlight(self.bracepos, cancel=True)
            self.bracepos = None
        cursor = self.textCursor()
        if cursor.position() == 0:
            return
        cursor.movePosition(QTextCursor.PreviousCharacter,
                            QTextCursor.KeepAnchor)
        text = unicode(cursor.selectedText())
        pos1 = cursor.position()
        if text in (')', ']', '}'):
            pos2 = self.find_brace_match(pos1, text, forward=False)
        elif text in ('(', '[', '{'):
            pos2 = self.find_brace_match(pos1, text, forward=True)
        else:
            return
        if pos2 is not None:
            self.bracepos = (pos1, pos2)
            self.__highlight(self.bracepos, color=self.matched_p_color)
        else:
            self.bracepos = (pos1,)
            self.__highlight(self.bracepos, color=self.unmatched_p_color)


    #-----Widget setup and options
    def set_codecompletion_auto(self, state):
        """Set code completion state"""
        self.codecompletion_auto = state
        
    def set_codecompletion_case(self, state):
        """Case sensitive completion"""
        self.codecompletion_case = state
        self.completion_widget.case_sensitive = state
        
    def set_codecompletion_single(self, state):
        """Show single completion"""
        self.codecompletion_single = state
        self.completion_widget.show_single = state
        
    def set_codecompletion_enter(self, state):
        """Enable Enter key to select completion"""
        self.codecompletion_enter = state
        self.completion_widget.enter_select = state
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state

    def set_wrap_mode(self, mode=None):
        """
        Set wrap mode
        Valid *mode* values: None, 'word', 'character'
        """
        if mode == 'word':
            wrap_mode = QTextOption.WrapAtWordBoundaryOrAnywhere
        elif mode == 'character':
            wrap_mode = QTextOption.WrapAnywhere
        else:
            wrap_mode = QTextOption.NoWrap
        self.setWordWrapMode(wrap_mode)
        
        
    #------Positions, coordinates (cursor, EOF, ...)
    def is_position_sup(self, pos1, pos2):
        """Return True is pos1 > pos2"""
        return pos1 > pos2
        
    def is_position_inf(self, pos1, pos2):
        """Return True is pos1 < pos2"""
        return pos1 < pos2
        
    def get_position(self, position):
        cursor = self.textCursor()
        if position == 'cursor':
            pass
        elif position == 'sol':
            cursor.movePosition(QTextCursor.StartOfBlock)
        elif position == 'eol':
            cursor.movePosition(QTextCursor.EndOfBlock)
        elif position == 'eof':
            cursor.movePosition(QTextCursor.End)
        elif position == 'sof':
            cursor.movePosition(QTextCursor.Start)
        else:
            # Assuming that input argument was already a position
            return position
        return cursor.position()
        
    def get_coordinates(self, position):
        position = self.get_position(position)
        cursor = self.textCursor()
        cursor.setPosition(position)
        point = self.cursorRect(cursor).center()
        return point.x(), point.y()
    
    def get_cursor_line_column(self):
        """Return cursor (line, column) numbers"""
        cursor = self.textCursor()
        return cursor.blockNumber(), cursor.columnNumber()
        
    def get_cursor_line_number(self):
        """Return cursor line number"""
        return self.textCursor().blockNumber()+1

    def set_cursor_position(self, position):
        """Set cursor position"""
        position = self.get_position(position)
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        
    def move_cursor(self, chars=0):
        """Move cursor to left or right (unit: characters)"""
        direction = QTextCursor.Right if chars > 0 else QTextCursor.Left
        for _i in range(abs(chars)):
            self.moveCursor(direction, QTextCursor.MoveAnchor)

    def is_cursor_on_first_line(self):
        """Return True if cursor is on the first line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock)
        return cursor.atStart()

    def is_cursor_on_last_line(self):
        """Return True if cursor is on the last line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.EndOfBlock)
        return cursor.atEnd()

    def is_cursor_at_end(self):
        """Return True if cursor is at the end of the text"""
        return self.textCursor().atEnd()

    def is_cursor_before(self, position, char_offset=0):
        """Return True if cursor is before *position*"""
        position = self.get_position(position) + char_offset
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        if position < cursor.position():
            cursor.setPosition(position)
            return self.textCursor() < cursor
                
    def __move_cursor_anchor(self, what, direction, move_mode):
        assert what in ('character', 'word', 'line')
        if what == 'character':
            if direction == 'left':
                self.moveCursor(QTextCursor.PreviousCharacter, move_mode)
            elif direction == 'right':
                self.moveCursor(QTextCursor.NextCharacter, move_mode)
        elif what == 'word':
            if direction == 'left':
                self.moveCursor(QTextCursor.PreviousWord, move_mode)
            elif direction == 'right':
                self.moveCursor(QTextCursor.NextWord, move_mode)
        elif what == 'line':
            if direction == 'down':
                self.moveCursor(QTextCursor.NextBlock, move_mode)
            elif direction == 'up':
                self.moveCursor(QTextCursor.PreviousBlock, move_mode)
                
    def move_cursor_to_next(self, what='word', direction='left'):
        """
        Move cursor to next *what* ('word' or 'character')
        toward *direction* ('left' or 'right')
        """
        self.__move_cursor_anchor(what, direction, QTextCursor.MoveAnchor)
    

    #------Selection
    def clear_selection(self):
        """Clear current selection"""
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def extend_selection_to_next(self, what='word', direction='left'):
        """
        Extend selection to next *what* ('word' or 'character')
        toward *direction* ('left' or 'right')
        """
        self.__move_cursor_anchor(what, direction, QTextCursor.KeepAnchor)

    def select_current_block(self):
        """
        Select block under cursor
        Block = group of lines separated by either empty lines or commentaries
        """
        cursor = self.textCursor()
        def _is_separator(cursor):
            cursor0 = QTextCursor(cursor)
            cursor0.select(QTextCursor.BlockUnderCursor)
            text = unicode(cursor0.selectedText())
            return len(text.strip()) == 0 or text.lstrip()[0] == '#'
        cursor.movePosition(QTextCursor.StartOfBlock)
        cur_pos = prev_pos = cursor.position()
        while _is_separator(cursor):
            # Moving to the next code block
            cursor.movePosition(QTextCursor.NextBlock)
            prev_pos = cur_pos
            cur_pos = cursor.position()
            if cur_pos == prev_pos:
                return
        while not _is_separator(cursor):
            # Moving to the previous code block
            cursor.movePosition(QTextCursor.PreviousBlock)
            prev_pos = cur_pos
            cur_pos = cursor.position()
            if cur_pos == prev_pos:
                if _is_separator(cursor):
                    return
                else:
                    break
        cursor.setPosition(prev_pos)
        while not _is_separator(cursor):
            # Moving to the next code block
            cursor.movePosition(QTextCursor.NextBlock,
                                QTextCursor.KeepAnchor)
            cur_pos = cursor.position()
            if cur_pos == prev_pos:
                cursor.movePosition(QTextCursor.EndOfBlock,
                                    QTextCursor.KeepAnchor)
                break
            prev_pos = cur_pos
        self.setTextCursor(cursor)


    #------EOL characters
    def set_eol_chars(self, text):
        """
        Set widget end-of-line (EOL) characters from text (analyzes text)
        """
        if not isinstance(text, basestring): # testing for QString (PyQt API#1)
            text = unicode(text)
        eol_chars = sourcecode.get_eol_chars(text)
        if eol_chars is not None and self.eol_chars is not None:
            self.document().setModified(True)
        self.eol_chars = eol_chars
        
    def get_line_separator(self):
        """Return line separator based on current EOL mode"""
        if self.eol_chars is not None:
            return self.eol_chars
        else:
            return os.linesep

    def get_text_with_eol(self):
        """
        Same as 'toPlainText', replace '\n' by correct end-of-line characters
        """
        utext = unicode(self.toPlainText())
        lines = utext.splitlines()
        linesep = self.get_line_separator()
        txt = linesep.join(lines)
        if utext.endswith('\n'):
            txt += linesep
        return txt
            

    #------Text selection
    def has_selected_text(self):
        """Returns True if some text is selected"""
        return bool(unicode(self.textCursor().selectedText()))

    def get_selected_text(self):
        """
        Return text selected by current text cursor, converted in unicode
        
        Replace the unicode line separator character \u2029 by 
        the line separator characters returned by get_line_separator
        """
        return unicode(self.textCursor().selectedText()).replace(u"\u2029",
                                                     self.get_line_separator())

    def copy(self):
        """
        Reimplement Qt method
        Copy text to clipboard with correct EOL chars
        """
        QApplication.clipboard().setText(self.get_selected_text())
    
    def remove_selected_text(self):
        """Delete selected text"""
        self.textCursor().removeSelectedText()
        
    def replace(self, text, pattern=None):
        """Replace selected text by *text*
        If *pattern* is not None, replacing selected text using regular
        expression text substitution"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if pattern is not None:
            seltxt = unicode(cursor.selectedText())
        cursor.removeSelectedText()
        if pattern is not None:
            text = re.sub(unicode(pattern), unicode(text), unicode(seltxt))
        cursor.insertText(text)
        cursor.endEditBlock()
        

    #------Text: get, set, ...
    def __select_text(self, position_from, position_to):
        position_from = self.get_position(position_from)
        position_to = self.get_position(position_to)
        cursor = self.textCursor()
        cursor.setPosition(position_from)
        cursor.setPosition(position_to, QTextCursor.KeepAnchor)
        return cursor

    def get_text_line(self, line_nb):
        """Return text line at line number *line_nb*"""
        # Taking into account the case when a file ends in an empty line,
        # since splitlines doesn't return that line as the last element
        # TODO: Make this function more efficient
        try:
            return unicode(self.toPlainText()).splitlines()[line_nb]
        except IndexError:
            return self.get_line_separator()
    
    def get_text(self, position_from, position_to):
        """
        Return text between *position_from* and *position_to*
        Positions may be positions or 'sol', 'eol', 'sof', 'eof' or 'cursor'
        """
        cursor = self.__select_text(position_from, position_to)
        text = unicode(cursor.selectedText())
        if text:
            while text.endswith("\n"):
                text = text[:-1]
            while text.endswith(u"\u2029"):
                text = text[:-1]
        return text
    
    def get_character(self, position):
        """Return character at *position*"""
        position = self.get_position(position)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        if position < cursor.position():
            cursor.setPosition(position)
            cursor.movePosition(QTextCursor.Right,
                                QTextCursor.KeepAnchor)
            return unicode(cursor.selectedText())
        else:
            return ''
    
    def insert_text(self, text):
        """Insert text at cursor position"""
        if not self.isReadOnly():
            self.textCursor().insertText(text)
    
    def replace_text(self, position_from, position_to, text):
        cursor = self.__select_text(position_from, position_to)
        cursor.removeSelectedText()
        cursor.insertText(text)
        
    def remove_text(self, position_from, position_to):
        cursor = self.__select_text(position_from, position_to)
        cursor.removeSelectedText()
        
    def find_multiline_pattern(self, regexp, cursor, findflag):
        """Reimplement QTextDocument's find method
        
        Add support for *multiline* regular expressions"""
        pattern = unicode(regexp.pattern())
        text = unicode(self.toPlainText())
        try:
            regobj = re.compile(pattern)
        except sre_constants.error:
            return
        if findflag & QTextDocument.FindBackward:
            # Find backward
            offset = min([cursor.selectionEnd(), cursor.selectionStart()])
            text = text[:offset]
            matches = [_m for _m in regobj.finditer(text, 0, offset)]
            if matches:
                match = matches[-1]
            else:
                return
        else:
            # Find forward
            offset = max([cursor.selectionEnd(), cursor.selectionStart()])
            match = regobj.search(text, offset)
        if match:
            pos1, pos2 = match.span()
            fcursor = self.textCursor()
            fcursor.setPosition(pos1)
            fcursor.setPosition(pos2, QTextCursor.KeepAnchor)
            return fcursor

    def find_text(self, text, changed=True, forward=True, case=False,
                  words=False, regexp=False):
        """Find text"""
        cursor = self.textCursor()
        findflag = QTextDocument.FindFlag()
        if not forward:
            findflag = findflag | QTextDocument.FindBackward
        moves = [QTextCursor.NoMove]
        if forward:
            moves += [QTextCursor.NextWord, QTextCursor.Start]
            if changed:
                if unicode(cursor.selectedText()):
                    new_position = min([cursor.selectionStart(),
                                        cursor.selectionEnd()])
                    cursor.setPosition(new_position)
                else:
                    cursor.movePosition(QTextCursor.PreviousWord)
        else:
            moves += [QTextCursor.End]
        if not regexp:
            text = re.escape(unicode(text))
        pattern = QRegExp(r"\b%s\b" % text if words else text,
                          Qt.CaseSensitive if case else Qt.CaseInsensitive,
                          QRegExp.RegExp2)
        for move in moves:
            cursor.movePosition(move)
            if regexp and '\\n' in text:
                # Multiline regular expression
                found_cursor = self.find_multiline_pattern(pattern, cursor,
                                                           findflag)
            else:
                # Single line find: using the QTextDocument's find function,
                # probably much more efficient than ours
                found_cursor = self.document().find(pattern, cursor, findflag)
            if found_cursor is not None and not found_cursor.isNull():
                self.setTextCursor(found_cursor)
                return True
        return False
    
    def get_current_word(self):
        """Return current word, i.e. word at cursor position"""
        cursor = self.textCursor()

        if cursor.hasSelection():
            # Removes the selection and moves the cursor to the left side 
            # of the selection: this is required to be able to properly 
            # select the whole word under cursor (otherwise, the same word is 
            # not selected when the cursor is at the right side of it):
            cursor.setPosition(min([cursor.selectionStart(),
                                    cursor.selectionEnd()]))
        else:
            # Checks if the first character to the right is a white space
            # and if not, moves the cursor one word to the left (otherwise,
            # if the character to the left do not match the "word regexp" 
            # (see below), the word to the left of the cursor won't be 
            # selected)
            cursor2 = self.textCursor()
            cursor2.movePosition(QTextCursor.NextCharacter,
                                 QTextCursor.KeepAnchor)
            if not unicode(cursor2.selectedText()).strip():
                cursor.movePosition(QTextCursor.WordLeft)

        cursor.select(QTextCursor.WordUnderCursor)
        text = unicode(cursor.selectedText())
        match = re.findall(r'([a-zA-Z\_]+[0-9a-zA-Z\_]*)', text)
        if match:
            return match[0]
    
    def get_current_line(self):
        """Return current line's text"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.BlockUnderCursor)
        return unicode(cursor.selectedText())
    
    def get_line_number_at(self, coordinates):
        """Return line number at *coordinates* (QPoint)"""
        cursor = self.cursorForPosition(coordinates)
        return cursor.blockNumber()-1
    
    def get_line_at(self, coordinates):
        """Return line at *coordinates* (QPoint)"""
        cursor = self.cursorForPosition(coordinates)
        cursor.select(QTextCursor.BlockUnderCursor)
        return unicode(cursor.selectedText()).replace(u'\u2029', '')
    
    def get_word_at(self, coordinates):
        """Return word at *coordinates* (QPoint)"""
        cursor = self.cursorForPosition(coordinates)
        cursor.select(QTextCursor.WordUnderCursor)
        return unicode(cursor.selectedText())
    
    def get_block_indentation(self, block_nb):
        """Return line indentation (character number)"""
        text = unicode(self.document().findBlockByNumber(block_nb).text())
        return len(text)-len(text.lstrip())
    
    def get_selection_bounds(self):
        """Return selection bounds (block numbers)"""
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        block_start = self.document().findBlock(start)
        block_end = self.document().findBlock(end)
        return sorted([block_start.blockNumber(), block_end.blockNumber()])
        
    def get_executable_text(self):
        """Return selected text or current line as an processed text,
        to be executable in a Python/IPython interpreter"""
        no_selection = not self.has_selected_text()
        if no_selection:
            self.select_current_block()
        
        ls = self.get_line_separator()
        
        _indent = lambda line: len(line)-len(line.lstrip())
        
        line_from, line_to = self.get_selection_bounds()
        text = self.get_selected_text()

        lines = text.split(ls)
        if len(lines) > 1:
            # Multiline selection -> eventually fixing indentation
            original_indent = _indent(self.get_text_line(line_from))
            text = (" "*(original_indent-_indent(lines[0])))+text
        
        # If there is a common indent to all lines, remove it
        min_indent = 999
        for line in text.split(ls):
            if line.strip():
                min_indent = min(_indent(line), min_indent)
        if min_indent:
            text = ls.join([line[min_indent:] for line in text.split(ls)])
        
        # Add an EOL character if a block stars with various Python
        # reserved words, so that it gets evaluated automatically
        # by the console
        first_line = lines[0].lstrip()
        last_line = self.get_text_line(line_to).strip()
        words = ['def', 'for', 'if', 'while', 'try', 'with', 'class']
        if any([first_line.startswith(w) for w in words]):
            text += ls
            if last_line != '':
                text += ls

        if no_selection:
            self.setFocus()
            self.clear_selection()
        
        return text
    
    def get_line_count(self):
        """Return document total line number"""
        return self.blockCount()
    
    def __duplicate_line_or_selection(self, after_current_line=True):
        """Duplicate current line or selected text"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        orig_sel = start_pos, end_pos = (cursor.selectionStart(),
                                         cursor.selectionEnd())
        if unicode(cursor.selectedText()):
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            cursor.movePosition(QTextCursor.StartOfBlock,
                                QTextCursor.KeepAnchor)
            if not unicode(cursor.selectedText()):
                cursor.movePosition(QTextCursor.PreviousBlock)
                end_pos = cursor.position()
            
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        while cursor.position() <= end_pos:
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            if cursor.atEnd():
                cursor_temp = QTextCursor(cursor)
                cursor_temp.clearSelection()
                cursor_temp.insertText(self.get_line_separator())
                break
            cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)            
        text = cursor.selectedText()
        cursor.clearSelection()
        
        if not after_current_line:
            # Moving cursor before current line/selected text
            cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.StartOfBlock)
            orig_sel = (orig_sel[0]+len(text), orig_sel[1]+len(text))
        
        cursor.insertText(text)
        cursor.endEditBlock()
        cursor.setPosition(orig_sel[0])
        cursor.setPosition(orig_sel[1], QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
    
    def duplicate_line(self):
        """
        Duplicate current line or selected text
        Paste the duplicated text *after* the current line/selected text
        """
        self.__duplicate_line_or_selection(after_current_line=True)
    
    def copy_line(self):
        """
        Copy current line or selected text
        Paste the duplicated text *before* the current line/selected text
        """
        self.__duplicate_line_or_selection(after_current_line=False)
        
    def __move_line_or_selection(self, after_current_line=True):
        """Move current line or selected text"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        orig_sel = start_pos, end_pos = (cursor.selectionStart(),
                                         cursor.selectionEnd())
        if unicode(cursor.selectedText()):
            # Check if start_pos is at the start of a block
            cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.StartOfBlock)
            start_pos = cursor.position()

            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            cursor.movePosition(QTextCursor.StartOfBlock,
                                QTextCursor.KeepAnchor)
            if unicode(cursor.selectedText()):
                cursor.movePosition(QTextCursor.NextBlock)
                end_pos = cursor.position()
        else:
            cursor.movePosition(QTextCursor.StartOfBlock)
            start_pos = cursor.position()
            cursor.movePosition(QTextCursor.NextBlock)
            end_pos = cursor.position()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        
        sel_text = unicode(cursor.selectedText())
        cursor.removeSelectedText()
        
        if after_current_line:
            text = unicode(cursor.block().text())
            orig_sel = (orig_sel[0]+len(text)+1, orig_sel[1]+len(text)+1)
            cursor.movePosition(QTextCursor.NextBlock)
        else:
            cursor.movePosition(QTextCursor.PreviousBlock)
            text = unicode(cursor.block().text())
            orig_sel = (orig_sel[0]-len(text)-1, orig_sel[1]-len(text)-1)
        cursor.insertText(sel_text)

        cursor.endEditBlock()

        cursor.setPosition(orig_sel[0])
        cursor.setPosition(orig_sel[1], QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
    
    def move_line_up(self):
        """Move up current line or selected text"""
        self.__move_line_or_selection(after_current_line=False)
        
    def move_line_down(self):
        """Move down current line or selected text"""
        self.__move_line_or_selection(after_current_line=True)
        
    def extend_selection_to_complete_lines(self):
        """Extend current selection to complete lines"""
        cursor = self.textCursor()
        start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        if cursor.atBlockStart():
            cursor.movePosition(QTextCursor.PreviousBlock,
                                QTextCursor.KeepAnchor)
            cursor.movePosition(QTextCursor.EndOfBlock,
                                QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        
    def delete_line(self):
        """Delete current line"""
        cursor = self.textCursor()
        if self.has_selected_text():
            self.extend_selection_to_complete_lines()
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
            cursor.setPosition(start_pos)
        else:
            start_pos = end_pos = cursor.position()
        cursor.beginEditBlock()
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        while cursor.position() <= end_pos:
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            if cursor.atEnd():
                break
            cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.endEditBlock()
        self.ensureCursorVisible()


    #------Code completion / Calltips
    def show_calltip(self, title, text, color='#2D62FF',
                     at_line=None, at_position=None):
        """Show calltip"""
        if text is None or len(text) == 0:
            return
        # Saving cursor position:
        if at_position is None:
            at_position = self.get_position('cursor')
        self.calltip_position = at_position
        # Preparing text:
        weight = 'bold' if self.calltip_font.bold() else 'normal'
        size = self.calltip_font.pointSize()
        family = self.calltip_font.family()
        format1 = '<div style=\'font-size: %spt; color: %s\'>' % (size, color)
        format2 = '<hr><div style=\'font-family: "%s"; font-size: %spt; font-weight: %s\'>' % (family, size, weight)
        if isinstance(text, list):
            text = "\n    ".join(text)
        text = text.replace('\n', '<br>')
        if len(text) > self.calltip_size:
            text = text[:self.calltip_size] + " ..."
        tiptext = format1 + ('<b>%s</b></div>' % title) \
                  + format2 + text + "</div>"
        # Showing tooltip at cursor position:
        cx, cy = self.get_coordinates('cursor')
        if at_line is not None:
            cx = 5
            cursor = QTextCursor(self.document().findBlockByNumber(at_line-1))
            cy = self.cursorRect(cursor).top()
        point = self.mapToGlobal(QPoint(cx, cy))
        point.setX(point.x()+self.get_linenumberarea_width())
        QToolTip.showText(point, tiptext)

    def hide_tooltip_if_necessary(self, key):
        """Hide calltip when necessary"""
        try:
            calltip_char = self.get_character(self.calltip_position)
            before = self.is_cursor_before(self.calltip_position,
                                           char_offset=1)
            other = key in (Qt.Key_ParenRight, Qt.Key_Period, Qt.Key_Tab)
            if calltip_char not in ('?','(') or before or other:
                QToolTip.hideText()
        except (IndexError, TypeError):
            QToolTip.hideText()

    def show_completion_widget(self, textlist, automatic=True):
        """Show completion widget"""
        self.completion_widget.show_list(textlist, automatic=automatic)
        
    def hide_completion_widget(self):
        """Hide completion widget"""
        self.completion_widget.hide()

    def show_completion_list(self, completions, completion_text="",
                             automatic=True):
        """Display the possible completions"""
        if len(completions) == 0 or completions == [completion_text]:
            return
        self.completion_text = completion_text
        # Sorting completion list (entries starting with underscore are 
        # put at the end of the list):
        underscore = set([comp for comp in completions if comp.startswith('_')])
        completions = sorted(set(completions)-underscore, key=string.lower)+\
                      sorted(underscore, key=string.lower)
        self.show_completion_widget(completions, automatic=automatic)
        
    def select_completion_list(self):
        """Completion list is active, Enter was just pressed"""
        self.completion_widget.item_selected()
        
    def insert_completion(self, text):
        if text:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.PreviousCharacter,
                                QTextCursor.KeepAnchor,
                                len(self.completion_text))
            cursor.removeSelectedText()
            self.insert_text(text)

    def is_completion_widget_visible(self):
        """Return True is completion list widget is visible"""
        return self.completion_widget.isVisible()
    
        
    #------Standard keys
    def stdkey_clear(self):
        if not self.has_selected_text():
            self.moveCursor(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        self.remove_selected_text()
    
    def stdkey_backspace(self):
        if not self.has_selected_text():
            self.moveCursor(QTextCursor.PreviousCharacter,
                            QTextCursor.KeepAnchor)
        self.remove_selected_text()

    def __get_move_mode(self, shift):
        return QTextCursor.KeepAnchor if shift else QTextCursor.MoveAnchor

    def stdkey_up(self, shift):
        self.moveCursor(QTextCursor.Up, self.__get_move_mode(shift))

    def stdkey_down(self, shift):
        self.moveCursor(QTextCursor.Down, self.__get_move_mode(shift))

    def stdkey_tab(self):
        self.insert_text(self.indent_chars)

    def stdkey_home(self, shift, prompt_pos=None):
        """Smart HOME feature: cursor is first moved at 
        indentation position, then at the start of the line"""
        if prompt_pos is None:
            start_position = self.get_position('sol')
        else:
            start_position = self.get_position(prompt_pos)
        text = self.get_text(start_position, 'eol')
        indent_pos = start_position+len(text)-len(text.lstrip())
        cursor = self.textCursor()
        move_mode = self.__get_move_mode(shift)
        if cursor.position() != indent_pos:
            cursor.setPosition(indent_pos, move_mode)
        else:
            cursor.setPosition(start_position, move_mode)
        self.setTextCursor(cursor)

    def stdkey_end(self, shift):
        self.moveCursor(QTextCursor.EndOfBlock, self.__get_move_mode(shift))

    def stdkey_pageup(self):
        pass

    def stdkey_pagedown(self):
        pass

    def stdkey_escape(self):
        pass

                
    #----Focus
    def focusInEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        self.emit(SIGNAL("focus_in()"))
        QPlainTextEdit.focusInEvent(self, event)
        
    def focusOutEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        QPlainTextEdit.focusOutEvent(self, event)


class QtANSIEscapeCodeHandler(ANSIEscapeCodeHandler):
    def __init__(self):
        ANSIEscapeCodeHandler.__init__(self)
        self.base_format = None
        self.current_format = None
        
    def set_light_background(self, state):
        if state:
            self.default_foreground_color = 30
            self.default_background_color = 47
        else:
            self.default_foreground_color = 37
            self.default_background_color = 40
        
    def set_base_format(self, base_format):
        self.base_format = base_format
        
    def get_format(self):
        return self.current_format
        
    def set_style(self):
        """
        Set font style with the following attributes:
        'foreground_color', 'background_color', 'italic',
        'bold' and 'underline'
        """
        if self.current_format is None:
            assert self.base_format is not None
            self.current_format = QTextCharFormat(self.base_format)
        # Foreground color
        if self.foreground_color is None:
            qcolor = self.base_format.foreground()
        else:
            cstr = self.ANSI_COLORS[self.foreground_color-30][self.intensity]
            qcolor = QColor(cstr)
        self.current_format.setForeground(qcolor)        
        # Background color
        if self.background_color is None:
            qcolor = self.base_format.background()
        else:
            cstr = self.ANSI_COLORS[self.background_color-40][self.intensity]
            qcolor = QColor(cstr)
        self.current_format.setBackground(qcolor)
        
        font = self.current_format.font()
        # Italic
        if self.italic is None:
            italic = self.base_format.fontItalic()
        else:
            italic = self.italic
        font.setItalic(italic)
        # Bold
        if self.bold is None:
            bold = self.base_format.font().bold()
        else:
            bold = self.bold
        font.setBold(bold)
        # Underline
        if self.underline is None:
            underline = self.base_format.font().underline()
        else:
            underline = self.underline
        font.setUnderline(underline)
        self.current_format.setFont(font)


def inverse_color(color):
    color.setHsv(color.hue(), color.saturation(), 255-color.value())
    
class ConsoleFontStyle(object):
    def __init__(self, foregroundcolor, backgroundcolor, 
                 bold, italic, underline):
        self.foregroundcolor = foregroundcolor
        self.backgroundcolor = backgroundcolor
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.format = None
        
    def apply_style(self, font, light_background, is_default):
        self.format = QTextCharFormat()
        self.format.setFont(font)
        foreground = QColor(self.foregroundcolor)
        if not light_background and is_default:
            inverse_color(foreground)
        self.format.setForeground(foreground)
        background = QColor(self.backgroundcolor)
        if not light_background:
            inverse_color(background)
        self.format.setBackground(background)
        font = self.format.font()
        font.setBold(self.bold)
        font.setItalic(self.italic)
        font.setUnderline(self.underline)
        self.format.setFont(font)
    
class ConsoleBaseWidget(TextEditBaseWidget):
    """Console base widget"""
    BRACE_MATCHING_SCOPE = ('sol', 'eol')
    COLOR_PATTERN = re.compile('\x01?\x1b\[(.*?)m\x02?')
    
    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)
        
        self.light_background = True

        self.setMaximumBlockCount(300)

        # ANSI escape code handler
        self.ansi_handler = QtANSIEscapeCodeHandler()
                
        # Disable undo/redo (nonsense for a console widget...):
        self.setUndoRedoEnabled(False)
        
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     lambda user_id, text:
                     self.emit(SIGNAL('completion_widget_activated(QString)'),
                               text))
        
        self.default_style = ConsoleFontStyle(
                            foregroundcolor=0x000000, backgroundcolor=0xFFFFFF,
                            bold=False, italic=False, underline=False)
        self.error_style  = ConsoleFontStyle(
                            foregroundcolor=0xFF0000, backgroundcolor=0xFFFFFF,
                            bold=False, italic=False, underline=False)
        self.traceback_link_style  = ConsoleFontStyle(
                            foregroundcolor=0x0000FF, backgroundcolor=0xFFFFFF,
                            bold=True, italic=False, underline=True)
        self.prompt_style  = ConsoleFontStyle(
                            foregroundcolor=0x00AA00, backgroundcolor=0xFFFFFF,
                            bold=True, italic=False, underline=False)
        self.font_styles = (self.default_style, self.error_style,
                            self.traceback_link_style, self.prompt_style)
        self.set_pythonshell_font()
        self.setMouseTracking(True)
        
    def set_light_background(self, state):
        self.light_background = state
        if state:
            self.set_palette(background=QColor(Qt.white),
                             foreground=QColor(Qt.darkGray))
        else:
            self.set_palette(background=QColor(Qt.black),
                             foreground=QColor(Qt.lightGray))
        self.ansi_handler.set_light_background(state)
        self.set_pythonshell_font()
        
    def set_selection(self, start, end):
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def truncate_selection(self, position_from):
        """Unselect read-only parts in shell, like prompt"""
        position_from = self.get_position(position_from)
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if start < end:
            start = max([position_from, start])
        else:
            end = max([position_from, end])
        self.set_selection(start, end)

    def restrict_cursor_position(self, position_from, position_to):
        """In shell, avoid editing text except between prompt and EOF"""
        position_from = self.get_position(position_from)
        position_to = self.get_position(position_to)
        cursor = self.textCursor()
        cursor_position = cursor.position()
        if cursor_position < position_from or cursor_position > position_to:
            self.set_cursor_position(position_to)

    #------Python shell
    def insert_text(self, text):
        """Reimplement TextEditBaseWidget method"""
        self.textCursor().insertText(text, self.default_style.format)
        
    def paste(self):
        """Reimplement Qt method"""
        if self.has_selected_text():
            self.remove_selected_text()
        self.insert_text(QApplication.clipboard().text())
        
    def append_text_to_shell(self, text, error, prompt):
        """
        Append text to Python shell
        In a way, this method overrides the method 'insert_text' when text is 
        inserted at the end of the text widget for a Python shell
        
        Handles error messages and show blue underlined links
        Handles ANSI color sequences
        Handles ANSI FF sequence
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        while True:
            index = text.find(chr(12))
            if index == -1:
                break
            text = text[index+1:]
            self.clear()
        if error:
            is_traceback = False
            for text in text.splitlines(True):
                if text.startswith('  File') \
                and not text.startswith('  File "<'):
                    is_traceback = True
                    # Show error links in blue underlined text
                    cursor.insertText('  ', self.default_style.format)
                    cursor.insertText(text[2:],
                                      self.traceback_link_style.format)
                else:
                    # Show error/warning messages in red
                    cursor.insertText(text, self.error_style.format)
            if is_traceback:
                self.emit(SIGNAL('traceback_available()'))
        elif prompt:
            # Show prompt in green
            cursor.insertText(text, self.prompt_style.format)
        else:
            # Show other outputs in black
            last_end = 0
            for match in self.COLOR_PATTERN.finditer(text):
                cursor.insertText(text[last_end:match.start()],
                                  self.default_style.format)
                last_end = match.end()
                for code in [int(_c) for _c in match.group(1).split(';')]:
                    self.ansi_handler.set_code(code)
                self.default_style.format = self.ansi_handler.get_format()
            cursor.insertText(text[last_end:], self.default_style.format)
#            # Slower alternative:
#            segments = self.COLOR_PATTERN.split(text)
#            cursor.insertText(segments.pop(0), self.default_style.format)
#            if segments:
#                for ansi_tags, text in zip(segments[::2], segments[1::2]):
#                    for ansi_tag in ansi_tags.split(';'):
#                        self.ansi_handler.set_code(int(ansi_tag))
#                    self.default_style.format = self.ansi_handler.get_format()
#                    cursor.insertText(text, self.default_style.format)
        self.set_cursor_position('eof')
        self.setCurrentCharFormat(self.default_style.format)
    
    def set_pythonshell_font(self, font=None):
        """Python Shell only"""
        if font is None:
            font = QFont()
        for style in self.font_styles:
            style.apply_style(font=font,
                              light_background=self.light_background,
                              is_default=style is self.default_style)
        self.ansi_handler.set_base_format(self.default_style.format)
        
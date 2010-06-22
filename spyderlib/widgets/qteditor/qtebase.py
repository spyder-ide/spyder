# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""QPlainTextEdit base class"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, re

from PyQt4.QtGui import (QTextCursor, QColor, QFont, QApplication, QTextEdit,
                         QTextCharFormat, QToolTip, QTextDocument, QListWidget,
                         QPlainTextEdit)
from PyQt4.QtCore import QPoint, SIGNAL, Qt

# Local imports
from spyderlib.config import CONF, get_font
from spyderlib.widgets.shellhelpers import ANSIEscapeCodeHandler

# For debugging purpose:
STDOUT = sys.stdout


class CompletionWidget(QListWidget):
    """Completion list widget"""
    def __init__(self, parent, ancestor):
        # Currently, the parent widget is set to None:
        QListWidget.__init__(self, None)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.textedit = parent
        self.completion_list = None
        self.case_sensitive = False
        self.show_single = None # see note in method 'setup'
        self.enter_select = None
        srect = QApplication.desktop().availableGeometry(self)
        self.screen_size = (srect.width(), srect.height())
        self.hide()
        self.connect(self, SIGNAL("itemActivated(QListWidgetItem*)"),
                     self.item_selected)
        
    def setup_options(self, case_sensitive, show_single):
        self.case_sensitive = case_sensitive
        self.show_single = show_single # not implemented yet because it would
        # require to know if the completion has been triggered manually or not
        
    def setup_appearance(self, size, font):
        self.resize(*size)
        self.setFont(font)
        
    def set_enter_select(self, state):
        self.enter_select = state        
        
    def show_list(self, completion_list):
        self.completion_list = completion_list
        self.clear()
        self.addItems(completion_list)
        self.setCurrentRow(0)
        self.show()
        self.raise_()
        self.setFocus()
        
        point = self.textedit.cursorRect().bottomRight()
        point = self.textedit.mapToGlobal(point)
        if self.screen_size[1]-point.y()-self.height() < 0:
            point = self.textedit.cursorRect().topRight()
            point = self.textedit.mapToGlobal(point)
            point.setY(point.y()-self.height())
        if self.parent() is not None:
            # Useful only if we set parent to 'ancestor' in __init__
            point = self.parent().mapFromGlobal(point)
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
        if (key in (Qt.Key_Return, Qt.Key_Enter) and self.enter_select) \
           or key == Qt.Key_Tab:
            self.item_selected()
            event.accept()
        elif key in (Qt.Key_Return, Qt.Key_Enter,
                     Qt.Key_Period, Qt.Key_Left, Qt.Key_Right):
            self.hide()
            self.textedit.keyPressEvent(event)
        elif event.modifiers() & Qt.ShiftModifier:
            self.textedit.keyPressEvent(event)
            if len(text):
                self.update_current()
            event.accept()
        elif key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown,
                     Qt.Key_Home, Qt.Key_End):
            QListWidget.keyPressEvent(self, event)
        elif len(text) or key == Qt.Key_Backspace:
            self.textedit.keyPressEvent(event)
            self.update_current()
            event.accept()
        else:
            self.hide()
            event.ignore()
            
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
        
        self.extra_selections_dict = {}
        
        # Undo/Redo
        self.undo_available = False
        self.redo_available = False
        self.connect(self, SIGNAL("undoAvailable(bool)"), self.set_undo)
        self.connect(self, SIGNAL("redoAvailable(bool)"), self.set_redo)
        self.connect(self, SIGNAL('textChanged()'), self.changed)
        self.connect(self, SIGNAL('cursorPositionChanged()'),
                     self.cursor_position_changed)

        # Code completion / calltips
        self.completion_widget = CompletionWidget(self, parent)
        self.codecompletion_auto = False
        self.codecompletion_enter = False
        self.calltips = True
        self.completion_text = ""
        self.calltip_position = None

        # Brace matching
        self.bracepos = None

        self.setup()
        
        
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
        self.emit(SIGNAL('modificationChanged(bool)'), self.isModified())


    #------Brace matching
    def __find_brace_match(self, position, brace, forward):
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
#            selection.format.setProperty(QTextFormat.OutlinePen, QPen(color))
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
            pos2 = self.__find_brace_match(pos1, text, forward=False)
        elif text in ('(', '[', '{'):
            pos2 = self.__find_brace_match(pos1, text, forward=True)
        else:
            return
        if pos2 is not None:
            self.bracepos = (pos1, pos2)
            self.__highlight(self.bracepos, color=QColor(Qt.green).lighter(160))
        else:
            self.bracepos = (pos1,)
            self.__highlight(self.bracepos, color=QColor(Qt.red).lighter(160))
        
        
    #------QsciScintilla API emulation
    def isModified(self):
        """Reimplement QScintilla method
        Returns true if the text has been modified"""
        return self.document().isModified()
    
    def setModified(self, state):
        """Reimplement QScintilla method
        Sets the modified state of the text edit to state"""
        self.document().setModified(state)
        
    def hasSelectedText(self):
        """Reimplements QScintilla method
        Returns true if some text is selected"""
        return not self.textCursor().selectedText().isEmpty()
    
    def selectedText(self):
        """Reimplements QScintilla method
        Returns the selected text or an empty string
        if there is no currently selected text"""
        return self.textCursor().selectedText()
    
    def removeSelectedText(self):
        """Delete selected text"""
        self.textCursor().removeSelectedText()
        
    def set_undo(self, state):
        """Set undo availablity"""
        self.undo_available = state
        
    def set_redo(self, state):
        """Set redo availablity"""
        self.redo_available = state
        
    def isUndoAvailable(self):
        """Reimplements QScintilla method
        Returns true if there is something that can be undone"""
        return self.undo_available
        
    def isRedoAvailable(self):
        """Reimplements QScintilla method
        Returns true if there is something that can be redone"""
        return self.redo_available
    
    def replace(self, text):
        """Reimplements QScintilla method"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(text)
        cursor.endEditBlock()
    
    def text(self, line_nb=None):
        """Reimplements QScintilla method"""
        if line_nb is None:
            return self.toPlainText()
        else:
            return unicode(self.toPlainText()).splitlines()[line_nb-1]
    
    def setText(self, text):
        """Reimplements QScintilla method"""
        self.setPlainText(text)

        
    #-----Widget setup and options
    def setup(self):
        """Configure QPlainTextEdit"""
        # Calltips
        self.calltip_size = CONF.get('shell_appearance', 'calltips/size')
        self.calltip_font = get_font('shell_appearance', 'calltips')
        # Completion
        size = CONF.get('shell_appearance', 'completion/size')
        font = get_font('shell_appearance', 'completion')
        self.completion_widget.setup_appearance(size, font)

    def set_codecompletion_auto(self, state):
        """Set code completion state"""
        self.codecompletion_auto = state
        
    def set_codecompletion_enter(self, state):
        """Enable Enter key to select completion"""
        self.codecompletion_enter = state
        self.completion_widget.set_enter_select(state)
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state

    def set_caret(self, color=None, width=None):
        """Set caret properties"""
        #XXX: not possible to change caret color in QPlainTextEdit
        if width is not None:
            self.setCursorWidth(width)
            
    def set_wrap_mode(self, mode=None):
        """
        Set wrap mode
        Valid *mode* values: None, 'word', 'character'
        """
        wrap_mode = QPlainTextEdit.NoWrap
        #XXX: no word/character wrapping in QPlainTextEdit
        if mode == 'word':
            wrap_mode = QPlainTextEdit.WidgetWidth
        elif mode == 'character':
            wrap_mode = QPlainTextEdit.WidgetWidth
        self.setLineWrapMode(wrap_mode)

    def toggle_wrap_mode(self, enable):
        """Enable/disable wrap mode"""
        self.set_wrap_mode('word' if enable else None)
        
        
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
        cursor = self.textCursor()
        return cursor.blockNumber()+1

    def set_cursor_position(self, position):
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
                self.moveCursor(QTextCursor.NextRow, move_mode)
            elif direction == 'up':
                self.moveCursor(QTextCursor.PreviousRow, move_mode)
        elif what == 'block':
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
        cursor.select(QTextCursor.BlockUnderCursor)
        self.setTextCursor(cursor)
        

    #------Text: get, set, replace, ...
    def __select_text(self, position_from, position_to):
        position_from = self.get_position(position_from)
        position_to = self.get_position(position_to)
        cursor = self.textCursor()
        cursor.setPosition(position_from)
        cursor.setPosition(position_to, QTextCursor.KeepAnchor)
        return cursor

    def get_text(self, position_from=None, position_to=None):
        """
        Return text between *position_from* and *position_to*
        Positions may be positions or 'sol', 'eol', 'sof', 'eof' or 'cursor'
        """
        if position_from is None and position_to is None:
            return self.text()
        cursor = self.__select_text(position_from, position_to)
        text = cursor.selectedText()
        if not text.isEmpty():
            while text.endsWith("\n"):
                text.chop(1)
            while text.endsWith(u"\u2029"):
                text.chop(1)
        return unicode(text)
    
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
        self.textCursor().insertText(text)
    
    def replace_text(self, position_from, position_to, text):
        cursor = self.__select_text(position_from, position_to)
        cursor.removeSelectedText()
        cursor.insertText(text)
        
    def remove_text(self, position_from, position_to):
        cursor = self.__select_text(position_from, position_to)
        cursor.removeSelectedText()

    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False):
        """Find text"""
        cursor = self.textCursor()
        findflag = QTextDocument.FindFlag()
        if not forward:
            findflag = findflag | QTextDocument.FindBackward
        if case:
            findflag = findflag | QTextDocument.FindCaseSensitively
        if words:
            findflag = findflag | QTextDocument.FindWholeWords
        moves = [QTextCursor.NoMove]
        if forward:
            moves += [QTextCursor.NextWord, QTextCursor.Start]
            if changed:
                cursor.movePosition(QTextCursor.PreviousWord)
        else:
            moves += [QTextCursor.End]
        for move in moves:
            cursor.movePosition(move)
            found_cursor = self.document().find(text, cursor, findflag)
            if not found_cursor.isNull():
                self.setTextCursor(found_cursor)
                return True
        return False
    
    def get_current_word(self):
        """Return current word, i.e. word at cursor position"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        text = unicode(cursor.selectedText())
        match = re.findall(r'([a-zA-Z_]+[0-9a-zA-Z_]*)', text)
        if match:
            return match[0]
    
    def get_current_line(self):
        """***NOT TESTED*** Return current line"""
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
    
    def get_indentation(self, block_nb):
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
        
    def get_line_count(self):
        """Return document total line number"""
        return self.blockCount()
    
    def duplicate_line(self):
        """Duplicate current line"""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
        if not cursor.selectedText().isEmpty():
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            cursor.movePosition(QTextCursor.StartOfBlock,
                                QTextCursor.KeepAnchor)
            if cursor.selectedText().isEmpty():
                cursor.movePosition(QTextCursor.PreviousBlock)
                end_pos = cursor.position()
            
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        while cursor.position() <= end_pos:
            cursor.movePosition(QTextCursor.NextBlock,
                                QTextCursor.KeepAnchor)            
        text = cursor.selectedText()
        cursor.clearSelection()
        cursor.insertText(text)
        cursor.endEditBlock()
        

    #------Code completion / Calltips
    def show_calltip(self, title, text, color='#2D62FF', at_line=None):
        """
        Show calltip
        This is here because QScintilla does not implement well calltips
        """
        if text is None or len(text)==0:
            return
        weight = 'bold' if self.calltip_font.bold() else 'normal'
        size = self.calltip_font.pointSize()
        family = self.calltip_font.family()
        format1 = '<div style=\'font-size: %spt; color: %s\'>' % (size, color)
        format2 = '<hr><div style=\'font-family: "%s"; font-size: %spt; font-weight: %s\'>' % (family, size, weight)
        if isinstance(text, list):
            text = "\n    ".join(text)
        else:
            text = text.replace('\n', '<br>')
        if len(text) > self.calltip_size:
            text = text[:self.calltip_size] + " ..."
        tiptext = format1 + ('<b>%s</b></div>' % title) \
                  + format2 + text + "</div>"
        # Showing tooltip at cursor position:
        cx, cy = self.get_coordinates('cursor')
        if at_line is not None:
            #TODO: this code has not yet been ported to QPlainTextEdit because it's
            # only used in editor widgets which are based on QsciScintilla
            cx = 5
            cursor = self.textCursor()
            block = self.document().findBlockByNumber(at_line-1)
            cursor.setPosition(block.position())
            cy = self.cursorRect(cursor).top()
        QToolTip.showText(self.mapToGlobal(QPoint(cx, cy)), tiptext)
        # Saving cursor position:
        self.calltip_position = self.get_position('cursor')

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

    def setup_code_completion(self, case_sensitive, show_single, from_document):
        """
        Setup code completion feature
        Argument 'from_document' is ignored: compat. with QScintilla's API
        """
        self.completion_widget.setup_options(case_sensitive, show_single)
    
    def show_completion_widget(self, textlist):
        """Show completion widget"""
        self.completion_widget.show_list(textlist)
        
    def hide_completion_widget(self):
        """Hide completion widget"""
        self.completion_widget.hide()
        
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
        if not self.hasSelectedText():
            self.moveCursor(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        self.textCursor().removeSelectedText()
    
    def stdkey_backspace(self):
        if not self.hasSelectedText():
            self.moveCursor(QTextCursor.PreviousCharacter,
                            QTextCursor.KeepAnchor)
        self.textCursor().removeSelectedText()

    def __get_move_mode(self, shift):
        return QTextCursor.KeepAnchor if shift else QTextCursor.MoveAnchor

    def stdkey_up(self, shift):
        self.moveCursor(QTextCursor.Up, self.__get_move_mode(shift))

    def stdkey_down(self, shift):
        self.moveCursor(QTextCursor.Down, self.__get_move_mode(shift))

    def stdkey_tab(self):
        self.insert_text(" "*4)

    def stdkey_home(self, shift, prompt_pos=None):
        move_mode = self.__get_move_mode(shift)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock, move_mode)
        if prompt_pos is not None:
            cursor.setPosition(prompt_pos, move_mode)
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
        
    def set_base_format(self, base_format):
        self.base_format = base_format
        
    def get_format(self):
        return self.current_format
        
    def set_style(self):
        """
        Set font style with the following attributes:
        'foreground_color', 'background_color', 'italic', 'bold' and 'underline'
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


class ConsoleBaseWidget(TextEditBaseWidget):
    """Console base widget"""
    BRACE_MATCHING_SCOPE = ('sol', 'eol')
    COLOR_PATTERN = re.compile('\x01?\x1b\[(.*?)m\x02?')
    
    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)

        self.setMaximumBlockCount(300)

        # ANSI escape code handler
        self.ansi_handler = QtANSIEscapeCodeHandler()
                
        # Disable undo/redo (nonsense for a console widget...):
        self.setUndoRedoEnabled(False)
        
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     lambda user_id, text:
                     self.emit(SIGNAL('completion_widget_activated(QString)'),
                               text))
        self.default_format = QTextCharFormat()
        self.prompt_format = QTextCharFormat()
        self.error_format = QTextCharFormat()
        self.traceback_link_format = QTextCharFormat()
        self.formats = {self.default_format: 'DEFAULT_STYLE',
                        self.prompt_format: 'PROMPT_STYLE',
                        self.error_format: 'ERROR_STYLE',
                        self.traceback_link_format: 'TRACEBACK_LINK_STYLE'}
        self.set_pythonshell_font()
        self.setMouseTracking(True)
        
    def remove_margins(self):
        """Suppressing Scintilla margins"""
        #TODO: implement this method
        pass

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
        self.textCursor().insertText(text, self.default_format)
        
    def paste(self):
        """Reimplement Qt method"""
        if self.hasSelectedText():
            self.removeSelectedText()
        self.insert_text(QApplication.clipboard().text())
        
    def append_text_to_shell(self, text, error, prompt):
        """
        Append text to Python shell
        In a way, this method overrides the method 'insert_text' when text is 
        inserted at the end of the text widget for a Python shell
        
        Handles error messages and show blue underlined links
        Handles ANSI color sequences
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        if error:
            for text in text.splitlines(True):
                if text.startswith('  File') \
                and not text.startswith('  File "<'):
                    # Show error links in blue underlined text
                    cursor.insertText('  ', self.default_format)
                    cursor.insertText(text[2:], self.traceback_link_format)
                else:
                    # Show error messages in red
                    cursor.insertText(text, self.error_format)
        elif prompt:
            # Show prompt in green
            cursor.insertText(text, self.prompt_format)
        else:
            # Show other outputs in black
            last_end = 0
            for match in self.COLOR_PATTERN.finditer(text):
                cursor.insertText(text[last_end:match.start()],
                                  self.default_format)
                last_end = match.end()
                for code in [int(_c) for _c in match.group(1).split(';')]:
                    self.ansi_handler.set_code(code)
                self.default_format = self.ansi_handler.get_format()
            cursor.insertText(text[last_end:], self.default_format)
#            # Slower alternative:
#            segments = self.COLOR_PATTERN.split(text)
#            cursor.insertText(segments.pop(0), self.default_format)
#            if segments:
#                for ansi_tags, text in zip(segments[::2], segments[1::2]):
#                    for ansi_tag in ansi_tags.split(';'):
#                        self.ansi_handler.set_code(int(ansi_tag))
#                    self.default_format = self.ansi_handler.get_format()
#                    cursor.insertText(text, self.default_format)
        self.set_cursor_position('eof')
        self.setCurrentCharFormat(self.default_format)
    
    def set_pythonshell_font(self, font=None):
        """Python Shell only"""
        if font is None:
            font = QFont()

        for format in self.formats:
            format.setFont(font)
        
        getstyleconf = lambda name, prop: CONF.get('shell_appearance',
                                                   name+'/'+prop)
        for format, stylestr in self.formats.items():
            foreground = getstyleconf(stylestr, 'foregroundcolor')
            format.setForeground(QColor(foreground))
            background = getstyleconf(stylestr, 'backgroundcolor')
            format.setBackground(QColor(background))
            font = format.font()
            font.setBold(getstyleconf(stylestr, 'bold'))
            font.setItalic(getstyleconf(stylestr, 'italic'))
            font.setUnderline(getstyleconf(stylestr, 'underline'))
            format.setFont(font)
            
        self.ansi_handler.set_base_format(self.default_format)
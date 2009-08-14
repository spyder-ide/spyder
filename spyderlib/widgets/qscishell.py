# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Terminal widget based on QScintilla"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os, time
import os.path as osp

from PyQt4.QtGui import QMenu, QApplication, QCursor, QToolTip
from PyQt4.QtCore import (Qt, QString, QCoreApplication, SIGNAL, pyqtProperty,
                          QStringList)
from PyQt4.Qsci import QsciScintilla

# For debugging purpose:
STDOUT = sys.stdout
STDERR = sys.stderr

# Local import
from spyderlib import __version__, encoding
from spyderlib.config import CONF, get_icon
from spyderlib.dochelpers import getobj
from spyderlib.qthelpers import (translate, keybinding, create_action,
                                 add_actions, restore_keyevent)
from spyderlib.widgets.qscibase import QsciBase
from spyderlib.widgets.shellhelpers import get_error_match


HISTORY_FILENAMES = []


class QsciShellBase(QsciBase):
    """
    Shell based on QScintilla
    """
    INITHISTORY = None
    SEPARATOR = None
    
    def __init__(self, parent, history_filename, debug=False, profile=False):
        """
        parent : specifies the parent widget
        """
        QsciBase.__init__(self, parent)
        
        # Prompt position: tuple (line, index)
        self.current_prompt_pos = None
        self.new_input_line = True
        
        # History
        self.histidx = None
        self.hist_wholeline = False
        assert isinstance(history_filename, (str, unicode))
        self.history_filename = history_filename
        self.history = self.load_history()
        
        # Context menu
        self.menu = None
        self.setup_context_menu()

        # Debug mode
        self.debug = debug

        # Simple profiling test
        self.profile = profile
        
        # write/flush
        self.__buffer = []
        self.__timestamp = 0.0
        
        # Mouse cursor
        self.__cursor_changed = False

        # Give focus to widget
        self.setFocus()
                
    def setup_scintilla(self):
        """Reimplement QsciBase method"""
        QsciBase.setup_scintilla(self)
        
        # Wrapping
        if CONF.get('shell', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
        # Caret
        self.setCaretForegroundColor(Qt.darkGray)
        self.setCaretWidth(2)
        
        # Suppressing Scintilla margins
        self.remove_margins()
        
        # Lexer
        self.default_style = 0
        self.prompt_style = 1
        self.error_style = 2
        self.traceback_link_style = 3
        
    def set_wrap_mode(self, enable):
        """
        Enable/disable wrap mode
        Reimplement QsciBase method: WrapWord -> WrapCharacter
        """
        self.setWrapMode(QsciScintilla.WrapCharacter if enable
                         else QsciScintilla.WrapNone)

    def setUndoRedoEnabled(self, state):
        """Fake Qt method (QTextEdit)"""
        pass

    def set_font(self, font):
        """Set shell font"""
        family = str(font.family())
        size = font.pointSize()
        for style in [self.default_style, self.error_style,
                      self.prompt_style, self.traceback_link_style]:
            self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, style, family)
            self.SendScintilla(QsciScintilla.SCI_STYLESETSIZE, style, size)
        getstyleconf = lambda name, prop: CONF.get('scintilla', name+'/'+prop)
        for stylestr in ['default_style', 'error_style',
                         'prompt_style', 'traceback_link_style']:
            style = getattr(self, stylestr)
            self.SendScintilla(QsciScintilla.SCI_STYLESETFORE,
                               style, getstyleconf(stylestr, 'foregroundcolor'))
            self.SendScintilla(QsciScintilla.SCI_STYLESETBACK,
                               style, getstyleconf(stylestr, 'backgroundcolor'))
            self.SendScintilla(QsciScintilla.SCI_STYLESETBOLD,
                               style, getstyleconf(stylestr, 'bold'))
            self.SendScintilla(QsciScintilla.SCI_STYLESETITALIC,
                               style, getstyleconf(stylestr, 'italic'))
            self.SendScintilla(QsciScintilla.SCI_STYLESETUNDERLINE,
                               style, getstyleconf(stylestr, 'underline'))


    #------ Context menu
    def setup_context_menu(self):
        """Setup shell context menu"""
        self.menu = QMenu(self)
        self.cut_action = create_action(self,
                           translate("InteractiveShell", "Cut"),
                           shortcut=keybinding('Cut'),
                           icon=get_icon('editcut.png'), triggered=self.cut)
        self.copy_action = create_action(self,
                           translate("InteractiveShell", "Copy"),
                           shortcut=keybinding('Copy'),
                           icon=get_icon('editcopy.png'), triggered=self.copy)
        self.copy_without_prompts_action = create_action(self,
                           translate("InteractiveShell",
                                     "Copy without prompts"),
                           icon=get_icon('copywop.png'),
                           triggered=self.copy_without_prompts)
        paste_action = create_action(self,
                           translate("InteractiveShell", "Paste"),
                           shortcut=keybinding('Paste'),
                           icon=get_icon('editpaste.png'), triggered=self.paste)
        add_actions(self.menu, (self.cut_action, self.copy_action,
                                self.copy_without_prompts_action,
                                paste_action) )
          
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        state = self.hasSelectedText()
        self.copy_action.setEnabled(state)
        self.copy_without_prompts_action.setEnabled(state)
        self.cut_action.setEnabled(state)
        self.menu.popup(event.globalPos())
        event.accept()        
        
        
    #------ Input buffer
    def get_current_line_to_cursor(self):
        line, index = self.getCursorPosition()
        pline, pindex = self.current_prompt_pos
        self.setSelection(pline, pindex, line, index)
        selected_text = unicode(self.selectedText())
        self.clear_selection()
        return selected_text
    
    def _select_input(self):
        """Select current line (without selecting console prompt)"""
        line, index = self.get_end_pos()
        pline, pindex = self.current_prompt_pos
        self.setSelection(pline, pindex, line, index)
            
    def clear_line(self):
        """Clear current line (without clearing console prompt)"""
        self._select_input()
        self.removeSelectedText()

    # The buffer being edited
    def _set_input_buffer(self, text):
        """Set input buffer"""
        self._select_input()
        self.replace(text)
        self.move_cursor_to_end()

    def _get_input_buffer(self):
        """Return input buffer"""
        self._select_input()
        input_buffer = self.selectedText()
        self.clear_selection()
        input_buffer = input_buffer.replace(os.linesep, '\n')
        return unicode(input_buffer)

    input_buffer = pyqtProperty("QString", _get_input_buffer, _set_input_buffer)
        
        
    #------ Prompt
    def new_prompt(self, prompt):
        """
        Print a new prompt and save its (line, index) position
        """
        self.write(prompt, prompt=True)
        # now we update our cursor giving end of prompt
        self.current_prompt_pos = self.getCursorPosition()
        self.ensureCursorVisible()
        
    def check_selection(self):
        """
        Check if selected text is r/w,
        otherwise remove read-only parts of selection
        """
        if self.current_prompt_pos is None:
            self.move_cursor_to_end()
            return
        line_from, index_from, line_to, index_to = self.getSelection()
        pline, pindex = self.current_prompt_pos
        if line_from < pline or \
           (line_from == pline and index_from < pindex):
            self.setSelection(pline, pindex, line_to, index_to)
        
        
    #------ Copy / Keyboard interrupt
    def copy(self):
        """Copy text to clipboard... or keyboard interrupt"""
        if self.hasSelectedText():
            QApplication.clipboard().setText( unicode(self.selectedText()) )
        else:
            self.emit(SIGNAL("keyboard_interrupt()"))
            
    def copy_without_prompts(self):
        """Copy text to clipboard without prompts"""
        text = unicode(self.selectedText()).replace('>>> ', '').strip()
        QApplication.clipboard().setText(text)

    def cut(self):
        """Cut text"""
        self.check_selection()
        if self.hasSelectedText():
            QsciScintilla.cut(self)

    def delete(self):
        """Remove selected text"""
        self.check_selection()
        if self.hasSelectedText():
            QsciScintilla.removeSelectedText(self)
        
        
    #------ Basic keypress event handler
    def on_enter(self, command):
        """on_enter"""
        self.emit(SIGNAL("execute(QString)"), command)
        self.add_to_history(command)
        self.new_input_line = True
        
    def on_new_line(self):
        """On new input line"""
        self.move_cursor_to_end()
        self.current_prompt_pos = self.getCursorPosition()
        self.new_input_line = False
        
    def paste(self):
        """Reimplement QScintilla method"""
        if self.new_input_line:
            self.on_new_line()
        QsciBase.paste(self)
        
    def keyPressEvent(self, event):
        """
        Reimplement Qt Method
        Basic keypress event handler
        (reimplemented in InteractiveShell to add more sophisticated features)
        """
        # Copy must be done first to be able to copy read-only text parts
        # (otherwise, right below, we would remove selection
        #  if not on current line)
        ctrl = event.modifiers() & Qt.ControlModifier
        if event.key() == Qt.Key_C and ctrl:
            self.copy()
            event.accept()
            return
        
        if self.new_input_line and ( len(event.text()) or event.key() in \
           (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right) ):
            self.on_new_line()
            
        self.process_keyevent(event)
        
    def process_keyevent(self, event):
        """Process keypress event"""
        event, text, key, ctrl, shift = restore_keyevent(event)
        
        last_line = self.lines()-1
        
        # Is cursor on the last line? and after prompt?
        if len(text):
            if self.hasSelectedText():
                self.check_selection()
            line, index = self.getCursorPosition()
            _pline, pindex = self.current_prompt_pos
            if line != last_line:
                # Moving cursor to the end of the last line
                self.move_cursor_to_end()
            elif index < pindex:
                # Moving cursor after prompt
                self.setCursorPosition(line, pindex)

        line, index = self.getCursorPosition()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.is_cursor_on_last_line():
                if self.isListActive():
                    self.SendScintilla(QsciScintilla.SCI_NEWLINE)
                else:
                    self.append('\n')
                    command = self.input_buffer
                    self.on_enter(command)
                    self.flush()
            # add and run selection
            else:
                text = self.selectedText()
                self.insert_text(text, at_end=True)
            event.accept()
            
        elif key == Qt.Key_Delete:
            if self.hasSelectedText():
                self.check_selection()
                self.removeSelectedText()
            elif self.is_cursor_on_last_line():
                self.SendScintilla(QsciScintilla.SCI_CLEAR)
            event.accept()
            
        elif key == Qt.Key_Backspace:
            self._key_backspace(line, index)
            event.accept()
            
        elif key == Qt.Key_Tab:
            self._key_tab()
            event.accept()

        elif key == Qt.Key_Left:
            event.accept()
            if self.current_prompt_pos == (line, index):
                # Avoid moving cursor on prompt
                return
            if shift:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDLEFTEXTEND)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARLEFTEXTEND)
            else:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDLEFT)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARLEFT)
                
        elif key == Qt.Key_Right:
            event.accept()
            if self.is_cursor_at_end():
                return
            if shift:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDRIGHTEXTEND)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARRIGHTEXTEND)
            else:
                if ctrl:
                    self.SendScintilla(QsciScintilla.SCI_WORDRIGHT)
                else:
                    self.SendScintilla(QsciScintilla.SCI_CHARRIGHT)

        elif (key == Qt.Key_Home) or ((key == Qt.Key_Up) and ctrl):
            self._key_home()
            event.accept()

        elif (key == Qt.Key_End) or ((key == Qt.Key_Down) and ctrl):
            self._key_end()
            event.accept()

        elif key == Qt.Key_Up:
            if line != last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() > self.getpointy(prompt=True):
                self.SendScintilla(QsciScintilla.SCI_LINEUP)
            else:
                self.browse_history(backward=True)
            event.accept()
                
        elif key == Qt.Key_Down:
            if line != last_line:
                self.move_cursor_to_end()
            if self.isListActive() or \
               self.getpointy() < self.getpointy(end=True):
                self.SendScintilla(QsciScintilla.SCI_LINEDOWN)
            else:
                self.browse_history(backward=False)
            event.accept()
            
        elif key == Qt.Key_PageUp:
            self._key_pageup()
            event.accept()
            
        elif key == Qt.Key_PageDown:
            self._key_pagedown()
            event.accept()

        elif key == Qt.Key_Escape:
            self._key_escape()
            event.accept()
                
        elif key == Qt.Key_V and ctrl:
            self.paste()
            event.accept()
            
        elif key == Qt.Key_X and ctrl:
            self.cut()
            event.accept()
            
        elif key == Qt.Key_Z and ctrl:
            self.undo()
            event.accept()
            
        elif key == Qt.Key_Y and ctrl:
            self.redo()
            event.accept()
                
        elif key == Qt.Key_Question and not self.hasSelectedText():
            self._key_question(text)
            event.accept()
            
        elif key == Qt.Key_ParenLeft and not self.hasSelectedText():
            self._key_parenleft(text)
            event.accept()
            
        elif key == Qt.Key_Period and not self.hasSelectedText():
            self._key_period(text)
            event.accept()

        elif ((key == Qt.Key_Plus) and ctrl) \
             or ((key==Qt.Key_Equal) and shift and ctrl):
            self.zoomIn()
            event.accept()

        elif (key == Qt.Key_Minus) and ctrl:
            self.zoomOut()
            event.accept()

        elif text.length():
            self.hist_wholeline = False
            QsciScintilla.keyPressEvent(self, event)
            self._key_other()
            event.accept()
                
        else:
            # Let the parent widget handle the key press event
            event.ignore()

        
        if QToolTip.isVisible():
            # Hide calltip when necessary (this is handled here because
            # QScintilla does not support user-defined calltips)
            _, index = self.getCursorPosition() # need the new index
            try:
                if (self.text(line)[self.calltip_index] not in ['?','(']) or \
                   index < self.calltip_index or \
                   key in (Qt.Key_ParenRight, Qt.Key_Period, Qt.Key_Tab):
                    QToolTip.hideText()
            except (IndexError, TypeError):
                QToolTip.hideText()
            
                
    #------ Key handlers
    def _key_other(self):
        raise NotImplementedError
    def _key_backspace(self):
        raise NotImplementedError
    def _key_tab(self):
        raise NotImplementedError
    def _key_home(self):
        raise NotImplementedError
    def _key_end(self):
        raise NotImplementedError
    def _key_pageup(self):
        raise NotImplementedError
    def _key_pagedown(self):
        raise NotImplementedError
    def _key_escape(self):
        raise NotImplementedError
    def _key_question(self, text):
        raise NotImplementedError
    def _key_parenleft(self, text):
        raise NotImplementedError
    def _key_period(self, text):
        raise NotImplementedError

        
    #------ History Management
    def load_history(self):
        """Load history from a .py file in user home directory"""
        if osp.isfile(self.history_filename):
            rawhistory, _ = encoding.readlines(self.history_filename)
            rawhistory = [line.replace('\n', '') for line in rawhistory]
            if rawhistory[1] != self.INITHISTORY[1]:
                rawhistory = self.INITHISTORY
        else:
            rawhistory = self.INITHISTORY
        history = [line for line in rawhistory \
                   if line and not line.startswith('#')]

        # Truncating history to X entries:
        while len(history) >= CONF.get('historylog', 'max_entries'):
            del history[0]
            while rawhistory[0].startswith('#'):
                del rawhistory[0]
            del rawhistory[0]
        # Saving truncated history:
        encoding.writelines(rawhistory, self.history_filename)
        return history
        
    def add_to_history(self, command):
        """Add command to history"""
        command = unicode(command)
        if command in ['', '\n'] or command.startswith('Traceback'):
            return
        if command.endswith('\n'):
            command = command[:-1]
        self.histidx = None
        if len(self.history)>0 and self.history[-1] == command:
            return
        self.history.append(command)
        text = os.linesep + command
        
        # When the first entry will be written in history file,
        # the separator will be append first:
        if self.history_filename not in HISTORY_FILENAMES:
            HISTORY_FILENAMES.append(self.history_filename)
            text = self.SEPARATOR + text
            
        encoding.write(text, self.history_filename, mode='ab')
        self.emit(SIGNAL('append_to_history(QString,QString)'),
                  self.history_filename, text)
        
    def browse_history(self, backward):
        """Browse history"""
        line, index = self.getCursorPosition()
        if index < self.text(line).length() and self.hist_wholeline:
            self.hist_wholeline = False
        tocursor = self.get_current_line_to_cursor()
        text, self.histidx = self.__find_in_history(tocursor,
                                                    self.histidx, backward)
        if text is not None:
            if self.hist_wholeline:
                self.clear_line()
                self.insert_text(text)
            else:
                # Removing text from cursor to the end of the line
                self.setSelection(line, index, line, self.lineLength(line))
                self.removeSelectedText()
                # Inserting history text
                self.insert_text(text)
                self.setCursorPosition(line, index)

    def __find_in_history(self, tocursor, start_idx, backward):
        """Find text 'tocursor' in history, from index 'start_idx'"""
        if start_idx is None:
            start_idx = len(self.history)
        # Finding text in history
        step = -1 if backward else 1
        idx = start_idx
        if len(tocursor) == 0 or self.hist_wholeline:
            idx += step
            if idx >= len(self.history) or len(self.history) == 0:
                return "", len(self.history)
            elif idx < 0:
                idx = 0
            self.hist_wholeline = True
            return self.history[idx], idx
        else:
            for index in xrange(len(self.history)):
                idx = (start_idx+step*(index+1)) % len(self.history)
                entry = self.history[idx]
                if entry.startswith(tocursor):
                    return entry[len(tocursor):], idx
            else:
                return None, start_idx
    
    
    #------ Simulation standards input/output
    def write_error(self, text):
        """Simulate stderr"""
        self.flush()
        self.write(text, flush=True, error=True)
        if self.debug:
            STDERR.write(text)

    def write(self, text, flush=False, error=False, prompt=False):
        """Simulate stdout and stderr"""
        if prompt:
            self.flush()
        if isinstance(text, QString):
            # This test is useful to discriminate QStrings from decoded str
            text = unicode(text)
        self.__buffer.append(text)
        ts = time.time()
        if flush or ts-self.__timestamp > 0.05 or prompt:
            self.flush(error=error, prompt=prompt)
            self.__timestamp = ts

    def flush(self, error=False, prompt=False):
        """Flush buffer, write text to console"""
        text = "".join(self.__buffer)
        self.__buffer = []
        self.insert_text(text, at_end=True, error=error, prompt=prompt)
        QCoreApplication.processEvents()
        self.repaint()
        # Clear input buffer:
        self.new_input_line = True
        
        
    #------ Utilities
    def getpointy(self, cursor=True, end=False, prompt=False):
        """Return point y of cursor, end or prompt"""
        line, index = self.getCursorPosition()
        if end:
            line, index = self.get_end_pos()
        elif prompt:
            index = 0
        pos = self.position_from_lineindex(line, index)
        return self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION,
                                  0, pos)


    #------ Text Insertion
    def insert_text(self, text, at_end=False, error=False, prompt=False):
        """
        Insert text at the current cursor position
        or at the end of the command line
        """
        if error and text.startswith('  File "<'):
            # Avoid printing 'File <console> [...]' which is related to the
            # code.InteractiveConsole Python interpreter emulation
            return
        if at_end:
            # Insert text at the end of the command line
            self.move_cursor_to_end()
            self.SendScintilla(QsciScintilla.SCI_STARTSTYLING,
                               len(unicode(self.text()).encode('utf-8')), 0xFF)
            if error:
                for text in text.splitlines(True):
                    if text.startswith('  File'):
                        # Show error links in blue underlined text
                        self.append('  ')
                        self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                           2, self.default_style)
                        self.append(text[2:])
                        self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                           len(text)-2,
                                           self.traceback_link_style)
                    else:
                        # Show error messages in red
                        self.append(text)
                        self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                           len(text),
                                           self.error_style)
            elif prompt:
                # Show prompt in green
                self.append(text)
                self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                   len(text), self.prompt_style)
            else:
                # Show other outputs in black
                self.append(text)
                self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                   len(text), self.default_style)
            self.move_cursor_to_end()
        else:
            # Insert text at current cursor position
            line, col = self.getCursorPosition()
            self.insertAt(text, line, col)
            self.setCursorPosition(line, col + len(unicode(text)))

            
    #------ Re-implemented Qt Methods
    def focusNextPrevChild(self, next):
        """
        Reimplemented to stop Tab moving to the next window
        """
        if next:
            return False
        return QsciScintilla.focusNextPrevChild(self, next)
        
    def mousePressEvent(self, event):
        """
        Re-implemented to handle the mouse press event.
        event: the mouse press event (QMouseEvent)
        """
        if event.button() == Qt.MidButton:
            self.setFocus()
            self.paste()
            event.accept()
        else:
            QsciScintilla.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """Go to error"""
        QsciScintilla.mouseReleaseEvent(self, event)            
        text = unicode(self.text(self.lineAt(event.pos())))
        if get_error_match(text) and not self.hasSelectedText():
            self.emit(SIGNAL("go_to_error(QString)"), text)

    def mouseMoveEvent(self, event):
        """Show Pointing Hand Cursor on error messages"""
        text = unicode(self.text(self.lineAt(event.pos())))
        if get_error_match(text):
            if not self.__cursor_changed:
                QApplication.setOverrideCursor(QCursor(Qt.PointingHandCursor))
                self.__cursor_changed = True
            event.accept()
            return
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False
        QsciScintilla.mouseMoveEvent(self, event)
        
    def leaveEvent(self, event):
        """If cursor has not been restored yet, do it now"""
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False
        QsciScintilla.leaveEvent(self, event)

    
    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Drag and Drop - Enter event"""
        event.setAccepted(event.mimeData().hasFormat("text/plain"))

    def dragMoveEvent(self, event):
        """Drag and Drop - Move event"""
        if (event.mimeData().hasFormat("text/plain")):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Drag and Drop - Drop event"""
        if(event.mimeData().hasFormat("text/plain")):
            text = event.mimeData().text()
            self.insert_text(text, at_end=True)
            self.setFocus()
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()


class QsciPythonShell(QsciShellBase):
    """
    Python shell based on QScintilla
    """
    INITHISTORY = ['# -*- coding: utf-8 -*-',
                   '# *** Spyder v%s -- History log ***' % __version__,]
    SEPARATOR = '%s##---(%s)---' % (os.linesep*2, time.ctime())
    
    def __init__(self, parent, history_filename, debug=False, profile=False):
        QsciShellBase.__init__(self, parent, history_filename, debug, profile)
        
        self.docviewer = None
        
        # Code completion / calltips
        self.codecompletion = True
        self.calltips = True
        self.completion_chars = 0
        self.calltip_index = None
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     self.completion_list_selected)
            
        # Allow raw_input support:
        self.input_loop = None
        self.input_mode = False
        
        
    def set_codecompletion(self, state):
        """Set code completion state"""
        self.codecompletion = state        
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state
            
                
    #------ Key handlers
    def _key_other(self):
        """1 character key"""
        if self.isListActive():
            self.completion_chars += 1                
                
    def _key_backspace(self, line, index):
        """Action for Backspace key"""
        if self.hasSelectedText():
            self.check_selection()
            self.removeSelectedText()
        elif self.current_prompt_pos == (line, index):
            # Avoid deleting prompt
            return
        elif self.is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
            if self.isListActive():
                self.completion_chars -= 1
                
    def _key_tab(self):
        """Action for TAB key"""
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_TAB)
        elif self.is_cursor_on_last_line():
            buf = self.get_current_line_to_cursor()
            empty_line = not buf.strip()
            if empty_line:
                self.SendScintilla(QsciScintilla.SCI_TAB)
            elif buf.endswith('.'):
                self.show_code_completion(self.get_last_obj())
            elif buf[-1] in ['"', "'"]:
                self.show_file_completion()
                
    def _key_home(self):
        """Action for Home key"""
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_VCHOME)
        elif self.is_cursor_on_last_line():
            self.setCursorPosition(*self.current_prompt_pos)
                
    def _key_end(self):
        """Action for End key"""
        if self.isListActive():
            self.SendScintilla(QsciScintilla.SCI_LINEEND)
        elif self.is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_LINEEND)
                
    def _key_pageup(self):
        """Action for PageUp key"""
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(QsciScintilla.SCI_PAGEUP)
    
    def _key_pagedown(self):
        """Action for PageDown key"""
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(QsciScintilla.SCI_PAGEDOWN)
                
    def _key_escape(self):
        """Action for ESCAPE key"""
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(QsciScintilla.SCI_CANCEL)
        else:
            self.clear_line()
                
    def _key_question(self, text):
        """Action for '?'"""
        if self.get_current_line_to_cursor():
            self.show_docstring(self.get_last_obj())
            _, self.calltip_index = self.getCursorPosition()
        self.insert_text(text)
        # In case calltip and completion are shown at the same time:
        if self.isListActive():
            self.completion_chars += 1
                
    def _key_parenleft(self, text):
        """Action for '('"""
        self.cancelList()
        if self.get_current_line_to_cursor():
            self.show_docstring(self.get_last_obj(), call=True)
            _, self.calltip_index = self.getCursorPosition()
        self.insert_text(text)
        
    def _key_period(self, text):
        """Action for '.'"""
        # Enable auto-completion only if last token isn't a float
        self.insert_text(text)
        last_obj = self.get_last_obj()
        if last_obj and not last_obj[-1].isdigit():
            self.show_code_completion(last_obj)

    
  
    #------ Code Completion / Calltips
    def completion_list_selected(self, userlist_id, seltxt):
        """
        Private slot to handle the selection from the completion list
        userlist_id: ID of the user list (should be 1) (integer)
        seltxt: selected text (QString)
        """
        if userlist_id == 1:
            cline, cindex = self.getCursorPosition()
            self.setSelection(cline, cindex-self.completion_chars+1,
                              cline, cindex)
            self.removeSelectedText()
            seltxt = unicode(seltxt)
            self.insert_text(seltxt)
            self.completion_chars = 0

    def show_completion_list(self, completions, text):
        """Private method to display the possible completions"""
        if len(completions) == 0:
            return
        if len(completions) > 1:
            self.showUserList(1, QStringList(sorted(completions)))
            self.completion_chars = 1
        else:
            txt = completions[0]
            if text != "":
                txt = txt.replace(text, "")
            self.insert_text(txt)
            self.completion_chars = 0

    def show_file_completion(self):
        """Display a completion list for files and directories"""
        cwd = os.getcwdu()
        self.show_completion_list(os.listdir(cwd), cwd)

    # Methods implemented in child class:
    # (e.g. InteractiveShell)
    def get_dir(self, objtxt):
        """Return dir(object)"""
        raise NotImplementedError
    def iscallable(self, objtxt):
        """Is object callable?"""
        raise NotImplementedError
    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        raise NotImplementedError
    def get__doc__(self, objtxt):
        """Get object __doc__"""
        raise NotImplementedError
    def get_doc(self, objtxt):
        """Get object documentation"""
        raise NotImplementedError
    def get_source(self, objtxt):
        """Get object source"""
        raise NotImplementedError
        
    def show_code_completion(self, text):
        """Display a completion list based on the last token"""
        if not self.codecompletion:
            return
        text = unicode(text) # Useful only for ExternalShellBase
        objdir = self.get_dir(text)
        if objdir:
            self.show_completion_list(objdir, 'dir(%s)' % text) 
    
    def show_docstring(self, text, call=False):
        """Show docstring or arguments"""
        if not self.calltips:
            return
        
        text = unicode(text) # Useful only for ExternalShellBase
        done = False
        if (self.docviewer is not None) and \
           (self.docviewer.dockwidget.isVisible()):
            # DocViewer widget exists and is visible
            self.docviewer.refresh(text)
            self.setFocus() # if docviewer was not at top level, raising it to
                            # top will automatically give it focus because of
                            # the visibility_changed signal, so we must give
                            # focus back to shell
            if call:
                # Display argument list if this is function call
                iscallable = self.iscallable(text)
                if iscallable is not None: # Useful only for ExternalShellBase
                    if iscallable:
                        arglist = self.get_arglist(text)
                        if arglist:
                            done = True
                            self.show_calltip(self.tr("Arguments"),
                                              arglist, '#129625')
                    else:
                        done = True
                        self.show_calltip(self.tr("Warning"),
                                          self.tr("Object `%1` is not callable"
                                                  " (i.e. not a function, "
                                                  "a method or a class "
                                                  "constructor)").arg(text),
                                          color='#FF0000')
        if not done:
            doc = self.get__doc__(text)
            if doc is None: # Useful only for ExternalShellBase
                return
            self.show_calltip(self.tr("Documentation"), doc)
        
        
    #------ Miscellanous
    def get_last_obj(self, last=False):
        """
        Return the last valid object on the current line
        """
        return getobj(self.get_current_line_to_cursor(), last=last)
        
    def set_docviewer(self, docviewer):
        """Set DocViewer DockWidget reference"""
        self.docviewer = docviewer
        self.docviewer.set_shell(self)


class QsciTerminal(QsciShellBase):
    """
    Terminal based on QScintilla
    """
    COM = 'rem' if os.name == 'nt' else '#'
    INITHISTORY = ['%s *** Spyder v%s -- History log ***' % (COM, __version__),
                   COM,]
    SEPARATOR = '%s%s ---(%s)---' % (os.linesep*2, COM, time.ctime())
    
    def __init__(self, parent, history_filename, debug=False, profile=False):
        QsciShellBase.__init__(self, parent, history_filename, debug, profile)
        
    #------ Key handlers
    def _key_other(self):
        """1 character key"""
        pass
                
    def _key_backspace(self, line, index):
        """Action for Backspace key"""
        if self.hasSelectedText():
            self.check_selection()
            self.removeSelectedText()
        elif self.current_prompt_pos == (line, index):
            # Avoid deleting prompt
            return
        elif self.is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_DELETEBACK)
                
    def _key_tab(self):
        """Action for TAB key"""
        if self.is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_TAB)
                
    def _key_home(self):
        """Action for Home key"""
        if self.is_cursor_on_last_line():
            self.setCursorPosition(*self.current_prompt_pos)
                
    def _key_end(self):
        """Action for End key"""
        if self.is_cursor_on_last_line():
            self.SendScintilla(QsciScintilla.SCI_LINEEND)
                
    def _key_pageup(self):
        """Action for PageUp key"""
        pass
    
    def _key_pagedown(self):
        """Action for PageDown key"""
        pass
                
    def _key_escape(self):
        """Action for ESCAPE key"""
        self.clear_line()
                
    def _key_question(self, text):
        """Action for '?'"""
        self.insert_text(text)
                
    def _key_parenleft(self, text):
        """Action for '('"""
        self.insert_text(text)
        
    def _key_period(self, text):
        """Action for '.'"""
        self.insert_text(text)

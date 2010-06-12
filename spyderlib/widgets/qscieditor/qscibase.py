# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""QScintilla base class"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, re
from PyQt4.QtGui import QToolTip
from PyQt4.QtCore import QPoint, SIGNAL, QString, QRegExp, Qt, QStringList
try:
    from PyQt4.Qsci import QsciScintilla
except ImportError, e:
    raise ImportError, str(e) + \
        "\nspyderlib's code editor features are based on QScintilla2\n" + \
        "(http://www.riverbankcomputing.co.uk/software/qscintilla)"

# Local imports
from spyderlib.config import CONF, get_font

# For debugging purpose:
STDOUT = sys.stdout


class TextEditBaseWidget(QsciScintilla):
    """
    Text edit base widget
    """
    def __init__(self, parent=None):
        QsciScintilla.__init__(self, parent)
        self.setup()
        
        # Code completion / calltips
        self.codecompletion_auto = False
        self.codecompletion_enter = False
        self.calltips = True
        self.completion_text = ""
        self.calltip_position = None
        self.connect(self, SIGNAL('userListActivated(int, const QString)'),
                     lambda user_id, text: self.completion_list_selected(text))
        
    #-----Widget setup and options
    def setup(self):
        """Configure Scintilla"""
        # UTF-8
        self.setUtf8(True)
        
        # Indentation
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(4)
        self.setTabIndents(True)
        self.setBackspaceUnindents(True)
        self.setTabWidth(4)
        
        # Enable brace matching
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(Qt.yellow)
        
        # Calltips
        self.calltip_size = CONF.get('shell_appearance', 'calltips/size')
        self.calltip_font = get_font('shell_appearance', 'calltips')

    def set_codecompletion_auto(self, state):
        """Set code completion state"""
        self.codecompletion_auto = state        
        
    def set_codecompletion_enter(self, state):
        """Enable Enter key to select completion"""
        self.codecompletion_enter = state
        
    def set_calltips(self, state):
        """Set calltips state"""
        self.calltips = state

    def set_caret(self, color=None, width=None):
        """Set caret properties"""
        if color is not None:
            self.setCaretForegroundColor(color)
        if width is not None:
            self.setCaretWidth(width)
            
    def set_wrap_mode(self, mode=None):
        """
        Set wrap mode
        Valid *mode* values: None, 'word', 'character'
        """
        wrap_mode = QsciScintilla.WrapNone
        if mode == 'word':
            wrap_mode = QsciScintilla.WrapWord
        elif mode == 'character':
            wrap_mode = QsciScintilla.WrapCharacter
        self.setWrapMode(wrap_mode)

    def toggle_wrap_mode(self, enable):
        """Enable/disable wrap mode"""
        self.set_wrap_mode('word' if enable else None)
        
        
    #------Positions, coordinates (cursor, EOF, ...)
    def is_position_sup(self, pos1, pos2):
        """Return True is pos1 > pos2"""
        line1, index1 = pos1
        line2, index2 = pos2
        return line1 > line2 or (line1 == line2 and index1 > index2)
        
    def is_position_inf(self, pos1, pos2):
        """Return True is pos1 < pos2"""
        line1, index1 = pos1
        line2, index2 = pos2
        return line1 < line2 or (line1 == line2 and index1 < index2)
        
    def get_position(self, position):
        if position == 'cursor':
            return self.getCursorPosition()
        elif position == 'sol':
            line, _index = self.getCursorPosition()
            return (line, 0)
        elif position == 'eol':
            line, _index = self.getCursorPosition()
            return (line, self.__get_line_end_index(line))
        elif position == 'eof':
            line = self.lines() - 1
            return (line, self.text(line).length())
        elif position == 'sof':
            return (0, 0)
        else:
            # Assuming that input argument was already a position
            return position
        
    def get_coordinates(self, position):
        line, index = self.get_position(position)
        return self.__get_coordinates_from_lineindex(line, index)
    
    def get_cursor_line_column(self):
        """Return cursor (line, column) numbers"""
        return self.getCursorPosition()
        
    def get_cursor_line_number(self):
        line, _index = self.getCursorPosition()
        return line+1

    def set_cursor_position(self, position):
        line, index = self.get_position(position)
        self.setCursorPosition(line, index)
        self.ensureCursorVisible()
        
    def move_cursor(self, chars=0):
        """Move cursor to left or right (unit: characters)"""
        line, index = self.getCursorPosition()
        index = min([0, max([self.lineLength(line), index+chars])])
        self.setCursorPosition(line, index)

    def is_cursor_on_first_line(self):
        """Return True if cursor is on the first line"""
        cline, _ = self.getCursorPosition()
        return cline == 0

    def is_cursor_on_last_line(self):
        """Return True if cursor is on the last line"""
        cline, _ = self.getCursorPosition()
        return cline == self.lines() - 1

    def is_cursor_at_end(self):
        """Return True if cursor is at the end of text"""
        cline, cindex = self.getCursorPosition()
        return (cline, cindex) == self.get_position('eof')

    def is_cursor_before(self, position, char_offset=0):
        """Return True if cursor is before *position*"""
        line, index = self.get_position(position)
        index += char_offset
        cline, cindex = self.get_position('cursor')
        return (line == cline and index < cindex) or line < cline
                
    def move_cursor_to_next(self, what='word', direction='left'):
        """
        Move cursor to next *what* ('word' or 'character')
        toward *direction* ('left' or 'right')
        """
        if what == 'word':
            if direction == 'left':
                self.SendScintilla(QsciScintilla.SCI_WORDLEFT)
            elif direction == 'right':
                self.SendScintilla(QsciScintilla.SCI_WORDRIGHT)
        elif what == 'character':
            if direction == 'left':
                self.SendScintilla(QsciScintilla.SCI_CHARLEFT)
            elif direction == 'right':
                self.SendScintilla(QsciScintilla.SCI_CHARRIGHT)
        elif what == 'line':
            # Do not use "SCI_LINEUP" and "SCI_LINEDOWN"
            # otherwise, when word wrapping is enabled, cursor would not go
            # to next/previous line of code but to next/previous displayed line
            cline, _cindex = self.getCursorPosition()
            if direction == 'down':
                self.setCursorPosition(max(0, cline+1), 0)
            elif direction == 'up':
                self.setCursorPosition(min(self.lines()-1, cline-1), 0)
        elif what == 'block':
            if direction == 'up':
                self.SendScintilla(QsciScintilla.SCI_PARAUP)
            elif direction == 'down':
                self.SendScintilla(QsciScintilla.SCI_PARADOWN)
    

    #------Selection
    def clear_selection(self):
        """Clear current selection"""
        line, index = self.getCursorPosition()
        self.setSelection(line, index, line, index)

    def extend_selection_to_next(self, what='word', direction='left'):
        """
        Extend selection to next *what* ('word' or 'character')
        toward *direction* ('left' or 'right')
        """
        if what == 'word':
            if direction == 'left':
                self.SendScintilla(QsciScintilla.SCI_WORDLEFTEXTEND)
            elif direction == 'right':
                self.SendScintilla(QsciScintilla.SCI_WORDRIGHTEXTEND)
        elif what == 'character':
            if direction == 'left':
                self.SendScintilla(QsciScintilla.SCI_CHARLEFTEXTEND)
            elif direction == 'right':
                self.SendScintilla(QsciScintilla.SCI_CHARRIGHTEXTEND)
        elif what == 'block':
            if direction == 'up':
                self.SendScintilla(QsciScintilla.SCI_PARAUPEXTEND)
            elif direction == 'down':
                self.SendScintilla(QsciScintilla.SCI_PARADOWNEXTEND)
                
    def select_current_line(self):
        """Select line under cursor"""
        self.set_cursor_position('eol')
        cline, cindex = self.getCursorPosition()
        self.setSelection(cline, cindex, cline, 0)

    def __get_previous_line(self):
        cline, cindex = self.getCursorPosition()
        self.move_cursor_to_next('line', 'up')
        text = self.get_current_line()
        self.setCursorPosition(cline, cindex)
        return text
                
    def __reverse_selection(self):
        line_from, index_from, line_to, index_to = self.getSelection()
        self.setSelection(line_to, index_to, line_from, index_from)
                
    def select_current_block(self):
        """
        Select block under cursor
        Block = group of lines separated by either empty lines or commentaries
        """
        self.set_cursor_position('sol')
        _is_empty_line = lambda text: len(text.strip()) == 0
        _is_comment = lambda text: text.lstrip()[0] == '#'
        _is_separator = lambda text: _is_empty_line(text) or _is_comment(text)
        if not _is_separator(self.get_current_line()) \
           and not _is_separator(self.__get_previous_line()):
            # Current line *and* previous line contain code:
            # moving to the beginning of the block
            self.move_cursor_to_next('block', 'up')
        elif _is_empty_line(self.get_current_line()):
            # Current line is empty, moving to next block
            self.move_cursor_to_next('block', 'down')
        else:
            # This is useful when cursor is in the middle of a block commentary
            while _is_comment(self.get_current_line()):
                if self.is_cursor_on_first_line():
                    break
                self.move_cursor_to_next('line', 'up')
                if _is_empty_line(self.get_current_line()):
                    self.move_cursor_to_next('line', 'down')
                    break
        self.extend_selection_to_next('block', 'down')
        self.__reverse_selection()
        

    #------Text: get, set, replace, ...
    def __select_text(self, position_from, position_to):
        line_from, index_from = self.get_position(position_from)
        line_to, index_to = self.get_position(position_to)
        self.setSelection(line_from, index_from, line_to, index_to)

    def get_text(self, position_from=None, position_to=None):
        """
        Return text between *position_from* and *position_to*
        Positions may be positions or 'sol', 'eol', 'sof', 'eof' or 'cursor'
        """
        if position_from is None and position_to is None:
            return self.text()
        self.__select_text(position_from, position_to)
        text = unicode(self.selectedText())
        self.clear_selection()
        return text
    
    def get_character(self, position):
        """Return character at *position*"""
        line, index = self.get_position(position)
        return unicode(self.text(line)[index])
    
    def insert_text(self, text):
        """Insert text at cursor position"""
        line, col = self.getCursorPosition()
        self.insertAt(text, line, col)
        self.setCursorPosition(line, col + len(unicode(text)))
    
    def replace_text(self, position_from, position_to, text):
        self.__select_text(position_from, position_to)
        self.removeSelectedText()
        self.insert_text(text)
        
    def remove_text(self, position_from, position_to):
        self.__select_text(position_from, position_to)
        self.removeSelectedText()
        
    def find_text(self, text, changed=True,
                  forward=True, case=False, words=False):
        """Find text"""
        # findFirst(expr, re, cs, wo, wrap, forward, line, index, show)
        if changed or not forward:
            line_from, index_from, _line_to, _index_to = self.getSelection()
            self.setCursorPosition(line_from, max([0, index_from-1]))
        return self.findFirst(text, False, case, words,
                              True, forward, -1, -1, True)    

    def get_current_word(self):
        """Return current word, i.e. word at cursor position"""
        line, index = self.getCursorPosition()
        text = self.text(line)
        wc = self.wordCharacters()
        if wc is None:
            regexp = QRegExp('[^\w_]')
        else:
            regexp = QRegExp('[^%s]' % re.escape(wc))
        start = text.lastIndexOf(regexp, index) + 1
        end = text.indexOf(regexp, index)
        if start == end + 1 and index > 0:
            # we are on a word boundary, try again
            start = text.lastIndexOf(regexp, index - 1) + 1
        if start == -1:
            start = 0
        if end == -1:
            end = text.length()
        if end > start:
            word = text.mid(start, end-start)
        else:
            word = QString('')
        return word

    def get_current_line(self):
        """Return current line"""
        cline, _cindex = self.getCursorPosition()
        return unicode(self.text(cline))

    def get_line_number_at(self, coordinates):
        """Return line number at *coordinates* (QPoint)"""
        return self.lineAt(coordinates)
    
    def get_line_at(self, coordinates):
        """Return line at *coordinates* (QPoint)"""
        return unicode( self.text( self.lineAt(coordinates) ) )
    
    def get_indentation(self, line_nb):
        """Return line indentation (character number)"""
        return self.indentation(line_nb)
    
    def get_selection_bounds(self):
        """Return selection bounds (line numbers)"""
        line_from, _index_from, line_to, _index_to = self.getSelection()
        return line_from, line_to
        
    def get_line_count(self):
        """Return document total line number"""
        return self.lines()


    #----QScintilla: positions
    def position_from_lineindex(self, line, index):
        """Convert (line, index) to position"""
        try:
            # QScintilla > v2.2
            return self.positionFromLineIndex(line, index)
        except AttributeError:
            pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, line)
            # Allow for multi-byte characters
            for _i in range(index):
                pos = self.SendScintilla(QsciScintilla.SCI_POSITIONAFTER, pos)
            return pos
    
    def lineindex_from_position(self, position):
        """Convert position to (line, index)"""
        try:
            # QScintilla > v2.2
            return self.lineIndexFromPosition(position)
        except AttributeError:
            line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, position)
            line_pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMLINE, line)
            index = 0
            # Handling lines with multi-byte characters:
            while line_pos < position:
                new_line_pos = self.positionAfter(line_pos)
                if new_line_pos == line_pos:
                    # End of line (wrong *position*)
                    break
                line_pos = new_line_pos
                index += 1
            return line, index
    
    def __get_coordinates_from_lineindex(self, line, index):
        """Return cursor x, y point coordinates for line, index position"""
        pos = self.position_from_lineindex(line, index)
        x_pt = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
        y_pt = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)
        return x_pt, y_pt

    def __get_line_end_index(self, line):
        """Return the line end index"""
        pos = self.SendScintilla(QsciScintilla.SCI_GETLINEENDPOSITION, line)
        _, index = self.lineindex_from_position(pos)
        return index

    
    #------Code completion / Calltips
    def setup_code_completion(self, case_sensitive, show_single, from_document):
        self.setAutoCompletionCaseSensitivity(case_sensitive)
        self.setAutoCompletionShowSingle(show_single)
        if from_document:
            self.setAutoCompletionSource(QsciScintilla.AcsDocument)
        else:
            self.setAutoCompletionSource(QsciScintilla.AcsNone)
    
    def show_calltip(self, title, text, color='#2D62FF', at_line=None):
        """
        Show calltip
        This is here because QScintilla does not implement well calltips
        """
        if text is None or len(text) == 0:
            return
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
            _, cy = self.__get_coordinates_from_lineindex(at_line-1, 0)
        QToolTip.showText(self.mapToGlobal(QPoint(cx, cy)), tiptext)
        # Saving cursor position:
        self.calltip_position = self.get_position('cursor')

    def hide_tooltip_if_necessary(self, key):
        """
        Hide calltip when necessary
        (this is handled here because QScintilla does not support
        user-defined calltips except very basic ones)
        """
        try:
            calltip_char = self.get_character(self.calltip_position)
            before = self.is_cursor_before(self.calltip_position,
                                           char_offset=1)
            other = key in (Qt.Key_ParenRight, Qt.Key_Period, Qt.Key_Tab)
            if calltip_char not in ('?','(') or before or other:
                QToolTip.hideText()
        except (IndexError, TypeError):
            QToolTip.hideText()

    def show_completion_widget(self, textlist):
        """Show completion widget"""
        self.showUserList(1, QStringList(textlist))
        
    def completion_widget_home(self):
        self.stdkey_home()
        
    def completion_widget_end(self):
        self.stdkey_end()
        
    def completion_widget_pageup(self):
        self.stdkey_pageup()
        
    def completion_widget_pagedown(self):
        self.stdkey_pagedown()

    def select_completion_list(self):
        """Completion list is active, Enter was just pressed"""
        self.SendScintilla(QsciScintilla.SCI_NEWLINE)
        
    def is_completion_widget_visible(self):
        """Return True is completion list widget is visible"""
        return self.isListActive()
    
    def hide_completion_widget(self):
        """Hide completion list widget"""
        self.cancelList()

    def completion_list_selected(self, text):
        """
        Private slot to handle the selection from the completion list
        seltxt: selected text (QString)
        """
        position_to = line_to, index_to = self.get_position('cursor')
        position_from = line_to, index_to-len(self.completion_text)
        self.replace_text(position_from, position_to, text)
        self.completion_text = ""
    
        
    #------Standard keys
    def stdkey_clear(self):
        self.SendScintilla(QsciScintilla.SCI_CLEAR)
    
    def stdkey_backspace(self):
        self.SendScintilla(QsciScintilla.SCI_DELETEBACK)

    def stdkey_up(self, shift):
        if shift:
            self.SendScintilla(QsciScintilla.SCI_LINEUPEXTEND)
        else:
            self.SendScintilla(QsciScintilla.SCI_LINEUP)

    def stdkey_down(self, shift):
        if shift:
            self.SendScintilla(QsciScintilla.SCI_LINEDOWNEXTEND)
        else:
            self.SendScintilla(QsciScintilla.SCI_LINEDOWN)

    def stdkey_tab(self):
        self.SendScintilla(QsciScintilla.SCI_TAB)

    def stdkey_home(self, shift=False):
        if shift:
            self.SendScintilla(QsciScintilla.SCI_VCHOMEEXTEND)
        else:
            self.SendScintilla(QsciScintilla.SCI_VCHOME)

    def stdkey_end(self, shift=False):
        if shift:
            self.SendScintilla(QsciScintilla.SCI_LINEENDEXTEND)
        else:
            self.SendScintilla(QsciScintilla.SCI_LINEEND)

    def stdkey_pageup(self):
        self.SendScintilla(QsciScintilla.SCI_PAGEUP)

    def stdkey_pagedown(self):
        self.SendScintilla(QsciScintilla.SCI_PAGEDOWN)

    def stdkey_escape(self):
        self.SendScintilla(QsciScintilla.SCI_CANCEL)

                
    #----Focus
    def focusInEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        self.emit(SIGNAL("focus_in()"))
        QsciScintilla.focusInEvent(self, event)
        
    def focusOutEvent(self, event):
        """Reimplemented to handle focus"""
        self.emit(SIGNAL("focus_changed()"))
        QsciScintilla.focusOutEvent(self, event)



def colorfix(color):
    """Fixing color code, otherwise QScintilla is taking red for blue..."""
    cstr = hex(color)[2:].rjust(6, '0')
    return eval('0x' + cstr[-2:] + cstr[2:4] + cstr[:2])


class ConsoleBaseWidget(TextEditBaseWidget):
    """Console base widget"""
    DEFAULT_STYLE = 0
    PROMPT_STYLE = 1
    ERROR_STYLE = 2
    TRACEBACK_LINK_STYLE = 3
    STYLES = {DEFAULT_STYLE: 'DEFAULT_STYLE',
              PROMPT_STYLE: 'PROMPT_STYLE',
              ERROR_STYLE: 'ERROR_STYLE',
              TRACEBACK_LINK_STYLE: 'TRACEBACK_LINK_STYLE'}
    
    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)
        
    def remove_margins(self):
        """Suppressing Scintilla margins"""
        self.setMarginWidth(0, 0)
        self.setMarginWidth(1, 0)
        self.setMarginWidth(2, 0)

    def setMaximumBlockCount(self, count):
        """Fake QPlainTextEdit method"""
        pass

    def truncate_selection(self, position_from):
        """Unselect read-only parts in shell, like prompt"""
        pline, pindex = self.get_position(position_from)
        line_from, index_from, line_to, index_to = self.getSelection()
        if line_from < pline or \
           (line_from == pline and index_from < pindex):
            self.setSelection(pline, pindex, line_to, index_to)

    def restrict_cursor_position(self, position_from, position_to):
        """In shell, avoid editing text except between prompt and EOF"""
        line_from, index_from = self.get_position(position_from)
        line_to, index_to = self.get_position(position_to)
        line, index = self.get_position('cursor')
        if (line < line_from or line > line_to) or \
           (line == line_to and index > index_to):
            # Moving cursor to the end of line_to
            self.set_cursor_position( (line_to, index_to) )
        elif line == line_from and index < index_from:
            # Moving cursor to the start of line_from
            self.set_cursor_position( (line_from, index_from) )

    #------Python shell
    def append_text_to_pythonshell(self, text, error, prompt):
        self.set_cursor_position('eof')
        self.SendScintilla(QsciScintilla.SCI_STARTSTYLING,
                           len(unicode(self.text()).encode('utf-8')), 0xFF)
        if error:
            for text in text.splitlines(True):
                if text.startswith('  File') \
                and not text.startswith('  File "<'):
                    # Show error links in blue underlined text
                    self.append('  ')
                    self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                       2, self.DEFAULT_STYLE)
                    self.append(text[2:])
                    self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                       len(text)-2,
                                       self.TRACEBACK_LINK_STYLE)
                else:
                    # Show error messages in red
                    self.append(text)
                    self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                                       len(text),
                                       self.ERROR_STYLE)
        elif prompt:
            # Show prompt in green
            self.append(text)
            self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                               len(text), self.PROMPT_STYLE)
        else:
            # Show other outputs in black
            self.append(text)
            self.SendScintilla(QsciScintilla.SCI_SETSTYLING,
                               len(text), self.DEFAULT_STYLE)
        self.set_cursor_position('eof')
    
    def set_pythonshell_font(self, font):
        """Python Shell only"""
        family = str(font.family())
        size = font.pointSize()
        for style in self.STYLES:
            self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, style, family)
            self.SendScintilla(QsciScintilla.SCI_STYLESETSIZE, style, size)
        getstyleconf = lambda name, prop: CONF.get('shell_appearance',
                                                   name+'/'+prop)
        for style, stylestr in self.STYLES.iteritems():
            foreground = colorfix(getstyleconf(stylestr, 'foregroundcolor'))
            background = colorfix(getstyleconf(stylestr, 'backgroundcolor'))
            self.SendScintilla(QsciScintilla.SCI_STYLESETFORE,
                               style, foreground)
            self.SendScintilla(QsciScintilla.SCI_STYLESETBACK,
                               style, background)
            self.SendScintilla(QsciScintilla.SCI_STYLESETBOLD,
                               style, getstyleconf(stylestr, 'bold'))
            self.SendScintilla(QsciScintilla.SCI_STYLESETITALIC,
                               style, getstyleconf(stylestr, 'italic'))
            self.SendScintilla(QsciScintilla.SCI_STYLESETUNDERLINE,
                               style, getstyleconf(stylestr, 'underline'))
    

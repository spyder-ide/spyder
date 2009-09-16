# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Editor widget based on QScintilla"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

import sys, os, re
from math import log

from PyQt4.QtGui import QMouseEvent, QColor, QMenu, QPixmap
from PyQt4.QtCore import Qt, SIGNAL, QString, QEvent, QTimer
from PyQt4.Qsci import (QsciScintilla, QsciAPIs, QsciLexerCPP, QsciLexerCSS,
                        QsciLexerDiff, QsciLexerHTML, QsciLexerPython,
                        QsciLexerProperties, QsciLexerBatch)
try:
    # In some official binary PyQt4 distributions,
    # the Fortran lexers are not included
    from PyQt4.Qsci import QsciLexerFortran, QsciLexerFortran77
except ImportError:
    QsciLexerFortran = None
    QsciLexerFortran77 = None

# For debugging purpose:
STDOUT = sys.stdout

# Local import
from spyderlib.config import CONF, get_icon, get_image_path
from spyderlib.qthelpers import (add_actions, create_action, keybinding,
                                 translate)
from spyderlib.widgets.qscibase import TextEditBaseWidget


#===============================================================================
# Pyflakes code analysis
#===============================================================================
import compiler
from spyderlib.pyflakes import checker

def check(filename):
    try:
        tree = compiler.parse(file(filename, 'U').read() + '\n')
    except (SyntaxError, IndentationError), e:
        message = e.args[0]
        value = sys.exc_info()[1]
        try:
            (lineno, _offset, _text) = value[1][1:]
        except IndexError:
            # Could not compile script
            return
        return [ (message, lineno, True) ]
    else:
        results = []
        w = checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            results.append( (warning.message % warning.message_args,
                             warning.lineno, False) )
        return results

if __name__ == '__main__':
    check_results = check(os.path.abspath("../spyder.py"))
    for message, line, error in check_results:
        print "Message: %s -- Line: %s -- Error? %s" % (message, line, error)


#===============================================================================
# QsciEditor widget
#===============================================================================
class QsciEditor(TextEditBaseWidget):
    """
    QScintilla Base Editor Widget
    """
    LEXERS = {
              ('py', 'pyw', 'python'): (QsciLexerPython, '#'),
              ('f', 'for'): (QsciLexerFortran77, 'c'),
              ('f90', 'f95', 'f2k'): (QsciLexerFortran, '!'),
              ('diff', 'patch', 'rej'): (QsciLexerDiff, ''),
              'css': (QsciLexerCSS, '#'),
              ('htm', 'html'): (QsciLexerHTML, ''),
              ('c', 'cpp', 'h'): (QsciLexerCPP, '//'),
              ('bat', 'cmd', 'nt'): (QsciLexerBatch, 'rem '),
              ('properties', 'session', 'ini', 'inf', 'reg', 'url',
               'cfg', 'cnf', 'aut', 'iss'): (QsciLexerProperties, '#'),
              }
    TAB_ALWAYS_INDENTS = ('py', 'pyw', 'python', 'c', 'cpp', 'h')
    OCCURENCE_INDICATOR = QsciScintilla.INDIC_CONTAINER
    
    def __init__(self, parent=None, linenumbers=True, language=None,
                 code_analysis=False, code_folding=False):
        TextEditBaseWidget.__init__(self, parent)
                    
        # Indicate occurences of the selected word
        self.connect(self, SIGNAL('cursorPositionChanged(int, int)'),
                     self.__cursor_position_changed)
        self.__find_start = None
        self.__find_end = None
        self.__find_flags = None
        self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE,
                           self.OCCURENCE_INDICATOR,
                           QsciScintilla.INDIC_BOX)
        self.SendScintilla(QsciScintilla.SCI_INDICSETFORE,
                           self.OCCURENCE_INDICATOR,
                           0x4400FF)

        self.supported_language = None
        self.comment_string = None

        # Mark errors, warnings, ...
        self.markers = []
        self.marker_lines = {}
        self.error = self.markerDefine(QPixmap(get_image_path('error.png'),
                                               'png'))
        self.warning = self.markerDefine(QPixmap(get_image_path('warning.png'),
                                                 'png'))
            
        # Scintilla Python API
        self.api = None
        
        # Mark occurences timer
        self.occurences_timer = QTimer(self)
        self.occurences_timer.setSingleShot(True)
        self.occurences_timer.setInterval(750)
        self.connect(self.occurences_timer, SIGNAL("timeout()"), 
                     self.__mark_occurences)
        
        # Context menu
        self.setup_context_menu()
        
        # Tab key behavior
        self.tab_indents = None
        self.tab_mode = True # see QsciEditor.set_tab_mode
        
    def setup_editor(self, linenumbers=True, language=None,
                     code_analysis=False, code_folding=False,
                     font=None, wrap=True):
        # Lexer
        self.set_language(language)
                
        # Tab always indents (event when cursor is not at the begin of line)
        self.tab_indents = language in self.TAB_ALWAYS_INDENTS
        if linenumbers:
            self.connect( self, SIGNAL('linesChanged()'), self.__lines_changed )
        self.setup_margins(linenumbers, code_analysis, code_folding)

        if font is not None:
            self.set_font(font)
        self.toggle_wrap_mode(wrap)
        self.setup_api()
        self.setModified(False)
        
    def set_tab_mode(self, enable):
        """
        enabled = tab always indent
        (otherwise tab indents only when cursor is at the beginning of a line)
        """
        self.tab_mode = enable
        
    def set_language(self, language):
        self.supported_language = False
        self.comment_string = ''
        if language is not None:
            for key in self.LEXERS:
                if language.lower() in key:
                    self.supported_language = True
                    lexer_class, comment_string = self.LEXERS[key]
                    self.comment_string = comment_string
                    if lexer_class is not None:
                        # Fortran lexers are sometimes unavailable:
                        # the corresponding class is then replaced by None
                        # (see the import lines at the beginning of the script)
                        self.setLexer( lexer_class(self) )
                    break
        
        
#===============================================================================
#    QScintilla
#===============================================================================
    def setup(self):
        """Reimplement TextEditBaseWidget method"""
        TextEditBaseWidget.setup(self)
        
        # Wrapping
        if CONF.get('editor', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
        # Indentation
        self.setIndentationGuides(True)
        self.setIndentationGuidesForegroundColor(Qt.lightGray)
        
        # 80-columns edge
        self.setEdgeColumn(80)
        self.setEdgeMode(QsciScintilla.EdgeLine)
        
        # Auto-completion
        self.setAutoCompletionSource(QsciScintilla.AcsAll)

    def setup_margins(self, linenumbers=True,
                      code_analysis=False, code_folding=False):
        """
        Setup margin settings
        (except font, now set in self.set_font)
        """
        for i_margin in range(5):
            # Reset margin settings
            self.setMarginWidth(i_margin, 0)
            self.setMarginLineNumbers(i_margin, False)
            self.setMarginMarkerMask(i_margin, 0)
            self.setMarginSensitivity(i_margin, False)
        if linenumbers:
            # 1: Line numbers margin
            self.setMarginLineNumbers(1, True)
            self.update_line_numbers_margin()
            if code_analysis:
                # 2: Errors/warnings margin
                mask = (1 << self.error) | (1 << self.warning)
                self.setMarginSensitivity(0, True)
                self.setMarginMarkerMask(0, mask)
                self.setMarginWidth(0, 14)
                self.connect(self,
                     SIGNAL('marginClicked(int,int,Qt::KeyboardModifiers)'),
                     self.__margin_clicked)
        if code_folding:
            # 0: Folding margin
            self.setMarginWidth(2, 14)
            self.setFolding(QsciScintilla.BoxedFoldStyle)                
        # Colors
        fcol = CONF.get('scintilla', 'margins/foregroundcolor')
        bcol = CONF.get('scintilla', 'margins/backgroundcolor')
        if fcol:
            self.setMarginsForegroundColor(QColor(fcol))
        if bcol:
            self.setMarginsBackgroundColor(QColor(bcol))
        fcol = CONF.get('scintilla', 'foldmarginpattern/foregroundcolor')
        bcol = CONF.get('scintilla', 'foldmarginpattern/backgroundcolor')
        if fcol and bcol:
            self.setFoldMarginColors(QColor(fcol), QColor(bcol))
        
    def setup_api(self):
        """Load and prepare API"""
        if self.lexer() is None:
            return
        self.api = QsciAPIs(self.lexer())
        is_api_ready = False
        api_path = CONF.get('editor', 'api')
        if not os.path.isfile(api_path):
            return False
        api_stat = CONF.get('editor', 'api_stat', None)
        current_api_stat = os.stat(api_path)
        if (api_stat is not None) and (api_stat == current_api_stat):
            if self.api.isPrepared():
                is_api_ready = self.api.loadPrepared()
        else:
            CONF.set('editor', 'api_stat', current_api_stat)
        if not is_api_ready:
            if self.api.load(api_path):
                self.api.prepare()
                self.connect(self.api, SIGNAL("apiPreparationFinished()"),
                             self.api.savePrepared)
        return is_api_ready
    
    def set_eol_mode(self, text):
        """
        Set QScintilla widget EOL mode based on *text* EOL characters
        """
        if isinstance(text, QString):
            text = unicode(text)
        if text.find("\r\n") > -1:
            self.setEolMode( QsciScintilla.EolMode(QsciScintilla.EolWindows) )
        elif text.find("\n") > -1:
            self.setEolMode( QsciScintilla.EolMode(QsciScintilla.EolUnix) )
        elif text.find("\r") > -1:
            self.setEolMode( QsciScintilla.EolMode(QsciScintilla.EolMac) )
        else:
            return None
        
    def get_line_separator(self):
        """Return line separator based on current EOL mode"""
        mode = self.eolMode()
        if mode == QsciScintilla.EolWindows:
            return '\r\n'
        elif mode == QsciScintilla.EolUnix:
            return '\n'
        elif mode == QsciScintilla.EolMac:
            return '\r'
        else:
            return ''
    
    def __find_first(self, text):
        """Find first occurence"""
        self.__find_flags = QsciScintilla.SCFIND_MATCHCASE | \
                            QsciScintilla.SCFIND_WHOLEWORD
        self.__find_start = 0
        line = self.lines()-1
        self.__find_end = self.position_from_lineindex(line,
                                                       self.text(line).length())
        return self.__find_next(text)
    
    def __find_next(self, text):
        """Find next occurence"""
        if self.__find_start == self.__find_end:
            return False
        
        self.SendScintilla(QsciScintilla.SCI_SETTARGETSTART,
                           self.__find_start)
        self.SendScintilla(QsciScintilla.SCI_SETTARGETEND,
                           self.__find_end)
        self.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS,
                           self.__find_flags)
        pos = self.SendScintilla(QsciScintilla.SCI_SEARCHINTARGET, 
                                 len(text), text)
        
        if pos == -1:
            return False
        self.__find_start = self.SendScintilla(QsciScintilla.SCI_GETTARGETEND)
        return True
        
    def __get_found_occurence(self):
        """Return found occurence"""
        spos = self.SendScintilla(QsciScintilla.SCI_GETTARGETSTART)
        epos = self.SendScintilla(QsciScintilla.SCI_GETTARGETEND)
        return (spos, epos - spos)
        
    def __cursor_position_changed(self):
        """Cursor position has changed"""
        #TODO: Add attribute for occurences marking enable/disable:
        # if self.occurences_marking:
        self.occurences_timer.stop()
        self.occurences_timer.start()
        
    def __mark_occurences(self):
        """Marking occurences of the currently selected word"""
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                           self.OCCURENCE_INDICATOR)
        self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE,
                           0, self.length())

        if not self.supported_language:
            return
            
        text = self.get_current_word()
        if text.isEmpty():
            return

        # Highlighting all occurences of word *text*
        ok = self.__find_first(text)
        while ok:
            spos = self.SendScintilla(QsciScintilla.SCI_GETTARGETSTART)
            epos = self.SendScintilla(QsciScintilla.SCI_GETTARGETEND)
            self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                               spos, epos-spos)
            ok = self.__find_next(text)
        
    def __lines_changed(self):
        """Update margin"""
        self.update_line_numbers_margin()
        
    def update_line_numbers_margin(self):
        """Update margin width"""
        width = log(self.lines(), 10) + 2
        self.setMarginWidth(1, QString('0'*int(width)))

    def delete(self):
        """Remove selected text"""
        # Used by global callbacks in Spyder -> delete_action
        QsciScintilla.removeSelectedText(self)

    def set_font(self, font):
        """Set shell font"""
        if self.lexer() is None:
            self.setFont(font)
        else:
            self.lexer().setFont(font)
            self.setLexer(self.lexer())
        self.setMarginsFont(font)
        
    def set_text(self, text):
        """Set the text of the editor"""
        self.setText(text)
        self.set_eol_mode(text)

    def get_text(self):
        """Return editor text"""
        return self.text()
        
    def fold_header(self, line):
        """Is it a fold header line?"""
        lvl = self.SendScintilla(QsciScintilla.SCI_GETFOLDLEVEL, line)
        return lvl & QsciScintilla.SC_FOLDLEVELHEADERFLAG
    
    def fold_expanded(self, line):
        """Is fold expanded?"""
        return self.SendScintilla(QsciScintilla.SCI_GETFOLDEXPANDED, line)
        
    def get_folded_lines(self):
        """Return the list of folded line numbers"""
        return [line for line in xrange(self.lines()) \
                if self.fold_header(line) and not self.fold_expanded(line) ]
        
    def unfold_all(self):
        """Unfold all folded lines"""
        for line in self.get_folded_lines():
            self.foldLine(line)
        
        
#===============================================================================
#    High-level editor features
#===============================================================================
    def highlight_line(self, line):
        """Highlight line number *line*"""
        text = unicode(self.text(line-1)).rstrip()
        self.setSelection(line-1, len(text), line-1, 0)
        self.ensureLineVisible(line-1)

    def cleanup_code_analysis(self):
        """Remove all code analysis markers"""
        for marker in self.markers:
            self.markerDeleteHandle(marker)
        self.markers = []
        self.marker_lines = {}
        
    def process_code_analysis(self, check_results):
        """Analyze filename code with pyflakes"""
        self.cleanup_code_analysis()
        if check_results is None:
            # Not able to compile module
            return
        for message, line0, error in check_results:
            line1 = line0 - 1
            marker = self.markerAdd(line1, 0 if error else 1)
            self.markers.append(marker)
            if line1 not in self.marker_lines:
                self.marker_lines[line1] = []
            self.marker_lines[line1].append( (message, error) )

    def __highlight_warning(self, line):
        self.highlight_line(line+1)
        self.__show_code_analysis_results(line)

    def go_to_next_warning(self):
        """Go to next code analysis warning message"""
        cline, _ = self.getCursorPosition()
        lines = sorted(self.marker_lines.keys())
        for line in lines:
            if line > cline:
                self.__highlight_warning(line)
                return
        else:
            self.__highlight_warning(lines[0])

    def go_to_previous_warning(self):
        """Go to previous code analysis warning message"""
        cline, _ = self.getCursorPosition()
        lines = sorted(self.marker_lines.keys(), reverse=True)
        for line in lines:
            if line < cline:
                self.__highlight_warning(line)
                return
        else:
            self.__highlight_warning(lines[0])

    def __show_code_analysis_results(self, line):
        """Show warning/error messages"""
        if line in self.marker_lines:
            msglist = [ msg for msg, _error in self.marker_lines[line] ]
            self.show_calltip(self.tr("Code analysis"), msglist,
                              color='#129625', at_line=line)
    
    def __margin_clicked(self, margin, line, modifier):
        """Margin was clicked, that's for sure!"""
        if margin == 0:
            self.__show_code_analysis_results(line)

    def mouseMoveEvent(self, event):
        line = self.get_line_number_at(event.pos())
        self.__show_code_analysis_results(line)
        QsciScintilla.mouseMoveEvent(self, event)
        
    def add_prefix(self, prefix):
        """Add prefix to current line or selected line(s)"""        
        if self.hasSelectedText():
            # Add prefix to selected line(s)
            line_from, index_from, line_to, index_to = self.getSelection()
            if index_to == 0:
                line_to -= 1
            self.beginUndoAction()
            for line in range(line_from, line_to+1):
                self.insertAt(prefix, line, 0)
            self.endUndoAction()
            if index_to == 0:
                line_to += 1
            else:
                index_to += len(prefix)
            self.setSelection(line_from, index_from+len(prefix),
                              line_to, index_to)
        else:
            # Add prefix to current line
            line, index = self.getCursorPosition()
            self.beginUndoAction()
            self.insertAt(prefix, line, 0)
            self.endUndoAction()
            self.setCursorPosition(line, index+len(prefix))
    
    def remove_prefix(self, prefix):
        """Remove prefix from current line or selected line(s)"""        
        if self.hasSelectedText():
            # Remove prefix from selected line(s)
            line_from, index_from, line_to, index_to = self.getSelection()
            if index_to == 0:
                line_to -= 1
            self.beginUndoAction()
            for line in range(line_from, line_to+1):
                if not self.text(line).startsWith(prefix):
                    continue
                self.setSelection(line, 0, line, len(prefix))
                self.removeSelectedText()
                if line == line_from:
                    index_from = max([0, index_from-len(prefix)])
                if line == line_to and index_to != 0:
                    index_to = max([0, index_to-len(prefix)])
            if index_to == 0:
                line_to += 1
            self.setSelection(line_from, index_from, line_to, index_to)
            self.endUndoAction()
        else:
            # Remove prefix from current line
            line, index = self.getCursorPosition()
            if not self.text(line).startsWith(prefix):
                return
            self.beginUndoAction()
            self.setSelection(line, 0, line, len(prefix))
            self.removeSelectedText()
            self.setCursorPosition(line, index-len(prefix))
            self.endUndoAction()
            self.setCursorPosition(line, max([0, index-len(prefix)]))
    
    def fix_indent(self, forward=True):
        """
        Fix indentation (Python only, no text selection)
        forward=True: fix indent only if text is not enough indented
                      (otherwise force indent)
        forward=False: fix indent only if text is too much indented
                       (otherwise force unindent)
        """
        if not isinstance(self.lexer(), QsciLexerPython):
            return        
        line, index = self.getCursorPosition()
        prevtext = unicode(self.text(line-1)).rstrip()
        indent = self.indentation(line)
        correct_indent = self.indentation(line-1)
        if prevtext.endswith(':'):
            # Indent            
            correct_indent += 4
        elif prevtext.endswith('continue') or prevtext.endswith('break'):
            # Unindent
            correct_indent -= 4
        elif prevtext.endswith(','):
            rlmap = {")":"(", "]":"[", "}":"{"}
            for par in rlmap:
                i_right = prevtext.rfind(par)
                if i_right != -1:
                    prevtext = prevtext[:i_right]
                    i_left = prevtext.rfind(rlmap[par])
                    if i_left != -1:
                        prevtext = prevtext[:i_left]
                    else:
                        break
            else:
                prevexpr = re.split(r'\(|\{|\[', prevtext)[-1]
                correct_indent = len(prevtext)-len(prevexpr)
        if forward:
            if indent == correct_indent or indent > correct_indent:
                # Force indent
                correct_indent = indent + 4
        elif indent == correct_indent or indent < correct_indent:
            # Force unindent
            correct_indent = indent - 4
            
        if correct_indent >= 0:
            self.beginUndoAction()
            self.setSelection(line, 0, line, indent)
            self.removeSelectedText()
            if index > indent:
                index -= indent-correct_indent
            else:
                index = correct_indent
            self.insertAt(" "*correct_indent, line, 0)
            self.setCursorPosition(line, index)
            self.endUndoAction()
    
    def __no_char_before_cursor(self):
        line, index = self.getCursorPosition()
        self.setSelection(line, 0, line, index)
        selected_text = unicode(self.selectedText())
        self.clear_selection()
        return len(selected_text.strip()) == 0
    
    def indent(self):
        """Indent current line or selection"""
        if self.hasSelectedText():
            self.add_prefix( " "*4 )
        elif self.__no_char_before_cursor() or \
             (self.tab_indents and self.tab_mode):
            if isinstance(self.lexer(), QsciLexerPython):
                self.fix_indent(forward=True)
            else:
                self.add_prefix( " "*4 )
        else:
            self.SendScintilla(QsciScintilla.SCI_TAB)
    
    def unindent(self):
        """Unindent current line or selection"""
        if self.hasSelectedText():
            self.remove_prefix( " "*4 )
        elif self.__no_char_before_cursor() or \
             (self.tab_indents and self.tab_mode):
            if isinstance(self.lexer(), QsciLexerPython):
                self.fix_indent(forward=False)
            else:
                self.remove_prefix( " "*4 )
            
    def comment(self):
        """Comment current line or selection"""
        self.add_prefix(self.comment_string)

    def uncomment(self):
        """Uncomment current line or selection"""
        self.remove_prefix(self.comment_string)
    
    def blockcomment(self):
        """Block comment current line or selection"""
        comline = self.comment_string + '='*(80-len(self.comment_string)) \
                  + self.get_line_separator()
        if self.hasSelectedText():
            line_from, _index_from, line_to, _index_to = self.getSelection()
            lines = range(line_from, line_to+1)
        else:
            line, _index = self.getCursorPosition()
            lines = [line]
        self.beginUndoAction()
        self.insertAt( comline, lines[-1]+1, 0 )
        self.insertAt( comline, lines[0], 0 )
        for l in lines:
            self.insertAt( '# ', l+1, 0 )
        self.endUndoAction()
        self.setCursorPosition(lines[-1]+2, 80)

    def __is_comment_bar(self, line):
        comline = '#' + '='*79 + self.get_line_separator()
        self.setSelection(line, 0, line+1, 0)
        return unicode(self.selectedText()) == comline            
    
    def unblockcomment(self):
        """Un-block comment current line or selection"""
        line, index = self.getCursorPosition()
        self.setSelection(line, 0, line, 1)
        if unicode(self.selectedText()) != '#':
            self.setCursorPosition(line, index)
            return
        # Finding first comment bar
        line1 = line-1
        while line1 >= 0 and not self.__is_comment_bar(line1):
            line1 -= 1
        if not self.__is_comment_bar(line1):
            self.setCursorPosition(line, index)
            return
        # Finding second comment bar
        line2 = line+1
        while line2 < self.lines() and not self.__is_comment_bar(line2):
            line2 += 1
        if not self.__is_comment_bar(line2) or line2 > self.lines()-2:
            self.setCursorPosition(line, index)
            return
        lines = range(line1+1, line2)
        self.beginUndoAction()
        self.setSelection(line2, 0, line2+1, 0)
        self.removeSelectedText()
        for l in lines:
            self.setSelection(l, 0, l, 2)
            self.removeSelectedText()
        self.setSelection(line1, 0, line1+1, 0)
        self.removeSelectedText()
        self.endUndoAction()
    
#===============================================================================
#    Qt Event handlers
#===============================================================================
    def setup_context_menu(self):
        """Setup context menu"""
        self.undo_action = create_action(self,
                           translate("SimpleEditor", "Undo"),
                           shortcut=keybinding('Undo'),
                           icon=get_icon('undo.png'), triggered=self.undo)
        self.redo_action = create_action(self,
                           translate("SimpleEditor", "Redo"),
                           shortcut=keybinding('Redo'),
                           icon=get_icon('redo.png'), triggered=self.redo)
        self.cut_action = create_action(self,
                           translate("SimpleEditor", "Cut"),
                           shortcut=keybinding('Cut'),
                           icon=get_icon('editcut.png'), triggered=self.cut)
        self.copy_action = create_action(self,
                           translate("SimpleEditor", "Copy"),
                           shortcut=keybinding('Copy'),
                           icon=get_icon('editcopy.png'), triggered=self.copy)
        paste_action = create_action(self,
                           translate("SimpleEditor", "Paste"),
                           shortcut=keybinding('Paste'),
                           icon=get_icon('editpaste.png'), triggered=self.paste)
        self.delete_action = create_action(self,
                           translate("SimpleEditor", "Delete"),
                           shortcut=keybinding('Delete'),
                           icon=get_icon('editdelete.png'),
                           triggered=self.removeSelectedText)
        selectall_action = create_action(self,
                           translate("SimpleEditor", "Select all"),
                           shortcut=keybinding('SelectAll'),
                           icon=get_icon('selectall.png'),
                           triggered=self.selectAll)
        self.menu = QMenu(self)
        add_actions(self.menu, (self.undo_action, self.redo_action, None,
                                self.cut_action, self.copy_action,
                                paste_action, self.delete_action,
                                None, selectall_action))        
        # Read-only context-menu
        self.readonly_menu = QMenu(self)
        add_actions(self.readonly_menu,
                    (self.copy_action, None, selectall_action))        
            
    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        key = event.key()
        ctrl = event.modifiers() & Qt.ControlModifier
        shift = event.modifiers() & Qt.ShiftModifier
        # Zoom in/out
        if ((key == Qt.Key_Plus) and ctrl) \
             or ((key==Qt.Key_Equal) and shift and ctrl):
            self.zoomIn()
            event.accept()
        elif (key == Qt.Key_Minus) and ctrl:
            self.zoomOut()
            event.accept()
        # Indent/unindent
        elif key == Qt.Key_Backtab:
            self.unindent()
            event.accept()
        elif (key == Qt.Key_Tab):
            if self.is_completion_widget_visible():
                self.SendScintilla(QsciScintilla.SCI_TAB)
            else:
                self.indent()
            event.accept()
#TODO: find other shortcuts...
#        elif (key == Qt.Key_3) and ctrl:
#            self.comment()
#            event.accept()
#        elif (key == Qt.Key_2) and ctrl:
#            self.uncomment()
#            event.accept()
#        elif (key == Qt.Key_4) and ctrl:
#            self.blockcomment()
#            event.accept()
#        elif (key == Qt.Key_5) and ctrl:
#            self.unblockcomment()
#            event.accept()
        else:
            QsciScintilla.keyPressEvent(self, event)
            
    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() == Qt.MidButton:
            self.setFocus()
            event = QMouseEvent(QEvent.MouseButtonPress, event.pos(),
                                Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            QsciScintilla.mousePressEvent(self, event)
            QsciScintilla.mouseReleaseEvent(self, event)
            self.paste()
        else:
            QsciScintilla.mousePressEvent(self, event)
            
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        state = self.hasSelectedText()
        self.copy_action.setEnabled(state)
        self.cut_action.setEnabled(state)
        self.delete_action.setEnabled(state)
        self.undo_action.setEnabled( self.isUndoAvailable() )
        self.redo_action.setEnabled( self.isRedoAvailable() )
        menu = self.menu
        if self.isReadOnly():
            menu = self.readonly_menu
        menu.popup(event.globalPos())
        event.accept()

# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Editor widget based on PyQt4.QtGui.QPlainTextEdit
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from __future__ import division

import sys, os, re, os.path as osp, time

from PyQt4.QtGui import (QMouseEvent, QColor, QMenu, QApplication, QSplitter,
                         QFont, QTextEdit, QTextFormat, QPainter, QTextCursor,
                         QPlainTextEdit, QBrush, QTextDocument, QTextCharFormat,
                         QPixmap, QPrinter, QToolTip, QCursor, QInputDialog,
                         QTextBlockUserData, QLineEdit, QShortcut, QKeySequence)
from PyQt4.QtCore import (Qt, SIGNAL, QString, QEvent, QTimer, QRect, QRegExp,
                          PYQT_VERSION_STR, QVariant)

# For debugging purpose:
STDOUT = sys.stdout

# Local import
from spyderlib.config import get_icon, get_image_path
from spyderlib.utils.qthelpers import (add_actions, create_action, keybinding,
                                       translate)
from spyderlib.utils.dochelpers import getobj
from spyderlib.widgets.codeeditor.base import TextEditBaseWidget
from spyderlib.widgets.codeeditor import syntaxhighlighters
from spyderlib.widgets.editortools import (PythonCFM, LineNumberArea, EdgeLine,
                                           ScrollFlagArea, check,
                                           OutlineExplorer)
from spyderlib.utils import sourcecode, is_keyword


#===============================================================================
# CodeEditor widget
#===============================================================================
class BlockUserData(QTextBlockUserData):
    def __init__(self, editor):
        QTextBlockUserData.__init__(self)
        self.editor = editor
        self.breakpoint = False
        self.breakpoint_condition = None
        self.code_analysis = []
        self.todo = ''
        self.editor.blockuserdata_list.append(self)
        
    def is_empty(self):
        return not self.breakpoint and not self.code_analysis and not self.todo
        
    def __del__(self):
        bud_list = self.editor.blockuserdata_list
        bud_list.pop(bud_list.index(self))

def get_primary_at(source_code, offset):
    """Return Python object in *source_code* at *offset*"""
    try:
        import rope.base.worder
        word_finder = rope.base.worder.Worder(source_code, True)
        return word_finder.get_primary_at(offset)
    except ImportError:
        return

class CodeEditor(TextEditBaseWidget):
    """
    Source Code Editor Widget based exclusively on Qt
    """
    LANGUAGES = {
                 ('py', 'pyw', 'python', 'ipy'): (syntaxhighlighters.PythonSH,
                                                  '#', PythonCFM),
                 ('pyx', 'pxi', 'pxd'): (syntaxhighlighters.CythonSH,
                                         '#', PythonCFM),
                 ('f', 'for'): (syntaxhighlighters.Fortran77SH, 'c', None),
                 ('f90', 'f95', 'f2k'): (syntaxhighlighters.FortranSH,
                                         '!', None),
#                 ('diff', 'patch', 'rej'): (QsciLexerDiff, '', None),
#                 'css': (QsciLexerCSS, '#', None),
#                 ('htm', 'html'): (QsciLexerHTML, '', None),
                 ('c', 'cpp', 'h', 'hpp', 'cxx'): (syntaxhighlighters.CppSH,
                                                   '//', None),
#                 ('bat', 'cmd', 'nt'): (QsciLexerBatch, 'rem ', None),
#                 ('properties', 'session', 'ini', 'inf', 'reg', 'url',
#                  'cfg', 'cnf', 'aut', 'iss'): (QsciLexerProperties, '#', None),
                 }
    TAB_ALWAYS_INDENTS = ('py', 'pyw', 'python', 'c', 'cpp', 'h')
    EOL_WINDOWS = 0
    EOL_UNIX = 1
    EOL_MAC = 2
    EOL_MODES = {"\r\n": EOL_WINDOWS, "\n": EOL_UNIX, "\r": EOL_MAC}
    
    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)
        
        self.eol_mode = None
        
        # Side areas background color
        self.area_background_color = QColor(Qt.white)
        
        # 80-col edge line
        self.edge_line = EdgeLine(self)
        
        # Markers
        self.markers_margin = True
        self.markers_margin_width = 15
        self.error_pixmap = QPixmap(get_image_path('error.png'), 'png')
        self.warning_pixmap = QPixmap(get_image_path('warning.png'), 'png')
        self.todo_pixmap = QPixmap(get_image_path('todo.png'), 'png')
        self.bp_pixmap = QPixmap(get_image_path('breakpoint.png'), 'png')
        self.bpc_pixmap = QPixmap(get_image_path('breakpoint_cond.png'), 'png')
        
        # Line number area management
        self.linenumbers_margin = True
        self.linenumberarea_enabled = None
        self.linenumberarea = LineNumberArea(self)
        self.connect(self, SIGNAL("blockCountChanged(int)"),
                     self.update_linenumberarea_width)
        self.connect(self, SIGNAL("updateRequest(QRect,int)"),
                     self.update_linenumberarea)

        # Syntax highlighting
        self.highlighter_class = None
        self.highlighter = None
        ccs = 'Spyder'
        if ccs not in syntaxhighlighters.COLOR_SCHEME_NAMES:
            ccs = syntaxhighlighters.COLOR_SCHEME_NAMES[0]
        self.color_scheme = ccs
        
        #  Background colors: current line, occurences
        self.currentline_color = QColor(Qt.red).lighter(190)
        self.highlight_current_line_enabled = False
        
        # Scrollbar flag area
        self.scrollflagarea_enabled = None
        self.scrollflagarea = ScrollFlagArea(self)
        self.scrollflagarea.hide()
        self.warning_color = "#FFAD07"
        self.error_color = "#EA2B0E"
        self.todo_color = "#B4D4F3"
        self.breakpoint_color = "#30E62E"

        self.update_linenumberarea_width(0)
                
        self.document_id = id(self)
                    
        # Indicate occurences of the selected word
        self.connect(self, SIGNAL('cursorPositionChanged()'),
                     self.__cursor_position_changed)
        self.__find_first_pos = None
        self.__find_flags = None

        self.supported_language = None
        self.classfunc_match = None
        self.comment_string = None
        
        # Block user data
        self.blockuserdata_list = []
        
        # Mark occurences timer
        self.occurence_highlighting = None
        self.occurence_timer = QTimer(self)
        self.occurence_timer.setSingleShot(True)
        self.occurence_timer.setInterval(1500)
        self.connect(self.occurence_timer, SIGNAL("timeout()"), 
                     self.__mark_occurences)
        self.occurences = []
        self.occurence_color = QColor(Qt.yellow).lighter(160)
        
        # Context menu
        self.setup_context_menu()
        
        # Tab key behavior
        self.tab_indents = None
        self.tab_mode = True # see CodeEditor.set_tab_mode
        
        self.go_to_definition_enabled = False
        self.close_parentheses_enabled = True
        self.auto_unindent_enabled = True
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.__cursor_changed = False
        self.ctrl_click_color = QColor(Qt.blue)
        
        # Keyboard shortcuts
        self.codecomp_sc = QShortcut(QKeySequence("Ctrl+Space"), self,
                                     self.do_code_completion)
        self.codecomp_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.duplicate_sc = QShortcut(QKeySequence("Ctrl+D"), self,
                                      self.duplicate_line)
        self.duplicate_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.gotodef_sc = QShortcut(QKeySequence("Ctrl+G"), self,
                                    self.do_go_to_definition)
        self.gotodef_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.comment_sc = QShortcut(QKeySequence("Ctrl+3"), self,
                                    self.comment)
        self.comment_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.uncomment_sc = QShortcut(QKeySequence("Ctrl+2"), self,
                                      self.uncomment)
        self.uncomment_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.blockcomment_sc = QShortcut(QKeySequence("Ctrl+4"), self,
                                         self.blockcomment)
        self.blockcomment_sc.setContext(Qt.WidgetWithChildrenShortcut)
        self.unblockcomment_sc = QShortcut(QKeySequence("Ctrl+5"), self,
                                           self.unblockcomment)
        self.unblockcomment_sc.setContext(Qt.WidgetWithChildrenShortcut)
        
    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [
                (self.codecomp_sc, "Code completion", "Ctrl+Space"),
                (self.duplicate_sc, "Duplicate line", "Ctrl+D"),
                (self.gotodef_sc, "Go to definition", "Ctrl+G"),
                (self.comment_sc, "Comment", "Ctrl+3"),
                (self.uncomment_sc, "Uncomment", "Ctrl+2"),
                (self.blockcomment_sc, "Blockcomment", "Ctrl+4"),
                (self.unblockcomment_sc, "Unblockcomment", "Ctrl+5"),
                ]

    def closeEvent(self, event):
        TextEditBaseWidget.closeEvent(self, event)
        if PYQT_VERSION_STR.startswith('4.6'):
            self.emit(SIGNAL('destroyed()'))
            
        
    def get_document_id(self):
        return self.document_id
        
    def set_as_clone(self, editor):
        """Set as clone editor"""
        self.setDocument(editor.document())
        self.document_id = editor.get_document_id()
        self.highlighter = editor.highlighter
        self._apply_highlighter_color_scheme()
        
    def setup_editor(self, linenumbers=True, language=None, code_analysis=False,
                     font=None, color_scheme=None, wrap=False, tab_mode=True,
                     highlight_current_line=True, occurence_highlighting=True,
                     scrollflagarea=True, todo_list=True,
                     codecompletion_auto=False, codecompletion_case=True,
                     codecompletion_single=False, codecompletion_enter=False,
                     calltips=None, go_to_definition=False,
                     close_parentheses=True, auto_unindent=True,
                     cloned_from=None):
        # Code completion and calltips
        self.set_codecompletion_auto(codecompletion_auto)
        self.set_codecompletion_case(codecompletion_case)
        self.set_codecompletion_single(codecompletion_single)
        self.set_codecompletion_enter(codecompletion_enter)
        self.set_calltips(calltips)
        self.set_go_to_definition_enabled(go_to_definition)
        self.set_close_parentheses_enabled(close_parentheses)
        self.set_auto_unindent_enabled(auto_unindent)
        
        # Scrollbar flag area
        self.set_scrollflagarea_enabled(scrollflagarea)
        
        # Line number area
        if cloned_from:
            self.setFont(font) # this is required for line numbers area
        self.setup_margins(linenumbers, code_analysis, todo_list)
        
        # Lexer
        self.set_language(language)
        
        # Highlight current line
        self.set_highlight_current_line(highlight_current_line)
                
        # Occurence highlighting
        self.set_occurence_highlighting(occurence_highlighting)
                
        # Tab always indents (even when cursor is not at the begin of line)
        self.set_tab_mode(tab_mode)
        
        if cloned_from is not None:
            self.set_as_clone(cloned_from)
            self.update_linenumberarea_width(0)
        elif font is not None:
            self.set_font(font, color_scheme)
        elif color_scheme is not None:
            self.set_color_scheme(color_scheme)
            
        self.toggle_wrap_mode(wrap)
        
    def set_tab_mode(self, enable):
        """
        enabled = tab always indent
        (otherwise tab indents only when cursor is at the beginning of a line)
        """
        self.tab_mode = enable
        
    def set_go_to_definition_enabled(self, enable):
        """Enable/Disable go-to-definition feature, which is implemented in 
        child class -> Editor widget"""
        self.go_to_definition_enabled = enable
        
    def set_close_parentheses_enabled(self, enable):
        """Enable/disable automatic parentheses insertion feature"""
        self.close_parentheses_enabled = enable
        
    def set_auto_unindent_enabled(self, enable):
        """Enable/disable automatic unindent after else/elif/finally/except"""
        self.auto_unindent_enabled = enable
        
    def set_occurence_highlighting(self, enable):
        """Enable/disable occurence highlighting"""
        self.occurence_highlighting = enable
        if not enable:
            self.__clear_occurences()
            
    def set_highlight_current_line(self, enable):
        """Enable/disable current line highlighting"""
        self.highlight_current_line_enabled = enable
        self.highlight_current_line()

    def set_language(self, language):
        self.tab_indents = language in self.TAB_ALWAYS_INDENTS
        self.supported_language = False
        self.comment_string = ''
        if language is None:
            if self.highlighter is not None:
                self.highlighter.setDocument(None)
            self.highlighter = None
            self.highlighter_class = None
        else:
            for key in self.LANGUAGES:
                if language.lower() in key:
                    self.supported_language = True
                    sh_class, comment_string, CFMatch = self.LANGUAGES[key]
                    self.comment_string = comment_string
                    if CFMatch is None:
                        self.classfunc_match = None
                    else:
                        self.classfunc_match = CFMatch()
                    apply_language = self.highlighter_class is not sh_class
                    self.highlighter_class = sh_class
                    if apply_language:
                        self.apply_highlighter_settings()
                
    def is_python(self):
        return self.highlighter_class is syntaxhighlighters.PythonSH
        
    def is_cython(self):
        return self.highlighter_class is syntaxhighlighters.CythonSH
        
    def rehighlight(self):
        """
        Rehighlight the whole document to rebuild outline explorer data
        and import statements data from scratch
        """
        if self.highlighter is not None:
            self.highlighter.rehighlight()
        
        
    def setup(self):
        """Reimplement TextEditBaseWidget method"""
        TextEditBaseWidget.setup(self)

    def setup_margins(self, linenumbers=True, code_analysis=False,
                      todo_list=True):
        """
        Setup margin settings
        (except font, now set in self.set_font)
        """
        self.linenumbers_margin = linenumbers
        self.markers_margin = code_analysis or todo_list
        enabled = linenumbers or code_analysis or todo_list
        self.set_linenumberarea_enabled(enabled)
    
    def remove_trailing_spaces(self):
        """Remove trailing spaces"""
        text_before = unicode(self.toPlainText())
        text_after = sourcecode.remove_trailing_spaces(text_before)
        if text_before != text_after:
            self.setPlainText(text_after)
            self.document().setModified(True)
            
    def fix_indentation(self):
        """Replace tabs by spaces"""
        text_before = unicode(self.toPlainText())
        text_after = sourcecode.fix_indentation(text_before)
        if text_before != text_after:
            self.setPlainText(text_after)
            self.document().setModified(True)

    def get_current_object(self):
        """Return current object (string) -- requires 'rope'"""
        source_code = unicode(self.toPlainText())
        offset = self.get_position('cursor')
        return get_primary_at(source_code, offset)
    
    #------EOL characters
    def set_eol_mode(self, text):
        """
        Set widget EOL mode based on *text* EOL characters
        """
        if isinstance(text, QString):
            text = unicode(text)
        eol_chars = sourcecode.get_eol_chars(text)
        if eol_chars is not None:
            if self.eol_mode is not None:
                self.document().setModified(True)
            self.eol_mode = self.EOL_MODES[eol_chars]
        
    def get_line_separator(self):
        """Return line separator based on current EOL mode"""
        for eol_chars, mode in self.EOL_MODES.iteritems():
            if self.eol_mode == mode:
                return eol_chars
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
    
    #------Find occurences
    def __find_first(self, text):
        """Find first occurence: scan whole document"""
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        cursor = self.textCursor()
        # Scanning whole document
        cursor.movePosition(QTextCursor.Start)
        regexp = QRegExp(r"\b%s\b" % QRegExp.escape(text), Qt.CaseSensitive)
        cursor = self.document().find(regexp, cursor, flags)
        self.__find_first_pos = cursor.position()
        return cursor
    
    def __find_next(self, text, cursor):
        """Find next occurence"""
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        regexp = QRegExp(r"\b%s\b" % QRegExp.escape(text), Qt.CaseSensitive)
        cursor = self.document().find(regexp, cursor, flags)
        if cursor.position() != self.__find_first_pos:
            return cursor
        
    def __cursor_position_changed(self):
        """Cursor position has changed"""
        line, column = self.get_cursor_line_column()
        self.emit(SIGNAL('cursorPositionChanged(int,int)'), line, column)
        self.highlight_current_line()
        if self.occurence_highlighting:
            self.occurence_timer.stop()
            self.occurence_timer.start()
        
    def __clear_occurences(self):
        """Clear occurence markers"""
        self.occurences = []
        self.clear_extra_selections('occurences')
        self.scrollflagarea.update()

    def __highlight_selection(self, key, cursor, foreground_color=None,
                        background_color=None, underline_color=None,
                        underline_style=QTextCharFormat.SpellCheckUnderline,
                        update=False):
        extra_selections = self.get_extra_selections(key)
        selection = QTextEdit.ExtraSelection()
        if foreground_color is not None:
            selection.format.setForeground(foreground_color)
        if background_color is not None:
            selection.format.setBackground(background_color)
        if underline_color is not None:
            selection.format.setProperty(QTextFormat.TextUnderlineStyle,
                                         QVariant(underline_style))
            selection.format.setProperty(QTextFormat.TextUnderlineColor,
                                         QVariant(underline_color))
        selection.format.setProperty(QTextFormat.FullWidthSelection,
                                     QVariant(True))
        selection.cursor = cursor
        extra_selections.append(selection)
        self.set_extra_selections(key, extra_selections)
        if update:
            self.update_extra_selections()
        
    def __mark_occurences(self):
        """Marking occurences of the currently selected word"""
        self.__clear_occurences()

        if not self.supported_language:
            return
        if self.has_selected_text():
            block1, block2 = self.get_selection_bounds()
            if block1 != block2:
                # Selection extends to more than one line
                return
            text = self.get_selected_text()
            if not re.match(r'([a-zA-Z_]+[0-9a-zA-Z_]*)$', text):
                # Selection is not a word
                return
        else:
            text = self.get_current_word()
            if text is None:
                return
        if (self.is_python() or self.is_cython()) and \
           (is_keyword(unicode(text)) or unicode(text) == 'self'):
            return

        # Highlighting all occurences of word *text*
        cursor = self.__find_first(text)
        self.occurences = []
        while cursor:
            self.occurences.append(cursor.blockNumber())
            self.__highlight_selection('occurences', cursor,
                                       background_color=self.occurence_color)
            cursor = self.__find_next(text, cursor)
        self.update_extra_selections()
        self.occurences.pop(-1)
        self.scrollflagarea.update()
        
    #-----markers
    def get_markers_margin(self):
        if self.markers_margin:
            return self.markers_margin_width
        else:
            return 0
        
    #-----linenumberarea
    def set_linenumberarea_enabled(self, state):
        self.linenumberarea_enabled = state
        self.linenumberarea.setVisible(state)
        self.update_linenumberarea_width(0)

    def get_linenumberarea_width(self):
        """Return current line number area width"""
        return self.linenumberarea.contentsRect().width()
    
    def compute_linenumberarea_width(self):
        """Compute and return line number area width"""
        if not self.linenumberarea_enabled:
            return 0
        digits = 1
        maxb = max(1, self.blockCount())
        while maxb >= 10:
            maxb /= 10
            digits += 1
        if self.linenumbers_margin:
            linenumbers_margin = 3+self.fontMetrics().width('9')*digits
        else:
            linenumbers_margin = 0
        return linenumbers_margin+self.get_markers_margin()
        
    def update_linenumberarea_width(self, new_block_count):
        """Update line number area width"""
        self.setViewportMargins(self.compute_linenumberarea_width(), 0,
                                self.get_scrollflagarea_width(), 0)
        
    def update_linenumberarea(self, qrect, dy):
        """Update line number area"""
        if dy:
            self.linenumberarea.scroll(0, dy)
        else:
            self.linenumberarea.update(0, qrect.y(),
                                       self.linenumberarea.width(),
                                       qrect.height())
        if qrect.contains(self.viewport().rect()):
            self.update_linenumberarea_width(0)
            
    def linenumberarea_paint_event(self, event):
        font_height = self.fontMetrics().height()
        painter = QPainter(self.linenumberarea)
        painter.fillRect(event.rect(), self.area_background_color)
                
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(
                                                    self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        painter.setPen(Qt.darkGray)
        def draw_pixmap(ytop, pixmap):
            painter.drawPixmap(0, ytop+(font_height-pixmap.height())/2, pixmap)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_number = block_number+1
                if self.linenumbers_margin:
                    number = QString.number(line_number)
                    painter.drawText(0, top, self.linenumberarea.width(),
                                     font_height, Qt.AlignRight|Qt.AlignBottom,
                                     number)
                data = block.userData()
                if self.markers_margin and data:
                    if data.code_analysis:
                        for _message, error in data.code_analysis:
                            if error:
                                break
                        if error:
                            draw_pixmap(top, self.error_pixmap)
                        else:
                            draw_pixmap(top, self.warning_pixmap)
                    if data.todo:
                        draw_pixmap(top, self.todo_pixmap)
                    if data.breakpoint:
                        if data.breakpoint_condition is None:
                            draw_pixmap(top, self.bp_pixmap)
                        else:
                            draw_pixmap(top, self.bpc_pixmap)
                    
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1
            
    def __get_linenumber_from_mouse_event(self, event):
        block = self.firstVisibleBlock()
        line_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(
                                                    self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top < event.pos().y():
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            line_number += 1
            
        return line_number
            
    def linenumberarea_mousepress_event(self, event):
        line_number = self.__get_linenumber_from_mouse_event(event)
        block = self.document().findBlockByNumber(line_number-1)
        data = block.userData()
        if data and data.code_analysis:
            self.__show_code_analysis_results(line_number, data.code_analysis)
            
    def linenumberarea_mousedoubleclick_event(self, event):
        line_number = self.__get_linenumber_from_mouse_event(event)
        shift = event.modifiers() & Qt.ShiftModifier
        self.add_remove_breakpoint(line_number, edit_condition=shift)
        
            
    #------Breakpoints
    def add_remove_breakpoint(self, line_number=None, condition=None,
                              edit_condition=False):
        if not self.is_python() and not self.is_cython():
            return
        if line_number is None:
            block = self.textCursor().block()
        else:
            block = self.document().findBlockByNumber(line_number-1)
        data = block.userData()
        if data:
            data.breakpoint = not data.breakpoint
        else:
            data = BlockUserData(self)
            data.breakpoint = True
        if condition is not None:
            data.breakpoint_condition = condition
        if edit_condition:
            data.breakpoint = True
            condition = data.breakpoint_condition
            if condition is None:
                condition = ''
            condition, valid = QInputDialog.getText(self,
                                        translate("SimpleEditor", 'Breakpoint'),
                                        translate("SimpleEditor", "Condition:"),
                                        QLineEdit.Normal, condition)
            if valid:
                condition = str(condition)
                if not condition:
                    condition = None
                data.breakpoint_condition = condition
            else:
                return
        if data.breakpoint:
            text = unicode(block.text()).strip()
            if len(text) == 0 or text.startswith('#') or text.startswith('"') \
               or text.startswith("'"):
                data.breakpoint = False
        block.setUserData(data)
        self.linenumberarea.update()
        self.scrollflagarea.update()
        
    def get_breakpoints(self):
        breakpoints = []
        block = self.document().firstBlock()
        for line_number in xrange(1, self.document().blockCount()+1):
            data = block.userData()
            if data and data.breakpoint:
                breakpoints.append((line_number, data.breakpoint_condition))
            block = block.next()
        return breakpoints
    
    def clear_breakpoints(self):
        for data in self.blockuserdata_list[:]:
            data.breakpoint = False
#            data.breakpoint_condition = None # not necessary, but logical
            if data.is_empty():
                del data
    
    def set_breakpoints(self, breakpoints):
        self.clear_breakpoints()
        for line_number, condition in breakpoints:
            self.add_remove_breakpoint(line_number, condition)
        
        
    #-----Code introspection
    def do_code_completion(self):
        if not self.is_completion_widget_visible():
            self.emit(SIGNAL('trigger_code_completion(bool)'), False)
            
    def do_go_to_definition(self):
        self.emit(SIGNAL("go_to_definition(int)"), self.textCursor().position())
            

    #-----scrollflagarea
    def set_scrollflagarea_enabled(self, state):
        self.scrollflagarea_enabled = state
        self.scrollflagarea.setVisible(state)
        self.update_linenumberarea_width(0)
            
    def get_scrollflagarea_width(self):
        if self.scrollflagarea_enabled:
            return ScrollFlagArea.WIDTH
        else:
            return 0
    
    def __set_scrollflagarea_painter(self, painter, light_color):
        painter.setPen(QColor(light_color).darker(120))
        painter.setBrush(QBrush(QColor(light_color)))
    
    def scrollflagarea_paint_event(self, event):
        cr = self.contentsRect()
        top = cr.top()+18
        hsbh = self.horizontalScrollBar().contentsRect().height()
        bottom = cr.bottom()-hsbh-22
        count = self.blockCount()
        
        make_flag = lambda line_nb: QRect(2, top+(line_nb-1)*(bottom-top)/count,
                                          self.scrollflagarea.WIDTH-4, 4)
        
        painter = QPainter(self.scrollflagarea)
        painter.fillRect(event.rect(), self.area_background_color)
        
        block = self.document().firstBlock()
        for line_number in xrange(1, self.document().blockCount()+1):
            data = block.userData()
            if data:
                if data.code_analysis:
                    # Warnings
                    color = self.warning_color
                    for _message, error in data.code_analysis:
                        if error:
                            color = self.error_color
                            break
                    self.__set_scrollflagarea_painter(painter, color)
                    painter.drawRect(make_flag(line_number))
                if data.todo:
                    # TODOs
                    self.__set_scrollflagarea_painter(painter, self.todo_color)
                    painter.drawRect(make_flag(line_number))
                if data.breakpoint:
                    # Breakpoints
                    self.__set_scrollflagarea_painter(painter,
                                                      self.breakpoint_color)
                    painter.drawRect(make_flag(line_number))
            block = block.next()
        # Occurences
        if self.occurences:
            self.__set_scrollflagarea_painter(painter, self.occurence_color)
            for line in self.occurences:
                painter.drawRect(make_flag(line))
                    
    def resizeEvent(self, event):
        """Reimplemented Qt method to handle line number area resizing"""
        TextEditBaseWidget.resizeEvent(self, event)
        cr = self.contentsRect()
        self.linenumberarea.setGeometry(\
                        QRect(cr.left(), cr.top(),
                              self.compute_linenumberarea_width(), cr.height()))
        self.__set_scrollflagarea_geometry(cr)
        
    def __set_scrollflagarea_geometry(self, contentrect):
        cr = contentrect
        if self.verticalScrollBar().isVisible():
            vsbw = self.verticalScrollBar().contentsRect().width()
        else:
            vsbw = 0
        _left, _top, right, _bottom = self.getContentsMargins()
        if right > vsbw:
            # Depending on the platform (e.g. on Ubuntu), the scrollbar sizes 
            # may be taken into account in the contents margins whereas it is 
            # not on Windows for example
            vsbw = 0
        self.scrollflagarea.setGeometry(\
                        QRect(cr.right()-ScrollFlagArea.WIDTH-vsbw, cr.top(),
                              self.scrollflagarea.WIDTH, cr.height()))

    #-----edgeline
    def viewportEvent(self, event):
        # 80-column edge line
        cr = self.contentsRect()
        offset = self.contentOffset()
        x = self.blockBoundingGeometry(self.firstVisibleBlock()) \
            .translated(offset.x(), offset.y()).left() \
            +self.get_linenumberarea_width() \
            +self.fontMetrics().width('9')*self.edge_line.column+5
        self.edge_line.setGeometry(\
                        QRect(x, cr.top(), 1, cr.bottom()))
        self.__set_scrollflagarea_geometry(cr)
        return TextEditBaseWidget.viewportEvent(self, event)

    #-----highlight current line
    def highlight_current_line(self):
        """Highlight current line"""
        if self.highlight_current_line_enabled:
            selection = QTextEdit.ExtraSelection()
            selection.format.setProperty(QTextFormat.FullWidthSelection,
                                         QVariant(True))
            selection.format.setBackground(self.currentline_color)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            self.set_extra_selections('current_line', [selection])
            self.update_extra_selections()
        else:
            self.clear_extra_selections('current_line')
        
    
    def delete(self):
        """Remove selected text"""
        # Used by global callbacks in Spyder -> delete_action
        self.remove_selected_text()
        
    def _apply_highlighter_color_scheme(self):
        hl = self.highlighter
        if hl is not None:
            self.set_palette(background=hl.get_background_color(),
                             foreground=hl.get_foreground_color())
            self.currentline_color = hl.get_currentline_color()
            self.occurence_color = hl.get_occurence_color()
            self.ctrl_click_color = hl.get_ctrlclick_color()
            self.area_background_color = hl.get_sideareas_color()
        self.highlight_current_line()
        
    def apply_highlighter_settings(self, color_scheme=None):
        if self.highlighter_class is not None:
            if not isinstance(self.highlighter, self.highlighter_class):
                # Highlighter object has not been constructed yet
                # or language has changed so it must be re-constructed
                if self.highlighter is not None:
                    # Removing old highlighter
                    self.highlighter.setParent(None)
                    self.highlighter.setDocument(None)
                self.highlighter = self.highlighter_class(self.document(),
                                                self.font(), self.color_scheme)
                self._apply_highlighter_color_scheme()
            else:
                # Highlighter object has already been created:
                # updating highlighter settings (font and color scheme)
                self.highlighter.setup_formats(self.font())
                if color_scheme is not None:
                    self.set_color_scheme(color_scheme)
                else:
                    self.highlighter.rehighlight()

    def set_font(self, font, color_scheme=None):
        """Set shell font"""
        # Note: why using this method to set color scheme instead of 
        #       'set_color_scheme'? To avoid rehighlighting the document twice
        #       at startup.
        if color_scheme is not None:
            self.color_scheme = color_scheme
        self.setFont(font)
        self.update_linenumberarea_width(0)
        self.apply_highlighter_settings(color_scheme)

    def set_color_scheme(self, color_scheme):
        self.color_scheme = color_scheme
        self.highlighter.set_color_scheme(color_scheme)
        self._apply_highlighter_color_scheme()
        
    def set_text(self, text):
        """Set the text of the editor"""
        self.setPlainText(text)
        self.set_eol_mode(text)
#        if self.supported_language:
#            self.highlighter.rehighlight()

    def append(self, text):
        """Append text to the end of the text widget"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)

    def paste(self):
        """
        Reimplement QPlainTextEdit's method to fix the following issue:
        on Windows, pasted text has only 'LF' EOL chars even if the original
        text has 'CRLF' EOL chars
        """
        clipboard = QApplication.clipboard()
        text = unicode(clipboard.text())
        if len(text.splitlines()) > 1:
            eol_chars = self.get_line_separator()
            clipboard.setText( eol_chars.join((text+eol_chars).splitlines()) )
        # Standard paste
        TextEditBaseWidget.paste(self)

    def get_block_data(self, block):
        return self.highlighter.block_data.get(block)

    def get_fold_level(self, block_nb):
        """Is it a fold header line?
        If so, return fold level
        If not, return None"""
        block = self.document().findBlockByNumber(block_nb)
        return self.get_block_data(block).fold_level
        
        
#===============================================================================
#    High-level editor features
#===============================================================================
    def _center_cursor(self):
        """QPlainTextEdit's "centerCursor" requires the widget to be visible"""
        self.centerCursor()
        self.disconnect(self, SIGNAL("focus_in()"), self._center_cursor)

    def go_to_line(self, line, word=''):
        """Go to line number *line* and eventually highlight it"""
        block = self.document().findBlockByNumber(line-1)
        cursor = self.textCursor()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        if self.isVisible():
            self.centerCursor()
        else:
            self.connect(self, SIGNAL("focus_in()"), self._center_cursor)
        self.horizontalScrollBar().setValue(0)
        if word and word in unicode(block.text()):
            self.find(word, QTextDocument.FindCaseSensitively)
        
    def cleanup_code_analysis(self):
        """Remove all code analysis markers"""
        self.clear_extra_selections('code_analysis')
        for data in self.blockuserdata_list[:]:
            data.code_analysis = []
            if data.is_empty():
                del data
        # When the new code analysis results are empty, it is necessary 
        # to update manually the scrollflag area (otherwise, the old flags 
        # will still be displayed):
        self.scrollflagarea.update()
        
    def process_code_analysis(self, check_results):
        """Analyze filename code with pyflakes"""
        self.cleanup_code_analysis()
        if check_results is None:
            # Not able to compile module
            return
        cursor = self.textCursor()
        document = self.document()
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        for message, line_number, error in check_results:
            # Note: line_number start from 1 (not 0)
            block = self.document().findBlockByNumber(line_number-1)
            data = block.userData()
            if not data:
                data = BlockUserData(self)
            data.code_analysis.append( (message, error) )
            block.setUserData(data)
            refs = re.findall(r"\'[a-zA-Z0-9_]*\'", message)
            for ref in refs:
                # Highlighting found references
                text = ref[1:-1]
                # Scanning line number *line* and following lines if continued
                def is_line_splitted(line_no):
                    text = unicode(document.findBlockByNumber(line_no).text())
                    stripped = text.strip()
                    return stripped.endswith('\\') or stripped.endswith(',') \
                           or len(stripped) == 0
                line2 = line_number-1
                while line2 < self.blockCount()-1 and is_line_splitted(line2):
                    line2 += 1
                cursor.setPosition(block.position())
                cursor.movePosition(QTextCursor.StartOfBlock)
                regexp = QRegExp(r"\b%s\b" % QRegExp.escape(text),
                                 Qt.CaseSensitive)
                cursor = document.find(regexp, cursor, flags)
                color = self.error_color if error else self.warning_color
                self.__highlight_selection('code_analysis', cursor,
                                           underline_color=QColor(color))
#                old_pos = None
#                if cursor:
#                    while cursor.blockNumber() <= line2 and cursor.position() != old_pos:
#                        self.__highlight_selection('code_analysis', cursor,
#                                       underline_color=self.warning_color)
#                        cursor = document.find(text, cursor, flags)
        self.update_extra_selections()

    def __show_code_analysis_results(self, line_number, code_analysis):
        """Show warning/error messages"""
        msglist = [ msg for msg, _error in code_analysis ]
        self.show_calltip(self.tr("Code analysis"), msglist,
                          color='#129625', at_line=line_number)

    def go_to_next_warning(self):
        """Go to next code analysis warning message
        and return new cursor position"""
        block = self.textCursor().block()
        line_count = self.document().blockCount()
        while True:
            if block.blockNumber()+1 < line_count:
                block = block.next()
            else:
                block = self.document().firstBlock()
            data = block.userData()
            if data and data.code_analysis:
                break
        line_number = block.blockNumber()+1
        self.go_to_line(line_number)
        self.__show_code_analysis_results(line_number, data.code_analysis)
        return self.get_position('cursor')

    def go_to_previous_warning(self):
        """Go to previous code analysis warning message
        and return new cursor position"""
        block = self.textCursor().block()
        while True:
            if block.blockNumber() > 0:
                block = block.previous()
            else:
                block = self.document().lastBlock()
            data = block.userData()
            if data and data.code_analysis:
                break
        line_number = block.blockNumber()+1
        self.go_to_line(line_number)
        self.__show_code_analysis_results(line_number, data.code_analysis)
        return self.get_position('cursor')

    
    #------Tasks management
    def go_to_next_todo(self):
        """Go to next todo and return new cursor position"""
        block = self.textCursor().block()
        line_count = self.document().blockCount()
        while True:
            if block.blockNumber()+1 < line_count:
                block = block.next()
            else:
                block = self.document().firstBlock()
            data = block.userData()
            if data and data.todo:
                break
        line_number = block.blockNumber()+1
        self.go_to_line(line_number)
        self.show_calltip(self.tr("To do"), data.todo,
                          color='#3096FC', at_line=line_number)
        return self.get_position('cursor')
            
    def process_todo(self, todo_results):
        """Process todo finder results"""
        for data in self.blockuserdata_list[:]:
            data.todo = ''
            if data.is_empty():
                del data
        for message, line_number in todo_results:
            block = self.document().findBlockByNumber(line_number-1)
            data = block.userData()
            if not data:
                data = BlockUserData(self)
            data.todo = message
            block.setUserData(data)
        self.scrollflagarea.update()
                
    
    #------Comments/Indentation
    def add_prefix(self, prefix):
        """Add prefix to current line or selected line(s)"""        
        cursor = self.textCursor()
        if self.has_selected_text():
            # Add prefix to selected line(s)
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
            
            # Let's see if selection begins at a block start
            first_pos = min([start_pos, end_pos])
            first_cursor = self.textCursor()
            first_cursor.setPosition(first_pos)
            begins_at_block_start = first_cursor.atBlockStart()
            
            cursor.beginEditBlock()
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            if cursor.atBlockStart():
                cursor.movePosition(QTextCursor.PreviousBlock)
                if cursor.position() < start_pos:
                    cursor.setPosition(start_pos)
                
            while cursor.position() >= start_pos:
                cursor.movePosition(QTextCursor.StartOfBlock)
                cursor.insertText(prefix)
                if start_pos == 0 and cursor.blockNumber() == 0:
                    # Avoid infinite loop when indenting the very first line
                    break
                cursor.movePosition(QTextCursor.PreviousBlock)
                cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.endEditBlock()
            if begins_at_block_start:
                # Extending selection to prefix:
                cursor = self.textCursor()
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                if start_pos < end_pos:
                    start_pos -= len(prefix)
                else:
                    end_pos -= len(prefix)
                cursor.setPosition(start_pos, QTextCursor.MoveAnchor)
                cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
        else:
            # Add prefix to current line
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.insertText(prefix)
    
    def __is_cursor_at_start_of_block(self, cursor):
        cursor.movePosition(QTextCursor.StartOfBlock)
        
    
    def remove_suffix(self, suffix):
        """
        Remove suffix from current line (there should not be any selection)
        """
        cursor = self.textCursor()
        cursor.setPosition(cursor.position()-len(suffix),
                           QTextCursor.KeepAnchor)
        if unicode(cursor.selectedText()) == suffix:
            cursor.removeSelectedText()
        
    def remove_prefix(self, prefix):
        """Remove prefix from current line or selected line(s)"""        
        cursor = self.textCursor()
        if self.has_selected_text():
            # Remove prefix from selected line(s)
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
            cursor.beginEditBlock()
            cursor.setPosition(end_pos)
            # Check if end_pos is at the start of a block: if so, starting
            # changes from the previous block
            if cursor.atBlockStart():
                cursor.movePosition(QTextCursor.PreviousBlock)
                if cursor.position() < start_pos:
                    cursor.setPosition(start_pos)
                
            old_pos = None
            while cursor.position() >= start_pos:
                new_pos = cursor.position()
                if old_pos == new_pos:
                    break
                else:
                    old_pos = new_pos
                cursor.movePosition(QTextCursor.StartOfBlock)
                cursor.setPosition(cursor.position()+len(prefix),
                                   QTextCursor.KeepAnchor)
                if unicode(cursor.selectedText()) == prefix:
                    cursor.removeSelectedText()
                cursor.movePosition(QTextCursor.PreviousBlock)
                cursor.movePosition(QTextCursor.EndOfBlock)
            cursor.endEditBlock()
        else:
            # Remove prefix from current line
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.setPosition(cursor.position()+len(prefix),
                               QTextCursor.KeepAnchor)
            if unicode(cursor.selectedText()) == prefix:
                cursor.removeSelectedText()
    
    def fix_indent(self, forward=True):
        """
        Fix indentation (Python only, no text selection)
        forward=True: fix indent only if text is not enough indented
                      (otherwise force indent)
        forward=False: fix indent only if text is too much indented
                       (otherwise force unindent)
                       
        Returns True if indent needed to be fixed
        """
        if not self.is_python() and not self.is_cython():
            return
        cursor = self.textCursor()
        block_nb = cursor.blockNumber()
        cursor.movePosition(QTextCursor.PreviousBlock)
        prevtext = unicode(cursor.block().text()).rstrip()
        indent = self.get_indentation(block_nb)
        correct_indent = self.get_indentation(block_nb-1)
        if prevtext.endswith(':'):
            # Indent            
            correct_indent += 4
        elif prevtext.endswith('continue') or prevtext.endswith('break') \
             or prevtext.endswith('pass'):
            # Unindent
            correct_indent -= 4
        elif prevtext.endswith(',') \
             and len(re.split(r'\(|\{|\[', prevtext)) > 1:
            rlmap = {")":"(", "]":"[", "}":"{"}
            for par in rlmap:
                i_right = prevtext.rfind(par)
                if i_right != -1:
                    prevtext = prevtext[:i_right]
                    for _i in range(len(prevtext.split(par))):
                        i_left = prevtext.rfind(rlmap[par])
                        if i_left != -1:
                            prevtext = prevtext[:i_left]
                        else:
                            break
            else:
                prevexpr = re.split(r'\(|\{|\[', prevtext)[-1]
                correct_indent = len(prevtext)-len(prevexpr)
                
        if (forward and indent >= correct_indent) or \
           (not forward and indent <= correct_indent):
            # No indentation fix is necessary
            return False
            
        if correct_indent >= 0:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.setPosition(cursor.position()+indent, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(" "*correct_indent)
            cursor.endEditBlock()
            return True
    
    def indent(self):
        """Indent current line or selection"""
        if self.has_selected_text():
            self.add_prefix(" "*4)
        elif not self.get_text('sol', 'cursor').strip() or \
             (self.tab_indents and self.tab_mode):
            if self.is_python() or self.is_cython():
                if not self.fix_indent(forward=True):
                    self.add_prefix(" "*4)
            else:
                self.add_prefix(" "*4)
        else:
            self.insert_text(" "*4)
            
    def indent_or_replace(self):
        """Indent or replace by 4 spaces depending on selection and tab mode"""
        if (self.tab_indents and self.tab_mode) or not self.has_selected_text():
            self.indent()
        else:
            cursor = self.textCursor()
            if self.get_selected_text() == unicode(cursor.block().text()):
                self.indent()
            else:
                cursor1 = self.textCursor()
                cursor1.setPosition(cursor.selectionStart())
                cursor2 = self.textCursor()
                cursor2.setPosition(cursor.selectionEnd())
                if cursor1.blockNumber() != cursor2.blockNumber():
                    self.indent()
                else:
                    self.replace(" "*4)
    
    def unindent(self):
        """Unindent current line or selection"""
        if self.has_selected_text():
            self.remove_prefix(" "*4)
        else:
            leading_text = self.get_text('sol', 'cursor')
            if not leading_text.strip() or (self.tab_indents and self.tab_mode):
                if self.is_python() or self.is_cython():
                    if not self.fix_indent(forward=False):
                        self.remove_prefix(" "*4)
                elif leading_text.endswith('\t'):
                    self.remove_prefix('\t')
                else:
                    self.remove_prefix(" "*4)
            
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
        cursor = self.textCursor()
        if self.has_selected_text():
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
            cursor.setPosition(start_pos)
            cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
            if cursor.atBlockStart():
                cursor.movePosition(QTextCursor.PreviousBlock,
                                    QTextCursor.KeepAnchor)
                cursor.movePosition(QTextCursor.EndOfBlock,
                                    QTextCursor.KeepAnchor)
                end_pos = cursor.position()
            self.setTextCursor(cursor)
            cursor.setPosition(start_pos)
        else:
            start_pos = end_pos = cursor.position()
        cursor.beginEditBlock()
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        while cursor.position() <= end_pos:
            cursor.insertText("# ")
            cursor.movePosition(QTextCursor.NextBlock)
        cursor.setPosition(end_pos)
        cursor.movePosition(QTextCursor.NextBlock)
        cursor.insertText(comline)
        cursor.setPosition(start_pos)
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.insertText(comline)
        cursor.endEditBlock()

    def __is_comment_bar(self, cursor):
        return cursor.block().text().startsWith('#' + '='*79)
    
    def unblockcomment(self):
        """Un-block comment current line or selection"""
        def __is_comment_bar(cursor):
            return cursor.block().text().startsWith('#' + '='*79)
        # Finding first comment bar
        cursor1 = self.textCursor()
        if __is_comment_bar(cursor1):
            return
        while not __is_comment_bar(cursor1):
            cursor1.movePosition(QTextCursor.PreviousBlock)
            if cursor1.atStart():
                break
        if not __is_comment_bar(cursor1):
            return
        def __in_block_comment(cursor):
            return cursor.block().text().startsWith('#')
        # Finding second comment bar
        cursor2 = QTextCursor(cursor1)
        cursor2.movePosition(QTextCursor.NextBlock)
        while not __is_comment_bar(cursor2) and __in_block_comment(cursor2):
            cursor2.movePosition(QTextCursor.NextBlock)
            if cursor2.block() == self.document().lastBlock():
                break
        if not __is_comment_bar(cursor2):
            return
        # Removing block comment
        cursor3 = self.textCursor()
        cursor3.beginEditBlock()
        cursor3.setPosition(cursor1.position())
        cursor3.movePosition(QTextCursor.NextBlock)
        while cursor3.position() < cursor2.position():
            cursor3.setPosition(cursor3.position()+2, QTextCursor.KeepAnchor)
            cursor3.removeSelectedText()
            cursor3.movePosition(QTextCursor.NextBlock)
        for cursor in (cursor2, cursor1):
            cursor3.setPosition(cursor.position())
            cursor3.select(QTextCursor.BlockUnderCursor)
            cursor3.removeSelectedText()
        cursor3.endEditBlock()
    
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
                           triggered=self.delete)
        selectall_action = create_action(self,
                           translate("SimpleEditor", "Select All"),
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
        text = unicode(event.text())
        if text:
            self.__clear_occurences()
        if QToolTip.isVisible():
            self.hide_tooltip_if_necessary(key)
        # Zoom in/out
        if key in (Qt.Key_Enter, Qt.Key_Return) and not shift and not ctrl:
            if self.is_completion_widget_visible() \
               and self.codecompletion_enter:
                self.select_completion_list()
            else:
                QPlainTextEdit.keyPressEvent(self, event)
                self.fix_indent()
        elif key == Qt.Key_Backspace and not shift and not ctrl:
            leading_text = self.get_text('sol', 'cursor')
            leading_length = len(leading_text)
            trailing_spaces = leading_length-len(leading_text.rstrip())
            if self.has_selected_text():
                QPlainTextEdit.keyPressEvent(self, event)
            else:
                trailing_text = self.get_text('cursor', 'eol')
                if leading_length > 4 and not leading_text.strip():
                    if leading_length % 4 == 0:
                        self.unindent()
                    else:
                        QPlainTextEdit.keyPressEvent(self, event)
                elif trailing_spaces and not trailing_text.strip():
                    self.remove_suffix(" "*trailing_spaces)
                elif leading_text and trailing_text and \
                     leading_text[-1]+trailing_text[0] in ('()', '[]', '{}'):
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.PreviousCharacter)
                    cursor.movePosition(QTextCursor.NextCharacter,
                                        QTextCursor.KeepAnchor, 2)
                    cursor.removeSelectedText()
                else:
                    QPlainTextEdit.keyPressEvent(self, event)
                    if self.is_completion_widget_visible():
                        self.completion_text = self.completion_text[:-1]
        elif key == Qt.Key_Period:
            self.insert_text(text)
            if self.codecompletion_auto:
                # Enable auto-completion only if last token isn't a float
                last_obj = getobj(self.get_text('sol', 'cursor'))
                if last_obj and not last_obj.isdigit():
                    self.emit(SIGNAL('trigger_code_completion(bool)'), True)
        elif key == Qt.Key_Home and not ctrl:
            self.stdkey_home(shift)
            event.accept()
        elif key == Qt.Key_ParenLeft and not self.has_selected_text():
            self.hide_completion_widget()
            position = self.get_position('cursor')
            s_trailing_text = self.get_text('cursor', 'eol').strip()
            if self.close_parentheses_enabled and \
               (len(s_trailing_text) == 0 or \
                s_trailing_text[0] in (',', ')', ']', '}')):
                self.insert_text('()')
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
            else:
                self.insert_text(text)
            if self.get_text('sol', 'cursor') and self.calltips:
                self.emit(SIGNAL('trigger_calltip(int)'), position)
            event.accept()
        elif key in (Qt.Key_BraceLeft, Qt.Key_BracketLeft) and \
             not self.has_selected_text() and self.close_parentheses_enabled:
            s_trailing_text = self.get_text('cursor', 'eol').strip()
            if len(s_trailing_text) == 0 or \
               s_trailing_text[0] in (',', ')', ']', '}'):
                self.insert_text({Qt.Key_BraceLeft: '{}',
                                  Qt.Key_BracketLeft: '[]'}[key])
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
                event.accept()
            else:
                QPlainTextEdit.keyPressEvent(self, event)
        elif key in (Qt.Key_ParenRight, Qt.Key_BraceRight, Qt.Key_BracketRight)\
             and not self.has_selected_text() and self.close_parentheses_enabled \
             and not self.textCursor().atBlockEnd():
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.NextCharacter,
                                QTextCursor.KeepAnchor)
            text = unicode(cursor.selectedText())
            if text == {Qt.Key_ParenRight: ')', Qt.Key_BraceRight: '}',
                        Qt.Key_BracketRight: ']'}[key]:
                cursor.clearSelection()
                self.setTextCursor(cursor)
                event.accept()
            else:
                QPlainTextEdit.keyPressEvent(self, event)
        elif key == Qt.Key_Colon and not self.has_selected_text() \
             and self.auto_unindent_enabled:
            leading_text = self.get_text('sol', 'cursor')
            if leading_text.lstrip() in ('else', 'finally'):
                ind = lambda txt: len(txt)-len(txt.lstrip())
                prevtxt = unicode(self.textCursor().block().previous().text())
                if ind(leading_text) == ind(prevtxt):
                    self.unindent()
            QPlainTextEdit.keyPressEvent(self, event)
        elif key == Qt.Key_Space and not shift and not ctrl \
             and not self.has_selected_text() and self.auto_unindent_enabled:
            leading_text = self.get_text('sol', 'cursor')
            if leading_text.lstrip() in ('elif', 'except'):
                ind = lambda txt: len(txt)-len(txt.lstrip())
                prevtxt = unicode(self.textCursor().block().previous().text())
                if ind(leading_text) == ind(prevtxt):
                    self.unindent()
            QPlainTextEdit.keyPressEvent(self, event)
        elif key == Qt.Key_Tab:
            # Important note: <TAB> can't be called with a QShortcut because
            # of its singular role with respect to widget focus management
            self.indent_or_replace()
        elif key == Qt.Key_Backtab:
            # Backtab, i.e. Shift+<TAB>, could be treated as a QShortcut but
            # there is no point since <TAB> can't (see above)
            self.unindent()
        else:
            QPlainTextEdit.keyPressEvent(self, event)
            if self.is_completion_widget_visible() and text:
                self.completion_text += text

    def mouseMoveEvent(self, event):
        """Underline words when pressing <CONTROL>"""
        if self.go_to_definition_enabled and \
           event.modifiers() & Qt.ControlModifier:
            text = self.get_word_at(event.pos())
            if text and (self.is_python() or self.is_cython()) \
               and not is_keyword(unicode(text)):
                if not self.__cursor_changed:
                    QApplication.setOverrideCursor(
                                                QCursor(Qt.PointingHandCursor))
                    self.__cursor_changed = True
                cursor = self.cursorForPosition(event.pos())
                cursor.select(QTextCursor.WordUnderCursor)
                self.clear_extra_selections('ctrl_click')
                self.__highlight_selection('ctrl_click', cursor, update=True,
                                foreground_color=self.ctrl_click_color,
                                underline_color=self.ctrl_click_color,
                                underline_style=QTextCharFormat.SingleUnderline)
                event.accept()
                return
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False
            self.clear_extra_selections('ctrl_click')
        QPlainTextEdit.mouseMoveEvent(self, event)
        
    def leaveEvent(self, event):
        """If cursor has not been restored yet, do it now"""
        if self.__cursor_changed:
            QApplication.restoreOverrideCursor()
            self.__cursor_changed = False
            self.clear_extra_selections('ctrl_click')
        QPlainTextEdit.leaveEvent(self, event)
            
    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if os.name != 'posix' and event.button() == Qt.MidButton:
            self.setFocus()
            event = QMouseEvent(QEvent.MouseButtonPress, event.pos(),
                                Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            QPlainTextEdit.mousePressEvent(self, event)
            QPlainTextEdit.mouseReleaseEvent(self, event)
            self.paste()
        elif event.button() == Qt.LeftButton \
             and (event.modifiers() & Qt.ControlModifier):
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()
            cursor.select(QTextCursor.WordUnderCursor)
            text = unicode(cursor.selectedText())
            QPlainTextEdit.mousePressEvent(self, event)
            if self.go_to_definition_enabled and text is not None and \
               (self.is_python() or self.is_cython()) and not is_keyword(text):
                self.emit(SIGNAL("go_to_definition(int)"), position)
        else:
            QPlainTextEdit.mousePressEvent(self, event)
            
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        state = self.has_selected_text()
        self.copy_action.setEnabled(state)
        self.cut_action.setEnabled(state)
        self.delete_action.setEnabled(state)
        self.undo_action.setEnabled( self.document().isUndoAvailable() )
        self.redo_action.setEnabled( self.document().isRedoAvailable() )
        menu = self.menu
        if self.isReadOnly():
            menu = self.readonly_menu
        menu.popup(event.globalPos())
        event.accept()
            
    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        if event.mimeData().hasText():
            TextEditBaseWidget.dragEnterEvent(self, event)
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        if event.mimeData().hasText():
            TextEditBaseWidget.dropEvent(self, event)
        else:
            event.ignore()


#===============================================================================
# CodeEditor's Printer
#===============================================================================

#TODO: Implement the header and footer support
class Printer(QPrinter):
    def __init__(self, mode=QPrinter.ScreenResolution, header_font=None):
        QPrinter.__init__(self, mode)
        self.setColorMode(QPrinter.Color)
        self.setPageOrder(QPrinter.FirstPageFirst)
        self.date = time.ctime()
        if header_font is not None:
            self.header_font = header_font
        
    # <!> The following method is simply ignored by QPlainTextEdit
    #     (this is a copy from QsciEditor's Printer)
    def formatPage(self, painter, drawing, area, pagenr):
        header = '%s - %s - Page %s' % (self.docName(), self.date, pagenr)
        painter.save()
        painter.setFont(self.header_font)
        painter.setPen(QColor(Qt.black))
        if drawing:
            painter.drawText(area.right()-painter.fontMetrics().width(header),
                             area.top()+painter.fontMetrics().ascent(), header)
        area.setTop(area.top()+painter.fontMetrics().height()+5)
        painter.restore()


#===============================================================================
# Editor + Class browser test
#===============================================================================
class TestEditor(CodeEditor):
    def __init__(self, parent):
        CodeEditor.__init__(self, parent)
        self.setup_editor(linenumbers=True, code_analysis=False,
                          todo_list=False)
        
    def load(self, filename):
        self.set_language(osp.splitext(filename)[1][1:])
        self.set_font(QFont("Courier New", 10), 'IDLE')
        self.set_text(file(filename, 'rb').read())
        self.setWindowTitle(filename)
#        self.setup_margins(True, True, True)

class TestWidget(QSplitter):
    def __init__(self, parent):
        QSplitter.__init__(self, parent)
        self.editor = TestEditor(self)
        self.addWidget(self.editor)
        self.classtree = OutlineExplorer(self)
        self.addWidget(self.classtree)
        self.connect(self.classtree, SIGNAL("edit_goto(QString,int,QString)"),
                     lambda _fn, line, word: self.editor.go_to_line(line, word))
        self.setStretchFactor(0, 4)
        self.setStretchFactor(1, 1)
        
    def load(self, filename):
        self.editor.load(filename)
        self.classtree.set_current_editor(self.editor, filename, False)
        
def test(fname):
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    win = TestWidget(None)
    win.show()
    win.load(fname)
    win.resize(800, 800)
    
    analysis_results = check(fname)
    win.editor.process_code_analysis(analysis_results)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = __file__
#        fname = r"d:\Python\scintilla\src\LexCPP.cxx"
        fname = r"C:\Python26\Lib\pdb.py"
#        fname = r"C:\Python26\Lib\ssl.py"
#        fname = r"D:\Python\testouille.py"
#        fname = r"C:\Python26\Lib\pydoc.py"
    test(fname)
# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Editor widget based on PyQt4.QtGui.QPlainTextEdit

******************************** WARNING ***************************************
    This module is currently not used in Spyder v1.x.
    This is still experimental but this will replace in time the current
    editor widget based on QScintilla
********************************************************************************
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
                         QPixmap, QPrinter)
from PyQt4.QtCore import Qt, SIGNAL, QString, QEvent, QTimer, QRect

# For debugging purpose:
STDOUT = sys.stdout

# Local import
from spyderlib.config import CONF, get_icon, get_image_path
from spyderlib.utils.qthelpers import (add_actions, create_action, keybinding,
                                       translate)
from spyderlib.widgets.qteditor.qtebase import TextEditBaseWidget
from spyderlib.widgets.qteditor.syntaxhighlighters import (PythonSH, CythonSH,
                                                           CppSH)
from spyderlib.widgets.editortools import (PythonCFM, ClassItem, FunctionItem,
                                           LineNumberArea, EdgeLine,
                                           ScrollFlagArea, check, ClassBrowser)
from spyderlib.utils import sourcecode, is_builtin, is_keyword


#===============================================================================
# QtEditor widget
#===============================================================================

#TODO: Create an autocompletion handler (instance of a 'AutoCompletionHandler' 
# class to be defined) and connect the 'import_statement' signal to a method of 
# this object.
# In this autocompletion handler, create an external shell by 
# refactoring a lot of code from spyderlib.widgets.externalshell,
# execute the import statements in this shell, and ask this shell 
# about code completion thanks to already existing 'getobjdir', ...
class QtEditor(TextEditBaseWidget):
    """
    QScintilla Base Editor Widget
    """
    LANGUAGES = {
                 ('py', 'pyw', 'python'): (PythonSH, '#', PythonCFM),
                 ('pyx',): (CythonSH, '#', PythonCFM),
#                 ('f', 'for'): (QsciLexerFortran77, 'c', None),
#                 ('f90', 'f95', 'f2k'): (QsciLexerFortran, '!', None),
#                 ('diff', 'patch', 'rej'): (QsciLexerDiff, '', None),
#                 'css': (QsciLexerCSS, '#', None),
#                 ('htm', 'html'): (QsciLexerHTML, '', None),
                 ('c', 'cpp', 'h', 'hpp', 'cxx'): (CppSH, '//', None),
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
        
        if os.name == 'nt':
            self.eol_mode = self.EOL_WINDOWS
        elif os.name == 'posix':
            self.eol_mode = self.EOL_UNIX
        else:
            self.eol_mode = self.EOL_MAC
        
        # 80-col edge line
        self.edge_line = EdgeLine(self)
        
        # Markers
        self.markers_margin = True
        self.markers_margin_width = 15
        self.error_pixmap = QPixmap(get_image_path('error.png'), 'png')
        self.warning_pixmap = QPixmap(get_image_path('warning.png'), 'png')
        self.todo_pixmap = QPixmap(get_image_path('todo.png'), 'png')
        
        # Line number area management
        self.linenumberarea = LineNumberArea(self)
        self.connect(self, SIGNAL("blockCountChanged(int)"),
                     self.update_linenumberarea_width)
        self.connect(self, SIGNAL("updateRequest(QRect,int)"),
                     self.update_linenumberarea)
        self.update_linenumberarea_width(0)
        
        # Highlight current line
        bcol = CONF.get('editor', 'currentline/backgroundcolor')
        bcol = QColor("#FFFF99") # IDLE color scheme
        bcol = QColor("#E8F2FE") # Pydev color scheme
        self.currentline_color = QColor(bcol)
        self.highlight_current_line()
        
        # Scrollbar flag area
        self.scrollflagarea = ScrollFlagArea(self)
        self.scrollflagarea.hide()
        self.warning_color = "#EFB870"
        self.error_color = "#ED9A91"
        self.todo_color = "#B4D4F3"
        
        self.highlighter_class = None
        self.highlighter = None
        
        self.setup_editor_args = None
        
        self.document_id = id(self)
                    
        # Indicate occurences of the selected word
        self.connect(self, SIGNAL('cursorPositionChanged()'),
                     self.__cursor_position_changed)
        self.__find_first_pos = None
        self.__find_flags = None

        self.supported_language = None
        self.classfunc_match = None
        self.__tree_cache = None
        self.comment_string = None

        # Code analysis markers: errors, warnings
        self.ca_marker_lines = {}
        
        # Todo finder
        self.todo_lines = {}
        
        # Mark occurences timer
        self.occurence_highlighting = None
        self.occurence_timer = QTimer(self)
        self.occurence_timer.setSingleShot(True)
        self.occurence_timer.setInterval(1500)
        self.connect(self.occurence_timer, SIGNAL("timeout()"), 
                     self.__mark_occurences)
        self.occurences = []
        bcol = QColor("#E8F2FE") # IDLE color scheme
        bcol = QColor("#FFFF99") # Pydev color scheme
        self.occurence_color = QColor(bcol)
        
        # Context menu
        self.setup_context_menu()
        
        # Tab key behavior
        self.tab_indents = None
        self.tab_mode = True # see QsciEditor.set_tab_mode
        
    def get_document_id(self):
        return self.document_id
        
    def set_as_clone(self, editor):
        """Set as clone editor"""
        self.setDocument(editor.document())
        self.document_id = editor.get_document_id()
        self.setup_editor(**editor.setup_editor_args)
        
    def setup_editor(self, linenumbers=True, language=None,
                     code_analysis=False, code_folding=False,
                     show_eol_chars=False, show_whitespace=False,
                     font=None, wrap=False, tab_mode=True,
                     occurence_highlighting=True, scrollflagarea=True,
                     todo_list=True):
        self.setup_editor_args = dict(
                linenumbers=linenumbers, language=language,
                code_analysis=code_analysis, code_folding=code_folding,
                show_eol_chars=show_eol_chars, show_whitespace=show_whitespace,
                font=font, wrap=wrap, tab_mode=tab_mode,
                occurence_highlighting=occurence_highlighting,
                scrollflagarea=scrollflagarea, todo_list=todo_list)
        
        # Scrollbar flag area
        self.set_scrollflagarea_enabled(scrollflagarea)
        
        # Lexer
        self.set_language(language)
                
        # Occurence highlighting
        self.set_occurence_highlighting(occurence_highlighting)
                
        # Tab always indents (even when cursor is not at the begin of line)
        self.tab_indents = language in self.TAB_ALWAYS_INDENTS
#        self.set_tab_mode(tab_mode)

        if font is not None:
            self.set_font(font)
        
#        self.setup_margins(linenumbers, code_analysis, code_folding)
        
        # Re-enable brace matching (already enabled in TextEditBaseWidget.setup
        # but for an unknown reason, changing the 'set_font' call above reset
        # this setting to default, which is no brace matching):
        # XXX: find out why
#        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
#        self.setMatchedBraceBackgroundColor(Qt.yellow)
        
        # Indentation (moved from QsciEditor.setup for the same reason as brace
        # matching -- see comment above)
#        self.setIndentationGuides(True)
#        self.setIndentationGuidesForegroundColor(Qt.lightGray)
        
#        self.set_eol_chars_visible(show_eol_chars)
#        self.set_whitespace_visible(show_whitespace)
        
        self.toggle_wrap_mode(wrap)
#        if self.is_python():
#            self.setup_api()
        self.setModified(False)
        
    def set_tab_mode(self, enable):
        """
        enabled = tab always indent
        (otherwise tab indents only when cursor is at the beginning of a line)
        """
        self.tab_mode = enable
        
    def set_occurence_highlighting(self, enable):
        """Enable/disable occurence highlighting"""
        self.occurence_highlighting = enable
        if not enable:
            self.__clear_occurences()

    def set_language(self, language):
        self.supported_language = False
        self.comment_string = ''
        if language is not None:
            for key in self.LANGUAGES:
                if language.lower() in key:
                    self.supported_language = True
                    sh_class, comment_string, CFMatch = self.LANGUAGES[key]
                    self.comment_string = comment_string
                    if CFMatch is None:
                        self.classfunc_match = None
                    else:
                        self.classfunc_match = CFMatch()
                    self.highlighter_class = sh_class
                
    def is_python(self):
        return self.highlighter_class is PythonSH
        
    def __remove_from_tree_cache(self, line=None, item=None):
        if line is None:
            for line, (_it, _level, _debug) in self.__tree_cache.iteritems():
                if _it is item:
                    break
        item, _level, debug = self.__tree_cache.pop(line)
        try:
            for child in [item.child(_i) for _i in range(item.childCount())]:
                self.__remove_from_tree_cache(item=child)
            item.parent().removeChild(item)
        except RuntimeError:
            # Item has already been deleted
            #XXX: remove this debug-related fragment of code
            print >>STDOUT, "unable to remove tree item: ", debug
        
    def populate_classbrowser(self, root_item):
        """Populate classes and functions browser (tree widget)"""
        if self.__tree_cache is None:
            self.__tree_cache = {}
        
        # Removing cached items for which line is > total line nb
        for _l in self.__tree_cache.keys():
            if _l >= self.blockCount():
                # Checking if key is still in tree cache in case one of its 
                # ancestors was deleted in the meantime (deleting all children):
                if _l in self.__tree_cache:
                    self.__remove_from_tree_cache(line=_l)
        
        ancestors = [(root_item, 0)]
        previous_item = None
        previous_level = None
        
        iterator = self.highlighter.get_classbrowser_data_iterator()
        for block_nb, data in iterator():
            if data is None:
                level = None
            else:
                level = data.fold_level
            citem, clevel, _d = self.__tree_cache.get(block_nb,
                                                      (None, None, ""))
            
            # Skip iteration if line is not the first line of a foldable block
            if level is None:
                if citem is not None:
                    self.__remove_from_tree_cache(line=block_nb)
                continue
            
            # Searching for class/function statements
            class_name = data.get_class_name()
            if class_name is None:
                func_name = data.get_function_name()
                if func_name is None:
                    if citem is not None:
                        self.__remove_from_tree_cache(line=block_nb)
                    continue
                
            if previous_level is not None:
                if level == previous_level:
                    pass
                elif level > previous_level:
                    ancestors.append((previous_item, previous_level))
                else:
                    while len(ancestors) > 1 and level <= previous_level:
                        ancestors.pop(-1)
                        _item, previous_level = ancestors[-1]
            parent, _level = ancestors[-1]
            
            if citem is not None:
                cname = unicode(citem.text(0))
                
            preceding = root_item if previous_item is None else previous_item
            if class_name is not None:
                if citem is not None:
                    if class_name == cname and level == clevel:
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        self.__remove_from_tree_cache(line=block_nb)
                item = ClassItem(class_name, block_nb, parent, preceding)
            else:
                if citem is not None:
                    if func_name == cname and level == clevel:
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        self.__remove_from_tree_cache(line=block_nb)
                item = FunctionItem(func_name, block_nb, parent, preceding)
                if item.is_method() and block_nb > 0:
                    decorator = self.classfunc_match.get_decorator(data.text)
                    item.set_decorator(decorator)
            item.setup()
            debug = "%s -- %s/%s" % (str(item.line).rjust(6),
                                     unicode(item.parent().text(0)),
                                     unicode(item.text(0)))
            self.__tree_cache[block_nb] = (item, level, debug)
            previous_level = level
            previous_item = item
        
        
#===============================================================================
#    QScintilla
#===============================================================================
    def setup(self):
        """Reimplement TextEditBaseWidget method"""
        TextEditBaseWidget.setup(self)

    def setup_margins(self, linenumbers=True, code_analysis=False,
                      code_folding=False, todo_list=True):
        """
        Setup margin settings
        (except font, now set in self.set_font)
        """
        # linenumbers argument is ignored
        # code_folding argument is not supported
        self.markers_margin =  code_analysis or todo_list
        
    def set_whitespace_visible(self, state):
        """Show/hide whitespace"""
        raise NotImplementedError
    
    def set_eol_chars_visible(self, state):
        """Show/hide EOL characters"""
        self.setEolVisibility(state)
    
    def convert_eol_chars(self):
        """Convert EOL characters to current mode"""
        self.convertEols(self.eolMode())
        
    def remove_trailing_spaces(self):
        """Remove trailing spaces"""
        text_before = unicode(self.text())
        text_after = sourcecode.remove_trailing_spaces(text_before)
        if text_before != text_after:
            self.setText(text_after)
            
    def fix_indentation(self):
        """Replace tabs by spaces"""
        text_before = unicode(self.text())
        text_after = sourcecode.fix_indentation(text_before)
        if text_before != text_after:
            self.setText(text_after)
    
    def set_eol_mode(self, text):
        """
        Set widget EOL mode based on *text* EOL characters
        """
        if isinstance(text, QString):
            text = unicode(text)
        eol_chars = sourcecode.get_eol_chars(text)
        if eol_chars is not None:
            self.eol_mode = self.EOL_MODES[eol_chars]
        
    def get_line_separator(self):
        """Return line separator based on current EOL mode"""
        for eol_chars, mode in self.EOL_MODES.iteritems():
            if self.eol_mode == mode:
                return eol_chars
        else:
            return ''
    
    def __find_first(self, text):
        """Find first occurence: scan whole document"""
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        cursor = self.textCursor()
        # Scanning whole document
        cursor.movePosition(QTextCursor.Start)
        cursor = self.document().find(text, cursor, flags)
        self.__find_first_pos = cursor.position()
        return cursor
    
    def __find_next(self, text, cursor):
        """Find next occurence"""
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        cursor = self.document().find(text, cursor, flags)
        if cursor.position() != self.__find_first_pos:
            return cursor
        
    def __cursor_position_changed(self):
        """Cursor position has changed"""
        self.highlight_current_line()
        if self.occurence_highlighting:
            self.occurence_timer.stop()
            self.occurence_timer.start()
        
    def __clear_occurences(self):
        """Clear occurence markers"""
        self.occurences = []
        self.clear_extra_selections('occurences')
        self.scrollflagarea.update()

    def __highlight_selection(self, key, cursor, background_color=None,
                              underline_color=None, update=False):
        extra_selections = self.get_extra_selections(key)
        selection = QTextEdit.ExtraSelection()
        if background_color is not None:
            selection.format.setBackground(background_color)
        if underline_color is not None:
            selection.format.setProperty(QTextFormat.TextUnderlineStyle,
                                         QTextCharFormat.SpellCheckUnderline)
            selection.format.setProperty(QTextFormat.TextUnderlineColor,
                                         underline_color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = cursor
        extra_selections.append(selection)
        self.set_extra_selections(key, extra_selections)
        if update:
            self.update_extra_selections()
        
    def __mark_occurences(self):
        """Marking occurences of the currently selected word"""
        self.__clear_occurences()

        if not self.supported_language or self.hasSelectedText():
            return
            
        text = self.get_current_word()
        if text is None:
            return
        if self.is_python() and \
           (is_builtin(unicode(text)) or is_keyword(unicode(text))):
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
    def get_linenumberarea_width(self):
        """Return line number area width"""
        digits = 1
        maxb = max(1, self.blockCount())
        while maxb >= 10:
            maxb /= 10
            digits += 1
        return 3+self.fontMetrics().width('9')*digits+self.get_markers_margin()
        
    def update_linenumberarea_width(self, new_block_count):
        """Update line number area width"""
        self.setViewportMargins(self.get_linenumberarea_width(), 0,
                                ScrollFlagArea.WIDTH, 0)
        
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
        painter.fillRect(event.rect(), QColor("#EFEFEF"))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(
                                                    self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = QString.number(block_number+1)
                painter.setPen(Qt.darkGray)
                painter.drawText(0, top, self.linenumberarea.width(),
                                 font_height, Qt.AlignRight|Qt.AlignBottom,
                                 number)
                code_analysis = self.ca_marker_lines.get(block_number)
                if code_analysis is not None:
                    for _message, error in code_analysis:
                        if error:
                            break
                    pixmap = self.error_pixmap if error else self.warning_pixmap
                    painter.drawPixmap(0, top+(font_height-pixmap.height())/2,
                                       pixmap)
                todo = self.todo_lines.get(block_number)
                if todo is not None:
                    pixmap = self.todo_pixmap
                    painter.drawPixmap(0, top+(font_height-pixmap.height())/2,
                                       pixmap)
                    
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    #-----scrollflagarea
    def set_scrollflagarea_enabled(self, state):
        if state:
            self.scrollflagarea.show()
            self.setViewportMargins(0, 0, ScrollFlagArea.WIDTH, 0)
        else:
            self.scrollflagarea.hide()
            self.setViewportMargins(0, 0, 0, 0)
    
    def __set_scrollflagarea_painter(self, painter, light_color):
        painter.setPen(QColor(light_color).darker(120))
        painter.setBrush(QBrush(QColor(light_color)))
    
    def scrollflagarea_paint_event(self, event):
        cr = self.contentsRect()
        top = cr.top()+18
        hsbh = self.horizontalScrollBar().contentsRect().height()
        bottom = cr.bottom()-hsbh-22
        count = self.blockCount()
        
        make_flag = lambda nb: QRect(2, top+nb*(bottom-top)/count,
                                     self.scrollflagarea.WIDTH-4, 4)
        
        painter = QPainter(self.scrollflagarea)
        painter.fillRect(event.rect(), QColor("#EFEFEF"))
        
        # Warnings
        self.__set_scrollflagarea_painter(painter, self.warning_color)
        errors = []
        for line, item in self.ca_marker_lines.iteritems():
            for _message, error in item:
                if error:
                    errors.append(line)
                    break
            if error:
                continue
            painter.drawRect(make_flag(line))
        # Errors
        self.__set_scrollflagarea_painter(painter, self.error_color)
        for line in errors:
            painter.drawRect(make_flag(line))
        # Occurences
        self.__set_scrollflagarea_painter(painter, self.occurence_color)
        for line in self.occurences:
            painter.drawRect(make_flag(line))
        # TODOs
        self.__set_scrollflagarea_painter(painter, self.todo_color)
        for line in self.todo_lines:
            painter.drawRect(make_flag(line))
                    
    def resizeEvent(self, event):
        """Reimplemented Qt method to handle line number area resizing"""
        super(QtEditor, self).resizeEvent(event)
        cr = self.contentsRect()
        self.linenumberarea.setGeometry(\
                        QRect(cr.left(), cr.top(),
                              self.get_linenumberarea_width(), cr.height()))
        vsbw = self.verticalScrollBar().contentsRect().width()
        self.scrollflagarea.setGeometry(\
                        QRect(cr.right()-ScrollFlagArea.WIDTH-vsbw, cr.top(),
                              self.scrollflagarea.WIDTH, cr.height()))

    #-----edgeline
    def viewportEvent(self, event):
        # 80-column edge line
        cr = self.contentsRect()
        x = self.blockBoundingGeometry(self.firstVisibleBlock()) \
            .translated(self.contentOffset()).left() \
            +self.linenumberarea.contentsRect().width() \
            +self.fontMetrics().width('9')*self.edge_line.column+5
        self.edge_line.setGeometry(\
                        QRect(x, cr.top(), 1, cr.bottom()))
        return super(QtEditor, self).viewportEvent(event)

    #-----highlight current line
    def highlight_current_line(self):
        """Highlight current line"""
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.format.setBackground(self.currentline_color)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            self.set_extra_selections('current_line', [selection])
            self.update_extra_selections()
        
    
    def delete(self):
        """Remove selected text"""
        # Used by global callbacks in Spyder -> delete_action
        self.removeSelectedText()

    def set_font(self, font):
        """Set shell font"""
        self.setFont(font)
        self.update_linenumberarea_width(0)
        if self.highlighter_class is not None:
            if not isinstance(self.highlighter, self.highlighter_class):
                self.highlighter = self.highlighter_class(self.document(), font)
            else:
                self.highlighter.setup_formats(font)
                self.highlighter.rehighlight()
#        margin_font = QFont(font)
#        margin_font.setPointSize(margin_font.pointSize()-1)
#        self.setMarginsFont(margin_font)
        
    def set_text(self, text):
        """Set the text of the editor"""
        self.setPlainText(text)
        self.set_eol_mode(text)
#        if self.supported_language:
#            self.highlighter.rehighlight()

    def paste(self):
        """
        Reimplement QsciScintilla's method to fix the following issue:
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

    def get_block_data(self, block_nb):
        block = self.document().findBlockByNumber(block_nb)
        return self.highlighter.block_data.get(block)

    def get_fold_level(self, block_nb):
        """Is it a fold header line?
        If so, return fold level
        If not, return None"""
        block = self.document().findBlockByNumber(block_nb)
        return self.get_block_data(block).fold_level
    
    def fold_expanded(self, line):
        """Is fold expanded?"""
        raise NotImplementedError
        
    def get_folded_lines(self):
        """Return the list of folded line numbers"""
        raise NotImplementedError
        
    def unfold_all(self):
        """Unfold all folded lines"""
        raise NotImplementedError
        
        
#===============================================================================
#    High-level editor features
#===============================================================================
    def highlight_line(self, line):
        """Highlight line number *line*"""
        block = self.document().findBlockByNumber(line-1)
        cursor = self.textCursor()
        cursor.setPosition(block.position())
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.horizontalScrollBar().setValue(0)
        
    def go_to_line(self, line):
        """Go to line number *line*"""
        position = self.document().findBlockByNumber(line).position()
        self.set_cursor_position(position)
        
    def cleanup_code_analysis(self):
        """Remove all code analysis markers"""
        self.clear_extra_selections('code_analysis')
        self.ca_marker_lines = {}
        
    def process_code_analysis(self, check_results):
        """Analyze filename code with pyflakes"""
        self.cleanup_code_analysis()
        if check_results is None:
            # Not able to compile module
            return
        cursor = self.textCursor()
        document = self.document()
        flags = QTextDocument.FindCaseSensitively|QTextDocument.FindWholeWords
        for message, line0, error in check_results:
            line1 = line0 - 1
            if line1 not in self.ca_marker_lines:
                self.ca_marker_lines[line1] = []
            self.ca_marker_lines[line1].append( (message, error) )
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
                line2 = line1
                while line2 < self.blockCount()-1 and is_line_splitted(line2):
                    line2 += 1
                cursor.setPosition(document.findBlockByNumber(line1).position())
                cursor.movePosition(QTextCursor.StartOfBlock)
                cursor = document.find(text, cursor, flags)
                self.__highlight_selection('code_analysis', cursor,
                                   underline_color=QColor(self.warning_color))
#                old_pos = None
#                if cursor:
#                    while cursor.blockNumber() <= line2 and cursor.position() != old_pos:
#                        self.__highlight_selection('code_analysis', cursor,
#                                       underline_color=self.warning_color)
#                        cursor = document.find(text, cursor, flags)
        self.update_extra_selections()

    def __highlight_warning(self, line):
        self.highlight_line(line+1)
        self.__show_code_analysis_results(line)

    def go_to_next_warning(self):
        """Go to next code analysis warning message"""
        cline = self.get_cursor_line_number()
        lines = sorted(self.ca_marker_lines.keys())
        for line in lines:
            if line > cline:
                self.__highlight_warning(line)
                return
        else:
            self.__highlight_warning(lines[0])

    def go_to_previous_warning(self):
        """Go to previous code analysis warning message"""
        cline = self.get_cursor_line_number()
        lines = sorted(self.ca_marker_lines.keys(), reverse=True)
        for line in lines:
            if line < cline:
                self.__highlight_warning(line)
                return
        else:
            self.__highlight_warning(lines[0])

    def __show_code_analysis_results(self, line):
        """Show warning/error messages"""
        if line in self.ca_marker_lines:
            msglist = [ msg for msg, _error in self.ca_marker_lines[line] ]
            self.show_calltip(self.tr("Code analysis"), msglist,
                              color='#129625', at_line=line)
    
    def __margin_clicked(self, margin, line, modifier):
        """Margin was clicked, that's for sure!"""
        if margin == 0:
            self.__show_code_analysis_results(line)

    
    #------Tasks management
    def __show_todo(self, line):
        """Show todo message"""
        if line in self.todo_lines:
            self.show_calltip(self.tr("To do"), self.todo_lines[line],
                              color='#3096FC', at_line=line)

    def __highlight_todo(self, line):
        self.highlight_line(line+1)
        self.__show_todo(line)

    def go_to_next_todo(self):
        """Go to next todo"""
        cline = self.get_cursor_line_number()
        lines = sorted(self.todo_lines.keys())
        for line in lines:
            if line > cline:
                self.__highlight_todo(line)
                return
        else:
            self.__highlight_todo(lines[0])
            
    def process_todo(self, todo_results):
        """Process todo finder results"""
        self.todo_lines = {}
        for message, line in todo_results:
            self.todo_lines[line-1] = message
        self.scrollflagarea.update()
                
    
    #------Comments/Indentation
    def add_prefix(self, prefix):
        """Add prefix to current line or selected line(s)"""        
        cursor = self.textCursor()
        if self.hasSelectedText():
            # Add prefix to selected line(s)
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
            cursor.beginEditBlock()
            cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.StartOfBlock)
            while cursor.position() < end_pos:
                cursor.insertText(prefix)
                cursor.movePosition(QTextCursor.NextBlock)
            cursor.endEditBlock()
        else:
            # Add prefix to current line
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.insertText(prefix)
    
    def remove_prefix(self, prefix):
        """Remove prefix from current line or selected line(s)"""        
        cursor = self.textCursor()
        if self.hasSelectedText():
            # Remove prefix from selected line(s)
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
            cursor.beginEditBlock()
            cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.StartOfBlock)
            while cursor.position() < end_pos:
                cursor.setPosition(cursor.position()+len(prefix),
                                   QTextCursor.KeepAnchor)
                if unicode(cursor.selectedText()) != prefix:
                    break
                cursor.removeSelectedText()
                cursor.movePosition(QTextCursor.NextBlock)
            cursor.endEditBlock()
        else:
            # Remove prefix from current line
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.setPosition(cursor.position()+len(prefix),
                               QTextCursor.KeepAnchor)
            if unicode(cursor.selectedText()) != prefix:
                return
            cursor.removeSelectedText()
    
    def fix_indent(self, forward=True):
        """
        Fix indentation (Python only, no text selection)
        forward=True: fix indent only if text is not enough indented
                      (otherwise force indent)
        forward=False: fix indent only if text is too much indented
                       (otherwise force unindent)
        """
        if not self.is_python():
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
        elif prevtext.endswith('continue') or prevtext.endswith('break'):
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
        if forward:
            if indent == correct_indent or indent > correct_indent:
                # Force indent
                correct_indent = indent + 4
        elif indent == correct_indent or indent < correct_indent:
            # Force unindent
            correct_indent = indent - 4
            
        if correct_indent >= 0:
            cursor = self.textCursor()
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.setPosition(cursor.position()+indent, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(" "*correct_indent)
            cursor.endEditBlock()
    
    def __no_char_before_cursor(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        return len(unicode(cursor.selectedText()).strip()) == 0
    
    def indent(self):
        """Indent current line or selection"""
        if self.hasSelectedText():
            self.add_prefix(" "*4)
        elif self.__no_char_before_cursor() or \
             (self.tab_indents and self.tab_mode):
            if self.is_python():
                self.fix_indent(forward=True)
            else:
                self.add_prefix(" "*4)
        else:
            self.insert_text(" "*4)
    
    def unindent(self):
        """Unindent current line or selection"""
        if self.hasSelectedText():
            self.remove_prefix( " "*4 )
        elif self.__no_char_before_cursor() or \
             (self.tab_indents and self.tab_mode):
            if self.is_python():
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
        cursor = self.textCursor()
        if self.hasSelectedText():
            start_pos, end_pos = cursor.selectionStart(), cursor.selectionEnd()
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
        # Finding first comment bar
        cursor1 = self.textCursor()
        if self.__is_comment_bar(cursor1):
            return
        while cursor1.position() > 0 and not self.__is_comment_bar(cursor1):
            cursor1.movePosition(QTextCursor.PreviousBlock)
        if not self.__is_comment_bar(cursor1):
            return
        # Finding second comment bar
        cursor2 = self.textCursor()
        while cursor2.position() > 0 and not self.__is_comment_bar(cursor2):
            cursor2.movePosition(QTextCursor.NextBlock)
        if not self.__is_comment_bar(cursor2):
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
             or ((key == Qt.Key_Equal) and shift and ctrl):
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
                self.select_completion_list()
            else:
                self.indent()
            event.accept()
        elif (key == Qt.Key_V) and ctrl:
            self.paste()
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
            QPlainTextEdit.keyPressEvent(self, event)
            
    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() == Qt.MidButton:
            self.setFocus()
            event = QMouseEvent(QEvent.MouseButtonPress, event.pos(),
                                Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            QPlainTextEdit.mousePressEvent(self, event)
            QPlainTextEdit.mouseReleaseEvent(self, event)
            self.paste()
        else:
            QPlainTextEdit.mousePressEvent(self, event)
            
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
            
    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        if event.mimeData().hasText():
            super(QtEditor, self).dragEnterEvent(event)
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        if event.mimeData().hasText():
            super(QtEditor, self).dropEvent(event)
        else:
            event.ignore()


#===============================================================================
# QtEditor's Printer
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
class TestEditor(QtEditor):
    def __init__(self, parent):
        super(TestEditor, self).__init__(parent)
        self.setup_editor(code_folding=True)
        
    def load(self, filename):
        self.set_language(osp.splitext(filename)[1][1:])
        self.set_font(QFont("Courier New", 10))
        self.set_text(file(filename, 'rb').read())
        self.setWindowTitle(filename)
#        self.setup_margins(True, True, True)

class TestWidget(QSplitter):
    def __init__(self, parent):
        super(TestWidget, self).__init__(parent)
        self.editor = TestEditor(self)
        self.addWidget(self.editor)
        self.classtree = ClassBrowser(self)
        self.addWidget(self.classtree)
        self.connect(self.classtree, SIGNAL("edit_goto(QString,int,bool)"),
                     lambda _fn, line, _h: self.editor.highlight_line(line))
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
#        fname = r"C:\Documents and Settings\Famille Baudrier\Bureau\scintilla\src\LexCPP.cxx"
#        fname = r"d:\Python\sandbox.pyw"
    test(fname)

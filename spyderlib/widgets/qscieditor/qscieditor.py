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

import sys, os, re, time, os.path as osp
from math import log

from PyQt4.QtGui import (QMouseEvent, QColor, QMenu, QPixmap, QPrinter, QWidget,
                         QApplication, QTreeWidgetItem, QSplitter, QFont,
                         QHBoxLayout, QVBoxLayout, QPainter, QBrush)
from PyQt4.QtCore import Qt, SIGNAL, QString, QEvent, QTimer, QRect
from PyQt4.Qsci import (QsciScintilla, QsciAPIs, QsciLexerCPP, QsciLexerCSS,
                        QsciLexerDiff, QsciLexerHTML, QsciLexerPython,
                        QsciLexerProperties, QsciLexerBatch, QsciPrinter)
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
from spyderlib.utils.qthelpers import (add_actions, create_action, keybinding,
                                       translate, create_toolbutton,
                                       set_item_user_text)
from spyderlib.utils import sourcecode, is_builtin, is_keyword
from spyderlib.widgets import OneColumnTree
from spyderlib.widgets.qscieditor.qscibase import TextEditBaseWidget


#===============================================================================
# Pyflakes code analysis
#===============================================================================
import compiler

def check(filename):
    try:
        import pyflakes.checker
    except ImportError:
        return []
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
        w = pyflakes.checker.Checker(tree, filename)
        w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
        for warning in w.messages:
            results.append( (warning.message % warning.message_args,
                             warning.lineno, False) )
        return results

if __name__ == '__main__':
    check_results = check(osp.abspath("../../spyder.py"))
    for message, line, error in check_results:
        print "Message: %s -- Line: %s -- Error? %s" % (message, line, error)


#===============================================================================
# Class browser
#===============================================================================
class PythonClassFuncMatch(object):
    """
    Collection of helpers to match functions and classes
    for Python language
    This has to be reimplemented for other languages for the class browser 
    to be supported (not implemented yet: class browser won't be populated
    unless the current script is a Python script)
    """
    def __get_name(self, statmt, text):
        match = re.match(r'[\ ]*%s ([a-zA-Z0-9_]*)[\ ]*[\(|\:]' % statmt, text)
        if match is not None:
            return match.group(1)
        
    def get_function_name(self, text):
        return self.__get_name('def', text)
    
    def get_class_name(self, text):
        return self.__get_name('class', text)
    
    def get_decorator(self, text):
        match = re.match(r'[\ ]*\@([a-zA-Z0-9_]*)', text)
        if match is not None:
            return match.group(1)


class FileRootItem(QTreeWidgetItem):
    def __init__(self, path, treewidget):
        QTreeWidgetItem.__init__(self, treewidget)
        self.path = path
        self.setIcon(0, get_icon('python.png'))
        self.setToolTip(0, path)
        set_item_user_text(self, path)
        
    def set_text(self, fullpath):
        self.setText(0, self.path if fullpath else osp.basename(self.path))
        
class TreeItem(QTreeWidgetItem):
    """Class browser item base class"""
    def __init__(self, name, line, parent, preceding):
        if preceding is None:
            QTreeWidgetItem.__init__(self, parent, QTreeWidgetItem.Type)
        else:
            if preceding is not parent:
                # Preceding must be either the same as item's parent
                # or have the same parent as item
                while preceding.parent() is not parent:
                    preceding = preceding.parent()
            QTreeWidgetItem.__init__(self, parent, preceding,
                                     QTreeWidgetItem.Type)
        self.setText(0, name)
        parent_text = unicode(parent.data(0, Qt.UserRole).toString())
        set_item_user_text(self, parent_text+'/'+name)
        self.line = line
        
    def set_icon(self, icon_name):
        self.setIcon(0, get_icon(icon_name))
        
    def setup(self):
        raise NotImplementedError

class ClassItem(TreeItem):
    def setup(self):
        self.set_icon('class.png')
        self.setToolTip(0, translate("ClassBrowser",
                             "Class defined at line %1").arg(str(self.line)))

class FunctionItem(TreeItem):
    def __init__(self, name, line, parent, preceding):
        super(FunctionItem, self).__init__(name, line, parent, preceding)
        self.decorator = None
        
    def set_decorator(self, decorator):
        self.decorator = decorator
        
    def is_method(self):
        return isinstance(self.parent(), ClassItem)
    
    def setup(self):
        if self.is_method():
            self.setToolTip(0, translate("ClassBrowser",
                             "Method defined at line %1").arg(str(self.line)))
            if self.decorator is not None:
                self.set_icon('decorator.png')
            else:
                name = unicode(self.text(0))
                if name.startswith('__'):
                    self.set_icon('private2.png')
                elif name.startswith('_'):
                    self.set_icon('private1.png')
                else:
                    self.set_icon('method.png')
        else:
            self.set_icon('function.png')
            self.setToolTip(0, translate("ClassBrowser",
                             "Function defined at line %1").arg(str(self.line)))


def get_item_children(item):
    children = [item.child(index) for index in range(item.childCount())]
    for child in children[:]:
        others = get_item_children(child)
        if others is not None:
            children += others
    return sorted(children, key=lambda child: child.line)

def item_at_line(root_item, line):
    previous_item = root_item
    for item in get_item_children(root_item):
        if item.line > line:
            return previous_item
        previous_item = item


class ClassBrowserTreeWidget(OneColumnTree):
    def __init__(self, parent, show_fullpath=False, fullpath_sorting=True):
        self.show_fullpath = show_fullpath
        self.fullpath_sorting = fullpath_sorting
        OneColumnTree.__init__(self, parent)
        self.freeze = False # Freezing widget to avoid any unwanted update
        self.editor_items = {}
        self.editor_ids = {}
        self.current_editor = None
        title = translate("ClassBrowser", "Classes and functions")
        self.set_title(title)
        self.setWindowTitle(title)

    def get_actions_from_items(self, items):
        """Reimplemented OneColumnTree method"""
        fromcursor_act = create_action(self,
                        text=translate('ClassBrowser', 'Go to cursor position'),
                        icon=get_icon('fromcursor.png'),
                        triggered=self.go_to_cursor_position)
        fullpath_act = create_action(self,
                        text=translate('ClassBrowser', 'Show absolute path'),
                        toggled=self.toggle_fullpath_mode)
        fullpath_act.setChecked(self.show_fullpath)
        actions = [fullpath_act, fromcursor_act]
        return actions
    
    def toggle_fullpath_mode(self, state):
        self.show_fullpath = state
        self.setTextElideMode(Qt.ElideMiddle if state else Qt.ElideRight)
        for index in range(self.topLevelItemCount()):
            self.topLevelItem(index).set_text(fullpath=self.show_fullpath)
            
    def set_fullpath_sorting(self, state):
        self.fullpath_sorting = state
        self.__sort_toplevel_items()
        
    def go_to_cursor_position(self):
        if self.current_editor is None:
            return
        line = self.current_editor.get_cursor_line_number()
        editor_id = self.editor_ids[self.current_editor]
        root_item = self.editor_items[editor_id]
        item = item_at_line(root_item, line)
        self.setCurrentItem(item)
        self.scrollToItem(item)
                
    def clear(self):
        """Reimplemented Qt method"""
        self.set_title('')
        OneColumnTree.clear(self)
        
    def set_current_editor(self, editor, fname, update):
        """Bind editor instance"""
        editor_id = editor.get_document_id()
        if editor_id in self.editor_ids.values():
            item = self.editor_items[editor_id]
            if not self.freeze:
                self.scrollToItem(item)
                self.root_item_selected(item)
            if update:
                self.save_expanded_state()
                editor.populate_classbrowser(item)
                self.restore_expanded_state()
        else:
            self.editor_items[editor_id] = self.populate(editor, fname)
            self.resizeColumnToContents(0)
        if editor not in self.editor_ids:
            self.editor_ids[editor] = editor_id
        self.current_editor = editor
        
    def update_all(self):
        self.save_expanded_state()
        for editor, editor_id in self.editor_ids.iteritems():
            item = self.editor_items[editor_id]
            editor.populate_classbrowser(item)
        self.restore_expanded_state()
        
    def remove_editor(self, editor):
        if editor in self.editor_ids:
            if self.current_editor is editor:
                self.current_editor = None
            editor_id = self.editor_ids.pop(editor)
            if editor_id not in self.editor_ids.values():
                root_item = self.editor_items.pop(editor_id)
                self.takeTopLevelItem(self.indexOfTopLevelItem(root_item))
        
    def __sort_toplevel_items(self):
        if self.fullpath_sorting:
            sort_func = lambda item: osp.dirname(item.path.lower())
        else:
            sort_func = lambda item: osp.basename(item.path.lower())
        self.sort_top_level_items(key=sort_func)
        
    def populate(self, editor, fname):
        """Populate tree"""
#        import time
#        t0 = time.time()
        root_item = FileRootItem(fname, self)
        root_item.set_text(fullpath=self.show_fullpath)
        editor.populate_classbrowser(root_item)
        self.__sort_toplevel_items()
        self.root_item_selected(root_item)
#        print >>STDOUT, "Elapsed time: %d ms" % round((time.time()-t0)*1000)
        return root_item

    def root_item_selected(self, item):
        """Root item has been selected: expanding it and collapsing others"""
        for index in range(self.topLevelItemCount()):
            root_item = self.topLevelItem(index)
            if root_item is item:
                self.expandItem(root_item)
            else:
                self.collapseItem(root_item)
                
    def restore(self):
        """Reimplemented OneColumnTree method"""
        if self.current_editor is not None:
            self.collapseAll()
            editor_id = self.editor_ids[self.current_editor]
            self.root_item_selected(self.editor_items[editor_id])

    def clicked(self, item):
        """Click event"""
        if isinstance(item, FileRootItem):
            self.root_item_selected(item)
        self.activated(item)

    def get_root_item(self, item):
        root_item = item
        while isinstance(root_item.parent(), QTreeWidgetItem):
            root_item = root_item.parent()
        return root_item
                
    def activated(self, item):
        """Double-click event"""
        line = 0
        if isinstance(item, TreeItem):
            line = item.line
        root_item = self.get_root_item(item)
        self.freeze = True
        self.parent().emit(SIGNAL("edit_goto(QString,int,bool)"),
                           root_item.path, line, True)
        self.freeze = False
        parent = self.current_editor.parent()
        for editor_id, i_item in self.editor_items.iteritems():
            if i_item is root_item:
                #XXX: not working anymore!!!
                for editor, _id in self.editor_ids.iteritems():
                    if _id == editor_id and editor.parent() is parent:
                        self.current_editor = editor
                        break
                break
    
    
class ClassBrowser(QWidget):
    """
    Class browser
    
    Signals:
        SIGNAL("edit_goto(QString,int,bool)")
    """
    def __init__(self, parent=None, show_fullpath=True, fullpath_sorting=True):
        QWidget.__init__(self, parent)
        
        self.treewidget = ClassBrowserTreeWidget(self,
                show_fullpath=show_fullpath, fullpath_sorting=fullpath_sorting)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignRight)
        for btn in self.setup_buttons():
            btn_layout.addWidget(btn)

        layout = QVBoxLayout()
        layout.addWidget(self.treewidget)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def setup_buttons(self):
        fromcursor_btn = create_toolbutton(self, get_icon("fromcursor.png"),
                         tip=translate('ClassBrowser', 'Go to cursor position'),
                         triggered=self.treewidget.go_to_cursor_position)
        collapse_btn = create_toolbutton(self, text_beside_icon=False)
        collapse_btn.setDefaultAction(self.treewidget.collapse_selection_action)
        expand_btn = create_toolbutton(self, text_beside_icon=False)
        expand_btn.setDefaultAction(self.treewidget.expand_selection_action)
        restore_btn = create_toolbutton(self, text_beside_icon=False)
        restore_btn.setDefaultAction(self.treewidget.restore_action)
        return (fromcursor_btn, collapse_btn, expand_btn, restore_btn)
        
    def set_current_editor(self, editor, fname, update):
        self.treewidget.set_current_editor(editor, fname, update)
        
    def remove_editor(self, editor):
        self.treewidget.remove_editor(editor)
        
    def get_show_fullpath_state(self):
        return self.treewidget.show_fullpath
    
    def update(self):
        self.treewidget.update_all()

    def set_fullpath_sorting(self, state):
        self.treewidget.set_fullpath_sorting(state)


#===============================================================================
# QsciEditor widget
#===============================================================================
class PythonLexer(QsciLexerPython):
    def __init__(self, parent):
        super(PythonLexer, self).__init__(parent)

class CythonLexer(QsciLexerPython):
    def __init__(self, parent):
        super(CythonLexer, self).__init__(parent)
    def language(self):
        return "Cython"

#TODO: Show/hide TODOs, FIXMEs and XXXs (the same way as code analysis results)
class ScrollFlagArea(QWidget):
    WIDTH = 12
    def __init__(self, editor):
        super(ScrollFlagArea, self).__init__(editor)
        self.code_editor = editor
        self.resize(self.WIDTH, 0)
        
    def paintEvent(self, event):
        self.code_editor.scrollflagarea_paint_event(event)
        
    def mousePressEvent(self, event):
        self.code_editor.scrollflagarea_mousepress_event(event)

class QsciEditor(TextEditBaseWidget):
    """
    QScintilla Base Editor Widget
    """
    LEXERS = {
              ('py', 'pyw', 'python'): (PythonLexer, '#', PythonClassFuncMatch),
              ('pyx',): (CythonLexer, '#', PythonClassFuncMatch),
              ('f', 'for'): (QsciLexerFortran77, 'c', None),
              ('f90', 'f95', 'f2k'): (QsciLexerFortran, '!', None),
              ('diff', 'patch', 'rej'): (QsciLexerDiff, '', None),
              'css': (QsciLexerCSS, '#', None),
              ('htm', 'html'): (QsciLexerHTML, '', None),
              ('c', 'cpp', 'h', 'hpp', 'cxx'): (QsciLexerCPP, '//', None),
              ('bat', 'cmd', 'nt'): (QsciLexerBatch, 'rem ', None),
              ('properties', 'session', 'ini', 'inf', 'reg', 'url',
               'cfg', 'cnf', 'aut', 'iss'): (QsciLexerProperties, '#', None),
              }
    TAB_ALWAYS_INDENTS = ('py', 'pyw', 'python', 'c', 'cpp', 'h')
    OCCURENCE_INDICATOR = QsciScintilla.INDIC_CONTAINER
    CA_REFERENCE_INDICATOR = QsciScintilla.INDIC_BOX
    EOL_MODES = {"\r\n": QsciScintilla.EolWindows,
                 "\n":   QsciScintilla.EolUnix,
                 "\r":   QsciScintilla.EolMac}
    
    def __init__(self, parent=None):
        TextEditBaseWidget.__init__(self, parent)

        # Code analysis markers: errors, warnings
        self.ca_markers = []
        self.ca_marker_lines = {}
        self.error = self.markerDefine(QPixmap(get_image_path('error.png'),
                                               'png'))
        self.warning = self.markerDefine(QPixmap(get_image_path('warning.png'),
                                                 'png'))
        
        # Mark occurences timer
        self.occurence_highlighting = None
        self.occurence_timer = QTimer(self)
        self.occurence_timer.setSingleShot(True)
        self.occurence_timer.setInterval(1500)
        self.connect(self.occurence_timer, SIGNAL("timeout()"), 
                     self.__mark_occurences)
        self.occurences = []
        
        # Scrollbar flag area
        self.scrollflagarea = None
        
        self.setup_editor_args = None
        
        self.document_id = id(self)
                    
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
                           0x10A000)
        self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE,
                           self.CA_REFERENCE_INDICATOR,
                           QsciScintilla.INDIC_SQUIGGLE)
        self.SendScintilla(QsciScintilla.SCI_INDICSETFORE,
                           self.CA_REFERENCE_INDICATOR,
                           0x39A2F1)

        self.supported_language = None
        self.classfunc_match = None
        self.__tree_cache = None
        self.comment_string = None
        
        # Current line and find markers
        self.currentline_marker = None
        self.foundline_markers = []
        self.currentline = self.markerDefine(QsciScintilla.Background)
        bcol = CONF.get('editor', 'currentline/backgroundcolor')
        self.setMarkerBackgroundColor(QColor(bcol), self.currentline)
        self.foundline = self.markerDefine(QsciScintilla.Background)
        bcol = CONF.get('editor', 'foundline/backgroundcolor')
        self.setMarkerBackgroundColor(QColor(bcol), self.foundline)

        # Scintilla Python API
        self.api = None
        
        # Context menu
        self.setup_context_menu()
        
        # Tab key behavior
        self.tab_indents = None
        self.tab_mode = True # see QsciEditor.set_tab_mode


    #===========================================================================
    # Scrollbar flag area management
    #===========================================================================
    def set_scrollflagarea_enabled(self, state):
        if state:
            self.scrollflagarea = ScrollFlagArea(self)
            self.setViewportMargins(0, 0, 10, 0)
        else:
            self.scrollflagarea = None
            self.setViewportMargins(0, 0, 0, 0)
            
    def scrollflagarea_paint_event(self, event):
        painter = QPainter(self.scrollflagarea)
        painter.fillRect(event.rect(), QColor("#EFEFEF"))
        
        cr = self.contentsRect()
        top = cr.top()+18
        bottom = cr.bottom()-self.horizontalScrollBar().contentsRect().height()-22
        count = self.lines()
        make_flag = lambda nb: QRect(2, top+nb*(bottom-top)/count,
                                     self.scrollflagarea.WIDTH-4, 4)
        
        # Warnings
        painter.setPen(QColor("#F6D357"))
        painter.setBrush(QBrush(QColor("#FCF1CA")))
        for line in self.ca_marker_lines:
            painter.drawRect(make_flag(line))
        # Occurences
        painter.setPen(QColor("#00A010"))
        painter.setBrush(QBrush(QColor("#7FE289")))
        for line in self.occurences:
            painter.drawRect(make_flag(line))
        
    def scrollflagarea_mousepress_event(self, event):
        y = event.pos().y()
        cr = self.contentsRect()
        top = cr.top()+18
        bottom = cr.bottom()-self.horizontalScrollBar().contentsRect().height()-22
        count = self.lines()
        nb = (y-1-top)*count/(bottom-top)
        self.highlight_line(nb)
            
    def resizeEvent(self, event):
        """Reimplemented Qt method to handle line number area resizing"""
        super(QsciEditor, self).resizeEvent(event)
        if self.scrollflagarea is not None:
            cr = self.contentsRect()
            vsbw = self.verticalScrollBar().contentsRect().width()
            self.scrollflagarea.setGeometry(\
                        QRect(cr.right()-ScrollFlagArea.WIDTH-vsbw, cr.top(),
                              self.scrollflagarea.WIDTH, cr.height()))
                
                
    def get_document_id(self):
        return self.document_id
        
    def set_as_clone(self, editor):
        """Set as clone editor"""
        self.setDocument(editor.document())
        self.document_id = editor.get_document_id()
        self.setup_editor(**self.setup_editor_args)
        
    def setup_editor(self, linenumbers=True, language=None,
                     code_analysis=False, code_folding=False,
                     show_eol_chars=False, show_whitespace=False,
                     font=None, wrap=False, tab_mode=True,
                     occurence_highlighting=True, scrollflagarea=True):
        self.setup_editor_args = dict(
                linenumbers=linenumbers, language=language,
                code_analysis=code_analysis, code_folding=code_folding,
                show_eol_chars=show_eol_chars, show_whitespace=show_whitespace,
                font=font, wrap=wrap, tab_mode=tab_mode,
                occurence_highlighting=occurence_highlighting,
                scrollflagarea=scrollflagarea)
        
        # Scrollbar flag area
        self.set_scrollflagarea_enabled(scrollflagarea)
        
        # Lexer
        self.set_language(language)
                
        # Occurence highlighting
        self.set_occurence_highlighting(occurence_highlighting)
                
        # Tab always indents (even when cursor is not at the begin of line)
        self.tab_indents = language in self.TAB_ALWAYS_INDENTS
        self.set_tab_mode(tab_mode)

        if font is not None:
            self.set_font(font)
        
        if linenumbers:
            self.connect(self, SIGNAL('linesChanged()'), self.__lines_changed)
        self.setup_margins(linenumbers, code_analysis, code_folding)
        
        # Re-enable brace matching (already enabled in TextEditBaseWidget.setup
        # but for an unknown reason, changing the 'set_font' call above reset
        # this setting to default, which is no brace matching):
        # XXX: find out why
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(Qt.yellow)
        
        # Indentation (moved from QsciEditor.setup for the same reason as brace
        # matching -- see comment above)
        self.setIndentationGuides(True)
        self.setIndentationGuidesForegroundColor(Qt.lightGray)
        
        self.set_eol_chars_visible(show_eol_chars)
        self.set_whitespace_visible(show_whitespace)
        
        self.toggle_wrap_mode(wrap)
        if self.is_python():
            self.setup_api()
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
            self.__clear_occurence_markers()

    def set_language(self, language):
        self.supported_language = False
        self.comment_string = ''
        if language is not None:
            for key in self.LEXERS:
                if language.lower() in key:
                    self.supported_language = True
                    lexer_class, comment_string, CFMatch = self.LEXERS[key]
                    self.comment_string = comment_string
                    if CFMatch is None:
                        self.classfunc_match = None
                    else:
                        self.classfunc_match = CFMatch()
                    if lexer_class is not None:
                        # Fortran lexers are sometimes unavailable:
                        # the corresponding class is then replaced by None
                        # (see the import lines at the beginning of the script)
                        lexer = lexer_class(self)
                        self.setLexer(lexer)
                    break
                
    def is_python(self):
        return isinstance(self.lexer(), PythonLexer)
        
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
            if _l >= self.lines():
                # Checking if key is still in tree cache in case one of its 
                # ancestors was deleted in the meantime (deleting all children):
                if _l in self.__tree_cache:
                    self.__remove_from_tree_cache(line=_l)
        
        line = -1
        ancestors = [(root_item, 0)]
        previous_item = None
        previous_level = None
        
        while line < self.lines():
            line += 1
            level = self.get_fold_level(line)
            citem, clevel, _d = self.__tree_cache.get(line, (None, None, ""))
            
            # Skip iteration if line is not the first line of a foldable block
            if level is None and citem is not None:
                self.__remove_from_tree_cache(line=line)
                continue

            # Searching for class/function statements
            text = unicode(self.text(line))
            class_name = self.classfunc_match.get_class_name(text)
            if class_name is None:
                func_name = self.classfunc_match.get_function_name(text)
                if func_name is None:
                    if citem is not None:
                        self.__remove_from_tree_cache(line=line)
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
                        self.__remove_from_tree_cache(line=line)
                item = ClassItem(class_name, line+1, parent, preceding)
            else:
                if citem is not None:
                    if func_name == cname and level == clevel:
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        self.__remove_from_tree_cache(line=line)
                item = FunctionItem(func_name, line+1, parent, preceding)
                if item.is_method() and line > 0:
                    text = unicode(self.text(line-1))
                    decorator = self.classfunc_match.get_decorator(text)
                    item.set_decorator(decorator)
            item.setup()
            debug = "%s -- %s/%s" % (str(item.line).rjust(6),
                                     unicode(item.parent().text(0)),
                                     unicode(item.text(0)))
            self.__tree_cache[line] = (item, level, debug)
            previous_level = level
            previous_item = item
        
        
#===============================================================================
#    QScintilla
#===============================================================================
    def setup(self):
        """Reimplement TextEditBaseWidget method"""
        TextEditBaseWidget.setup(self)
        
        # Wrapping
        if CONF.get('editor', 'wrapflag'):
            self.setWrapVisualFlags(QsciScintilla.WrapFlagByBorder)
        
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
        """Load and prepare Python API"""
        if self.lexer() is None:
            return
        self.api = QsciAPIs(self.lexer())
        is_api_ready = False
        api_path = CONF.get('editor', 'api')
        if not osp.isfile(api_path):
            from spyderlib.config import DATA_PATH
            api_path = osp.join(DATA_PATH, 'python.api')
            if osp.isfile(api_path):
                CONF.set('editor', 'api', api_path)
            else:
                return False
        api_size = CONF.get('editor', 'api_size', None)
        current_api_size = os.stat(api_path).st_size
        if api_size is not None and api_size == current_api_size:
            if self.api.isPrepared():
                is_api_ready = self.api.loadPrepared()
        else:
            CONF.set('editor', 'api_size', current_api_size)
        if not is_api_ready:
            if self.api.load(api_path):
                self.api.prepare()
                self.connect(self.api, SIGNAL("apiPreparationFinished()"),
                             self.api.savePrepared)
        return is_api_ready
    
    def set_whitespace_visible(self, state):
        """Show/hide whitespace"""
        if state:
            self.setWhitespaceVisibility(QsciScintilla.WsVisible)
        else:
            self.setWhitespaceVisibility(QsciScintilla.WsInvisible)
    
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
        Set QScintilla widget EOL mode based on *text* EOL characters
        """
        if isinstance(text, QString):
            text = unicode(text)
        eol_chars = sourcecode.get_eol_chars(text)
        if eol_chars is not None:
            self.setEolMode(self.EOL_MODES[eol_chars])
        
    def get_line_separator(self):
        """Return line separator based on current EOL mode"""
        current_mode = self.eolMode()
        for eol_chars, mode in self.EOL_MODES.iteritems():
            if current_mode == mode:
                return eol_chars
        else:
            return ''
    
    def __find_first(self, text, line=None):
        """
        Find first occurence
        line is None: scan whole document
        *or*
        line is not None: scan only line number *line*
        """
        self.__find_flags = QsciScintilla.SCFIND_MATCHCASE | \
                            QsciScintilla.SCFIND_WHOLEWORD
        if line is None:
            # Scanning whole document
            self.__find_start = 0
            line = self.lines()-1
        else:
            # Scanning line number *line* and following lines if continued
            self.__find_start = self.position_from_lineindex(line, 0)
            def is_line_splitted(line_no):
                stripped = unicode(self.text(line_no)).strip()
                return stripped.endswith('\\') or stripped.endswith(',') \
                       or len(stripped) == 0
            while line < self.lines()-1 and is_line_splitted(line):
                line += 1
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
        if self.currentline_marker is not None:
            self.markerDeleteHandle(self.currentline_marker)
        line, _index = self.getCursorPosition()
        self.currentline_marker = self.markerAdd(line, self.currentline)
        if self.occurence_highlighting:
            self.occurence_timer.stop()
            self.occurence_timer.start()
        
    def __clear_occurence_markers(self):
        """Clear occurence markers"""
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                           self.OCCURENCE_INDICATOR)
        self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE,
                           0, self.length())
        self.occurences = []
        if self.scrollflagarea is not None:
            self.scrollflagarea.repaint()
        
    def __mark_occurences(self):
        """Marking occurences of the currently selected word"""
        self.__clear_occurence_markers()

        if not self.supported_language or self.hasSelectedText():
            return
            
        text = self.get_current_word()
        if text.isEmpty():
            return
        if self.is_python() and \
           (is_builtin(unicode(text)) or is_keyword(unicode(text))):
            return

        # Highlighting all occurences of word *text*
        ok = self.__find_first(text)
        self.occurences = []
        while ok:
            spos = self.SendScintilla(QsciScintilla.SCI_GETTARGETSTART)
            epos = self.SendScintilla(QsciScintilla.SCI_GETTARGETEND)
            self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                               spos, epos-spos)
            ok = self.__find_next(text)
            line, _index = self.lineindex_from_position(spos)
            self.occurences.append(line)
        if self.scrollflagarea is not None:
            self.scrollflagarea.repaint()
        
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
            lexer = self.lexer()
            for style in range(16):
                font_i = QFont(font)
                if font.weight() == QFont.Normal:
                    font_i.setWeight(lexer.defaultFont(style).weight())
                lexer.setFont(font_i, style)
            self.setLexer(self.lexer())
        margin_font = QFont(font)
        margin_font.setPointSize(margin_font.pointSize()-1)
        self.setMarginsFont(margin_font)
        
    def set_text(self, text):
        """Set the text of the editor"""
        self.setText(text)
        self.set_eol_mode(text)
        if self.supported_language:
            self.colourise_all()

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
        
    def colourise_all(self):
        """Force Scintilla to process the whole document"""
        textlength = self.SendScintilla(QsciScintilla.SCI_GETTEXTLENGTH)
        self.SendScintilla(QsciScintilla.SCI_COLOURISE, 0, textlength)
        
    def get_fold_level(self, line):
        """Is it a fold header line?
        If so, return fold level
        If not, return None"""
        lvl = self.SendScintilla(QsciScintilla.SCI_GETFOLDLEVEL, line)
        if lvl & QsciScintilla.SC_FOLDLEVELHEADERFLAG:
            return lvl & QsciScintilla.SC_FOLDLEVELNUMBERMASK
    
    def fold_expanded(self, line):
        """Is fold expanded?"""
        return self.SendScintilla(QsciScintilla.SCI_GETFOLDEXPANDED, line)
        
    def get_folded_lines(self):
        """Return the list of folded line numbers"""
        return [line for line in xrange(self.lines()) \
                if self.get_fold_level(line) and not self.fold_expanded(line)]
        
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
        self.horizontalScrollBar().setValue(0)
        
    def go_to_line(self, line):
        """Go to line number *line*"""
        self.setCursorPosition(line-1, 0)
        self.ensureLineVisible(line-1)
        
    def set_found_lines(self, lines):
        """Set found lines, i.e. lines corresponding to found results"""
        for marker in self.foundline_markers:
            self.markerDeleteHandle(marker)
        self.foundline_markers = []
        for line in lines:
            self.foundline_markers.append(self.markerAdd(line, self.foundline))

    def cleanup_code_analysis(self):
        """Remove all code analysis markers"""
        for marker in self.ca_markers:
            self.markerDeleteHandle(marker)
        self.ca_markers = []
        self.ca_marker_lines = {}
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT,
                           self.CA_REFERENCE_INDICATOR)
        self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE,
                           0, self.length())
        
    def process_code_analysis(self, check_results):
        """Analyze filename code with pyflakes"""
        self.cleanup_code_analysis()
        if check_results is None:
            # Not able to compile module
            return
        for message, line0, error in check_results:
            line1 = line0 - 1
            marker = self.markerAdd(line1,
                                    self.error if error else self.warning)
            self.ca_markers.append(marker)
            if line1 not in self.ca_marker_lines:
                self.ca_marker_lines[line1] = []
            self.ca_marker_lines[line1].append( (message, error) )
            refs = re.findall(r"\'[a-zA-Z0-9_]*\'", message)
            for ref in refs:
                # Highlighting found references
                text = ref[1:-1]
                ok = self.__find_first(text, line=line1)
                while ok:
                    spos = self.SendScintilla(QsciScintilla.SCI_GETTARGETSTART)
                    epos = self.SendScintilla(QsciScintilla.SCI_GETTARGETEND)
                    self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                                       spos, epos-spos)
                    ok = self.__find_next(text)

    def __highlight_warning(self, line):
        self.highlight_line(line+1)
        self.__show_code_analysis_results(line)

    def go_to_next_warning(self):
        """Go to next code analysis warning message"""
        cline, _ = self.getCursorPosition()
        lines = sorted(self.ca_marker_lines.keys())
        for line in lines:
            if line > cline:
                self.__highlight_warning(line)
                return
        else:
            self.__highlight_warning(lines[0])

    def go_to_previous_warning(self):
        """Go to previous code analysis warning message"""
        cline, _ = self.getCursorPosition()
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

#    def mouseMoveEvent(self, event):
#        line = self.get_line_number_at(event.pos())
#        self.__show_code_analysis_results(line)
#        QsciScintilla.mouseMoveEvent(self, event)
        
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
        if not self.is_python():
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
            if self.is_python():
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
                self.SendScintilla(QsciScintilla.SCI_TAB)
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
            QsciScintilla.keyPressEvent(self, event)
            if CONF.get('main', 'workaround/gnome_qscintilla'):
                # Workaround for QScintilla's completion with Gnome
                from PyQt4.QtGui import QListWidget
                if self.is_completion_widget_visible():
                    for w in self.children():
                        if isinstance(w, QListWidget):
                            w.setWindowFlags(Qt.Dialog| Qt.FramelessWindowHint)
                            w.show()
            
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
            
    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        if event.mimeData().hasText():
            super(QsciEditor, self).dragEnterEvent(event)
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        if event.mimeData().hasText():
            super(QsciEditor, self).dropEvent(event)
        else:
            event.ignore()


#===============================================================================
# QsciEditor's Printer
#===============================================================================

class Printer(QsciPrinter):
    def __init__(self, mode=QPrinter.ScreenResolution, header_font=None):
        QsciPrinter.__init__(self, mode)
        if True:
            self.setColorMode(QPrinter.Color)
        else:
            self.setColorMode(QPrinter.GrayScale)
        if True:
            self.setPageOrder(QPrinter.FirstPageFirst)
        else:
            self.setPageOrder(QPrinter.LastPageFirst)
        self.date = time.ctime()
        if header_font is not None:
            self.header_font = header_font
        
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
class TestEditor(QsciEditor):
    def __init__(self, parent):
        super(TestEditor, self).__init__(parent)
        self.setup_editor(code_folding=True)
        
    def load(self, filename):
        self.set_language(osp.splitext(filename)[1][1:])
        self.set_text(file(filename, 'rb').read())
        self.setWindowTitle(filename)
        self.set_font(QFont("Courier New", 10))
        self.setup_margins(True, True, True)

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
    win.editor.set_found_lines([6, 8, 10])
    
    analysis_results = check(fname)
    win.editor.process_code_analysis(analysis_results)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = __file__
        fname = r"d:\Python\sandbox.pyw"
    test(fname)

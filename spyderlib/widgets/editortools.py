# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Editor tools: class browser, etc."""

import sys, re,  os.path as osp

from PyQt4.QtGui import (QWidget, QTreeWidgetItem,  QHBoxLayout, QVBoxLayout,
                         QPainter, QColor)
from PyQt4.QtCore import Qt, SIGNAL, QSize

# For debugging purpose:
STDOUT = sys.stdout

# Local import
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import (create_action, translate,
                                       create_toolbutton, set_item_user_text)
from spyderlib.widgets import OneColumnTree


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
class PythonCFM(object):
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
                           root_item.path, line, False)
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
# Viewport widgets
#===============================================================================
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.code_editor = editor
        
    def sizeHint(self):
        return QSize(self.code_editor.get_linenumberarea_width(), 0)
        
    def paintEvent(self, event):
        self.code_editor.linenumberarea_paint_event(event)

    def mousePressEvent(self, event):
        self.code_editor.linenumberarea_mousepress_event(event)

class ScrollFlagArea(QWidget):
    WIDTH = 12
    def __init__(self, editor):
        super(ScrollFlagArea, self).__init__(editor)
        self.code_editor = editor
        
    def sizeHint(self):
        return QSize(self.WIDTH, 0)
        
    def paintEvent(self, event):
        self.code_editor.scrollflagarea_paint_event(event)
        
    def mousePressEvent(self, event):
        y = event.pos().y()
        vsb = self.code_editor.verticalScrollBar()
        vsbcr = vsb.contentsRect()
        range = vsb.maximum()-vsb.minimum()
        vsb.setValue(vsb.minimum()+range*(y-vsbcr.top()-20)/(vsbcr.height()-55))

class EdgeLine(QWidget):
    def __init__(self, editor):
        super(EdgeLine, self).__init__(editor)
        self.code_editor = editor
        self.column = 80
        
    def paintEvent(self, event):
        painter = QPainter(self)
        color = QColor(Qt.darkGray)
        color.setAlphaF(.5)
        painter.fillRect(event.rect(), color)


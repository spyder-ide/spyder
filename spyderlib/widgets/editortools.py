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
        
    def set_path(self, path, fullpath):
        self.path = path
        self.set_text(fullpath)
        
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


def remove_from_tree_cache(tree_cache, line=None, item=None):
    if line is None:
        for line, (_it, _level, _debug) in tree_cache.iteritems():
            if _it is item:
                break
    item, _level, debug = tree_cache.pop(line)
    try:
        for child in [item.child(_i) for _i in range(item.childCount())]:
            remove_from_tree_cache(tree_cache, item=child)
        item.parent().removeChild(item)
    except RuntimeError:
        # Item has already been deleted
        #XXX: remove this debug-related fragment of code
        print >>STDOUT, "unable to remove tree item: ", debug

class ClassBrowserTreeWidget(OneColumnTree):
    def __init__(self, parent, show_fullpath=False, fullpath_sorting=True,
                 show_all_files=True):
        self.show_fullpath = show_fullpath
        self.fullpath_sorting = fullpath_sorting
        self.show_all_files = show_all_files
        OneColumnTree.__init__(self, parent)
        self.freeze = False # Freezing widget to avoid any unwanted update
        self.editor_items = {}
        self.editor_tree_cache = {}
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
        allfiles_act = create_action(self,
                        text=translate('ClassBrowser', 'Show all files'),
                        toggled=self.toggle_show_all_files)
        allfiles_act.setChecked(self.show_all_files)
        actions = [fullpath_act, allfiles_act, fromcursor_act]
        return actions
    
    def toggle_fullpath_mode(self, state):
        self.show_fullpath = state
        self.setTextElideMode(Qt.ElideMiddle if state else Qt.ElideRight)
        for index in range(self.topLevelItemCount()):
            self.topLevelItem(index).set_text(fullpath=self.show_fullpath)
            
    def __hide_or_show_root_items(self, item):
        """
        show_all_files option is disabled: hide all root items except *item*
        show_all_files option is enabled: do nothing
        """
        for _it in self.get_top_level_items():
            _it.setHidden(_it is not item and not self.show_all_files)
            
    def toggle_show_all_files(self, state):
        self.show_all_files = state
        if self.current_editor is not None:
            editor_id = self.editor_ids[self.current_editor]
            item = self.editor_items[editor_id]
            self.__hide_or_show_root_items(item)
            
    def set_fullpath_sorting(self, state):
        self.fullpath_sorting = state
        self.__sort_toplevel_items()
        
    def go_to_cursor_position(self):
        if self.current_editor is not None:
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
                self.__hide_or_show_root_items(item)
            if update:
                self.save_expanded_state()
                tree_cache = self.editor_tree_cache[editor_id]
                self.populate_branch(editor, item, tree_cache)
                self.restore_expanded_state()
        else:
    #        import time
    #        t0 = time.time()
            root_item = FileRootItem(fname, self)
            root_item.set_text(fullpath=self.show_fullpath)
            tree_cache = self.populate_branch(editor, root_item)
            self.__sort_toplevel_items()
            self.root_item_selected(root_item)
    #        print >>STDOUT, "Elapsed time: %d ms" % round((time.time()-t0)*1000)
            self.editor_items[editor_id] = root_item
            self.editor_tree_cache[editor_id] = tree_cache
            self.resizeColumnToContents(0)
        if editor not in self.editor_ids:
            self.editor_ids[editor] = editor_id
        self.current_editor = editor
        
    def file_renamed(self, editor, new_filename):
        """File was renamed, updating class browser tree"""
        editor_id = editor.get_document_id()
        if editor_id in self.editor_ids.values():
            root_item = self.editor_items[editor_id]
            root_item.set_path(new_filename, fullpath=self.show_fullpath)
        
    def update_all(self):
        self.save_expanded_state()
        for editor, editor_id in self.editor_ids.iteritems():
            item = self.editor_items[editor_id]
            tree_cache = self.editor_tree_cache[editor_id]
            self.populate_branch(editor, item, tree_cache)
        self.restore_expanded_state()
        
    def remove_editor(self, editor):
        if editor in self.editor_ids:
            if self.current_editor is editor:
                self.current_editor = None
            editor_id = self.editor_ids.pop(editor)
            if editor_id not in self.editor_ids.values():
                root_item = self.editor_items.pop(editor_id)
                self.editor_tree_cache.pop(editor_id)
                try:
                    self.takeTopLevelItem(self.indexOfTopLevelItem(root_item))
                except RuntimeError:
                    # item has already been removed
                    pass
        
    def __sort_toplevel_items(self):
        if self.fullpath_sorting:
            sort_func = lambda item: osp.dirname(item.path.lower())
        else:
            sort_func = lambda item: osp.basename(item.path.lower())
        self.sort_top_level_items(key=sort_func)
            
    def populate_branch(self, editor, root_item, tree_cache=None):
        if tree_cache is None:
            tree_cache = {}
        
        # Removing cached items for which line is > total line nb
        for _l in tree_cache.keys():
            if _l >= editor.get_line_count():
                # Checking if key is still in tree cache in case one of its 
                # ancestors was deleted in the meantime (deleting all children):
                if _l in tree_cache:
                    remove_from_tree_cache(tree_cache, line=_l)
                    
        ancestors = [(root_item, 0)]
        previous_item = None
        previous_level = None
        
        if editor.highlighter is not None:
            # QtEditor
            cb_data = editor.highlighter.get_classbrowser_data()
        else:
            # QsciEditor
            cb_data = None
        for block_nb in range(editor.get_line_count()):
            line_nb = block_nb+1
            if cb_data is not None:
                data = cb_data.get(block_nb)
            else:
                from spyderlib.widgets.qteditor.syntaxhighlighters import ClassBrowserData
                data = ClassBrowserData()
                text = unicode(editor.text(block_nb))
                data.text = text
                data.fold_level = editor.get_fold_level(block_nb)
                class_name = editor.classfunc_match.get_class_name(text)
                if class_name is not None:
                    data.def_type = ClassBrowserData.CLASS
                    data.def_name = class_name
                else:
                    func_name = editor.classfunc_match.get_function_name(text)
                    if func_name is not None:
                        data.def_type = ClassBrowserData.FUNCTION
                        data.def_name = func_name
            
            if data is None:
                level = None
            else:
                level = data.fold_level
            citem, clevel, _d = tree_cache.get(line_nb,
                                                      (None, None, ""))
            
            # Skip iteration if line is not the first line of a foldable block
            if level is None:
                if citem is not None:
                    remove_from_tree_cache(tree_cache, line=line_nb)
                continue
            
            # Searching for class/function statements
            class_name = data.get_class_name()
            if class_name is None:
                func_name = data.get_function_name()
                if func_name is None:
                    if citem is not None:
                        remove_from_tree_cache(tree_cache, line=line_nb)
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
                        remove_from_tree_cache(tree_cache, line=line_nb)
                item = ClassItem(class_name, line_nb, parent, preceding)
            else:
                if citem is not None:
                    if func_name == cname and level == clevel:
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        remove_from_tree_cache(tree_cache, line=line_nb)
                item = FunctionItem(func_name, line_nb, parent, preceding)
                if item.is_method() and line_nb > 1:
                    text = unicode(editor.text(block_nb-1))
                    decorator = editor.classfunc_match.get_decorator(text)
                    item.set_decorator(decorator)
            item.setup()
            debug = "%s -- %s/%s" % (str(item.line).rjust(6),
                                     unicode(item.parent().text(0)),
                                     unicode(item.text(0)))
            tree_cache[line_nb] = (item, level, debug)
            previous_level = level
            previous_item = item
            
        return tree_cache

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
        self.parent().emit(SIGNAL("edit_goto(QString,int,QString)"),
                           root_item.path, line, item.text(0))
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
        SIGNAL("edit_goto(QString,int,QString)")
    """
    def __init__(self, parent=None, show_fullpath=True, fullpath_sorting=True,
                 show_all_files=True):
        QWidget.__init__(self, parent)

        self.treewidget = ClassBrowserTreeWidget(self,
                                            show_fullpath=show_fullpath,
                                            fullpath_sorting=fullpath_sorting,
                                            show_all_files=show_all_files)

        self.visibility_action = create_action(self,
                                           self.tr("Show/hide class browser"),
                                           icon='class_browser_vis.png',
                                           toggled=self.toggle_visibility)
        self.visibility_action.setChecked(True)
        
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignRight)
        for btn in self.setup_buttons():
            btn_layout.addWidget(btn)

        layout = QVBoxLayout()
        layout.addWidget(self.treewidget)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def toggle_visibility(self, state):
        self.setVisible(state)
        current_editor = self.treewidget.current_editor
        if current_editor is not None:
            current_editor.clearFocus()
            current_editor.setFocus()
            if state:
                self.emit(SIGNAL("classbrowser_is_visible()"))
        
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
        
    def get_options(self):
        """
        Return class browser options
        except for fullpath sorting option which is more global
        """
        return dict(show_fullpath=self.treewidget.show_fullpath,
                    show_all_files=self.treewidget.show_all_files,
                    expanded_state=self.treewidget.get_expanded_state(),
                    scrollbar_position=self.treewidget.get_scrollbar_position(),
                    visibility=self.isVisible())
    
    def update(self):
        self.treewidget.update_all()

    def set_fullpath_sorting(self, state):
        self.treewidget.set_fullpath_sorting(state)

    def file_renamed(self, editor, new_filename):
        self.treewidget.file_renamed(editor, new_filename)


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

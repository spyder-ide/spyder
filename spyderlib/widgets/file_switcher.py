# -*- coding: utf-8 -*-
#
# Augmented file switcher by DM, 2015 (based on original in widgets/editor.py)
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from __future__ import print_function

from spyderlib.baseconfig import _
from spyderlib.qt.QtGui import (QVBoxLayout, QHBoxLayout,
                                QListWidget, QListWidgetItem,
                                QDialog, QLineEdit, QKeyEvent,
                                QStyledItemDelegate, QStyleOptionViewItemV4, 
                                QApplication, QTextDocument, QStyle,
                                QAbstractTextDocumentLayout, QToolButton,
                                QToolTip)
from spyderlib.qt.QtCore import (Signal, Qt,  QObject,
                                  QSize, QEvent, QPoint)

import os
import os.path as osp

# Local imports
from spyderlib.guiconfig import  new_shortcut
from spyderlib.py3compat import to_text_string
from spyderlib.utils.qthelpers import get_std_icon

class HTMLDelegate(QStyledItemDelegate):
    """ Taken from http://stackoverflow.com/a/5443112/2399799
    """
    def paint(self, painter, option, index):
        options = QStyleOptionViewItemV4(option)
        self.initStyleOption(options,index)

        style = QApplication.style() if options.widget is None \
                                        else options.widget.style()

        doc = QTextDocument()
        doc.setHtml(options.text)

        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter);

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItemV4(option)
        self.initStyleOption(options,index)

        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())



class UpDownFilter(QObject):
    up_down = Signal(int)
    def eventFilter(self, src, e):
        if isinstance(e,QKeyEvent) and e.type() == QEvent.KeyPress:
            if e.key() == Qt.Key_Up:
                self.up_down.emit(-1)
            elif e.key() == Qt.Key_Down:
                self.up_down.emit(+1)
        #Call Base Class Method to Continue Normal Event Processing
        return super(UpDownFilter,self).eventFilter(src, e)

def shorten_paths(path_list):
    """
    Takes a list of paths and tries to "intelligently" shorten them all.  The
    aim is to make it clear to the user where the paths differ, as that is 
    likely what they care about.  Note that this operates on a list of paths 
    not individual paths.
    
    If the path ends in an actual file this will be removed.
    
    TODO: at the end, if the path is too long, should do a more dumb kind of 
    shortening, but not completely dumb.
    """
    
    # convert the path strings to a list of tokens 
    # and start building the new_path using the drive 
    path_list = path_list[:] # clone locally
    new_path_list = []
    for ii, path in enumerate(path_list):
        drive, path = osp.splitdrive(osp.dirname(path))
        new_path_list.append(drive + osp.sep)
        path_list[ii] = [part for part in path.split(osp.sep) if len(part) > 0]
            
    def recurse_level(level_idx):
        # if toks are all empty we need not have reucrsed here
        if all(len(toks) == 0 for _, toks in level_idx.iteritems()):
            return
        
        # firstly, find the longest common prefix for all in the level
        # s = len of longest common prefix
        _, sample_toks = next(level_idx.iteritems())
        if len(sample_toks) == 0:
            s = 0
        else:
            for s, sample_val in enumerate(sample_toks):
                if not all(len(toks) > s and toks[s] == sample_val \
                                    for _, toks in level_idx.iteritems()):
                    break

        # Shorten longest common prefix
        if s == 0:
            short_form = ''
        else:
            if s == 1:
                short_form = sample_toks[0]
            elif s == 2:
                short_form = sample_toks[0] + os.sep + sample_toks[1]
            else:
                short_form = "..." + os.sep + sample_toks[s-1]
            for idx in level_idx:
                new_path_list[idx] += short_form + os.sep
                level_idx[idx] = level_idx[idx][s:]
    
        # Group the remaining bit after the common prefix, shorten, and recurse
        while len(level_idx):
            k, group = 0, level_idx # k is the length of the group's common prefix
            while True:            
                # Abort if we've gone beyond the end of one or more in the group
                prospective_group = {idx: toks for idx, toks in group.iteritems()\
                                                    if len(toks) == k}
                if len(prospective_group) > 0:
                    if k == 0:
                        group = prospective_group
                    break            
                # Only keep going if all n still match on the kth token 
                _, sample_toks = next(group.iteritems())
                prospective_group = {idx: toks for idx, toks in group.iteritems()\
                                                    if toks[k] == sample_toks[k]}
                if len(prospective_group) == len(group) or k == 0:
                    group = prospective_group
                    k += 1
                else:
                    break        
            _, sample_toks = next(group.iteritems())
            if k == 0:
                short_form = ''
            if k == 1:
                short_form = sample_toks[0] 
            elif k == 2:
                short_form  = sample_toks[0] + os.sep + sample_toks[1]
            elif k > 2:
                short_form =  sample_toks[0] + "..." + os.sep + sample_toks[k-1]
            for idx in group.keys():
                new_path_list[idx] += short_form + (os.sep if k > 0 else '')
                del level_idx[idx]
            recurse_level({idx: toks[k:] for idx, toks in group.iteritems()})
                        
    recurse_level(dict(enumerate(path_list)))
    return [path[:-1] for path in new_path_list] #trim final sep


        
class HelperToolButton(QToolButton):
    """ """
    def __init__(self):
        QToolButton.__init__(self)

    def setToolTip(self, text):
        """ """
        self._tip_text = text

    def toolTip(self):
        """ """
        return self._tip_text

    def mousePressEvent(self, event):
        """ """
        QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        """ """
        QToolTip.showText(self.mapToGlobal(QPoint(0, 0)), self._tip_text)
        
class FileSwitcher(QDialog):
    close_file = Signal(int)
    edit_file = Signal(int)
    edit_line = Signal(int)

    def __init__(self, parent, tabs, tab_data):
        QDialog.__init__(self, parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint) 
        self.setWindowOpacity(0.9)
        self.setModal(True)

        self.tabs = tabs
        self.tab_data = tab_data
        self.filtered_index_to_path = None
        self.full_index_to_path = None
        self.path_to_line_count = None

        edit_layout = QHBoxLayout()         
        self.edit = QLineEdit(self)
        self.up_down_filter = UpDownFilter()
        self.up_down_filter.up_down.connect(self.handle_up_down)
        self.edit.installEventFilter(self.up_down_filter)
        self.edit.returnPressed.connect(self.handle_edit_file)
        self.edit.textChanged.connect(lambda text: self.synchronize(None))

        edit_layout.addWidget(self.edit)
        self.button_help = HelperToolButton()
        self.button_help.setIcon(get_std_icon('MessageBoxInformation'))
        style = """
            QToolButton {
              border: 1px solid grey;
              padding:0px;
              border-radius: 2px;
              background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                  stop: 0 #f6f7fa, stop: 1 #dadbde);
            }
            """
        self.button_help.setStyleSheet(style)
        help_str = _("""
            Press <b>Enter</b> to switch files.<br>
            Or <b>Esc</b> to cancel.<br>
            Type to filter filenames.<br>
            Use <b>:number</b> to go to a line,<br>
            e.g. 'main:42'.<br>
            Press <b>Ctrl+W</b> to close current tab.
            """)
        self.button_help.setToolTip(help_str)
        edit_layout.addWidget(self.button_help)
        
        
        self.listwidget = QListWidget(self)
        self.listwidget.setItemDelegate(HTMLDelegate(self))
        self.listwidget.itemSelectionChanged.connect(self.item_selection_changed)
        self.listwidget.itemActivated.connect(self.handle_edit_file)
        self.original_path = None
        self.original_line_num = None
        self.line_num = -1
        self.line_num_modified_for_path = None
        
        self.edit_line.connect(self.handle_edit_line)        
        self.rejected.connect(self.handle_rejection)
        new_shortcut("Ctrl+W", self, lambda: \
                self.close_file.emit(self.filtered_index_to_full(\
                                                self.listwidget.currentRow())))
         
        vlayout = QVBoxLayout()
        vlayout.addLayout(edit_layout)
        vlayout.addWidget(self.listwidget)
        self.setLayout(vlayout)

        self.edit.selectAll()
        self.edit.setFocus() 
        geo = parent.geometry()
        width = min(300,0.8*geo.width())
        self.listwidget.setMinimumWidth(width)

        left = parent.geometry().width()/2 - width/2
        top = 0
        while parent:
            geo = parent.geometry()
            top += geo.top()
            left += geo.left()
            parent = parent.parent()
        self.move(left,
                  top + self.tabs.tabBar().geometry().height() + 1) 
        # Note: the +1px on the top is a hack 

    def filtered_index_to_full(self,idx):
        # Note we assume idx is valid and the two mappings are valid
        return self.full_index_to_path.index(self.filtered_index_to_path[idx])
        
    def handle_up_down(self, up_down):
        row = self.listwidget.currentRow() + up_down
        if 0 <= row < self.listwidget.count():
            self.listwidget.setCurrentRow(row)

    def handle_rejection(self):
        self.edit_line.emit(-1) # reset line number for current tab (if there was a change)
        if self.original_path is not None:
            self.edit_file.emit(self.full_index_to_path.index(self.original_path))

    def handle_edit_file(self):
        row = self.listwidget.currentRow()
        if self.listwidget.count() > 0 and row >= 0:
            self.edit_file.emit(self.filtered_index_to_full(row))
            self.accept()

    def current_path(self):
        if self.listwidget.currentRow() >=0:
            return  self.filtered_index_to_path[self.listwidget.currentRow()]
        else:
            return None
            
    def handle_edit_line(self, line_num):
        current_path = self.current_path()
        
        # If we've changed path since last doing a goto line, we need to reset that previous file
        # TODO: I think this may be slightly buggy, but it's not majorly important
        if self.line_num_modified_for_path is not None \
                and current_path != self.line_num_modified_for_path:
            if self.line_num_modified_for_path in self.full_index_to_path:
                self.tabs.widget(self.full_index_to_path.index(\
                                        self.line_num_modified_for_path))\
                                    .go_to_line(self.original_line_num)
            self.line_num_modified_for_path = None
            self.original_line_num = None
            
        self.line_num = line_num # we record it for use when switching items in the list

        # Apply the line num to the current file, recording the original location if need be            
        if line_num >= 0 and len(self.filtered_index_to_path) > 0:
            if self.original_line_num is None:
                self.original_line_num = self.parent().get_current_editor()\
                                                      .get_cursor_line_number()
                self.line_num_modified_for_path = current_path
            editor = self.parent().get_current_editor()
            editor.go_to_line(min(line_num, editor.get_line_count()))

    def item_selection_changed(self):            
        row = self.listwidget.currentRow()  
        if self.listwidget.count() > 0 and row >= 0:
            try:
                self.edit_file.emit(self.filtered_index_to_full(row))
            except ValueError:
                pass
            self.edit_line.emit(self.line_num) # if this is -1 it does nothing

    def synchronize(self, stack_index):
        """
        stack_index is either an index into the tab list or None.
        """
        count = self.tabs.count()
        if count == 0:
            self.accept()
            return
            
        if stack_index is not None:
            # cache full paths, and short paths and invalidate line couts
            self.full_index_to_path = [getattr(td,'filename',None) \
                                                    for td in self.tab_data]
            current_path = self.original_path = \
                                        self.full_index_to_path[stack_index]
            self.full_index_to_short_path = \
                                        shorten_paths(self.full_index_to_path)  
            self.path_to_line_count = None # we only get this on demand
        else:
            current_path = self.current_path() # could be None
                
        # get filter text and optional line number
        filter_text = to_text_string(self.edit.text()).lower()
        trying_for_line_num = (':' in filter_text)
        filter_text, line_num = filter_text.split(':',1) \
                                if trying_for_line_num else (filter_text, "")
        try:
            line_num = int(line_num)
        except ValueError:
            line_num = -1

        # cache line counts if we need now them
        if trying_for_line_num and self.path_to_line_count is None:
            self.path_to_line_count = \
                            {path: self.tabs.widget(idx).get_line_count()\
                             for idx, path in enumerate(self.full_index_to_path)}
        
        self.listwidget.clear()
        self.filtered_index_to_path = []
        for index, path in enumerate(self.full_index_to_path):
            text = to_text_string(self.tabs.tabText(index))
            if len(filter_text) == 0 or filter_text in text.lower():
                if len(filter_text) > 0:
                    text = text.replace(filter_text,'<u>' + filter_text + '</u>')
                text = "<b>" + text + "</b>"
                if trying_for_line_num:
                    text += " [" + str(self.path_to_line_count[path]) + " " \
                                    + _("lines") + "] "
                text += "<br><span style='font-size:10px'>" \
                      + self.full_index_to_short_path[index] + "</span>"
                item = QListWidgetItem(self.tabs.tabIcon(index),
                                       text, self.listwidget)
                item.setToolTip(path)
                item.setSizeHint(QSize(0, 25))
                self.listwidget.addItem(item)
                self.filtered_index_to_path.append(path)
                
        if current_path is not None \
                        and current_path in self.filtered_index_to_path:
            self.listwidget.setCurrentRow(self.filtered_index_to_path\
                                              .index(current_path))
        elif len(self.filtered_index_to_path) > 0:
            self.listwidget.setCurrentRow(0)
        self.edit_line.emit(line_num) # could be -1

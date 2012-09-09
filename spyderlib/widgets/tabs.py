# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Tabs widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import (QTabWidget, QMenu, QDrag, QApplication,
                                QTabBar, QShortcut, QKeySequence, QWidget,
                                QHBoxLayout)
from spyderlib.qt.QtCore import SIGNAL, Qt, QPoint, QMimeData, QByteArray

import os.path as osp

# Local imports
from spyderlib.baseconfig import _
from spyderlib.config import get_icon
from spyderlib.utils.misc import get_common_path
from spyderlib.utils.qthelpers import (add_actions, create_toolbutton,
                                       create_action)


class TabBar(QTabBar):
    """Tabs base class with drag and drop support"""
    def __init__(self, parent, ancestor):
        QTabBar.__init__(self, parent)
        self.ancestor = ancestor
            
        # Dragging tabs
        self.__drag_start_pos = QPoint()
        self.setAcceptDrops(True)

    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() == Qt.LeftButton:
            self.__drag_start_pos = QPoint(event.pos())
        QTabBar.mousePressEvent(self, event)
    
    def mouseMoveEvent(self, event):
        """Override Qt method"""
        if event.buttons() == Qt.MouseButtons(Qt.LeftButton) and \
           (event.pos() - self.__drag_start_pos).manhattanLength() > \
                QApplication.startDragDistance():
            drag = QDrag(self)
            mimeData = QMimeData()
            mimeData.setData("parent-id", QByteArray.number(id(self.ancestor)))
            mimeData.setData("tabwidget-id",
                             QByteArray.number(id(self.parentWidget())))
            mimeData.setData("tabbar-id", QByteArray.number(id(self)))
            mimeData.setData("source-index", 
                         QByteArray.number(self.tabAt(self.__drag_start_pos)))
            drag.setMimeData(mimeData)
            drag.exec_()
        QTabBar.mouseMoveEvent(self, event)
    
    def dragEnterEvent(self, event):
        """Override Qt method"""
        mimeData = event.mimeData()
        formats = list( mimeData.formats() )
        if "parent-id" in formats and \
           mimeData.data("parent-id").toLong()[0] == id(self.ancestor):
            event.acceptProposedAction()
        QTabBar.dragEnterEvent(self, event)
    
    def dropEvent(self, event):
        """Override Qt method"""
        mimeData = event.mimeData()
        index_from = mimeData.data("source-index").toInt()[0]
        index_to = self.tabAt(event.pos())
        if index_to == -1:
            index_to = self.count()
        if mimeData.data("tabbar-id").toLong()[0] != id(self):
            tabwidget_from = str(mimeData.data("tabwidget-id").toLong()[0])
            
            # We pass self object ID as a QString, because otherwise it would 
            # depend on the platform: long for 64bit, int for 32bit. Replacing 
            # by long all the time is not working on some 32bit platforms 
            # (see Issue 1094, Issue 1098)
            self.emit(SIGNAL("move_tab(QString,int,int)"), 
                      tabwidget_from, index_from, index_to)

            event.acceptProposedAction()
        elif index_from != index_to:
            self.emit(SIGNAL("move_tab(int,int)"), index_from, index_to)
            event.acceptProposedAction()
        QTabBar.dropEvent(self, event)
        
        
class BaseTabs(QTabWidget):
    """TabWidget with context menu and corner widgets"""
    def __init__(self, parent, actions=None, menu=None,
                 corner_widgets=None, menu_use_tooltips=False):
        QTabWidget.__init__(self, parent)
        
        self.setUsesScrollButtons(True)
        
        self.corner_widgets = {}
        self.menu_use_tooltips = menu_use_tooltips
        
        if menu is None:
            self.menu = QMenu(self)
            if actions:
                add_actions(self.menu, actions)
        else:
            self.menu = menu
            
        # Corner widgets
        if corner_widgets is None:
            corner_widgets = {}
        corner_widgets.setdefault(Qt.TopLeftCorner, [])
        corner_widgets.setdefault(Qt.TopRightCorner, [])
        self.browse_button = create_toolbutton(self,
                                          icon=get_icon("browse_tab.png"),
                                          tip=_("Browse tabs"))
        self.browse_tabs_menu = QMenu(self)
        self.browse_button.setMenu(self.browse_tabs_menu)
        self.browse_button.setPopupMode(self.browse_button.InstantPopup)
        self.connect(self.browse_tabs_menu, SIGNAL("aboutToShow()"),
                     self.update_browse_tabs_menu)
        corner_widgets[Qt.TopLeftCorner] += [self.browse_button]

        self.set_corner_widgets(corner_widgets)
        
    def update_browse_tabs_menu(self):
        """Update browse tabs menu"""
        self.browse_tabs_menu.clear()
        names = []
        dirnames = []
        for index in range(self.count()):
            if self.menu_use_tooltips:
                text = unicode(self.tabToolTip(index))
            else:
                text = unicode(self.tabText(index))
            names.append(text)
            if osp.isfile(text):
                # Testing if tab names are filenames
                dirnames.append(osp.dirname(text))
        offset = None
        
        # If tab names are all filenames, removing common path:
        if len(names) == len(dirnames):
            common = get_common_path(dirnames)
            if common is None:
                offset = None
            else:
                offset = len(common)+1
                if offset <= 3:
                    # Common path is not a path but a drive letter...
                    offset = None
                
        for index, text in enumerate(names):
            tab_action = create_action(self, text[offset:],
                                       icon=self.tabIcon(index),
                                       toggled=lambda state, index=index:
                                               self.setCurrentIndex(index),
                                       tip=self.tabToolTip(index))
            tab_action.setChecked(index == self.currentIndex())
            self.browse_tabs_menu.addAction(tab_action)
        
    def set_corner_widgets(self, corner_widgets):
        """
        Set tabs corner widgets
        corner_widgets: dictionary of (corner, widgets)
        corner: Qt.TopLeftCorner or Qt.TopRightCorner
        widgets: list of widgets (may contains integers to add spacings)
        """
        assert isinstance(corner_widgets, dict)
        assert all(key in (Qt.TopLeftCorner, Qt.TopRightCorner)
                   for key in corner_widgets)
        self.corner_widgets.update(corner_widgets)
        for corner, widgets in self.corner_widgets.iteritems():
            cwidget = QWidget()
            cwidget.hide()
            prev_widget = self.cornerWidget(corner)
            if prev_widget:
                prev_widget.close()
            self.setCornerWidget(cwidget, corner)
            clayout = QHBoxLayout()
            clayout.setContentsMargins(0, 0, 0, 0)
            for widget in widgets:
                if isinstance(widget, int):
                    clayout.addSpacing(widget)
                else:
                    clayout.addWidget(widget)
            cwidget.setLayout(clayout)
            cwidget.show()
            
    def add_corner_widgets(self, widgets, corner=Qt.TopRightCorner):
        self.set_corner_widgets({corner:
                                 self.corner_widgets.get(corner, [])+widgets})
        
    def contextMenuEvent(self, event):
        """Override Qt method"""
        if self.menu:
            self.menu.popup(event.globalPos())
            
    def mousePressEvent(self, event):
        """Override Qt method"""
        if event.button() == Qt.MidButton:
            index = self.tabBar().tabAt(event.pos())
            if index >= 0:
                self.emit(SIGNAL("close_tab(int)"), index)
                event.accept()
                return
        QTabWidget.mousePressEvent(self, event)
        
    def keyPressEvent(self, event):
        """Override Qt method"""
        ctrl = event.modifiers() & Qt.ControlModifier
        key = event.key()
        handled = False
        if ctrl and self.count() > 0:
            index = self.currentIndex()
            if key == Qt.Key_PageUp and index > 0:
                self.setCurrentIndex(index-1)
                handled = True
            elif key == Qt.Key_PageDown and index < self.count()-1:
                self.setCurrentIndex(index+1)
                handled = True
        if not handled:
            QTabWidget.keyPressEvent(self, event)
        
    def set_close_function(self, func):
        """Setting Tabs close function
        None -> tabs are not closable"""
        state = func is not None
        if state:
            self.connect(self, SIGNAL("close_tab(int)"), func)
        try:
            # Assuming Qt >= 4.5
            QTabWidget.setTabsClosable(self, state)
            self.connect(self, SIGNAL("tabCloseRequested(int)"), func)
        except AttributeError:
            # Workaround for Qt < 4.5
            close_button = create_toolbutton(self, triggered=func,
                                             icon=get_icon("fileclose.png"),
                                             tip=_("Close current tab"))
            self.setCornerWidget(close_button if state else None)

        
class Tabs(BaseTabs):
    """BaseTabs widget with movable tabs and tab navigation shortcuts"""
    def __init__(self, parent, actions=None, menu=None,
                 corner_widgets=None, menu_use_tooltips=False):
        BaseTabs.__init__(self, parent, actions, menu,
                          corner_widgets, menu_use_tooltips)
        tab_bar = TabBar(self, parent)
        self.connect(tab_bar, SIGNAL('move_tab(int,int)'), self.move_tab)
        self.connect(tab_bar, SIGNAL('move_tab(QString,int,int)'),
                     self.move_tab_from_another_tabwidget)
        self.setTabBar(tab_bar)
        self.index_history = []
        self.connect(self, SIGNAL('currentChanged(int)'),
                     self.__current_changed)
        tabsc = QShortcut(QKeySequence("Ctrl+Tab"), parent, self.tab_navigate)
        tabsc.setContext(Qt.WidgetWithChildrenShortcut)
        closesc = QShortcut(QKeySequence("Ctrl+F4"), parent,
                            lambda: self.emit(SIGNAL("close_tab(int)"),
                                              self.currentIndex()))
        closesc.setContext(Qt.WidgetWithChildrenShortcut)
        
    def __current_changed(self, index):
        for _i in self.index_history[:]:
            if _i > self.count()-1:
                self.index_history.pop(self.index_history.index(_i))
        while index in self.index_history:
            self.index_history.pop(self.index_history.index(index))
        self.index_history.append(index)
        
    def tab_navigate(self):
        """Ctrl+Tab"""
        if len(self.index_history) < self.count():
            # When tab is inserted, the 'currentChanged' signal is not emitted
            # because index is still the same...
            # so we add the index to history here:
            index = self.currentIndex()
            for _j, _i in enumerate(self.index_history[:]):
                if _i >= index:
                    self.index_history[_j] = _i+1
            self.__current_changed(index)
        if len(self.index_history) > 1:
            last = len(self.index_history)-1
            index = self.index_history.pop(last)
            self.index_history.insert(0, index)
            self.setCurrentIndex(self.index_history[last])

    def move_tab(self, index_from, index_to):
        """Move tab inside a tabwidget"""
        self.emit(SIGNAL('move_data(int,int)'), index_from, index_to)

        tip, text = self.tabToolTip(index_from), self.tabText(index_from)
        icon, widget = self.tabIcon(index_from), self.widget(index_from)
        current_widget = self.currentWidget()
        
        self.removeTab(index_from)
        self.insertTab(index_to, widget, icon, text)
        self.setTabToolTip(index_to, tip)
        
        self.setCurrentWidget(current_widget)
        
        self.emit(SIGNAL('move_tab_finished()'))

    def move_tab_from_another_tabwidget(self, tabwidget_from,
                                        index_from, index_to):
        """Move tab from a tabwidget to another"""
            
        # We pass self object IDs as QString objs, because otherwise it would 
        # depend on the platform: long for 64bit, int for 32bit. Replacing 
        # by long all the time is not working on some 32bit platforms 
        # (see Issue 1094, Issue 1098)
        self.emit(SIGNAL('move_tab(QString,QString,int,int)'),
                  tabwidget_from, str(id(self)), index_from, index_to)

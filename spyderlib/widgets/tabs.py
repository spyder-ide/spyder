# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Tabs widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QTabWidget, QMenu, QDrag, QApplication, QTabBar,
                         QShortcut, QKeySequence)
from PyQt4.QtCore import SIGNAL, Qt, QPoint, QMimeData, QByteArray

# Local imports
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import (add_actions, create_toolbutton,
                                       create_action, translate)

# For debugging purpose:
import sys
STDOUT = sys.stdout


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
        formats = mimeData.formats()
        if formats.contains("parent-id") and \
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
            tabwidget_from = mimeData.data("tabwidget-id").toLong()[0]
            self.emit(SIGNAL("move_tab(long,int,int)"), 
                      tabwidget_from, index_from, index_to)
            event.acceptProposedAction()
        elif index_from != index_to:
            self.emit(SIGNAL("move_tab(int,int)"), index_from, index_to)
            event.acceptProposedAction()
        QTabBar.dropEvent(self, event)
        
        
class BaseTabs(QTabWidget):
    def __init__(self, parent, actions=None, menu=None):
        QTabWidget.__init__(self, parent)
        if menu is None:
            self.menu = QMenu(self)
            if actions:
                add_actions(self.menu, actions)
        else:
            self.menu = menu
        
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
        if handled:
            event.accept()
        else:
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
                                             tip=translate("Tabs",
                                                           "Close current tab"))
            self.setCornerWidget(close_button if state else None)

        
class Tabs(BaseTabs):
    """TabWidget with a context-menu"""
    def __init__(self, parent, actions=None):
        BaseTabs.__init__(self, parent, actions)
        tab_bar = TabBar(self, parent)
        self.connect(tab_bar, SIGNAL('move_tab(int,int)'), self.move_tab)
        self.connect(tab_bar, SIGNAL('move_tab(long,int,int)'),
                     self.move_tab_from_another_tabwidget)
        self.setTabBar(tab_bar)
        self.index_history = []
        self.connect(self, SIGNAL('currentChanged(int)'),
                     self.__current_changed)
        tabsc = QShortcut(QKeySequence("Ctrl+Tab"), parent, self.tab_navigate)
        tabsc.setContext(Qt.WidgetWithChildrenShortcut)
        # Browsing tabs button
        browse_button = create_toolbutton(self,
                                          icon=get_icon("browse_tab.png"),
                                          tip=translate("Tabs", "Browse tabs"))
        self.browse_tabs_menu = QMenu(self)
        browse_button.setMenu(self.browse_tabs_menu)
        browse_button.setPopupMode(browse_button.InstantPopup)
        self.connect(self.browse_tabs_menu, SIGNAL("aboutToShow()"),
                     self.update_browse_tabs_menu)
        self.setCornerWidget(browse_button)
        
    def update_browse_tabs_menu(self):
        """Update browse tabs menu"""
        self.browse_tabs_menu.clear()
        for index in range(self.count()):
            tab_action = create_action(self, self.tabText(index),
                                       icon=self.tabIcon(index),
                                       toggled=lambda state, index=index:
                                               self.setCurrentIndex(index),
                                       tip=self.tabToolTip(index))
            tab_action.setChecked(index == self.currentIndex())
            self.browse_tabs_menu.addAction(tab_action)
        
    def __current_changed(self, index):
        for _i in self.index_history[:]:
            if _i > self.count()-1:
                self.index_history.pop(self.index_history.index(_i))
        while index in self.index_history:
            self.index_history.pop(self.index_history.index(index))
        self.index_history.append(index)
        
    def tab_navigate(self):
        """Ctrl+Tab"""
        if len(self.index_history) > 1:
            last = len(self.index_history)-1
            index = self.index_history.pop(last)
            self.index_history.insert(0, index)
            self.setCurrentIndex(self.index_history[last])
        elif len(self.index_history) == 0 and self.count():
            self.index_history = [self.currentIndex()]            

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
        self.emit(SIGNAL('move_tab(long,long,int,int)'),
                  tabwidget_from, id(self), index_from, index_to)

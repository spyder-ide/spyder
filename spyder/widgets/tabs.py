# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tabs widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp
import sys

# Third party imports
from qtpy.QtCore import QByteArray, QMimeData, QPoint, Qt, Signal, QEvent
from qtpy.QtGui import QDrag
from qtpy.QtWidgets import (QApplication, QHBoxLayout, QMenu, QTabBar,
                            QTabWidget, QWidget, QLineEdit)

# Local imports
from spyder.config.base import _
from spyder.config.gui import config_shortcut
from spyder.py3compat import PY2, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.misc import get_common_path
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton)


class TabBar(QTabBar):
    """Tabs base class with drag and drop support"""
    sig_move_tab = Signal((int, int), (str, int, int))
    
    def __init__(self, parent, ancestor, rename_tabs=False):
        QTabBar.__init__(self, parent)
        self.ancestor = ancestor

        # To style tabs on Mac
        if sys.platform == 'darwin':
            self.setObjectName('plugin-tab')
            
        # Dragging tabs
        self.__drag_start_pos = QPoint()
        self.setAcceptDrops(True)
        self.setUsesScrollButtons(True)

        # Tab name editor
        self.rename_tabs = rename_tabs
        self.tab_name_editor = None
        if self.rename_tabs:
            # Creates tab name editor
            self.tab_name_editor = EditTabNamePopup(self)

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
            # Converting id's to long to avoid an OverflowError with PySide
            if PY2:
                ancestor_id = long(id(self.ancestor))
                parent_widget_id = long(id(self.parentWidget()))
                self_id = long(id(self))
            else:
                ancestor_id = id(self.ancestor)
                parent_widget_id = id(self.parentWidget())
                self_id = id(self)
            mimeData.setData("parent-id", QByteArray.number(ancestor_id))
            mimeData.setData("tabwidget-id",
                             QByteArray.number(parent_widget_id))
            mimeData.setData("tabbar-id", QByteArray.number(self_id))
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
            self.sig_move_tab[(str, int, int)].emit(tabwidget_from, index_from,
                                                    index_to)

            event.acceptProposedAction()
        elif index_from != index_to:
            self.sig_move_tab.emit(index_from, index_to)
            event.acceptProposedAction()
        QTabBar.dropEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Override Qt method to trigger the tab name editor."""
        if self.rename_tabs is True and \
                event.buttons() == Qt.MouseButtons(Qt.LeftButton):
            # Tab index
            index = self.tabAt(event.pos())
            if index >= 0:
                # Tab is valid, call tab name editor
                self.tab_name_editor.edit_tab(index)
        else:
            # Even is not interessant, raise to parent
            QTabBar.mouseDoubleClickEvent(self, event)

        
class BaseTabs(QTabWidget):
    """TabWidget with context menu and corner widgets"""
    sig_close_tab = Signal(int)
    
    def __init__(self, parent, actions=None, menu=None,
                 corner_widgets=None, menu_use_tooltips=False):
        QTabWidget.__init__(self, parent)
        self.setUsesScrollButtons(True)

        # To style tabs on Mac
        if sys.platform == 'darwin':
            self.setObjectName('plugin-tab')

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
                                          icon=ima.icon('browse_tab'),
                                          tip=_("Browse tabs"))
        self.browse_tabs_menu = QMenu(self)
        self.browse_button.setMenu(self.browse_tabs_menu)
        self.browse_button.setPopupMode(self.browse_button.InstantPopup)
        self.browse_tabs_menu.aboutToShow.connect(self.update_browse_tabs_menu)
        corner_widgets[Qt.TopLeftCorner] += [self.browse_button]

        self.set_corner_widgets(corner_widgets)

    def update_browse_tabs_menu(self):
        """Update browse tabs menu"""
        self.browse_tabs_menu.clear()
        names = []
        dirnames = []
        for index in range(self.count()):
            if self.menu_use_tooltips:
                text = to_text_string(self.tabToolTip(index))
            else:
                text = to_text_string(self.tabText(index))
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
        for corner, widgets in list(self.corner_widgets.items()):
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
        self.setCurrentIndex(self.tabBar().tabAt(event.pos()))
        if self.menu:
            self.menu.popup(event.globalPos())
            
    def mousePressEvent(self, event):
        """Override Qt method"""
        if event.button() == Qt.MidButton:
            index = self.tabBar().tabAt(event.pos())
            if index >= 0:
                self.sig_close_tab.emit(index)
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
            if key == Qt.Key_PageUp:
                if index > 0:
                    self.setCurrentIndex(index - 1)
                else:
                    self.setCurrentIndex(self.count() - 1)
                handled = True
            elif key == Qt.Key_PageDown:
                if index < self.count() - 1:
                    self.setCurrentIndex(index + 1)
                else:
                    self.setCurrentIndex(0)
                handled = True
        if not handled:
            QTabWidget.keyPressEvent(self, event)
        
    def set_close_function(self, func):
        """Setting Tabs close function
        None -> tabs are not closable"""
        state = func is not None
        if state:
            self.sig_close_tab.connect(func)
        try:
            # Assuming Qt >= 4.5
            QTabWidget.setTabsClosable(self, state)
            self.tabCloseRequested.connect(func)
        except AttributeError:
            # Workaround for Qt < 4.5
            close_button = create_toolbutton(self, triggered=func,
                                             icon=ima.icon('fileclose'),
                                             tip=_("Close current tab"))
            self.setCornerWidget(close_button if state else None)

        
class Tabs(BaseTabs):
    """BaseTabs widget with movable tabs and tab navigation shortcuts"""
    # Signals
    move_data = Signal(int, int)
    move_tab_finished = Signal()
    sig_move_tab = Signal(str, str, int, int)
    
    def __init__(self, parent, actions=None, menu=None,
                 corner_widgets=None, menu_use_tooltips=False,
                 rename_tabs=False):
        BaseTabs.__init__(self, parent, actions, menu,
                          corner_widgets, menu_use_tooltips)
        tab_bar = TabBar(self, parent, rename_tabs=rename_tabs)
        tab_bar.sig_move_tab.connect(self.move_tab)
        tab_bar.sig_move_tab[(str, int, int)].connect(
                                          self.move_tab_from_another_tabwidget)
        self.setTabBar(tab_bar)

        config_shortcut(lambda: self.tab_navigate(1), context='editor',
                        name='go to next file', parent=parent)
        config_shortcut(lambda: self.tab_navigate(-1), context='editor',
                        name='go to previous file', parent=parent)
        config_shortcut(lambda: self.sig_close_tab.emit(self.currentIndex()),
                        context='editor', name='close file 1', parent=parent)
        config_shortcut(lambda: self.sig_close_tab.emit(self.currentIndex()),
                        context='editor', name='close file 2', parent=parent)

    def tab_navigate(self, delta=1):
        """Ctrl+Tab"""
        if delta > 0 and self.currentIndex() == self.count()-1:
            index = delta-1
        elif delta < 0 and self.currentIndex() == 0:
            index = self.count()+delta
        else:
            index = self.currentIndex()+delta
        self.setCurrentIndex(index)

    def move_tab(self, index_from, index_to):
        """Move tab inside a tabwidget"""
        self.move_data.emit(index_from, index_to)

        tip, text = self.tabToolTip(index_from), self.tabText(index_from)
        icon, widget = self.tabIcon(index_from), self.widget(index_from)
        current_widget = self.currentWidget()
        
        self.removeTab(index_from)
        self.insertTab(index_to, widget, icon, text)
        self.setTabToolTip(index_to, tip)
        
        self.setCurrentWidget(current_widget)
        self.move_tab_finished.emit()

    def move_tab_from_another_tabwidget(self, tabwidget_from,
                                        index_from, index_to):
        """Move tab from a tabwidget to another"""
            
        # We pass self object IDs as QString objs, because otherwise it would 
        # depend on the platform: long for 64bit, int for 32bit. Replacing 
        # by long all the time is not working on some 32bit platforms 
        # (see Issue 1094, Issue 1098)
        self.sig_move_tab.emit(tabwidget_from, str(id(self)), index_from,
                               index_to)


class EditTabNamePopup(QLineEdit):
    """Popup on top of the tab to edit its name."""

    def __init__(self, parent):
        """Popup on top of the tab to edit its name."""

        # Variables
        # Parent (main)
        self.main = parent if parent is not None else self.parent()
        # Track with tab is being edited
        self.tab_index = None
      
        # Widget setup
        QLineEdit.__init__(self, parent=None)
        
        # Slot to handle tab name update
        self.editingFinished.connect(self.edit_finished)

        # Even filter to catch clicks and ESC key
        self.installEventFilter(self)
        
        # Clean borders and no shadow to blend with tab
        self.setWindowFlags(
            Qt.Popup |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint
        )
        self.setFrame(False)

        # Align with tab name
        self.setTextMargins(9, 0, 0, 0)

    def eventFilter(self, widget, event):
        """Catch clicks outside the object and ESC key press."""
        if ((event.type() == QEvent.MouseButtonPress and
                 not self.geometry().contains(event.globalPos())) or
                (event.type() == QEvent.KeyPress and
                 event.key() == Qt.Key_Escape)):
            # Exits editing
            self.hide()
            self.setFocus(False)
            return True
        
        # Event is not interessant, raise to parent
        return QLineEdit.eventFilter(self, widget, event)

    def edit_tab(self, index):
        """Activate the edit tab."""
        
        # Sets focus, shows cursor
        self.setFocus(True)
        
        # Updates tab index
        self.tab_index = index
        
        # Gets tab size and shrinks to avoid overlapping tab borders
        rect = self.main.tabRect(index)
        rect.adjust(1, 1, -2, -1)
        
        # Sets size
        self.setFixedSize(rect.size())

        # Places on top of the tab
        self.move(self.main.mapToGlobal(rect.topLeft()))

        # Copies tab name and selects all
        self.setText(self.main.tabText(index))
        self.selectAll()

        if not self.isVisible():
            # Makes editor visible
            self.show()

    def edit_finished(self):
        """On clean exit, update tab name."""
        # Hides editor
        self.hide()
        
        if isinstance(self.tab_index, int) and self.tab_index >= 0:
            # We are editing a valid tab, update name
            self.main.setTabText(self.tab_index, self.text())

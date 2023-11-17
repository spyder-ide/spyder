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

# Third party imports
from qdarkstyle.colorsystem import Gray
import qstylizer.style
from qtpy import PYQT5
from qtpy.QtCore import QEvent, QPoint, Qt, Signal, Slot, QSize
from qtpy.QtGui import QFontMetrics
from qtpy.QtWidgets import (
    QHBoxLayout, QLineEdit, QMenu, QTabBar, QTabWidget, QToolButton, QWidget)

# Local imports
from spyder.config.base import _
from spyder.config.gui import is_dark_interface
from spyder.config.manager import CONF
from spyder.py3compat import to_text_string
from spyder.utils.icon_manager import ima
from spyder.utils.misc import get_common_path
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton)
from spyder.utils.stylesheet import MAC, PANES_TABBAR_STYLESHEET, WIN


class EditTabNamePopup(QLineEdit):
    """Popup on top of the tab to edit its name."""

    def __init__(self, parent, split_char, split_index):
        """Popup on top of the tab to edit its name."""

        # Variables
        # Parent (main)
        self.main = parent if parent is not None else self.parent()
        self.split_char = split_char
        self.split_index = split_index

        # Track which tab is being edited
        self.tab_index = None

        # Track if any text has been typed
        self.has_typed = False

        # Track the initial tab text
        self.initial_text = None

        # Widget setup
        QLineEdit.__init__(self, parent=parent)

        # Slot to handle tab name update
        self.editingFinished.connect(self.edit_finished)

        # Even filter to catch clicks and ESC key
        self.installEventFilter(self)

        # Clean borders and no shadow to blend with tab
        if PYQT5:
            self.setWindowFlags(
                Qt.Popup |
                Qt.FramelessWindowHint |
                Qt.NoDropShadowWindowHint
            )
        else:
            self.setWindowFlags(
                Qt.Popup |
                Qt.FramelessWindowHint
            )
        self.setFrame(False)

    def eventFilter(self, widget, event):
        """Catch clicks outside the object and ESC key press."""
        if (
            event.type() == QEvent.MouseButtonPress
            and not self.geometry().contains(event.globalPos())
        ):
            # Exit editing and change text
            self.hide()
            return True
        elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            # Exit editing and restore initial text
            self.setText(self.initial_text)
            self.hide()
            return True
        elif event.type() == QEvent.KeyPress and event.text():
            # Remove left margin when the user starts typing to not crop long
            # names.
            if not self.has_typed:
                self.setTextMargins(0, 0, 0, 0)
                self.has_typed = True

        # Event is not interesting, raise to parent
        return QLineEdit.eventFilter(self, widget, event)

    def edit_tab(self, index):
        """Activate the edit tab."""
        self.has_typed = False

        # Sets focus, shows cursor
        self.setFocus()

        # Updates tab index
        self.tab_index = index

        # Gets tab size and adjust top margin
        rect = self.main.tabRect(index)
        top_margin = PANES_TABBAR_STYLESHEET.TOP_MARGIN.split('px')[0]
        rect.adjust(2, int(top_margin), 0, 0)

        # Sets size
        self.setFixedSize(rect.size())

        # Places on top of the tab
        self.move(self.main.mapToGlobal(rect.topLeft()))

        # Copies tab name and selects all
        self.initial_text = self.main.tabText(index)
        text = self.initial_text.replace('&', '')
        if self.split_char:
            text = text.split(self.split_char)[self.split_index]

        self.setText(text)
        self.selectAll()

        # Center text because it looks nicer.
        metrics = QFontMetrics(self.font())
        text_width = metrics.width(text) + self.font().pointSize()
        self.setTextMargins((rect.width() - text_width) // 2, 0, 0, 0)

        if not self.isVisible():
            # Makes editor visible
            self.show()

    def edit_finished(self):
        """On clean exit, update tab name."""
        # Hides editor
        self.hide()

        if isinstance(self.tab_index, int) and self.tab_index >= 0:
            # We are editing a valid tab, update name
            tab_text = to_text_string(self.text())
            self.main.setTabText(self.tab_index, tab_text)
            self.main.sig_name_changed.emit(tab_text)


class CloseTabButton(QToolButton):
    """Close button for our tabs."""

    SIZE = 16  # in pixels
    sig_clicked = Signal(int)

    def __init__(self, parent, index):
        super().__init__(parent)
        self.index = index

        # Icon and tooltip
        self.setIcon(ima.icon('fileclose'))
        self._tab_tooltip = ''

        # Size
        size = self.SIZE
        self.resize(size + 2, size + 6)
        self.setIconSize(QSize(size, size))

        # Colors for different states
        self._selected_tab_color = QStylePalette.COLOR_BACKGROUND_5
        self._not_selected_tab_color = QStylePalette.COLOR_BACKGROUND_4

        self._hover_selected_tab_color = QStylePalette.COLOR_BACKGROUND_6
        self._hover_not_selected_tab_color = QStylePalette.COLOR_BACKGROUND_5

        self._clicked_selected_tab_color = (
            Gray.B70 if is_dark_interface() else Gray.B80
        )
        self._clicked_not_selected_tab_color = QStylePalette.COLOR_BACKGROUND_6

        # To keep track of the tab's current color
        self._tab_color = self._selected_tab_color

        # Stylesheet
        self.css = qstylizer.style.StyleSheet()
        self.css.QToolButton.setValues(
            marginTop='9px',
            marginBottom='-7px',
            marginLeft='3px' if MAC else '2px',
            marginRight='-7px' if MAC else '-6px',
            padding='0px',
            paddingTop='-5px' if (MAC or WIN) else '-8px',
            borderRadius='3px'
        )

        self._set_background_color(self._selected_tab_color)

        # Signals
        self.clicked.connect(lambda: self.sig_clicked.emit(self.index))

    def enterEvent(self, event):
        """Actions to take when hovering the widget with the mouse."""
        # Set background color on hover according to the tab one
        if self._tab_color == self._selected_tab_color:
            self._set_background_color(self._hover_selected_tab_color)
        else:
            self._set_background_color(self._hover_not_selected_tab_color)

        # Don't show tooltip on hover because it's annoying
        self._tab_tooltip = self.parent().tabToolTip(self.index)
        self.parent().setTabToolTip(self.index, '')

        super().enterEvent(event)

    def leaveEvent(self, event):
        """Actions to take when leaving the widget with the mouse."""
        # Restore background color
        if self._tab_color == self._selected_tab_color:
            self._set_background_color(self._selected_tab_color)
        else:
            self._set_background_color(self._not_selected_tab_color)

        # Restore tab tooltip
        self.parent().setTabToolTip(self.index, self._tab_tooltip)

        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Actions to take when clicking the widget."""
        # Set the clicked state for the button
        if self._tab_color == self._selected_tab_color:
            self._set_background_color(self._clicked_selected_tab_color)
        else:
            self._set_background_color(self._clicked_not_selected_tab_color)

        super().mousePressEvent(event)

    def set_selected_color(self):
        """Set background color when the tab is selected."""
        self._tab_color = self._selected_tab_color
        self._set_background_color(self._selected_tab_color)

    def set_not_selected_color(self):
        """Set background color when the tab is not selected."""
        self._tab_color = self._not_selected_tab_color
        self._set_background_color(self._not_selected_tab_color)

    def _set_background_color(self, background_color):
        """Auxiliary function to set the widget's background color."""
        self.css.setValues(backgroundColor=f'{background_color}')
        self.setStyleSheet(self.css.toString())


class TabBar(QTabBar):
    """Tabs base class with drag and drop support"""
    sig_move_tab = Signal((int, int), (str, int, int))
    sig_name_changed = Signal(str)

    def __init__(self, parent, ancestor, rename_tabs=False, split_char='',
                 split_index=0):
        QTabBar.__init__(self, parent)
        self.ancestor = ancestor
        self.setObjectName('pane-tabbar')

        # Dragging tabs
        self.__drag_start_pos = QPoint()
        self.setAcceptDrops(True)
        self.setUsesScrollButtons(True)
        self.setMovable(True)

        # Tab name editor
        self.rename_tabs = rename_tabs
        if self.rename_tabs:
            # Creates tab name editor
            self.tab_name_editor = EditTabNamePopup(self, split_char,
                                                    split_index)
        else:
            self.tab_name_editor = None

        self.close_btn_side = QTabBar.LeftSide if MAC else QTabBar.RightSide

        # Signals
        self.currentChanged.connect(self._on_tab_changed)
        self.tabMoved.connect(self._on_tab_moved)

    def refresh_style(self):
        """Refresh the widget style."""
        self._on_tab_changed(self.currentIndex())

    def _on_tab_changed(self, index):
        """Actions to take when the current tab has changed."""
        # Repaint background color of close buttons
        for i in range(self.count()):
            close_btn: CloseTabButton = self.tabButton(i, self.close_btn_side)

            if close_btn:
                close_btn.index = i

                if i == index:
                    close_btn.set_selected_color()
                else:
                    close_btn.set_not_selected_color()

    def _on_tab_moved(self, index_from, index_to):
        """Actions to take when drag and drop a tab to a different place."""
        # Repaint background color of switched buttons
        close_btn_from = self.tabButton(index_from, self.close_btn_side)
        close_btn_to = self.tabButton(index_to, self.close_btn_side)

        close_btn_from.index, close_btn_to.index = index_from, index_to

        close_btn_from.set_not_selected_color()
        close_btn_to.set_selected_color()

    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() == Qt.LeftButton:
            self.__drag_start_pos = QPoint(event.pos())
        QTabBar.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        """Override Qt method"""
        # FIXME: This was added by Pierre presumably to move tabs
        # between plugins, but righit now it's breaking the regular
        # Qt drag behavior for tabs, so we're commenting it for
        # now
        #if event.buttons() == Qt.MouseButtons(Qt.LeftButton) and \
        #   (event.pos() - self.__drag_start_pos).manhattanLength() > \
        #        QApplication.startDragDistance():
        #    drag = QDrag(self)
        #    mimeData = QMimeData()#

        #    ancestor_id = to_text_string(id(self.ancestor))
        #    parent_widget_id = to_text_string(id(self.parentWidget()))
        #    self_id = to_text_string(id(self))
        #    source_index = to_text_string(self.tabAt(self.__drag_start_pos))

        #    mimeData.setData("parent-id", to_binary_string(ancestor_id))
        #    mimeData.setData("tabwidget-id",
        #                     to_binary_string(parent_widget_id))
        #    mimeData.setData("tabbar-id", to_binary_string(self_id))
        #    mimeData.setData("source-index", to_binary_string(source_index))

        #    drag.setMimeData(mimeData)
        #    drag.exec_()
        QTabBar.mouseMoveEvent(self, event)

    def dragEnterEvent(self, event):
        """Override Qt method"""
        mimeData = event.mimeData()
        formats = list(mimeData.formats())

        if (
            "parent-id" in formats
            and int(mimeData.data("parent-id")) == id(self.ancestor)
        ):
            event.acceptProposedAction()

        QTabBar.dragEnterEvent(self, event)

    def dropEvent(self, event):
        """Override Qt method"""
        mimeData = event.mimeData()
        index_from = int(mimeData.data("source-index"))
        index_to = self.tabAt(event.pos())
        if index_to == -1:
            index_to = self.count()
        if int(mimeData.data("tabbar-id")) != id(self):
            tabwidget_from = to_text_string(mimeData.data("tabwidget-id"))

            # We pass self object ID as a QString, because otherwise it would
            # depend on the platform: long for 64bit, int for 32bit. Replacing
            # by long all the time is not working on some 32bit platforms.
            # See spyder-ide/spyder#1094 and spyder-ide/spyder#1098.
            self.sig_move_tab[(str, int, int)].emit(tabwidget_from, index_from,
                                                    index_to)
            event.acceptProposedAction()
        elif index_from != index_to:
            self.sig_move_tab.emit(index_from, index_to)
            event.acceptProposedAction()
        QTabBar.dropEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Override Qt method to trigger the tab name editor."""
        if (
            self.rename_tabs is True
            and event.buttons() == Qt.MouseButtons(Qt.LeftButton)
        ):
            # Tab index
            index = self.tabAt(event.pos())
            if index >= 0:
                # Tab is valid, call tab name editor
                self.tab_name_editor.edit_tab(index)
        else:
            # Event is not interesting, raise to parent
            QTabBar.mouseDoubleClickEvent(self, event)

    def tabInserted(self, index):
        """Actions to take when a new tab is added or inserted."""
        # Use our own close button because we can style it to our needs.
        close_button = CloseTabButton(self, index)

        # Request to close the tab when the close button is clicked
        close_button.sig_clicked.connect(self.tabCloseRequested)

        # Set close button
        self.setTabButton(index, self.close_btn_side, close_button)


class BaseTabs(QTabWidget):
    """TabWidget with context menu and corner widgets"""
    sig_close_tab = Signal(int)

    def __init__(self, parent, actions=None, menu=None,
                 corner_widgets=None, menu_use_tooltips=False):
        QTabWidget.__init__(self, parent)
        self.setTabBar(TabBar(self, parent))

        # Needed to prevent eliding tabs text on MacOS
        # See spyder-ide/spyder#18817
        self.setElideMode(Qt.ElideNone)
        self.tabBar().setObjectName('pane-tabbar')

        self.corner_widgets = {}
        self.menu_use_tooltips = menu_use_tooltips

        if menu is None:
            self.menu = QMenu(self)
            if actions:
                add_actions(self.menu, actions)
        else:
            self.menu = menu

        self.setStyleSheet(str(PANES_TABBAR_STYLESHEET))

        # Corner widgets
        if corner_widgets is None:
            corner_widgets = {}
        corner_widgets.setdefault(Qt.TopLeftCorner, [])
        corner_widgets.setdefault(Qt.TopRightCorner, [])

        self.browse_button = create_toolbutton(
            self, icon=ima.icon('browse_tab'), tip=_("Browse tabs"))
        self.browse_button.setStyleSheet(str(PANES_TABBAR_STYLESHEET))

        self.browse_tabs_menu = QMenu(self)
        self.browse_tabs_menu.setObjectName('checkbox-padding')
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

            # This removes some white dots in our tabs (not all but most).
            # See spyder-ide/spyder#15081
            cwidget.setObjectName('corner-widget')
            cwidget.setStyleSheet(
                "QWidget#corner-widget {border-radius: '0px'}")

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

    def get_offset_pos(self, event):
        """
        Add offset to position event to capture the mouse cursor
        inside a tab.
        """
        # This is necessary because event.pos() is the position in this
        # widget, not in the tabBar. see spyder-ide/spyder#12617
        tb = self.tabBar()
        point = tb.mapFromGlobal(event.globalPos())
        return tb.tabAt(point)

    def contextMenuEvent(self, event):
        """Override Qt method"""
        index = self.get_offset_pos(event)
        self.setCurrentIndex(index)
        if self.menu:
            self.menu.popup(event.globalPos())

    def mousePressEvent(self, event):
        """Override Qt method"""
        if event.button() == Qt.MidButton:
            index = self.get_offset_pos(event)
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
            if key == Qt.Key_PageUp or key == Qt.Key_8:
                if index > 0:
                    self.setCurrentIndex(index - 1)
                else:
                    self.setCurrentIndex(self.count() - 1)
                handled = True
            elif key == Qt.Key_PageDown or key == Qt.Key_9:
                if index < self.count() - 1:
                    self.setCurrentIndex(index + 1)
                else:
                    self.setCurrentIndex(0)
                handled = True
        if not handled:
            QTabWidget.keyPressEvent(self, event)

    def tab_navigate(self, delta=1):
        """Ctrl+Tab"""
        if delta > 0 and self.currentIndex() == self.count()-1:
            index = delta-1
        elif delta < 0 and self.currentIndex() == 0:
            index = self.count()+delta
        else:
            index = self.currentIndex()+delta
        self.setCurrentIndex(index)

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

    def refresh_style(self):
        """Refresh the widget style."""
        self.tabBar().refresh_style()


class Tabs(BaseTabs):
    """BaseTabs widget with movable tabs and tab navigation shortcuts."""
    # Signals
    move_data = Signal(int, int)
    move_tab_finished = Signal()
    sig_move_tab = Signal(str, str, int, int)

    def __init__(self, parent, actions=None, menu=None,
                 corner_widgets=None, menu_use_tooltips=False,
                 rename_tabs=False, split_char='',
                 split_index=0):
        BaseTabs.__init__(self, parent, actions, menu,
                          corner_widgets, menu_use_tooltips)
        tab_bar = TabBar(self, parent,
                         rename_tabs=rename_tabs,
                         split_char=split_char,
                         split_index=split_index)
        tab_bar.sig_move_tab.connect(self.move_tab)
        tab_bar.sig_move_tab[(str, int, int)].connect(
            self.move_tab_from_another_tabwidget)
        self.setTabBar(tab_bar)

        CONF.config_shortcut(
            lambda: self.tab_navigate(1),
            context='editor',
            name='go to next file',
            parent=parent)

        CONF.config_shortcut(
            lambda: self.tab_navigate(-1),
            context='editor',
            name='go to previous file',
            parent=parent)

        CONF.config_shortcut(
            lambda: self.sig_close_tab.emit(self.currentIndex()),
            context='editor',
            name='close file 1',
            parent=parent)

        CONF.config_shortcut(
            lambda: self.sig_close_tab.emit(self.currentIndex()),
            context='editor',
            name='close file 2',
            parent=parent)

    @Slot(int, int)
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

    @Slot(str, int, int)
    def move_tab_from_another_tabwidget(self, tabwidget_from,
                                        index_from, index_to):
        """Move tab from a tabwidget to another"""

        # We pass self object IDs as QString objs, because otherwise it would
        # depend on the platform: long for 64bit, int for 32bit. Replacing
        # by long all the time is not working on some 32bit platforms.
        # See spyder-ide/spyder#1094 and spyder-ide/spyder#1098.
        self.sig_move_tab.emit(tabwidget_from, to_text_string(id(self)),
                               index_from, index_to)

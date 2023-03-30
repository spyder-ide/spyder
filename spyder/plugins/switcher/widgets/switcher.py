# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Switcher Main Widget."""


# Third party imports
from qtpy.QtCore import QEvent, QObject, Qt, Signal, Slot, QModelIndex
from qtpy.QtGui import QStandardItemModel
from qtpy.QtWidgets import (QAbstractItemView, QDialog, QLineEdit,
                            QListView, QListWidgetItem, QStyle,
                            QVBoxLayout)

# Local imports
from spyder.plugins.switcher.widgets.proxymodel import SwitcherProxyModel
from spyder.plugins.switcher.widgets.item import (
    SwitcherItem, SwitcherSeparatorItem)
from spyder.py3compat import TEXT_TYPES, to_text_string
from spyder.utils.icon_manager import ima
from spyder.widgets.helperwidgets import HTMLDelegate
from spyder.utils.stringmatching import get_search_scores
from spyder.plugins.switcher.utils import clean_string


# Style dict constants
FONT_SIZE = 10
ITEM_STYLES = {
    'title_color': ima.MAIN_FG_COLOR,
    'description_color': 'rgb(153, 153, 153)',
    'section_color': 'rgb(70, 179, 239)',
    'shortcut_color': 'rgb(153, 153, 153)',
    'title_font_size': FONT_SIZE,
    'description_font_size': FONT_SIZE,
    'section_font_size': FONT_SIZE,
    'shortcut_font_size': FONT_SIZE,
}

ITEM_SEPARATOR_STYLES = {
    'color': ima.MAIN_FG_COLOR,
    'font_size': FONT_SIZE,
}


class KeyPressFilter(QObject):
    """Use with `installEventFilter` to get up/down arrow key press signal."""

    sig_up_key_pressed = Signal()
    sig_down_key_pressed = Signal()
    sig_enter_key_pressed = Signal()

    def eventFilter(self, src, e):
        """Override Qt eventFilter."""
        if e.type() == QEvent.KeyPress:
            if e.key() == Qt.Key_Up:
                self.sig_up_key_pressed.emit()
                return True
            elif e.key() == Qt.Key_Down:
                self.sig_down_key_pressed.emit()
                return True
            elif (e.key() == Qt.Key_Return):
                self.sig_enter_key_pressed.emit()
                return True
        return super(KeyPressFilter, self).eventFilter(src, e)


class SwitcherDelegate(HTMLDelegate):
    """
    This delegate allows the list view of the switcher to look like it has
    the focus, even when its focus policy is set to Qt.NoFocus.
    """

    def paint(self, painter, option, index):
        """
        Override Qt method to force this delegate to look active at all times.
        """
        option.state |= QStyle.State_Active
        super(SwitcherDelegate, self).paint(painter, option, index)


class Switcher(QDialog):
    """
    A multi purpose switcher.

    Example
    -------
      SwitcherItem:      [title description    <shortcut> section]
      SwitcherItem:      [title description    <shortcut> section]
      SwitcherSeparator: [---------------------------------------]
      SwitcherItem:      [title description    <shortcut> section]
      SwitcherItem:      [title description    <shortcut> section]
    """

    # Dismissed switcher
    sig_rejected = Signal()
    # Search/Filter text changes
    sig_text_changed = Signal(TEXT_TYPES[-1])
    # Current item changed
    sig_item_changed = Signal(object)
    # List item selected, mode and cleaned search text
    sig_item_selected = Signal(object, TEXT_TYPES[-1], TEXT_TYPES[-1], )
    sig_mode_selected = Signal(TEXT_TYPES[-1])

    _MAX_NUM_ITEMS = 15
    _MIN_WIDTH = 580
    _MIN_HEIGHT = 200
    _MAX_HEIGHT = 390
    _ITEM_WIDTH = _MIN_WIDTH - 20

    def __init__(self, parent, help_text=None, item_styles=ITEM_STYLES,
                 item_separator_styles=ITEM_SEPARATOR_STYLES):
        """Multi purpose switcher."""
        super(Switcher, self).__init__(parent)
        self._modes = {}
        self._mode_on = ''
        self._item_styles = item_styles
        self._item_separator_styles = item_separator_styles

        # Widgets
        self.edit = QLineEdit(self)
        self.list = QListView(self)
        self.model = QStandardItemModel(self.list)
        self.proxy = SwitcherProxyModel(self.list)
        self.filter = KeyPressFilter()

        # Widgets setup
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setWindowOpacity(0.95)
#        self.setMinimumHeight(self._MIN_HEIGHT)
        self.setMaximumHeight(self._MAX_HEIGHT)
        self.edit.installEventFilter(self.filter)
        self.edit.setPlaceholderText(help_text if help_text else '')
        self.list.setMinimumWidth(self._MIN_WIDTH)
        self.list.setItemDelegate(SwitcherDelegate(self))
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setSelectionBehavior(self.list.SelectItems)
        self.list.setSelectionMode(self.list.SingleSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.proxy.setSourceModel(self.model)
        self.list.setModel(self.proxy)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        layout.addWidget(self.list)
        self.setLayout(layout)

        # Signals
        self.filter.sig_up_key_pressed.connect(self.previous_row)
        self.filter.sig_down_key_pressed.connect(self.next_row)
        self.filter.sig_enter_key_pressed.connect(self.enter)
        self.edit.textChanged.connect(self.setup)
        self.edit.textChanged.connect(self.sig_text_changed)
        self.edit.returnPressed.connect(self.enter)
        self.list.clicked.connect(self.enter)
        self.list.clicked.connect(self.edit.setFocus)
        self.list.selectionModel().currentChanged.connect(
            self.current_item_changed)
        self.edit.setFocus()

    # ---- Helper methods
    def _add_item(self, item, last_item=True):
        """Perform common actions when adding items."""
        item.set_width(self._ITEM_WIDTH)
        self.model.appendRow(item)
        if last_item:
            # Only set the current row to the first item when the added item is
            # the last one in order to prevent performance issues when
            # adding multiple items
            self.set_current_row(0)
            self.set_height()
        self.setup_sections()

    # ---- API
    def clear(self):
        """Remove all items from the list and clear the search text."""
        self.set_placeholder_text('')
        self.model.beginResetModel()
        self.model.clear()
        self.model.endResetModel()
        self.setMinimumHeight(self._MIN_HEIGHT)

    def set_placeholder_text(self, text):
        """Set the text appearing on the empty line edit."""
        self.edit.setPlaceholderText(text)

    def add_mode(self, token, description):
        """Add mode by token key and description."""
        if len(token) == 1:
            self._modes[token] = description
        else:
            raise Exception('Token must be of length 1!')

    def get_mode(self):
        """Get the current mode the switcher is in."""
        return self._mode_on

    def remove_mode(self, token):
        """Remove mode by token key."""
        if token in self._modes:
            self._modes.pop(token)

    def clear_modes(self):
        """Delete all modes spreviously defined."""
        del self._modes
        self._modes = {}

    def add_item(self, icon=None, title=None, description=None, shortcut=None,
                 section=None, data=None, tool_tip=None, action_item=False,
                 last_item=True):
        """Add switcher list item."""
        item = SwitcherItem(
            parent=self.list,
            icon=icon,
            title=title,
            description=description,
            data=data,
            shortcut=shortcut,
            section=section,
            action_item=action_item,
            tool_tip=tool_tip,
            styles=self._item_styles
        )
        self._add_item(item, last_item=last_item)

    def add_separator(self):
        """Add separator item."""
        item = SwitcherSeparatorItem(parent=self.list,
                                     styles=self._item_separator_styles)
        self._add_item(item)

    def setup(self):
        """Set-up list widget content based on the filtering."""
        # Check exited mode
        mode = self._mode_on
        if mode:
            search_text = self.search_text()[len(mode):]
        else:
            search_text = self.search_text()

        # Check exited mode
        if self.search_text() == '':
            self._mode_on = ''
            self.clear()
            self.proxy.set_filter_by_score(False)
            self.sig_mode_selected.emit(self._mode_on)
            return

        # Check entered mode
        for key in self._modes:
            if self.search_text().startswith(key) and not mode:
                self._mode_on = key
                self.sig_mode_selected.emit(key)
                return

        # Filter by text
        titles = []
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if isinstance(item, SwitcherItem):
                title = item.get_title()
            else:
                title = ''
            titles.append(title)

        search_text = clean_string(search_text)
        scores = get_search_scores(to_text_string(search_text),
                                   titles, template=u"<b>{0}</b>")

        for idx, (title, rich_title, score_value) in enumerate(scores):
            item = self.model.item(idx)
            if not self._is_separator(item) and not item.is_action_item():
                rich_title = rich_title.replace(" ", "&nbsp;")
                item.set_rich_title(rich_title)
            item.set_score(score_value)
        self.proxy.set_filter_by_score(True)

        self.setup_sections()
        if self.count():
            self.set_current_row(0)
        else:
            self.set_current_row(-1)
        self.set_height()

    def setup_sections(self):
        """Set-up which sections appear on the item list."""
        mode = self._mode_on
        if mode:
            search_text = self.search_text()[len(mode):]
        else:
            search_text = self.search_text()

        if search_text:
            for row in range(self.model.rowCount()):
                item = self.model.item(row)
                if isinstance(item, SwitcherItem):
                    item.set_section_visible(False)
        else:
            sections = []
            for row in range(self.model.rowCount()):
                item = self.model.item(row)
                if isinstance(item, SwitcherItem):
                    sections.append(item.get_section())
                    item.set_section_visible(bool(search_text))
                else:
                    sections.append('')

                if row != 0:
                    visible = sections[row] != sections[row - 1]
                    if not self._is_separator(item):
                        item.set_section_visible(visible)
                else:
                    item.set_section_visible(True)

        self.proxy.sortBy('_score')
        self.sig_item_changed.emit(self.current_item())

    def set_height(self):
        """Set height taking into account the number of items."""
        if self.count() >= self._MAX_NUM_ITEMS:
            switcher_height = self._MAX_HEIGHT
        elif self.count() != 0 and self.current_item():
            current_item = self.current_item()
            item_height = current_item.get_height()
            list_height = item_height * (self.count() + 3)
            edit_height = self.edit.height()
            spacing_height = self.layout().spacing() * 4
            switcher_height = list_height + edit_height + spacing_height
            switcher_height = max(switcher_height, self._MIN_HEIGHT)
        else:
            switcher_height = self._MIN_HEIGHT
        self.setFixedHeight(int(switcher_height))

    def set_position(self, top):
        """Set the position of the dialog."""
        parent = self.parent()
        if parent is not None:
            geo = parent.geometry()
            width = self.list.width()  # This has been set in setup
            left = parent.geometry().width()/2 - width/2

            while parent:
                geo = parent.geometry()
                top += geo.top()
                left += geo.left()
                parent = parent.parent()

            self.move(round(left), top)

    @Slot(QModelIndex, QModelIndex)
    def current_item_changed(self, current, previous):
        """Handle item selection."""
        self.sig_item_changed.emit(self.current_item())

    # ---- Qt overrides
    # ------------------------------------------------------------------------
    @Slot()
    @Slot(QListWidgetItem)
    def enter(self, itemClicked=None):
        """Override Qt method."""
        row = self.current_row()
        model_index = self.proxy.mapToSource(self.proxy.index(row, 0))
        item = self.model.item(model_index.row())
        if item:
            mode = self._mode_on
            self.sig_item_selected.emit(item, mode,
                                        self.search_text()[len(mode):])

    def accept(self):
        """Override Qt method."""
        super(Switcher, self).accept()

    def reject(self):
        """Override Qt method."""
        self.set_search_text('')
        self.sig_rejected.emit()
        super(Switcher, self).reject()

    def resizeEvent(self, event):
        """Override Qt method."""
        super(Switcher, self).resizeEvent(event)

    # ---- Helper methods: Lineedit widget
    def search_text(self):
        """Get the normalized (lowecase) content of the search text."""
        return to_text_string(self.edit.text()).lower()

    def set_search_text(self, string):
        """Set the content of the search text."""
        self.edit.setText(string)

    # ---- Helper methods: List widget
    def _is_separator(self, item):
        """Check if item is an separator item (SwitcherSeparatorItem)."""
        return isinstance(item, SwitcherSeparatorItem)

    def _select_row(self, steps):
        """Select row in list widget based on a number of steps with direction.

        Steps can be positive (next rows) or negative (previous rows).
        """
        row = self.current_row() + steps
        if 0 <= row < self.count():
            self.set_current_row(row)

    def count(self):
        """Get the item count in the list widget."""
        return self.proxy.rowCount()

    def current_row(self):
        """Return the current selected row in the list widget."""
        return self.list.currentIndex().row()

    def current_item(self):
        """Return the current selected item in the list widget."""
        row = self.current_row()
        model_index = self.proxy.mapToSource(self.proxy.index(row, 0))
        item = self.model.item(model_index.row())
        return item

    def set_current_row(self, row):
        """Set the current selected row in the list widget."""
        proxy_index = self.proxy.index(row, 0)
        selection_model = self.list.selectionModel()

        # https://doc.qt.io/qt-5/qitemselectionmodel.html#SelectionFlag-enum
        selection_model.setCurrentIndex(
            proxy_index, selection_model.ClearAndSelect)

        # Ensure that the selected item is visible
        self.list.scrollTo(proxy_index, QAbstractItemView.EnsureVisible)

    def previous_row(self):
        """Select previous row in list widget."""
        steps = 1
        prev_row = self.current_row() - steps

        if prev_row == -1:
            self.set_current_row(self.count() - 1)
        else:
            if prev_row >= 0:
                # Need to map the filtered list to the actual model items
                list_index = self.proxy.index(prev_row, 0)
                model_index = self.proxy.mapToSource(list_index)
                item = self.model.item(model_index.row(), 0)
                if self._is_separator(item):
                    steps += 1
            self._select_row(-steps)

    def next_row(self):
        """Select next row in list widget."""
        steps = 1
        next_row = self.current_row() + steps

        # Need to map the filtered list to the actual model items
        list_index = self.proxy.index(next_row, 0)
        model_index = self.proxy.mapToSource(list_index)
        item = self.model.item(model_index.row(), 0)

        if next_row >= self.count():
            self.set_current_row(0)
        else:
            if item:
                if self._is_separator(item):
                    steps += 1
            self._select_row(steps)

# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Switcher widget interface."""

# Standard library imports
from __future__ import print_function
import os
import sys

# Third party imports
from qtpy.QtCore import (QEvent, QObject, QSize, QSortFilterProxyModel, Qt,
                         Signal, Slot, QModelIndex)
from qtpy.QtGui import QStandardItem, QStandardItemModel, QTextDocument
from qtpy.QtWidgets import (QAbstractItemView, QApplication, QDialog,
                            QLineEdit, QListView, QListWidgetItem, QStyle,
                            QVBoxLayout)

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.config.utils import is_ubuntu
from spyder.py3compat import TEXT_TYPES, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.stringmatching import get_search_scores
from spyder.widgets.helperwidgets import HTMLDelegate

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


def clean_string(text):
    """Remove regex special characters from string."""
    for ch in ('(', ')', '.', '\\', '?', '*', '[', ']', '&', '|', '^', '+'):
        text = text.replace(ch, '')
    return text


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


class SwitcherBaseItem(QStandardItem):
    """Base List Item."""

    _PADDING = 5
    _WIDTH = 400
    _STYLES = None
    _TEMPLATE = None

    def __init__(self, parent=None, styles=_STYLES):
        """Create basic List Item."""
        super(SwitcherBaseItem, self).__init__()

        # Style
        self._width = self._WIDTH
        self._padding = self._PADDING
        self._styles = styles if styles else {}
        self._action_item = False
        self._score = -1
        self._height = self._get_height()

        # Setup
        # self._height is a float from QSizeF but
        # QSize() expects a QSize or (int, int) as parameters
        self.setSizeHint(QSize(0, int(self._height)))

    def _render_text(self):
        """Render the html template for this item."""
        raise NotImplementedError

    def _set_rendered_text(self):
        """Set the rendered html template as text of this item."""
        self.setText(self._render_text())

    def _set_styles(self):
        """Set the styles for this item."""
        raise NotImplementedError

    def _get_height(self):
        """
        Return the expected height of this item's text, including
        the text margins.
        """
        raise NotImplementedError

    # --- API
    def set_width(self, value):
        """Set the content width."""
        self._width = value - (self._padding * 3)
        self._set_rendered_text()

    def get_width(self):
        """Return the content width."""
        return self._width

    def get_height(self):
        """Return the content height."""
        return self._height

    def get_score(self):
        """Return the fuzzy matchig score."""
        return self._score

    def set_score(self, value):
        """Set the search text fuzzy match score."""
        self._score = value
        self._set_rendered_text()

    def is_action_item(self):
        """Return whether the item is of action type."""
        return bool(self._action_item)

    # --- Qt overrides
    def refresh(self):
        """Override Qt."""
        super(SwitcherBaseItem, self).refresh()
        self._set_styles()
        self._set_rendered_text()


class SwitcherSeparatorItem(SwitcherBaseItem):
    """
    Separator Item represented as <hr>.

    Based on HTML delegate.

    See: https://doc.qt.io/qt-5/richtext-html-subset.html
    """

    _SEPARATOR = '_'
    _STYLE_ATTRIBUTES = ['color', 'font_size']
    _STYLES = {
        'color': QApplication.palette().text().color().name(),
        'font_size': 10,
    }
    _TEMPLATE = \
        u'''<table cellpadding="{padding}" cellspacing="0" width="{width}"
                  height="{height}" border="0">
  <tr><td valign="top" align="center"><hr></td></tr>
</table>'''

    def __init__(self, parent=None, styles=_STYLES):
        """Separator Item represented as <hr>."""
        super(SwitcherSeparatorItem, self).__init__(parent=parent,
                                                    styles=styles)
        self.setFlags(Qt.NoItemFlags)
        self._set_rendered_text()

    # --- Helpers
    def _set_styles(self):
        """Set the styles for this item."""
        for attr in self._STYLE_ATTRIBUTES:
            if attr not in self._styles:
                self._styles[attr] = self._STYLES[attr]

        rich_font = self._styles['font_size']

        if sys.platform == 'darwin':
            font_size = rich_font
        elif os.name == 'nt':
            font_size = rich_font
        elif is_ubuntu():
            font_size = rich_font - 2
        else:
            font_size = rich_font - 2

        self._styles['font_size'] = font_size

    def _render_text(self):
        """Render the html template for this item."""
        padding = self._padding
        width = self._width
        height = self.get_height()
        text = self._TEMPLATE.format(width=width, height=height,
                                     padding=padding, **self._styles)
        return text

    def _get_height(self):
        """
        Return the expected height of this item's text, including
        the text margins.
        """
        doc = QTextDocument()
        doc.setHtml('<hr>')
        doc.setDocumentMargin(self._PADDING)
        return doc.size().height()


class SwitcherItem(SwitcherBaseItem):
    """
    Switcher item with title, description, shortcut and section.

    SwitcherItem: [title description    <shortcut> section]

    Based on HTML delegate.
    See: https://doc.qt.io/qt-5/richtext-html-subset.html
    """

    _FONT_SIZE = 10
    _STYLE_ATTRIBUTES = ['title_color', 'description_color', 'section_color',
                         'shortcut_color', 'title_font_size',
                         'description_font_size', 'section_font_size',
                         'shortcut_font_size']
    _STYLES = {
        'title_color': QApplication.palette().text().color().name(),
        'description_color': 'rgb(153, 153, 153)',
        'section_color': 'rgb(70, 179, 239)',
        'shortcut_color': 'rgb(153, 153, 153)',
        'title_font_size': _FONT_SIZE,
        'description_font_size': _FONT_SIZE,
        'section_font_size': _FONT_SIZE,
        'shortcut_font_size': _FONT_SIZE,
    }
    _TEMPLATE = u'''
<table width="{width}" max_width="{width}" height="{height}"
                          cellpadding="{padding}">
  <tr>
    <td valign="middle">
      <span style="color:{title_color};font-size:{title_font_size}pt">
        {title}
      </span>&nbsp;
      <small
       style="color:{description_color};font-size:{description_font_size}pt">
        <span>{description}</span>
      </small>
    </td>
    <td valign="middle" align="right" float="right">
      <span style="color:{shortcut_color};font-size:{shortcut_font_size}pt">
         <small><code><i>{shortcut}</i></code></small>
      </span>&nbsp;
      <span style="color:{section_color};font-size:{section_font_size}pt">
         <small>{section}</small>
      </span>
    </td>
  </tr>
</table>'''

    def __init__(self, parent=None, icon=None, title=None, description=None,
                 shortcut=None, section=None, data=None, tool_tip=None,
                 action_item=False, styles=_STYLES):
        """Switcher item with title, description, shortcut and section."""
        super(SwitcherItem, self).__init__(parent=parent, styles=styles)

        self._title = title if title else ''
        self._rich_title = ''
        self._shortcut = shortcut if shortcut else ''
        self._description = description if description else ''
        self._section = section if section else ''
        self._icon = icon
        self._data = data
        self._score = -1
        self._action_item = action_item

        self._section_visible = True

        # Setup
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        if icon:
            self.setIcon(icon)
            # TODO: Change fixed icon size value
            self._icon_width = 20
        else:
            self._icon_width = 0

        self._set_styles()
        self._set_rendered_text()

    # --- Helpers
    def _render_text(self, title=None, description=None, section=None):
        """Render the html template for this item."""
        if self._rich_title:
            title = self._rich_title
        else:
            title = title if title else self._title

        # TODO: Based on width this should elide/shorten
        description = description if description else self._description

        if self._section_visible:
            section = section if section else self._section
        else:
            section = ''

        padding = self._PADDING
        width = int(self._width - self._icon_width)
        height = int(self.get_height())
        self.setSizeHint(QSize(width, height))

        shortcut = '&lt;' + self._shortcut + '&gt;' if self._shortcut else ''

        title = to_text_string(title, encoding='utf-8')
        section = to_text_string(section, encoding='utf-8')
        description = to_text_string(description, encoding='utf-8')
        shortcut = to_text_string(shortcut, encoding='utf-8')

        text = self._TEMPLATE.format(width=width, height=height, title=title,
                                     section=section, description=description,
                                     padding=padding, shortcut=shortcut,
                                     **self._styles)
        return text

    def _set_styles(self):
        """Set the styles for this item."""
        for attr in self._STYLE_ATTRIBUTES:
            if attr not in self._styles:
                self._styles[attr] = self._STYLES[attr]

        rich_font = self._styles['title_font_size']

        if sys.platform == 'darwin':
            title_font_size = rich_font
            description_font_size = title_font_size + 2
        elif os.name == 'nt':
            title_font_size = rich_font
            description_font_size = title_font_size + 1
        elif is_ubuntu():
            title_font_size = rich_font - 2
            description_font_size = title_font_size + 1
        else:
            title_font_size = rich_font - 2
            description_font_size = title_font_size + 1

        self._styles['description_font_size'] = description_font_size
        self._styles['section_font_size'] = description_font_size

    def _get_height(self):
        """
        Return the expected height of this item's text, including
        the text margins.
        """
        doc = QTextDocument()
        try:
            doc.setHtml('<span style="font-size:{}pt">Title</span>'
                        .format(self._styles['title_font_size']))
        except KeyError:
            doc.setHtml('<span>Title</span>')
        doc.setDocumentMargin(self._PADDING)
        return doc.size().height()

    # --- API
    def set_icon(self, icon):
        """Set the QIcon for the list item."""
        self._icon = icon
        self.setIcon(icon)

    def get_icon(self):
        """Return the QIcon for the list item."""
        return self._icon

    def set_title(self, value):
        """Set the main text (title) of the item."""
        self._title = value
        self._set_rendered_text()

    def get_title(self):
        """Return the the main text (title) of the item."""
        return self._title

    def set_rich_title(self, value):
        """Set the rich title version (filter highlight) of the item."""
        self._rich_title = value
        self._set_rendered_text()

    def get_rich_title(self):
        """Return the rich title version (filter highlight) of the item."""
        return self._rich_title

    def set_description(self, value):
        """Set the item description text."""
        self._description = value
        self._set_rendered_text()

    def get_description(self):
        """Return the item description text."""
        return self._description

    def set_shortcut(self, value):
        """Set the shortcut for the item action."""
        self._shortcut = value
        self._set_rendered_text()

    def get_shortcut(self, value):
        """Return the shortcut for the item action."""
        return self._shortcut

    def set_tooltip(self, value):
        """Set the tooltip text for the item."""
        super(SwitcherItem, self).setTooltip(value)

    def set_data(self, value):
        """Set the additional data associated to the item."""
        self._data = value

    def get_data(self):
        """Return the additional data associated to the item."""
        return self._data

    def set_section(self, value):
        """Set the item section name."""
        self._section = value
        self._set_rendered_text()

    def get_section(self):
        """Return the item section name."""
        return self._section

    def set_section_visible(self, value):
        """Set visibility of the item section."""
        self._section_visible = value
        self._set_rendered_text()

    def set_action_item(self, value):
        """Enable/disable the action type for the item."""
        self._action_item = value
        self._set_rendered_text()


class SwitcherProxyModel(QSortFilterProxyModel):
    """A proxy model to perform sorting on the scored items."""

    def __init__(self, parent=None):
        """Proxy model to perform sorting on the scored items."""
        super(SwitcherProxyModel, self).__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)
        self.__filter_by_score = False

    def set_filter_by_score(self, value):
        """
        Set whether the items should be filtered by their score result.

        Parameters
        ----------
        value : bool
           Indicates whether the items should be filtered by their
           score result.
        """
        self.__filter_by_score = value
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """Override Qt method to filter items by their score result."""
        item = self.sourceModel().item(source_row)
        if self.__filter_by_score is False or item.is_action_item():
            return True
        else:
            return not item.get_score() == -1

    def sortBy(self, attr):
        """Override Qt method."""
        self.__sort_by = attr
        self.invalidate()
        self.sort(0, Qt.AscendingOrder)

    def lessThan(self, left, right):
        """Override Qt method."""
        left_item = self.sourceModel().itemFromIndex(left)
        right_item = self.sourceModel().itemFromIndex(right)

        # Check for attribute, otherwise, check for data
        if hasattr(left_item, self.__sort_by):
            left_data = getattr(left_item, self.__sort_by)
            right_data = getattr(right_item, self.__sort_by)
            return left_data < right_data


# --- Widgets
# ----------------------------------------------------------------------------
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

    # --- Helper methods
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

    # --- API
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

    # --- Qt overrides
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

    # --- Helper methods: Lineedit widget
    def search_text(self):
        """Get the normalized (lowecase) content of the search text."""
        return to_text_string(self.edit.text()).lower()

    def set_search_text(self, string):
        """Set the content of the search text."""
        self.edit.setText(string)

    # --- Helper methods: List widget
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


def create_vcs_example_switcher(sw):
    """Add example data for vcs."""
    sw.clear()
    sw.set_placeholder_text('Select a ref to Checkout')
    sw.add_item(title='Create New Branch', action_item=True,
                icon=ima.icon('MessageBoxInformation'))
    sw.add_item(title='master', description='123123')
    sw.add_item(title='develop', description='1231232a')
    sw.add_item(title=u'test-试', description='1231232ab')
    sw.add_separator()
    sw.add_item(title='other', description='q2211231232a')


def create_options_example_switcher(sw):
    """Add example actions."""
    sw.clear()
    sw.set_placeholder_text('Select Action')
    section = _('change view')
    sw.add_item(title=_('Indent Using Spaces'), description='Test',
                section=section, shortcut='Ctrl+I')
    sw.add_item(title=_('Indent Using Tabs'), description='Test',
                section=section)
    sw.add_item(title=_('Detect Indentation from Content'), section=section)
    sw.add_separator()
    section = _('convert file')
    sw.add_item(title=_('Convert Indentation to Spaces'), description='Test',
                section=section)
    sw.add_item(title=_('Convert Indentation to Tabs'), section=section)
    sw.add_item(title=_('Trim Trailing Whitespace'), section=section)


def create_help_example_switcher(sw):
    """Add help data."""
    sw.clear()
    sw.add_item(title=_('Help me!'), section='1')
    sw.add_separator()
    sw.add_item(title=_('Help me 2!'), section='2')
    sw.add_separator()
    sw.add_item(title=_('Help me 3!'), section='3')


def create_line_example_switcher(sw):
    """Add current line example."""
    sw.clear()
    sw.add_item(title=_('Current line, type something'), action_item=True)


def create_symbol_example_switcher(sw):
    """Add symbol data example."""
    sw.clear()
    sw.add_item(title=_('Some symbol'))
    sw.add_item(title=_('another symbol'))


def create_example_switcher(main=None):
    """Create example switcher."""
    # Create Switcher
    if main is None:
        main = QLineEdit()
    sw = Switcher(main)
    sw.add_mode('>', _('Commands'))
    sw.add_mode('?', _('Help'))
    sw.add_mode(':', _('Go to Line'))
    sw.add_mode('@', _('Go to Symbol in File'))

    def handle_modes(mode):
        if mode == '>':
            create_options_example_switcher(sw)
        elif mode == '?':
            create_help_example_switcher(sw)
        elif mode == ':':
            create_line_example_switcher(sw)
        elif mode == '@':
            create_symbol_example_switcher(sw)
        elif mode == '':
            create_vcs_example_switcher(sw)

    def item_selected(item, mode, search_text):
        print([item, mode, search_text])  # spyder: test-skip
        print([item.get_title(), mode, search_text])  # spyder: test-skip

    sw.sig_mode_selected.connect(handle_modes)
    sw.sig_item_selected.connect(item_selected)

    create_vcs_example_switcher(sw)
    sw.show()


def test(main=None):  # pragma: no cover
    """Launch the switcher with some test values."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    create_example_switcher(main=main)
    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    test()

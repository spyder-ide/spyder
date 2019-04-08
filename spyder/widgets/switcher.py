# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from __future__ import print_function
from collections import namedtuple, OrderedDict
import os
import os.path as osp
import re
import sys

# Third party imports
from qtpy.QtCore import (Signal, Slot, QEvent, QFileInfo, QObject, QRegExp,
                         QSize, Qt, QSortFilterProxyModel)
from qtpy.QtGui import (QIcon, QRegExpValidator, QTextCursor, QStandardItem,
                        QStandardItemModel)
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QVBoxLayout,
                            QMainWindow, QListView)

# Local imports
from spyder.config.base import _
from spyder.py3compat import iteritems, TEXT_TYPES, to_text_string
from spyder.config.utils import is_ubuntu
from spyder.utils import icon_manager as ima
from spyder.utils.stringmatching import get_search_scores
from spyder.widgets.helperwidgets import HelperToolButton, HTMLDelegate
from spyder.config.main import CONF


class KeyPressFilter(QObject):
    """Use with `installEventFilter` to get up/down arrow key press signal."""

    sig_up_key_pressed = Signal()
    sig_down_key_pressed = Signal()
    sig_enter_key_pressed = Signal()

    def eventFilter(self, src, e):
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


class SwitcherBaseItem(QStandardItem):
    """"""
    _WIDTH = 400
    _HEIGHT = None
    _STYLES = None
    _TEMPLATE = None

    def __init__(self, parent=None):
        """"""
        super(SwitcherBaseItem, self).__init__()

        # Style
        self._width = self._WIDTH
        self._height = self._HEIGHT
        self._action_item = False
        self._score = -1

        # Setup
        self.setSizeHint(QSize(0, self._HEIGHT))

    def _render_text(self):
        """"""
        raise NotImplementedError

    def _set_rendered_text(self):
        """"""
        self.setText(self._render_text())

    # --- API
    def set_width(self, value):
        """"""
        self._width = value
        self._set_rendered_text()

    def get_width(self):
        """"""
        return self._width

    def set_score(self, value):
        """"""
        self._score = value
        self._set_rendered_text()

    def is_action_item(self):
        """"""
        return bool(self._action_item)

    # --- Qt overrides
    def refresh(self):
        """"""
        super(SwitcherBaseItem, self).refresh()
        self._set_styles()
        self._set_rendered_text()


class SwitcherSeparatorItem(SwitcherBaseItem):
    """
    Based on HTML delegate.

    See: https://doc.qt.io/qt-5/richtext-html-subset.html
    """

    _SEPARATOR = '_'
    _HEIGHT = 15
    _STYLES = {
        'color': 'black',
        'font_size': CONF.get('appearance', 'rich_font/size', 10),
    }
    _TEMPLATE = \
        '''<table cellpadding="5" cellspacing="0" width="{width}"
            height="{height}" border="0">
  <tr><td valign="top" align="center"><hr></td></tr>
</table>'''

    def __init__(self, parent=None):
        """"""
        super(SwitcherSeparatorItem, self).__init__()
        self.setFlags(Qt.NoItemFlags)
        self._set_rendered_text()

    # --- Helpers
    @classmethod
    def _set_styles(self, cls):
        """Build the text that will appear on the list widget."""
        rich_font = CONF.get('appearance', 'rich_font/size', 10)

        if sys.platform == 'darwin':
            font_size = rich_font
        elif os.name == 'nt':
            font_size = rich_font
        elif is_ubuntu():
            font_size = rich_font - 2
        else:
            font_size = rich_font - 2

        cls._STYLES['font_size'] = font_size
        cls._STYLES['color'] = ima.MAIN_FG_COLOR

    def _render_text(self):
        """"""
        width = self._width
        height = self._HEIGHT
        text = self._TEMPLATE.format(width=width - 10, height=height,
                                     **self._STYLES)
        return text


class SwitcherItem(SwitcherBaseItem):
    """
    Based on HTML delegate.

    See: https://doc.qt.io/qt-5/richtext-html-subset.html
    """
    _FONT_SIZE = CONF.get('appearance', 'rich_font/size', 10)
    _HEIGHT = 20
    _PADDING = 5
    _STYLES = {
        'title_color': 'black',
        'description_color': 'rgb(153, 153, 153)',
        'section_color': 'blue',
        'shortcut_color': 'rgb(153, 153, 153)',
        'title_font_size': _FONT_SIZE,
        'description_font_size': _FONT_SIZE,
        'section_font_size': _FONT_SIZE,
        'shortcut_font_size': _FONT_SIZE,
    }
    _TEMPLATE = '''<table width="{width}" height="{height}"
                    cellpadding="{padding}">
  <tr>
    <td valign="bottom">
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
                 action_item=False):
        """"""
        super(SwitcherItem, self).__init__()

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

        self._set_styles()
        self._set_rendered_text()

    # --- Helpers
    def _render_text(self, title=None, description=None, section=None):
        """"""
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
        width = self._width - padding * 2
        height = self._HEIGHT
        shortcut = '&lt;' + self._shortcut + '&gt;' if self._shortcut else ''
        text = self._TEMPLATE.format(width=width, height=height, title=title,
                                     section=section, description=description,
                                     padding=padding, shortcut=shortcut,
                                     **self._STYLES)
        return text

    def _set_rendered_text(self):
        """"""
        self.setText(self._render_text())

    @classmethod
    def _set_styles(cls):
        """Build the text that will appear on the list widget."""
        rich_font = CONF.get('appearance', 'rich_font/size', 10)
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

        cls._STYLES['title_font_size'] = title_font_size
        cls._STYLES['description_font_size'] = description_font_size
        cls._STYLES['section_font_size'] = description_font_size
        cls._STYLES['title_color'] = 'black'
        # cls._STYLES['description_color'] = 'black'
        # cls._STYLES['section_color'] = 'black'

    # --- API
    def set_icon(self, value):
        """"""
        self._icon = icon
        self.setIcon(icon)

    def get_icon(self):
        """"""
        return self._icon

    def set_title(self, value):
        """"""
        self._title = value
        self._set_rendered_text()

    def get_title(self):
        """"""
        return self._title

    def set_rich_title(self, value):
        """"""
        self._rich_title = value
        self._set_rendered_text()

    def get_rich_title(self):
        """"""
        return self._rich_title

    def set_description(self, value):
        """"""
        self._description = value
        self._set_rendered_text()

    def get_description(self):
        """"""
        return self._description

    def set_shortcut(self, value):
        """"""
        self._shortcut = value
        self._set_rendered_text()

    def get_shortcut(self, value):
        """"""
        return self._shortcut

    def set_tooltip(self, value):
        """"""
        super(SwitcherItem, self).setTooltip(value)

    def set_data(self, value):
        """"""
        self._data = value

    def get_data(self):
        """"""
        return self._data

    def get_score(self):
        """"""
        return self._score

    def set_section(self, value):
        """"""
        self._section = value
        self._set_rendered_text()

    def get_section(self):
        """"""
        return self._section

    def set_section_visible(self, value):
        """"""
        self._section_visible = value
        self._set_rendered_text()

    def set_action_item(self, value):
        """"""
        self._action_item = value
        self._set_rendered_text()


class SwitcherProxyModel(QSortFilterProxyModel):
    """"""

    def __init__(self, parent=None):
        """"""
        super(SwitcherProxyModel, self).__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def sortBy(self, attr):
        """"""
        self.__sort_by = attr
        self.invalidate()
        self.sort(0, Qt.DescendingOrder)

    def lessThan(self, left, right):
        """"""
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
    """A multi purpose switcher."""

    sig_text_changed = Signal(TEXT_TYPES[-1])  # Search/Filter text changes
    sig_item_selected = Signal(object)  # List item sleected with click/enter
    sig_mode_selected = Signal(TEXT_TYPES[-1])

    _MIN_WIDTH = 500

    def __init__(self, parent, help_text=None):
        super(Switcher, self).__init__(parent)
        self._visible_rows = 0
        self._modes = {}
        self._mode_on = ''

        # Widgets
        self.edit = QLineEdit(self)
        self.list = QListView(self)
        self.model = QStandardItemModel(self.list)
        self.proxy = SwitcherProxyModel(self.list)
        self.filter = KeyPressFilter()

        # Widgets setup
        # self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setWindowOpacity(0.95)
        self.edit.installEventFilter(self.filter)
        self.edit.setPlaceholderText(help_text if help_text else '')
        self.list.setMinimumWidth(self._MIN_WIDTH)
        self.list.setItemDelegate(HTMLDelegate(self))
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setSelectionBehavior(self.list.SelectRows)
        self.list.setSelectionMode(self.list.SingleSelection)
        self.proxy.setSourceModel(self.model)
        self.list.setModel(self.proxy)

        # Layout
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(self.edit)
        layout = QVBoxLayout()
        layout.addLayout(edit_layout)
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

    # --- Helper methods
    def _add_item(self, item):
        """"""
        item.set_width(self._MIN_WIDTH)
        self.model.appendRow(item)
        self.set_current_row(0)
        self._visible_rows = self.model.rowCount()
        self.setup_sections()

    # --- API
    def clear(self):
        """"""
        self.set_placeholder_text('')
        self.model.beginResetModel()
        self.model.clear()
        self.model.endResetModel()

    def set_placeholder_text(self, text):
        """"""
        self.edit.setPlaceholderText(text)

    def add_mode(self, token, description):
        """"""
        self._modes[token] = description

    def add_item(self, icon=None, title=None, description=None, shortcut=None,
                 section=None, data=None, tool_tip=None, action_item=False):
        """"""
        # TODO: Add caching
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
        )
        item.set_width(self._MIN_WIDTH)
        self._add_item(item)

    def add_separator(self):
        """"""
        item = SwitcherSeparatorItem(parent=self.list)
        self._add_item(item)

    def setup(self):
        """Setup list widget content."""
        # Check exited mode
        mode = self._mode_on
        if mode:
            search_text = self.search_text()[len(mode):]
        else:
            search_text = self.search_text()

        if mode and self.search_text() == '':
            self._mode_on = ''
            self.sig_mode_selected.emit(self._mode_on)

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

        scores = get_search_scores(search_text, titles, template="<b>{0}</b>")

        self._visible_rows = self.model.rowCount()
        for idx, score in enumerate(scores):
            title, rich_title, score_value = score
            item = self.model.item(idx)

            if not self._is_separator(item):
                item.set_rich_title(rich_title)

            item.set_score(score_value)
            proxy_index = self.proxy.mapFromSource(self.model.index(idx, 0))

            if not item.is_action_item():
                self.list.setRowHidden(proxy_index.row(), score_value == -1)

                if score_value == -1:
                    self._visible_rows -= 1

        self.set_current_row(0)
        self.setup_sections()
        self.proxy.sortBy('_score')

    def setup_sections(self):
        """"""
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
            self.sig_item_selected.emit(item)
        self.accept()

    def accept(self):
        """Override Qt method."""
        self.clear()
        super(Switcher, self).accept()

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
        """"""
        return isinstance(item, SwitcherSeparatorItem)

    def _select_row(self, steps):
        """Select row in list widget based on a number of steps with direction.

        Steps can be positive (next rows) or negative (previous rows).
        """
        row = self.current_row() + steps
        if 0 <= row < self.count():
            self.set_current_row(row)

    def count(self):
        """Gets the item count in the list widget."""
        return self._visible_rows

    def current_row(self):
        """Returns the current selected row in the list widget."""
        return self.list.currentIndex().row()

    def set_current_row(self, row):
        """Sets the current selected row in the list widget."""
        index = self.model.index(row, 0)
        selection_model = self.list.selectionModel()

        # https://doc.qt.io/qt-5/qitemselectionmodel.html#SelectionFlag-enum
        selection_model.setCurrentIndex(index, selection_model.ClearAndSelect)

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
                    steps +=  1
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
    sw.clear()
    sw.set_placeholder_text('Select a ref to Checkout')
    sw.add_item(title='Create New Branch', action_item=True,
                icon=ima.icon('MessageBoxInformation'))
    sw.add_item(title='master', description='123123')
    sw.add_item(title='develop', description='1231232a')
    sw.add_separator()
    sw.add_item(title='other', description='q2211231232a')


def create_options_example_switcher(sw):
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


def test():  # pragma: no cover
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    w = QLineEdit()

    # Create Switcher
    sw = Switcher(w)
    sw.add_mode('>', 'Commands')

    def handle_modes(mode):
        if mode == '>':
            create_options_example_switcher(sw)
        elif mode == '':
            create_vcs_example_switcher(sw)

    def print_item_selected(item):
        print([item.get_title()])

    sw.sig_mode_selected.connect(handle_modes)
    sw.sig_item_selected.connect(print_item_selected)

    create_vcs_example_switcher(sw)
    sw.show()

    app.exec_()


if __name__ == "__main__":  # pragma: no cover
    test()

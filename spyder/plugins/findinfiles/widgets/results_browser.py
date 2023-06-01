# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Results browser."""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import QPoint, QSize, Qt, Signal, Slot
from qtpy.QtGui import (QAbstractTextDocumentLayout, QColor, QFontMetrics,
                        QTextDocument)
from qtpy.QtWidgets import (QApplication, QStyle, QStyledItemDelegate,
                            QStyleOptionViewItem, QTreeWidgetItem)

# Local imports
from spyder.api.translations import _
from spyder.config.gui import get_font
from spyder.plugins.findinfiles.widgets.search_thread import (
    ELLIPSIS, MAX_RESULT_LENGTH)
from spyder.utils import icon_manager as ima
from spyder.utils.palette import QStylePalette
from spyder.widgets.onecolumntree import OneColumnTree


# ---- Constants
# ----------------------------------------------------------------------------
ON = 'on'
OFF = 'off'


# ---- Items
# ----------------------------------------------------------------------------
class LineMatchItem(QTreeWidgetItem):

    def __init__(self, parent, lineno, colno, match, font, text_color):
        self.lineno = lineno
        self.colno = colno
        self.match = match['formatted_text']
        self.plain_match = match['text']
        self.text_color = text_color
        self.font = font
        super().__init__(parent, [self.__repr__()], QTreeWidgetItem.Type)

    def __repr__(self):
        match = str(self.match).rstrip()
        _str = (
            f"<!-- LineMatchItem -->"
            f"<p style=\"color:'{self.text_color}';\">"
            f'&nbsp;&nbsp;'
            f"<b>{self.lineno}</b> ({self.colno}): "
            f"<span style='font-family:{self.font.family()};"
            f"font-size:{self.font.pointSize()}pt;'>{match}</span></p>"
        )
        return _str

    def __unicode__(self):
        return self.__repr__()

    def __str__(self):
        return self.__repr__()

    def __lt__(self, x):
        return self.lineno < x.lineno

    def __ge__(self, x):
        return self.lineno >= x.lineno


class FileMatchItem(QTreeWidgetItem):

    def __init__(self, parent, path, filename, sorting, text_color):

        self.sorting = sorting
        self.filename = osp.basename(filename)

        # Get relative dirname according to the path we're searching in.
        dirname = osp.dirname(filename)

        # Catch errors when it's not possible to get the relative directory
        # name. This happens when the user is searching in a single file.
        # Fixes spyder-ide/spyder#17443 and spyder-ide/spyder#20964
        try:
            rel_dirname = dirname.split(path)[1]
            if rel_dirname.startswith(osp.sep):
                rel_dirname = rel_dirname[1:]
        except IndexError:
            rel_dirname = dirname

        self.rel_dirname = rel_dirname

        title = (
            f'<!-- FileMatchItem -->'
            f'<b style="color:{text_color}">{osp.basename(filename)}</b>'
            f'&nbsp;&nbsp;&nbsp;'
            f'<span style="color:{text_color}">'
            f'<em>{self.rel_dirname}</em>'
            f'</span>'
        )

        super().__init__(parent, [title], QTreeWidgetItem.Type)

        self.setIcon(0, ima.get_icon_by_extension_or_type(filename, 1.0))
        self.setToolTip(0, filename)

    def __lt__(self, x):
        if self.sorting['status'] == ON:
            return self.filename < x.filename
        else:
            return False

    def __ge__(self, x):
        if self.sorting['status'] == ON:
            return self.filename >= x.filename
        else:
            return False


# ---- Browser
# ----------------------------------------------------------------------------
class ItemDelegate(QStyledItemDelegate):

    def __init__(self, parent):
        super().__init__(parent)
        self._margin = None
        self._background_color = QColor(QStylePalette.COLOR_BACKGROUND_3)
        self.width = 0

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        # Set background color for selected and hovered items.
        # Inspired by:
        # - https://stackoverflow.com/a/43253004/438386
        # - https://stackoverflow.com/a/27274233/438386

        # This is commented for now until we find a way to correctly colorize
        # the entire line with a single color.
        # if options.state & QStyle.State_Selected:
        #     # This only applies when the selected item doesn't have focus
        #     if not (options.state & QStyle.State_HasFocus):
        #         options.palette.setBrush(
        #             QPalette.Highlight,
        #             QBrush(self._background_color)
        #         )

        if options.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, self._background_color)

        # Set text
        doc = QTextDocument()
        text = options.text
        doc.setHtml(text)
        doc.setDocumentMargin(0)

        # This needs to be an empty string to avoid overlapping the
        # normal text of the QTreeWidgetItem
        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText,
                                        options, None)
        painter.save()

        painter.translate(textRect.topLeft() + QPoint(0, 4))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        size = QSize(self.width, int(doc.size().height()))
        return size


class ResultsBrowser(OneColumnTree):
    sig_edit_goto_requested = Signal(str, int, str, int, int)
    sig_max_results_reached = Signal()

    def __init__(self, parent, text_color, max_results=1000):
        super().__init__(parent)
        self.search_text = None
        self.results = None
        self.max_results = max_results
        self.total_matches = None
        self.error_flag = None
        self.completed = None
        self.sorting = {}
        self.font = get_font()
        self.data = None
        self.files = None
        self.root_items = None
        self.text_color = text_color
        self.path = None
        self.longest_file_item = ''
        self.longest_line_item = ''

        # Setup
        self.set_title('')
        self.set_sorting(OFF)
        self.setSortingEnabled(False)
        self.setItemDelegate(ItemDelegate(self))
        self.setUniformRowHeights(True)  # Needed for performance
        self.sortByColumn(0, Qt.AscendingOrder)

        # Only show the actions for collaps/expand all entries in the widget
        # For further information see spyder-ide/spyder#13178
        self.common_actions = self.common_actions[:2]

        # Signals
        self.header().sectionClicked.connect(self.sort_section)

    def activated(self, item):
        """Double-click event."""
        itemdata = self.data.get(id(self.currentItem()))
        if itemdata is not None:
            filename, lineno, colno, colend = itemdata
            self.sig_edit_goto_requested.emit(
                filename, lineno, self.search_text, colno, colend - colno)

    def set_sorting(self, flag):
        """Enable result sorting after search is complete."""
        self.sorting['status'] = flag
        self.header().setSectionsClickable(flag == ON)

    @Slot(int)
    def sort_section(self, idx):
        self.setSortingEnabled(True)

    def clicked(self, item):
        """Click event."""
        if isinstance(item, FileMatchItem):
            if item.isExpanded():
                self.collapseItem(item)
            else:
                self.expandItem(item)
        else:
            self.activated(item)

    def clear_title(self, search_text):
        self.font = get_font()
        self.clear()
        self.setSortingEnabled(False)
        self.num_files = 0
        self.data = {}
        self.files = {}
        self.set_sorting(OFF)
        self.search_text = search_text
        title = "'%s' - " % search_text
        text = _('String not found')
        self.set_title(title + text)

    @Slot(object)
    def append_file_result(self, filename):
        """Real-time update of file items."""
        if len(self.data) < self.max_results:
            item = FileMatchItem(
                self,
                self.path,
                filename,
                self.sorting,
                self.text_color
            )

            self.files[filename] = item

            item.setExpanded(True)
            self.num_files += 1

            item_text = osp.join(item.rel_dirname, item.filename)
            if len(item_text) > len(self.longest_file_item):
                self.longest_file_item = item_text

    @Slot(object, object)
    def append_result(self, items, title):
        """Real-time update of line items."""
        if len(self.data) >= self.max_results:
            self.set_title(_('Maximum number of results reached! Try '
                             'narrowing the search.'))
            self.sig_max_results_reached.emit()
            return

        available = self.max_results - len(self.data)
        if available < len(items):
            items = items[:available]

        self.setUpdatesEnabled(False)
        self.set_title(title)
        for item in items:
            filename, lineno, colno, line, match_end = item
            file_item = self.files.get(filename, None)
            if file_item:
                item = LineMatchItem(file_item, lineno, colno, line,
                                     self.font, self.text_color)
                self.data[id(item)] = (filename, lineno, colno, match_end)

                if len(item.plain_match) > len(self.longest_line_item):
                    self.longest_line_item = item.plain_match

        self.setUpdatesEnabled(True)

    def set_max_results(self, value):
        """Set maximum amount of results to add."""
        self.max_results = value

    def set_path(self, path):
        """Set path where the search is performed."""
        self.path = path

    def set_width(self):
        """Set widget width according to its longest item."""
        # File item width
        file_item_size = self.fontMetrics().size(
            Qt.TextSingleLine,
            self.longest_file_item
        )
        file_item_width = file_item_size.width()

        # Line item width
        metrics = QFontMetrics(self.font)
        line_item_chars = len(self.longest_line_item)
        if line_item_chars >= MAX_RESULT_LENGTH:
            line_item_chars = MAX_RESULT_LENGTH + len(ELLIPSIS) + 1
        line_item_width = line_item_chars * metrics.width('W')

        # Select width
        if file_item_width > line_item_width:
            width = file_item_width
        else:
            width = line_item_width

        # Increase width a bit to not be too near to the edge
        self.itemDelegate().width = width + 10

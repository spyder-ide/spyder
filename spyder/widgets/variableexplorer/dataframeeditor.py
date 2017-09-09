# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the New BSD License
#
# DataFrameModel is based on the class ArrayModel from array editor
# and the class DataFrameModel from the pandas project.
# Present in pandas.sandbox.qtpandas in v0.13.1
# Copyright (c) 2011-2012, Lambda Foundry, Inc.
# and PyData Development Team All rights reserved

"""
Pandas DataFrame Editor Dialog
"""
import time
# Third party imports
from qtpy import API
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt, Signal, Slot,
                         QItemSelectionModel, QEvent)
from qtpy.QtGui import QColor, QCursor
from qtpy.QtWidgets import (QApplication, QCheckBox, QDialogButtonBox, QDialog,
                            QGridLayout, QHBoxLayout, QInputDialog, QLineEdit,
                            QMenu, QMessageBox, QPushButton, QTableView,
                            QHeaderView, QScrollBar, QTableWidget, QFrame,
                            QItemDelegate)

from pandas import DataFrame, DatetimeIndex, Series
import numpy as np

# Local imports
from spyder.config.base import _
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.config.gui import get_font, config_shortcut
from spyder.py3compat import (io, is_text_string, PY2, to_text_string,
                              TEXT_TYPES)
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    keybinding, qapplication)
from spyder.widgets.variableexplorer.arrayeditor import get_idx_rect

# Supported Numbers and complex numbers
REAL_NUMBER_TYPES = (float, int, np.int64, np.int32)
COMPLEX_NUMBER_TYPES = (complex, np.complex64, np.complex128)
# Used to convert bool intrance to false since bool('False') will return True
_bool_false = ['false', '0']

# Default format for data frames with floats
DEFAULT_FORMAT = '%.3g'

# Limit at which dataframe is considered so large that it is loaded on demand
LARGE_SIZE = 5e5
LARGE_NROWS = 1e5
LARGE_COLS = 60
ROWS_TO_LOAD = 500
COLS_TO_LOAD = 40

# Background colours
BACKGROUND_NUMBER_MINHUE = 0.66 # hue for largest number
BACKGROUND_NUMBER_HUERANGE = 0.33 # (hue for smallest) minus (hue for largest)
BACKGROUND_NUMBER_SATURATION = 0.7
BACKGROUND_NUMBER_VALUE = 1.0
BACKGROUND_NUMBER_ALPHA = 0.6 
BACKGROUND_NONNUMBER_COLOR = Qt.lightGray
BACKGROUND_INDEX_ALPHA = 0.8
BACKGROUND_STRING_ALPHA = 0.05
BACKGROUND_MISC_ALPHA = 0.3


def bool_false_check(value):
    """
    Used to convert bool intrance to false.

    Needed since any string in bool('') will return True.
    """
    if value.lower() in _bool_false:
        value = ''
    return value


def global_max(col_vals, index):
    """Returns the global maximum and minimum."""
    col_vals_without_None = [x for x in col_vals if x is not None]
    max_col, min_col = zip(*col_vals_without_None)
    return max(max_col), min(min_col)


class DataFrameModel(QAbstractTableModel):
    """ DataFrame Table Model.

    Partly based in ExtDataModel and ExtFrameModel classes
    of the gtabview project.

    For more information please see:
    https://github.com/wavexx/gtabview/blob/master/gtabview/models.py
    """
    
    ROWS_TO_LOAD = 500
    COLS_TO_LOAD = 40

    def __init__(self, dataFrame, format=DEFAULT_FORMAT, parent=None):
        QAbstractTableModel.__init__(self)
        self.dialog = parent
        self.df = dataFrame
        self.df_index = dataFrame.index.tolist()
        self.df_header = dataFrame.columns.tolist()
        self._format = format
        self.complex_intran = None
        
        self.total_rows = self.df.shape[0]
        self.total_cols = self.df.shape[1]
        size = self.total_rows * self.total_cols

        self.max_min_col = None
        if size < LARGE_SIZE:
            self.max_min_col_update()
            self.colum_avg_enabled = True
            self.bgcolor_enabled = True
            self.colum_avg(1)
        else:
            self.colum_avg_enabled = False
            self.bgcolor_enabled = False
            self.colum_avg(0)

        # Use paging when the total size, number of rows or number of
        # columns is too large
        if size > LARGE_SIZE:
            self.rows_loaded = self.ROWS_TO_LOAD
            self.cols_loaded = self.COLS_TO_LOAD
        else:
            if self.total_rows > LARGE_NROWS:
                self.rows_loaded = self.ROWS_TO_LOAD
            else:
                self.rows_loaded = self.total_rows
            if self.total_cols > LARGE_COLS:
                self.cols_loaded = self.COLS_TO_LOAD
            else:
                self.cols_loaded = self.total_cols

    def _axis(self, axis):
        return self.df.columns if axis == 0 else self.df.index

    def _axis_levels(self, axis):
        ax = self._axis(axis)
        return 1 if not hasattr(ax, 'levels') \
            else len(ax.levels)

    @property
    def shape(self):
        return self.df.shape

    @property
    def header_shape(self):
        return (self._axis_levels(0), self._axis_levels(1))

    @property
    def chunk_size(self):
        return max(*self.shape())

    def header(self, axis, x, level=0):
        ax = self._axis(axis)
        return ax.values[x] if not hasattr(ax, 'levels') \
            else ax.values[x][level]

    def name(self, axis, level):
        ax = self._axis(axis)
        if hasattr(ax, 'levels'):
            return ax.names[level]
        if ax.name:
            return ax.name
        return ''

    def max_min_col_update(self):
        """
        Determines the maximum and minimum number in each column.

        The result is a list whose k-th entry is [vmax, vmin], where vmax and
        vmin denote the maximum and minimum of the k-th column (ignoring NaN). 
        This list is stored in self.max_min_col.

        If the k-th column has a non-numerical dtype, then the k-th entry
        is set to None. If the dtype is complex, then compute the maximum and
        minimum of the absolute values. If vmax equals vmin, then vmin is 
        decreased by one.
        """
        if self.df.shape[0] == 0: # If no rows to compute max/min then return
            return
        self.max_min_col = []
        for dummy, col in self.df.iteritems():
            if col.dtype in REAL_NUMBER_TYPES + COMPLEX_NUMBER_TYPES:
                if col.dtype in REAL_NUMBER_TYPES:
                    vmax = col.max(skipna=True)
                    vmin = col.min(skipna=True)
                else:
                    vmax = col.abs().max(skipna=True)
                    vmin = col.abs().min(skipna=True)
                if vmax != vmin:
                    max_min = [vmax, vmin]
                else:
                    max_min = [vmax, vmin - 1]
            else:
                max_min = None
            self.max_min_col.append(max_min)

    def get_format(self):
        """Return current format"""
        # Avoid accessing the private attribute _format from outside
        return self._format

    def set_format(self, format):
        """Change display format"""
        self._format = format
        self.reset()

    def bgcolor(self, state):
        """Toggle backgroundcolor"""
        self.bgcolor_enabled = state > 0
        self.reset()

    def colum_avg(self, state):
        """Toggle backgroundcolor"""
        self.colum_avg_enabled = state > 0
        if self.colum_avg_enabled:
            self.return_max = lambda col_vals, index: col_vals[index]
        else:
            self.return_max = global_max
        self.reset()

    def get_bgcolor(self, index):
        """Background color depending on value."""
        column = index.column()
        if not self.bgcolor_enabled:
            return
        value = self.get_value(index.row(), column)
        if self.max_min_col[column] is None:
            color = QColor(BACKGROUND_NONNUMBER_COLOR)
            if is_text_string(value):
                color.setAlphaF(BACKGROUND_STRING_ALPHA)
            else:
                color.setAlphaF(BACKGROUND_MISC_ALPHA)
        else:
            if isinstance(value, COMPLEX_NUMBER_TYPES):
                color_func = abs
            else:
                color_func = float
            vmax, vmin = self.return_max(self.max_min_col, column)
            hue = (BACKGROUND_NUMBER_MINHUE + BACKGROUND_NUMBER_HUERANGE *
                   (vmax - color_func(value)) / (vmax - vmin))
            hue = float(abs(hue))
            if hue > 1:
                hue = 1
            color = QColor.fromHsvF(hue, BACKGROUND_NUMBER_SATURATION,
                                    BACKGROUND_NUMBER_VALUE,
                                    BACKGROUND_NUMBER_ALPHA)
        return color

    def get_value(self, row, column):
        """Return the value of the DataFrame."""
        # To increase the performance iat is used but that requires error
        # handling, so fallback uses iloc
        try:
            value = self.df.iat[row, column]
        except:
            try:
                value = self.df.iloc[row, column]
            except IndexError:
                value = None
        return value

    def update_df_index(self):
        """"Update the DataFrame index"""
        self.df_index = self.df.index.tolist()

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            column = index.column()
            row = index.row()
            value = self.get_value(row, column)
            if isinstance(value, float):
                try:
                    return to_qvariant(self._format % value)
                except (ValueError, TypeError):
                    # may happen if format = '%d' and value = NaN;
                    # see issue 4139
                    return to_qvariant(DEFAULT_FORMAT % value)
            else:
                try:
                    return to_qvariant(to_text_string(value))
                except UnicodeDecodeError:
                    return to_qvariant(encoding.to_unicode(value))
        elif role == Qt.BackgroundColorRole:
            return to_qvariant(self.get_bgcolor(index))
        elif role == Qt.FontRole:
            return to_qvariant(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
        return to_qvariant()

    def sort(self, column, order=Qt.AscendingOrder):
        """Overriding sort method"""
        if self.complex_intran is not None:
            if self.complex_intran.any(axis=0).iloc[column]:
                QMessageBox.critical(self.dialog, "Error",
                                     "TypeError error: no ordering "
                                     "relation is defined for complex numbers")
                return False
        try:
            ascending = order == Qt.AscendingOrder
            if column >= 0:
                try:
                    self.df.sort_values(by=self.df.columns[column],
                                        ascending=ascending, inplace=True,
                                        kind='mergesort')
                except AttributeError:
                    # for pandas version < 0.17
                    self.df.sort(columns=self.df.columns[column],
                                 ascending=ascending, inplace=True,
                                 kind='mergesort')
                self.update_df_index()
            else:
                # To sort by index
                self.df.sort_index(inplace=True, ascending=ascending)
                self.update_df_index()
        except TypeError as e:
            QMessageBox.critical(self.dialog, "Error",
                                 "TypeError error: %s" % str(e))
            return False

        self.reset()
        return True

    def flags(self, index):
        """Set flags"""
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index) |
                            Qt.ItemIsEditable)

    def setData(self, index, value, role=Qt.EditRole, change_type=None):
        """Cell content change"""
        column = index.column()
        row = index.row()

        if change_type is not None:
            try:
                value = self.data(index, role=Qt.DisplayRole)
                val = from_qvariant(value, str)
                if change_type is bool:
                    val = bool_false_check(val)
                self.df.iloc[row, column] = change_type(val)
            except ValueError:
                self.df.iloc[row, column] = change_type('0')
        else:
            val = from_qvariant(value, str)
            current_value = self.get_value(row, column)
            if isinstance(current_value, bool):
                val = bool_false_check(val)
            supported_types = (bool,) + REAL_NUMBER_TYPES + COMPLEX_NUMBER_TYPES
            if (isinstance(current_value, supported_types) or 
                    is_text_string(current_value)):
                try:
                    self.df.iloc[row, column] = current_value.__class__(val)
                except ValueError as e:
                    QMessageBox.critical(self.dialog, "Error",
                                         "Value error: %s" % str(e))
                    return False
            else:
                QMessageBox.critical(self.dialog, "Error",
                                     "The type of the cell is not a supported "
                                     "type")
                return False
        self.max_min_col_update()
        return True

    def get_data(self):
        """Return data"""
        return self.df

    def rowCount(self, index=QModelIndex()):
        """DataFrame row number"""
        if self.total_rows <= self.rows_loaded:
            return self.total_rows
        else:
            return self.rows_loaded

    def can_fetch_more(self, rows=False, columns=False):
        if rows:
            if self.total_rows > self.rows_loaded:
                return True
            else:
                return False
        if columns:
            if self.total_cols > self.cols_loaded:
                return True
            else:
                return False

    def fetch_more(self, rows=False, columns=False):
        if self.can_fetch_more(rows=rows):
            reminder = self.total_rows - self.rows_loaded
            items_to_fetch = min(reminder, self.ROWS_TO_LOAD)
            self.beginInsertRows(QModelIndex(), self.rows_loaded,
                                 self.rows_loaded + items_to_fetch - 1)
            self.rows_loaded += items_to_fetch
            self.endInsertRows()
        if self.can_fetch_more(columns=columns):
            reminder = self.total_cols - self.cols_loaded
            items_to_fetch = min(reminder, self.COLS_TO_LOAD)
            self.beginInsertColumns(QModelIndex(), self.cols_loaded,
                                    self.cols_loaded + items_to_fetch - 1)
            self.cols_loaded += items_to_fetch
            self.endInsertColumns()

    def columnCount(self, index=QModelIndex()):
        """DataFrame column number"""
        # This is done to implement series
        if len(self.df.shape) == 1:
            return 2
        elif self.total_cols <= self.cols_loaded:
            return self.total_cols
        else:
            return self.cols_loaded

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class FrozenTableView(QTableView):
    """This class implements a table with its first column frozen
    For more information please see:
    http://doc.qt.io/qt-5/qtwidgets-itemviews-frozencolumn-example.html"""
    def __init__(self, parent):
        """Constructor."""
        QTableView.__init__(self, parent)
        self.parent = parent
        self.setModel(parent.model())
        self.setFocusPolicy(Qt.NoFocus)
        self.verticalHeader().hide()
        try:
            self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        except:  # support for qtpy<1.2.0
            self.horizontalHeader().setResizeMode(QHeaderView.Fixed)

        parent.viewport().stackUnder(self)

        self.setSelectionModel(parent.selectionModel())
        for col in range(1, parent.model().columnCount()):
            self.setColumnHidden(col, True)

        self.setColumnWidth(0, parent.columnWidth(0))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.show()

        self.setVerticalScrollMode(1)

    def update_geometry(self):
        """Update the frozen column size when an update occurs
        in its parent table"""
        self.setGeometry(self.parent.verticalHeader().width() +
                         self.parent.frameWidth(),
                         self.parent.frameWidth(),
                         self.parent.columnWidth(0),
                         self.parent.viewport().height() +
                         self.parent.horizontalHeader().height())


class DataFrameView(QTableView):
    """Data Frame view class"""
    sig_sortByColumn = Signal()
    sig_fetch_more_columns = Signal()
    sig_fetch_more_rows = Signal()

    def __init__(self, parent, model, header, hscroll, vscroll):
        """Constructor."""
        QTableView.__init__(self, parent)
        self.setModel(model)
        self.setHorizontalScrollBar(hscroll)
        self.setVerticalScrollBar(vscroll)
        self.setHorizontalScrollMode(1)
        self.setVerticalScrollMode(1)

        self.sort_old = [None]
        self.header_class = header
        self.header_class.sectionClicked.connect(self.sortByColumn)
        self.menu = self.setup_menu()
        config_shortcut(self.copy, context='variable_explorer', name='copy',
                        parent=self)
        self.horizontalScrollBar().valueChanged.connect(
                        lambda val: self.load_more_data(val, columns=True))
        self.verticalScrollBar().valueChanged.connect(
                        lambda val: self.load_more_data(val, rows=True))

    def load_more_data(self, value, rows=False, columns=False):
        """Load more rows and columns to display."""
        if rows and value == self.verticalScrollBar().maximum():
            self.model().fetch_more(rows=rows)
            self.sig_fetch_more_rows.emit()
        if columns and value == self.horizontalScrollBar().maximum():
            self.model().fetch_more(columns=columns)
            self.sig_fetch_more_columns.emit()

    def sortByColumn(self, index):
        """Implement a Column sort."""
        if self.sort_old == [None]:
            self.header_class.setSortIndicatorShown(True)
        sort_order = self.header_class.sortIndicatorOrder()
        self.sig_sortByColumn.emit()
        if not self.model().sort(index, sort_order):
            if len(self.sort_old) != 2:
                self.header_class.setSortIndicatorShown(False)
            else:
                self.header_class.setSortIndicator(self.sort_old[0],
                                                   self.sort_old[1])
            return
        self.sort_old = [index, self.header_class.sortIndicatorOrder()]

    def contextMenuEvent(self, event):
        """Reimplement Qt method."""
        self.menu.popup(event.globalPos())
        event.accept()

    def setup_menu(self):
        """Setup context menu."""
        copy_action = create_action(self, _('Copy'),
                                    shortcut=keybinding('Copy'),
                                    icon=ima.icon('editcopy'),
                                    triggered=self.copy,
                                    context=Qt.WidgetShortcut)
        functions = ((_("To bool"), bool), (_("To complex"), complex),
                     (_("To int"), int), (_("To float"), float),
                     (_("To str"), to_text_string))
        types_in_menu = [copy_action]
        for name, func in functions:
            # QAction.triggered works differently for PySide and PyQt
            if not API == 'pyside':
                types_in_menu += [create_action(self, name,
                                                triggered=lambda _checked,
                                                func=func:
                                                    self.change_type(func),
                                                    context=Qt.WidgetShortcut)]
            else:
                types_in_menu += [create_action(self, name,
                                                triggered=lambda func=func:
                                                    self.change_type(func),
                                                    context=Qt.WidgetShortcut)]
        menu = QMenu(self)
        add_actions(menu, types_in_menu)
        return menu

    def change_type(self, func):
        """A function that changes types of cells."""
        model = self.model()
        index_list = self.selectedIndexes()
        [model.setData(i, '', change_type=func) for i in index_list]

    @Slot()
    def copy(self):
        """Copy text to clipboard"""
        if not self.selectedIndexes():
            return
        (row_min, row_max,
         col_min, col_max) = get_idx_rect(self.selectedIndexes())
        index = header = False
        df = self.model().df
        obj = df.iloc[slice(row_min, row_max + 1),
                      slice(col_min, col_max + 1)]
        output = io.StringIO()
        obj.to_csv(output, sep='\t', index=index, header=header)
        if not PY2:
            contents = output.getvalue()
        else:
            contents = output.getvalue().decode('utf-8')
        output.close()
        clipboard = QApplication.clipboard()
        clipboard.setText(contents)


class DataFrameHeader(QAbstractTableModel):
    """
    Data Frame Header/Index class.

    Taken from gtabview project (Header4ExtModel).
    For more information please see:
    https://github.com/wavexx/gtabview/blob/master/gtabview/viewer.py
    """

    COLUMN_INDEX = -1  # Makes reference to the index of the table.

    def __init__(self, model, axis, palette):
        super(DataFrameHeader, self).__init__()
        self.model = model
        self.axis = axis
        self._palette = palette
        if self.axis == 0:
            self.total_cols = self.model.shape[1]
            self._shape = (self.model.header_shape[0], self.model.shape[1])
            if self.total_cols > LARGE_COLS:
                self.cols_loaded = COLS_TO_LOAD
            else:
                self.cols_loaded = self.total_cols
        else:
            self.total_rows = self.model.shape[0]
            self._shape = (self.model.shape[0], self.model.header_shape[1])
            if self.total_rows > LARGE_NROWS:
                self.rows_loaded = ROWS_TO_LOAD
            else:
                self.rows_loaded = self.total_rows

    def rowCount(self, index=None):
        if self.axis == 0:
            return max(1, self._shape[0])
        else:
            if self.total_rows <= self.rows_loaded:
                return self.total_rows
            else:
                return self.rows_loaded

    def columnCount(self, index=QModelIndex()):
        """DataFrame column number"""
        # This is done to implement series
        if self.axis == 0:
            if len(self.model.shape) == 1:
                return 2
            elif self.total_cols <= self.cols_loaded:
                return self.total_cols
            else:
                return self.cols_loaded
        else:
            return max(1, self._shape[1])

    def can_fetch_more(self):
        if self.axis == 1:
            if self.total_rows > self.rows_loaded:
                return True
            else:
                return False
        if self.axis == 0:
            if self.total_cols > self.cols_loaded:
                return True
            else:
                return False

    def fetch_more(self, rows=False, columns=False):
        if self.can_fetch_more() and self.axis == 1:
            reminder = self.total_rows - self.rows_loaded
            items_to_fetch = min(reminder, ROWS_TO_LOAD)
            self.beginInsertRows(QModelIndex(), self.rows_loaded,
                                 self.rows_loaded + items_to_fetch - 1)
            self.rows_loaded += items_to_fetch
            self.endInsertRows()
        if self.can_fetch_more() and self.axis == 0:
            reminder = self.total_cols - self.cols_loaded
            items_to_fetch = min(reminder, COLS_TO_LOAD)
            self.beginInsertColumns(QModelIndex(), self.cols_loaded,
                                    self.cols_loaded + items_to_fetch - 1)
            self.cols_loaded += items_to_fetch
            self.endInsertColumns()

    def sort(self, column, order=Qt.AscendingOrder):
        """Overriding sort method."""
        ascending = order == Qt.AscendingOrder
        self.model.sort(self.COLUMN_INDEX, order=ascending)
        return True

    def headerData(self, section, orientation, role):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return Qt.AlignCenter | Qt.AlignBottom
            else:
                return Qt.AlignRight | Qt.AlignVCenter
        if role != Qt.DisplayRole:
            return None
        if self.axis == 1 and self._shape[1] <= 1:
            return None
        orient_axis = 0 if orientation == Qt.Horizontal else 1
        if self.model.header_shape[orient_axis] > 1:
            header = section
        else:
            header = self.model.header(self.axis, section)
            if isinstance(header, TEXT_TYPES):
                # Get the proper encoding of the text in the header.
                # Fixes Issue 3896
                if not PY2:
                    try:
                        header = header.encode('utf-8')
                        coding = 'utf-8-sig'
                    except UnicodeEncodeError:
                        coding = encoding.get_coding(header)
                else:
                    coding = encoding.get_coding(header)
                return to_text_string(header, encoding=coding)
            header = to_text_string(header)
        return header

    def data(self, index, role):
        if not index.isValid() or \
           index.row() >= self._shape[0] or \
           index.column() >= self._shape[1]:
            return None
        row, col = ((index.row(), index.column()) if self.axis == 0
                    else (index.column(), index.row()))
        if role == Qt.BackgroundRole:
            prev = self.model.header(self.axis, col - 1, row) if col else None
            cur = self.model.header(self.axis, col, row)
            return self._palette.midlight() if prev != cur else None
        if role != Qt.DisplayRole:
            return None
        if self.axis == 0 and self._shape[0] <= 1:
            return None
        return to_text_string(self.model.header(self.axis, col, row))


class DataFrameLevel(QAbstractTableModel):
    """
    Data Frame level class.

    Taken from the gtabview project(Level4ExtModel).
    For more information please see:
    https://github.com/wavexx/gtabview/blob/master/gtabview/viewer.py
    """

    def __init__(self, model, palette, font):
        super(DataFrameLevel, self).__init__()
        self.model = model
        self._background = palette.dark().color()
        if self._background.lightness() > 127:
            self._foreground = palette.text()
        else:
            self._foreground = palette.highlightedText()
        self._palette = palette
        font.setBold(True)
        self._font = font

    def rowCount(self, index=None):
        return max(1, self.model.header_shape[0])

    def columnCount(self, index=None):
        return max(1, self.model.header_shape[1])

    def headerData(self, section, orientation, role):
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return Qt.AlignCenter | Qt.AlignBottom
            else:
                return Qt.AlignRight | Qt.AlignVCenter
        if role != Qt.DisplayRole:
            return None
        if self.model.header_shape[0] <= 1 and orientation == Qt.Horizontal:
            return 'Index'
        elif self.model.header_shape[0] <= 1:
            return None
        return 'Index ' + to_text_string(section)

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.FontRole:
            return self._font
        if index.row() == self.model.header_shape[0] - 1:
            if role == Qt.DisplayRole:
                return str(self.model.name(1, index.column()))
            elif role == Qt.ForegroundRole:
                return self._foreground
            elif role == Qt.BackgroundRole:
                return self._background
        elif index.column() == self.model.header_shape[1] - 1:
            if role == Qt.DisplayRole:
                return str(self.model.name(0, index.row()))
            elif role == Qt.ForegroundRole:
                return self._foreground
            elif role == Qt.BackgroundRole:
                return self._background
        elif role == Qt.BackgroundRole:
            return self._palette.window()
        return None


class DataFrameEditor(QDialog):
    """
    Dialog for displaying and editing DataFrame and related objects.

    Signals
    -------
    sig_option_changed(str, object): Raised if an option is changed.
       Arguments are name of option and its new value.
    """
    sig_option_changed = Signal(str, object)

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.is_series = False
        self.layout = None

    def setup_and_check(self, data, title=''):
        """
        Setup DataFrameEditor:
        return False if data is not supported, True otherwise.
        Supported types for data are DataFrame, Series and DatetimeIndex.
        """
        self._selection_rec = False
        self._model = None

        self.layout = QGridLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setWindowIcon(ima.icon('arredit'))
        if title:
            title = to_text_string(title) + " - %s" % data.__class__.__name__
        else:
            title = _("%s editor") % data.__class__.__name__
        if isinstance(data, Series):
            self.is_series = True
            data = data.to_frame()
        elif isinstance(data, DatetimeIndex):
            data = DataFrame(data)

        self.setWindowTitle(title)
        self.resize(600, 500)

        self.hscroll = QScrollBar(Qt.Horizontal)
        self.vscroll = QScrollBar(Qt.Vertical)

        self.table_level = QTableView()
        self.table_level.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_level.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_level.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_level.setFrameStyle(QFrame.Plain)
        self.table_level.horizontalHeader().sectionResized.connect(
                                                        self._index_resized)
        self.table_level.verticalHeader().sectionResized.connect(
                                                        self._header_resized)
        self.table_level.setItemDelegate(QItemDelegate())
        self.layout.addWidget(self.table_level, 0, 0)
        self.table_level.setContentsMargins(0, 0, 0, 0)
        self.table_level.horizontalHeader().sectionClicked.connect(
                                                            self.sortByIndex)
        self.table_header = QTableView()
        self.table_header.verticalHeader().hide()
        self.table_header.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_header.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_header.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_header.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table_header.setHorizontalScrollBar(self.hscroll)
        self.table_header.setFrameStyle(QFrame.Plain)
        self.table_header.horizontalHeader().sectionResized.connect(
                                                        self._column_resized)
        self.table_header.setItemDelegate(QItemDelegate())
        self.layout.addWidget(self.table_header, 0, 1)

        self.table_index = QTableView()
        self.table_index.horizontalHeader().hide()
        self.table_index.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_index.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_index.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_index.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table_index.setVerticalScrollBar(self.vscroll)
        self.table_index.setFrameStyle(QFrame.Plain)
        self.table_index.verticalHeader().sectionResized.connect(
                                                            self._row_resized)
        self.table_index.setItemDelegate(QItemDelegate())
        self.layout.addWidget(self.table_index, 1, 0)
        self.table_index.setContentsMargins(0, 0, 0, 0)

        self.dataModel = DataFrameModel(data, parent=self)
        self.dataTable = DataFrameView(self, self.dataModel,
                                       self.table_header.horizontalHeader(),
                                       self.hscroll, self.vscroll)
        self.dataTable.verticalHeader().hide()
        self.dataTable.horizontalHeader().hide()
        self.dataTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dataTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dataTable.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.dataTable.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.dataTable.setFrameStyle(QFrame.Plain)
        self.dataTable.setItemDelegate(QItemDelegate())
        self.layout.addWidget(self.dataTable, 1, 1)
        self.setFocusProxy(self.dataTable)
        self.dataTable.sig_sortByColumn.connect(self._sort_update)
        self.dataTable.sig_fetch_more_columns.connect(self._fetch_more_columns)
        self.dataTable.sig_fetch_more_rows.connect(self._fetch_more_rows)

        self.layout.addWidget(self.hscroll, 2, 0, 2, 2)
        self.layout.addWidget(self.vscroll, 0, 2, 2, 2)

        # autosize columns on-demand
        self._autosized_cols = set()
        self._max_autosize_ms = None
        self.dataTable.installEventFilter(self)

        avg_width = self.fontMetrics().averageCharWidth()
        self.min_trunc = avg_width * 8  # Minimum size for columns
        self.max_width = avg_width * 64  # Maximum size for columns

        self.setLayout(self.layout)
        self.setMinimumSize(400, 300)
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        btn_layout = QHBoxLayout()

        btn = QPushButton(_("Format"))
        # disable format button for int type
        btn_layout.addWidget(btn)
        btn.clicked.connect(self.change_format)
        btn = QPushButton(_('Resize'))
        btn_layout.addWidget(btn)
        btn.clicked.connect(self.resize_to_contents)

        bgcolor = QCheckBox(_('Background color'))
        bgcolor.setChecked(self.dataModel.bgcolor_enabled)
        bgcolor.setEnabled(self.dataModel.bgcolor_enabled)
        bgcolor.stateChanged.connect(self.change_bgcolor_enable)
        btn_layout.addWidget(bgcolor)

        self.bgcolor_global = QCheckBox(_('Column min/max'))
        self.bgcolor_global.setChecked(self.dataModel.colum_avg_enabled)
        self.bgcolor_global.setEnabled(not self.is_series and
                                       self.dataModel.bgcolor_enabled)
        self.bgcolor_global.stateChanged.connect(self.dataModel.colum_avg)
        btn_layout.addWidget(self.bgcolor_global)

        btn_layout.addStretch()
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        btn_layout.addWidget(bbox)
        btn_layout.setContentsMargins(4, 4, 4, 4)
        self.layout.addLayout(btn_layout, 4, 0, 2, 2)
        self.setModel(self.dataModel)
        self.resizeColumnsToContents()

        return True

    def sortByIndex(self, index):
        """Implement a Index sort."""
        self.table_level.horizontalHeader().setSortIndicatorShown(True)
        sort_order = self.table_level.horizontalHeader().sortIndicatorOrder()
        self.table_index.model().sort(index, sort_order)
        self._sort_update()

    def model(self):
        return self._model

    def _column_resized(self, col, old_width, new_width):
        self.dataTable.setColumnWidth(col, new_width)
        self._update_layout()

    def _row_resized(self, row, old_height, new_height):
        self.dataTable.setRowHeight(row, new_height)
        self._update_layout()

    def _index_resized(self, col, old_width, new_width):
        self.table_index.setColumnWidth(col, new_width)
        self._update_layout()

    def _header_resized(self, row, old_height, new_height):
        self.table_header.setRowHeight(row, new_height)
        self._update_layout()

    def _update_layout(self):
        h_width = max(self.table_level.verticalHeader().sizeHint().width(),
                      self.table_index.verticalHeader().sizeHint().width())
        self.table_level.verticalHeader().setFixedWidth(h_width)
        self.table_index.verticalHeader().setFixedWidth(h_width)

        last_row = self._model.header_shape[0] - 1
        if last_row < 0:
            hdr_height = self.table_level.horizontalHeader().height()
        else:
            hdr_height = self.table_level.rowViewportPosition(last_row) + \
                         self.table_level.rowHeight(last_row) + \
                         self.table_level.horizontalHeader().height()
            if last_row == 0:
                self.table_level.setRowHidden(0, True)
                self.table_header.setRowHidden(0, True)
        self.table_header.setFixedHeight(hdr_height)
        self.table_level.setFixedHeight(hdr_height)

        last_col = self._model.header_shape[1] - 1
        if last_col < 0:
            idx_width = self.table_level.verticalHeader().width()
        else:
            idx_width = self.table_level.columnViewportPosition(last_col) + \
                        self.table_level.columnWidth(last_col) + \
                        self.table_level.verticalHeader().width()
        self.table_index.setFixedWidth(idx_width)
        self.table_level.setFixedWidth(idx_width)
        self._resizeVisibleColumnsToContents()

    def _reset_model(self, table, model):
        old_sel_model = table.selectionModel()
        table.setModel(model)
        if old_sel_model:
            del old_sel_model

    def setAutosizeLimit(self, limit_ms):
        self._max_autosize_ms = limit_ms

    def setModel(self, model, relayout=True):
        self._model = model
        sel_model = self.dataTable.selectionModel()
        sel_model.currentColumnChanged.connect(
                self._resizeCurrentColumnToContents)

        self._reset_model(self.table_level, DataFrameLevel(model,
                                                           self.palette(),
                                                           self.font()))
        self._reset_model(self.table_header, DataFrameHeader(model,
                                                             0,
                                                             self.palette()))
        self._reset_model(self.table_index, DataFrameHeader(model,
                                                            1,
                                                            self.palette()))
        # Needs to be called after setting all table models
        if relayout:
            self._update_layout()

    def setCurrentIndex(self, y, x):
        self.dataTable.selectionModel().setCurrentIndex(
            self.dataTable.model().index(y, x),
            QItemSelectionModel.ClearAndSelect)

    def _sizeHintForColumn(self, table, col, limit_ms=None):
        max_row = table.model().rowCount()
        lm_start = time.clock()
        lm_row = 64 if limit_ms else max_row
        max_width = 0
        for row in range(max_row):
            v = table.sizeHintForIndex(table.model().index(row, col))
            max_width = max(max_width, v.width())
            if row > lm_row:
                lm_now = time.clock()
                lm_elapsed = (lm_now - lm_start) * 1000
                if lm_elapsed >= limit_ms:
                    break
                lm_row = int((row / lm_elapsed) * limit_ms)
        return max_width

    def _resizeColumnToContents(self, header, data, col, limit_ms):
        hdr_width = self._sizeHintForColumn(header, col, limit_ms)
        data_width = self._sizeHintForColumn(data, col, limit_ms)
        if data_width > hdr_width:
            width = min(self.max_width, data_width)
        elif hdr_width > data_width * 2:
            width = max(min(hdr_width, self.min_trunc), min(self.max_width,
                        data_width))
        else:
            width = min(self.max_width, hdr_width)
        header.setColumnWidth(col, width)

    def _resizeColumnsToContents(self, header, data, limit_ms):
        max_col = data.model().columnCount()
        if limit_ms is None:
            max_col_ms = None
        else:
            max_col_ms = limit_ms / max(1, max_col)
        for col in range(max_col):
            self._resizeColumnToContents(header, data, col, max_col_ms)

    def eventFilter(self, obj, event):
        if obj == self.dataTable and event.type() == QEvent.Resize:
            self._resizeVisibleColumnsToContents()
        return False

    def _resizeVisibleColumnsToContents(self):
        index_column = self.dataTable.rect().topLeft().x()
        start = col = self.dataTable.columnAt(index_column)
        width = self._model.shape[1]
        end = self.dataTable.columnAt(self.dataTable.rect().bottomRight().x())
        end = width if end == -1 else end + 1
        if self._max_autosize_ms is None:
            max_col_ms = None
        else:
            max_col_ms = self._max_autosize_ms / max(1, end - start)
        while col < end:
            resized = False
            if col not in self._autosized_cols:
                self._autosized_cols.add(col)
                resized = True
                self._resizeColumnToContents(self.table_header, self.dataTable,
                                             col, max_col_ms)
            col += 1
            if resized:
                # As we resize columns, the boundary will change
                index_column = self.dataTable.rect().bottomRight().x()
                end = self.dataTable.columnAt(index_column)
                end = width if end == -1 else end + 1
                if max_col_ms is not None:
                    max_col_ms = self._max_autosize_ms / max(1, end - start)

    def _resizeCurrentColumnToContents(self, new_index, old_index):
        if new_index.column() not in self._autosized_cols:
            # Ensure the requested column is fully into view after resizing
            self._resizeVisibleColumnsToContents()
            self.dataTable.scrollTo(new_index)

    def resizeColumnsToContents(self):
        self._autosized_cols = set()
        self._resizeColumnsToContents(self.table_level,
                                      self.table_index, self._max_autosize_ms)
        self._update_layout()
        self.table_level.resizeColumnsToContents()

    def change_bgcolor_enable(self, state):
        """
        This is implementet so column min/max is only active when bgcolor is
        """
        self.dataModel.bgcolor(state)
        self.bgcolor_global.setEnabled(not self.is_series and state > 0)

    def change_format(self):
        """
        Ask user for display format for floats and use it.

        This function also checks whether the format is valid and emits
        `sig_option_changed`.
        """
        format, valid = QInputDialog.getText(self, _('Format'),
                                             _("Float formatting"),
                                             QLineEdit.Normal,
                                             self.dataModel.get_format())
        if valid:
            format = str(format)
            try:
                format % 1.1
            except:
                msg = _("Format ({}) is incorrect").format(format)
                QMessageBox.critical(self, _("Error"), msg)
                return
            if not format.startswith('%'):
                msg = _("Format ({}) should start with '%'").format(format)
                QMessageBox.critical(self, _("Error"), msg)
                return
            self.dataModel.set_format(format)
            self.sig_option_changed.emit('dataframe_format', format)

    def get_value(self):
        """Return modified Dataframe -- this is *not* a copy"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        df = self.dataModel.get_data()
        if self.is_series:
            return df.iloc[:, 0]
        else:
            return df

    def _update_header_size(self):
        """Update the column width of the header."""
        column_count = self.table_header.model().columnCount()
        for index in range(0, column_count):
            if index < column_count:
                column_width = self.dataTable.columnWidth(index)
                self.table_header.setColumnWidth(index, column_width)
            else:
                break

    def _sort_update(self):
        """
        Update the model for all the QTableView objects.

        Uses the model of the dataTable as the base.
        """
        self.setModel(self.dataTable.model())

    def _fetch_more_columns(self):
        """Fetch more data for the header (columns)."""
        self.table_header.model().fetch_more()

    def _fetch_more_rows(self):
        """Fetch more data for the index (rows)."""
        self.table_index.model().fetch_more()

    def resize_to_contents(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.dataTable.resizeColumnsToContents()
        self.dataModel.fetch_more(columns=True)
        self.dataTable.resizeColumnsToContents()
        self._update_header_size()
        QApplication.restoreOverrideCursor()


#==============================================================================
# Tests
#==============================================================================
def test_edit(data, title="", parent=None):
    """Test subroutine"""
    app = qapplication()                  # analysis:ignore
    dlg = DataFrameEditor(parent=parent)

    if dlg.setup_and_check(data, title=title):
        dlg.exec_()
        return dlg.get_value()
    else:
        import sys
        sys.exit(1)


def test():
    """DataFrame editor test"""
    from numpy import nan
    from pandas.util.testing import assert_frame_equal, assert_series_equal

    df1 = DataFrame([
                     [True, "bool"],
                     [1+1j, "complex"],
                     ['test', "string"],
                     [1.11, "float"],
                     [1, "int"],
                     [np.random.rand(3, 3), "Unkown type"],
                     ["Large value", 100],
                     ["áéí", "unicode"]
                    ],
                    index=['a', 'b', nan, nan, nan, 'c',
                           "Test global max", 'd'],
                    columns=[nan, 'Type'])
    out = test_edit(df1)
    assert_frame_equal(df1, out)

    result = Series([True, "bool"], index=[nan, 'Type'], name='a')
    out = test_edit(df1.iloc[0])
    assert_series_equal(result, out)

    df1 = DataFrame(np.random.rand(100100, 10))
    out = test_edit(df1)
    assert_frame_equal(out, df1)

    series = Series(np.arange(10), name=0)
    out = test_edit(series)
    assert_series_equal(series, out)


if __name__ == '__main__':
    test()

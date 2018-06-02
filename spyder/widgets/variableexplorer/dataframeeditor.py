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

# Third party imports
from qtpy import API
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, Slot
from qtpy.QtGui import QColor, QCursor
from qtpy.QtWidgets import (QApplication, QCheckBox, QDialog, QGridLayout,
                            QHBoxLayout, QInputDialog, QLineEdit, QMenu,
                            QMessageBox, QPushButton, QTableView, QHeaderView)

from pandas import DataFrame, DatetimeIndex, Series
try:
    from pandas._libs.tslib import OutOfBoundsDatetime
except ImportError:  # For pandas version < 0.20
    from pandas.tslib import OutOfBoundsDatetime
import numpy as np

# Local imports
from spyder.config.base import _
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.config.gui import get_font, config_shortcut
from spyder.py3compat import (io, is_text_string, is_type_text_string, PY2,
                              to_text_string, TEXT_TYPES)
from spyder.utils import encoding
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    keybinding, qapplication)
from spyder.widgets.variableexplorer.arrayeditor import get_idx_rect

# Supported Numbers and complex numbers
REAL_NUMBER_TYPES = (float, int, np.int64, np.int32)
COMPLEX_NUMBER_TYPES = (complex, np.complex64, np.complex128)
# Used to convert bool intrance to false since bool('False') will return True
_bool_false = ['false', 'f', '0', '0.', '0.0', ' ']

# Default format for data frames with floats
DEFAULT_FORMAT = '%.6g'

# Limit at which dataframe is considered so large that it is loaded on demand
LARGE_SIZE = 5e5
LARGE_NROWS = 1e5
LARGE_COLS = 60

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
    Used to convert bool intrance to false since any string in bool('')
    will return True
    """
    if value.lower() in _bool_false:
        value = ''
    return value


def global_max(col_vals, index):
    """Returns the global maximum and minimum"""
    col_vals_without_None = [x for x in col_vals if x is not None]
    max_col, min_col = zip(*col_vals_without_None)
    return max(max_col), min(min_col)


class DataFrameModel(QAbstractTableModel):
    """ DataFrame Table Model"""
    
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

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header data"""
        if role != Qt.DisplayRole:
            return to_qvariant()

        if orientation == Qt.Horizontal:
            if section == 0:
                return 'Index'
            elif section == 1 and PY2:
                header = self.df_header[0]
                # Get rid of possible BOM utf-8 data present at the
                # beginning of a file, which gets attached to the first
                # column header when headers are present in the first
                # row.
                # Fixes Issue 2514
                try:
                    header = to_text_string(header, encoding='utf-8-sig')
                except:
                    # Don't perform any conversion on strings because it
                    # leads to differences between the data present in
                    # the dataframe and what is shown by Spyder
                    if not is_type_text_string(header):
                        header = to_text_string(self.df_header[0])
                return to_qvariant(header)
            elif is_type_text_string(self.df_header[section-1]):
                # Don't perform any conversion on strings because it
                # leads to differences between the data present in
                # the dataframe and what is shown by Spyder
                return to_qvariant(self.df_header[section-1])
            else:
                return to_qvariant(to_text_string(self.df_header[section-1]))
        else:
            return to_qvariant()

    def get_bgcolor(self, index):
        """Background color depending on value"""
        column = index.column()
        if column == 0:
            color = QColor(BACKGROUND_NONNUMBER_COLOR)
            color.setAlphaF(BACKGROUND_INDEX_ALPHA)
            return color
        if not self.bgcolor_enabled:
            return
        value = self.get_value(index.row(), column-1)
        if self.max_min_col[column - 1] is None:
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
            vmax, vmin = self.return_max(self.max_min_col, column-1)
            hue = (BACKGROUND_NUMBER_MINHUE + BACKGROUND_NUMBER_HUERANGE *
                   (vmax - color_func(value)) / (vmax - vmin))
            hue = float(abs(hue))
            if hue > 1:
                hue = 1
            color = QColor.fromHsvF(hue, BACKGROUND_NUMBER_SATURATION,
                                    BACKGROUND_NUMBER_VALUE, BACKGROUND_NUMBER_ALPHA)
        return color

    def get_value(self, row, column):
        """Returns the value of the DataFrame"""
        # To increase the performance iat is used but that requires error
        # handling, so fallback uses iloc
        try:
            value = self.df.iat[row, column]
        except OutOfBoundsDatetime:
            value = self.df.iloc[:, column].astype(str).iat[row]
        except:
            value = self.df.iloc[row, column]
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
            if column == 0:
                df_idx = self.df_index[row]
                if is_type_text_string(df_idx):
                    # Don't perform any conversion on strings
                    # because it leads to differences between
                    # the data present in the dataframe and
                    # what is shown by Spyder
                    return df_idx
                else:
                    return to_qvariant(to_text_string(df_idx))
            else:
                value = self.get_value(row, column-1)
                if isinstance(value, float):
                    try:
                        return to_qvariant(self._format % value)
                    except (ValueError, TypeError):
                        # may happen if format = '%d' and value = NaN;
                        # see issue 4139
                        return to_qvariant(DEFAULT_FORMAT % value)
                elif is_type_text_string(value):
                    # Don't perform any conversion on strings
                    # because it leads to differences between
                    # the data present in the dataframe and
                    # what is shown by Spyder
                    return value
                else:
                    return to_qvariant(to_text_string(value))
        elif role == Qt.BackgroundColorRole:
            return to_qvariant(self.get_bgcolor(index))
        elif role == Qt.FontRole:
            return to_qvariant(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
        return to_qvariant()

    def sort(self, column, order=Qt.AscendingOrder):
        """Overriding sort method"""
        if self.complex_intran is not None:
            if self.complex_intran.any(axis=0).iloc[column-1]:
                QMessageBox.critical(self.dialog, "Error",
                                     "TypeError error: no ordering "
                                     "relation is defined for complex numbers")
                return False
        try:
            ascending = order == Qt.AscendingOrder
            if column > 0:
                try:
                    self.df.sort_values(by=self.df.columns[column-1],
                                        ascending=ascending, inplace=True,
                                        kind='mergesort')
                except AttributeError:
                    # for pandas version < 0.17
                    self.df.sort(columns=self.df.columns[column-1],
                                 ascending=ascending, inplace=True,
                                 kind='mergesort')
                except ValueError as e:
                    # Not possible to sort on duplicate columns #5225
                    QMessageBox.critical(self.dialog, "Error",
                                         "ValueError: %s" % to_text_string(e))
                except SystemError as e:
                    # Not possible to sort on category dtypes #5361
                    QMessageBox.critical(self.dialog, "Error",
                                         "SystemError: %s" % to_text_string(e))
                self.update_df_index()
            else:
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
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
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
                self.df.iloc[row, column - 1] = change_type(val)
            except ValueError:
                self.df.iloc[row, column - 1] = change_type('0')
        else:
            val = from_qvariant(value, str)
            current_value = self.get_value(row, column-1)
            if isinstance(current_value, (bool, np.bool_)):
                val = bool_false_check(val)
            supported_types = (bool, np.bool_) + REAL_NUMBER_TYPES
            if (isinstance(current_value, supported_types) or
                    is_text_string(current_value)):
                try:
                    self.df.iloc[row, column-1] = current_value.__class__(val)
                except (ValueError, OverflowError) as e:
                    QMessageBox.critical(self.dialog, "Error",
                                         str(type(e).__name__) + ": " + str(e))
                    return False
            else:
                QMessageBox.critical(self.dialog, "Error",
                                     "Editing dtype {0!s} not yet supported."
                                     .format(type(current_value).__name__))
                return False
        self.max_min_col_update()
        self.dataChanged.emit(index, index)
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
            return self.total_cols + 1
        else:
            return self.cols_loaded + 1

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
    def __init__(self, parent, model):
        QTableView.__init__(self, parent)
        self.setModel(model)

        self.frozen_table_view = FrozenTableView(self)
        self.frozen_table_view.update_geometry()

        self.setHorizontalScrollMode(1)
        self.setVerticalScrollMode(1)

        self.horizontalHeader().sectionResized.connect(self.update_section_width)
        self.verticalHeader().sectionResized.connect(self.update_section_height)

        self.frozen_table_view.verticalScrollBar().valueChanged.connect(
            self.verticalScrollBar().setValue)

        self.sort_old = [None]
        self.header_class = self.horizontalHeader()
        self.header_class.sectionClicked.connect(self.sortByColumn)
        self.menu = self.setup_menu()
        config_shortcut(self.copy, context='variable_explorer', name='copy',
                        parent=self)
        self.horizontalScrollBar().valueChanged.connect(
                        lambda val: self.load_more_data(val, columns=True))
        self.verticalScrollBar().valueChanged.connect(
                        lambda val: self.load_more_data(val, rows=True))
        self.verticalScrollBar().valueChanged.connect(
            self.frozen_table_view.verticalScrollBar().setValue)
    
    def update_section_width(self, logical_index, old_size, new_size):
        """Update the horizontal width of the frozen column when a
        change takes place in the first column of the table"""
        if logical_index == 0:
            self.frozen_table_view.setColumnWidth(0, new_size)
            self.frozen_table_view.update_geometry()

    def update_section_height(self, logical_index, old_size, new_size):
        """Update the vertical width of the frozen column when a
        change takes place on any of the rows"""
        self.frozen_table_view.setRowHeight(logical_index, new_size)

    def resizeEvent(self, event):
        """Update the frozen column dimensions.

        Updates takes place when the enclosing window of this 
        table reports a dimension change
        """
        QTableView.resizeEvent(self, event)
        self.frozen_table_view.update_geometry()

    def moveCursor(self, cursor_action, modifiers):
        """Update the table position.

        Updates the position along with the frozen column
        when the cursor (selector) changes its position
        """
        current = QTableView.moveCursor(self, cursor_action, modifiers)
        
        col_width = (self.frozen_table_view.columnWidth(0) + 
                     self.frozen_table_view.columnWidth(1))
        topleft_x = self.visualRect(current).topLeft().x()

        overflow = self.MoveLeft and current.column() > 1
        overflow = overflow and topleft_x < col_width

        if cursor_action == overflow:
            new_value = (self.horizontalScrollBar().value() + 
                         topleft_x - col_width)
            self.horizontalScrollBar().setValue(new_value)
        return current

    def scrollTo(self, index, hint):
        """Scroll the table.

        It is necessary to ensure that the item at index is visible.
        The view will try to position the item according to the
        given hint. This method does not takes effect only if
        the frozen column is scrolled.
        """
        if index.column() > 1:
            QTableView.scrollTo(self, index, hint)

    def load_more_data(self, value, rows=False, columns=False):
        if rows and value == self.verticalScrollBar().maximum():
            self.model().fetch_more(rows=rows)
        if columns and value == self.horizontalScrollBar().maximum():
            self.model().fetch_more(columns=columns)

    def sortByColumn(self, index):
        """ Implement a Column sort """
        if self.sort_old == [None]:
            self.header_class.setSortIndicatorShown(True)
        sort_order = self.header_class.sortIndicatorOrder()
        if not self.model().sort(index, sort_order):
            if len(self.sort_old) != 2:
                self.header_class.setSortIndicatorShown(False)
            else:
                self.header_class.setSortIndicator(self.sort_old[0],
                                                   self.sort_old[1])
            return
        self.sort_old = [index, self.header_class.sortIndicatorOrder()]

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        self.menu.popup(event.globalPos())
        event.accept()

    def setup_menu(self):
        """Setup context menu"""
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
                slot = lambda _checked, func=func: self.change_type(func)
            else:
                slot = lambda func=func: self.change_type(func)
            types_in_menu += [create_action(self, name,
                                            triggered=slot,
                                            context=Qt.WidgetShortcut)]
        menu = QMenu(self)
        add_actions(menu, types_in_menu)
        return menu

    def change_type(self, func):
        """A function that changes types of cells"""
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
        if col_min == 0:
            col_min = 1
            index = True
        df = self.model().df
        if col_max == 0:  # To copy indices
            contents = '\n'.join(map(str, df.index.tolist()[slice(row_min,
                                                            row_max+1)]))
        else:  # To copy DataFrame
            if (col_min == 0 or col_min == 1) and (df.shape[1] == col_max):
                header = True
            obj = df.iloc[slice(row_min, row_max+1), slice(col_min-1, col_max)]
            output = io.StringIO()
            obj.to_csv(output, sep='\t', index=index, header=header)
            if not PY2:
                contents = output.getvalue()
            else:
                contents = output.getvalue().decode('utf-8')
            output.close()
        clipboard = QApplication.clipboard()
        clipboard.setText(contents)


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
        self.layout = QGridLayout()
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

        self.dataModel = DataFrameModel(data, parent=self)
        self.dataModel.dataChanged.connect(self.save_and_close_enable)
        self.dataTable = DataFrameView(self, self.dataModel)

        self.layout.addWidget(self.dataTable)
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

        self.btn_save_and_close = QPushButton(_('Save and Close'))
        self.btn_save_and_close.setDisabled(True)
        self.btn_save_and_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_('Close'))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        self.layout.addLayout(btn_layout, 2, 0)

        return True

    @Slot(QModelIndex, QModelIndex)
    def save_and_close_enable(self, top_left, bottom_right):
        """Handle the data change event to enable the save and close button."""
        self.btn_save_and_close.setEnabled(True)
        self.btn_save_and_close.setAutoDefault(True)
        self.btn_save_and_close.setDefault(True)

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

    def resize_to_contents(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.dataTable.resizeColumnsToContents()
        self.dataModel.fetch_more(columns=True)
        self.dataTable.resizeColumnsToContents()
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

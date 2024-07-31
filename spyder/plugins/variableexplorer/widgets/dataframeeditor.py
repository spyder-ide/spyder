# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2011-2012 Lambda Foundry, Inc. and PyData Development Team
# Copyright (c) 2013 Jev Kuznetsov and contributors
# Copyright (c) 2014-2015 Scott Hansen <firecat4153@gmail.com>
# Copyright (c) 2014-2016 Yuri D'Elia "wave++" <wavexx@thregr.org>
# Copyright (c) 2014- Spyder Project Contributors
#
# Components of gtabview originally distributed under the MIT (Expat) license.
# This file as a whole distributed under the terms of the New BSD License
# (BSD 3-clause; see NOTICE.txt in the Spyder root directory for details).
# -----------------------------------------------------------------------------

"""
Pandas DataFrame Editor Dialog.

DataFrameModel is based on the class ArrayModel from array editor
and the class DataFrameModel from the pandas project.
Present in pandas.sandbox.qtpandas in v0.13.1.

DataFrameHeaderModel and DataFrameLevelModel are based on the classes
Header4ExtModel and Level4ExtModel from the gtabview project.
DataFrameModel is based on the classes ExtDataModel and ExtFrameModel, and
DataFrameEditor is based on gtExtTableView from the same project.

DataFrameModel originally based on pandas/sandbox/qtpandas.py of the
`pandas project <https://github.com/pandas-dev/pandas>`_.
The current version is qtpandas/models/DataFrameModel.py of the
`QtPandas project <https://github.com/draperjames/qtpandas>`_.

Components of gtabview from gtabview/viewer.py and gtabview/models.py of the
`gtabview project <https://github.com/TabViewer/gtabview>`_.
"""

# Standard library imports
import io
from time import perf_counter
from typing import Any, Callable, Optional

# Third party imports
from packaging.version import parse
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtCore import (
    QAbstractTableModel, QEvent, QItemSelectionModel, QModelIndex, QPoint, Qt,
    Signal, Slot)
from qtpy.QtGui import QColor, QCursor
from qtpy.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QItemDelegate, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollBar,
    QStyle, QTableView, QTableWidget, QToolButton, QVBoxLayout, QWidget)
from spyder_kernels.utils.lazymodules import numpy as np, pandas as pd

# Local imports
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _
from spyder.plugins.variableexplorer.widgets.arrayeditor import get_idx_rect
from spyder.plugins.variableexplorer.widgets.basedialog import BaseDialog
from spyder.plugins.variableexplorer.widgets.preferences import (
    PreferencesDialog
)
from spyder.py3compat import (is_text_string, is_type_text_string,
                              to_text_string)
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.qthelpers import keybinding, qapplication
from spyder.utils.stylesheet import AppStyle, MAC


# =============================================================================
# ---- Constants
# =============================================================================

class DataframeEditorActions:
    ConvertToBool = 'convert_to_bool_action'
    ConvertToComplex = 'convert_to_complex_action'
    ConvertToFloat = 'convert_to_float_action'
    ConvertToInt = 'convert_to_int_action'
    ConvertToStr = 'convert_to_str_action'
    Copy = 'copy_action'
    DuplicateColumn = 'duplicate_column_action'
    DuplicateRow = 'duplicate_row_action'
    Edit = 'edit_action'
    EditHeader = 'edit_header_action'
    EditIndex = 'edit_index_action'
    InsertAbove = 'insert_above_action'
    InsertAfter = 'insert_after_action'
    InsertBefore = 'insert_before_action'
    InsertBelow = 'insert_below_action'
    Preferences = 'preferences_action'
    Refresh = 'refresh_action'
    RemoveColumn = 'remove_column_action'
    RemoveRow = 'remove_row_action'
    ResizeColumns = 'resize_columns_action'
    ResizeRows = 'resize_rows_action'


class DataframeEditorMenus:
    Context = 'context_menu'
    ConvertTo = 'convert_to_submenu'
    Header = 'header_context_menu'
    Index = 'index_context_menu'
    Options = 'options_menu'


class DataframeEditorWidgets:
    OptionsToolButton = 'options_button_widget'
    Toolbar = 'toolbar'
    ToolbarStretcher = 'toolbar_stretcher'


class DataframeEditorContextMenuSections:
    Edit = 'edit_section'
    Row = 'row_section'
    Column = 'column_section'
    Convert = 'convert_section'


class DataframeEditorToolbarSections:
    Row = 'row_section'
    ColumnAndRest = 'column_section'


# Supported real and complex number types
REAL_NUMBER_TYPES = (float, int, np.int64, np.int32)
COMPLEX_NUMBER_TYPES = (complex, np.complex64, np.complex128)

# Used to convert bool intrance to false since bool('False') will return True
_bool_false = ['false', 'f', '0', '0.', '0.0', ' ']

# Default format for data frames with floats
DEFAULT_FORMAT = '.6g'

# Limit at which dataframe is considered so large that it is loaded on demand
LARGE_SIZE = 5e5
LARGE_NROWS = 1e5
LARGE_COLS = 60
ROWS_TO_LOAD = 500
COLS_TO_LOAD = 40

# Background colours
BACKGROUND_NUMBER_MINHUE = 0.66  # hue for largest number
BACKGROUND_NUMBER_HUERANGE = 0.33  # (hue for smallest) minus (hue for largest)
BACKGROUND_NUMBER_SATURATION = 0.7
BACKGROUND_NUMBER_VALUE = 1.0
BACKGROUND_NUMBER_ALPHA = 0.6
BACKGROUND_NONNUMBER_COLOR = SpyderPalette.COLOR_BACKGROUND_2
BACKGROUND_STRING_ALPHA = 0.05
BACKGROUND_MISC_ALPHA = 0.3

# =============================================================================
# ---- Utility functions
# =============================================================================

def is_any_real_numeric_dtype(dtype) -> bool:
    """
    Test whether a Pandas dtype is a real numeric type.
    """
    try:
        import pandas.api.types
        return pandas.api.types.is_any_real_numeric_dtype(dtype)
    except Exception:
        # Pandas version 1
        return dtype in REAL_NUMBER_TYPES


def bool_false_check(value):
    """
    Used to convert bool entrance to false.

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


# =============================================================================
# ---- Main classes
# =============================================================================

class DataFrameModel(QAbstractTableModel, SpyderFontsMixin):
    """
    DataFrame Table Model.

    Partly based in ExtDataModel and ExtFrameModel classes
    of the gtabview project.

    For more information please see:
    https://github.com/wavexx/gtabview/blob/master/gtabview/models.py

    Attributes
    ----------
    bgcolor_enabled : bool
        If True, vary backgrond color depending on cell value
    colum_avg_enabled : bool
        If True, select background color by comparing cell value against
        column maximum and minimum. Otherwise, use maximum and minimum of
        the entire dataframe.
    _format_spec : str
        Format specification for floats
    """

    def __init__(self, dataFrame, format_spec=DEFAULT_FORMAT, parent=None):
        QAbstractTableModel.__init__(self)
        self.dialog = parent
        self.df = dataFrame
        self.df_columns_list = None
        self.df_index_list = None
        self._format_spec = format_spec
        self.complex_intran = None
        self.display_error_idxs = []

        self.total_rows = self.df.shape[0]
        self.total_cols = self.df.shape[1]
        size = self.total_rows * self.total_cols

        self.max_min_col = None
        if size < LARGE_SIZE:
            self.max_min_col_update()
            self.colum_avg_enabled = True
            self.bgcolor_enabled = True
            self.colum_avg(True)
        else:
            self.colum_avg_enabled = False
            self.bgcolor_enabled = False
            self.colum_avg(False)

        # Use paging when the total size, number of rows or number of
        # columns is too large
        if size > LARGE_SIZE:
            self.rows_loaded = ROWS_TO_LOAD
            self.cols_loaded = COLS_TO_LOAD
        else:
            if self.total_rows > LARGE_NROWS:
                self.rows_loaded = ROWS_TO_LOAD
            else:
                self.rows_loaded = self.total_rows
            if self.total_cols > LARGE_COLS:
                self.cols_loaded = COLS_TO_LOAD
            else:
                self.cols_loaded = self.total_cols

    def _axis(self, axis):
        """
        Return the corresponding labels taking into account the axis.

        The axis could be horizontal (0) or vertical (1).
        """
        return self.df.columns if axis == 0 else self.df.index

    def _axis_list(self, axis):
        """
        Return the corresponding labels as a list taking into account the axis.

        The axis could be horizontal (0) or vertical (1).
        """
        if axis == 0:
            if self.df_columns_list is None:
                self.df_columns_list = self.df.columns.tolist()
            return self.df_columns_list
        else:
            if self.df_index_list is None:
                self.df_index_list = self.df.index.tolist()
            return self.df_index_list

    def _axis_levels(self, axis):
        """
        Return the number of levels in the labels taking into account the axis.

        Get the number of levels for the columns (0) or rows (1).
        """
        ax = self._axis(axis)
        return 1 if not hasattr(ax, 'levels') else len(ax.levels)

    @property
    def shape(self):
        """Return the shape of the dataframe."""
        return self.df.shape

    @property
    def header_shape(self):
        """Return the levels for the columns and rows of the dataframe."""
        return (self._axis_levels(0), self._axis_levels(1))

    @property
    def chunk_size(self):
        """Return the max value of the dimensions of the dataframe."""
        return max(*self.shape())

    def header(self, axis, x, level=0):
        """
        Return the values of the labels for the header of columns or rows.

        The value corresponds to the header of column or row x in the
        given level.
        """
        ax = self._axis(axis)
        if not hasattr(ax, 'levels'):
            ax = self._axis_list(axis)
            if len(ax) > 0:
                return ax[x]
            else:
                return None
        else:
            return ax.values[x][level]

    def name(self, axis, level):
        """Return the labels of the levels if any."""
        ax = self._axis(axis)
        if hasattr(ax, 'levels'):
            return ax.names[level]
        if ax.name:
            return ax.name

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
        if self.df.shape[0] == 0:  # If no rows to compute max/min then return
            return
        self.max_min_col = []
        for __, col in self.df.items():
            # This is necessary to catch an error in Pandas when computing
            # the maximum of a column.
            # Fixes spyder-ide/spyder#17145
            try:
                if (
                    is_any_real_numeric_dtype(col.dtype)
                    or col.dtype in COMPLEX_NUMBER_TYPES
                ):
                    if is_any_real_numeric_dtype(col.dtype):
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
            except TypeError:
                max_min = None
            self.max_min_col.append(max_min)

    def get_format_spec(self) -> str:
        """
        Return current format specification for floats.
        """
        # Avoid accessing the private attribute _format_spec from outside
        return self._format_spec

    def set_format_spec(self, format_spec: str) -> None:
        """
        Set format specification for floats.
        """
        self._format_spec = format_spec
        self.reset()

    def bgcolor(self, value: bool):
        """
        Set whether background color varies depending on cell value.
        """
        self.bgcolor_enabled = value
        self.reset()

    def colum_avg(self, value: bool):
        """
        Set what to compute cell value with to choose background color.

        If `value` is True, then compare against column maximum and minimum,
        otherwise compare against maximum and minimum over all columns.
        """
        self.colum_avg_enabled = value
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
        if self.max_min_col[column] is None or pd.isna(value):
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

            # This is necessary to catch an error in Pandas when computing
            # the difference between the max and min of a column.
            # Fixes spyder-ide/spyder#18005
            try:
                if vmax - vmin == 0:
                    vmax_vmin_diff = 1.0
                else:
                    vmax_vmin_diff = vmax - vmin
            except TypeError:
                return

            hue = (BACKGROUND_NUMBER_MINHUE + BACKGROUND_NUMBER_HUERANGE *
                   (vmax - color_func(value)) / (vmax_vmin_diff))
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
        except pd._libs.tslib.OutOfBoundsDatetime:
            value = self.df.iloc[:, column].astype(str).iat[row]
        except:
            value = self.df.iloc[row, column]
        return value

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
                    return to_qvariant(format(value, self._format_spec))
                except (ValueError, TypeError):
                    # may happen if format = 'd' and value = NaN;
                    # see spyder-ide/spyder#4139.
                    return to_qvariant(format(value, DEFAULT_FORMAT))
            elif is_type_text_string(value):
                # Don't perform any conversion on strings
                # because it leads to differences between
                # the data present in the dataframe and
                # what is shown by Spyder
                return value
            else:
                try:
                    return to_qvariant(to_text_string(value))
                except Exception:
                    self.display_error_idxs.append(index)
                    return u'Display Error!'
        elif role == Qt.BackgroundColorRole:
            return to_qvariant(self.get_bgcolor(index))
        elif role == Qt.FontRole:
            return self.get_font(SpyderFontType.MonospaceInterface)
        elif role == Qt.ToolTipRole:
            if index in self.display_error_idxs:
                return _("It is not possible to display this value because\n"
                         "an error occurred while trying to do it")
        return to_qvariant()

    def recalculate_index(self):
        """Recalcuate index information."""
        self.df_index_list = self.df.index.tolist()
        self.df_columns_list = self.df.columns.tolist()
        self.total_rows = self.df.shape[0]

        # Necessary to set rows_loaded because rowCount() method
        self.rows_loaded = self.df.shape[0]

        # Necessary to set cols_loaded because of columnCount() method
        self.cols_loaded = self.df.shape[1]
        self.total_cols = self.df.shape[1]

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
                except ValueError as e:
                    # Not possible to sort on duplicate columns
                    # See spyder-ide/spyder#5225.
                    QMessageBox.critical(self.dialog, "Error",
                                         "ValueError: %s" % to_text_string(e))
                except SystemError as e:
                    # Not possible to sort on category dtypes
                    # See spyder-ide/spyder#5361.
                    QMessageBox.critical(self.dialog, "Error",
                                         "SystemError: %s" % to_text_string(e))
            else:
                # Update index list
                self.recalculate_index()
                # To sort by index
                self.df.sort_index(inplace=True, ascending=ascending)
        except TypeError as e:
            QMessageBox.critical(self.dialog, "Error",
                                 "TypeError error: %s" % str(e))
            return False

        self.reset()
        return True

    def flags(self, index):
        """Set flags"""
        return (
            QAbstractTableModel.flags(self, index) | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index, value, role=Qt.EditRole, change_type=None):
        """Cell content change"""
        column = index.column()
        row = index.row()

        if index in self.display_error_idxs:
            return False
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
            if isinstance(current_value, (bool, np.bool_)):
                val = bool_false_check(val)
            supported_types = (bool, np.bool_) + REAL_NUMBER_TYPES
            if (isinstance(current_value, supported_types) or
                    is_text_string(current_value)):
                try:
                    self.df.iloc[row, column] = current_value.__class__(val)
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
        # Avoid a "Qt exception in virtual methods" generated in our
        # tests on Windows/Python 3.7
        # See spyder-ide/spyder#8910.
        try:
            if self.total_rows <= self.rows_loaded:
                return self.total_rows
            else:
                return self.rows_loaded
        except AttributeError:
            return 0

    def fetch_more(self, rows=False, columns=False):
        """Get more columns and/or rows."""
        if rows and self.total_rows > self.rows_loaded:
            reminder = self.total_rows - self.rows_loaded
            items_to_fetch = min(reminder, ROWS_TO_LOAD)
            self.beginInsertRows(QModelIndex(), self.rows_loaded,
                                 self.rows_loaded + items_to_fetch - 1)
            self.rows_loaded += items_to_fetch
            self.endInsertRows()
        if columns and self.total_cols > self.cols_loaded:
            reminder = self.total_cols - self.cols_loaded
            items_to_fetch = min(reminder, COLS_TO_LOAD)
            self.beginInsertColumns(QModelIndex(), self.cols_loaded,
                                    self.cols_loaded + items_to_fetch - 1)
            self.cols_loaded += items_to_fetch
            self.endInsertColumns()

    def columnCount(self, index=QModelIndex()):
        """DataFrame column number"""
        # Avoid a "Qt exception in virtual methods" generated in our
        # tests on Windows/Python 3.7
        # See spyder-ide/spyder#8910.
        try:
            # This is done to implement series
            if len(self.df.shape) == 1:
                return 2
            elif self.total_cols <= self.cols_loaded:
                return self.total_cols
            else:
                return self.cols_loaded
        except AttributeError:
            return 0

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class DataFrameView(QTableView, SpyderWidgetMixin):
    """
    Data Frame view class.

    Signals
    -------
    sig_sort_by_column(): Raised after more columns are fetched.
    sig_fetch_more_rows(): Raised after more rows are fetched.
    """
    sig_sort_by_column = Signal()
    sig_fetch_more_columns = Signal()
    sig_fetch_more_rows = Signal()

    CONF_SECTION = 'variable_explorer'

    def __init__(self, parent, model, header, hscroll, vscroll,
                 data_function: Optional[Callable[[], Any]] = None):
        """Constructor."""
        QTableView.__init__(self, parent)

        self.menu = None
        self.menu_header_h = None
        self.empty_ws_menu = None
        self.copy_action = None
        self.edit_action = None
        self.edit_header_action = None
        self.insert_action_above = None
        self.insert_action_below = None
        self.insert_action_after = None
        self.insert_action_before = None
        self.remove_row_action = None
        self.remove_col_action = None
        self.duplicate_row_action = None
        self.duplicate_col_action = None
        self.convert_to_menu = None
        self.resize_action = None
        self.resize_columns_action = None

        self.menu = self.setup_menu()
        self.menu_header_h = self.setup_menu_header()
        self.register_shortcut_for_widget(name='copy', triggered=self.copy)

        self.setModel(model)
        self.setHorizontalScrollBar(hscroll)
        self.setVerticalScrollBar(vscroll)
        self.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)

        self.sort_old = [None]
        self.header_class = header
        self.header_class.setContextMenuPolicy(Qt.CustomContextMenu)
        self.header_class.customContextMenuRequested.connect(
            self.show_header_menu)
        self.header_class.sectionClicked.connect(self.sortByColumn)
        self.data_function = data_function
        self.horizontalScrollBar().valueChanged.connect(
            self._load_more_columns)
        self.verticalScrollBar().valueChanged.connect(self._load_more_rows)

    def _load_more_columns(self, value):
        """Load more columns to display."""
        # Needed to avoid a NameError while fetching data when closing
        # See spyder-ide/spyder#12034.
        try:
            self.load_more_data(value, columns=True)
        except NameError:
            pass

    def _load_more_rows(self, value):
        """Load more rows to display."""
        # Needed to avoid a NameError while fetching data when closing
        # See spyder-ide/spyder#12034.
        try:
            self.load_more_data(value, rows=True)
        except NameError:
            pass

    def load_more_data(self, value, rows=False, columns=False):
        """Load more rows and columns to display."""
        try:
            if rows and value == self.verticalScrollBar().maximum():
                self.model().fetch_more(rows=rows)
                self.sig_fetch_more_rows.emit()
            if columns and value == self.horizontalScrollBar().maximum():
                self.model().fetch_more(columns=columns)
                self.sig_fetch_more_columns.emit()

        except NameError:
            # Needed to handle a NameError while fetching data when closing
            # See spyder-ide/spyder#7880.
            pass

    def setModel(self, model: DataFrameModel) -> None:
        """
        Set the model for the view to present.

        This overrides the function in QTableView so that we can enable or
        disable actions when appropriate if the selection changes.
        """
        super().setModel(model)
        self.selectionModel().selectionChanged.connect(self.refresh_menu)
        self.refresh_menu()

    def sortByColumn(self, index):
        """Implement a column sort."""
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
        self.sig_sort_by_column.emit()

    def show_header_menu(self, pos):
        """Show edition menu for header."""
        global_pos = self.mapToGlobal(pos)
        index = self.indexAt(pos)
        self.header_class.setCurrentIndex(index)
        self.menu_header_h.popup(global_pos)

    def contextMenuEvent(self, event):
        """Reimplement Qt method."""
        self.menu.popup(event.globalPos())
        event.accept()

    def setup_menu_header(self):
        """Setup context header menu."""
        edit_header_action = self.create_action(
            name=DataframeEditorActions.EditHeader,
            text=_("Edit"),
            icon=ima.icon('edit'),
            triggered=self.edit_header_item,
            register_action=False
        )
        menu = self.create_menu(DataframeEditorMenus.Header, register=False)
        self.add_item_to_menu(edit_header_action, menu)
        return menu

    def refresh_menu(self):
        """Refresh context menu"""
        index = self.currentIndex()

        # Enable/disable edit actions
        condition_edit = (
            index.isValid() and
            (len(self.selectedIndexes()) == 1)
        )

        for action in [self.edit_action, self.insert_action_above,
                       self.insert_action_below, self.insert_action_after,
                       self.insert_action_before, self.duplicate_row_action,
                       self.duplicate_col_action]:
            action.setEnabled(condition_edit)

        # Enable/disable actions for remove col/row and copy
        condition_copy_remove = (
            index.isValid() and
            (len(self.selectedIndexes()) > 0)
        )

        for action in [self.copy_action, self.remove_row_action,
                       self.remove_col_action]:
            action.setEnabled(condition_copy_remove)

    def setup_menu(self):
        """Setup context menu."""
        # ---- Create actions

        self.resize_action = self.create_action(
            name=DataframeEditorActions.ResizeRows,
            text=_("Resize rows to contents"),
            icon=ima.icon('collapse_row'),
            triggered=lambda: self.resize_to_contents(rows=True),
            register_action=False
        )
        self.resize_columns_action = self.create_action(
            name=DataframeEditorActions.ResizeColumns,
            text=_("Resize columns to contents"),
            icon=ima.icon('collapse_column'),
            triggered=self.resize_to_contents,
            register_action=False
        )
        self.edit_action = self.create_action(
            name=DataframeEditorActions.Edit,
            text=_("Edit"),
            icon=ima.icon('edit'),
            triggered=self.edit_item,
            register_action=False
        )
        self.insert_action_above = self.create_action(
            name=DataframeEditorActions.InsertAbove,
            text=_("Insert above"),
            icon=ima.icon('insert_above'),
            triggered=lambda: self.insert_item(axis=1, before_above=True),
            register_action=False
        )
        self.insert_action_below = self.create_action(
            name=DataframeEditorActions.InsertBelow,
            text=_("Insert below"),
            icon=ima.icon('insert_below'),
            triggered=lambda: self.insert_item(axis=1, before_above=False),
            register_action=False
        )
        self.insert_action_before = self.create_action(
            name=DataframeEditorActions.InsertBefore,
            text=_("Insert before"),
            icon=ima.icon('insert_before'),
            triggered=lambda: self.insert_item(axis=0, before_above=True),
            register_action=False
        )
        self.insert_action_after = self.create_action(
            name=DataframeEditorActions.InsertAfter,
            text=_("Insert after"),
            icon=ima.icon('insert_after'),
            triggered=lambda: self.insert_item(axis=0, before_above=False),
            register_action=False
        )
        self.remove_row_action = self.create_action(
            name=DataframeEditorActions.RemoveRow,
            text=_("Remove row"),
            icon=ima.icon('delete_row'),
            triggered=self.remove_item,
            register_action=False
        )
        self.remove_col_action = self.create_action(
            name=DataframeEditorActions.RemoveColumn,
            text=_("Remove column"),
            icon=ima.icon('delete_column'),
            triggered=lambda: self.remove_item(axis=1),
            register_action=False
        )
        self.duplicate_row_action = self.create_action(
            name=DataframeEditorActions.DuplicateRow,
            text=_("Duplicate row"),
            icon=ima.icon('duplicate_row'),
            triggered=lambda: self.duplicate_row_col(dup_row=True),
            register_action=False
        )
        self.duplicate_col_action = self.create_action(
            name=DataframeEditorActions.DuplicateColumn,
            text=_("Duplicate column"),
            icon=ima.icon('duplicate_column'),
            triggered=lambda: self.duplicate_row_col(dup_row=False),
            register_action=False
        )
        self.copy_action = self.create_action(
            name=DataframeEditorActions.Copy,
            text=_('Copy'),
            icon=ima.icon('editcopy'),
            triggered=self.copy,
            register_action=False
        )
        self.copy_action.setShortcut(keybinding('Copy'))
        self.copy_action.setShortcutContext(Qt.WidgetShortcut)

        # ---- Create "Convert to" submenu and actions

        self.convert_to_menu = self.create_menu(
            menu_id=DataframeEditorMenus.ConvertTo,
            title=_('Convert to'),
            register=False
        )
        functions = (
            (_("Bool"), bool, DataframeEditorActions.ConvertToBool),
            (_("Complex"), complex, DataframeEditorActions.ConvertToComplex),
            (_("Int"), int, DataframeEditorActions.ConvertToInt),
            (_("Float"), float, DataframeEditorActions.ConvertToFloat),
            (_("Str"), to_text_string, DataframeEditorActions.ConvertToStr)
        )
        for text, func, name in functions:
            def slot():
                self.change_type(func)
            action = self.create_action(
                name=name,
                text=text,
                triggered=slot,
                context=Qt.WidgetShortcut,
                register_action=False
            )
            self.add_item_to_menu(action, self.convert_to_menu)

        # ---- Create context menu and fill it

        menu = self.create_menu(DataframeEditorMenus.Context, register=False)
        for action in [self.copy_action, self.edit_action]:
            self.add_item_to_menu(
                action,
                menu,
                section=DataframeEditorContextMenuSections.Edit
            )
        for action in [self.insert_action_above, self.insert_action_below,
                       self.duplicate_row_action, self.remove_row_action]:
            self.add_item_to_menu(
                action,
                menu,
                section=DataframeEditorContextMenuSections.Row
            )
        for action in [self.insert_action_before, self.insert_action_after,
                       self.duplicate_col_action, self.remove_col_action]:
            self.add_item_to_menu(
                action,
                menu,
                section=DataframeEditorContextMenuSections.Column
            )
        self.add_item_to_menu(
            self.convert_to_menu,
            menu,
            section=DataframeEditorContextMenuSections.Convert
        )

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
        # Copy index and header too (equal True).
        # See spyder-ide/spyder#11096
        index = header = True
        df = self.model().df
        obj = df.iloc[slice(row_min, row_max + 1),
                      slice(col_min, col_max + 1)]
        output = io.StringIO()
        try:
            obj.to_csv(output, sep='\t', index=index, header=header)
        except UnicodeEncodeError:
            # Needed to handle encoding errors in Python 2
            # See spyder-ide/spyder#4833
            QMessageBox.critical(
                self,
                _("Error"),
                _("Text can't be copied."))
        contents = output.getvalue()
        output.close()
        clipboard = QApplication.clipboard()
        clipboard.setText(contents)

    def resize_to_contents(self, rows=False):
        """Resize rows or cols to its contents."""
        if isinstance(self.parent(), DataFrameEditor):
            if rows:
                self.resizeRowsToContents()
                self.parent().table_index.resizeRowsToContents()
            else:
                self.parent().resize_to_contents()

    def flags(self, index):
        """Set flags"""
        return Qt.ItemFlags(
            int(QAbstractTableModel.flags(self, index) |
                Qt.ItemIsEditable | Qt.ItemIsEnabled |
                Qt.ItemIsSelectable | Qt.EditRole)
        )

    def edit_header_item(self):
        """Edit header item"""
        pos = self.header_class.currentIndex()
        index = self.header_class.logicalIndex(pos.column())
        if index >= 0:
            model_index = self.header_class.model().index(0, index)
            index_number_rows = 1

            if type(self.model().df.columns[0]) is tuple:
                index_number_rows = len(self.model().df.columns[0])

            if index_number_rows > 1:
                dialog = QInputDialog()
                dialog.setWindowTitle("Enter the values")
                label = QLabel("Enter the values:")
                dialog.show()
                dialog.findChild(QLineEdit).hide()
                dialog.findChild(QLabel).hide()
                lines = []
                for row in range(index_number_rows):
                    line = QLineEdit(text=self.model().df.columns[index][row])
                    dialog.layout().insertWidget(row, line)
                    lines.append(line)
                dialog.layout().insertWidget(0, label)
                dialog.hide()
                confirmation = dialog.exec_() == QDialog.Accepted
                if confirmation:
                    value = tuple(line.text() for line in lines)
            else:
                value, confirmation = QInputDialog.getText(
                    self,
                    _("Enter a value"),
                    _("Enter a value"),
                    QLineEdit.Normal,
                    ""
                )

            if confirmation:
                if value not in self.model().df.columns.tolist():
                    if type(value) is tuple:
                        n_cols = len(self.model().df.columns)
                        cols = self.model().df.columns
                        names = cols.names
                        cols = (
                            self.model().df.columns.tolist()[0:index]
                            + [value]
                            + self.model().df.columns.tolist()[index+1:n_cols]
                        )
                        self.model().df.columns = (
                            pd.MultiIndex.from_tuples(cols, names=names)
                        )
                    else:
                        self.header_class.model().setData(
                            model_index,
                            value,
                            Qt.EditRole
                        )

                    self.parent()._reload()
                    self.model().dataChanged.emit(pos, pos)
                else:
                    QMessageBox.warning(
                        self.model().dialog,
                        _("Warning: Duplicate column"),
                        _('Column with name "{}" already exists!').format(
                            value)
                    )

    def edit_item(self):
        """Edit item"""
        index = self.currentIndex()
        if not index.isValid():
            return

        # TODO: Remove hard coded "Value" column number (3 here)
        self.edit(index.child(index.row(), index.column()))

    def insert_item(self, axis=0, before_above=False):
        """Insert row or column."""
        current_index = self.currentIndex()
        if not current_index.isValid():
            return False

        column = current_index.column()
        row = current_index.row()
        step = 0
        df = self.model().df

        if not before_above:
            step = 1

        if axis == 0:
            # insert column
            module = df.iat[row, column].__class__.__module__

            if module == 'builtins':
                # Evaluate character '' (empty) to initialize the column as a
                # neutral data type
                eval_type = df.iat[row, column].__class__.__name__ + '('')'
            else:
                # Necessary because of import numpy as np
                if module == 'numpy':
                    module = 'np'
                eval_type = (
                    module
                    + '.'
                    + df.iat[row, column].__class__.__name__
                    + '('')'
                )

            indexes = df.axes[1].tolist()
            new_name = 'new_col'
            if type(indexes[column]) is not str:
                new_name = indexes[column]

            if new_name in indexes:
                if type(new_name) is tuple:
                    tuple_idx = []
                    new_tuple = []

                    for idx in indexes:
                        tuple_idx = tuple_idx + list(idx)

                    for idx in range(len(new_name)):
                        new_tuple.append(
                            self.next_index_name(tuple_idx, new_name[idx])
                        )

                    new_name = tuple(new_tuple)
                else:
                    new_name = self.next_index_name(indexes, new_name)

            item_value = eval(eval_type)
            if item_value == ():
                item_value = ('')

            df.insert(
                loc=column + step,
                column=new_name,
                value=item_value,
                allow_duplicates=True
            )

            self.model().max_min_col_update()
            if before_above:
                column = column + 1

        if axis == 1:
            # insert row
            indexes = df.axes[0].tolist()
            new_name = 'new_row'
            if type(indexes[row]) is not str:
                new_name = indexes[row]
            if new_name in indexes:
                new_name = self.next_index_name(indexes, new_name)

            # Slice the upper half of the dataframe
            df1 = df[0:row + step]

            # Store the result of lower half of the dataframe
            df2 = df[row + step:]

            # Insert the row in the upper half dataframe
            new_row = df.iloc[[row]]
            new_row.axes[0].values[0] = new_name

            for col in range(len(new_row.columns)):
                module = new_row.iat[0, col].__class__.__module__
                if module == 'builtins':
                    # Evaluate character '' (empty) to initialyze the column as
                    # a neutral data type
                    eval_type = new_row.iat[0, col].__class__.__name__ + '('')'
                else:
                    # Necessary because of import numpy as np
                    if module == 'numpy':
                        module = 'np'
                    eval_type = (
                        module
                        + '.'
                        + new_row.iat[0, col].__class__.__name__
                        + '('')'
                    )

                new_row.iat[0, col] = eval(eval_type)

            self.model().df = pd.concat([df1, new_row, df2])
            if before_above:
                row = row + 1

        self.parent()._reload()
        self.model().dataChanged.emit(current_index, current_index)
        self.setCurrentIndex(self.model().index(row, column))

    def duplicate_row_col(self, dup_row=False):
        """Duplicate row or column."""
        current_index = self.currentIndex()
        if not current_index.isValid():
            return False

        column = current_index.column()
        row = current_index.row()
        df = self.model().df

        if dup_row:
            # Slice the upper half of the dataframe
            df1 = self.model().df[0:row]

            # Store the result of lower half of the dataframe
            df2 = self.model().df[row:]

            # Insert the row in the upper half dataframe
            new_row = self.model().df.iloc[[row]]
            label = new_row.axes[0].values[0]
            indexes = self.model().df.axes[0].tolist()
            indexes.remove(label)
            new_name = self.next_index_name(indexes, label)
            new_row.axes[0].values[0] = new_name
            self.model().df = pd.concat([df1, new_row, df2])
            row = row + 1
        else:
            indexes = df.axes[1].tolist()
            label = indexes[column]
            indexes.remove(label)

            if type(label) is tuple:
                tuple_idx = []
                new_tuple = []

                for idx in indexes:
                    tuple_idx = tuple_idx + list(idx)

                for idx in range(len(label)):
                    new_tuple.append(
                        self.next_index_name(tuple_idx, label[idx])
                    )
                new_name = tuple(new_tuple)
            else:
                new_name = self.next_index_name(indexes, label)

            df.insert(loc=column+1, column=new_name, value='',
                      allow_duplicates=True)
            df[new_name] = df.iloc[:, column]
            self.model().max_min_col_update()

        self.parent()._reload()
        self.model().dataChanged.emit(current_index, current_index)
        self.setCurrentIndex(self.model().index(row, column))

    def next_index_name(self, indexes, label):
        """
        Calculate and generate next index_name for a duplicate column/row
        rol/col_copy(ind).
        """
        ind = -1
        name = ''
        acceptable_types = (
            [str, float, int, complex, bool]
            + list(REAL_NUMBER_TYPES)
            + list(COMPLEX_NUMBER_TYPES)
        )

        if type(label) not in acceptable_types:
            # Case receiving a different type of acceptable_type,
            # treat as string
            label = str(label)

        if type(label) is str:
            # Make all indexes strings to compare
            for i in range(len(indexes)):
                if type(indexes[i]) is not str:
                    indexes[i] = str(indexes[i])

            # Verify if find '_copy(' in the label
            if label.rfind('_copy(') == -1:
                # If not found, verify in other indexes
                name = label + '_copy('

                for n in indexes:
                    if n.rfind(name) == 0:
                        # label_copy( starts in first position
                        init_pos = len(name)
                        final_pos = len(n) - 1
                        curr_ind = n[init_pos:final_pos]
                        if (
                            curr_ind.isnumeric()
                            and n[final_pos:final_pos+1] == ')'
                        ):
                            if ind < int(curr_ind):
                                ind = int(curr_ind)
            else:
                # If 'copy_(' string is in label, verify if valid and check
                # next.
                init_pos = label.rfind('_copy(') + 6
                final_pos = len(label) - 1
                curr_ind = label[init_pos:final_pos]

                if curr_ind.isnumeric():
                    if label[final_pos:final_pos+1] == ')':
                        ind = int(curr_ind)
                        name = label[0:init_pos]

                        for n in indexes:
                            if n.rfind(name) == 0:
                                init_pos = len(name)
                                final_pos = len(n) - 1
                                curr_ind = n[init_pos:final_pos]
                                if (
                                    curr_ind.isnumeric()
                                    and n[final_pos:final_pos+1] == ')'
                                ):
                                    if ind < int(curr_ind):
                                        ind = int(curr_ind)
                    else:
                        # If not closed parenthesis, treat entire string as
                        # valid
                        name = label + '_copy('
                        for n in indexes:
                            if n.rfind(name) == 0:
                                init_pos = len(name)
                                final_pos = len(n) - 1
                                curr_ind = n[init_pos:final_pos]
                                if (
                                    curr_ind.isnumeric()
                                    and n[final_pos:final_pos+1] == ')'
                                ):
                                    if ind < int(curr_ind):
                                        ind = int(curr_ind)
                else:
                    # Found '_copy(not a number)', treat entire string as valid
                    # and check if exist other '_copy(Not number)*_copy(number)
                    name = label + '_copy('
                    for n in indexes:
                        if n.rfind(name) == 0:
                            init_pos = len(name)
                            final_pos = len(n) - 1
                            curr_ind = n[init_pos:final_pos]
                            if (
                                curr_ind.isnumeric()
                                and n[final_pos:final_pos+1] == ')'
                            ):
                                if ind < int(curr_ind):
                                    ind = int(curr_ind)

            ind = ind+1
            return name + str(ind) + ')'
        else:
            # Type is numeric: increment 1 and check if it is in list.
            label = label + 1

            while label in indexes:
                label = label + 1

            return label

    @Slot()
    def remove_item(self, force=False, axis=0):
        """Remove item."""
        indexes = self.selectedIndexes()
        index_label = []
        df = self.model().df
        if not indexes:
            return

        # Keep focus on the item before the deleted one
        focus_row = indexes[0].row()
        focus_col = indexes[0].column()
        if axis == 0 and focus_row > 0:
            focus_row = focus_row - 1
        if axis == 1 and focus_col > 0:
            focus_col = focus_col - 1

        for index in indexes:
            if not index.isValid():
                return
            else:
                if axis == 0:
                    row_label = df.axes[axis][index.row()]
                    if row_label not in index_label:
                        index_label.append(row_label)
                else:
                    column_label = df.axes[axis][index.column()]
                    if column_label not in index_label:
                        index_label.append(column_label)

        if not force:
            one = _("Do you want to remove the selected item?")
            more = _("Do you want to remove all selected items?")
            answer = QMessageBox.question(
                self,
                _("Remove"),
                one if len(indexes) == 1 else more,
                QMessageBox.Yes | QMessageBox.No
            )

        if force or answer == QMessageBox.Yes:
            for label in index_label:
                try:
                    df.drop(label, inplace=True, axis=axis)
                except TypeError as e:
                    QMessageBox.warning(
                        self.model().dialog,
                        _("Warning: It was not possible to remove this item!"),
                        _("ValueError: {} must be removed from index.").format(
                            str(e))
                    )
                    return False

            self.parent()._reload()
            index = QModelIndex()
            self.model().dataChanged.emit(index, index)
            self.setCurrentIndex(self.model().index(focus_row, focus_col))


class DataFrameHeaderModel(QAbstractTableModel, SpyderFontsMixin):
    """
    This class is the model for the header and index of the DataFrameEditor.

    Taken from gtabview project (Header4ExtModel).
    For more information please see:
    https://github.com/wavexx/gtabview/blob/master/gtabview/viewer.py
    """

    COLUMN_INDEX = -1  # Makes reference to the index of the table.

    def __init__(self, model, axis, use_monospace_font=False):
        """
        Header constructor.

        The 'model' is the QAbstractTableModel of the dataframe, the 'axis' is
        to acknowledge if is for the header (horizontal - 0) or for the
        index (vertical - 1) and the palette is the set of colors to use.
        """
        super().__init__()
        self.model = model
        self.axis = axis
        self.use_monospace_font = use_monospace_font

        self.total_rows = self.model.shape[0]
        self.total_cols = self.model.shape[1]
        self.cols_loaded = self.model.cols_loaded
        self.rows_loaded = self.model.rows_loaded

        if self.axis == 0:
            self.total_cols = self.model.shape[1]
            self._shape = (self.model.header_shape[0], self.model.shape[1])
        else:
            self.total_rows = self.model.shape[0]
            self._shape = (self.model.shape[0], self.model.header_shape[1])

    def rowCount(self, index=None):
        """Get number of rows in the header."""
        if self.axis == 0:
            return max(1, self._shape[0])
        else:
            if self.total_rows <= self.rows_loaded:
                return self.total_rows
            else:
                return self.rows_loaded

    def columnCount(self, index=QModelIndex()):
        """DataFrame column number"""
        if self.axis == 0:
            if self.total_cols <= self.cols_loaded:
                return self.total_cols
            else:
                return self.cols_loaded
        else:
            return max(1, self._shape[1])

    def fetch_more(self, rows=False, columns=False):
        """Get more columns or rows (based on axis)."""
        if self.axis == 1 and self.total_rows > self.rows_loaded:
            reminder = self.total_rows - self.rows_loaded
            items_to_fetch = min(reminder, ROWS_TO_LOAD)
            self.beginInsertRows(QModelIndex(), self.rows_loaded,
                                 self.rows_loaded + items_to_fetch - 1)
            self.rows_loaded += items_to_fetch
            self.endInsertRows()
        if self.axis == 0 and self.total_cols > self.cols_loaded:
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
        """Get the information to put in the header."""
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return Qt.AlignCenter
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        if role != Qt.DisplayRole and role != Qt.ToolTipRole:
            return None
        if self.axis == 1 and self._shape[1] <= 1:
            return None
        orient_axis = 0 if orientation == Qt.Horizontal else 1
        if self.model.header_shape[orient_axis] > 1:
            header = section
        else:
            header = self.model.header(self.axis, section)

            # Don't perform any conversion on strings
            # because it leads to differences between
            # the data present in the dataframe and
            # what is shown by Spyder
            if not is_type_text_string(header):
                header = to_text_string(header)

        return header

    def data(self, index, role):
        """
        Get the data for the header.

        This is used when a header has levels.
        """
        if (
            not index.isValid()
            or index.row() >= self._shape[0]
            or index.column() >= self._shape[1]
        ):
            return None

        row, col = (
            (index.row(), index.column()) if self.axis == 0
            else (index.column(), index.row())
        )

        if self.use_monospace_font and role == Qt.FontRole:
            return self.get_font(SpyderFontType.MonospaceInterface)

        if role != Qt.DisplayRole:
            return None

        if self.axis == 0 and self._shape[0] <= 1:
            return None

        header = self.model.header(self.axis, col, row)

        # Don't perform any conversion on strings
        # because it leads to differences between
        # the data present in the dataframe and
        # what is shown by Spyder
        if not is_type_text_string(header):
            header = to_text_string(header)

        return header

    def flags(self, index):
        """Set flags"""
        return Qt.ItemFlags(
            int(QAbstractTableModel.flags(self, index) |
                Qt.ItemIsEditable |
                Qt.ItemIsEnabled |
                Qt.ItemIsSelectable)
        )

    def setData(self, index, value, role):
        """Cell content change"""
        df = self.model.df

        if role == Qt.EditRole:
            if self.axis == 1:
                old_value = df.index[index.row()]

                if value not in df.index.tolist():
                    if type(old_value) is tuple:
                        old_value_list = list(old_value)
                        rows = df.index
                        names = rows.names
                        old_value_list[index.column()] = value
                        rows = (
                            df.index.tolist()[0:index.row()]
                            + [tuple(old_value_list)]
                            + df.index.tolist()[index.row()+1:]
                        )
                        df.index = pd.MultiIndex.from_tuples(rows, names=names)
                    else:
                        try:
                            df.rename(index={old_value: value}, inplace=True,
                                      errors='raise')
                        except TypeError as e:
                            QMessageBox.warning(
                                self.model().dialog,
                                _("Warning: It was not possible to remove "
                                  "this index!"),
                                _("ValueError: {} must be removed from "
                                  "index.").format(str(e))
                            )
                            return False
                else:
                    QMessageBox.warning(
                        self.model().dialog,
                        _("Warning: Duplicate index!"),
                        _('Row with name "{}" already exists!').format(value)
                    )
                    return False

                self.model.dialog._reload()
                self.model.dataChanged.emit(index, index)
                return True

            if self.axis == 0:
                old_value = df.columns[index.column()]

                try:
                    df.rename(columns={old_value: value}, inplace=True,
                              errors='raise')
                except Exception:
                    return False

                return True

            return True

        return False


class DataFrameLevelModel(QAbstractTableModel, SpyderFontsMixin):
    """
    Data Frame level class.

    This class is used to represent index levels in the DataFrameEditor. When
    using MultiIndex, this model creates labels for the index/header as Index i
    for each section in the index/header

    Based on the gtabview project (Level4ExtModel).
    For more information please see:
    https://github.com/wavexx/gtabview/blob/master/gtabview/viewer.py
    """

    def __init__(self, model):
        super().__init__()
        self.model = model
        self._background = QColor(SpyderPalette.COLOR_BACKGROUND_2)

    def rowCount(self, index=None):
        """Get number of rows (number of levels for the header)."""
        return max(1, self.model.header_shape[0])

    def columnCount(self, index=None):
        """Get the number of columns (number of levels for the index)."""
        return max(1, self.model.header_shape[1])

    def headerData(self, section, orientation, role):
        """
        Get the text to put in the header of the levels of the indexes.

        By default it returns 'Index i', where i is the section in the index
        """
        if role == Qt.TextAlignmentRole:
            if orientation == Qt.Horizontal:
                return Qt.AlignCenter
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        if role != Qt.DisplayRole and role != Qt.ToolTipRole:
            return None
        if self.model.header_shape[0] <= 1 and orientation == Qt.Horizontal:
            if self.model.name(1, section):
                return self.model.name(1, section)
            return _('Index')
        elif self.model.header_shape[0] <= 1:
            return None
        elif self.model.header_shape[1] <= 1 and orientation == Qt.Vertical:
            return None
        return _('Index') + ' ' + to_text_string(section)

    def data(self, index, role):
        """Get the information of the levels."""
        if not index.isValid():
            return None
        if role == Qt.FontRole:
            return self.get_font(SpyderFontType.Interface)
        label = ''
        if index.column() == self.model.header_shape[1] - 1:
            label = str(self.model.name(0, index.row()))
        elif index.row() == self.model.header_shape[0] - 1:
            label = str(self.model.name(1, index.column()))
        if role == Qt.DisplayRole and label:
            return label
        elif role == Qt.BackgroundRole:
            return self._background
        elif role == Qt.BackgroundRole:
            return self._palette.window()
        return None


class EmptyDataFrame:
    shape = (0, 0)


class DataFrameEditor(BaseDialog, SpyderWidgetMixin):
    """
    Dialog for displaying and editing DataFrame and related objects.

    Based on the gtabview project (ExtTableView).
    For more information please see:
    https://github.com/wavexx/gtabview/blob/master/gtabview/viewer.py
    """
    CONF_SECTION = 'variable_explorer'

    def __init__(
        self,
        parent: QWidget = None,
        data_function: Optional[Callable[[], Any]] = None
    ):
        super().__init__(parent)
        self.data_function = data_function

        self.refresh_action = self.create_action(
            name=DataframeEditorActions.Refresh,
            text=_('Refresh'),
            icon=ima.icon('refresh'),
            tip=_('Refresh editor with current value of variable in console'),
            triggered=self.refresh_editor,
            register_action=False
        )
        self.refresh_action.setEnabled(self.data_function is not None)
        self.preferences_action = self.create_action(
            name=DataframeEditorActions.Preferences,
            icon=self.create_icon('configure'),
            text=_('Display options ...'),
            triggered=self.show_preferences_dialog,
            register_action=False
        )

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.is_series = False
        self.layout = None
        self.glayout = None
        self.menu_header_v = None
        self.dataTable = None

    def setup_and_check(self, data, title='') -> bool:
        """
        Setup editor.

        It returns False if data is not supported, True otherwise. Supported
        types for data are DataFrame, Series and Index.
        """
        if title:
            title = to_text_string(title) + " - %s" % data.__class__.__name__
        else:
            title = _("%s editor") % data.__class__.__name__

        self.setup_ui(title)
        return self.set_data_and_check(data)

    def setup_ui(self, title: str) -> None:
        """
        Create user interface.
        """
        # ---- Toolbar (to be filled later)

        self.toolbar = self.create_toolbar(
            DataframeEditorWidgets.Toolbar,
            register=False
        )

        # ---- Grid layout with tables and scrollbars showing data frame

        self.glayout = QGridLayout()
        self.glayout.setSpacing(0)
        self.glayout.setContentsMargins(0, 0, 0, 0)

        self.hscroll = QScrollBar(Qt.Horizontal)
        self.vscroll = QScrollBar(Qt.Vertical)

        # Create the view for the level
        self.create_table_level()

        # Create the view for the horizontal header
        self.create_table_header()

        # Create the view for the vertical index
        self.create_table_index()

        # Create menu to allow edit index
        self.menu_header_v = self.setup_menu_header(self.table_index)

        # Create the model and view of the data
        empty_data = EmptyDataFrame()
        self.dataModel = DataFrameModel(empty_data, parent=self)
        self.dataModel.dataChanged.connect(self.save_and_close_enable)
        self.create_data_table()

        self.glayout.addWidget(self.hscroll, 2, 0, 1, 2)
        self.glayout.addWidget(self.vscroll, 0, 2, 2, 1)

        # autosize columns on-demand
        self._autosized_cols = set()

        # Set limit time to calculate column sizeHint to 300ms,
        # See spyder-ide/spyder#11060
        self._max_autosize_ms = 300
        self.dataTable.installEventFilter(self)

        avg_width = self.fontMetrics().averageCharWidth()
        self.min_trunc = avg_width * 12  # Minimum size for columns
        self.max_width = avg_width * 64  # Maximum size for columns

        # ---- Buttons at bottom

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_save_and_close = QPushButton(_('Save and Close'))
        self.btn_save_and_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_('Close'))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        # ---- Final layout

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.toolbar)

        # Remove vertical space between toolbar and data frame
        style = self.style()
        default_spacing = style.pixelMetric(QStyle.PM_LayoutVerticalSpacing)
        self.layout.addSpacing(-default_spacing)

        self.layout.addLayout(self.glayout)
        self.layout.addSpacing((-1 if MAC else 2) * AppStyle.MarginSize)
        self.layout.addLayout(btn_layout)
        self.setLayout(self.layout)

        self.setWindowTitle(title)

        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)

    def set_data_and_check(self, data) -> bool:
        """
        Checks whether data is suitable and display it in the editor.

        This method returns False if data is not supported.
        """
        if not isinstance(data, (pd.DataFrame, pd.Series, pd.Index)):
            return False

        self._selection_rec = False
        self._model = None

        if isinstance(data, pd.Series):
            self.is_series = True
            data = data.to_frame()
        elif isinstance(data, pd.Index):
            data = pd.DataFrame(data)

        # Create the model and view of the data
        self.dataModel = DataFrameModel(data, parent=self)
        self.dataModel.dataChanged.connect(self.save_and_close_enable)
        self.dataTable.setModel(self.dataModel)

        # autosize columns on-demand
        self._autosized_cols = set()

        # Set limit time to calculate column sizeHint to 300ms,
        # See spyder-ide/spyder#11060
        self._max_autosize_ms = 300
        self.dataTable.installEventFilter(self)

        self.setModel(self.dataModel)
        self.resizeColumnsToContents()

        self.btn_save_and_close.setDisabled(True)
        self.dataModel.set_format_spec(self.get_conf('dataframe_format'))

        if self.table_header.rowHeight(0) == 0:
            self.table_header.setRowHeight(0, self.table_header.height())

        stretcher = self.create_stretcher(
            DataframeEditorWidgets.ToolbarStretcher
        )

        options_menu = self.create_menu(
            DataframeEditorMenus.Options,
            register=False
        )
        self.add_item_to_menu(self.preferences_action, options_menu)

        options_button = self.create_toolbutton(
            name=DataframeEditorWidgets.OptionsToolButton,
            text=_('Options'),
            icon=ima.icon('tooloptions'),
            register=False
        )
        options_button.setPopupMode(QToolButton.InstantPopup)
        options_button.setMenu(options_menu)

        self.toolbar.clear()
        self.toolbar._section_items.clear()
        self.toolbar._item_map.clear()

        for item in [
            self.dataTable.insert_action_above,
            self.dataTable.insert_action_below,
            self.dataTable.duplicate_row_action,
            self.dataTable.remove_row_action
        ]:
            self.add_item_to_toolbar(
                item,
                self.toolbar,
                section=DataframeEditorToolbarSections.Row
            )

        for item in [
            self.dataTable.insert_action_before,
            self.dataTable.insert_action_after,
            self.dataTable.duplicate_col_action,
            self.dataTable.remove_col_action,
            stretcher,
            self.dataTable.resize_action,
            self.dataTable.resize_columns_action,
            self.refresh_action,
            options_button
        ]:
            self.add_item_to_toolbar(
                item,
                self.toolbar,
                section=DataframeEditorToolbarSections.ColumnAndRest
            )

        self.toolbar.render()

        return True

    @Slot(QModelIndex, QModelIndex)
    def save_and_close_enable(self, top_left, bottom_right):
        """Handle the data change event to enable the save and close button."""
        self.btn_save_and_close.setEnabled(True)
        self.btn_save_and_close.setAutoDefault(True)
        self.btn_save_and_close.setDefault(True)

    def setup_menu_header(self, header):
        """Setup context header menu."""
        edit_header_action = self.create_action(
            name=DataframeEditorActions.EditIndex,
            text=_("Edit"),
            icon=ima.icon('edit'),
            triggered=lambda: self.edit_header_item(header=header),
            register_action=False
        )
        menu = self.create_menu(DataframeEditorMenus.Index, register=False)
        self.add_item_to_menu(edit_header_action, menu)
        return menu

    @Slot()
    def edit_header_item(self, header=None):
        """Edit item"""

        index = header.currentIndex()
        header.setUpdatesEnabled(True)
        header.setCurrentIndex(index)
        header.edit(index)

    def contextMenuEvent(self, event):
        """Reimplement Qt method."""
        v = QPoint(event.x() - self.table_index.x(), event.y() -
                   self.table_index.y())
        if self.table_index.indexAt(v).isValid():
            self.menu_header_v.popup(event.globalPos())
            event.accept()

    def flags(self, index):
        """Set flags"""
        return Qt.ItemFlags(
            int(QAbstractTableModel.flags(self, index) |
                Qt.ItemIsEditable |
                Qt.ItemIsEnabled |
                Qt.ItemIsSelectable)
        )

    def create_table_level(self):
        """Create the QTableView that will hold the level model."""
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
        self.glayout.addWidget(self.table_level, 0, 0)
        self.table_level.setContentsMargins(0, 0, 0, 0)
        self.table_level.horizontalHeader().sectionClicked.connect(
            self.sortByIndex)

    def create_table_header(self):
        """Create the QTableView that will hold the header model."""
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
        self.glayout.addWidget(self.table_header, 0, 1)

    def create_table_index(self):
        """Create the QTableView that will hold the index model."""
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
        self.glayout.addWidget(self.table_index, 1, 0)
        self.table_index.setContentsMargins(0, 0, 0, 0)

    def create_data_table(self):
        """Create the QTableView that will hold the data model."""
        self.dataTable = DataFrameView(self, self.dataModel,
                                       self.table_header.horizontalHeader(),
                                       self.hscroll, self.vscroll,
                                       self.data_function)
        self.dataTable.verticalHeader().hide()
        self.dataTable.horizontalHeader().hide()
        self.dataTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dataTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dataTable.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.dataTable.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.dataTable.setFrameStyle(QFrame.Plain)
        self.dataTable.setItemDelegate(QItemDelegate())
        self.glayout.addWidget(self.dataTable, 1, 1)
        self.setFocusProxy(self.dataTable)
        self.dataTable.sig_sort_by_column.connect(self._sort_update)
        self.dataTable.sig_fetch_more_columns.connect(self._fetch_more_columns)
        self.dataTable.sig_fetch_more_rows.connect(self._fetch_more_rows)

    def sortByIndex(self, index):
        """Implement a Index sort."""
        self.table_level.horizontalHeader().setSortIndicatorShown(True)
        sort_order = self.table_level.horizontalHeader().sortIndicatorOrder()
        self.table_index.model().sort(index, sort_order)
        self._sort_update()

    def model(self):
        """Get the model of the dataframe."""
        return self._model

    def _column_resized(self, col, old_width, new_width):
        """Update the column width."""
        self.dataTable.setColumnWidth(col, new_width)
        self._update_layout()

    def _row_resized(self, row, old_height, new_height):
        """Update the row height."""
        self.dataTable.setRowHeight(row, new_height)
        self._update_layout()

    def _index_resized(self, col, old_width, new_width):
        """Resize the corresponding column of the index section selected."""
        self.table_index.setColumnWidth(col, new_width)
        self._update_layout()

    def _header_resized(self, row, old_height, new_height):
        """Resize the corresponding row of the header section selected."""
        self.table_header.setRowHeight(row, new_height)
        self._update_layout()

    def _update_layout(self):
        """Set the width and height of the QTableViews and hide rows."""
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
            # Check if the header shape has only one row (which display the
            # same info than the horizontal header).
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
        """Set the model in the given table."""
        old_sel_model = table.selectionModel()
        table.setModel(model)
        if old_sel_model:
            del old_sel_model

    def setAutosizeLimitTime(self, limit_ms):
        """Set maximum time to calculate size hint for columns."""
        self._max_autosize_ms = limit_ms

    def setModel(self, model, relayout=True):
        """Set the model for the data, header/index and level views."""
        self._model = model
        sel_model = self.dataTable.selectionModel()
        sel_model.currentColumnChanged.connect(
                self._resizeCurrentColumnToContents)

        # Asociate the models (level, vertical index and horizontal header)
        # with its corresponding view.
        self._reset_model(self.table_level, DataFrameLevelModel(model))
        self._reset_model(self.table_header, DataFrameHeaderModel(model, 0))

        # We use our monospace font for the index so that it matches the one
        # used for data and things look consistent.
        # Fixes issue spyder-ide/spyder#20960
        self._reset_model(
            self.table_index,
            DataFrameHeaderModel(model, 1, use_monospace_font=True)
        )

        # Needs to be called after setting all table models
        if relayout:
            self._update_layout()

    def setCurrentIndex(self, y, x):
        """Set current selection."""
        self.dataTable.selectionModel().setCurrentIndex(
            self.dataTable.model().index(y, x),
            QItemSelectionModel.ClearAndSelect)

    def _sizeHintForColumn(self, table, col, limit_ms=None):
        """Get the size hint for a given column in a table."""
        max_row = table.model().rowCount()
        lm_start = perf_counter()
        lm_row = 64 if limit_ms else max_row
        max_width = self.min_trunc
        for row in range(max_row):
            v = table.sizeHintForIndex(table.model().index(row, col))
            max_width = max(max_width, v.width())
            if row > lm_row:
                lm_now = perf_counter()
                lm_elapsed = (lm_now - lm_start) * 1000
                if lm_elapsed >= limit_ms:
                    break
                lm_row = int((row / lm_elapsed) * limit_ms)
        return max_width

    def _resizeColumnToContents(self, header, data, col, limit_ms):
        """Resize a column by its contents."""
        hdr_width = self._sizeHintForColumn(header, col, limit_ms)
        data_width = self._sizeHintForColumn(data, col, limit_ms)
        if data_width > hdr_width:
            width = min(self.max_width, data_width)
        elif hdr_width > data_width * 2:
            width = max(min(hdr_width, self.min_trunc), min(self.max_width,
                        data_width))
        else:
            width = max(min(self.max_width, hdr_width), self.min_trunc)
        header.setColumnWidth(col, width)

    def _resizeColumnsToContents(self, header, data, limit_ms):
        """Resize all the colummns to its contents."""
        max_col = data.model().columnCount()
        if limit_ms is None:
            max_col_ms = None
        else:
            max_col_ms = limit_ms / max(1, max_col)
        for col in range(max_col):
            self._resizeColumnToContents(header, data, col, max_col_ms)

    def eventFilter(self, obj, event):
        """Override eventFilter to catch resize event."""
        if obj == self.dataTable and event.type() == QEvent.Resize:
            self._resizeVisibleColumnsToContents()
        return False

    def _resizeVisibleColumnsToContents(self):
        """Resize the columns that are in the view."""
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
        """Resize the current column to its contents."""
        if new_index.column() not in self._autosized_cols:
            # Ensure the requested column is fully into view after resizing
            self._resizeVisibleColumnsToContents()
            self.dataTable.scrollTo(new_index)

    def resizeColumnsToContents(self):
        """Resize the columns to its contents."""
        self._autosized_cols = set()
        self._resizeColumnsToContents(self.table_level,
                                      self.table_index, self._max_autosize_ms)
        self._update_layout()

    def show_preferences_dialog(self) -> None:
        """
        Show dialog for setting view options and process user choices.
        """
        # Create dialog using current options
        dialog = PreferencesDialog('dataframe', parent=self)
        dialog.float_format = self.dataModel.get_format_spec()
        dialog.varying_background = self.dataModel.bgcolor_enabled
        dialog.global_algo = not self.dataModel.colum_avg_enabled

        # Show dialog and allow user to interact
        result = dialog.exec_()

        # If user clicked 'OK' then set new options accordingly
        if result == QDialog.Accepted:
            float_format = dialog.float_format
            try:
                format(1.1, float_format)
            except:
                msg = _("Format ({}) is incorrect").format(float_format)
                QMessageBox.critical(self, _("Error"), msg)
            else:
                self.dataModel.set_format_spec(float_format)
                self.set_conf('dataframe_format', float_format)

            self.dataModel.bgcolor(dialog.varying_background)
            if dialog.varying_background:
                self.dataModel.colum_avg(not dialog.global_algo)

    def refresh_editor(self) -> None:
        """
        Refresh data in editor.
        """
        assert self.data_function is not None

        if self.btn_save_and_close.isEnabled():
            if not self.ask_for_refresh_confirmation():
                return

        try:
            data = self.data_function()
        except (IndexError, KeyError):
            self.error(_('The variable no longer exists.'))
            return

        if not self.set_data_and_check(data):
            self.error(
                _('The new value cannot be displayed in the dataframe '
                  'editor.')
            )

    def ask_for_refresh_confirmation(self) -> bool:
        """
        Ask user to confirm refreshing the editor.

        This function is to be called if refreshing the editor would overwrite
        changes that the user made previously. The function returns True if
        the user confirms that they want to refresh and False otherwise.
        """
        message = _('Refreshing the editor will overwrite the changes that '
                    'you made. Do you want to proceed?')
        result = QMessageBox.question(
            self,
            _('Refresh dataframe editor?'),
            message
        )
        return result == QMessageBox.Yes

    def error(self, message):
        """An error occurred, closing the dialog box"""
        QMessageBox.critical(self, _("Dataframe editor"), message)
        self.reject()

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
        self.table_header.resizeColumnsToContents()
        column_count = self.table_header.model().columnCount()
        for index in range(0, column_count):
            if index < column_count:
                column_width = self.dataTable.columnWidth(index)
                header_width = self.table_header.columnWidth(index)
                if column_width > header_width:
                    self.table_header.setColumnWidth(index, column_width)
                else:
                    self.dataTable.setColumnWidth(index, header_width)
            else:
                break

    def _sort_update(self):
        """
        Update the model for all the QTableView objects.

        Uses the model of the dataTable as the base.
        """
        # Update index list calculation
        self.dataModel.recalculate_index()
        self.setModel(self.dataTable.model())

    def _reload(self):
        """
        Reload the model for all the QTableView objects.

        Uses the model of the dataTable as the base.
        """
        # Update index list calculation and reload model
        self.dataModel.recalculate_index()
        self.dataModel.reset()
        self.setModel(self.dataTable.model())

    def _fetch_more_columns(self):
        """Fetch more data for the header (columns)."""
        self.table_header.model().fetch_more()

    def _fetch_more_rows(self):
        """Fetch more data for the index (rows)."""
        self.table_index.model().fetch_more()

    @Slot()
    def resize_to_contents(self):
        """"Resize columns to contents"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.dataTable.resizeColumnsToContents()
        self.dataModel.fetch_more(columns=True)
        self.dataTable.resizeColumnsToContents()
        self._update_header_size()
        QApplication.restoreOverrideCursor()


# ==============================================================================
# Tests
# ==============================================================================
def test_edit(data, title="", parent=None):
    """Test subroutine"""
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

    if parse(pd.__version__) >= parse('2.0.0'):
        from pandas.testing import assert_frame_equal, assert_series_equal
    else:
        from pandas.util.testing import assert_frame_equal, assert_series_equal

    app = qapplication()                  # analysis:ignore

    df1 = pd.DataFrame(
        [
            [True, "bool"],
            [1+1j, "complex"],
            ['test', "string"],
            [1.11, "float"],
            [1, "int"],
            [np.random.rand(3, 3), "Unkown type"],
            ["Large value", 100],
            ["áéí", "unicode"]
        ],
        index=['a', 'b', nan, nan, nan, 'c', "Test global max", 'd'],
        columns=[nan, 'Type']
    )
    out = test_edit(df1)
    assert_frame_equal(df1, out)

    result = pd.Series([True, "bool"], index=[nan, 'Type'], name='a')
    out = test_edit(df1.iloc[0])
    assert_series_equal(result, out)

    df1 = pd.DataFrame(np.random.rand(100100, 10))
    out = test_edit(df1)
    assert_frame_equal(out, df1)

    series = pd.Series(np.arange(10), name=0)
    out = test_edit(series)
    assert_series_equal(series, out)


if __name__ == '__main__':
    test()

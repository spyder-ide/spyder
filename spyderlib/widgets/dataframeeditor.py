# -*- coding: utf-8 -*-
#
# Copyright © 2014 Spyder development team
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

from spyderlib.qt.QtCore import (QAbstractTableModel, Qt, QModelIndex,
                                 SIGNAL, SLOT)
from spyderlib.qt.QtGui import (QDialog, QTableView, QColor, QGridLayout,
                                QDialogButtonBox, QHBoxLayout, QPushButton,
                                QCheckBox, QMessageBox, QInputDialog, QCursor,
                                QLineEdit, QApplication, QMenu, QKeySequence)
from spyderlib.qt.compat import to_qvariant, from_qvariant
from spyderlib.utils.qthelpers import (qapplication, get_icon, create_action,
                                       add_actions, keybinding)

from spyderlib.baseconfig import _
from spyderlib.guiconfig import get_font, new_shortcut
from spyderlib.py3compat import io, is_text_string, to_text_string, PY2
from spyderlib.utils import encoding
from spyderlib.widgets.arrayeditor import get_idx_rect

from pandas import DataFrame, TimeSeries
import numpy as np

# Supported Numbers and complex numbers
_sup_nr = (float, int, np.int64, np.int32)
_sup_com = (complex, np.complex64, np.complex128)
# Used to convert bool intrance to false since bool('False') will return True
_bool_false = ['false', '0']


LARGE_SIZE = 5e5
LARGE_NROWS = 1e5
LARGE_COLS = 60


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
    max_col, min_col = zip(*col_vals)
    return max(max_col), min(min_col)


class DataFrameModel(QAbstractTableModel):
    """ DataFrame Table Model"""
    
    ROWS_TO_LOAD = 500
    COLS_TO_LOAD = 40
    
    def __init__(self, dataFrame, format="%.3g", parent=None):
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

        huerange = [.66, .99]  # Hue
        self.sat = .7  # Saturation
        self.val = 1.  # Value
        self.alp = .6  # Alpha-channel
        self.hue0 = huerange[0]
        self.dhue = huerange[1]-huerange[0]
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
        """Determines the maximum and minimum number in each column"""
        max_r = self.df.max(numeric_only=True)
        min_r = self.df.min(numeric_only=True)
        self.max_min_col = list(zip(max_r, min_r))
        if len(self.max_min_col) != self.df.shape[1]:
            # Then it contain complex numbers or other types
            float_intran = self.df.applymap(lambda e: isinstance(e, _sup_nr))
            self.complex_intran = self.df.applymap(lambda e:
                                                   isinstance(e, _sup_com))
            mask = float_intran & (~ self.complex_intran)
            try:
                df_abs = self.df[self.complex_intran].abs()
            except TypeError:
                df_abs = self.df[self.complex_intran]
            max_c = df_abs.max(skipna=True)
            min_c = df_abs.min(skipna=True)
            df_real = self.df[mask]
            max_r = df_real.max(skipna=True)
            min_r = df_real.min(skipna=True)
            self.max_min_col = list(zip(DataFrame([max_c,
                                                   max_r]).max(skipna=True),
                                        DataFrame([min_c,
                                                   min_r]).min(skipna=True)))
        self.max_min_col = [[vmax, vmin-1] if vmax == vmin else [vmax, vmin]
                            for vmax, vmin in self.max_min_col]

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
                # Get rid of possible BOM utf-8 data present at the
                # beginning of a file, which gets attached to the first
                # column header when headers are present in the first
                # row.
                # Fixes Issue 2514
                try:
                    header = to_text_string(self.df_header[0],
                                            encoding='utf-8-sig')
                except:
                    header = to_text_string(self.df_header[0])
                return to_qvariant(header)
            else:
                return to_qvariant(to_text_string(self.df_header[section-1]))
        else:
            return to_qvariant()

    def get_bgcolor(self, index):
        """Background color depending on value"""
        column = index.column()
        if column == 0:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.8)
            return color
        if not self.bgcolor_enabled:
            return
        value = self.get_value(index.row(), column-1)
        if isinstance(value, _sup_com):
            color_func = abs
        else:
            color_func = float
        if isinstance(value, _sup_nr+_sup_com) and self.bgcolor_enabled:
            vmax, vmin = self.return_max(self.max_min_col, column-1)
            hue = self.hue0 + self.dhue*(vmax-color_func(value)) / (vmax-vmin)
            hue = float(abs(hue))
            color = QColor.fromHsvF(hue, self.sat, self.val, self.alp)
        elif is_text_string(value):
            color = QColor(Qt.lightGray)
            color.setAlphaF(.05)
        else:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.3)
        return color

    def get_value(self, row, column):
        """Returns the value of the DataFrame"""
        # To increase the performance iat is used but that requires error
        # handling, so fallback uses iloc
        try:
            value = self.df.iat[row, column]
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
                return to_qvariant(to_text_string(self.df_index[row]))
            else:
                value = self.get_value(row, column-1)
                if isinstance(value, float):
                    return to_qvariant(self._format % value)
                else:
                    try:
                        return to_qvariant(to_text_string(value))
                    except UnicodeDecodeError:
                        return to_qvariant(encoding.to_unicode(value))
        elif role == Qt.BackgroundColorRole:
            return to_qvariant(self.get_bgcolor(index))
        elif role == Qt.FontRole:
            return to_qvariant(get_font('arrayeditor'))
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
            if column > 0:
                self.df.sort(columns=self.df.columns[column-1],
                             ascending=order, inplace=True)
                self.update_df_index()
            else:
                self.df.sort_index(inplace=True, ascending=order)
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
            if isinstance(current_value, bool):
                val = bool_false_check(val)
            if isinstance(current_value, ((bool,) + _sup_nr + _sup_com)) or \
               is_text_string(current_value):
                try:
                    self.df.iloc[row, column-1] = current_value.__class__(val)
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
        # This is done to implement timeseries
        if len(self.df.shape) == 1:
            return 2
        elif self.total_cols <= self.cols_loaded:
            return self.total_cols + 1
        else:
            return self.cols_loaded + 1


class DataFrameView(QTableView):
    """Data Frame view class"""
    def __init__(self, parent, model):
        QTableView.__init__(self, parent)
        self.setModel(model)

        self.sort_old = [None]
        self.header_class = self.horizontalHeader()
        self.connect(self.header_class,
                     SIGNAL("sectionClicked(int)"), self.sortByColumn)
        self.menu = self.setup_menu()
        new_shortcut(QKeySequence.Copy, self, self.copy)
        self.connect(self.horizontalScrollBar(), SIGNAL("valueChanged(int)"),
                     lambda val: self.load_more_data(val, columns=True))
        self.connect(self.verticalScrollBar(), SIGNAL("valueChanged(int)"),
                     lambda val: self.load_more_data(val, rows=True))
    
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
        copy_action = create_action(self, _( "Copy"),
                                    shortcut=keybinding("Copy"),
                                    icon=get_icon('editcopy.png'),
                                    triggered=self.copy,
                                    context=Qt.WidgetShortcut)
        functions = ((_("To bool"), bool), (_("To complex"), complex),
                     (_("To int"), int), (_("To float"), float),
                     (_("To str"), to_text_string))
        types_in_menu = [copy_action]
        for name, func in functions:
            types_in_menu += [create_action(self, name,
                                            triggered=lambda func=func:
                                                      self.change_type(func),
                                            context=Qt.WidgetShortcut)]
        menu = QMenu(self)
        add_actions(menu, types_in_menu)
        return menu

    def change_type(self, func):
        """A function that changes types of cells"""
        model = self.model()
        index_list = self.selectedIndexes()
        [model.setData(i, '', change_type=func) for i in index_list]

    def copy(self):
        """Copy text to clipboard"""
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
            contents = output.getvalue()
            output.close()
        clipboard = QApplication.clipboard()
        clipboard.setText(contents)


class DataFrameEditor(QDialog):
    """ Data Frame Editor Dialog """
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.is_time_series = False
        self.layout = None

    def setup_and_check(self, data, title=''):
        """
        Setup DataFrameEditor:
        return False if data is not supported, True otherwise
        """
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.setWindowIcon(get_icon('arredit.png'))
        if title:
            title = to_text_string(title) + " - %s" % data.__class__.__name__
        else:
            title = _("%s editor") % data.__class__.__name__
        if isinstance(data, TimeSeries):
            self.is_time_series = True
            data = data.to_frame()

        self.setWindowTitle(title)
        self.resize(600, 500)

        self.dataModel = DataFrameModel(data, parent=self)
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
        self.connect(btn, SIGNAL("clicked()"), self.change_format)
        btn = QPushButton(_('Resize'))
        btn_layout.addWidget(btn)
        self.connect(btn, SIGNAL("clicked()"), self.resize_to_contents)

        bgcolor = QCheckBox(_('Background color'))
        bgcolor.setChecked(self.dataModel.bgcolor_enabled)
        bgcolor.setEnabled(self.dataModel.bgcolor_enabled)
        self.connect(bgcolor, SIGNAL("stateChanged(int)"),
                     self.change_bgcolor_enable)
        btn_layout.addWidget(bgcolor)

        self.bgcolor_global = QCheckBox(_('Column min/max'))
        self.bgcolor_global.setChecked(self.dataModel.colum_avg_enabled)
        self.bgcolor_global.setEnabled(not self.is_time_series and
                                       self.dataModel.bgcolor_enabled)
        self.connect(self.bgcolor_global, SIGNAL("stateChanged(int)"),
                     self.dataModel.colum_avg)
        btn_layout.addWidget(self.bgcolor_global)

        btn_layout.addStretch()
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        btn_layout.addWidget(bbox)

        self.layout.addLayout(btn_layout, 2, 0)

        return True

    def change_bgcolor_enable(self, state):
        """
        This is implementet so column min/max is only active when bgcolor is
        """
        self.dataModel.bgcolor(state)
        self.bgcolor_global.setEnabled(not self.is_time_series and state > 0)

    def change_format(self):
        """Change display format"""
        format, valid = QInputDialog.getText(self, _('Format'),
                                             _("Float formatting"),
                                             QLineEdit.Normal,
                                             self.dataModel.get_format())
        if valid:
            format = str(format)
            try:
                format % 1.1
            except:
                QMessageBox.critical(self, _("Error"),
                                     _("Format (%s) is incorrect") % format)
                return
            self.dataModel.set_format(format)

    def get_value(self):
        """Return modified Dataframe -- this is *not* a copy"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        df = self.dataModel.get_data()
        if self.is_time_series:
            return df.iloc[:, 0]
        else:
            return df

    def resize_to_contents(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.dataTable.resizeColumnsToContents()
        self.dataModel.fetch_more(columns=True)
        self.dataTable.resizeColumnsToContents()
        QApplication.restoreOverrideCursor()


def test_edit(data, title="", parent=None):
    """Test subroutine"""
    dlg = DataFrameEditor(parent=parent)
    if dlg.setup_and_check(data, title=title) and dlg.exec_():
        return dlg.get_value()
    else:
        import sys
        sys.exit()


def test():
    """DataFrame editor test"""
    from numpy import nan

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
    print("out:", out)
    out = test_edit(df1.iloc[0])
    print("out:", out)
    df1 = DataFrame(np.random.rand(100001, 10))
    # Sorting large DataFrame takes time
    df1.sort(columns=[0, 1], inplace=True)
    out = test_edit(df1)
    print("out:", out)
    out = test_edit(TimeSeries(np.arange(10)))
    print("out:", out)
    return out


if __name__ == '__main__':
    _app = qapplication()
    df = test()

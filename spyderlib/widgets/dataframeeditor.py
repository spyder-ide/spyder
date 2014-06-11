# -*- coding: utf-8 -*-
#
# Copyright © 2014 Daniel Høegh
# Licensed under the terms of the MIT License
"""
Pandas DataFrame Editor Dialog based on Qt
"""

from spyderlib.qt.QtCore import (QAbstractTableModel, Qt, QModelIndex,
                                 SIGNAL, SLOT)
from spyderlib.qt.QtGui import (QDialog, QTableView, QColor, QGridLayout,
                                QDialogButtonBox, QHBoxLayout, QPushButton,
                                QCheckBox, QMessageBox, QInputDialog,
                                QLineEdit, QApplication, QMenu)

from spyderlib.baseconfig import _
from spyderlib.guiconfig import get_font
from spyderlib.qt.compat import to_qvariant, from_qvariant
from spyderlib.utils.qthelpers import (qapplication, get_icon, create_action,
                                       add_actions, keybinding)
from spyderlib.py3compat import io, to_text_string
from pandas import DataFrame, TimeSeries
import numpy as np

_sup_nr = (float, int, np.int64)
_sup_com = (complex, np.complex64, np.complex128)

def get_idx_rect(index_list):
    """Extract the boundaries from a list of indexes"""
    rows, cols = list(zip(*[(i.row(), i.column()) for i in index_list]))
    return ( min(rows), max(rows), min(cols), max(cols) )

class DataFrameModel(QAbstractTableModel):
    """
    Data model for a DataFrame class
    Based on the Class DataFrameModel from the pandas project.
    Present in pandas.sandbox.qtpandas in v0.13.1
    Copyright (c) 2011-2012, Lambda Foundry, Inc.
    and PyData Development Team All rights reserved
    """
    def __init__(self, dataFrame, format="%.3g", parent=None):
        QAbstractTableModel.__init__(self)
        self.dialog = parent
        self.df = dataFrame
        self.sat = .7  # Saturation
        self.val = 1.  # Value
        self.alp = .3  # Alpha-channel
        self._format = format
        self.bgcolor_enabled = True
        self.complex_intran = None

        huerange = [.66, .99] # Hue
        self.sat = .7 # Saturation
        self.val = 1. # Value
        self.alp = .6 # Alpha-channel
        self.hue0 = huerange[0]
        self.dhue = huerange[1]-huerange[0]
        self.float_cols = []
        self.float_cols_update()
        self.bool_false =['false','0']
    
    def float_cols_update(self):
        """Determines the maximum and minimum number in each column"""
        max_r = self.df.max(numeric_only=True)
        min_r = self.df.min(numeric_only=True)
        self.float_cols = zip(max_r, min_r)
        if len(self.float_cols)!=self.df.shape[1]:
            # Then it contain complex numbers or other types
            float_intran = self.df.applymap(lambda e: isinstance(e, _sup_nr))
            self.complex_intran = self.df.applymap(lambda e: isinstance(e, _sup_com))
            mask = float_intran & (~ self.complex_intran)
            df_abs=self.df[self.complex_intran].abs()
            max_c = df_abs.max(skipna=True)
            min_c = df_abs.min(skipna=True)
            df_real = self.df[mask]
            max_r = df_real.max(skipna=True)
            min_r = df_real.min(skipna=True)
            self.float_cols = zip(DataFrame([max_c,max_r]).max(skipna=True),DataFrame([min_c,min_r]).min(skipna=True))
        self.float_cols = [[vmax, vmin-1] if vmax == vmin else [vmax, vmin] for vmax, vmin in self.float_cols]
            
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
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header data"""
        if role != Qt.DisplayRole:
            return to_qvariant()

        if orientation == Qt.Horizontal:
            if section == 0:
                return 'Index'
            else:
                return to_qvariant(to_text_string(self.df.columns.tolist()\
                                                  [section-1]))
        else:
            return to_qvariant()

    def get_bgcolor(self, index):
        """Background color depending on value"""
        column = index.column()
        if column == 0:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.8)
            return color
        value = self.get_value(index.row(), column-1)
        if isinstance(value,_sup_com):
            color_func = abs
        else:
            color_func = float
        if isinstance(value, _sup_nr+_sup_com) and self.bgcolor_enabled:
            vmax, vmin = self.float_cols[column-1]
            hue = self.hue0+self.dhue*(vmax-color_func(value))/(vmax-vmin)
            hue = float(abs(hue))
            color = QColor.fromHsvF(hue, self.sat, self.val, self.alp)
        elif isinstance(value, basestring):
            color = QColor(Qt.lightGray)
            color.setAlphaF(.05)
        else:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.3)
        return color
        
    def get_value(self, row, column):
        """Returns the value of the DataFrame"""
        # To increase the performance iat is used but that requires error
        # handeling when index contains nan, so fallback uses iloc
        try:
            value = self.df.iat[row, column]
        except KeyError:
            value = self.df.iloc[row, column]
        return value
        
    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            column = index.column()
            row = index.row()
            if  column == 0:
                return to_qvariant(to_text_string(self.df.index.tolist()[row]))
            else:
                value = self.get_value(row, column-1)
                if isinstance(value, float):
                    return to_qvariant(self._format %value)
                else:
                    return to_qvariant(to_text_string(value))
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
                                     "TypeError error: no ordering "\
                                     "relation is defined for complex numbers")
                        
                return False
        try:
            if column > 0:
                self.df.sort(columns=self.df.columns[column-1], ascending=order,
                             inplace=True)
            else: 
                self.df.sort_index(inplace=True, ascending=order)
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
                            
    def bool_false_check(self, value):
        if value.lower() in self.bool_false:
            value = ''
        return value
        
    def setData(self, index, value,role=Qt.EditRole, change_type=None):
        """Cell content change"""
        column = index.column()        
        row = index.row()
        
        if change_type!=None:
            try:
                value = self.data(index, role=Qt.DisplayRole)
                val = from_qvariant(value, str)
                if change_type is bool:
                    val = self.bool_false_check(val)
                self.df.iloc[row, column - 1] = change_type(val)
            except ValueError:
                self.df.iloc[row, column - 1] = change_type('0')
        else:

            val = from_qvariant(value, str)
            current_value = self.get_value(row, column-1)
            if isinstance(current_value,bool):
                val = self.bool_false_check(val)
            if isinstance(current_value,((basestring, bool)+_sup_nr+_sup_com)):
                try:
                    self.df.iloc[row, column - 1] = current_value.__class__(val)
                    #it is faster but does not work if the row index contains nan
                    #self.df.set_value(row, col, value)
                except ValueError as e:
                    QMessageBox.critical(self.dialog, "Error",
                                         "Value error: %s" % str(e))
                    return False
            else:
                QMessageBox.critical(self.dialog, "Error",
                                 "The type of the cell is not a supported type")
            
                return False
        self.float_cols_update()    
        return True
        
    def get_data(self):
        """Return data"""
        return self.df

    def rowCount(self, index=QModelIndex()):
        """DataFrame row number"""
        return self.df.shape[0]

    def columnCount(self, index=QModelIndex()):
        """DataFrame column number"""
        shape = self.df.shape
        #this is done to implement timeseries
        if len(shape) == 1:
            return 2
        else:
            return shape[1]+1

class DataFrameView(QTableView):
    """Array view class"""
    def __init__(self, parent, model):
        QTableView.__init__(self, parent)
        self.setModel(model)
        
        self.sort_old = [None]
        self.header_class=self.horizontalHeader()
        self.connect(self.header_class,
                     SIGNAL("sectionClicked(int)"), self.sortByColumn)
        
        self.menu = self.setup_menu()
        
    def sortByColumn(self,index):
        """ Implement a Column sort """
        if self.sort_old == [None]:
            self.header_class.setSortIndicatorShown(True)
        sort_order=self.header_class.sortIndicatorOrder() 
        if not self.model().sort(index,sort_order):
            if len(self.sort_old)!=2:
                self.header_class.setSortIndicatorShown(False)
            else:
                self.header_class.setSortIndicator(self.sort_old[0],self.sort_old[1])
            return
        self.sort_old=[index, self.header_class.sortIndicatorOrder()]

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
        functions = (("To bool",bool),("To complex",complex),("To int",int),("To float",float),
                     ("To str",str),("To unicode",unicode))
        types_in_menu = [copy_action , None]
        for name, func in functions:
    
            types_in_menu += [create_action(self, _(name),
                                             triggered=lambda func=func: self.change_type(func),
                                             context=Qt.WidgetShortcut)]
                                        
        menu = QMenu(self)
        add_actions(menu, types_in_menu)
        return menu
        
    def change_type(self, func):
        """A function that changes types of cells"""
        model = self.model()
        index_list=self.selectedIndexes()
        [model.setData(i,'',change_type=func) for i in index_list]
     
    def copy(self, index=False, header=False):
        """Copy text to clipboard"""
        row_min, row_max, col_min, col_max = get_idx_rect(self.selectedIndexes())
        if col_min == 0:
            col_min=1
            index = True
        df = self.model().df
        if col_max == 0: # To copy indices
            contents = '\n'.join(map(str,df.index.tolist()[slice(row_min, row_max+1)]))
        else: # To copy DataFrame
            if df.shape[0]==row_max+1 and row_min==0:
                header = True
            obj = df.iloc[slice(row_min, row_max+1),slice(col_min-1, col_max)]
            
            output = io.StringIO()
            obj.to_csv(output, sep='\t', index=index, header=header)
            contents = output.getvalue()
            output.close()
        clipboard = QApplication.clipboard()
        clipboard.setText(contents)

class DataFrameEditor(QDialog):
    ''' a simple widget for using DataFrames in a gui '''
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.is_time_series = False
        self.layout = None

    def setup_and_check(self, dataFrame, title=''):
        """
        Setup DataFrameEditor:
        return False if data is not supported, True otherwise
        """
        if isinstance(dataFrame, TimeSeries):
            self.is_time_series = True
            dataFrame = dataFrame.to_frame()
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.setWindowIcon(get_icon('arredit.png'))
        if title:
            title = to_text_string(title) # in case title is not a string
        else:
            title = _("Data Frame editor")
        self.setWindowTitle(title)
        self.resize(600, 500)

        self.dataModel = DataFrameModel(dataFrame, parent=self)
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
        self.connect(btn, SIGNAL("clicked()"), 
                     self.dataTable.resizeColumnsToContents)
        
        bgcolor = QCheckBox(_('Background color'))
        bgcolor.setChecked(self.dataModel.bgcolor_enabled)
        bgcolor.setEnabled(self.dataModel.bgcolor_enabled)
        self.connect(bgcolor, SIGNAL("stateChanged(int)"),
                     self.dataModel.bgcolor)
        btn_layout.addWidget(bgcolor)
        btn_layout.addStretch()
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        btn_layout.addWidget(bbox)
        
        self.layout.addLayout(btn_layout, 2, 0)
        
        return True
        
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
    
    df1 = DataFrame([[True, "bool"],
                     [1+1j, "complex"],
                     ['test', "string"],
                     [1.11, "float"],
                     [1, "int"],
                     [np.random.rand(3,3), "Unkown type"]],
                     index=['a', 'b', nan, nan, nan,'c'],
                     columns=[nan, 'Type'])         
    out = test_edit(df1)
    print("out:", out)
    out = test_edit(df1.iloc[0])
    print("out:", out)
    df1 = DataFrame(np.random.rand(1000,10))
    df1.sort(columns=[0,1],inplace=True)
    out = test_edit(df1)
    print("out:", out)
    out = test_edit(TimeSeries(range(10)))
    print("out:", out)
    return out

if __name__ == '__main__':
    _app = qapplication()
    df = test()


# -*- coding: utf-8 -*-
#
# Copyright © 2014 Daniel Høegh
# Licensed under the terms of the MIT License
"""
Pandas DataFrame Editor Dialog based on Qt
"""

from spyderlib.qt.QtCore import (QAbstractTableModel, Qt, QModelIndex, SIGNAL,
                                 SLOT)
from spyderlib.qt.QtGui import (QDialog, QTableView, QColor, QGridLayout,
                                QDialogButtonBox, QHBoxLayout, QPushButton,
                                QCheckBox, QMessageBox, QInputDialog, QLineEdit)
from spyderlib.qt.compat import to_qvariant, from_qvariant
from spyderlib.utils.qthelpers import qapplication, get_icon
from spyderlib.py3compat import to_text_string
from pandas import DataFrame, TimeSeries


class DataFrameModel(QAbstractTableModel):
    """
    Data model for a DataFrame class
    Based on the Class DataFrameModel from the pandas project.
    Present in pandas.sandbox.qtpandas in v0.13.1
    Copyright (c) 2011-2012, Lambda Foundry, Inc.
    and PyData Development Team All rights reserved
    """
    def __init__(self, dataFrame, format="%.3g"):
        super(DataFrameModel, self).__init__()
        self.df = dataFrame
        self.sat = .7  # Saturation
        self.val = 1.  # Value
        self.alp = .3  # Alpha-channel
        self._format = format
        self.bgcolor_enabled = True
        self.signalUpdate()
        
        huerange = [.66, .99] # Hue
        self.sat = .7 # Saturation
        self.val = 1. # Value
        self.alp = .6 # Alpha-channel
        self.hue0 = huerange[0]
        self.dhue = huerange[1]-huerange[0]
        self.float_cols = []
        self.float_cols_update()
    
    def float_cols_update(self):
        float_intran = self.df.apply(lambda row : [ not isinstance(e, basestring) for e in row ],axis=1)
        self.float_cols = zip(self.df[float_intran].max(), self.df[float_intran].min())
        
        
    def signalUpdate(self):
        ''' tell viewers to update their data (this is full update, not
        efficient)'''
        self.layoutChanged.emit()
    
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
        if role != Qt.DisplayRole:
            return to_qvariant()

        if orientation == Qt.Horizontal:
            if section == 0:
                return 'Index'
            else:
                return to_qvariant(to_text_string(self.df.columns.tolist()[section-1]))
        else:
            return to_qvariant()

    def get_bgcolor(self, index):
        """Background color depending on value"""
        column = index.column()
        if column == 0:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.8)
            return color
        value = self.df.iloc[index.row(), column-1]
        if not isinstance(value,basestring) and self.bgcolor_enabled:
            vmax, vmin = self.float_cols[column-1]
            hue = self.hue0+\
                  self.dhue*(vmax-value)\
                  /(vmax-vmin)
            hue = float(abs(hue))
            color = QColor.fromHsvF(hue, self.sat, self.val, self.alp)
        else:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.05)
        return color

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            column = index.column()
            row = index.row()
            if  column == 0:
                return to_qvariant(to_text_string(self.df.index.tolist()[row]))
            else:
                value = self.df.iloc[row,column-1]
                if isinstance(value, float):
                    return to_qvariant(self._format %value)
                else:
                    return to_qvariant(to_text_string(value))
        elif role == Qt.BackgroundColorRole:
            return to_qvariant(self.get_bgcolor(index))
        return to_qvariant()
    
    def sort(self, column, order=Qt.AscendingOrder):
        """Overriding sort method"""
        
        if column > 0:
            self.df.sort(columns=self.df.columns[column-1], ascending=order, inplace=True)
        else: 
            self.df.sort_index(inplace=True, ascending=order)
        self.reset()
        
    def flags(self, index):
        if index.column() == 0:
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index) |
                            Qt.ItemIsEditable)

    def setData(self, index, value, role=Qt.EditRole):
        column = index.column()        
        row = index.row()
        value = from_qvariant(value, str)
        try:
            value = float(value)
            if value.is_integer():
                value = int(value)
        except ValueError:
            value = unicode(value)
        self.df.iloc[row, column - 1] = value
        #it is faster but does not work if the row index contains nan
        #self.df.set_value(row, col, value)
        self.float_cols_update()    
        return True
        
    def get_data(self):
        """Return data"""
        return self.df

    def rowCount(self, index=QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QModelIndex()):
        shape = self.df.shape
        #this is done to implement timeseries
        if len(shape) == 1:
            return 2
        else:
            return shape[1]+1


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
        elif isinstance(dataFrame, DataFrame):
            pass
        else:
            return False
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.setWindowIcon(get_icon('arredit.png'))
        if title:
            title = unicode(title)  # in case title is not a string
        else:
            title = "Data Frame editor"
        self.setWindowTitle(title)
        self.resize(600, 500)

        self.dataModel = DataFrameModel(dataFrame)
        self.dataTable = QTableView()
        self.dataTable.setModel(self.dataModel)
        self.dataTable.resizeColumnsToContents()
        
        self.layout.addWidget(self.dataTable)
        self.setLayout(self.layout)
        self.setMinimumSize(400, 300)
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        btn_layout = QHBoxLayout()
        
        btn = QPushButton("Format")
        # disable format button for int type
        btn_layout.addWidget(btn)
        self.connect(btn, SIGNAL("clicked()"), self.change_format)
        btn = QPushButton('Resize')
        btn_layout.addWidget(btn)
        self.connect(btn, SIGNAL("clicked()"), self.dataTable.resizeColumnsToContents)
        
        bgcolor = QCheckBox('Background color')
        bgcolor.setChecked(self.dataModel.bgcolor_enabled)
        bgcolor.setEnabled(self.dataModel.bgcolor_enabled)
        self.connect(bgcolor, SIGNAL("stateChanged(int)"), self.dataModel.bgcolor)
        btn_layout.addWidget(bgcolor)
        btn_layout.addStretch()
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        btn_layout.addWidget(bbox)
        
        self.layout.addLayout(btn_layout, 2, 0)
        
        self.connect(self.dataTable.horizontalHeader(),SIGNAL("sectionClicked(int)"), self.sortByColumn)
        
        return True
        
    def change_format(self):
        """Change display format"""
        format, valid = QInputDialog.getText(self, 'Format',
                                 "Float formatting",
                                 QLineEdit.Normal, self.dataModel.get_format())
        if valid:
            format = str(format)
            try:
                format % 1.1
            except:
                QMessageBox.critical(self, ("Error"),
                                     ("Format (%s) is incorrect") % format)
                return
            self.dataModel.set_format(format)    
            
    def sortByColumn(self,index):
        self.dataTable.setSortingEnabled(True)
        
    def get_value(self):
        """Return modified Dataframe -- this is *not* a copy"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        df = self.dataModel.get_data()
        if self.is_time_series:
            return df.ix[:, df.columns[0]]
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
    df1 = DataFrame([[1, 'test'], [1, 'test'], [1, 'test'], [1, 'test']],
                    index=['a', 'b', nan, nan], columns=['a', 'b'])
    out = test_edit(df1)
    print("out:", out)
    out = test_edit(df1['a'])
    print("out:", out)
    df1 = DataFrame([[2, 'two'], [1, 'one'], [3, 'test'], [4, 'test']])
    df1.sort(columns=[0,1],inplace=True)
    out = test_edit(df1)
    print("out:", out)
    out = test_edit(TimeSeries(range(10)))
    print("out:", out)
    return out

if __name__ == '__main__':
    _app = qapplication()
    df = test()

# -*- coding: utf-8 -*-
"""
pandas DataFrame Editor Dialog based on Qt
"""

# Or if you use PyQt4:
from spyderlib.qt.QtCore import (QAbstractTableModel, Qt, QModelIndex, SIGNAL,
                                 SLOT)
from spyderlib.qt.QtGui import (QDialog, QTableView, QColor, QGridLayout,
                                QDialogButtonBox, QHBoxLayout)
from spyderlib.qt.compat import to_qvariant, from_qvariant
from spyderlib.utils.qthelpers import qapplication, get_icon
from spyderlib.widgets.dicteditorutils import get_color_name
from numpy import int64
from pandas import DataFrame, TimeSeries

class DataFrameModel(QAbstractTableModel):
    ''' data model for a DataFrame class '''
    def __init__(self, dataFrame):
        super(DataFrameModel, self).__init__()
        self.df = dataFrame
        self.sat = .7  # Saturation
        self.val = 1.  # Value
        self.alp = .3  # Alpha-channel
        self.signalUpdate()
        
    def signalUpdate(self):
        ''' tell viewers to update their data (this is full update, not
        efficient)'''
        self.layoutChanged.emit()

    #------------- table display functions -----------------
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return to_qvariant()

        if orientation == Qt.Horizontal:
            if section == 0:
                return 'Index'
            else:
                return to_qvariant(str(self.df.columns.tolist()[section-1]))
        else:
            return to_qvariant()
        
    def get_bgcolor(self, index):
        """Background color depending on value"""
        if index.column() == 0:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.05)
        else:
            value = self.df.ix[index.row(), index.column()-1]
            color = QColor(get_color_name(value))
            color.setAlphaF(self.alp)
        return color
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if index.column() == 0:
                return to_qvariant(str(self.df.index.tolist()[index.row()]))
            else:
                return to_qvariant(str(self.df.ix[index.row(),
                                                  index.column()-1]))
        elif role == Qt.BackgroundColorRole:
            return to_qvariant(self.get_bgcolor(index))
        return to_qvariant()

    def flags(self, index):
        if index.column() == 0:
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                            Qt.ItemIsEditable)

    def setData(self, index, value, role=Qt.EditRole):
        #row = self.df.index[index.row()]
        value = from_qvariant(value, str)
        if isinstance(self.df.ix[index.row(), index.column()-1],
                      (long, int, int64, float, unicode, str)):
                try:
                    value = float(value)
                except ValueError:
                    value = unicode(value)
                self.df.ix[index.row(), index.column()-1] = value
                #it is faster but does not work if the row index contains nan
                #self.df.set_value(row, col, value)
                return True
        else:
            return False
        

    def get_data(self):
        """Return data"""
        return self.df

    def rowCount(self, index=QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QModelIndex()):
         shape=self.df.shape
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
            dataFrame=dataFrame.to_frame()
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
        # Set DataFrame
        
        self.setMinimumSize(400, 300)
         # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        btn_layout = QHBoxLayout()
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        
        btn_layout.addWidget(bbox)
        self.layout.addLayout(btn_layout, 2, 0)
        return True
        
    def get_value(self):
        """Return modified Dataframe -- this is *not* a copy"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        df=self.dataModel.get_data()
        if self.is_time_series:
            return df.ix[:,df.columns[0]]
        else:
            return df


def test_edit(data, title="", parent=None, is_time_series=False):
    """Test subroutine"""
    dlg = DataFrameEditor(parent=parent)
    if dlg.setup_and_check(data, title=title) and dlg.exec_():
        return dlg.get_value()
    else:
        import sys
        sys.exit()


def test():
    from numpy import nan
    df1 = DataFrame([[1, 'test'], [1, 'test'], [1, 'test'], [1, 'test']],
                    index=['a', 'b', nan, nan], columns=['a', 'b'])
    out = test_edit(df1)
    print("out:", out)
    out = test_edit(df1['a'])
    print("out:", out)
    df1 = DataFrame([[1, 'test'], [1, 'test'], [1, 'test'], [1, 'test']])
    print("out:", test_edit(df1))
    out = test_edit(TimeSeries(range(10)))
    print("out:", out)
    return out
    
if __name__ == '__main__':
    _app = qapplication()
    df = test()

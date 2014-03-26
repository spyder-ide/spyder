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
from spyderlib.utils.qthelpers import qapplication
from spyderlib.widgets.dicteditorutils import get_color_name
from numpy import int64


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
                return 'row'
            try:
                return self.df.columns.tolist()[section-1]
            except (IndexError, ):
                return to_qvariant()
        else:
            return to_qvariant()
        return to_qvariant()
        
    def get_bgcolor(self, index):
        """Background color depending on value"""
        value = self.df.ix[index.row(), index.column()-1]
        if index.column() == 0:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.05)
        else:
            color = QColor(get_color_name(value))
            color.setAlphaF(self.alp)
        return color
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole:
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

    def setData(self, index, value, role):
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
        return self.df.shape[1]+1


class DataFrameEditor(QDialog):
    ''' a simple widget for using DataFrames in a gui '''
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.data = None
        self.arraywidget = None
        self.stack = None
        self.layout = None
    
    def setup_and_check(self, dataFrame, title=''):
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        # self.setWindowIcon(get_icon('arredit.png'))
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
        return self.dataModel.get_data()


def test_edit(data, title="", parent=None):
    """Test subroutine"""
    dlg = DataFrameEditor(parent)
    if dlg.setup_and_check(data) and dlg.exec_():
        return dlg.get_value()
    else:
        import sys
        sys.exit()


def test():
    from pandas import DataFrame
    from numpy import nan
    df1 = DataFrame([[1, 'test'], [1, 'test'], [1, 'test'], [1, 'test']],
                    index=['a', 'b', nan, nan], columns=['a', 'b'])
    out = test_edit(df1)
    print ("out:", out)
    return out
    
if __name__ == '__main__':
    _app = qapplication()
    df = test()

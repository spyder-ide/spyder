# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
NumPy Array Editor Dialog based on PyQt4
"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtCore import Qt, QVariant, QModelIndex, QAbstractTableModel
from PyQt4.QtCore import SIGNAL, SLOT
from PyQt4.QtGui import (QHBoxLayout, QColor, QTableView, QItemDelegate,
                         QLineEdit, QCheckBox, QGridLayout, QDoubleValidator,
                         QDialog, QDialogButtonBox, QMessageBox, QPushButton,
                         QInputDialog, QMenu, QApplication, QKeySequence)
import numpy as N
import StringIO

# Local import
from spyderlib.config import get_icon, get_font
from spyderlib.qthelpers import translate, add_actions, create_action, keybinding


def is_float(dtype):
    """Return True if datatype dtype is a float kind"""
    return ('float' in dtype.name) or dtype.name in ['single', 'double']

def is_number(dtype):
    """Return True is datatype dtype is a number kind"""
    return is_float(dtype) or ('int' in dtype.name) or ('long' in dtype.name) \
           or ('short' in dtype.name)

def get_idx_rect(index_list):
    """Extract the boundaries from a list of indexes"""
    rows, cols = zip(*[(i.row(),i.column()) for i in index_list])
    return ( min(rows), max(rows), min(cols), max(cols) )


class ArrayModel(QAbstractTableModel):
    """Array Editor Table Model"""
    def __init__(self, data, changes,
                 format="%.3f", xy_mode=False, readonly=False, parent=None):
        super(ArrayModel, self).__init__()

        self.dialog = parent
        self.changes = changes
        self.readonly = readonly
        self.test_array = N.array([0], dtype=data.dtype)

        # Backgroundcolor settings
        huerange = [.66, .99] # Hue
        self.sat = .7 # Saturation
        self.val = 1. # Value
        self.alp = .6 # Alpha-channel

        self._data = data
        self._format = format
        self._xy = xy_mode
        
        self.vmin = data.min()
        self.vmax = data.max()
        if self.vmax == self.vmin:
            self.vmin -= 1
        self.hue0 = huerange[0]
        self.dhue = huerange[1] - huerange[0]
        
        self.bgcolor_enabled = True
        
    def get_format(self):
        """Return current format"""
        # Avoid accessing the private attribute _format from outside
        return self._format
    
    def get_data(self):
        """Return data"""
        return self._data
    
    def set_format(self, format):
        """Change display format"""
        self._format = format
        self.reset()

    def columnCount(self, qindex=QModelIndex()):
        """Array column number"""
        return self._data.shape[1]

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
        return self._data.shape[0]

    def bgcolor(self, state):
        """Toggle backgroundcolor"""
        self.bgcolor_enabled = state > 0
        self.reset()

    def get_value(self, index):
        i = index.row()
        j = index.column()
        return self.changes.get((i, j), self._data[i, j])

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return QVariant()
        value = self.get_value(index)
        if role == Qt.DisplayRole:
            return QVariant( self._format % value )
        elif role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignCenter|Qt.AlignVCenter))
        elif role == Qt.BackgroundColorRole and self.bgcolor_enabled:
            hue = self.hue0+self.dhue*(self.vmax-value)/(self.vmax-self.vmin)
            color = QColor.fromHsvF(hue, self.sat, self.val, self.alp)
            return QVariant(color)
        elif role == Qt.FontRole:
            return QVariant(get_font('arrayeditor'))
        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        """Cell content change"""
        if not index.isValid() or self.readonly:
            return False
        i = index.row()
        j = index.column()
        value = str(value.toString())
        if self._data.dtype.name == "bool":
            try:
                val = bool(float(value))
            except ValueError:
                val = value.lower() == "true"
        else:
            try:
                val = float(value)
            except ValueError, e:
                QMessageBox.critical(self.dialog, "Error",
                                     "Value error: %s" % e.message)
        try:
            self.test_array[0] = val # will raise an Exception eventually
        except OverflowError, e:
            print type(e.message)
            QMessageBox.critical(self.dialog, "Error",
                                 "Overflow error: %s" % e.message)
            return False
        
        # Add change to self.changes
        self.changes[(i, j)] = val
        self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                  index, index)
        if val > self.vmax:
            self.vmax = val
        if val < self.vmin:
            self.vmin = val
        return True
    
    def flags(self, index):
        """Set editable flag"""
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(QAbstractTableModel.flags(self, index)|
                            Qt.ItemIsEditable)
                
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header data"""
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return QVariant(int(section))
        else:
            if self._xy:
                if section == 0:
                    return QVariant('x')
                elif self.rowCount() == 2:
                    return QVariant('y')
                else:
                    return QVariant('y ('+str(section-1)+')')
            else:
                return QVariant(int(section))


class ArrayDelegate(QItemDelegate):
    """Array Editor Item Delegate"""
    def __init__(self, dtype, parent=None):
        super(ArrayDelegate, self).__init__(parent)
        self.dtype = dtype

    def createEditor(self, parent, option, index):
        """Create editor widget"""
        model = index.model()
        if model._data.dtype.name == "bool":
            value = not model.get_value(index)
            model.setData(index, QVariant(value))
            return
        else:
            editor = QLineEdit(parent)
            editor.setFont(get_font('arrayeditor'))
            editor.setAlignment(Qt.AlignCenter)
            if is_number(self.dtype):
                editor.setValidator( QDoubleValidator(editor) )
            self.connect(editor, SIGNAL("returnPressed()"),
                         self.commitAndCloseEditor)
            return editor

    def commitAndCloseEditor(self):
        """Commit and close editor"""
        editor = self.sender()
        self.emit(SIGNAL("commitData(QWidget*)"), editor)
        self.emit(SIGNAL("closeEditor(QWidget*)"), editor)

    def setEditorData(self, editor, index):
        """Set editor widget's data"""
        text = index.model().data(index, Qt.DisplayRole).toString()
        editor.setText( text )


#TODO: Implement "Paste" (from clipboard) feature
class ArrayView(QTableView):
    """Array view class"""
    def __init__(self,parent=None):
        super(ArrayView,self).__init__()
        self.menu = self.setup_menu()
    
    def setup_menu(self):
        """Setup context menu"""
        self.copy_action = create_action(self, translate("ArrayEditor", "Copy"),
                                         shortcut=keybinding("Copy"),
                                         icon=get_icon('editcopy.png'),
                                         triggered=self.copy,
                                         window_context=False)
        menu = QMenu(self)
        add_actions(menu, [self.copy_action,])
        return menu

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        self.menu.popup(event.globalPos())
        event.accept()
        
    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event == QKeySequence.Copy:
            self.copy()
            event.accept()
        else:
            QTableView.keyPressEvent(self, event)

    def _sel_to_text(self, cell_range):
        """Copy an array portion to a unicode string"""
        row_min, row_max, col_min, col_max = get_idx_rect(cell_range)
        _data = self.model().get_data()
        output = StringIO.StringIO()
        N.savetxt(output,
                  _data[row_min:row_max+1, col_min:col_max+1],
                  delimiter='\t')
        contents = output.getvalue()
        output.close()
        return contents
    
    def copy(self):
        """Copy text to clipboard"""
        cliptxt = self._sel_to_text( self.selectedIndexes() )
        clipboard = QApplication.clipboard()
        clipboard.setText(cliptxt)


class ArrayEditor(QDialog):
    """Array Editor Dialog"""
    FORMATS = {
               'single': '%.3f',
               'double': '%.3f',
               'float_': '%.3f',
               'float32': '%.3f',
               'float64': '%.3f',
               'float96': '%.3f',
               'int_': '%d',
               'int8': '%d',
               'int16': '%d',
               'int32': '%d',
               'int64': '%d',
               'uint': '%d',
               'uint8': '%d',
               'uint16': '%d',
               'uint32': '%d',
               'uint64': '%d',
               'bool': '%r'
               }
    
    def __init__(self, data, title='', xy=False, readonly=False):
        super(ArrayEditor, self).__init__()
        format = self.get_format(data)
        
        self.data = data
        self.changes = {}
        self.old_data_shape = None
        if len(self.data.shape)==1:
            self.old_data_shape = self.data.shape
            self.data.shape = (self.data.shape[0], 1)

        if len(self.data.shape)!=2:
            raise RuntimeError( "ArrayEditor doesn't support arrays"
                                " with more than 2 dimensions" )
        
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.setWindowIcon(get_icon('arredit.png'))
        title = self.tr("Array editor") + \
                "%s" % (" - "+str(title) if str(title) else "")
        if readonly:
            title += ' (' + self.tr('read only') + ')'
        self.setWindowTitle(title)
        self.resize(600, 500)

        # Table configuration
        self.view = ArrayView()
        self.model = ArrayModel(self.data, self.changes, format=format,
                                xy_mode=xy, readonly=readonly, parent=self)
        self.view.setModel(self.model)
        self.view.setItemDelegate(ArrayDelegate(data.dtype, self))
        total_width = 0
        for k in xrange(self.data.shape[1]):
            total_width += self.view.columnWidth(k)
        total_width = min(total_width, 1024)
        view_size = self.view.size()
        self.view.viewport().resize( total_width, view_size.height() )
        self.layout.addWidget(self.view, 0, 0)

        layout = QHBoxLayout()
        btn = QPushButton(self.tr("Format"))
        # disable format button for int type
        btn.setEnabled( is_float(data.dtype) )
        layout.addWidget( btn )
        self.connect(btn, SIGNAL("clicked()"), self.change_format )
        btn = QPushButton(self.tr("Resize"))
        layout.addWidget( btn )
        self.connect(btn, SIGNAL("clicked()"), self.resize_to_contents )
        bgcolor = QCheckBox(self.tr('Background color'))
        bgcolor.setChecked(True)
        self.connect(bgcolor, SIGNAL("stateChanged(int)"), self.model.bgcolor)
        layout.addWidget( bgcolor )
        
        # Buttons configuration
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel )
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        layout.addWidget(bbox)
        self.layout.addLayout(layout, 2, 0)
        
        self.setMinimumSize(400, 300)
        
        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)
        
    def accept(self):
        """Reimplement Qt method"""
        for (i, j), value in self.changes.iteritems():
            self.data[i, j] = value
        if self.old_data_shape:
            self.data.shape = self.old_data_shape
        QDialog.accept(self)

    def reject(self):
        """Reimplement Qt method"""
        if self.old_data_shape:
            self.data.shape = self.old_data_shape
        QDialog.reject(self)
        
    def get_format(self, data):
        """Return (type, format) depending on array dtype"""
        name = data.dtype.name
        try:
            return self.FORMATS[name]
        except KeyError:
            QMessageBox.warning(self, self.tr("Array editor"),
                self.tr("Warning: %1 arrays are currently not supported") \
                .arg(name))
            return '%.3f'

    def resize_to_contents(self):
        """Resize cells to contents"""
        self.view.resizeColumnsToContents()
        self.view.resizeRowsToContents()
        
    def change_format(self):
        """Change display format"""
        format, valid = QInputDialog.getText(self, self.tr('Format'),
                          self.tr("Float formatting"), QLineEdit.Normal,
                          self.model.get_format())
        if valid:
            format = str(format)
            try:
                format % 1.1
            except:
                QMessageBox.critical(self, self.tr("Error"),
                      self.tr("Format (%1) is incorrect").arg(format))
                return
            self.model.set_format(format)
    
    
def aedit(data, title=""):
    """
    Edit the array 'data' with the ArrayEditor and return the edited copy
    (if Cancel is pressed, return None)
    (instantiate a new QApplication if necessary,
    so it can be called directly from the interpreter)
    """
    if QApplication.startingUp():
        QApplication([])
    dialog = ArrayEditor(data, title)
    if dialog.exec_():
        return data

if __name__ == "__main__":
    arr = N.random.rand(5, 5)
    print "out:", aedit(arr, "float array")
    arr_in = N.array([True, False, True])
    print "in:", arr_in
    arr_out = aedit(arr_in, "bool array")
    print "out:", arr_out
    print arr_in is arr_out
    arr = N.array([1, 2, 3], dtype="int8")
    print "out:", aedit(arr, "int array")

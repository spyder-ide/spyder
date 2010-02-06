# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Text data Importing Wizard based on PyQt4
"""

from PyQt4.QtCore import (Qt, QVariant, QModelIndex, QAbstractTableModel,
                          SIGNAL, SLOT, QString, pyqtSignature)
from PyQt4.QtGui import (QTableView, QVBoxLayout, QHBoxLayout, QGridLayout,
                         QWidget,QDialog, QTextEdit, QTabWidget, QPushButton,
                         QLabel, QSpacerItem, QSizePolicy, QCheckBox, QColor,
                         QRadioButton, QLineEdit, QFrame, QMenu, QIntValidator,
                         QGroupBox, QMessageBox)

from functools import partial as ft_partial

# Local import
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import translate, add_actions, create_action

def try_to_parse(value):
    _types = ('int', 'float')
    for _t in _types:
        try:
            _val = eval("%s('%s')" % (_t, value))
            return _val
        except ValueError:
            pass
    return value

def try_to_eval(value):
    try:
        return eval(value)
    except (NameError, SyntaxError, ImportError):
        return value

#----Numpy arrays support
class FakeObject(object):
    """Fake class used in replacement of missing modules"""
    pass
try:
    from numpy import ndarray, array
except ImportError:
    class ndarray(FakeObject):
        """Fake ndarray"""
        pass

#----date and datetime objects support
import datetime
try:
    from dateutil.parser import parse as dateparse
except ImportError:
    from string import atoi
    def dateparse(datestr, dayfirst=True):
        """Just for 'day/month/year' strings"""
        _a, _b, _c = map(atoi, datestr.split('/'))
        if dayfirst:
            return datetime.datetime(_c, _b, _a)
        return datetime.datetime(_c, _a, _b)

def datestr_to_datetime(value, dayfirst=True):
    return dateparse(value, dayfirst=dayfirst)

#----Background colors for supported types 
COLORS = {
          bool: Qt.magenta,
          (int, float, long): Qt.blue,
          list: Qt.yellow,
          dict: Qt.cyan,
          tuple: Qt.lightGray,
          (str, unicode): Qt.darkRed,
          ndarray: Qt.green,
          datetime.date: Qt.darkYellow,
          }

def get_color(value, alpha):
    """Return color depending on value type"""
    color = QColor()
    for typ in COLORS:
        if isinstance(value, typ):
            color = QColor(COLORS[typ])
    color.setAlphaF(alpha)
    return color

class ContentsWidget(QWidget):
    """Import wizard contents widget"""
    def __init__(self, parent, text):
        QWidget.__init__(self, parent)
        
        self.text_editor = QTextEdit(self)
        self.text_editor.setText(text)
        self.text_editor.setReadOnly(True)
        
        # Type frame
        type_layout = QHBoxLayout()
        type_label = QLabel(translate("ImportWizard", "Import as"))
        type_layout.addWidget(type_label)
        data_btn = QRadioButton(translate("ImportWizard", "data"))
        data_btn.setChecked(True)
        self._as_data= True
        type_layout.addWidget(data_btn)
        code_btn = QRadioButton(translate("ImportWizard", "code"))
        self._as_code = False
        type_layout.addWidget(code_btn)        
        txt_btn = QRadioButton(translate("ImportWizard", "text"))
        type_layout.addWidget(txt_btn)
        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        type_layout.addItem(h_spacer)        
        type_frame = QFrame()
        type_frame.setLayout(type_layout)
        
        # Opts frame
        grid_layout = QGridLayout()
        grid_layout.setSpacing(0)
        
        col_label = QLabel(translate("ImportWizard", "Column separator:"))
        grid_layout.addWidget(col_label, 0, 0)
        col_w = QWidget()
        col_btn_layout = QHBoxLayout()
        self.tab_btn = QRadioButton(translate("ImportWizard", "Tab"))
        self.tab_btn.setChecked(True)
        col_btn_layout.addWidget(self.tab_btn)
        other_btn_col = QRadioButton(translate("ImportWizard", "other"))
        col_btn_layout.addWidget(other_btn_col)
        col_w.setLayout(col_btn_layout)
        grid_layout.addWidget(col_w, 0, 1)
        self.line_edt = QLineEdit(",")
        self.line_edt.setMaximumWidth(30)
        self.line_edt.setEnabled(False)
        self.connect(other_btn_col, SIGNAL("toggled(bool)"),
                     self.line_edt, SLOT("setEnabled(bool)"))
        grid_layout.addWidget(self.line_edt, 0, 2)

        row_label = QLabel(translate("ImportWizard", "Row separator:"))
        grid_layout.addWidget(row_label, 1, 0)
        row_w = QWidget()
        row_btn_layout = QHBoxLayout()
        self.eol_btn = QRadioButton(translate("ImportWizard", "EOL"))
        self.eol_btn.setChecked(True)
        row_btn_layout.addWidget(self.eol_btn)
        other_btn_row = QRadioButton(translate("ImportWizard", "other"))
        row_btn_layout.addWidget(other_btn_row)
        row_w.setLayout(row_btn_layout)
        grid_layout.addWidget(row_w, 1, 1)
        self.line_edt_row = QLineEdit(";")
        self.line_edt_row.setMaximumWidth(30)
        self.line_edt_row.setEnabled(False)
        self.connect(other_btn_row, SIGNAL("toggled(bool)"),
                     self.line_edt_row, SLOT("setEnabled(bool)"))
        grid_layout.addWidget(self.line_edt_row, 1, 2)

        grid_layout.setRowMinimumHeight(2, 15)
        
        other_group = QGroupBox(translate("ImportWizard",
                                            "Additionnal options"))
        other_layout = QGridLayout()
        other_group.setLayout(other_layout)

        skiprows_label = QLabel(translate("ImportWizard", "Skip rows:"))
        other_layout.addWidget(skiprows_label, 0, 0)
        self.skiprows_edt = QLineEdit('0')
        self.skiprows_edt.setMaximumWidth(30)
        intvalid = QIntValidator(0, len(unicode(text).splitlines()),
                                 self.skiprows_edt)
        self.skiprows_edt.setValidator(intvalid)
        other_layout.addWidget(self.skiprows_edt, 0, 1)
        
        other_layout.setColumnMinimumWidth(2, 5)
        
        comments_label = QLabel(translate("ImportWizard", "Comments:"))
        other_layout.addWidget(comments_label, 0, 3)
        self.comments_edt = QLineEdit('#')
        self.comments_edt.setMaximumWidth(30)
        other_layout.addWidget(self.comments_edt, 0, 4)
        
        self.trnsp_box = QCheckBox(translate("ImportWizard", "Transpose"))
        #self.trnsp_box.setEnabled(False)
        other_layout.addWidget(self.trnsp_box, 1, 0, 2, 0)
        
        grid_layout.addWidget(other_group, 3, 0, 2, 0)
        
        opts_frame = QFrame()
        opts_frame.setLayout(grid_layout)
        
        self.connect(data_btn, SIGNAL("toggled(bool)"),
                     opts_frame, SLOT("setEnabled(bool)"))
        self.connect(data_btn, SIGNAL("toggled(bool)"),
                     self, SLOT("set_as_data(bool)"))
        self.connect(code_btn, SIGNAL("toggled(bool)"),
                     self, SLOT("set_as_code(bool)"))
#        self.connect(txt_btn, SIGNAL("toggled(bool)"),
#                     self, SLOT("is_text(bool)"))

        # Final layout
        layout = QVBoxLayout()
        layout.addWidget(type_frame)
        layout.addWidget(self.text_editor)
        layout.addWidget(opts_frame)
        self.setLayout(layout)

    def get_as_data(self):
        """Return if data type conversion"""
        return self._as_data
    
    def get_as_code(self):
        """Return if code type conversion"""
        return self._as_code
    
    def get_as_num(self):
        """Return if numeric type conversion"""
        return self._as_num

    def get_col_sep(self):
        """Return the column separator"""
        if self.tab_btn.isChecked():
            return u"\t"
        return unicode(self.line_edt.text())
    
    def get_row_sep(self):
        """Return the row separator"""
        if self.eol_btn.isChecked():
            return u"\n"
        return unicode(self.line_edt_row.text())
    
    def get_skiprows(self):
        """Return number of lines to be skipped"""
        return int(unicode(self.skiprows_edt.text()))
    
    def get_comments(self):
        """Return comment string"""
        return unicode(self.comments_edt.text())

    @pyqtSignature("bool")
    def set_as_data(self, as_data):
        """Set if data type conversion"""
        self._as_data = as_data
        self.emit(SIGNAL("asDataChanged(bool)"), as_data)

    @pyqtSignature("bool")
    def set_as_code(self, as_code):
        """Set if code type conversion"""
        self._as_code = as_code

class PreviewTableModel(QAbstractTableModel):
    """Import wizard preview table model"""
    def __init__(self, data=[], parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        """Return row count"""
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()):
        """Return column count"""
        return len(self._data[0])

    def _display_data(self, index):
        """Return a data element"""
        return QVariant(self._data[index.row()][index.column()])
    
    def data(self, index, role=Qt.DisplayRole):
        """Return a model data element"""
        if not index.isValid():
            return QVariant()
        if role == Qt.DisplayRole:
            return self._display_data(index)
        elif role == Qt.BackgroundColorRole:
            return QVariant(get_color(self._data[index.row()][index.column()], .2))            
        elif role == Qt.TextAlignmentRole:
            return QVariant(int(Qt.AlignRight|Qt.AlignVCenter))
        return QVariant()
    
    def setData(self, index, value, role=Qt.EditRole):
        """Set model data"""
        return False

    def get_data(self):
        """Return a copy of model data"""
        return self._data[:][:]

    def parse_data_type(self, index, **kwargs):
        """Parse a type to an other type"""
        if not index.isValid():
            return False
        try:
            if kwargs['atype'] == "date":
                self._data[index.row()][index.column()] = \
                    datestr_to_datetime(self._data[index.row()][index.column()],
                                    kwargs['dayfirst']).date()
            elif kwargs['atype'] == "perc":
                _tmp = self._data[index.row()][index.column()].replace("%", "")
                self._data[index.row()][index.column()] = eval(_tmp)/100.
            elif kwargs['atype'] == "account":
                _tmp = self._data[index.row()][index.column()].replace(",", "")
                self._data[index.row()][index.column()] = eval(_tmp)
            elif kwargs['atype'] == "unicode":
                self._data[index.row()][index.column()] = unicode(
                    self._data[index.row()][index.column()])
            elif kwargs['atype'] == "int":
                self._data[index.row()][index.column()] = int(
                    self._data[index.row()][index.column()])
            elif kwargs['atype'] == "float":
                self._data[index.row()][index.column()] = float(
                    self._data[index.row()][index.column()])                
            self.emit(SIGNAL("dataChanged(QModelIndex,QModelIndex)"), index, index)
        except Exception, instance:
            print instance

class PreviewTable(QTableView):
    """Import wizard preview widget"""
    def __init__(self, parent):
        QTableView.__init__(self, parent)
        self._model = None

        # Setting up actions
        self.date_dayfirst_action = create_action(self, "dayfirst",
            triggered=ft_partial(self.parse_to_type, atype="date", dayfirst=True))
        self.date_monthfirst_action = create_action(self,"monthfirst",
            triggered=ft_partial(self.parse_to_type, atype="date", dayfirst=False))
        self.perc_action = create_action(self, "perc",
            triggered=ft_partial(self.parse_to_type, atype="perc"))
        self.acc_action = create_action(self, "account",
            triggered=ft_partial(self.parse_to_type, atype="account"))
        self.str_action = create_action(self, "unicode",
            triggered=ft_partial(self.parse_to_type, atype="unicode"))
        self.int_action = create_action(self, "int",
            triggered=ft_partial(self.parse_to_type, atype="int"))
        self.float_action = create_action(self,"float",
            triggered=ft_partial(self.parse_to_type, atype="float"))
        
        # Setting up menus
        self.date_menu = QMenu()
        self.date_menu.setTitle("Date")
        add_actions( self.date_menu, (self.date_dayfirst_action,
                                      self.date_monthfirst_action))
        self.parse_menu = QMenu(self)
        self.parse_menu.addMenu(self.date_menu)
        add_actions( self.parse_menu, (self.perc_action, self.acc_action))
        self.parse_menu.setTitle("String to")
        self.opt_menu = QMenu(self)
        self.opt_menu.addMenu(self.parse_menu)
        add_actions( self.opt_menu, (self.str_action, self.int_action,
                                     self.float_action))

    def _shape_text(self, text, colsep=u"\t", rowsep=u"\n", transpose=False,
                    skiprows=0, comments='#'):
        """Decode the shape of the given text"""
        assert colsep != rowsep
        out = []
        text_rows = map(None, text.split(rowsep))[skiprows:]
        for row in text_rows:
            stripped = unicode(row).strip()
            if len(stripped) == 0 or stripped.startswith(comments):
                continue
            line = QString(row).split(colsep)
            line = map(lambda x: try_to_parse(unicode(x)), line)
            out.append(line)
        if transpose:
            return [[r[col] for r in out] for col in range(len(out[0]))]
        return out
    
    def get_data(self):
        """Return model data"""
        if self._model is None:
            return None
        return self._model.get_data()

    def process_data(self, text, colsep=u"\t", rowsep=u"\n", transpose=False,
                     skiprows=0, comments='#'):
        """Put data into table model"""
        data = self._shape_text(text, colsep, rowsep, transpose, skiprows,
                                comments)
        self._model = PreviewTableModel(data)
        self.setModel(self._model)

    def parse_to_type(self,**kwargs):
        """Parse to a given type"""
        indexes = self.selectedIndexes()
        if not indexes: return
        for index in indexes:
            self.model().parse_data_type(index, **kwargs)
    
    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        self.opt_menu.popup(event.globalPos())
        event.accept()

class PreviewWidget(QWidget):
    """Import wizard preview widget"""
    
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        
        vert_layout = QVBoxLayout()
        
        hor_layout = QHBoxLayout()
        self.array_box = QCheckBox(translate("ImportWizard", "Import as array"))
        self.array_box.setEnabled(ndarray is not FakeObject)
        self.array_box.setChecked(ndarray is not FakeObject)
        hor_layout.addWidget(self.array_box)
        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)        
        hor_layout.addItem(h_spacer)
        
        self._table_view = PreviewTable(self)
        vert_layout.addLayout(hor_layout)
        vert_layout.addWidget(self._table_view)
        self.setLayout(vert_layout)

    def open_data(self, text, colsep=u"\t", rowsep=u"\n",
                  transpose=False, skiprows=0, comments='#'):
        """Open clipboard text as table"""
        self._table_view.process_data(text, colsep, rowsep, transpose,
                                      skiprows, comments)
    
    def get_data(self):
        """Return table data"""
        return self._table_view.get_data()

class ImportWizard(QDialog):
    """Text data import wizard"""
    def __init__(self, parent, text,
                 title=None, icon=None, contents_title=None, varname=None):
        QDialog.__init__(self, parent)
        
        if title is None:
            title = translate("ImportWizard", "Import wizard")
        self.setWindowTitle(title)
        if icon is None:
            self.setWindowIcon(get_icon("fileimport.png"))
        if contents_title is None:
            contents_title = translate("ImportWizard", "Raw text")
        
        if varname is None:
            varname = translate("ImportWizard", "variable_name")
        
        self.var_name, self.clip_data = None, None
        
        # Setting GUI
        self.tab_widget = QTabWidget(self)
        self.text_widget = ContentsWidget(self, text)
        self.table_widget = PreviewWidget(self)
        
        self.tab_widget.addTab(self.text_widget, translate("ImportWizard",
                                                           "text"))
        self.tab_widget.setTabText(0, contents_title)
        self.tab_widget.addTab(self.table_widget, translate("ImportWizard",
                                                            "table"))
        self.tab_widget.setTabText(1, translate("ImportWizard", "Preview"))
        self.tab_widget.setTabEnabled(1, False)
        
        name_layout = QHBoxLayout()
        name_h_spacer = QSpacerItem(40, 20, 
                                    QSizePolicy.Expanding, QSizePolicy.Minimum)
        name_layout.addItem(name_h_spacer)
        
        name_label = QLabel(translate("ImportWizard", "Name"))
        name_layout.addWidget(name_label)
        self.name_edt = QLineEdit()
        self.name_edt.setMaximumWidth(100)
        self.name_edt.setText(varname)
        name_layout.addWidget(self.name_edt)
        
        btns_layout = QHBoxLayout()
        cancel_btn = QPushButton(translate("ImportWizard", "Cancel"))
        btns_layout.addWidget(cancel_btn)
        self.connect(cancel_btn, SIGNAL("clicked()"), self, SLOT("reject()"))
        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        btns_layout.addItem(h_spacer)
        self.back_btn = QPushButton(translate("ImportWizard", "Previous"))
        self.back_btn.setEnabled(False)
        btns_layout.addWidget(self.back_btn)
        self.connect(self.back_btn, SIGNAL("clicked()"),
                     ft_partial(self._set_step, step=-1))
        self.fwd_btn = QPushButton(translate("ImportWizard", "Next"))
        btns_layout.addWidget(self.fwd_btn)
        self.connect(self.fwd_btn, SIGNAL("clicked()"),
                     ft_partial(self._set_step, step=1))
        self.done_btn = QPushButton(translate("ImportWizard", "Done"))
        self.done_btn.setEnabled(False)
        btns_layout.addWidget(self.done_btn)
        self.connect(self.done_btn, SIGNAL("clicked()"),
                     self, SLOT("process()"))
        
        self.connect(self.text_widget, SIGNAL("asDataChanged(bool)"),
                     self.fwd_btn, SLOT("setEnabled(bool)"))
        self.connect(self.text_widget, SIGNAL("asDataChanged(bool)"),
                     self.done_btn, SLOT("setDisabled(bool)"))
        layout = QVBoxLayout()
        layout.addLayout(name_layout)
        layout.addWidget(self.tab_widget)
        layout.addLayout(btns_layout)
        self.setLayout(layout)

    def _focus_tab(self, tab_idx):
        """Change tab focus"""
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, False)
        self.tab_widget.setTabEnabled(tab_idx, True)
        self.tab_widget.setCurrentIndex(tab_idx)
        
    def _set_step(self,step):
        """Proceed to a given step"""
        new_tab = self.tab_widget.currentIndex() + step
        assert new_tab < self.tab_widget.count() and new_tab >= 0
        if new_tab == self.tab_widget.count()-1:
            try:
                self.table_widget.open_data(self._get_plain_text(),
                                        self.text_widget.get_col_sep(),
                                        self.text_widget.get_row_sep(),
                                        self.text_widget.trnsp_box.isChecked(),
                                        self.text_widget.get_skiprows(),
                                        self.text_widget.get_comments())
                self.done_btn.setEnabled(True)
                self.done_btn.setDefault(True)
                self.fwd_btn.setEnabled(False)
                self.back_btn.setEnabled(True)
            except (SyntaxError, AssertionError), error:
                QMessageBox.critical(self,
                            translate("ImportWizard", "Import wizard"),
                            translate("ImportWizard",
                                      "<b>Unable to proceed to next step</b>"
                                      "<br><br>Please check your entries."
                                      "<br><br>Error message:<br>%2") \
                            .arg(str(error)))
                return
        elif new_tab == 0:
            self.done_btn.setEnabled(False)
            self.fwd_btn.setEnabled(True)
            self.back_btn.setEnabled(False)
        self._focus_tab(new_tab)
    
    def get_data(self):
        """Return processed data"""
        return self.var_name, self.clip_data

    def _simplify_shape(self, alist, rec=0):
        """Reduce the alist dimension if needed"""
        if rec != 0:
            if len(alist) == 1:
                return alist[-1]
            return alist
        if len(alist) == 1:
            return self._simplify_shape(alist[-1], 1)
        return map(lambda al: self._simplify_shape(al, 1), alist)

    def _get_table_data(self):
        """Return clipboard processed as data"""
        data = self._simplify_shape(
                self.table_widget.get_data())
        if self.table_widget.array_box.isChecked():
            return array(data)
        return data

    def _get_plain_text(self):
        """Return clipboard as text"""
        return self.text_widget.text_editor.toPlainText()

    @pyqtSignature("")
    def process(self):
        """Process the data from clipboard"""
        var_name = self.name_edt.text()
        try:
            self.var_name = str(var_name)
        except UnicodeEncodeError:
            self.var_name = unicode(var_name)
        if self.text_widget.get_as_data():
            self.clip_data = self._get_table_data()
        elif self.text_widget.get_as_code():
            self.clip_data = try_to_eval(
                unicode(self._get_plain_text()))
        else:
            self.clip_data = unicode(self._get_plain_text())
        self.accept()


def test(text):
    """Test"""
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()
    dialog = ImportWizard(None, text)
    if dialog.exec_():
        print dialog.get_data()

if __name__ == "__main__":
    test(QString(u"17/11/1976\t1.34\n14/05/09\t3.14"))

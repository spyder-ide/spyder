# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Text data Importing Wizard based on Qt
"""

# Standard library imports
from __future__ import print_function
from functools import partial as ft_partial

# Third party imports
from qtpy.compat import to_qvariant
from qtpy.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, Slot
from qtpy.QtGui import QColor, QIntValidator
from qtpy.QtWidgets import (QCheckBox, QDialog, QFrame, QGridLayout, QGroupBox,
                            QHBoxLayout, QLabel, QLineEdit,
                            QPushButton, QMenu, QMessageBox, QRadioButton,
                            QSizePolicy, QSpacerItem, QTableView, QTabWidget,
                            QTextEdit, QVBoxLayout, QWidget)

# If pandas fails to import here (for any reason), Spyder
# will crash at startup.
try:
    import pandas as pd
except:
    pd = None

# Local import
from spyder.config.base import _
from spyder.py3compat import (INT_TYPES, io, TEXT_TYPES, to_text_string,
                              zip_longest)
from spyder.utils import programs
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import add_actions, create_action


def try_to_parse(value):
    _types = ('int', 'float')
    for _t in _types:
        try:
            _val = eval("%s('%s')" % (_t, value))
            return _val
        except (ValueError, SyntaxError):
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
except:
    class ndarray(FakeObject):  # analysis:ignore
        """Fake ndarray"""
        pass

#----date and datetime objects support
import datetime
try:
    from dateutil.parser import parse as dateparse
except:
    def dateparse(datestr, dayfirst=True):  # analysis:ignore
        """Just for 'day/month/year' strings"""
        _a, _b, _c = list(map(int, datestr.split('/')))
        if dayfirst:
            return datetime.datetime(_c, _b, _a)
        return datetime.datetime(_c, _a, _b)

def datestr_to_datetime(value, dayfirst=True):
    return dateparse(value, dayfirst=dayfirst)

#----Background colors for supported types
COLORS = {
          bool: Qt.magenta,
          tuple([float] + list(INT_TYPES)): Qt.blue,
          list: Qt.yellow,
          set: Qt.darkGreen,
          dict: Qt.cyan,
          tuple: Qt.lightGray,
          TEXT_TYPES: Qt.darkRed,
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
    asDataChanged = Signal(bool)

    def __init__(self, parent, text):
        QWidget.__init__(self, parent)

        self.text_editor = QTextEdit(self)
        self.text_editor.setText(text)
        self.text_editor.setReadOnly(True)

        # Type frame
        type_layout = QHBoxLayout()
        type_label = QLabel(_("Import as"))
        type_layout.addWidget(type_label)
        data_btn = QRadioButton(_("data"))
        data_btn.setChecked(True)
        self._as_data= True
        type_layout.addWidget(data_btn)
        code_btn = QRadioButton(_("code"))
        self._as_code = False
        type_layout.addWidget(code_btn)
        txt_btn = QRadioButton(_("text"))
        type_layout.addWidget(txt_btn)

        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        type_layout.addItem(h_spacer)
        type_frame = QFrame()
        type_frame.setLayout(type_layout)

        # Opts frame
        grid_layout = QGridLayout()
        grid_layout.setSpacing(0)

        col_label = QLabel(_("Column separator:"))
        grid_layout.addWidget(col_label, 0, 0)
        col_w = QWidget()
        col_btn_layout = QHBoxLayout()
        self.tab_btn = QRadioButton(_("Tab"))
        self.tab_btn.setChecked(False)
        col_btn_layout.addWidget(self.tab_btn)
        self.ws_btn = QRadioButton(_("Whitespace"))
        self.ws_btn.setChecked(False)
        col_btn_layout.addWidget(self.ws_btn)
        other_btn_col = QRadioButton(_("other"))
        other_btn_col.setChecked(True)
        col_btn_layout.addWidget(other_btn_col)
        col_w.setLayout(col_btn_layout)
        grid_layout.addWidget(col_w, 0, 1)
        self.line_edt = QLineEdit(",")
        self.line_edt.setMaximumWidth(30)
        self.line_edt.setEnabled(True)
        other_btn_col.toggled.connect(self.line_edt.setEnabled)
        grid_layout.addWidget(self.line_edt, 0, 2)

        row_label = QLabel(_("Row separator:"))
        grid_layout.addWidget(row_label, 1, 0)
        row_w = QWidget()
        row_btn_layout = QHBoxLayout()
        self.eol_btn = QRadioButton(_("EOL"))
        self.eol_btn.setChecked(True)
        row_btn_layout.addWidget(self.eol_btn)
        other_btn_row = QRadioButton(_("other"))
        row_btn_layout.addWidget(other_btn_row)
        row_w.setLayout(row_btn_layout)
        grid_layout.addWidget(row_w, 1, 1)
        self.line_edt_row = QLineEdit(";")
        self.line_edt_row.setMaximumWidth(30)
        self.line_edt_row.setEnabled(False)
        other_btn_row.toggled.connect(self.line_edt_row.setEnabled)
        grid_layout.addWidget(self.line_edt_row, 1, 2)

        grid_layout.setRowMinimumHeight(2, 15)

        other_group = QGroupBox(_("Additional options"))
        other_layout = QGridLayout()
        other_group.setLayout(other_layout)

        skiprows_label = QLabel(_("Skip rows:"))
        other_layout.addWidget(skiprows_label, 0, 0)
        self.skiprows_edt = QLineEdit('0')
        self.skiprows_edt.setMaximumWidth(30)
        intvalid = QIntValidator(0, len(to_text_string(text).splitlines()),
                                 self.skiprows_edt)
        self.skiprows_edt.setValidator(intvalid)
        other_layout.addWidget(self.skiprows_edt, 0, 1)

        other_layout.setColumnMinimumWidth(2, 5)

        comments_label = QLabel(_("Comments:"))
        other_layout.addWidget(comments_label, 0, 3)
        self.comments_edt = QLineEdit('#')
        self.comments_edt.setMaximumWidth(30)
        other_layout.addWidget(self.comments_edt, 0, 4)

        self.trnsp_box = QCheckBox(_("Transpose"))
        #self.trnsp_box.setEnabled(False)
        other_layout.addWidget(self.trnsp_box, 1, 0, 2, 0)

        grid_layout.addWidget(other_group, 3, 0, 2, 0)

        opts_frame = QFrame()
        opts_frame.setLayout(grid_layout)

        data_btn.toggled.connect(opts_frame.setEnabled)
        data_btn.toggled.connect(self.set_as_data)
        code_btn.toggled.connect(self.set_as_code)
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
        elif self.ws_btn.isChecked():
            return None
        return to_text_string(self.line_edt.text())

    def get_row_sep(self):
        """Return the row separator"""
        if self.eol_btn.isChecked():
            return u"\n"
        return to_text_string(self.line_edt_row.text())

    def get_skiprows(self):
        """Return number of lines to be skipped"""
        return int(to_text_string(self.skiprows_edt.text()))

    def get_comments(self):
        """Return comment string"""
        return to_text_string(self.comments_edt.text())

    @Slot(bool)
    def set_as_data(self, as_data):
        """Set if data type conversion"""
        self._as_data = as_data
        self.asDataChanged.emit(as_data)

    @Slot(bool)
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
        return to_qvariant(self._data[index.row()][index.column()])

    def data(self, index, role=Qt.DisplayRole):
        """Return a model data element"""
        if not index.isValid():
            return to_qvariant()
        if role == Qt.DisplayRole:
            return self._display_data(index)
        elif role == Qt.BackgroundColorRole:
            return to_qvariant(get_color(self._data[index.row()][index.column()], .2))
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignRight|Qt.AlignVCenter))
        return to_qvariant()

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
                self._data[index.row()][index.column()] = to_text_string(
                    self._data[index.row()][index.column()])
            elif kwargs['atype'] == "int":
                self._data[index.row()][index.column()] = int(
                    self._data[index.row()][index.column()])
            elif kwargs['atype'] == "float":
                self._data[index.row()][index.column()] = float(
                    self._data[index.row()][index.column()])
            self.dataChanged.emit(index, index)
        except Exception as instance:
            print(instance)  # spyder: test-skip

    def reset(self):
        self.beginResetModel()
        self.endResetModel()

class PreviewTable(QTableView):
    """Import wizard preview widget"""
    def __init__(self, parent):
        QTableView.__init__(self, parent)
        self._model = None

        # Setting up actions
        self.date_dayfirst_action = create_action(self, "dayfirst",
            triggered=ft_partial(self.parse_to_type, atype="date", dayfirst=True))
        self.date_monthfirst_action = create_action(self, "monthfirst",
            triggered=ft_partial(self.parse_to_type, atype="date", dayfirst=False))
        self.perc_action = create_action(self, "perc",
            triggered=ft_partial(self.parse_to_type, atype="perc"))
        self.acc_action = create_action(self, "account",
            triggered=ft_partial(self.parse_to_type, atype="account"))
        self.str_action = create_action(self, "unicode",
            triggered=ft_partial(self.parse_to_type, atype="unicode"))
        self.int_action = create_action(self, "int",
            triggered=ft_partial(self.parse_to_type, atype="int"))
        self.float_action = create_action(self, "float",
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

    def _shape_text(self, text, colsep=u"\t", rowsep=u"\n",
                    transpose=False, skiprows=0, comments='#'):
        """Decode the shape of the given text"""
        assert colsep != rowsep
        out = []
        text_rows = text.split(rowsep)[skiprows:]
        for row in text_rows:
            stripped = to_text_string(row).strip()
            if len(stripped) == 0 or stripped.startswith(comments):
                continue
            line = to_text_string(row).split(colsep)
            line = [try_to_parse(to_text_string(x)) for x in line]
            out.append(line)
        # Replace missing elements with np.nan's or None's
        if programs.is_module_installed('numpy'):
            from numpy import nan
            out = list(zip_longest(*out, fillvalue=nan))
        else:
            out = list(zip_longest(*out, fillvalue=None))
        # Tranpose the last result to get the expected one
        out = [[r[col] for r in out] for col in range(len(out[0]))]
        if transpose:
            return [[r[col] for r in out] for col in range(len(out[0]))]
        return out

    def get_data(self):
        """Return model data"""
        if self._model is None:
            return None
        return self._model.get_data()

    def process_data(self, text, colsep=u"\t", rowsep=u"\n",
                     transpose=False, skiprows=0, comments='#'):
        """Put data into table model"""
        data = self._shape_text(text, colsep, rowsep, transpose, skiprows,
                                comments)
        self._model = PreviewTableModel(data)
        self.setModel(self._model)

    @Slot()
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

        # Type frame
        type_layout = QHBoxLayout()
        type_label = QLabel(_("Import as"))
        type_layout.addWidget(type_label)

        self.array_btn = array_btn = QRadioButton(_("array"))
        array_btn.setEnabled(ndarray is not FakeObject)
        array_btn.setChecked(ndarray is not FakeObject)
        type_layout.addWidget(array_btn)

        list_btn = QRadioButton(_("list"))
        list_btn.setChecked(not array_btn.isChecked())
        type_layout.addWidget(list_btn)

        if pd:
            self.df_btn = df_btn = QRadioButton(_("DataFrame"))
            df_btn.setChecked(False)
            type_layout.addWidget(df_btn)

        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        type_layout.addItem(h_spacer)
        type_frame = QFrame()
        type_frame.setLayout(type_layout)

        self._table_view = PreviewTable(self)
        vert_layout.addWidget(type_frame)
        vert_layout.addWidget(self._table_view)
        self.setLayout(vert_layout)

    def open_data(self, text, colsep=u"\t", rowsep=u"\n",
                  transpose=False, skiprows=0, comments='#'):
        """Open clipboard text as table"""
        if pd:
            self.pd_text = text
            self.pd_info = dict(sep=colsep, lineterminator=rowsep,
                skiprows=skiprows, comment=comments)
            if colsep is None:
                self.pd_info = dict(lineterminator=rowsep, skiprows=skiprows,
                    comment=comments, delim_whitespace=True)
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

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        if title is None:
            title = _("Import wizard")
        self.setWindowTitle(title)
        if icon is None:
            self.setWindowIcon(ima.icon('fileimport'))
        if contents_title is None:
            contents_title = _("Raw text")

        if varname is None:
            varname = _("variable_name")

        self.var_name, self.clip_data = None, None

        # Setting GUI
        self.tab_widget = QTabWidget(self)
        self.text_widget = ContentsWidget(self, text)
        self.table_widget = PreviewWidget(self)

        self.tab_widget.addTab(self.text_widget, _("text"))
        self.tab_widget.setTabText(0, contents_title)
        self.tab_widget.addTab(self.table_widget, _("table"))
        self.tab_widget.setTabText(1, _("Preview"))
        self.tab_widget.setTabEnabled(1, False)

        name_layout = QHBoxLayout()
        name_label = QLabel(_("Variable Name"))
        name_layout.addWidget(name_label)

        self.name_edt = QLineEdit()
        self.name_edt.setText(varname)
        name_layout.addWidget(self.name_edt)

        btns_layout = QHBoxLayout()
        cancel_btn = QPushButton(_("Cancel"))
        btns_layout.addWidget(cancel_btn)
        cancel_btn.clicked.connect(self.reject)
        h_spacer = QSpacerItem(40, 20,
                               QSizePolicy.Expanding, QSizePolicy.Minimum)
        btns_layout.addItem(h_spacer)
        self.back_btn = QPushButton(_("Previous"))
        self.back_btn.setEnabled(False)
        btns_layout.addWidget(self.back_btn)
        self.back_btn.clicked.connect(ft_partial(self._set_step, step=-1))
        self.fwd_btn = QPushButton(_("Next"))
        if not text:
            self.fwd_btn.setEnabled(False)
        btns_layout.addWidget(self.fwd_btn)
        self.fwd_btn.clicked.connect(ft_partial(self._set_step, step=1))
        self.done_btn = QPushButton(_("Done"))
        self.done_btn.setEnabled(False)
        btns_layout.addWidget(self.done_btn)
        self.done_btn.clicked.connect(self.process)

        self.text_widget.asDataChanged.connect(self.fwd_btn.setEnabled)
        self.text_widget.asDataChanged.connect(self.done_btn.setDisabled)
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

    def _set_step(self, step):
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
            except (SyntaxError, AssertionError) as error:
                QMessageBox.critical(self, _("Import wizard"),
                            _("<b>Unable to proceed to next step</b>"
                              "<br><br>Please check your entries."
                              "<br><br>Error message:<br>%s") % str(error))
                return
        elif new_tab == 0:
            self.done_btn.setEnabled(False)
            self.fwd_btn.setEnabled(True)
            self.back_btn.setEnabled(False)
        self._focus_tab(new_tab)

    def get_data(self):
        """Return processed data"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.var_name, self.clip_data

    def _simplify_shape(self, alist, rec=0):
        """Reduce the alist dimension if needed"""
        if rec != 0:
            if len(alist) == 1:
                return alist[-1]
            return alist
        if len(alist) == 1:
            return self._simplify_shape(alist[-1], 1)
        return [self._simplify_shape(al, 1) for al in alist]

    def _get_table_data(self):
        """Return clipboard processed as data"""
        data = self._simplify_shape(
                self.table_widget.get_data())
        if self.table_widget.array_btn.isChecked():
            return array(data)
        elif pd and self.table_widget.df_btn.isChecked():
            info = self.table_widget.pd_info
            buf = io.StringIO(self.table_widget.pd_text)
            return pd.read_csv(buf, **info)
        return data

    def _get_plain_text(self):
        """Return clipboard as text"""
        return self.text_widget.text_editor.toPlainText()

    @Slot()
    def process(self):
        """Process the data from clipboard"""
        var_name = self.name_edt.text()
        try:
            self.var_name = str(var_name)
        except UnicodeEncodeError:
            self.var_name = to_text_string(var_name)
        if self.text_widget.get_as_data():
            self.clip_data = self._get_table_data()
        elif self.text_widget.get_as_code():
            self.clip_data = try_to_eval(
                to_text_string(self._get_plain_text()))
        else:
            self.clip_data = to_text_string(self._get_plain_text())
        self.accept()


def test(text):
    """Test"""
    from spyder.utils.qthelpers import qapplication
    _app = qapplication()  # analysis:ignore
    dialog = ImportWizard(None, text)
    if dialog.exec_():
        print(dialog.get_data())  # spyder: test-skip

if __name__ == "__main__":
    test(u"17/11/1976\t1.34\n14/05/09\t3.14")

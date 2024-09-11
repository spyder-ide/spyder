# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
NumPy Array Editor Dialog based on Qt
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
from __future__ import annotations
import io
from typing import Callable, Optional, TYPE_CHECKING

# Third party imports
from qtpy.compat import from_qvariant, to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QItemSelection, QLocale,
                         QItemSelectionRange, QModelIndex, Qt, Slot)
from qtpy.QtGui import QColor, QCursor, QDoubleValidator, QKeySequence
from qtpy.QtWidgets import (
    QAbstractItemDelegate, QApplication, QDialog, QHBoxLayout, QInputDialog,
    QItemDelegate, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
    QStackedWidget, QStyle, QTableView, QToolButton, QVBoxLayout, QWidget)
from spyder_kernels.utils.nsview import value_to_display
from spyder_kernels.utils.lazymodules import numpy as np

if TYPE_CHECKING:
    from numpy.typing import ArrayLike

# Local imports
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.widgets.comboboxes import SpyderComboBox
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import _
from spyder.plugins.variableexplorer.widgets.basedialog import BaseDialog
from spyder.plugins.variableexplorer.widgets.preferences import (
    PreferencesDialog
)
from spyder.py3compat import (is_binary_string, is_string, is_text_string,
                              to_binary_string, to_text_string)
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import keybinding, safe_disconnect
from spyder.utils.stylesheet import AppStyle, MAC


# =============================================================================
# ---- Constants
# =============================================================================

class ArrayEditorActions:
    Copy = 'copy_action'
    Edit = 'edit_action'
    Preferences = 'preferences_action'
    Refresh = 'refresh_action'
    Resize = 'resize_action'


class ArrayEditorMenus:
    Options = 'options_menu'


class ArrayEditorWidgets:
    OptionsToolButton = 'options_button_widget'
    Toolbar = 'toolbar'
    ToolbarStretcher = 'toolbar_stretcher'


# Note: string and unicode data types will be formatted with '' (see below)
SUPPORTED_FORMATS = {
    'single': '.6g',
    'double': '.6g',
    'float_': '.6g',
    'longfloat': '.6g',
    'float16': '.6g',
    'float32': '.6g',
    'float64': '.6g',
    'float96': '.6g',
    'float128': '.6g',
    'csingle': '.6g',
    'complex_': '.6g',
    'clongfloat': '.6g',
    'complex64': '.6g',
    'complex128': '.6g',
    'complex192': '.6g',
    'complex256': '.6g',
    'byte': 'd',
    'bytes8': 's',
    'short': 'd',
    'intc': 'd',
    'int_': 'd',
    'longlong': 'd',
    'intp': 'd',
    'int8': 'd',
    'int16': 'd',
    'int32': 'd',
    'int64': 'd',
    'ubyte': 'd',
    'ushort': 'd',
    'uintc': 'd',
    'uint': 'd',
    'ulonglong': 'd',
    'uintp': 'd',
    'uint8': 'd',
    'uint16': 'd',
    'uint32': 'd',
    'uint64': 'd',
    'bool_': '',
    'bool8': '',
    'bool': '',
}


LARGE_SIZE = 5e5
LARGE_NROWS = 1e5
LARGE_COLS = 60

#==============================================================================
# ---- Utility functions
#==============================================================================

def is_float(dtype):
    """Return True if datatype dtype is a float kind"""
    return ('float' in dtype.name) or dtype.name in ['single', 'double']


def is_number(dtype):
    """Return True is datatype dtype is a number kind"""
    return is_float(dtype) or ('int' in dtype.name) or ('long' in dtype.name) \
           or ('short' in dtype.name)


def get_idx_rect(index_list):
    """Extract the boundaries from a list of indexes"""
    rows, cols = list(zip(*[(i.row(), i.column()) for i in index_list]))
    return ( min(rows), max(rows), min(cols), max(cols) )


#==============================================================================
# ---- Main classes
#==============================================================================

class ArrayModel(QAbstractTableModel, SpyderFontsMixin):
    """
    Array Editor Table Model

    Attributes
    ----------
    bgcolor_enabled : bool
        If True, vary backgrond color depending on cell value
    _format_spec : str
        Format specification for floats
    """

    ROWS_TO_LOAD = 500
    COLS_TO_LOAD = 40

    def __init__(self, data, format_spec=".6g", readonly=False, parent=None):
        QAbstractTableModel.__init__(self)

        self.dialog = parent
        self.changes = {}
        self.readonly = readonly
        self.test_array = np.array([0], dtype=data.dtype)

        # for complex numbers, shading will be based on absolute value
        # but for all other types it will be the real part
        if data.dtype in (np.complex64, np.complex128):
            self.color_func = np.abs
        else:
            self.color_func = np.real

        # Backgroundcolor settings
        huerange = [.66, .99] # Hue
        self.sat = .7 # Saturation
        self.val = 1. # Value
        self.alp = .6 # Alpha-channel

        self._data = data
        self._format_spec = format_spec

        self.total_rows = self._data.shape[0]
        self.total_cols = self._data.shape[1]
        size = self.total_rows * self.total_cols

        if not self._data.dtype.name == 'object':
            try:
                self.vmin = np.nanmin(self.color_func(data))
                self.vmax = np.nanmax(self.color_func(data))
                if self.vmax == self.vmin:
                    self.vmin -= 1
                self.hue0 = huerange[0]
                self.dhue = huerange[1]-huerange[0]
                self.bgcolor_enabled = True
            except (AttributeError, TypeError, ValueError):
                self.vmin = None
                self.vmax = None
                self.hue0 = None
                self.dhue = None
                self.bgcolor_enabled = False

        # Array with infinite values cannot display background colors and
        # crashes. See: spyder-ide/spyder#8093
        self.has_inf = False
        if data.dtype.kind in ['f', 'c']:
            self.has_inf = np.any(np.isinf(data))

        # Deactivate coloring for object arrays or arrays with inf values
        if self._data.dtype.name == 'object' or self.has_inf:
            self.bgcolor_enabled = False

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

    def get_data(self):
        """Return data"""
        return self._data

    def columnCount(self, qindex=QModelIndex()):
        """Array column number"""
        if self.total_cols <= self.cols_loaded:
            return self.total_cols
        else:
            return self.cols_loaded

    def rowCount(self, qindex=QModelIndex()):
        """Array row number"""
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

    def bgcolor(self, value: bool):
        """
        Set whether background color varies depending on cell value.
        """
        self.bgcolor_enabled = value
        self.reset()

    def get_value(self, index):
        i = index.row()
        j = index.column()
        if len(self._data.shape) == 1:
            value = self._data[j]
        else:
            value = self._data[i, j]
        return self.changes.get((i, j), value)

    def data(self, index, role=Qt.DisplayRole):
        """Cell content."""
        if not index.isValid():
            return to_qvariant()
        value = self.get_value(index)
        dtn = self._data.dtype.name

        # Tranform binary string to unicode so they are displayed
        # correctly
        if is_binary_string(value):
            try:
                value = to_text_string(value, 'utf8')
            except Exception:
                pass

        # Handle roles
        if role == Qt.DisplayRole:
            if value is np.ma.masked:
                return ''
            else:
                if dtn == 'object':
                    # We don't know what's inside an object array, so
                    # we can't trust value repr's here.
                    return value_to_display(value)
                else:
                    try:
                        format_spec = self._format_spec
                        return to_qvariant(format(value, format_spec))
                    except TypeError:
                        self.readonly = True
                        return repr(value)
        elif role == Qt.TextAlignmentRole:
            return to_qvariant(int(Qt.AlignCenter|Qt.AlignVCenter))
        elif (role == Qt.BackgroundColorRole and self.bgcolor_enabled
                and value is not np.ma.masked and not self.has_inf):
            try:
                hue = (self.hue0 +
                       self.dhue * (float(self.vmax) - self.color_func(value))
                       / (float(self.vmax) - self.vmin))
                hue = float(np.abs(hue))
                color = QColor.fromHsvF(hue, self.sat, self.val, self.alp)
                return to_qvariant(color)
            except (TypeError, ValueError):
                return to_qvariant()
        elif role == Qt.FontRole:
            return self.get_font(SpyderFontType.MonospaceInterface)
        return to_qvariant()

    def setData(self, index, value, role=Qt.EditRole):
        """Cell content change"""
        if not index.isValid() or self.readonly:
            return False
        i = index.row()
        j = index.column()
        value = from_qvariant(value, str)
        dtype = self._data.dtype.name
        if dtype == "bool":
            try:
                val = bool(float(value))
            except ValueError:
                val = value.lower() == "true"
        elif dtype.startswith("string") or dtype.startswith("bytes"):
            val = to_binary_string(value, 'utf8')
        elif dtype.startswith("unicode") or dtype.startswith("str"):
            val = to_text_string(value)
        else:
            if value.lower().startswith('e') or value.lower().endswith('e'):
                return False
            try:
                val = complex(value)
                if not val.imag:
                    val = val.real
            except ValueError as e:
                QMessageBox.critical(self.dialog, "Error",
                                     "Value error: %s" % str(e))
                return False
        try:
            self.test_array[0] = val  # will raise an Exception eventually
        except OverflowError as e:
            print("OverflowError: " + str(e))  # spyder: test-skip
            QMessageBox.critical(self.dialog, "Error",
                                 "Overflow error: %s" % str(e))
            return False

        # Add change to self.changes
        # Use self.test_array to convert to correct dtype
        self.changes[(i, j)] = self.test_array[0]
        self.dataChanged.emit(index, index)

        if not is_string(val):
            val = self.color_func(val)

            if val > self.vmax:
                self.vmax = val

            if val < self.vmin:
                self.vmin = val

        return True

    def flags(self, index):
        """Set editable flag"""
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        return (
            QAbstractTableModel.flags(self, index) | Qt.ItemFlag.ItemIsEditable
        )

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header data"""
        if role != Qt.DisplayRole:
            return to_qvariant()
        return to_qvariant(int(section))

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class ArrayDelegate(QItemDelegate, SpyderFontsMixin):
    """Array Editor Item Delegate"""
    def __init__(self, dtype, parent=None):
        QItemDelegate.__init__(self, parent)
        self.dtype = dtype

    def createEditor(self, parent, option, index):
        """Create editor widget"""
        model = index.model()
        value = model.get_value(index)
        if type(value) == np.ndarray or model.readonly:
            # The editor currently cannot properly handle this case
            return
        elif model._data.dtype.name == "bool":
            value = not value
            model.setData(index, to_qvariant(value))
            return
        elif value is not np.ma.masked:
            editor = QLineEdit(parent)
            editor.setFont(
                self.get_font(SpyderFontType.MonospaceInterface)
            )
            editor.setAlignment(Qt.AlignCenter)
            if is_number(self.dtype):
                validator = QDoubleValidator(editor)
                validator.setLocale(QLocale('C'))
                editor.setValidator(validator)
            editor.returnPressed.connect(self.commitAndCloseEditor)
            return editor

    def commitAndCloseEditor(self):
        """Commit and close editor"""
        editor = self.sender()
        # Avoid a segfault with PyQt5. Variable value won't be changed
        # but at least Spyder won't crash. It seems generated by a bug in sip.
        try:
            self.commitData.emit(editor)
        except AttributeError:
            pass
        self.closeEditor.emit(editor, QAbstractItemDelegate.NoHint)

    def setEditorData(self, editor, index):
        """Set editor widget's data"""
        text = from_qvariant(index.model().data(index, Qt.DisplayRole), str)
        editor.setText(text)


#TODO: Implement "Paste" (from clipboard) feature
class ArrayView(QTableView, SpyderWidgetMixin):
    """Array view class"""

    CONF_SECTION = 'variable_explorer'

    def __init__(self, parent, model, dtype, shape):
        QTableView.__init__(self, parent)

        self.setModel(model)
        self.setItemDelegate(ArrayDelegate(dtype, self))
        total_width = 0
        for k in range(shape[1]):
            total_width += self.columnWidth(k)
        self.viewport().resize(min(total_width, 1024), self.height())
        self.shape = shape
        self.menu = self.setup_menu()
        self.register_shortcut_for_widget(name='copy', triggered=self.copy)
        self.horizontalScrollBar().valueChanged.connect(
            self._load_more_columns
        )
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

        try:
            old_selection = self.selectionModel().selection()
            old_rows_loaded = old_cols_loaded = None

            if rows and value == self.verticalScrollBar().maximum():
                old_rows_loaded = self.model().rows_loaded
                self.model().fetch_more(rows=rows)

            if columns and value == self.horizontalScrollBar().maximum():
                old_cols_loaded = self.model().cols_loaded
                self.model().fetch_more(columns=columns)

            if old_rows_loaded is not None or old_cols_loaded is not None:
                # if we've changed anything, update selection
                new_selection = QItemSelection()
                for part in old_selection:
                    top = part.top()
                    bottom = part.bottom()
                    if (old_rows_loaded is not None and
                            top == 0 and bottom == (old_rows_loaded-1)):
                        # complete column selected (so expand it to match
                        # updated range)
                        bottom = self.model().rows_loaded-1
                    left = part.left()
                    right = part.right()
                    if (old_cols_loaded is not None
                            and left == 0 and right == (old_cols_loaded-1)):
                        # compete row selected (so expand it to match updated
                        # range)
                        right = self.model().cols_loaded-1
                    top_left = self.model().index(top, left)
                    bottom_right = self.model().index(bottom, right)
                    part = QItemSelectionRange(top_left, bottom_right)
                    new_selection.append(part)
                self.selectionModel().select(
                    new_selection, self.selectionModel().ClearAndSelect)
        except NameError:
            # Needed to handle a NameError while fetching data when closing
            # See isue 7880
            pass

    @Slot()
    def resize_to_contents(self):
        """Resize cells to contents"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.resizeColumnsToContents()
        self.model().fetch_more(columns=True)
        self.resizeColumnsToContents()
        QApplication.restoreOverrideCursor()

    def setup_menu(self):
        """Setup context menu"""
        self.copy_action = self.create_action(
            name=ArrayEditorActions.Copy,
            text=_('Copy'),
            icon=ima.icon('editcopy'),
            triggered=self.copy,
            register_action=False
        )
        self.copy_action.setShortcut(keybinding('Copy'))
        self.copy_action.setShortcutContext(Qt.WidgetShortcut)

        edit_action = self.create_action(
            name=ArrayEditorActions.Edit,
            text=_('Edit'),
            icon=ima.icon('edit'),
            triggered=self.edit_item,
            register_action=False
        )

        menu = self.create_menu('Editor menu', register=False)
        for action in [self.copy_action, edit_action]:
            self.add_item_to_menu(action, menu)

        return menu

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        self.menu.popup(event.globalPos())
        event.accept()

    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event == QKeySequence.Copy:
            self.copy()
        else:
            QTableView.keyPressEvent(self, event)

    def _sel_to_text(self, cell_range):
        """Copy an array portion to a unicode string"""
        if not cell_range:
            return
        row_min, row_max, col_min, col_max = get_idx_rect(cell_range)
        if col_min == 0 and col_max == (self.model().cols_loaded-1):
            # we've selected a whole column. It isn't possible to
            # select only the first part of a column without loading more,
            # so we can treat it as intentional and copy the whole thing
            col_max = self.model().total_cols-1
        if row_min == 0 and row_max == (self.model().rows_loaded-1):
            row_max = self.model().total_rows-1

        _data = self.model().get_data()
        output = io.BytesIO()
        try:
            fmt = '%' + self.model().get_format_spec()
            np.savetxt(output, _data[row_min:row_max+1, col_min:col_max+1],
                       delimiter='\t', fmt=fmt)
        except:
            QMessageBox.warning(self, _("Warning"),
                                _("It was not possible to copy values for "
                                  "this array"))
            return
        contents = output.getvalue().decode('utf-8')
        output.close()
        return contents

    @Slot()
    def copy(self):
        """Copy text to clipboard"""
        cliptxt = self._sel_to_text( self.selectedIndexes() )
        clipboard = QApplication.clipboard()
        clipboard.setText(cliptxt)

    def edit_item(self):
        """Edit item"""
        index = self.currentIndex()
        if index.isValid():
            self.edit(index)


class ArrayEditorWidget(QWidget):

    def __init__(self, parent, data, readonly=False):
        QWidget.__init__(self, parent)
        self.data = data
        self.old_data_shape = None
        if len(self.data.shape) == 1:
            self.old_data_shape = self.data.shape
            self.data.shape = (self.data.shape[0], 1)
        elif len(self.data.shape) == 0:
            self.old_data_shape = self.data.shape
            self.data.shape = (1, 1)

        # Use '' as default format specifier, because 's' does not produce
        # a `str` for arrays with strings, see spyder-ide/spyder#22466
        format_spec = SUPPORTED_FORMATS.get(data.dtype.name, '')

        self.model = ArrayModel(self.data, format_spec=format_spec,
                                readonly=readonly, parent=self)
        self.view = ArrayView(self, self.model, data.dtype, data.shape)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def accept_changes(self):
        """Accept changes"""
        for (i, j), value in list(self.model.changes.items()):
            self.data[i, j] = value
        if self.old_data_shape is not None:
            self.data.shape = self.old_data_shape

    def reject_changes(self):
        """Reject changes"""
        if self.old_data_shape is not None:
            self.data.shape = self.old_data_shape

    @Slot()
    def change_format(self):
        """Change display format"""
        format_spec, valid = QInputDialog.getText(self, _( 'Format'),
                                 _( "Float formatting"),
                                 QLineEdit.Normal, self.model.get_format_spec())
        if valid:
            format_spec = str(format_spec)
            try:
                format(1.1, format_spec)
            except:
                QMessageBox.critical(self, _("Error"),
                                     _("Format (%s) is incorrect") % format_spec)
                return
            self.model.set_format_spec(format_spec)


class ArrayEditor(BaseDialog, SpyderWidgetMixin):
    """Array Editor Dialog"""

    CONF_SECTION = 'variable_explorer'

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        data_function: Optional[Callable[[], ArrayLike]] = None
    ):
        """
        Constructor.

        Parameters
        ----------
        parent : Optional[QWidget]
            The parent widget. The default is None.
        data_function : Optional[Callable[[], ArrayLike]]
            A function which returns the current value of the array. This is
            used for refreshing the editor. If set to None, the editor cannot
            be refreshed. The default is None.
        """

        super().__init__(parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.data_function = data_function
        self.data = None
        self.arraywidget = None
        self.stack = None
        self.btn_save_and_close = None
        self.btn_close = None
        # Values for 3d array editor
        self.dim_indexes = [{}, {}, {}]
        self.last_dim = 0  # Adjust this for changing the startup dimension

    def setup_and_check(self, data, title='', readonly=False):
        """
        Setup the editor.

        It returns False if data is not supported, True otherwise.
        """
        self.setup_ui(title, readonly)
        return self.set_data_and_check(data, readonly)

    def setup_ui(self, title='', readonly=False):
        """
        Create the user interface.

        This creates the necessary widgets and layouts that make up the user
        interface of the array editor. Some elements need to be hidden
        depending on the data; this will be done when the data is set.
        """

        # ---- Actions

        def do_nothing():
            # .create_action() needs a toggled= parameter, but we can only
            # set it later in the set_data_and_check method, so we use this
            # function as a placeholder here.
            pass

        self.preferences_action = self.create_action(
            name=ArrayEditorActions.Preferences,
            icon=self.create_icon('configure'),
            text=_('Display options ...'),
            triggered=self.show_preferences_dialog,
            register_action=False
        )
        self.refresh_action = self.create_action(
            ArrayEditorActions.Refresh,
            text=_('Refresh'),
            icon=self.create_icon('refresh'),
            tip=_('Refresh editor with current value of variable in console'),
            triggered=self.refresh,
            register_action=False
        )
        self.refresh_action.setDisabled(self.data_function is None)
        self.resize_action = self.create_action(
            ArrayEditorActions.Resize,
            text=_('Resize'),
            icon=self.create_icon('collapse_column'),
            tip=_('Resize columns to contents'),
            triggered=do_nothing,
            register_action=False
        )

        # ---- Toolbar and options menu

        options_menu = self.create_menu(
            ArrayEditorMenus.Options,
            register=False
        )
        options_menu.add_action(self.preferences_action)

        options_button = self.create_toolbutton(
            name=ArrayEditorWidgets.OptionsToolButton,
            text=_('Options'),
            icon=ima.icon('tooloptions'),
            register=False
        )
        options_button.setPopupMode(QToolButton.InstantPopup)
        options_button.setMenu(options_menu)

        toolbar = self.create_toolbar(
            ArrayEditorWidgets.Toolbar,
            register=False
        )
        stretcher = self.create_stretcher(ArrayEditorWidgets.ToolbarStretcher)
        for item in [stretcher, self.resize_action, self.refresh_action,
                     options_button]:
            self.add_item_to_toolbar(item, toolbar)

        toolbar.render()

        # ---- Stack widget (empty)

        self.stack = QStackedWidget(self)
        self.stack.currentChanged.connect(self.current_widget_changed)

        # ---- Widgets in bottom left for special arrays
        #
        # These are normally hidden. When editing masked, record or 3d arrays,
        # the relevant elements are made visible in the set_data_and_check
        # method.

        self.btn_layout = QHBoxLayout()

        self.combo_label = QLabel()
        self.btn_layout.addWidget(self.combo_label)

        self.combo_box = SpyderComboBox(self)
        self.combo_box.currentIndexChanged.connect(self.combo_box_changed)
        self.btn_layout.addWidget(self.combo_box)

        self.shape_label = QLabel()
        self.btn_layout.addWidget(self.shape_label)

        self.index_label = QLabel(_('Index:'))
        self.btn_layout.addWidget(self.index_label)

        self.index_spin = QSpinBox(self, keyboardTracking=False)
        self.index_spin.valueChanged.connect(self.change_active_widget)
        self.btn_layout.addWidget(self.index_spin)

        self.slicing_label = QLabel()
        self.btn_layout.addWidget(self.slicing_label)

        self.masked_label = QLabel(
            _('<u>Warning</u>: Changes are applied separately')
        )
        self.masked_label.setToolTip(
            _("For performance reasons, changes applied to masked arrays "
              "won't be reflected in array's data (and vice-versa).")
        )
        self.btn_layout.addWidget(self.masked_label)

        self.btn_layout.addStretch()

        # ---- Push buttons on the bottom right

        self.btn_save_and_close = QPushButton(_('Save and Close'))
        self.btn_save_and_close.setDisabled(True)
        self.btn_save_and_close.clicked.connect(self.accept)
        self.btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_('Close'))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        self.btn_layout.addWidget(self.btn_close)

        # ---- Final layout

        layout = QVBoxLayout()
        layout.addWidget(toolbar)

        # Remove vertical space between toolbar and table containing array
        style = self.style()
        default_spacing = style.pixelMetric(QStyle.PM_LayoutVerticalSpacing)
        layout.addSpacing(-default_spacing)

        layout.addWidget(self.stack)
        layout.addSpacing((-1 if MAC else 2) * AppStyle.MarginSize)
        layout.addLayout(self.btn_layout)
        self.setLayout(layout)

        # Set title
        if title:
            title = to_text_string(title) + " - " + _("NumPy object array")
        else:
            title = _("Array editor")
        if readonly:
            title += ' (' + _('read only') + ')'
        self.setWindowTitle(title)

        # Set minimum size
        self.setMinimumSize(500, 300)

        # Make the dialog act as a window
        self.setWindowFlags(Qt.Window)

    def set_data_and_check(self, data, readonly=False):
        """
        Setup ArrayEditor:
        return False if data is not supported, True otherwise
        """
        if not isinstance(data, (np.ndarray, np.ma.MaskedArray)):
            return False

        self.data = data
        readonly = readonly or not self.data.flags.writeable
        is_masked_array = isinstance(data, np.ma.MaskedArray)

        # Reset data for 3d arrays
        self.dim_indexes = [{}, {}, {}]
        self.last_dim = 0

        # This is necessary in case users subclass ndarray and set the dtype
        # to an object that is not an actual dtype.
        # Fixes spyder-ide/spyder#20462
        if hasattr(data.dtype, 'names'):
            is_record_array = data.dtype.names is not None
        else:
            is_record_array = False

        if data.ndim > 3:
            self.error(_("Arrays with more than 3 dimensions are not "
                         "supported"))
            return False
        if not is_record_array:
            # This is necessary in case users subclass ndarray and set the
            # dtype to an object that is not an actual dtype.
            # Fixes spyder-ide/spyder#20462
            if hasattr(data.dtype, 'name'):
                dtn = data.dtype.name
            else:
                dtn = 'Unknown'

            if dtn == 'object':
                # If the array doesn't have shape, we can't display it
                if data.shape == ():
                    self.error(_("Object arrays without shape are not "
                                 "supported"))
                    return False
                # We don't know what's inside these arrays, so we can't handle
                # edits
                self.readonly = readonly = True
            elif (dtn not in SUPPORTED_FORMATS and not dtn.startswith('str')
                    and not dtn.startswith('unicode')):
                arr = _("%s arrays") % dtn
                self.error(_("%s are currently not supported") % arr)
                return False

        # ---- Stack widget

        # Remove old widgets, if any
        while self.stack.count() > 0:
            # Note: widgets get renumbered after removeWidget()
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()

        # Add widgets to the stack
        if is_record_array:
            for name in data.dtype.names:
                self.stack.addWidget(ArrayEditorWidget(self, data[name],
                                                       readonly))
        elif is_masked_array:
            self.stack.addWidget(ArrayEditorWidget(self, data, readonly))
            self.stack.addWidget(ArrayEditorWidget(self, data.data, readonly))
            self.stack.addWidget(ArrayEditorWidget(self, data.mask, readonly))
        elif data.ndim == 3:
            # Set the widget to display when launched
            self.combo_box_changed(self.last_dim)
        else:
            self.stack.addWidget(ArrayEditorWidget(self, data, readonly))

        self.arraywidget = self.stack.currentWidget()
        self.arraywidget.model.dataChanged.connect(self.save_and_close_enable)

        # ---- Actions

        safe_disconnect(self.resize_action.triggered)
        self.resize_action.triggered.connect(
            self.arraywidget.view.resize_to_contents)

        # ---- Widgets in bottom left

        # By default, all these widgets are hidden
        self.combo_label.hide()
        self.combo_box.hide()
        self.shape_label.hide()
        self.index_label.hide()
        self.index_spin.hide()
        self.slicing_label.hide()
        self.masked_label.hide()

        # Empty combo box
        while self.combo_box.count() > 0:
            self.combo_box.removeItem(0)

        # Handle cases
        if is_record_array:

            self.combo_label.setText(_('Record array fields:'))
            self.combo_label.show()

            names = []
            for name in data.dtype.names:
                field = data.dtype.fields[name]
                text = name
                if len(field) >= 3:
                    title = field[2]
                    if not is_text_string(title):
                        title = repr(title)
                    text += ' - '+title
                names.append(text)
            self.combo_box.addItems(names)
            self.combo_box.show()

        elif is_masked_array:

            names = [_('Masked data'), _('Data'), _('Mask')]
            self.combo_box.addItems(names)
            self.combo_box.show()

            self.masked_label.show()

        elif data.ndim == 3:

            self.combo_label.setText(_('Axis:'))
            self.combo_label.show()

            names = [str(i) for i in range(3)]
            self.combo_box.addItems(names)
            self.combo_box.show()

            self.shape_label.show()
            self.index_label.show()
            self.index_spin.show()
            self.slicing_label.show()

        # ---- Bottom row of buttons

        self.btn_save_and_close.setDisabled(True)
        if readonly:
            self.btn_save_and_close.hide()

        return True

    @Slot(QModelIndex, QModelIndex)
    def save_and_close_enable(self, left_top, bottom_right):
        """Handle the data change event to enable the save and close button."""
        if self.btn_save_and_close.isVisible():
            self.btn_save_and_close.setEnabled(True)
            self.btn_save_and_close.setAutoDefault(True)
            self.btn_save_and_close.setDefault(True)

    def current_widget_changed(self, index):
        self.arraywidget = self.stack.widget(index)
        if self.arraywidget:
            self.arraywidget.model.dataChanged.connect(
                self.save_and_close_enable
            )

    def change_active_widget(self, index):
        """
        This is implemented for handling negative values in index for
        3d arrays, to give the same behavior as slicing
        """
        string_index = [':']*3
        string_index[self.last_dim] = '<font color=red>%i</font>'
        self.slicing_label.setText((r"Slicing: [" + ", ".join(string_index) +
                                "]") % index)
        if index < 0:
            data_index = self.data.shape[self.last_dim] + index
        else:
            data_index = index
        slice_index = [slice(None)]*3
        slice_index[self.last_dim] = data_index

        stack_index = self.dim_indexes[self.last_dim].get(data_index)
        if stack_index is None:
            stack_index = self.stack.count()
            try:
                self.stack.addWidget(ArrayEditorWidget(
                    self, self.data[tuple(slice_index)]))
            except IndexError:  # Handle arrays of size 0 in one axis
                self.stack.addWidget(ArrayEditorWidget(self, self.data))
            self.dim_indexes[self.last_dim][data_index] = stack_index
            self.stack.update()
        self.stack.setCurrentIndex(stack_index)

    def combo_box_changed(self, index):
        """
        Handle changes in the combo box

        For masked and record arrays, this changes the visible widget in the
        stack. For 3d arrays, this changes the active axis the array editor is
        plotting over.
        """
        if self.data.ndim != 3:
            self.stack.setCurrentIndex(index)
            return

        self.last_dim = index
        string_size = ['%i']*3
        string_size[index] = '<font color=red>%i</font>'
        self.shape_label.setText(('Shape: (' + ', '.join(string_size) +
                                 ')    ') % self.data.shape)
        if self.index_spin.value() != 0:
            self.index_spin.setValue(0)
        else:
            # this is done since if the value is currently 0 it does not emit
            # currentIndexChanged(int)
            self.change_active_widget(0)
        self.index_spin.setRange(-self.data.shape[index],
                                 self.data.shape[index]-1)

    def show_preferences_dialog(self) -> None:
        """
        Show dialog for setting view options and process user choices.
        """
        # Create dialog using current options
        dialog = PreferencesDialog('array', parent=self)
        dialog.float_format = self.arraywidget.model.get_format_spec()
        dialog.varying_background = self.arraywidget.model.bgcolor_enabled

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
                self.arraywidget.model.set_format_spec(float_format)
                self.set_conf('dataframe_format', float_format)

            self.arraywidget.model.bgcolor(dialog.varying_background)

    def refresh(self) -> None:
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
                _('The new value cannot be displayed in the array editor.')
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
            _('Refresh array editor?'),
            message
        )
        return result == QMessageBox.Yes

    @Slot()
    def accept(self):
        """Reimplement Qt method."""
        try:
            for index in range(self.stack.count()):
                self.stack.widget(index).accept_changes()
            QDialog.accept(self)
        except RuntimeError:
            # Sometimes under CI testing the object the following error appears
            # RuntimeError: wrapped C/C++ object has been deleted
            pass

    def get_value(self):
        """Return modified array -- this is *not* a copy"""
        # It is important to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.data

    def error(self, message):
        """An error occurred, closing the dialog box"""
        QMessageBox.critical(self, _("Array editor"), message)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.reject()

    @Slot()
    def reject(self):
        """Reimplement Qt method"""
        if self.arraywidget is not None:
            for index in range(self.stack.count()):
                self.stack.widget(index).reject_changes()
        QDialog.reject(self)

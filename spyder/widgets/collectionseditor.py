# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# ----------------------------------------------------------------------------

"""
Collections (i.e. dictionary, list, set and tuple) editor widget and dialog.
"""

#TODO: Multiple selection: open as many editors (array/dict/...) as necessary,
#      at the same time

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
from __future__ import print_function
import datetime
import re
import sys
import warnings

# Third party imports
from qtpy.compat import getsavefilename, to_qvariant
from qtpy.QtCore import (QAbstractTableModel, QModelIndex, Qt,
                         Signal, Slot)
from qtpy.QtGui import QColor, QKeySequence
from qtpy.QtWidgets import (QAbstractItemView, QApplication, QDialog,
                            QHBoxLayout, QHeaderView, QInputDialog,
                            QLineEdit, QMenu, QMessageBox,
                            QPushButton, QTableView, QVBoxLayout,
                            QWidget)
from spyder_kernels.utils.misc import fix_reference_name
from spyder_kernels.utils.nsview import (
    DataFrame, display_to_value, FakeObject, get_human_readable_type,
    get_numpy_type_string, get_size, get_type_string, Image,
    MaskedArray, ndarray, np_savetxt, Series, sort_against,
    try_to_eval, unsorted_unique, value_to_display, get_object_attrs,
    get_type_string, NUMERIC_NUMPY_TYPES)

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.config.base import _
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.config.gui import get_font
from spyder.py3compat import (io, is_binary_string, PY3, to_text_string,
                              is_type_text_string, NUMERIC_TYPES)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import add_actions, create_action, mimedata2url
from spyder.utils.stringmatching import get_search_scores, get_search_regex
from spyder.plugins.variableexplorer.widgets.collectionsdelegate import (
    CollectionsDelegate)
from spyder.plugins.variableexplorer.widgets.importwizard import ImportWizard
from spyder.widgets.helperwidgets import CustomSortFilterProxy
from spyder.plugins.variableexplorer.widgets.basedialog import BaseDialog
from spyder.utils.palette import SpyderPalette


# Maximum length of a serialized variable to be set in the kernel
MAX_SERIALIZED_LENGHT = 1e6

LARGE_NROWS = 100
ROWS_TO_LOAD = 50


def natsort(s):
    """
    Natural sorting, e.g. test3 comes before test100.
    Taken from https://stackoverflow.com/a/16090640/3110740
    """
    if not isinstance(s, (str, bytes)):
        return s
    x = [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', s)]
    return x


class ProxyObject(object):
    """Dictionary proxy to an unknown object."""

    def __init__(self, obj):
        """Constructor."""
        self.__obj__ = obj

    def __len__(self):
        """Get len according to detected attributes."""
        return len(get_object_attrs(self.__obj__))

    def __getitem__(self, key):
        """Get the attribute corresponding to the given key."""
        # Catch NotImplementedError to fix spyder-ide/spyder#6284 in pandas
        # MultiIndex due to NA checking not being supported on a multiindex.
        # Catch AttributeError to fix spyder-ide/spyder#5642 in certain special
        # classes like xml when this method is called on certain attributes.
        # Catch TypeError to prevent fatal Python crash to desktop after
        # modifying certain pandas objects. Fix spyder-ide/spyder#6727.
        # Catch ValueError to allow viewing and editing of pandas offsets.
        # Fix spyder-ide/spyder#6728-
        try:
            attribute_toreturn = getattr(self.__obj__, key)
        except (NotImplementedError, AttributeError, TypeError, ValueError):
            attribute_toreturn = None
        return attribute_toreturn

    def __setitem__(self, key, value):
        """Set attribute corresponding to key with value."""
        # Catch AttributeError to gracefully handle inability to set an
        # attribute due to it not being writeable or set-table.
        # Fix spyder-ide/spyder#6728.
        # Also, catch NotImplementedError for safety.
        try:
            setattr(self.__obj__, key, value)
        except (TypeError, AttributeError, NotImplementedError):
            pass
        except Exception as e:
            if "cannot set values for" not in str(e):
                raise


class ReadOnlyCollectionsModel(QAbstractTableModel):
    """CollectionsEditor Read-Only Table Model"""

    sig_setting_data = Signal()

    def __init__(self, parent, data, title="", names=False,
                 minmax=False, remote=False):
        QAbstractTableModel.__init__(self, parent)
        if data is None:
            data = {}
        self._parent = parent
        self.scores = []
        self.names = names
        self.minmax = minmax
        self.remote = remote
        self.header0 = None
        self._data = None
        self.total_rows = None
        self.showndata = None
        self.keys = None
        self.title = to_text_string(title) # in case title is not a string
        if self.title:
            self.title = self.title + ' - '
        self.sizes = []
        self.types = []
        self.set_data(data)

    def get_data(self):
        """Return model data"""
        return self._data

    def set_data(self, data, coll_filter=None):
        """Set model data"""
        self._data = data
        data_type = get_type_string(data)

        if (coll_filter is not None and not self.remote and
                isinstance(data, (tuple, list, dict, set))):
            data = coll_filter(data)
        self.showndata = data

        self.header0 = _("Index")
        if self.names:
            self.header0 = _("Name")
        if isinstance(data, tuple):
            self.keys = list(range(len(data)))
            self.title += _("Tuple")
        elif isinstance(data, list):
            self.keys = list(range(len(data)))
            self.title += _("List")
        elif isinstance(data, set):
            self.keys = list(range(len(data)))
            self.title += _("Set")
            self._data = list(data)
        elif isinstance(data, dict):
            try:
                self.keys = sorted(list(data.keys()), key=natsort)
            except TypeError:
                # This is necessary to display dictionaries with mixed
                # types as keys.
                # Fixes spyder-ide/spyder#13481
                self.keys = list(data.keys())
            self.title += _("Dictionary")
            if not self.names:
                self.header0 = _("Key")
        else:
            self.keys = get_object_attrs(data)
            self._data = data = self.showndata = ProxyObject(data)
            if not self.names:
                self.header0 = _("Attribute")
        if not isinstance(self._data, ProxyObject):
            if len(self.keys) > 1:
                elements = _("elements")
            else:
                elements = _("element")
            self.title += (' (' + str(len(self.keys)) + ' ' + elements + ')')
        else:
            self.title += data_type
        self.total_rows = len(self.keys)
        if self.total_rows > LARGE_NROWS:
            self.rows_loaded = ROWS_TO_LOAD
        else:
            self.rows_loaded = self.total_rows
        self.sig_setting_data.emit()
        self.set_size_and_type()
        if len(self.keys):
            # Needed to update search scores when
            # adding values to the namespace
            self.update_search_letters()
        self.reset()

    def set_size_and_type(self, start=None, stop=None):
        data = self._data

        if start is None and stop is None:
            start = 0
            stop = self.rows_loaded
            fetch_more = False
        else:
            fetch_more = True

        # Ignore pandas warnings that certain attributes are deprecated
        # and will be removed, since they will only be accessed if they exist.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=(r"^\w+\.\w+ is deprecated and "
                                   "will be removed in a future version"))
            if self.remote:
                sizes = [data[self.keys[index]]['size']
                         for index in range(start, stop)]
                types = [data[self.keys[index]]['type']
                         for index in range(start, stop)]
            else:
                sizes = [get_size(data[self.keys[index]])
                         for index in range(start, stop)]
                types = [get_human_readable_type(data[self.keys[index]])
                         for index in range(start, stop)]

        if fetch_more:
            self.sizes = self.sizes + sizes
            self.types = self.types + types
        else:
            self.sizes = sizes
            self.types = types

    def load_all(self):
        """Load all the data."""
        self.fetchMore(number_to_fetch=self.total_rows)

    def sort(self, column, order=Qt.AscendingOrder):
        """Overriding sort method"""

        def all_string(listlike):
            return all([isinstance(x, str) for x in listlike])

        reverse = (order == Qt.DescendingOrder)
        sort_key = natsort if all_string(self.keys) else None

        if column == 0:
            self.sizes = sort_against(self.sizes, self.keys,
                                      reverse=reverse,
                                      sort_key=natsort)
            self.types = sort_against(self.types, self.keys,
                                      reverse=reverse,
                                      sort_key=natsort)
            try:
                self.keys.sort(reverse=reverse, key=sort_key)
            except:
                pass
        elif column == 1:
            self.keys[:self.rows_loaded] = sort_against(self.keys,
                                                        self.types,
                                                        reverse=reverse)
            self.sizes = sort_against(self.sizes, self.types, reverse=reverse)
            try:
                self.types.sort(reverse=reverse)
            except:
                pass
        elif column == 2:
            self.keys[:self.rows_loaded] = sort_against(self.keys,
                                                        self.sizes,
                                                        reverse=reverse)
            self.types = sort_against(self.types, self.sizes, reverse=reverse)
            try:
                self.sizes.sort(reverse=reverse)
            except:
                pass
        elif column in [3, 4]:
            values = [self._data[key] for key in self.keys]
            self.keys = sort_against(self.keys, values, reverse=reverse)
            self.sizes = sort_against(self.sizes, values, reverse=reverse)
            self.types = sort_against(self.types, values, reverse=reverse)
        self.beginResetModel()
        self.endResetModel()

    def columnCount(self, qindex=QModelIndex()):
        """Array column number"""
        if self._parent.proxy_model:
            return 5
        else:
            return 4

    def rowCount(self, index=QModelIndex()):
        """Array row number"""
        if self.total_rows <= self.rows_loaded:
            return self.total_rows
        else:
            return self.rows_loaded

    def canFetchMore(self, index=QModelIndex()):
        if self.total_rows > self.rows_loaded:
            return True
        else:
            return False

    def fetchMore(self, index=QModelIndex(), number_to_fetch=None):
        reminder = self.total_rows - self.rows_loaded
        if number_to_fetch is not None:
            items_to_fetch = min(reminder, number_to_fetch)
        else:
            items_to_fetch = min(reminder, ROWS_TO_LOAD)
        self.set_size_and_type(self.rows_loaded,
                               self.rows_loaded + items_to_fetch)
        self.beginInsertRows(QModelIndex(), self.rows_loaded,
                             self.rows_loaded + items_to_fetch - 1)
        self.rows_loaded += items_to_fetch
        self.endInsertRows()

    def get_index_from_key(self, key):
        try:
            return self.createIndex(self.keys.index(key), 0)
        except (RuntimeError, ValueError):
            return QModelIndex()

    def get_key(self, index):
        """Return current key"""
        return self.keys[index.row()]

    def get_value(self, index):
        """Return current value"""
        if index.column() == 0:
            return self.keys[ index.row() ]
        elif index.column() == 1:
            return self.types[ index.row() ]
        elif index.column() == 2:
            return self.sizes[ index.row() ]
        else:
            return self._data[ self.keys[index.row()] ]

    def get_bgcolor(self, index):
        """Background color depending on value"""
        if index.column() == 0:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.05)
        elif index.column() < 3:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.2)
        else:
            color = QColor(Qt.lightGray)
            color.setAlphaF(.3)
        return color

    def update_search_letters(self, text=""):
        """Update search letters with text input in search box."""
        self.letters = text
        names = [str(key) for key in self.keys]
        results = get_search_scores(text, names, template='<b>{0}</b>')
        if results:
            self.normal_text, _, self.scores = zip(*results)
            self.reset()

    def row_key(self, row_num):
        """
        Get row name based on model index.
        Needed for the custom proxy model.
        """
        return self.keys[row_num]

    def row_type(self, row_num):
        """
        Get row type based on model index.
        Needed for the custom proxy model.
        """
        return self.types[row_num]

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return to_qvariant()
        value = self.get_value(index)
        if index.column() == 4 and role == Qt.DisplayRole:
            # TODO: Check the effect of not hiding the column
            # Treating search scores as a table column simplifies the
            # sorting once a score for a specific string in the finder
            # has been defined. This column however should always remain
            # hidden.
            return to_qvariant(self.scores[index.row()])
        if index.column() == 3 and self.remote:
            value = value['view']
        if index.column() == 3:
            display = value_to_display(value, minmax=self.minmax)
        else:
            if is_type_text_string(value):
                display = to_text_string(value, encoding="utf-8")
            elif not isinstance(value, NUMERIC_TYPES + NUMERIC_NUMPY_TYPES):
                display = to_text_string(value)
            else:
                display = value
        if role == Qt.UserRole:
            if isinstance(value, NUMERIC_TYPES + NUMERIC_NUMPY_TYPES):
                return to_qvariant(value)
            else:
                return to_qvariant(display)
        elif role == Qt.DisplayRole:
            return to_qvariant(display)
        elif role == Qt.EditRole:
            return to_qvariant(value_to_display(value))
        elif role == Qt.TextAlignmentRole:
            if index.column() == 3:
                if len(display.splitlines()) < 3:
                    return to_qvariant(int(Qt.AlignLeft|Qt.AlignVCenter))
                else:
                    return to_qvariant(int(Qt.AlignLeft|Qt.AlignTop))
            else:
                return to_qvariant(int(Qt.AlignLeft|Qt.AlignVCenter))
        elif role == Qt.BackgroundColorRole:
            return to_qvariant( self.get_bgcolor(index) )
        elif role == Qt.FontRole:
            return to_qvariant(get_font(font_size_delta=DEFAULT_SMALL_DELTA))
        return to_qvariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overriding method headerData"""
        if role != Qt.DisplayRole:
            return to_qvariant()
        i_column = int(section)
        if orientation == Qt.Horizontal:
            headers = (self.header0, _("Type"), _("Size"), _("Value"),
                       _("Score"))
            return to_qvariant( headers[i_column] )
        else:
            return to_qvariant()

    def flags(self, index):
        """Overriding method flags"""
        # This method was implemented in CollectionsModel only, but to enable
        # tuple exploration (even without editing), this method was moved here
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemFlags(int(QAbstractTableModel.flags(self, index) |
                                Qt.ItemIsEditable))

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class CollectionsModel(ReadOnlyCollectionsModel):
    """Collections Table Model"""

    def set_value(self, index, value):
        """Set value"""
        self._data[ self.keys[index.row()] ] = value
        self.showndata[ self.keys[index.row()] ] = value
        self.sizes[index.row()] = get_size(value)
        self.types[index.row()] = get_human_readable_type(value)
        self.sig_setting_data.emit()

    def type_to_color(self, python_type, numpy_type):
        """Get the color that corresponds to a Python type."""
        # Color for unknown types
        color = SpyderPalette.GROUP_12

        if numpy_type != 'Unknown':
            if numpy_type == 'Array':
                color = SpyderPalette.GROUP_9
            elif numpy_type == 'Scalar':
                color = SpyderPalette.GROUP_2
        elif python_type == 'bool':
            color = SpyderPalette.GROUP_1
        elif python_type in ['int', 'float', 'complex']:
            color = SpyderPalette.GROUP_2
        elif python_type in ['str', 'unicode']:
            color = SpyderPalette.GROUP_3
        elif 'datetime' in python_type:
            color = SpyderPalette.GROUP_4
        elif python_type == 'list':
            color = SpyderPalette.GROUP_5
        elif python_type == 'set':
            color = SpyderPalette.GROUP_6
        elif python_type == 'tuple':
            color = SpyderPalette.GROUP_7
        elif python_type == 'dict':
            color = SpyderPalette.GROUP_8
        elif python_type in ['MaskedArray', 'Matrix', 'NDArray']:
            color = SpyderPalette.GROUP_9
        elif (python_type in ['DataFrame', 'Series'] or
                'Index' in python_type):
            color = SpyderPalette.GROUP_10
        elif python_type == 'PIL.Image.Image':
            color = SpyderPalette.GROUP_11
        else:
            color = SpyderPalette.GROUP_12

        return color

    def get_bgcolor(self, index):
        """Background color depending on value."""
        value = self.get_value(index)
        if index.column() < 3:
            color = ReadOnlyCollectionsModel.get_bgcolor(self, index)
        else:
            if self.remote:
                python_type = value['python_type']
                numpy_type = value['numpy_type']
            else:
                python_type = get_type_string(value)
                numpy_type = get_numpy_type_string(value)
            color_name = self.type_to_color(python_type, numpy_type)
            color = QColor(color_name)
            color.setAlphaF(0.5)
        return color

    def setData(self, index, value, role=Qt.EditRole):
        """Cell content change"""
        if not index.isValid():
            return False
        if index.column() < 3:
            return False
        value = display_to_value(value, self.get_value(index),
                                 ignore_errors=True)
        self.set_value(index, value)
        self.dataChanged.emit(index, index)
        return True


class BaseHeaderView(QHeaderView):
    """
    A header view for the BaseTableView that emits a signal when the width of
    one of its sections is resized by the user.
    """
    sig_user_resized_section = Signal(int, int, int)

    def __init__(self, parent=None):
        super(BaseHeaderView, self).__init__(Qt.Horizontal, parent)
        self._handle_section_is_pressed = False
        self.sectionResized.connect(self.sectionResizeEvent)
        # Needed to enable sorting by column
        # See spyder-ide/spyder#9835
        self.setSectionsClickable(True)

    def mousePressEvent(self, e):
        super(BaseHeaderView, self).mousePressEvent(e)
        self._handle_section_is_pressed = (self.cursor().shape() ==
                                           Qt.SplitHCursor)

    def mouseReleaseEvent(self, e):
        super(BaseHeaderView, self).mouseReleaseEvent(e)
        self._handle_section_is_pressed = False

    def sectionResizeEvent(self, logicalIndex, oldSize, newSize):
        if self._handle_section_is_pressed:
            self.sig_user_resized_section.emit(logicalIndex, oldSize, newSize)


class BaseTableView(QTableView, SpyderConfigurationAccessor):
    """Base collection editor table view"""
    CONF_SECTION = 'variable_explorer'

    sig_files_dropped = Signal(list)
    redirect_stdio = Signal(bool)
    sig_free_memory_requested = Signal()
    sig_editor_creation_started = Signal()
    sig_editor_shown = Signal()

    def __init__(self, parent):
        super().__init__(parent=parent)

        self.array_filename = None
        self.menu = None
        self.empty_ws_menu = None
        self.paste_action = None
        self.copy_action = None
        self.edit_action = None
        self.plot_action = None
        self.hist_action = None
        self.imshow_action = None
        self.save_array_action = None
        self.insert_action = None
        self.insert_action_above = None
        self.insert_action_below = None
        self.remove_action = None
        self.minmax_action = None
        self.rename_action = None
        self.duplicate_action = None
        self.last_regex = ''
        self.view_action = None
        self.delegate = None
        self.proxy_model = None
        self.source_model = None
        self.setAcceptDrops(True)
        self.automatic_column_width = True
        self.setHorizontalHeader(BaseHeaderView(parent=self))
        self.horizontalHeader().sig_user_resized_section.connect(
            self.user_resize_columns)

    def setup_table(self):
        """Setup table"""
        self.horizontalHeader().setStretchLastSection(True)
        self.adjust_columns()
        # Sorting columns
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)

    def setup_menu(self):
        """Setup context menu"""
        resize_action = create_action(self, _("Resize rows to contents"),
                                      triggered=self.resizeRowsToContents)
        resize_columns_action = create_action(
            self,
            _("Resize columns to contents"),
            triggered=self.resize_column_contents)
        self.paste_action = create_action(self, _("Paste"),
                                          icon=ima.icon('editpaste'),
                                          triggered=self.paste)
        self.copy_action = create_action(self, _("Copy"),
                                         icon=ima.icon('editcopy'),
                                         triggered=self.copy)
        self.edit_action = create_action(self, _("Edit"),
                                         icon=ima.icon('edit'),
                                         triggered=self.edit_item)
        self.plot_action = create_action(self, _("Plot"),
                                    icon=ima.icon('plot'),
                                    triggered=lambda: self.plot_item('plot'))
        self.plot_action.setVisible(False)
        self.hist_action = create_action(self, _("Histogram"),
                                    icon=ima.icon('hist'),
                                    triggered=lambda: self.plot_item('hist'))
        self.hist_action.setVisible(False)
        self.imshow_action = create_action(self, _("Show image"),
                                           icon=ima.icon('imshow'),
                                           triggered=self.imshow_item)
        self.imshow_action.setVisible(False)
        self.save_array_action = create_action(self, _("Save array"),
                                               icon=ima.icon('filesave'),
                                               triggered=self.save_array)
        self.save_array_action.setVisible(False)
        self.insert_action = create_action(
            self, _("Insert"),
            icon=ima.icon('insert'),
            triggered=lambda: self.insert_item(below=False)
        )
        self.insert_action_above = create_action(
            self, _("Insert above"),
            icon=ima.icon('insert'),
            triggered=lambda: self.insert_item(below=False)
        )
        self.insert_action_below = create_action(
            self, _("Insert below"),
            icon=ima.icon('insert'),
            triggered=lambda: self.insert_item(below=True)
        )
        self.remove_action = create_action(self, _("Remove"),
                                           icon=ima.icon('editdelete'),
                                           triggered=self.remove_item)
        self.rename_action = create_action(self, _("Rename"),
                                           icon=ima.icon('rename'),
                                           triggered=self.rename_item)
        self.duplicate_action = create_action(self, _("Duplicate"),
                                              icon=ima.icon('edit_add'),
                                              triggered=self.duplicate_item)
        self.view_action = create_action(
            self,
            _("View with the Object Explorer"),
            icon=ima.icon('outline_explorer'),
            triggered=self.view_item)
        menu = QMenu(self)
        menu_actions = [self.edit_action, self.plot_action, self.hist_action,
                        self.imshow_action, self.save_array_action,
                        self.insert_action,
                        self.insert_action_above, self.insert_action_below,
                        self.remove_action, self.copy_action,
                        self.paste_action, self.view_action,
                        None, self.rename_action, self.duplicate_action,
                        None, resize_action, resize_columns_action]
        add_actions(menu, menu_actions)
        self.empty_ws_menu = QMenu(self)
        add_actions(
            self.empty_ws_menu,
            [self.insert_action, self.paste_action]
        )
        return menu


    # ------ Remote/local API -------------------------------------------------
    def remove_values(self, keys):
        """Remove values from data"""
        raise NotImplementedError

    def copy_value(self, orig_key, new_key):
        """Copy value"""
        raise NotImplementedError

    def new_value(self, key, value):
        """Create new value in data"""
        raise NotImplementedError

    def is_list(self, key):
        """Return True if variable is a list, a set or a tuple"""
        raise NotImplementedError

    def get_len(self, key):
        """Return sequence length"""
        raise NotImplementedError

    def is_array(self, key):
        """Return True if variable is a numpy array"""
        raise NotImplementedError

    def is_image(self, key):
        """Return True if variable is a PIL.Image image"""
        raise NotImplementedError

    def is_dict(self, key):
        """Return True if variable is a dictionary"""
        raise NotImplementedError

    def get_array_shape(self, key):
        """Return array's shape"""
        raise NotImplementedError

    def get_array_ndim(self, key):
        """Return array's ndim"""
        raise NotImplementedError

    def oedit(self, key):
        """Edit item"""
        raise NotImplementedError

    def plot(self, key, funcname):
        """Plot item"""
        raise NotImplementedError

    def imshow(self, key):
        """Show item's image"""
        raise NotImplementedError

    def show_image(self, key):
        """Show image (item is a PIL image)"""
        raise NotImplementedError
    #--------------------------------------------------------------------------

    def refresh_menu(self):
        """Refresh context menu"""
        index = self.currentIndex()
        condition = index.isValid()
        self.edit_action.setEnabled(condition)
        self.remove_action.setEnabled(condition)
        self.refresh_plot_entries(index)

    def refresh_plot_entries(self, index):
        if index.isValid():
            if self.proxy_model:
                key = self.proxy_model.get_key(index)
            else:
                key = self.source_model.get_key(index)
            is_list = self.is_list(key)
            is_array = self.is_array(key) and self.get_len(key) != 0
            condition_plot = (is_array and len(self.get_array_shape(key)) <= 2)
            condition_hist = (is_array and self.get_array_ndim(key) == 1)
            condition_imshow = condition_plot and self.get_array_ndim(key) == 2
            condition_imshow = condition_imshow or self.is_image(key)
        else:
            is_array = condition_plot = condition_imshow = is_list \
                     = condition_hist = False
        is_list_instance = isinstance(self.source_model.get_data(), list)
        self.plot_action.setVisible(condition_plot or is_list)
        self.hist_action.setVisible(condition_hist or is_list)
        self.insert_action.setVisible(not is_list_instance)
        self.insert_action_above.setVisible(is_list_instance)
        self.insert_action_below.setVisible(is_list_instance)
        self.imshow_action.setVisible(condition_imshow)
        self.save_array_action.setVisible(is_array)

    def resize_column_contents(self):
        """Resize columns to contents."""
        self.automatic_column_width = True
        self.adjust_columns()

    def user_resize_columns(self, logical_index, old_size, new_size):
        """Handle the user resize action."""
        self.automatic_column_width = False

    def adjust_columns(self):
        """Resize two first columns to contents"""
        if self.automatic_column_width:
            for col in range(3):
                self.resizeColumnToContents(col)

    def set_data(self, data):
        """Set table data"""
        if data is not None:
            self.source_model.set_data(data, self.dictfilter)
            self.source_model.reset()
            self.sortByColumn(0, Qt.AscendingOrder)

    def mousePressEvent(self, event):
        """Reimplement Qt method"""
        if event.button() != Qt.LeftButton:
            QTableView.mousePressEvent(self, event)
            return
        index_clicked = self.indexAt(event.pos())
        if index_clicked.isValid():
            if index_clicked == self.currentIndex() \
               and index_clicked in self.selectedIndexes():
                self.clearSelection()
            else:
                QTableView.mousePressEvent(self, event)
        else:
            self.clearSelection()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        index_clicked = self.indexAt(event.pos())
        if index_clicked.isValid():
            row = index_clicked.row()
            # TODO: Remove hard coded "Value" column number (3 here)
            index_clicked = index_clicked.child(row, 3)
            self.edit(index_clicked)
        else:
            event.accept()

    def keyPressEvent(self, event):
        """Reimplement Qt methods"""
        if event.key() == Qt.Key_Delete:
            self.remove_item()
        elif event.key() == Qt.Key_F2:
            self.rename_item()
        elif event == QKeySequence.Copy:
            self.copy()
        elif event == QKeySequence.Paste:
            self.paste()
        else:
            QTableView.keyPressEvent(self, event)

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        if self.source_model.showndata:
            self.refresh_menu()
            self.menu.popup(event.globalPos())
            event.accept()
        else:
            self.empty_ws_menu.popup(event.globalPos())
            event.accept()

    def dragEnterEvent(self, event):
        """Allow user to drag files"""
        if mimedata2url(event.mimeData()):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Allow user to move files"""
        if mimedata2url(event.mimeData()):
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Allow user to drop supported files"""
        urls = mimedata2url(event.mimeData())
        if urls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self.sig_files_dropped.emit(urls)
        else:
            event.ignore()

    @Slot()
    def edit_item(self):
        """Edit item"""
        index = self.currentIndex()
        if not index.isValid():
            return
        # TODO: Remove hard coded "Value" column number (3 here)
        self.edit(index.child(index.row(), 3))

    @Slot()
    def remove_item(self, force=False):
        """Remove item"""
        indexes = self.selectedIndexes()
        if not indexes:
            return
        for index in indexes:
            if not index.isValid():
                return
        if not force:
            one = _("Do you want to remove the selected item?")
            more = _("Do you want to remove all selected items?")
            answer = QMessageBox.question(self, _("Remove"),
                                          one if len(indexes) == 1 else more,
                                          QMessageBox.Yes | QMessageBox.No)
        if force or answer == QMessageBox.Yes:
            if self.proxy_model:
                idx_rows = unsorted_unique(
                    [self.proxy_model.mapToSource(idx).row()
                     for idx in indexes])
            else:
                idx_rows = unsorted_unique([idx.row() for idx in indexes])
            keys = [self.source_model.keys[idx_row] for idx_row in idx_rows]
            self.remove_values(keys)

    def copy_item(self, erase_original=False, new_name=None):
        """Copy item"""
        indexes = self.selectedIndexes()
        if not indexes:
            return
        if self.proxy_model:
            idx_rows = unsorted_unique(
                [self.proxy_model.mapToSource(idx).row() for idx in indexes])
        else:
            idx_rows = unsorted_unique([idx.row() for idx in indexes])
        if len(idx_rows) > 1 or not indexes[0].isValid():
            return
        orig_key = self.source_model.keys[idx_rows[0]]
        if erase_original:
            title = _('Rename')
            field_text = _('New variable name:')
        else:
            title = _('Duplicate')
            field_text = _('Variable name:')
        data = self.source_model.get_data()
        if isinstance(data, (list, set)):
            new_key, valid = len(data), True
        elif new_name is not None:
            new_key, valid = new_name, True
        else:
            new_key, valid = QInputDialog.getText(self, title, field_text,
                                                  QLineEdit.Normal, orig_key)
        if valid and to_text_string(new_key):
            new_key = try_to_eval(to_text_string(new_key))
            if new_key == orig_key:
                return
            self.copy_value(orig_key, new_key)
            if erase_original:
                self.remove_values([orig_key])

    @Slot()
    def duplicate_item(self):
        """Duplicate item"""
        self.copy_item()

    @Slot()
    def rename_item(self, new_name=None):
        """Rename item"""
        self.copy_item(erase_original=True, new_name=new_name)

    @Slot()
    def insert_item(self, below=True):
        """Insert item"""
        index = self.currentIndex()
        if not index.isValid():
            row = self.source_model.rowCount()
        else:
            if self.proxy_model:
                if below:
                    row = self.proxy_model.mapToSource(index).row() + 1
                else:
                    row = self.proxy_model.mapToSource(index).row()
            else:
                if below:
                    row = index.row() + 1
                else:
                    row = index.row()
        data = self.source_model.get_data()
        if isinstance(data, list):
            key = row
            data.insert(row, '')
        elif isinstance(data, dict):
            key, valid = QInputDialog.getText(self, _( 'Insert'), _( 'Key:'),
                                              QLineEdit.Normal)
            if valid and to_text_string(key):
                key = try_to_eval(to_text_string(key))
            else:
                return
        else:
            return
        value, valid = QInputDialog.getText(self, _('Insert'), _('Value:'),
                                            QLineEdit.Normal)
        if valid and to_text_string(value):
            self.new_value(key, try_to_eval(to_text_string(value)))

    @Slot()
    def view_item(self):
        """View item with the Object Explorer"""
        index = self.currentIndex()
        if not index.isValid():
            return
        # TODO: Remove hard coded "Value" column number (3 here)
        index = index.child(index.row(), 3)
        self.delegate.createEditor(self, None, index, object_explorer=True)

    def __prepare_plot(self):
        try:
            import guiqwt.pyplot   #analysis:ignore
            return True
        except:
            try:
                if 'matplotlib' not in sys.modules:
                    import matplotlib
                return True
            except Exception:
                QMessageBox.warning(self, _("Import error"),
                                    _("Please install <b>matplotlib</b>"
                                      " or <b>guiqwt</b>."))

    def plot_item(self, funcname):
        """Plot item"""
        index = self.currentIndex()
        if self.__prepare_plot():
            if self.proxy_model:
                key = self.source_model.get_key(
                    self.proxy_model.mapToSource(index))
            else:
                key = self.source_model.get_key(index)
            try:
                self.plot(key, funcname)
            except (ValueError, TypeError) as error:
                QMessageBox.critical(self, _( "Plot"),
                                     _("<b>Unable to plot data.</b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % str(error))

    @Slot()
    def imshow_item(self):
        """Imshow item"""
        index = self.currentIndex()
        if self.__prepare_plot():
            if self.proxy_model:
                key = self.source_model.get_key(
                    self.proxy_model.mapToSource(index))
            else:
                key = self.source_model.get_key(index)
            try:
                if self.is_image(key):
                    self.show_image(key)
                else:
                    self.imshow(key)
            except (ValueError, TypeError) as error:
                QMessageBox.critical(self, _( "Plot"),
                                     _("<b>Unable to show image.</b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % str(error))

    @Slot()
    def save_array(self):
        """Save array"""
        title = _( "Save array")
        if self.array_filename is None:
            self.array_filename = getcwd_or_home()
        self.redirect_stdio.emit(False)
        filename, _selfilter = getsavefilename(self, title,
                                               self.array_filename,
                                               _("NumPy arrays")+" (*.npy)")
        self.redirect_stdio.emit(True)
        if filename:
            self.array_filename = filename
            data = self.delegate.get_value( self.currentIndex() )
            try:
                import numpy as np
                np.save(self.array_filename, data)
            except Exception as error:
                QMessageBox.critical(self, title,
                                     _("<b>Unable to save array</b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % str(error))

    @Slot()
    def copy(self):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipl = []
        for idx in self.selectedIndexes():
            if not idx.isValid():
                continue
            obj = self.delegate.get_value(idx)
            # Check if we are trying to copy a numpy array, and if so make sure
            # to copy the whole thing in a tab separated format
            if isinstance(obj, (ndarray, MaskedArray)) \
              and ndarray is not FakeObject:
                if PY3:
                    output = io.BytesIO()
                else:
                    output = io.StringIO()
                try:
                    np_savetxt(output, obj, delimiter='\t')
                except:
                    QMessageBox.warning(self, _("Warning"),
                                        _("It was not possible to copy "
                                          "this array"))
                    return
                obj = output.getvalue().decode('utf-8')
                output.close()
            elif isinstance(obj, (DataFrame, Series)) \
              and DataFrame is not FakeObject:
                output = io.StringIO()
                try:
                    obj.to_csv(output, sep='\t', index=True, header=True)
                except Exception:
                    QMessageBox.warning(self, _("Warning"),
                                        _("It was not possible to copy "
                                          "this dataframe"))
                    return
                if PY3:
                    obj = output.getvalue()
                else:
                    obj = output.getvalue().decode('utf-8')
                output.close()
            elif is_binary_string(obj):
                obj = to_text_string(obj, 'utf8')
            else:
                obj = to_text_string(obj)
            clipl.append(obj)
        clipboard.setText('\n'.join(clipl))

    def import_from_string(self, text, title=None):
        """Import data from string"""
        data = self.source_model.get_data()
        # Check if data is a dict
        if not hasattr(data, "keys"):
            return
        editor = ImportWizard(
            self, text, title=title, contents_title=_("Clipboard contents"),
            varname=fix_reference_name("data", blacklist=list(data.keys())))
        if editor.exec_():
            var_name, clip_data = editor.get_data()
            self.new_value(var_name, clip_data)

    @Slot()
    def paste(self):
        """Import text/data/code from clipboard"""
        clipboard = QApplication.clipboard()
        cliptext = ''
        if clipboard.mimeData().hasText():
            cliptext = to_text_string(clipboard.text())
        if cliptext.strip():
            self.import_from_string(cliptext, title=_("Import from clipboard"))
        else:
            QMessageBox.warning(self, _( "Empty clipboard"),
                                _("Nothing to be imported from clipboard."))


class CollectionsEditorTableView(BaseTableView):
    """CollectionsEditor table view"""
    def __init__(self, parent, data, readonly=False, title="",
                 names=False):
        BaseTableView.__init__(self, parent)
        self.dictfilter = None
        self.readonly = readonly or isinstance(data, (tuple, set))
        CollectionsModelClass = (ReadOnlyCollectionsModel if self.readonly
                                 else CollectionsModel)
        self.source_model = CollectionsModelClass(
            self,
            data,
            title,
            names=names,
            minmax=self.get_conf('minmax')
        )
        self.model = self.source_model
        self.setModel(self.source_model)
        self.delegate = CollectionsDelegate(self)
        self.setItemDelegate(self.delegate)

        self.setup_table()
        self.menu = self.setup_menu()

        if isinstance(data, set):
            self.horizontalHeader().hideSection(0)

    #------ Remote/local API --------------------------------------------------
    def remove_values(self, keys):
        """Remove values from data"""
        data = self.source_model.get_data()
        for key in sorted(keys, reverse=True):
            data.pop(key)
        self.set_data(data)

    def copy_value(self, orig_key, new_key):
        """Copy value"""
        data = self.source_model.get_data()
        if isinstance(data, list):
            data.append(data[orig_key])
        if isinstance(data, set):
            data.add(data[orig_key])
        else:
            data[new_key] = data[orig_key]
        self.set_data(data)

    def new_value(self, key, value):
        """Create new value in data"""
        data = self.source_model.get_data()
        data[key] = value
        self.set_data(data)

    def is_list(self, key):
        """Return True if variable is a list or a tuple"""
        data = self.source_model.get_data()
        return isinstance(data[key], (tuple, list))

    def is_set(self, key):
        """Return True if variable is a set"""
        data = self.source_model.get_data()
        return isinstance(data[key], set)

    def get_len(self, key):
        """Return sequence length"""
        data = self.source_model.get_data()
        return len(data[key])

    def is_array(self, key):
        """Return True if variable is a numpy array"""
        data = self.source_model.get_data()
        return isinstance(data[key], (ndarray, MaskedArray))

    def is_image(self, key):
        """Return True if variable is a PIL.Image image"""
        data = self.source_model.get_data()
        return isinstance(data[key], Image)

    def is_dict(self, key):
        """Return True if variable is a dictionary"""
        data = self.source_model.get_data()
        return isinstance(data[key], dict)

    def get_array_shape(self, key):
        """Return array's shape"""
        data = self.source_model.get_data()
        return data[key].shape

    def get_array_ndim(self, key):
        """Return array's ndim"""
        data = self.source_model.get_data()
        return data[key].ndim

    def oedit(self, key):
        """Edit item"""
        data = self.source_model.get_data()
        from spyder.plugins.variableexplorer.widgets.objecteditor import (
                oedit)
        oedit(data[key])

    def plot(self, key, funcname):
        """Plot item"""
        data = self.source_model.get_data()
        import spyder.pyplot as plt
        plt.figure()
        getattr(plt, funcname)(data[key])
        plt.show()

    def imshow(self, key):
        """Show item's image"""
        data = self.source_model.get_data()
        import spyder.pyplot as plt
        plt.figure()
        plt.imshow(data[key])
        plt.show()

    def show_image(self, key):
        """Show image (item is a PIL image)"""
        data = self.source_model.get_data()
        data[key].show()
    #--------------------------------------------------------------------------

    def refresh_menu(self):
        """Refresh context menu"""
        data = self.source_model.get_data()
        index = self.currentIndex()
        condition = (not isinstance(data, (tuple, set))) and index.isValid() \
                    and not self.readonly
        self.edit_action.setEnabled( condition )
        self.remove_action.setEnabled( condition )
        self.insert_action.setEnabled(not self.readonly)
        self.insert_action_above.setEnabled(not self.readonly)
        self.insert_action_below.setEnabled(not self.readonly)
        self.duplicate_action.setEnabled(condition)
        condition_rename = not isinstance(data, (tuple, list, set))
        self.rename_action.setEnabled(condition_rename)
        self.refresh_plot_entries(index)

    def set_filter(self, dictfilter=None):
        """Set table dict filter"""
        self.dictfilter = dictfilter


class CollectionsEditorWidget(QWidget):
    """Dictionary Editor Widget"""
    def __init__(self, parent, data, readonly=False, title="", remote=False):
        QWidget.__init__(self, parent)
        if remote:
            self.editor = RemoteCollectionsEditorTableView(self, data, readonly)
        else:
            self.editor = CollectionsEditorTableView(self, data, readonly,
                                                     title)
        layout = QVBoxLayout()
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def set_data(self, data):
        """Set DictEditor data"""
        self.editor.set_data(data)

    def get_title(self):
        """Get model title"""
        return self.editor.source_model.title


class CollectionsEditor(BaseDialog):
    """Collections Editor Dialog"""
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.data_copy = None
        self.widget = None
        self.btn_save_and_close = None
        self.btn_close = None

    def setup(self, data, title='', readonly=False, remote=False,
              icon=None, parent=None):
        """Setup editor."""
        if isinstance(data, (dict, set)):
            # dictionary, set
            self.data_copy = data.copy()
            datalen = len(data)
        elif isinstance(data, (tuple, list)):
            # list, tuple
            self.data_copy = data[:]
            datalen = len(data)
        else:
            # unknown object
            import copy
            try:
                self.data_copy = copy.deepcopy(data)
            except NotImplementedError:
                self.data_copy = copy.copy(data)
            except (TypeError, AttributeError):
                readonly = True
                self.data_copy = data
            datalen = len(get_object_attrs(data))

        # If the copy has a different type, then do not allow editing, because
        # this would change the type after saving; cf. spyder-ide/spyder#6936.
        if type(self.data_copy) != type(data):
            readonly = True

        self.widget = CollectionsEditorWidget(self, self.data_copy,
                                              title=title, readonly=readonly,
                                              remote=remote)
        self.widget.editor.source_model.sig_setting_data.connect(
                                                    self.save_and_close_enable)
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)

        # Buttons configuration
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if not readonly:
            self.btn_save_and_close = QPushButton(_('Save and Close'))
            self.btn_save_and_close.setDisabled(True)
            self.btn_save_and_close.clicked.connect(self.accept)
            btn_layout.addWidget(self.btn_save_and_close)

        self.btn_close = QPushButton(_('Close'))
        self.btn_close.setAutoDefault(True)
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

        self.setWindowTitle(self.widget.get_title())
        if icon is None:
            self.setWindowIcon(ima.icon('dictedit'))

        if sys.platform == 'darwin':
            # See: https://github.com/spyder-ide/spyder/issues/9051
            self.setWindowFlags(Qt.Tool)
        else:
            # Make the dialog act as a window
            self.setWindowFlags(Qt.Window)

    @Slot()
    def save_and_close_enable(self):
        """Handle the data change event to enable the save and close button."""
        if self.btn_save_and_close:
            self.btn_save_and_close.setEnabled(True)
            self.btn_save_and_close.setAutoDefault(True)
            self.btn_save_and_close.setDefault(True)

    def get_value(self):
        """Return modified copy of dictionary or list"""
        # It is import to avoid accessing Qt C++ object as it has probably
        # already been destroyed, due to the Qt.WA_DeleteOnClose attribute
        return self.data_copy


#==============================================================================
# Remote versions of CollectionsDelegate and CollectionsEditorTableView
#==============================================================================
class RemoteCollectionsDelegate(CollectionsDelegate):
    """CollectionsEditor Item Delegate"""
    def __init__(self, parent=None):
        CollectionsDelegate.__init__(self, parent)

    def get_value(self, index):
        if index.isValid():
            source_index = index.model().mapToSource(index)
            name = source_index.model().keys[source_index.row()]
            return self.parent().get_value(name)

    def set_value(self, index, value):
        if index.isValid():
            source_index = index.model().mapToSource(index)
            name = source_index.model().keys[source_index.row()]
            self.parent().new_value(name, value)


class RemoteCollectionsEditorTableView(BaseTableView):
    """DictEditor table view"""
    def __init__(self, parent, data, shellwidget=None, remote_editing=False,
                 create_menu=False):
        BaseTableView.__init__(self, parent)

        self.shellwidget = shellwidget
        self.var_properties = {}
        self.dictfilter = None
        self.delegate = None
        self.readonly = False
        self.finder = None

        self.source_model = CollectionsModel(
            self, data, names=True,
            minmax=self.get_conf('minmax'),
            remote=True)

        self.horizontalHeader().sectionClicked.connect(
            self.source_model.load_all)

        self.proxy_model = CollectionsCustomSortFilterProxy(self)
        self.model = self.proxy_model

        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setFilterKeyColumn(0)  # Col 0 for Name
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setSortRole(Qt.UserRole)
        self.setModel(self.proxy_model)

        self.hideColumn(4)  # Column 4 for Score

        self.delegate = RemoteCollectionsDelegate(self)
        self.delegate.sig_free_memory_requested.connect(
            self.sig_free_memory_requested)
        self.delegate.sig_editor_creation_started.connect(
            self.sig_editor_creation_started)
        self.delegate.sig_editor_shown.connect(self.sig_editor_shown)
        self.setItemDelegate(self.delegate)

        self.setup_table()

        if create_menu:
            self.menu = self.setup_menu()

    # ------ Remote/local API -------------------------------------------------
    def get_value(self, name):
        """Get the value of a variable"""
        value = self.shellwidget.get_value(name)
        return value

    def new_value(self, name, value):
        """Create new value in data"""
        try:
            self.shellwidget.set_value(name, value)
        except TypeError as e:
            QMessageBox.critical(self, _("Error"),
                                 "TypeError: %s" % to_text_string(e))
        self.shellwidget.refresh_namespacebrowser()

    def remove_values(self, names):
        """Remove values from data"""
        for name in names:
            self.shellwidget.remove_value(name)
        self.shellwidget.refresh_namespacebrowser()

    def copy_value(self, orig_name, new_name):
        """Copy value"""
        self.shellwidget.copy_value(orig_name, new_name)
        self.shellwidget.refresh_namespacebrowser()

    def is_list(self, name):
        """Return True if variable is a list, a tuple or a set"""
        return self.var_properties[name]['is_list']

    def is_dict(self, name):
        """Return True if variable is a dictionary"""
        return self.var_properties[name]['is_dict']

    def get_len(self, name):
        """Return sequence length"""
        return self.var_properties[name]['len']

    def is_array(self, name):
        """Return True if variable is a NumPy array"""
        return self.var_properties[name]['is_array']

    def is_image(self, name):
        """Return True if variable is a PIL.Image image"""
        return self.var_properties[name]['is_image']

    def is_data_frame(self, name):
        """Return True if variable is a DataFrame"""
        return self.var_properties[name]['is_data_frame']

    def is_series(self, name):
        """Return True if variable is a Series"""
        return self.var_properties[name]['is_series']

    def get_array_shape(self, name):
        """Return array's shape"""
        return self.var_properties[name]['array_shape']

    def get_array_ndim(self, name):
        """Return array's ndim"""
        return self.var_properties[name]['array_ndim']

    def plot(self, name, funcname):
        """Plot item"""
        sw = self.shellwidget
        sw.execute("%%varexp --%s %s" % (funcname, name))

    def imshow(self, name):
        """Show item's image"""
        sw = self.shellwidget
        sw.execute("%%varexp --imshow %s" % name)

    def show_image(self, name):
        """Show image (item is a PIL image)"""
        command = "%s.show()" % name
        sw = self.shellwidget
        sw.execute(command)

    # ------ Other ------------------------------------------------------------
    def setup_menu(self):
        """Setup context menu."""
        menu = BaseTableView.setup_menu(self)
        return menu

    def set_regex(self, regex=None, reset=False):
        """Update the regex text for the variable finder."""
        if reset or self.finder is None or not self.finder.text():
            text = ''
        else:
            text = self.finder.text().replace(' ', '').lower()

        self.proxy_model.set_filter(text)
        self.source_model.update_search_letters(text)

        if text:
            # TODO: Use constants for column numbers
            self.sortByColumn(4, Qt.DescendingOrder)  # Col 4 for index

        self.last_regex = regex

    def next_row(self):
        """Move to next row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.proxy_model.rowCount()
        if row + 1 == rows:
            row = -1
        self.selectRow(row + 1)

    def previous_row(self):
        """Move to previous row from currently selected row."""
        row = self.currentIndex().row()
        rows = self.proxy_model.rowCount()
        if row == 0:
            row = rows
        self.selectRow(row - 1)


class CollectionsCustomSortFilterProxy(CustomSortFilterProxy):
    """
    Custom column filter based on regex and model data.

    Reimplements 'filterAcceptsRow' to follow NamespaceBrowser model.
    Reimplements 'set_filter' to allow sorting while filtering
    """

    def get_key(self, index):
        """Return current key from source model."""
        source_index = self.mapToSource(index)
        return self.sourceModel().get_key(source_index)

    def get_index_from_key(self, key):
        """Return index using key from source model."""
        source_index = self.sourceModel().get_index_from_key(key)
        return self.mapFromSource(source_index)

    def get_value(self, index):
        """Return current value from source model."""
        source_index = self.mapToSource(index)
        return self.sourceModel().get_value(source_index)

    def set_value(self, index, value):
        """Set value in source model."""
        try:
            source_index = self.mapToSource(index)
            self.sourceModel().set_value(source_index, value)
        except AttributeError:
            # Read-only models don't have set_value method
            pass

    def set_filter(self, text):
        """Set regular expression for filter."""
        self.pattern = get_search_regex(text)
        self.invalidateFilter()

    def filterAcceptsRow(self, row_num, parent):
        """
        Qt override.

        Reimplemented from base class to allow the use of custom filtering
        using to columns (name and type).
        """
        model = self.sourceModel()
        name = to_text_string(model.row_key(row_num))
        variable_type = to_text_string(model.row_type(row_num))
        r_name = re.search(self.pattern, name)
        r_type = re.search(self.pattern, variable_type)

        if r_name is None and r_type is None:
            return False
        else:
            return True

    def lessThan(self, left, right):
        """
        Implements ordering in a natural way, as a human would sort.
        This functions enables sorting of the main variable editor table,
        which does not rely on 'self.sort()'.
        """
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)
        try:
            if isinstance(leftData, str) and isinstance(rightData, str):
                return natsort(leftData) < natsort(rightData)
            else:
                return leftData < rightData
        except TypeError:
            # This is needed so all the elements that cannot be compared such
            # as dataframes and numpy arrays are grouped together in the
            # variable explorer. For more info see spyder-ide/spyder#14527
            return True


# =============================================================================
# Tests
# =============================================================================
def get_test_data():
    """Create test data."""
    import numpy as np
    from spyder.pil_patch import Image
    image = Image.fromarray(np.random.randint(256, size=(100, 100)),
                            mode='P')
    testdict = {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]}
    testdate = datetime.date(1945, 5, 8)
    test_timedelta = datetime.timedelta(days=-1, minutes=42, seconds=13)

    try:
        import pandas as pd
    except (ModuleNotFoundError, ImportError):
        test_df = None
        test_timestamp = test_pd_td = test_dtindex = test_series = None
    else:
        test_timestamp = pd.Timestamp("1945-05-08T23:01:00.12345")
        test_pd_td = pd.Timedelta(days=2193, hours=12)
        test_dtindex = pd.date_range(start="1939-09-01T",
                                     end="1939-10-06",
                                     freq="12H")
        test_series = pd.Series({"series_name": [0, 1, 2, 3, 4, 5]})
        test_df = pd.DataFrame({"string_col": ["a", "b", "c", "d"],
                                "int_col": [0, 1, 2, 3],
                                "float_col": [1.1, 2.2, 3.3, 4.4],
                                "bool_col": [True, False, False, True]})

    class Foobar(object):

        def __init__(self):
            self.text = "toto"
            self.testdict = testdict
            self.testdate = testdate

    foobar = Foobar()
    return {'object': foobar,
            'module': np,
            'str': 'kjkj kj k j j kj k jkj',
            'unicode': to_text_string('éù', 'utf-8'),
            'list': [1, 3, [sorted, 5, 6], 'kjkj', None],
            'set': {1, 2, 1, 3, None, 'A', 'B', 'C', True, False},
            'tuple': ([1, testdate, testdict, test_timedelta], 'kjkj', None),
            'dict': testdict,
            'float': 1.2233,
            'int': 223,
            'bool': True,
            'array': np.random.rand(10, 10).astype(np.int64),
            'masked_array': np.ma.array([[1, 0], [1, 0]],
                                        mask=[[True, False], [False, False]]),
            '1D-array': np.linspace(-10, 10).astype(np.float16),
            '3D-array': np.random.randint(2, size=(5, 5, 5)).astype(np.bool_),
            'empty_array': np.array([]),
            'image': image,
            'date': testdate,
            'datetime': datetime.datetime(1945, 5, 8, 23, 1, 0, int(1.5e5)),
            'timedelta': test_timedelta,
            'complex': 2+1j,
            'complex64': np.complex64(2+1j),
            'complex128': np.complex128(9j),
            'int8_scalar': np.int8(8),
            'int16_scalar': np.int16(16),
            'int32_scalar': np.int32(32),
            'int64_scalar': np.int64(64),
            'float16_scalar': np.float16(16),
            'float32_scalar': np.float32(32),
            'float64_scalar': np.float64(64),
            'bool_scalar': np.bool(8),
            'bool__scalar': np.bool_(8),
            'timestamp': test_timestamp,
            'timedelta_pd': test_pd_td,
            'datetimeindex': test_dtindex,
            'series': test_series,
            'ddataframe': test_df,
            'None': None,
            'unsupported1': np.arccos,
            'unsupported2': np.cast,
            # Test for spyder-ide/spyder#3518.
            'big_struct_array': np.zeros(1000, dtype=[('ID', 'f8'),
                                                      ('param1', 'f8', 5000)]),
            }


def editor_test():
    """Test Collections editor."""
    from spyder.utils.qthelpers import qapplication

    app = qapplication()             #analysis:ignore
    dialog = CollectionsEditor()
    dialog.setup(get_test_data())
    dialog.show()
    app.exec_()


def remote_editor_test():
    """Test remote collections editor."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()

    from spyder.config.manager import CONF
    from spyder_kernels.utils.nsview import (make_remote_view,
                                             REMOTE_SETTINGS)

    settings = {}
    for name in REMOTE_SETTINGS:
        settings[name] = CONF.get('variable_explorer', name)

    remote = make_remote_view(get_test_data(), settings)
    dialog = CollectionsEditor()
    dialog.setup(remote, remote=True)
    dialog.show()
    app.exec_()


if __name__ == "__main__":
    editor_test()
    remote_editor_test()

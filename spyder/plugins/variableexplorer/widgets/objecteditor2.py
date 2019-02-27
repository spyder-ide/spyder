# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Spyder Project Contributors
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license.
# Licensed under the terms of the MIT License; see NOTICE.txt in the Spyder
# root directory for details
# -----------------------------------------------------------------------------

from __future__ import absolute_import
from __future__ import print_function

# Standard library imports
import logging
import inspect
import traceback
import hashlib
import six
from difflib import SequenceMatcher
from collections import OrderedDict
from six import unichr
import string
import pprint

# Third-party imports
from qtpy.QtCore import (Slot, QAbstractItemModel, QModelIndex, QPoint,
                         QSize, Qt, QTimer, QSortFilterProxyModel)
from qtpy.QtGui import QFont, QKeySequence, QBrush, QColor, QTextOption
from qtpy.QtWidgets import (QAbstractItemView, QAction, QActionGroup,
                            QButtonGroup, QGridLayout, QHBoxLayout, QGroupBox,
                            QMessageBox, QMenuBar,
                            QPlainTextEdit, QRadioButton,
                            QSplitter, QVBoxLayout, QWidget, QDialog,
                            QTableWidget, QTreeView, QTreeWidget)

# Local imports
from spyder.config.base import _
from spyder.utils.qthelpers import (add_actions, create_action,
                                    keybinding, qapplication)

logger = logging.getLogger(__name__)

# About message
PROGRAM_NAME = 'objbrowser'
PROGRAM_URL = 'https://github.com/titusjan/objbrowser'


# Maximum number of characters used in the __str__ method to
# represent the underlying object
MAX_OBJ_STR_LEN = 50

# Attribute models constants
try:
    import numpy as np
except ImportError:
    _NUMPY_INSTALLED = False
else:
    _NUMPY_INSTALLED = True

SMALL_COL_WIDTH = 120
MEDIUM_COL_WIDTH = 200

_PRETTY_PRINTER = pprint.PrettyPrinter(indent=4)

_ALL_PREDICATES = (inspect.ismodule, inspect.isclass, inspect.ismethod,
                   inspect.isfunction, inspect.isgeneratorfunction,
                   inspect.isgenerator,
                   inspect.istraceback, inspect.isframe, inspect.iscode,
                   inspect.isbuiltin, inspect.isroutine, inspect.isabstract,
                   inspect.ismethoddescriptor, inspect.isdatadescriptor,
                   inspect.isgetsetdescriptor, inspect.ismemberdescriptor)

# The cast to int is necessary to avoid a bug in PySide, See:
# https://bugreports.qt-project.org/browse/PYSIDE-20
ALIGN_LEFT = int(Qt.AlignVCenter | Qt.AlignLeft)
ALIGN_RIGHT = int(Qt.AlignVCenter | Qt.AlignRight)


# Utility functions
def name_is_special(method_name):
    "Returns true if the method name starts and ends with two underscores"
    return method_name.startswith('__') and method_name.endswith('__')


def logging_basic_config(level='INFO'):
    """
    Setup basic config logging. Useful for debugging to
    quickly setup a useful logger.
    """
    fmt = '%(filename)25s:%(lineno)-4d : %(levelname)-7s: %(message)s'
    logging.basicConfig(level=level, format=fmt)


def check_class(obj, target_class, allow_none=False):
    """
    Checks that the  obj is a (sub)type of target_class.
    Raises a TypeError if this is not the case.
    """
    if not isinstance(obj, target_class):
        if not (allow_none and obj is None):
            raise TypeError("obj must be a of type {}, got: {}"
                            .format(target_class, type(obj)))


# Needed because boolean QSettings in Pyside are converted incorrect the second
# time in Windows (and Linux?) because of a bug in Qt. See:
# https://www.mail-archive.com/pyside@lists.pyside.org/msg00230.html
def setting_str_to_bool(s):
    """Converts 'true' to True and 'false' to False if s is a string."""
    if isinstance(s, six.string_types):
        s = s.lower()
        if s == 'true':
            return True
        elif s == 'false':
            return False
        else:
            return ValueError('Invalid boolean representation: {!r}'.format(s))
    else:
        return s


def cut_off_str(obj, max_len):
    """
    Creates a string representation of an object, no longer than
    max_len characters

    Uses repr(obj) to create the string representation.
    If this is longer than max_len -3 characters, the last three will
    be replaced with elipsis.
    """
    s = repr(obj)
    if len(s) > max_len - 3:
        s = s[:max_len - 3] + '...'
    return s


###################
# Data functions ##
###################
def tio_call(obj_fn, tree_item):
    """Calls obj_fn(tree_item.obj)."""
    return obj_fn(tree_item.obj)


def safe_tio_call(obj_fn, tree_item, log_exceptions=False):
    """
    Call the obj_fn(tree_item.obj).
    Returns empty string in case of an error.
    """
    tio = tree_item.obj
    try:
        return str(obj_fn(tio))
    except Exception as ex:
        if log_exceptions:
            logger.exception(ex)
        return ""


def safe_data_fn(obj_fn, log_exceptions=False):
    """
    Creates a function that returns an empty string in case of an exception.

    :param fnobj_fn: function that will be wrapped
    :type obj_fn: object to basestring function
    :returns: function that can be used as AttributeModel data_fn attribute
    :rtype: objbrowser.treeitem.TreeItem to string function
    """
    def data_fn(tree_item):
        """
        Call the obj_fn(tree_item.obj).
        Returns empty string in case of an error.
        """
        return safe_tio_call(obj_fn, tree_item, log_exceptions=log_exceptions)

    return data_fn


def tio_predicates(tree_item):
    """Returns the inspect module predicates that are true for this object."""
    tio = tree_item.obj
    predicates = [pred.__name__ for pred in _ALL_PREDICATES if pred(tio)]
    return ", ".join(predicates)


def tio_summary(tree_item):
    """
    Returns a small summary of regular objects.
    For callables and modules an empty string is returned.
    """
    tio = tree_item.obj
    if isinstance(tio, six.string_types):
        return tio
    elif isinstance(tio, (list, tuple, set, frozenset, dict)):
        n_items = len(tio)
        if n_items == 0:
            return _("empty {}").format(type(tio).__name__)
        if n_items == 1:
            return _("{} of {} item").format(type(tio).__name__, n_items)
        else:
            return _("{} of {} items").format(type(tio).__name__, n_items)
    elif _NUMPY_INSTALLED and isinstance(tio, np.ndarray):
        return _("array of {}, shape: {}").format(tio.dtype, tio.shape)
    elif callable(tio) or inspect.ismodule(tio):
        return ""
    else:
        return str(tio)


def tio_is_attribute(tree_item):
    """
    Returns 'True' if the tree item object is an attribute of the parent
    opposed to e.g. a list element.
    """
    if tree_item.is_attribute is None:
        return ''
    else:
        return str(tree_item.is_attribute)


def tio_is_callable(tree_item):
    """Returns 'True' if the tree item object is callable."""
    return str(callable(tree_item.obj))  # Python 2
    # return str(hasattr(tree_item.obj, "__call__")) # Python 3?


def tio_doc_str(tree_item):
    """Returns the doc string of an object."""
    tio = tree_item.obj
    try:
        return tio.__doc__
    except AttributeError:
        return _('<no doc string found>')


# Attributes models
class AttributeModel(object):
    """
    Determines how an object attribute is rendered
    in a table column or details pane.
    """
    def __init__(self,
                 name,
                 doc=_("<no help available>"),
                 data_fn=None,
                 col_visible=True,
                 width=SMALL_COL_WIDTH,
                 alignment=ALIGN_LEFT,
                 line_wrap=QTextOption.NoWrap):
        """
        Constructor

        :param name: name used to describe the attribute
        :type name: string
        :param doc: short string documenting the attribute
        :type doc: string
        :param data_fn: function that calculates the value shown in the UI
        :type  data_fn: function(TreeItem_ to string.
        :param col_visible: if True, the attribute is col_visible by default
                            in the table
        :type col_visible: bool
        :param width: default width in the attribute table
        :type with: int
        :param alignment: alignment of the value in the table
        :type alignment: Qt.AlignmentFlag
        :param line_wrap: Line wrap mode of the attribute in the details pane
        :type line_wrap: QtGui.QPlainTextEdit
        """

        if not callable(data_fn):
            raise ValueError("data_fn must be function(TreeItem)->string")

        self.name = name
        self.doc = doc
        self.data_fn = data_fn
        self.col_visible = col_visible
        self.width = width
        self.alignment = alignment
        self.line_wrap = line_wrap

    def __repr__(self):
        """String representation."""
        return _("<AttributeModel for {!r}>").format(self.name)

    @property
    def settings_name(self):
        """The name where spaces are replaced by underscores."""
        sname = self.name.replace(' ', '_')
        return sname.translate(None,
                               string.punctuation).translate(None,
                                                             string.whitespace)


#######################
# Column definitions ##
#######################
ATTR_MODEL_NAME = AttributeModel(
    'name',
    doc=_("The name of the object."),
    data_fn=lambda tree_item: tree_item.obj_name
    if tree_item.obj_name else _('<root>'),
    col_visible=True,
    width=SMALL_COL_WIDTH)


ATTR_MODEL_PATH = AttributeModel(
    'path',
    doc=_("A path to the data: e.g. var[1]['a'].item"),
    data_fn=lambda tree_item: tree_item.obj_path
    if tree_item.obj_path else _('<root>'),
    col_visible=True,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_SUMMARY = AttributeModel(
    'summary',
    doc=_("A summary of the object for regular "
          "objects (is empty for non-regular objects"
          "such as callables or modules)."),
    data_fn=tio_summary,
    col_visible=True,
    alignment=ALIGN_LEFT,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_UNICODE = AttributeModel(
    'unicode',
    doc=_("The unicode representation "
          "of the object. In Python 2 it uses unicode()"
          "In Python 3 the str() function is used."),
    data_fn=lambda tree_item: six.text_type(tree_item.obj),
    col_visible=True,
    width=MEDIUM_COL_WIDTH,
    line_wrap=QTextOption.WrapAtWordBoundaryOrAnywhere)


ATTR_MODEL_STR = AttributeModel(
    'str',
    doc=_("The string representation of the object using the str() function."
          "In Python 3 there is no difference with the 'unicode' column."),
    data_fn=lambda tree_item: str(tree_item.obj),
    col_visible=False,
    width=MEDIUM_COL_WIDTH,
    line_wrap=QTextOption.WrapAtWordBoundaryOrAnywhere)


ATTR_MODEL_REPR = AttributeModel(
    'repr',
    doc=_("The string representation of the "
          "object using the repr() function."),
    data_fn=lambda tree_item: repr(tree_item.obj),
    col_visible=True,
    width=MEDIUM_COL_WIDTH,
    line_wrap=QTextOption.WrapAtWordBoundaryOrAnywhere)


ATTR_MODEL_TYPE = AttributeModel(
    'type',
    doc=_("Type of the object determined using the builtin type() function"),
    data_fn=lambda tree_item: str(type(tree_item.obj)),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_CLASS = AttributeModel(
    'type name',
    doc="The name of the class of the object via obj.__class__.__name__",
    data_fn=lambda tree_item: type(tree_item.obj).__name__,
    col_visible=True,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_LENGTH = AttributeModel(
    'length',
    doc=_("The length of the object using the len() function"),
    # data_fn     = tio_length,
    data_fn=safe_data_fn(len),
    col_visible=False,
    alignment=ALIGN_RIGHT,
    width=SMALL_COL_WIDTH)


ATTR_MODEL_ID = AttributeModel(
    'id',
    doc=_("The identifier of the object with "
          "calculated using the id() function"),
    data_fn=lambda tree_item: "0x{:X}".format(id(tree_item.obj)),
    col_visible=False,
    alignment=ALIGN_RIGHT,
    width=SMALL_COL_WIDTH)


ATTR_MODEL_IS_ATTRIBUTE = AttributeModel(
    'is attribute',
    doc=_("The object is an attribute of the parent "
          "(opposed to e.g. a list element)."
          "Attributes are displayed in italics in the table."),
    data_fn=tio_is_attribute,
    col_visible=False,
    width=SMALL_COL_WIDTH)


ATTR_MODEL_CALLABLE = AttributeModel(
    'is callable',
    doc=_("True if the object is callable."
          "Determined with the `callable` built-in function."
          "Callable objects are displayed in blue in the table."),
    data_fn=tio_is_callable,
    col_visible=True,
    width=SMALL_COL_WIDTH)


ATTR_MODEL_IS_ROUTINE = AttributeModel(
    'is routine',
    doc=_("True if the object is a user-defined or "
          "built-in function or method."
          "Determined with the inspect.isroutine() method."),
    data_fn=lambda tree_item: str(inspect.isroutine(tree_item.obj)),
    col_visible=False,
    width=SMALL_COL_WIDTH)


ATTR_MODEL_PRED = AttributeModel(
    'inspect predicates',
    doc=_("Predicates from the inspect module"),
    data_fn=tio_predicates,
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_PRETTY_PRINT = AttributeModel(
    'pretty print',
    doc=_("Pretty printed representation of "
          "the object using the pprint module."),
    data_fn=lambda tree_item: _PRETTY_PRINTER.pformat(tree_item.obj),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_DOC_STRING = AttributeModel(
    'doc string',
    doc=_("The object's doc string"),
    data_fn=tio_doc_str,
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_GET_DOC = AttributeModel(
    'inspect.getdoc',
    doc=_("The object's doc string, leaned up by inspect.getdoc()"),
    data_fn=safe_data_fn(inspect.getdoc),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_GET_COMMENTS = AttributeModel(
    'inspect.getcomments',
    doc=_("Comments above the object's definition. "
          "Retrieved using inspect.getcomments()"),
    data_fn=lambda tree_item: inspect.getcomments(tree_item.obj),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_GET_MODULE = AttributeModel(
    'inspect.getmodule',
    doc=_("The object's module. Retrieved using inspect.module"),
    data_fn=safe_data_fn(inspect.getmodule),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_GET_FILE = AttributeModel(
    'inspect.getfile',
    doc=_("The object's file. Retrieved using inspect.getfile"),
    data_fn=safe_data_fn(inspect.getfile),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_GET_SOURCE_FILE = AttributeModel(
    'inspect.getsourcefile',  # calls inspect.getfile()
    doc=_("The object's file. Retrieved using inspect.getsourcefile"),
    data_fn=safe_data_fn(inspect.getsourcefile),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_GET_SOURCE_LINES = AttributeModel(
    'inspect.getsourcelines',
    doc=_("Uses inspect.getsourcelines() "
          "to get a list of source lines for the object"),
    data_fn=safe_data_fn(inspect.getsourcelines),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ATTR_MODEL_GET_SOURCE = AttributeModel(
    'inspect.getsource',
    doc=_("The source code of an object retrieved using inspect.getsource"),
    data_fn=safe_data_fn(inspect.getsource),
    col_visible=False,
    width=MEDIUM_COL_WIDTH)


ALL_ATTR_MODELS = (
    ATTR_MODEL_NAME,
    ATTR_MODEL_PATH,
    ATTR_MODEL_SUMMARY,
    ATTR_MODEL_UNICODE,
    ATTR_MODEL_STR,
    ATTR_MODEL_REPR,
    ATTR_MODEL_TYPE,
    ATTR_MODEL_CLASS,
    ATTR_MODEL_LENGTH,
    ATTR_MODEL_ID,
    ATTR_MODEL_IS_ATTRIBUTE,
    ATTR_MODEL_CALLABLE,
    ATTR_MODEL_IS_ROUTINE,
    ATTR_MODEL_PRED,
    ATTR_MODEL_PRETTY_PRINT,
    ATTR_MODEL_DOC_STRING,
    ATTR_MODEL_GET_DOC,
    ATTR_MODEL_GET_COMMENTS,
    ATTR_MODEL_GET_MODULE,
    ATTR_MODEL_GET_FILE,
    ATTR_MODEL_GET_SOURCE_FILE,
    ATTR_MODEL_GET_SOURCE_LINES,
    ATTR_MODEL_GET_SOURCE)

DEFAULT_ATTR_COLS = (
    ATTR_MODEL_NAME,
    ATTR_MODEL_PATH,
    ATTR_MODEL_SUMMARY,
    ATTR_MODEL_UNICODE,
    ATTR_MODEL_STR,
    ATTR_MODEL_REPR,
    ATTR_MODEL_LENGTH,
    ATTR_MODEL_TYPE,
    ATTR_MODEL_CLASS,
    ATTR_MODEL_ID,
    ATTR_MODEL_IS_ATTRIBUTE,
    ATTR_MODEL_CALLABLE,
    ATTR_MODEL_IS_ROUTINE,
    ATTR_MODEL_PRED,
    ATTR_MODEL_GET_MODULE,
    ATTR_MODEL_GET_FILE,
    ATTR_MODEL_GET_SOURCE_FILE)

DEFAULT_ATTR_DETAILS = (
    ATTR_MODEL_PATH,  # to allow for copy/paste
    # ATTR_MODEL_SUMMARY, # Too similar to unicode column
    ATTR_MODEL_UNICODE,
    # ATTR_MODEL_STR, # Too similar to unicode column
    ATTR_MODEL_REPR,
    ATTR_MODEL_PRETTY_PRINT,
    # ATTR_MODEL_DOC_STRING, # not used, too similar to ATTR_MODEL_GET_DOC
    ATTR_MODEL_GET_DOC,
    ATTR_MODEL_GET_COMMENTS,
    # ATTR_MODEL_GET_MODULE, # not used, already in table
    ATTR_MODEL_GET_FILE,
    # ATTR_MODEL_GET_SOURCE_FILE,  # not used, already in table
    # ATTR_MODEL_GET_SOURCE_LINES, # not used, ATTR_MODEL_GET_SOURCE is better
    ATTR_MODEL_GET_SOURCE)

# Sanity check for duplicates
assert len(ALL_ATTR_MODELS) == len(set(ALL_ATTR_MODELS))
assert len(DEFAULT_ATTR_COLS) == len(set(DEFAULT_ATTR_COLS))
assert len(DEFAULT_ATTR_DETAILS) == len(set(DEFAULT_ATTR_DETAILS))


# Toogle mixin
class ToggleColumnMixIn(object):
    """
    Adds actions to a QTableView that can show/hide columns
    by right clicking on the header
    """
    def add_header_context_menu(self, checked=None, checkable=None,
                                enabled=None):
        """
        Adds the context menu from using header information

        checked can be a header_name -> boolean dictionary. If given, headers
        with the key name will get the checked value from the dictionary.
        The corresponding column will be hidden if checked is False.

        checkable can be a header_name -> boolean dictionary. If given, headers
        with the key name will get the checkable value from the dictionary.

        enabled can be a header_name -> boolean dictionary. If given, headers
        with the key name will get the enabled value from the dictionary.
        """
        checked = checked if checked is not None else {}
        checkable = checkable if checkable is not None else {}
        enabled = enabled if enabled is not None else {}

        horizontal_header = self._horizontal_header()
        horizontal_header.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.toggle_column_actions_group = QActionGroup(self)
        self.toggle_column_actions_group.setExclusive(False)
        self.__toggle_functions = []  # for keeping references

        for col in range(horizontal_header.count()):
            column_label = self.model().headerData(col, Qt.Horizontal,
                                                   Qt.DisplayRole)
            logger.debug("Adding: col {}: {}".format(col, column_label))
            action = QAction(str(column_label),
                             self.toggle_column_actions_group,
                             checkable=checkable.get(column_label, True),
                             enabled=enabled.get(column_label, True),
                             toolTip="Shows or hides "
                                     "the {} column".format(column_label))
            func = self.__make_show_column_function(col)
            self.__toggle_functions.append(func)  # keep reference
            horizontal_header.addAction(action)
            is_checked = checked.get(
                column_label,
                not horizontal_header.isSectionHidden(col))
            horizontal_header.setSectionHidden(col, not is_checked)
            action.setChecked(is_checked)
            action.toggled.connect(func)

    def get_header_context_menu_actions(self):
        """Returns the actions of the context menu of the header."""
        return self._horizontal_header().actions()

    def _horizontal_header(self):
        """
        Returns the horizontal header (of type QHeaderView).

        Override this if the horizontalHeader() function does not exist.
        """
        return self.horizontalHeader()

    def __make_show_column_function(self, column_idx):
        """Creates a function that shows or hides a column."""
        show_column = lambda checked: self.setColumnHidden(column_idx,
                                                           not checked)
        return show_column

    def read_view_settings(self, key, settings=None, reset=False):
        """
        Reads the persistent program settings

        :param reset: If True, the program resets to its default settings
        :returns: True if the header state was restored, otherwise returns
                  False
        """
        logger.debug("Reading view settings for: {}".format(key))
        header_restored = False
#        if not reset:
#            if settings is None:
#                settings = get_qsettings()
#            horizontal_header = self._horizontal_header()
#            header_data = settings.value(key)
#            if header_data:
#                header_restored = horizontal_header.restoreState(header_data)
#
#            # update actions
#            for col, action in enumerate(horizontal_header.actions()):
#                is_checked = not horizontal_header.isSectionHidden(col)
#                action.setChecked(is_checked)

        return header_restored

    def write_view_settings(self, key, settings=None):
        """Writes the view settings to the persistent store."""
        logger.debug("Writing view settings for: {}".format(key))
#
#        if settings is None:
#            settings = get_qsettings()
#        settings.setValue(key, self._horizontal_header().saveState())


class ToggleColumnTableWidget(QTableWidget, ToggleColumnMixIn):
    """
    A QTableWidget where right clicking on the header allows the user
    to show/hide columns.
    """
    pass


class ToggleColumnTreeWidget(QTreeWidget, ToggleColumnMixIn):
    """
    A QTreeWidget where right clicking on the header allows the user to
    show/hide columns.
    """
    def _horizontal_header(self):
        """
        Returns the horizontal header (of type QHeaderView).

        Override this if the horizontalHeader() function does not exist.
        """
        return self.header()


class ToggleColumnTreeView(QTreeView, ToggleColumnMixIn):
    """
    A QTreeView where right clicking on the header allows the user to
    show/hide columns.
    """
    def _horizontal_header(self):
        """
        Returns the horizontal header (of type QHeaderView).

        Override this if the horizontalHeader() function does not exist.
        """
        return self.header()


# TreeWidget Elements
class TreeItem(object):
    """Tree node class that can be used to build trees of objects."""
    def __init__(self, obj, name, obj_path, is_attribute, parent=None):
        self.parent_item = parent
        self.obj = obj
        self.obj_name = str(name)
        self.obj_path = str(obj_path)
        self.is_attribute = is_attribute
        self.child_items = []
        self.has_children = True
        self.children_fetched = False

    def __str__(self):
        n_children = len(self.child_items)
        if n_children == 0:
            return "<TreeItem(0x{:x}): {} = {}>".format(
                id(self.obj),
                self.obj_path,
                cut_off_str(self.obj, MAX_OBJ_STR_LEN))
        else:
            return "<TreeItem(0x{:x}): {} ({:d} children)>".format(
                id(self.obj),
                self.obj_path,
                len(self.child_items))

    def __repr__(self):
        n_children = len(self.child_items)
        return "<TreeItem(0x{:x}): {} ({:d} children)>" \
            .format(id(self.obj), self.obj_path, n_children)

    @property
    def is_special_attribute(self):
        """
        Return true if the items is an attribute and its
        name begins and end with 2 underscores.
        """
        return self.is_attribute and name_is_special(self.obj_name)

    @property
    def is_callable_attribute(self):
        """Return true if the items is an attribute and it is callable."""
        return self.is_attribute and self.is_callable

    @property
    def is_callable(self):
        """Return true if the underlying object is callable."""
        return callable(self.obj)

    def append_child(self, item):
        item.parent_item = self
        self.child_items.append(item)

    def insert_children(self, idx, items):
        self.child_items[idx:idx] = items
        for item in items:
            item.parent_item = self

    def child(self, row):
        return self.child_items[row]

    def child_count(self):
        return len(self.child_items)

    def parent(self):
        return self.parent_item

    def row(self):
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        else:
            return 0

    def pretty_print(self, indent=0):
        if 0:
            print(indent * "    " + str(self))
        else:
            logger.debug(indent * "    " + str(self))
        for child_item in self.child_items:
            child_item.pretty_print(indent + 1)


# Based on: PySide examples/itemviews/simpletreemodel
# See: https://github.com/PySide/Examples/blob/master/examples/
# itemviews/simpletreemodel/simpletreemodel.py

# TODO: a lot of methods (e.g. rowCount) test if parent.column() > 0.
# This should probably be replaced with an assert.

# Keep the method names camelCase since it inherits from a Qt object.
# Disabled need for docstrings. For a good explanation of the methods,
# take a look at the Qt simple tree model example.
# See: http://harmattan-dev.nokia.com/docs/
# library/html/qt4/itemviews-simpletreemodel.html

# The main window inherits from a Qt class, therefore it has many
# ancestors public methods and attributes.
class TreeModel(QAbstractItemModel):
    """
    Model that provides an interface to an objectree
    that is build of TreeItems.
    """
    def __init__(self,
                 obj,
                 obj_name='',
                 attr_cols=None,
                 parent=None):
        """
        Constructor

        :param obj: any Python object or variable
        :param obj_name: name of the object as it will appear in the root node
                         If empty, no root node will be drawn.
        :param attr_cols: list of AttributeColumn definitions
        :param parent: the parent widget
        """
        super(TreeModel, self).__init__(parent)
        self._attr_cols = attr_cols

        self.regular_font = QFont()  # Font for members (non-functions)
        # Font for __special_attributes__
        self.special_attribute_font = QFont()
        self.special_attribute_font.setItalic(True)

        self.regular_color = QBrush(QColor('black'))
        self.callable_color = QBrush(
            QColor('mediumblue'))  # for functions, methods, etc.

        # The following members will be initialized by populateTree
        # The rootItem is always invisible. If the obj_name
        # is the empty string, the inspectedItem
        # will be the rootItem (and therefore be invisible).
        # If the obj_name is given, an
        # invisible root item will be added and the
        # inspectedItem will be its only child.
        # In that case the inspected item will be visible.
        self._inspected_node_is_visible = None
        self._inspected_item = None
        self._root_item = None
        self.populateTree(obj, obj_name)

    @property
    def inspectedNodeIsVisible(self):
        """
        Returns True if the inspected node is visible.
        In that case an invisible root node has been added.
        """
        return self._inspected_node_is_visible

    @property
    def rootItem(self):
        """ The root TreeItem.
        """
        return self._root_item

    @property
    def inspectedItem(self):  # TODO: needed?
        """The TreeItem that contains the item under inspection."""
        return self._inspected_item

    def rootIndex(self):  # TODO: needed?
        """
        The index that returns the root element
        (same as an invalid index).
        """
        return QModelIndex()

    def inspectedIndex(self):
        """The model index that point to the inspectedItem."""
        if self.inspectedNodeIsVisible:
            return self.createIndex(0, 0, self._inspected_item)
        else:
            return self.rootIndex()

    def columnCount(self, _parent=None):
        """ Returns the number of columns in the tree """
        return len(self._attr_cols)

    def data(self, index, role):
        """Returns the tree item at the given index and role."""
        if not index.isValid():
            return None

        col = index.column()
        tree_item = index.internalPointer()
        obj = tree_item.obj

        if role == Qt.DisplayRole:
            try:
                attr = self._attr_cols[col].data_fn(tree_item)
                # Replace carriage returns and line feeds with unicode glyphs
                # so that all table rows fit on one line.
                # return attr.replace('\n',
                #                     unichr(0x240A)).replace('\r',
                #                     unichr(0x240D))
                return (attr.replace('\r\n', unichr(0x21B5))
                            .replace('\n', unichr(0x21B5))
                            .replace('\r', unichr(0x21B5)))
            except Exception as ex:
                # logger.exception(ex)
                return "**ERROR**: {}".format(ex)

        elif role == Qt.TextAlignmentRole:
            return self._attr_cols[col].alignment

        elif role == Qt.ForegroundRole:
            if tree_item.is_callable:
                return self.callable_color
            else:
                return self.regular_color

        elif role == Qt.FontRole:
            if tree_item.is_attribute:
                return self.special_attribute_font
            else:
                return self.regular_font
        else:
            return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._attr_cols[section].name
        else:
            return None

    def treeItem(self, index):
        if not index.isValid():
            return self.rootItem
        else:
            return index.internalPointer()

    def index(self, row, column, parent=None):

        if parent is None:
            logger.debug("parent is None")
            parent = QModelIndex()

        parentItem = self.treeItem(parent)

        if not self.hasIndex(row, column, parent):
            logger.debug("hasIndex "
                         "is False: ({}, {}) {!r}".format(row,
                                                          column, parentItem))
            # logger.warn("Parent index model"
            #             ": {!r} != {!r}".format(parent.model(), self))

            return QModelIndex()

        childItem = parentItem.child(row)
        # logger.debug("  {}".format(childItem.obj_path))
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            logger.warn("no childItem")
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent()

        if parent_item is None or parent_item == self.rootItem:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent=None):
        parent = QModelIndex() if parent is None else parent

        if parent.column() > 0:
            # This is taken from the PyQt simpletreemodel example.
            return 0
        else:
            return self.treeItem(parent).child_count()

    def hasChildren(self, parent=None):
        parent = QModelIndex() if parent is None else parent
        if parent.column() > 0:
            return 0
        else:
            return self.treeItem(parent).has_children

    def canFetchMore(self, parent=None):
        parent = QModelIndex() if parent is None else parent
        if parent.column() > 0:
            return 0
        else:
            result = not self.treeItem(parent).children_fetched
            # logger.debug("canFetchMore: {} = {}".format(parent, result))
            return result

    def fetchMore(self, parent=None):
        """
        Fetches the children given the model index of a parent node.
        Adds the children to the parent.
        """
        parent = QModelIndex() if parent is None else parent
        if parent.column() > 0:
            return

        parent_item = self.treeItem(parent)
        if parent_item.children_fetched:
            return

        tree_items = self._fetchObjectChildren(parent_item.obj,
                                               parent_item.obj_path)

        self.beginInsertRows(parent, 0, len(tree_items) - 1)
        for tree_item in tree_items:
            parent_item.append_child(tree_item)

        parent_item.children_fetched = True
        self.endInsertRows()

    def _fetchObjectChildren(self, obj, obj_path):
        """
        Fetches the children of a Python object.
        Returns: list of TreeItems
        """
        obj_children = []
        path_strings = []

        if isinstance(obj, (list, tuple)):
            obj_children = sorted(enumerate(obj))
            path_strings = ['{}[{}]'.format(obj_path,
                            item[0]) if obj_path else item[0]
                            for item in obj_children]
        elif isinstance(obj, (set, frozenset)):
            obj_children = [('pop()', elem) for elem in obj]
            path_strings = ['{0}.pop()'.format(obj_path,
                            item[0]) if obj_path else item[0]
                            for item in obj_children]
        elif hasattr(obj, 'items'):  # dictionaries and the likes.
            try:
                obj_children = list(obj.items())
            except Exception as ex:
                # Can happen if the items method expects an argument,
                # for instance the types.DictType.items
                # method expects a dictionary.
                logger.warn("No items expanded. "
                            "Objects items() call failed: {}".format(ex))
                obj_children = []

            # Sort keys, except when the object is an OrderedDict.
            if not isinstance(obj, OrderedDict):
                try:
                    obj_children = sorted(obj.items())
                except Exception as ex:
                    logger.debug("Unable to sort "
                                 "dictionary keys: {}".format(ex))

            path_strings = ['{}[{!r}]'.format(obj_path,
                            item[0]) if obj_path else item[0]
                            for item in obj_children]

        assert len(obj_children) == len(path_strings), "sanity check"
        is_attr_list = [False] * len(obj_children)

        # Object attributes
        for attr_name, attr_value in sorted(inspect.getmembers(obj)):
            obj_children.append((attr_name, attr_value))
            path_strings.append('{}.{}'.format(obj_path,
                                attr_name) if obj_path else attr_name)
            is_attr_list.append(True)

        assert len(obj_children) == len(path_strings), "sanity check"
        tree_items = []
        for item, path_str, is_attr in zip(obj_children, path_strings,
                                           is_attr_list):
            name, child_obj = item
            tree_items.append(TreeItem(child_obj, name, path_str, is_attr))

        return tree_items

    def populateTree(self, obj, obj_name='', inspected_node_is_visible=None):
        """Fills the tree using a python object. Sets the rootItem."""
        logger.debug("populateTree with object id = 0x{:x}".format(id(obj)))

        if inspected_node_is_visible is None:
            inspected_node_is_visible = (obj_name != '')
        self._inspected_node_is_visible = inspected_node_is_visible

        if self._inspected_node_is_visible:
            self._root_item = TreeItem(None, _('<invisible_root>'),
                                       _('<invisible_root>'), None)
            self._root_item.children_fetched = True
            self._inspected_item = TreeItem(obj, obj_name,
                                            obj_name, is_attribute=None)
            self._root_item.append_child(self._inspected_item)
        else:
            # The root itself will be invisible
            self._root_item = TreeItem(obj, obj_name,
                                       obj_name, is_attribute=None)
            self._inspected_item = self._root_item

            # Fetch all items of the root so we can
            # select the first row in the constructor.
            root_index = self.index(0, 0)
            self.fetchMore(root_index)

    def _auxRefreshTree(self, tree_index):
        """
        Auxiliary function for refreshTree that recursively refreshes the
        tree nodes.

        If the underlying Python object has been changed, we don't want to
        delete the old tree model and create a new one from scratch because
        this loses all information about which nodes are fetched and expanded.
        Instead the old tree model is updated. Using the difflib from the
        standard library it is determined for a parent node which child nodes
        should be added or removed. This is done based on the node names only,
        not on the node contents (the underlying Python objects). Testing the
        underlying nodes for equality is potentially slow. It is faster to
        let the refreshNode function emit the dataChanged signal for all cells.
        """
        tree_item = self.treeItem(tree_index)
        logger.debug("_auxRefreshTree({}): {}{}".format(
            tree_index, tree_item.obj_path,
            "*" if tree_item.children_fetched else ""))

        if tree_item.children_fetched:

            old_items = tree_item.child_items
            new_items = self._fetchObjectChildren(tree_item.obj,
                                                  tree_item.obj_path)

            old_item_names = [(item.obj_name,
                               item.is_attribute) for item in old_items]
            new_item_names = [(item.obj_name,
                               item.is_attribute) for item in new_items]
            seqMatcher = SequenceMatcher(isjunk=None, a=old_item_names,
                                         b=new_item_names,
                                         autojunk=False)
            opcodes = seqMatcher.get_opcodes()

            logger.debug("(reversed) "
                         "opcodes: {}".format(list(reversed(opcodes))))

            for tag, i1, i2, j1, j2 in reversed(opcodes):

                if 1 or tag != 'equal':
                    logger.debug("  {:7s}, a[{}:{}] ({}), b[{}:{}] ({})"
                                 .format(tag, i1, i2,
                                         old_item_names[i1:i2], j1, j2,
                                         new_item_names[j1:j2]))

                if tag == 'equal':
                    # Only when node names are equal is _auxRefreshTree
                    # called recursively.
                    assert i2-i1 == j2-j1, ("equal sanity "
                                            "check failed "
                                            "{} != {}".format(i2-i1, j2-j1))
                    for old_row, new_row in zip(range(i1, i2), range(j1, j2)):
                        old_items[old_row].obj = new_items[new_row].obj
                        child_index = self.index(old_row, 0, parent=tree_index)
                        self._auxRefreshTree(child_index)

                elif tag == 'replace':
                    # Explicitly remove the old item and insert the new.
                    # The old item may have child nodes which indices must be
                    # removed by Qt, otherwise it crashes.
                    assert i2-i1 == j2-j1, ("replace sanity "
                                            "check failed "
                                            "{} != {}").format(i2-i1, j2-j1)

                    # row number of first removed
                    first = i1
                    # row number of last element after insertion
                    last = i1 + i2 - 1
                    logger.debug("     calling "
                                 "beginRemoveRows({}, {}, {})".format(
                                    tree_index, first, last))
                    self.beginRemoveRows(tree_index, first, last)
                    del tree_item.child_items[i1:i2]
                    self.endRemoveRows()

                    # row number of first element after insertion
                    first = i1
                    # row number of last element after insertion
                    last = i1 + j2 - j1 - 1
                    logger.debug("     calling "
                                 "beginInsertRows({}, {}, {})".format(
                                    tree_index, first, last))
                    self.beginInsertRows(tree_index, first, last)
                    tree_item.insert_children(i1, new_items[j1:j2])
                    self.endInsertRows()

                elif tag == 'delete':
                    assert j1 == j2, ("delete"
                                      " sanity check "
                                      "failed. {} != {}".format(j1, j2))
                    # row number of first that will be removed
                    first = i1
                    # row number of last element after insertion
                    last = i1 + i2 - 1
                    logger.debug("     calling "
                                 "beginRemoveRows"
                                 "({}, {}, {})".format(tree_index,
                                                       first, last))
                    self.beginRemoveRows(tree_index, first, last)
                    del tree_item.child_items[i1:i2]
                    self.endRemoveRows()

                elif tag == 'insert':
                    assert i1 == i2, ("insert "
                                      "sanity check "
                                      "failed. {} != {}".format(i1, i2))
                    # row number of first element after insertion
                    first = i1
                    # row number of last element after insertion
                    last = i1 + j2 - j1 - 1
                    logger.debug("     "
                                 "calling beginInsertRows"
                                 "({}, {}, {})".format(tree_index,
                                                       first, last))
                    self.beginInsertRows(tree_index, first, last)
                    tree_item.insert_children(i1, new_items[j1:j2])
                    self.endInsertRows()
                else:
                    raise ValueError("Invalid tag: {}".format(tag))

    def refreshTree(self):
        """
        Refreshes the tree model from the underlying root object
        (which may have been changed).
        """
        logger.info("")
        logger.info("refreshTree: {}".format(self.rootItem))

        root_item = self.treeItem(self.rootIndex())
        logger.info("  root_item:      {} (idx={})".format(root_item,
                                                           self.rootIndex()))
        inspected_item = self.treeItem(self.inspectedIndex())
        logger.info("  inspected_item: {} (idx={})".format(
            inspected_item,
            self.inspectedIndex()))

        assert (root_item is inspected_item) != self.inspectedNodeIsVisible, \
            "sanity check"

        self._auxRefreshTree(self.inspectedIndex())

        root_obj = self.rootItem.obj
        logger.debug("After _auxRefreshTree, "
                     "root_obj: {}".format(cut_off_str(root_obj, 80)))
        self.rootItem.pretty_print()

        # Emit the dataChanged signal for all cells.
        # This is faster than checking which nodes
        # have changed, which may be slow for some underlying Python objects.
        n_rows = self.rowCount()
        n_cols = self.columnCount()
        top_left = self.index(0, 0)
        bottom_right = self.index(n_rows-1, n_cols-1)

        logger.debug("bottom_right: ({}, {})".format(bottom_right.row(),
                                                     bottom_right.column()))
        self.dataChanged.emit(top_left, bottom_right)


class TreeProxyModel(QSortFilterProxyModel):
    """Proxy model that overrides the sorting and can filter out items."""
    def __init__(self,
                 show_callable_attributes=True,
                 show_special_attributes=True,
                 parent=None):
        """
        Constructor

        :param show_callable_attributes: if True the callables objects,
            i.e. objects (such as function) that  a __call__ method,
            will be displayed (in brown). If False they are hidden.
        :param show_special_attributes: if True the objects special attributes,
            i.e. methods with a name that starts and ends with two underscores,
            will be displayed (in italics). If False they are hidden.
        :param parent: the parent widget
        """
        super(TreeProxyModel, self).__init__(parent)

        self._show_callables = show_callable_attributes
        self._show_special_attributes = show_special_attributes

    def treeItem(self, proxy_index):
        index = self.mapToSource(proxy_index)
        return self.sourceModel().treeItem(index)

    def firstItemIndex(self):
        """Returns the first child of the root item."""
        # We cannot just call the same function of the source model
        # because the first node there may be hidden.
        source_root_index = self.sourceModel().rootIndex()
        proxy_root_index = self.mapFromSource(source_root_index)
        first_item_index = self.index(0, 0, proxy_root_index)
        return first_item_index

    def filterAcceptsRow(self, sourceRow, sourceParentIndex):
        """
        Returns true if the item in the row indicated by the given source_row
        and source_parent should be included in the model.
        """
        parent_item = self.sourceModel().treeItem(sourceParentIndex)
        tree_item = parent_item.child(sourceRow)

        accept = ((self._show_special_attributes or
                   not tree_item.is_special_attribute) and
                  (self._show_callables or
                   not tree_item.is_callable_attribute))

        # logger.debug("filterAcceptsRow = {}: {}".format(accept, tree_item))
        return accept

    def getShowCallables(self):
        return self._show_callables

    def setShowCallables(self, show_callables):
        """
        Shows/hides show_callables, which have a __call__ attribute.
        Repopulates the tree.
        """
        logger.debug("setShowCallables: {}".format(show_callables))
        self._show_callables = show_callables
        self.invalidateFilter()

    def getShowSpecialAttributes(self):
        return self._show_special_attributes

    def setShowSpecialAttributes(self, show_special_attributes):
        """
        Shows/hides special attributes, which begin with an underscore.
        Repopulates the tree.
        """
        logger.debug("setShowSpecialAttributes:"
                     " {}".format(show_special_attributes))
        self._show_special_attributes = show_special_attributes
        self.invalidateFilter()


class ObjectBrowser(QDialog):
    """Object browser main widget window."""
    _browsers = []  # Keep lists of browser windows.

    def __init__(self,
                 obj,
                 name='',
                 attribute_columns=DEFAULT_ATTR_COLS,
                 attribute_details=DEFAULT_ATTR_DETAILS,
                 show_callable_attributes=None,  # Uses value from QSettings
                 show_special_attributes=None,  # Uses value from QSettings
                 auto_refresh=None,  # Uses value from QSettings
                 refresh_rate=None,  # Uses value from QSettings
                 reset=False):
        """
        Constructor

        :param name: name of the object as it will appear in the root node
        :param obj: any Python object or variable
        :param attribute_columns: list of AttributeColumn objects that
            define which columns are present in the table and their defaults
        :param attribute_details: list of AttributeDetails objects that define
            which attributes can be selected in the details pane.
        :param show_callable_attributes: if True rows where the 'is attribute'
            and 'is callable' columns are both True, are displayed.
            Otherwise they are hidden.
        :param show_special_attributes: if True rows where the 'is attribute'
            is True and the object name starts and ends with two underscores,
            are displayed. Otherwise they are hidden.
        :param auto_refresh: If True, the contents refershes itsef every
            <refresh_rate> seconds.
        :param refresh_rate: number of seconds between automatic refreshes.
            Default = 2 .
        :param reset: If true the persistent settings, such as column widths,
            are reset.
        """
        super(ObjectBrowser, self).__init__()

        self._instance_nr = self._add_instance()

        # Model
        self._attr_cols = attribute_columns
        self._attr_details = attribute_details

        (self._auto_refresh,
         self._refresh_rate,
         show_callable_attributes,
         show_special_attributes) = self._readModelSettings(
            reset=reset,
            auto_refresh=auto_refresh,
            refresh_rate=refresh_rate,
            show_callable_attributes=show_callable_attributes,
            show_special_attributes=show_special_attributes)

        self._tree_model = TreeModel(obj, name, attr_cols=self._attr_cols)

        self._proxy_tree_model = TreeProxyModel(
            show_callable_attributes=show_callable_attributes,
            show_special_attributes=show_special_attributes)

        self._proxy_tree_model.setSourceModel(self._tree_model)
        # self._proxy_tree_model.setSortRole(RegistryTableModel.SORT_ROLE)
        self._proxy_tree_model.setDynamicSortFilter(True)
        # self._proxy_tree_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        # Views
        self._setup_actions()
        self._setup_menu()
        self._setup_views()
        self.setWindowTitle("{} - {}".format(PROGRAM_NAME, name))

        self._readViewSettings(reset=reset)

        assert self._refresh_rate > 0, ("refresh_rate must be > 0."
                                        " Got: {}".format(self._refresh_rate))
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(self._refresh_rate * 1000)
        self._refresh_timer.timeout.connect(self.refresh)

        # Update views with model
        self.toggle_special_attribute_action.setChecked(
            show_special_attributes)
        self.toggle_callable_action.setChecked(show_callable_attributes)
        self.toggle_auto_refresh_action.setChecked(self._auto_refresh)

        # Select first row so that a hidden root node will not be selected.
        first_row_index = self._proxy_tree_model.firstItemIndex()
        self.obj_tree.setCurrentIndex(first_row_index)
        if self._tree_model.inspectedNodeIsVisible:
            self.obj_tree.expand(first_row_index)

    def refresh(self):
        """Refreshes object brawser contents."""
        logger.debug("Refreshing")
        self._tree_model.refreshTree()

    def _add_instance(self):
        """
        Adds the browser window to the list of browser references.
        If a None is present in the list it is inserted at that position,
        otherwise it is appended to the list. The index number is returned.

        This mechanism is used so that repeatedly creating and closing windows
        does not increase the instance number, which is used in writing
        the persistent settings.
        """
        try:
            idx = self._browsers.index(None)
        except ValueError:
            self._browsers.append(self)
            idx = len(self._browsers) - 1
        else:
            self._browsers[idx] = self

        return idx

    def _remove_instance(self):
        """Sets the reference in the browser list to None."""
        idx = self._browsers.index(self)
        self._browsers[idx] = None

    def _make_show_column_function(self, column_idx):
        """Creates a function that shows or hides a column."""
        show_column = lambda checked: self.obj_tree.setColumnHidden(
            column_idx, not checked)
        return show_column

    def _setup_actions(self):
        """Creates the main window actions."""
        # Show/hide callable objects
        self.toggle_callable_action = \
            QAction("Show callable attributes", self, checkable=True,
                    shortcut=QKeySequence("Alt+C"),
                    statusTip="Shows/hides attributes "
                              "that are callable (functions, methods, etc)")
        self.toggle_callable_action.toggled.connect(
            self._proxy_tree_model.setShowCallables)

        # Show/hide special attributes
        self.toggle_special_attribute_action = \
            QAction("Show __special__ attributes", self, checkable=True,
                    shortcut=QKeySequence("Alt+S"),
                    statusTip="Shows or hides __special__ attributes")
        self.toggle_special_attribute_action.toggled.connect(
            self._proxy_tree_model.setShowSpecialAttributes)

        # Toggle auto-refresh on/off
        self.toggle_auto_refresh_action = \
            QAction("Auto-refresh", self, checkable=True,
                    statusTip="Auto refresh every "
                              "{} seconds".format(self._refresh_rate))
        self.toggle_auto_refresh_action.toggled.connect(
            self.toggle_auto_refresh)

        # Add another refresh action with a different short cut. An action
        # must be added to a visible widget for it to receive events.
        # from being displayed again in the menu
        self.refresh_action_f5 = QAction(self, text="&Refresh2", shortcut="F5")
        self.refresh_action_f5.triggered.connect(self.refresh)
        self.addAction(self.refresh_action_f5)

    def _setup_menu(self):
        """Sets up the main menu."""
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        menuBar = QMenuBar()
        view_menu = menuBar.addMenu("&View")
        view_menu.addAction("&Refresh", self.refresh, "Ctrl+R")
        view_menu.addAction(self.toggle_auto_refresh_action)

        view_menu.addSeparator()
        self.show_cols_submenu = view_menu.addMenu("Table columns")
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_callable_action)
        view_menu.addAction(self.toggle_special_attribute_action)

        menuBar.addSeparator()
        help_menu = menuBar.addMenu("&Help")
        help_menu.addAction('&About', self.about)
        self.layout.setMenuBar(menuBar)

    def _setup_views(self):
        """Creates the UI widgets."""
        self.central_splitter = QSplitter(self, orientation=Qt.Vertical)
        self.layout.addWidget(self.central_splitter)

        # Tree widget
        self.obj_tree = ToggleColumnTreeView()
        self.obj_tree.setAlternatingRowColors(True)
        self.obj_tree.setModel(self._proxy_tree_model)
        self.obj_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.obj_tree.setUniformRowHeights(True)
        self.obj_tree.setAnimated(True)
        self.obj_tree.add_header_context_menu()

        # Stretch last column?
        # It doesn't play nice when columns are hidden and then shown again.
        obj_tree_header = self.obj_tree.header()
        obj_tree_header.setSectionsMovable(True)
        obj_tree_header.setStretchLastSection(False)
        for action in self.obj_tree.toggle_column_actions_group.actions():
            self.show_cols_submenu.addAction(action)

        self.central_splitter.addWidget(self.obj_tree)

        # Bottom pane
        bottom_pane_widget = QWidget()
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(0)
        bottom_layout.setContentsMargins(5, 5, 5, 5)  # left top right bottom
        bottom_pane_widget.setLayout(bottom_layout)
        self.central_splitter.addWidget(bottom_pane_widget)

        group_box = QGroupBox("Details")
        bottom_layout.addWidget(group_box)

        group_layout = QHBoxLayout()
        group_layout.setContentsMargins(2, 2, 2, 2)  # left top right bottom
        group_box.setLayout(group_layout)

        # Radio buttons
        radio_widget = QWidget()
        radio_layout = QVBoxLayout()
        radio_layout.setContentsMargins(0, 0, 0, 0)  # left top right bottom
        radio_widget.setLayout(radio_layout)

        self.button_group = QButtonGroup(self)
        for button_id, attr_detail in enumerate(self._attr_details):
            radio_button = QRadioButton(attr_detail.name)
            radio_layout.addWidget(radio_button)
            self.button_group.addButton(radio_button, button_id)

        self.button_group.buttonClicked[int].connect(
            self._change_details_field)
        self.button_group.button(0).setChecked(True)

        radio_layout.addStretch(1)
        group_layout.addWidget(radio_widget)

        # Editor widget
        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        # font.setPointSize(14)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setFont(font)
        group_layout.addWidget(self.editor)

        # Splitter parameters
        self.central_splitter.setCollapsible(0, False)
        self.central_splitter.setCollapsible(1, True)
        self.central_splitter.setSizes([400, 200])
        self.central_splitter.setStretchFactor(0, 10)
        self.central_splitter.setStretchFactor(1, 0)

        # Connect signals
        # Keep a temporary reference of the selection_model to prevent
        # segfault in PySide.
        # See http://permalink.gmane.org/gmane.comp.lib.qt.pyside.devel/222
        selection_model = self.obj_tree.selectionModel()
        selection_model.currentChanged.connect(self._update_details)

    # End of setup_methods
    def _settings_group_name(self, postfix):
        """
        Constructs a group name for the persistent settings.

        Because the columns in the main table are extendible, we must
        store the settings in a different group if a different combination of
        columns is used. Therefore the settings group name contains a hash that
        is calculated from the used column names. Furthermore the window
        number is included in the settings group name. Finally a
        postfix string is appended.
        """
        column_names = ",".join([col.name for col in self._attr_cols])
        settings_str = column_names
        columns_hash = hashlib.md5(settings_str.encode('utf-8')).hexdigest()
        settings_grp = "{}_win{}_{}".format(columns_hash, self._instance_nr,
                                            postfix)
        return settings_grp

    def _readModelSettings(self,
                           reset=False,
                           auto_refresh=None,
                           refresh_rate=None,
                           show_callable_attributes=None,
                           show_special_attributes=None):
        """
        Reads the persistent model settings .
        The persistent settings (show_callable_attributes,
        show_special_attributes)
        can be overridden by giving it a True or False value.
        If reset is True and the setting is None, True is used as default.
        """
        default_auto_refresh = False
        default_refresh_rate = 2
        default_sra = True
        default_ssa = True
        if reset:
            logger.debug("Resetting persistent model settings")
            if refresh_rate is None:
                refresh_rate = default_refresh_rate
            if auto_refresh is None:
                auto_refresh = default_auto_refresh
            if show_callable_attributes is None:
                show_callable_attributes = default_sra
            if show_special_attributes is None:
                show_special_attributes = default_ssa
        else:
            logger.debug("Reading "
                         "model settings for window: {:d}".format(
                             self._instance_nr))
#            settings = get_qsettings()
#            settings.beginGroup(self._settings_group_name('model'))

            if auto_refresh is None:
                auto_refresh = default_auto_refresh

            if refresh_rate is None:
                refresh_rate = default_refresh_rate

            if show_callable_attributes is None:
                show_callable_attributes = default_sra

            if show_special_attributes is None:
                show_special_attributes = default_ssa

        return (auto_refresh, refresh_rate,
                show_callable_attributes, show_special_attributes)

    def _readViewSettings(self, reset=False):
        """
        Reads the persistent program settings.

        :param reset: If True, the program resets to its default settings.
        """
        pos = QPoint(20 * self._instance_nr, 20 * self._instance_nr)
        window_size = QSize(1024, 700)
        details_button_idx = 0

        header = self.obj_tree.header()
        header_restored = False

        if reset:
            logger.debug("Resetting persistent view settings")
        else:
            pos = pos
            window_size = window_size
            details_button_idx = details_button_idx
#            splitter_state = settings.value("central_splitter/state")
            splitter_state = None
            if splitter_state:
                self.central_splitter.restoreState(splitter_state)
#            header_restored = self.obj_tree.read_view_settings(
#                'table/header_state',
#                settings, reset)
            header_restored = False

        if not header_restored:
            column_sizes = [col.width for col in self._attr_cols]
            column_visible = [col.col_visible for col in self._attr_cols]

            for idx, size in enumerate(column_sizes):
                if size > 0:  # Just in case
                    header.resizeSection(idx, size)

            for idx, visible in enumerate(column_visible):
                elem = self.obj_tree.toggle_column_actions_group.actions()[idx]
                elem.setChecked(visible)

        self.resize(window_size)
        self.move(pos)
        button = self.button_group.button(details_button_idx)
        if button is not None:
            button.setChecked(True)

    def _writeViewSettings(self):
        """Writes the view settings to the persistent store."""
        logger.debug("Writing view settings "
                     "for window: {:d}".format(self._instance_nr))
#
#        settings = get_qsettings()
#        settings.beginGroup(self._settings_group_name('view'))
#        self.obj_tree.write_view_settings("table/header_state", settings)
#        settings.setValue("central_splitter/state",
#                          self.central_splitter.saveState())
#        settings.setValue("details_button_idx", self.button_group.checkedId())
#        settings.setValue("main_window/pos", self.pos())
#        settings.setValue("main_window/size", self.size())
#        settings.endGroup()

    @Slot(QModelIndex, QModelIndex)
    def _update_details(self, current_index, _previous_index):
        """Shows the object details in the editor given an index."""
        tree_item = self._proxy_tree_model.treeItem(current_index)
        self._update_details_for_item(tree_item)

    def _change_details_field(self, _button_id=None):
        """Changes the field that is displayed in the details pane."""
        # logger.debug("_change_details_field: {}".format(_button_id))
        current_index = self.obj_tree.selectionModel().currentIndex()
        tree_item = self._proxy_tree_model.treeItem(current_index)
        self._update_details_for_item(tree_item)

    def _update_details_for_item(self, tree_item):
        """Shows the object details in the editor given an tree_item."""
        self.editor.setStyleSheet("color: black;")
        try:
            # obj = tree_item.obj
            button_id = self.button_group.checkedId()
            assert button_id >= 0, ("No radio button selected. "
                                    "Please report this bug.")
            attr_details = self._attr_details[button_id]
            data = attr_details.data_fn(tree_item)
            self.editor.setPlainText(data)
            self.editor.setWordWrapMode(attr_details.line_wrap)
        except Exception as ex:
            self.editor.setStyleSheet("color: red;")
            stack_trace = traceback.format_exc()
            self.editor.setPlainText("{}\n\n{}".format(ex, stack_trace))
            self.editor.setWordWrapMode(
                QTextOption.WrapAtWordBoundaryOrAnywhere)

    def toggle_auto_refresh(self, checked):
        """Toggles auto-refresh on/off."""
        if checked:
            logger.info("Auto-refresh on. "
                        "Rate {:g} seconds".format(self._refresh_rate))
            self._refresh_timer.start()
        else:
            logger.info("Auto-refresh off")
            self._refresh_timer.stop()
        self._auto_refresh = checked

    def _finalize(self):
        """
        Cleans up resources when this window is closed.
        Disconnects all signals for this window.
        """
        self._refresh_timer.stop()
        self._refresh_timer.timeout.disconnect(self.refresh)
        self.toggle_callable_action.toggled.disconnect(
            self._proxy_tree_model.setShowCallables)
        self.toggle_special_attribute_action.toggled.disconnect(
            self._proxy_tree_model.setShowSpecialAttributes)
        self.toggle_auto_refresh_action.toggled.disconnect(
            self.toggle_auto_refresh)
        self.refresh_action_f5.triggered.disconnect(self.refresh)
        self.button_group.buttonClicked[int].disconnect(
            self._change_details_field)
        selection_model = self.obj_tree.selectionModel()
        selection_model.currentChanged.disconnect(self._update_details)

    def about(self):
        """ Shows the about message window. """
        message = (_("{}: {}").format(PROGRAM_NAME, PROGRAM_URL))
        QMessageBox.about(self, _("About {}").format(PROGRAM_NAME), message)

    def closeEvent(self, event):
        """Called when the window is closed."""
        logger.debug("closeEvent")
        self._writeViewSettings()
        self._finalize()
        self.close()
        event.accept()
        self._remove_instance()
        self.about_to_quit()
        logger.debug("Closed {} window {}".format(PROGRAM_NAME,
                                                  self._instance_nr))

    def about_to_quit(self):
        """Called when application is about to quit."""
        # Sanity check
        for idx, bw in enumerate(self._browsers):
            if bw is not None:
                raise AssertionError("Reference not"
                                     " cleaned up: {}".format(idx))

    @classmethod
    def create_browser(cls, *args, **kwargs):
        """
        Creates and shows and ObjectBrowser window.

        The *args and **kwargs will be passed to the ObjectBrowser constructor.

        A (class attribute) reference to the browser window is kept to prevent
        it from being garbage-collected.
        """
        object_browser = cls(*args, **kwargs)
        object_browser.exec_()
#        return object_browser


# =============================================================================
# Tests
# =============================================================================
def test():
    """Run object editor test"""
    import datetime
    import numpy as np
    from spyder.pil_patch import Image

    app = qapplication()

    data = np.random.random_integers(255, size=(100, 100)).astype('uint8')
    image = Image.fromarray(data)

    class Foobar(object):
        def __init__(self):
            self.text = "toto"

        def get_text(self):
            return self.text
    foobar = Foobar()
    example = {'str': 'kjkj kj k j j kj k jkj',
               'list': [1, 3, 4, 'kjkj', None],
               'set': {1, 2, 1, 3, None, 'A', 'B', 'C', True, False},
               'dict': {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]},
               'float': 1.2233,
               'array': np.random.rand(10, 10),
               'image': image,
               'date': datetime.date(1945, 5, 8),
               'datetime': datetime.datetime(1945, 5, 8),
               'foobar': foobar}
    ObjectBrowser.create_browser(example, 'Example')


if __name__ == "__main__":
    test()

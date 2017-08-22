# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Utilities for the Collections editor widget and dialog
"""

from __future__ import print_function

import re

# Local imports
from spyder.config.base import get_supported_types
from spyder.py3compat import (NUMERIC_TYPES, TEXT_TYPES, to_text_string,
                              is_text_string, is_binary_string, reprlib,
                              PY2, to_binary_string)
from spyder.utils import programs
from spyder import dependencies
from spyder.config.base import _


#==============================================================================
# Dependencies
#==============================================================================
PANDAS_REQVER = '>=0.13.1'
dependencies.add('pandas',  _("View and edit DataFrames and Series in the "
                              "Variable Explorer"),
                 required_version=PANDAS_REQVER, optional=True)

NUMPY_REQVER = '>=1.7'
dependencies.add("numpy", _("View and edit two and three dimensional arrays "
                            "in the Variable Explorer"),
                 required_version=NUMPY_REQVER, optional=True)

#==============================================================================
# FakeObject
#==============================================================================
class FakeObject(object):
    """Fake class used in replacement of missing modules"""
    pass


#==============================================================================
# Numpy arrays and numeric types support
#==============================================================================
try:
    from numpy import (ndarray, array, matrix, recarray,
                       int64, int32, float64, float32,
                       complex64, complex128)
    from numpy.ma import MaskedArray
    from numpy import savetxt as np_savetxt
    from numpy import get_printoptions, set_printoptions
except:
    ndarray = array = matrix = recarray = MaskedArray = np_savetxt = \
    int64 = int32 = float64 = float32 = complex64 = complex128 = FakeObject

def get_numpy_dtype(obj):
    """Return NumPy data type associated to obj
    Return None if NumPy is not available
    or if obj is not a NumPy array or scalar"""
    if ndarray is not FakeObject:
        # NumPy is available
        import numpy as np
        if isinstance(obj, np.generic) or isinstance(obj, np.ndarray):
        # Numpy scalars all inherit from np.generic.
        # Numpy arrays all inherit from np.ndarray.
        # If we check that we are certain we have one of these
        # types then we are less likely to generate an exception below.
            try:
                return obj.dtype.type
            except (AttributeError, RuntimeError):
                #  AttributeError: some NumPy objects have no dtype attribute
                #  RuntimeError: happens with NetCDF objects (Issue 998)
                return


#==============================================================================
# Pandas support
#==============================================================================
if programs.is_module_installed('pandas', PANDAS_REQVER):
    try:
        from pandas import DataFrame, DatetimeIndex, Series
    except:
        DataFrame = DatetimeIndex = Series = FakeObject
else:
    DataFrame = DatetimeIndex = Series = FakeObject      # analysis:ignore


#==============================================================================
# PIL Images support
#==============================================================================
try:
    from spyder import pil_patch
    Image = pil_patch.Image.Image
except:
    Image = FakeObject  # analysis:ignore


#==============================================================================
# BeautifulSoup support (see Issue 2448)
#==============================================================================
try:
    import bs4
    NavigableString = bs4.element.NavigableString
except:
    NavigableString = FakeObject  # analysis:ignore


#==============================================================================
# Misc.
#==============================================================================
def address(obj):
    """Return object address as a string: '<classname @ address>'"""
    return "<%s @ %s>" % (obj.__class__.__name__,
                          hex(id(obj)).upper().replace('X', 'x'))


def try_to_eval(value):
    """Try to eval value"""
    try:
        return eval(value)
    except (NameError, SyntaxError, ImportError):
        return value

    
def get_size(item):
    """Return size of an item of arbitrary type"""
    if isinstance(item, (list, tuple, dict)):
        return len(item)
    elif isinstance(item, (ndarray, MaskedArray)):
        return item.shape
    elif isinstance(item, Image):
        return item.size
    if isinstance(item, (DataFrame, DatetimeIndex, Series)):
        return item.shape
    else:
        return 1


def get_object_attrs(obj):
    """
    Get the attributes of an object using dir.

    This filters protected attributes
    """
    attrs = [k for k in dir(obj) if not k.startswith('__')]
    if not attrs:
        attrs = dir(obj)
    return attrs


# =============================================================================
# Set limits for the amount of elements in the repr of collections (lists,
# dicts, tuples and sets) and Numpy arrays
# =============================================================================
CollectionsRepr = reprlib.Repr()
CollectionsRepr.maxlist = 10
CollectionsRepr.maxdict = 10
CollectionsRepr.maxtuple = 10
CollectionsRepr.maxset = 10


#==============================================================================
# Date and datetime objects support
#==============================================================================
import datetime


try:
    from dateutil.parser import parse as dateparse
except:
    def dateparse(datestr):  # analysis:ignore
        """Just for 'year, month, day' strings"""
        return datetime.datetime( *list(map(int, datestr.split(','))) )


def datestr_to_datetime(value):
    rp = value.rfind('(')+1
    v = dateparse(value[rp:-1])
    print(value, "-->", v)  # spyder: test-skip
    return v


#==============================================================================
# Background colors for supported types
#==============================================================================
ARRAY_COLOR = "#00ff00"
SCALAR_COLOR = "#0000ff"
COLORS = {
          bool:               "#ff00ff",
          NUMERIC_TYPES:      SCALAR_COLOR,
          list:               "#ffff00",
          dict:               "#00ffff",
          tuple:              "#c0c0c0",
          TEXT_TYPES:         "#800000",
          (ndarray,
           MaskedArray,
           matrix,
           DataFrame,
           Series,
           DatetimeIndex):    ARRAY_COLOR,
          Image:              "#008000",
          datetime.date:      "#808000",
          }
CUSTOM_TYPE_COLOR = "#7755aa"
UNSUPPORTED_COLOR = "#ffffff"

def get_color_name(value):
    """Return color name depending on value type"""
    if not is_known_type(value):
        return CUSTOM_TYPE_COLOR
    for typ, name in list(COLORS.items()):
        if isinstance(value, typ):
            return name
    else:
        np_dtype = get_numpy_dtype(value)
        if np_dtype is None or not hasattr(value, 'size'):
            return UNSUPPORTED_COLOR
        elif value.size == 1:
            return SCALAR_COLOR
        else:
            return ARRAY_COLOR


def is_editable_type(value):
    """Return True if data type is editable with a standard GUI-based editor,
    like CollectionsEditor, ArrayEditor, QDateEdit or a simple QLineEdit"""
    return get_color_name(value) not in (UNSUPPORTED_COLOR, CUSTOM_TYPE_COLOR)


#==============================================================================
# Sorting
#==============================================================================
def sort_against(list1, list2, reverse=False):
    """
    Arrange items of list1 in the same order as sorted(list2).

    In other words, apply to list1 the permutation which takes list2 
    to sorted(list2, reverse).
    """
    try:
        return [item for _, item in 
                sorted(zip(list2, list1), key=lambda x: x[0], reverse=reverse)]
    except:
        return list1


def unsorted_unique(lista):
    """Removes duplicates from lista neglecting its initial ordering"""
    return list(set(lista))


#==============================================================================
# Display <--> Value
#==============================================================================
def default_display(value):
    """Default display for unknown objects."""
    object_type = type(value)
    try:
        name = object_type.__name__
        module = object_type.__module__
        return name + ' of ' + module
    except:
        type_str = to_text_string(object_type)
        return type_str[1:-1]


def value_to_display(value, minmax=False):
    """Convert value for display purpose"""
    # To save current Numpy threshold
    np_threshold = FakeObject

    try:
        numeric_numpy_types = (int64, int32, float64, float32,
                               complex128, complex64)
        if ndarray is not FakeObject:
            # Save threshold
            np_threshold = get_printoptions().get('threshold')
            # Set max number of elements to show for Numpy arrays
            # in our display
            set_printoptions(threshold=10)
        if isinstance(value, recarray):
            fields = value.names
            display = 'Field names: ' + ', '.join(fields)
        elif isinstance(value, MaskedArray):
            display = 'Masked array'
        elif isinstance(value, ndarray):
            if minmax:
                try:
                    display = 'Min: %r\nMax: %r' % (value.min(), value.max())
                except (TypeError, ValueError):
                    display = repr(value)
            else:
                display = repr(value)
        elif any([type(value) == t for t in [list, tuple, dict, set]]):
            display = CollectionsRepr.repr(value)
        elif isinstance(value, Image):
            display = '%s  Mode: %s' % (address(value), value.mode)
        elif isinstance(value, DataFrame):
            cols = value.columns
            if PY2 and len(cols) > 0:
                # Get rid of possible BOM utf-8 data present at the
                # beginning of a file, which gets attached to the first
                # column header when headers are present in the first
                # row.
                # Fixes Issue 2514
                try:
                    ini_col = to_text_string(cols[0], encoding='utf-8-sig')
                except:
                    ini_col = to_text_string(cols[0])
                cols = [ini_col] + [to_text_string(c) for c in cols[1:]]
            else:
                cols = [to_text_string(c) for c in cols]
            display = 'Column names: ' + ', '.join(list(cols))
        elif isinstance(value, NavigableString):
            # Fixes Issue 2448
            display = to_text_string(value)
        elif isinstance(value, DatetimeIndex):
            display = value.summary()
        elif is_binary_string(value):
            try:
                display = to_text_string(value, 'utf8')
            except:
                display = value
        elif is_text_string(value):
            display = value
        elif isinstance(value, NUMERIC_TYPES) or isinstance(value, bool) or \
          isinstance(value, datetime.date) or \
          isinstance(value, numeric_numpy_types):
            display = repr(value)
        else:
            # Note: Don't trust on repr's. They can be inefficient and
            # so freeze Spyder quite easily
            display = default_display(value)
    except:
        display = default_display(value)

    # Truncate display at 80 chars to avoid freezing Spyder
    # because of large displays
    if len(display) > 80:
        display = display[:80].rstrip() + ' ...'

    # Restore Numpy threshold
    if np_threshold is not FakeObject:
        set_printoptions(threshold=np_threshold)

    return display



def display_to_value(value, default_value, ignore_errors=True):
    """Convert back to value"""
    from qtpy.compat import from_qvariant
    value = from_qvariant(value, to_text_string)
    try:
        np_dtype = get_numpy_dtype(default_value)
        if isinstance(default_value, bool):
            # We must test for boolean before NumPy data types
            # because `bool` class derives from `int` class
            try:
                value = bool(float(value))
            except ValueError:
                value = value.lower() == "true"
        elif np_dtype is not None:
            if 'complex' in str(type(default_value)):
                value = np_dtype(complex(value))
            else:
                value = np_dtype(value)
        elif is_binary_string(default_value):
            value = to_binary_string(value, 'utf8')
        elif is_text_string(default_value):
            value = to_text_string(value)
        elif isinstance(default_value, complex):
            value = complex(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            try:
                value = int(value)
            except ValueError:
                value = float(value)
        elif isinstance(default_value, datetime.datetime):
            value = datestr_to_datetime(value)
        elif isinstance(default_value, datetime.date):
            value = datestr_to_datetime(value).date()
        elif ignore_errors:
            value = try_to_eval(value)
        else:
            value = eval(value)
    except (ValueError, SyntaxError):
        if ignore_errors:
            value = try_to_eval(value)
        else:
            return default_value
    return value


# =============================================================================
# Types
# =============================================================================
def get_type_string(item):
    """Return type string of an object."""
    if isinstance(item, DataFrame):
        return "DataFrame"
    if isinstance(item, DatetimeIndex):
        return "DatetimeIndex"
    if isinstance(item, Series):
        return "Series"
    found = re.findall(r"<(?:type|class) '(\S*)'>",
                       to_text_string(type(item)))
    if found:
        return found[0]
    

def is_known_type(item):
    """Return True if object has a known type"""
    # Unfortunately, the masked array case is specific
    return isinstance(item, MaskedArray) or get_type_string(item) is not None


def get_human_readable_type(item):
    """Return human-readable type string of an item"""
    if isinstance(item, (ndarray, MaskedArray)):
        return item.dtype.name
    elif isinstance(item, Image):
        return "Image"
    else:
        text = get_type_string(item)
        if text is None:
            text = to_text_string('unknown')
        else:
            return text[text.find('.')+1:]


#==============================================================================
# Globals filter: filter namespace dictionaries (to be edited in
# CollectionsEditor)
#==============================================================================
def is_supported(value, check_all=False, filters=None, iterate=True):
    """Return True if the value is supported, False otherwise"""
    assert filters is not None
    if value is None:
        return True
    if not is_editable_type(value):
        return False
    elif not isinstance(value, filters):
        return False
    elif iterate:
        if isinstance(value, (list, tuple, set)):
            valid_count = 0
            for val in value:
                if is_supported(val, filters=filters, iterate=check_all):
                    valid_count += 1
                if not check_all:
                    break
            return valid_count > 0
        elif isinstance(value, dict):
            for key, val in list(value.items()):
                if not is_supported(key, filters=filters, iterate=check_all) \
                   or not is_supported(val, filters=filters,
                                       iterate=check_all):
                    return False
                if not check_all:
                    break
    return True


def globalsfilter(input_dict, check_all=False, filters=None,
                  exclude_private=None, exclude_capitalized=None,
                  exclude_uppercase=None, exclude_unsupported=None,
                  excluded_names=None):
    """Keep only objects that can be pickled"""
    output_dict = {}
    for key, value in list(input_dict.items()):
        excluded = (exclude_private and key.startswith('_')) or \
                   (exclude_capitalized and key[0].isupper()) or \
                   (exclude_uppercase and key.isupper()
                    and len(key) > 1 and not key[1:].isdigit()) or \
                   (key in excluded_names) or \
                   (exclude_unsupported and \
                    not is_supported(value, check_all=check_all,
                                     filters=filters))
        if not excluded:
            output_dict[key] = value
    return output_dict


#==============================================================================
# Create view to be displayed by NamespaceBrowser
#==============================================================================
REMOTE_SETTINGS = ('check_all', 'exclude_private', 'exclude_uppercase',
                   'exclude_capitalized', 'exclude_unsupported',
                   'excluded_names', 'minmax')


def get_remote_data(data, settings, mode, more_excluded_names=None):
    """
    Return globals according to filter described in *settings*:
        * data: data to be filtered (dictionary)
        * settings: variable explorer settings (dictionary)
        * mode (string): 'editable' or 'picklable'
        * more_excluded_names: additional excluded names (list)
    """
    supported_types = get_supported_types()
    assert mode in list(supported_types.keys())
    excluded_names = settings['excluded_names']
    if more_excluded_names is not None:
        excluded_names += more_excluded_names
    return globalsfilter(data, check_all=settings['check_all'],
                         filters=tuple(supported_types[mode]),
                         exclude_private=settings['exclude_private'],
                         exclude_uppercase=settings['exclude_uppercase'],
                         exclude_capitalized=settings['exclude_capitalized'],
                         exclude_unsupported=settings['exclude_unsupported'],
                         excluded_names=excluded_names)


def make_remote_view(data, settings, more_excluded_names=None):
    """
    Make a remote view of dictionary *data*
    -> globals explorer
    """
    data = get_remote_data(data, settings, mode='editable',
                           more_excluded_names=more_excluded_names)
    remote = {}
    for key, value in list(data.items()):
        view = value_to_display(value, minmax=settings['minmax'])
        remote[key] = {'type':  get_human_readable_type(value),
                       'size':  get_size(value),
                       'color': get_color_name(value),
                       'view':  view}
    return remote

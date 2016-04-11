# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Utilities for the Collections editor widget and dialog
"""

from __future__ import print_function

import re

# Local imports
from spyderlib.py3compat import (NUMERIC_TYPES, TEXT_TYPES, to_text_string,
                                 is_text_string, is_binary_string, reprlib,
                                 PY2, to_binary_string)
from spyderlib.utils import programs
from spyderlib import dependencies
from spyderlib.config.base import _


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
# Numpy arrays support
#==============================================================================
try:
    from numpy import ndarray, array, matrix, recarray
    from numpy.ma import MaskedArray
    from numpy import savetxt as np_savetxt
except ImportError:
    ndarray = array = matrix = recarray = MaskedArray = np_savetxt = FakeObject  # analysis:ignore


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
    from pandas import DataFrame, Series
else:
    DataFrame = Series = FakeObject      # analysis:ignore


#==============================================================================
# PIL Images support
#==============================================================================
try:
    from spyderlib import pil_patch
    Image = pil_patch.Image.Image
except ImportError:
    Image = FakeObject  # analysis:ignore


#==============================================================================
# BeautifulSoup support (see Issue 2448)
#==============================================================================
try:
    import bs4
    NavigableString = bs4.element.NavigableString
except ImportError:
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
    if isinstance(item, (DataFrame, Series)):
        return item.shape
    else:
        return 1


#==============================================================================
# Set limits for the amount of elements in the repr of collections (lists,
# dicts, tuples and sets)
#==============================================================================
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
except ImportError:
    def dateparse(datestr):  # analysis:ignore
        """Just for 'year, month, day' strings"""
        return datetime.datetime( *list(map(int, datestr.split(','))) )


def datestr_to_datetime(value):
    rp = value.rfind('(')+1
    v = dateparse(value[rp:-1])
    print(value, "-->", v)
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
           Series):           ARRAY_COLOR,
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
def sort_against(lista, listb, reverse=False):
    """Arrange lista items in the same order as sorted(listb)"""
    try:
        return [item for _, item in sorted(zip(listb, lista), reverse=reverse)]
    except:
        return lista


def unsorted_unique(lista):
    """Removes duplicates from lista neglecting its initial ordering"""
    return list(set(lista))


#==============================================================================
# Display <--> Value
#==============================================================================
def value_to_display(value, truncate=False, trunc_len=80, minmax=False):
    """Convert value for display purpose"""
    try:
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
        elif isinstance(value, ndarray):
            display = repr(value)
        elif isinstance(value, (list, tuple, dict, set)):
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
        elif is_binary_string(value):
            try:
                display = to_text_string(value, 'utf8')
            except:
                display = value
        elif is_text_string(value):
            display = value
        elif isinstance(value, NUMERIC_TYPES) or isinstance(value, bool) or \
          isinstance(value, datetime.date):
            display = repr(value)
        else:
            # Note: Don't trust on repr's. They can be inefficient and
            # so freeze Spyder quite easily
            # display = repr(value)
            type_str = to_text_string(type(value))
            display = type_str[1:-1]
            if truncate and len(display) > trunc_len:
                display = display[:trunc_len].rstrip() + ' ...'
    except:
        type_str = to_text_string(type(value))
        display = type_str[1:-1]

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


#==============================================================================
# Types
#==============================================================================
def get_type_string(item):
    """Return type string of an object"""
    if isinstance(item, DataFrame):
        return "DataFrame"
    if isinstance(item, Series):
        return "Series"
    found = re.findall(r"<(?:type|class) '(\S*)'>", str(type(item)))
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
    if not is_editable_type(value):
        return False
    elif not isinstance(value, filters):
        return False
    elif iterate:
        if isinstance(value, (list, tuple, set)):
            for val in value:
                if not is_supported(val, filters=filters, iterate=check_all):
                    return False
                if not check_all:
                    break
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

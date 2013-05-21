# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Utilities for the Dictionary Editor Widget and Dialog based on Qt
"""

import re

#----Numpy arrays support
class FakeObject(object):
    """Fake class used in replacement of missing modules"""
    pass
try:
    from numpy import ndarray
    from numpy import array, matrix #@UnusedImport (object eval)
    from numpy.ma import MaskedArray
except ImportError:
    ndarray = array = matrix = MaskedArray = FakeObject  # analysis:ignore


def get_numpy_dtype(obj):
    """Return NumPy data type associated to obj
    Return None if NumPy is not available
    or if obj is not a NumPy array or scalar"""
    if ndarray is not FakeObject:
        # NumPy is available
        import numpy as np
        if isinstance(obj, np.object):
            # Note: TTBOMK, there is no type associated to both NumPy arrays 
            # and scalars, so we must handle the AttributeError exception.
            # Thus, we could have skipped the `isinstance(obj, np.object)` 
            # test, but keeping it is the only way to be sure that the object 
            # is really a NumPy object instead of an object simply following 
            # the same interface.
            try:
                return obj.dtype.type
            except (AttributeError, RuntimeError):
                #  AttributeError: some NumPy objects have no dtype attribute
                #  RuntimeError: happens with NetCDF objects (Issue 998)
                return


#----PIL Images support
try:
    from spyderlib import pil_patch
    Image = pil_patch.Image.Image
except ImportError:
    Image = FakeObject  # analysis:ignore


#----Misc.
def address(obj):
    """Return object address as a string: '<classname @ address>'"""
    return "<%s @ %s>" % (obj.__class__.__name__,
                          hex(id(obj)).upper().replace('X','x'))


#----date and datetime objects support
import datetime
try:
    from dateutil.parser import parse as dateparse
except ImportError:
    def dateparse(datestr):  # analysis:ignore
        """Just for 'year, month, day' strings"""
        return datetime.datetime( *map(int, datestr.split(',')) )
def datestr_to_datetime(value):
    rp = value.rfind('(')+1
    v = dateparse(value[rp:-1])
    print value, "-->", v
    return v


#----Background colors for supported types
ARRAY_COLOR = "#00ff00"
SCALAR_COLOR = "#0000ff"
COLORS = {
          bool:               "#ff00ff",
          (int, float,
           complex, long):    SCALAR_COLOR,
          list:               "#ffff00",
          dict:               "#00ffff",
          tuple:              "#c0c0c0",
          (str, unicode):     "#800000",
          (ndarray,
           MaskedArray):      ARRAY_COLOR,
          Image:              "#008000",
          datetime.date:      "#808000",
          }
CUSTOM_TYPE_COLOR = "#7755aa"
UNSUPPORTED_COLOR = "#ffffff"

def get_color_name(value):
    """Return color name depending on value type"""
    if not is_known_type(value):
        return CUSTOM_TYPE_COLOR
    for typ, name in COLORS.iteritems():
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
    like DictEditor, ArrayEditor, QDateEdit or a simple QLineEdit"""
    return get_color_name(value) not in (UNSUPPORTED_COLOR, CUSTOM_TYPE_COLOR)


#----Sorting
def sort_against(lista, listb, reverse=False):
    """Arrange lista items in the same order as sorted(listb)"""
    return [item for _, item in sorted(zip(listb, lista), reverse=reverse)]

def unsorted_unique(lista):
    """Removes duplicates from lista neglecting its initial ordering"""
    set = {}
    map(set.__setitem__,lista,[])
    return set.keys()


#----Display <--> Value
def value_to_display(value, truncate=False,
                     trunc_len=80, minmax=False, collvalue=True):
    """Convert value for display purpose"""
    if minmax and isinstance(value, (ndarray, MaskedArray)):
        if value.size == 0:
            return repr(value)
        try:
            return 'Min: %r\nMax: %r' % (value.min(), value.max())
        except TypeError:
            pass
        except ValueError:
            # Happens when one of the array cell contains a sequence
            pass
    if isinstance(value, Image):
        return '%s  Mode: %s' % (address(value), value.mode)
    if not isinstance(value, (str, unicode)):
        if isinstance(value, (list, tuple, dict, set)) and not collvalue:            
            value = address(value)
        else:
            value = repr(value)
    if truncate and len(value) > trunc_len:
        value = value[:trunc_len].rstrip() + ' ...'
    return value

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
    else:
        return 1

def get_type_string(item):
    """Return type string of an object"""
    found = re.findall(r"<type '([\S]*)'>", str(type(item)))
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
            text = unicode('unknown')
        else:
            return text[text.find('.')+1:]


#----Globals filter: filter namespace dictionaries (to be edited in DictEditor)
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
            for key, val in value.iteritems():
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
    for key, value in input_dict.items():
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

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
except ImportError:
    class ndarray(FakeObject):
        """Fake ndarray"""
        pass

#----PIL Images support
try:
    from PIL.Image import Image
    import PIL.Image
except:
    class Image(FakeObject):
        """Fake PIL Image"""
        pass

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
    from string import atoi
    def dateparse(datestr):
        """Just for 'year, month, day' strings"""
        return datetime.datetime( *map(atoi, datestr.split(',')) )
def datestr_to_datetime(value):
    rp = value.rfind('(')+1
    return dateparse(value[rp:-1])

#----Background colors for supported types 
COLORS = {
          bool:               "#ff00ff",
          (int, float, long): "#0000ff",
          list:               "#ffff00",
          dict:               "#00ffff",
          tuple:              "#c0c0c0",
          (str, unicode):     "#800000",
          ndarray:            "#00ff00",
          Image:              "#008000",
          datetime.date:      "#808000",
          }

def get_color_name(value):
    """Return color name depending on value type"""
    if not is_known_type(value):
        return "#7755aa"
    for typ, name in COLORS.iteritems():
        if isinstance(value, typ):
            return name
    else:
        return "#ffffff"

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
    if minmax and isinstance(value, ndarray):
        if value.size == 0:
            return repr(value)
        try:
            return 'Min: %r\nMax: %r' % (value.min(), value.max())
        except TypeError:
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
    
def display_to_value(value, default_value, ignore_errors=True):
    """Convert back to value"""
    value = unicode(value.toString())
    try:
        if isinstance(default_value, str):
            value = str(value)
        elif isinstance(default_value, unicode):
            value = unicode(value)
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
            raise
    return value

def get_size(item):
    """Return size of an item of arbitrary type"""
    if isinstance(item, (list, tuple, dict)):
        return len(item)
    elif isinstance(item, ndarray):
        return item.shape
    elif isinstance(item, Image):
        return item.size
    else:
        return 1

def get_type_string(item):
    """Return type string of an object"""
    if isinstance(item, ndarray):
        return item.dtype.name
    elif isinstance(item, Image):
        return "Image"
    else:
        found = re.findall(r"<type '([\S]*)'>", str(type(item)))
        if found:
            return found[0]

def get_type(item):
    """Return type of an item"""
    text = get_type_string(item)
    if text is None:
        text = unicode('unknown')
    return text[text.find('.')+1:]

def is_known_type(item):
    """Return True if object has a known type"""
    return get_type_string(item) is not None


#----Globals filter: filter namespace dictionaries (to be edited in DictEditor)
def is_supported(value, iter=0, itermax=-1, filters=None):
    """Return True if the value is supported, False otherwise"""
    assert filters is not None
    if iter == itermax:
        return True
    elif not isinstance(value, filters):
        return False
    elif isinstance(value, (list, tuple, set)):
        for val in value:
            if not is_supported(val, iter+1, filters=filters):
                return False
    elif isinstance(value, dict):
        for key, val in value.iteritems():
            if not is_supported(key, iter+1, filters=filters) \
               or not is_supported(val, iter+1, filters=filters):
                return False
    return True

def globalsfilter(input_dict, itermax=-1, filters=None,
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
                    not is_supported(value, itermax=itermax, filters=filters))
        if not excluded:
            output_dict[key] = value
    return output_dict


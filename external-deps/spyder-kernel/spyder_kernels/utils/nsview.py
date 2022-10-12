# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Utilities to build a namespace view.
"""

from __future__ import print_function

from itertools import islice
import inspect
import re

# Local imports
from spyder_kernels.py3compat import (NUMERIC_TYPES, INT_TYPES, TEXT_TYPES,
                                      to_text_string, is_text_string,
                                      is_type_text_string,
                                      is_binary_string, PY2,
                                      to_binary_string, iteritems)
from spyder_kernels.utils.lazymodules import (
    bs4, FakeObject, numpy as np, pandas as pd, PIL)


#==============================================================================
# Numpy support
#==============================================================================
def get_numeric_numpy_types():
    return (np.int64, np.int32, np.int16, np.int8, np.uint64, np.uint32,
            np.uint16, np.uint8, np.float64, np.float32, np.float16,
            np.complex64, np.complex128, np.bool_)


def get_numpy_dtype(obj):
    """
    Return Numpy data type associated to `obj`.

    Return None if Numpy is not available, if we get errors or if `obj` is not
    a Numpy array or scalar.
    """
    # Check if NumPy is available
    if np.ndarray is not FakeObject:
        # All Numpy scalars inherit from np.generic and all Numpy arrays
        # inherit from np.ndarray. If we check that we are certain we have one
        # of these types then we are less likely to generate an exception
        # below.
        # Note: The try/except is necessary to fix spyder-ide/spyder#19516.
        try:
            scalar_or_array = (
                isinstance(obj, np.generic) or isinstance(obj, np.ndarray)
            )
        except Exception:
            return

        if scalar_or_array:
            try:
                return obj.dtype.type
            except (AttributeError, RuntimeError):
                #  AttributeError: some NumPy objects have no dtype attribute
                #  RuntimeError: happens with NetCDF objects (Issue 998)
                return


def get_numpy_type_string(value):
    """Get the type of a Numpy object as a string."""
    np_dtype = get_numpy_dtype(value)
    if np_dtype is None or not hasattr(value, 'size'):
        return 'Unknown'
    elif value.size == 1:
        return 'Scalar'
    else:
        return 'Array'


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
    """Return shape/size/len of an item of arbitrary type"""
    try:
        if (
            hasattr(item, 'size') and hasattr(item.size, 'compute') or
            hasattr(item, 'shape') and hasattr(item.shape, 'compute')
        ):
            # This is necessary to avoid an error when trying to
            # get the size/shape of dask objects. We don't compute the
            # size/shape since such operation could be expensive.
            # Fixes spyder-ide/spyder#16844
            return 1
        elif (
            hasattr(item, 'shape') and
            isinstance(item.shape, (tuple, np.integer))
        ):
            try:
                if item.shape:
                    # This is needed since values could return as
                    # `shape` an instance of a `tuple` subclass.
                    # See spyder-ide/spyder#16348
                    if isinstance(item.shape, tuple):
                        return tuple(item.shape)
                    return item.shape
                else:
                    # Scalar value
                    return 1
            except RecursionError:
                # This is necessary to avoid an error when trying to
                # get the shape of these objects.
                # Fixes spyder-ide/spyder-kernels#217
                return (-1, -1)
        elif (hasattr(item, 'size') and
                isinstance(item.size, (tuple, np.integer))):
            try:
                return item.size
            except RecursionError:
                return (-1, -1)
        elif hasattr(item, '__len__'):
            return len(item)
        else:
            return 1
    except Exception:
        # There is one item
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


def str_to_timedelta(value):
    """Convert a string to a datetime.timedelta value.

    The following strings are accepted:

        - 'datetime.timedelta(1, 5, 12345)'
        - 'timedelta(1, 5, 12345)'
        - '(1, 5, 12345)'
        - '1, 5, 12345'
        - '1'

    if there are less then three parameters, the missing parameters are
    assumed to be 0. Variations in the spacing of the parameters are allowed.

    Raises:
        ValueError for strings not matching the above criterion.

    """
    m = re.match(r'^(?:(?:datetime\.)?timedelta)?'
                 r'\(?'
                 r'([^)]*)'
                 r'\)?$', value)
    if not m:
        raise ValueError('Invalid string for datetime.timedelta')
    args = [int(a.strip()) for a in m.group(1).split(',')]
    return datetime.timedelta(*args)


#==============================================================================
# Supported types
#==============================================================================
def is_editable_type(value):
    """
    Return True if data type is editable with a standard GUI-based editor,
    like CollectionsEditor, ArrayEditor, QDateEdit or a simple QLineEdit.
    """
    if not is_known_type(value):
        return False
    else:
        supported_types = [
            'bool', 'int', 'long', 'float', 'complex', 'list', 'set', 'dict',
            'tuple', 'str', 'unicode', 'NDArray', 'MaskedArray', 'Matrix',
            'DataFrame', 'Series', 'PIL.Image.Image', 'datetime.date',
            'datetime.timedelta'
        ]

        if (get_type_string(value) not in supported_types and
                not isinstance(value, pd.Index)):
            np_dtype = get_numpy_dtype(value)
            if np_dtype is None or not hasattr(value, 'size'):
                return False
        return True


#==============================================================================
# Sorting
#==============================================================================
def sort_against(list1, list2, reverse=False, sort_key=None):
    """
    Arrange items of list1 in the same order as sorted(list2).

    In other words, apply to list1 the permutation which takes list2 
    to sorted(list2, reverse).
    """
    if sort_key is None:
        key = lambda x: x[0]
    else:
        key = lambda x: sort_key(x[0])
    try:
        return [item for _, item in 
                sorted(zip(list2, list1), key=key, reverse=reverse)]
    except:
        return list1


def unsorted_unique(lista):
    """Removes duplicates from lista neglecting its initial ordering"""
    return list(set(lista))


#==============================================================================
# Display <--> Value
#==============================================================================
def default_display(value, with_module=True):
    """Default display for unknown objects."""
    object_type = type(value)
    try:
        name = object_type.__name__
        module = object_type.__module__

        # Classes correspond to new types
        if name == 'type':
            name = 'class'

        if with_module:
            if name == 'module':
                return value.__name__ + ' module'
            if module == 'builtins':
                return name + ' object'
            return name + ' object of ' + module + ' module'
        return name
    except Exception:
        type_str = to_text_string(object_type)
        return type_str[1:-1]


def collections_display(value, level):
    """Display for collections (i.e. list, set, tuple and dict)."""
    is_dict = isinstance(value, dict)
    is_set = isinstance(value, set)

    # Get elements
    if is_dict:
        elements = iteritems(value)
    else:
        elements = value

    # Truncate values
    truncate = False
    if level == 1 and len(value) > 10:
        elements = islice(elements, 10) if is_dict or is_set else value[:10]
        truncate = True
    elif level == 2 and len(value) > 5:
        elements = islice(elements, 5) if is_dict or is_set else value[:5]
        truncate = True

    # Get display of each element
    if level <= 2:
        if is_dict:
            displays = [value_to_display(k, level=level) + ':' +
                        value_to_display(v, level=level)
                        for (k, v) in list(elements)]
        else:
            displays = [value_to_display(e, level=level)
                        for e in elements]
        if truncate:
            displays.append('...')
        display = ', '.join(displays)
    else:
        display = '...'

    # Return display
    if is_dict:
        display = '{' + display + '}'
    elif isinstance(value, list):
        display = '[' + display + ']'
    elif isinstance(value, set):
        display = '{' + display + '}'
    else:
        display = '(' + display + ')'

    return display


def value_to_display(value, minmax=False, level=0):
    """Convert value for display purpose"""
    # To save current Numpy printoptions
    np_printoptions = FakeObject
    numeric_numpy_types = get_numeric_numpy_types()

    try:
        if np.ndarray is not FakeObject:
            # Save printoptions
            np_printoptions = np.get_printoptions()
            # Set max number of elements to show for Numpy arrays
            # in our display
            np.set_printoptions(threshold=10)
        if isinstance(value, np.recarray):
            if level == 0:
                fields = value.names
                display = 'Field names: ' + ', '.join(fields)
            else:
                display = 'Recarray'
        elif isinstance(value, np.ma.MaskedArray):
            display = 'Masked array'
        elif isinstance(value, np.ndarray):
            if level == 0:
                if minmax:
                    try:
                        display = 'Min: %r\nMax: %r' % (value.min(), value.max())
                    except (TypeError, ValueError):
                        if value.dtype.type in numeric_numpy_types:
                            display = str(value)
                        else:
                            display = default_display(value)
                elif value.dtype.type in numeric_numpy_types:
                    display = str(value)
                else:
                    display = default_display(value)
            else:
                display = 'Numpy array'
        elif any([type(value) == t for t in [list, set, tuple, dict]]):
            display = collections_display(value, level+1)
        elif isinstance(value, PIL.Image.Image):
            if level == 0:
                display = '%s  Mode: %s' % (address(value), value.mode)
            else:
                display = 'Image'
        elif isinstance(value, pd.DataFrame):
            if level == 0:
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
            else:
                display = 'Dataframe'
        elif isinstance(value, bs4.element.NavigableString):
            # Fixes Issue 2448
            display = to_text_string(value)
            if level > 0:
                display = u"'" + display + u"'"
        elif isinstance(value, pd.Index):
            if level == 0:
                try:
                    display = value._summary()
                except AttributeError:
                    display = value.summary()
            else:
                display = 'Index'
        elif is_binary_string(value):
            # We don't apply this to classes that extend string types
            # See issue 5636
            if is_type_text_string(value):
                try:
                    display = to_text_string(value, 'utf8')
                    if level > 0:
                        display = u"'" + display + u"'"
                except:
                    display = value
                    if level > 0:
                        display = b"'" + display + b"'"
            else:
                display = default_display(value)
        elif is_text_string(value):
            # We don't apply this to classes that extend string types
            # See issue 5636
            if is_type_text_string(value):
                display = value
                if level > 0:
                    display = u"'" + display + u"'"
            else:
                display = default_display(value)
        elif (isinstance(value, datetime.date) or
              isinstance(value, datetime.timedelta)):
            display = str(value)
        elif (isinstance(value, NUMERIC_TYPES) or
              isinstance(value, bool) or
              isinstance(value, numeric_numpy_types)):
            display = repr(value)
        else:
            if level == 0:
                display = default_display(value)
            else:
                display = default_display(value, with_module=False)
    except Exception:
        display = default_display(value)

    # Truncate display at 70 chars to avoid freezing Spyder
    # because of large displays
    if len(display) > 70:
        if is_binary_string(display):
            ellipses = b' ...'
        else:
            ellipses = u' ...'
        display = display[:70].rstrip() + ellipses

    # Restore Numpy printoptions
    if np_printoptions is not FakeObject:
        np.set_printoptions(**np_printoptions)

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
        elif isinstance(default_value, datetime.timedelta):
            value = str_to_timedelta(value)
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
    # The try/except is necessary to fix spyder-ide/spyder#19516.
    try:
        # Numpy objects (don't change the order!)
        if isinstance(item, np.ma.MaskedArray):
            return "MaskedArray"
        if isinstance(item, np.matrix):
            return "Matrix"
        if isinstance(item, np.ndarray):
            return "NDArray"

        # Pandas objects
        if isinstance(item, pd.DataFrame):
            return "DataFrame"
        if isinstance(item, pd.Index):
            return type(item).__name__
        if isinstance(item, pd.Series):
            return "Series"
    except Exception:
        pass

    found = re.findall(r"<(?:type|class) '(\S*)'>",
                       to_text_string(type(item)))
    if found:
        if found[0] == 'type':
            return 'class'
        return found[0]
    else:
        return 'Unknown'


def is_known_type(item):
    """Return True if object has a known type"""
    # Unfortunately, the masked array case is specific
    return (isinstance(item, np.ma.MaskedArray) or
            get_type_string(item) != 'Unknown')


def get_human_readable_type(item):
    """Return human-readable type string of an item"""
    # The try/except is necessary to fix spyder-ide/spyder#19516.
    try:
        if isinstance(item, (np.ndarray, np.ma.MaskedArray)):
            return u'Array of ' + item.dtype.name
        elif isinstance(item, PIL.Image.Image):
            return "Image"
        else:
            text = get_type_string(item)
            return text[text.find('.')+1:]
    except Exception:
        return 'Unknown'


#==============================================================================
# Globals filter: filter namespace dictionaries (to be edited in
# CollectionsEditor)
#==============================================================================
def is_supported(value, check_all=False, filters=None, iterate=False):
    """Return True if value is supported, False otherwise."""
    assert filters is not None
    if value is None:
        return True
    if is_callable_or_module(value):
        return True
    elif not is_editable_type(value):
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


def is_callable_or_module(value):
    """Return True if value is a callable or module, False otherwise."""
    try:
        callable_or_module = callable(value) or inspect.ismodule(value)
    except Exception:
        callable_or_module = False
    return callable_or_module


def globalsfilter(input_dict, check_all=False, filters=None,
                  exclude_private=None, exclude_capitalized=None,
                  exclude_uppercase=None, exclude_unsupported=None,
                  excluded_names=None, exclude_callables_and_modules=None):
    """Keep objects in namespace view according to different criteria."""
    output_dict = {}
    _is_string = is_type_text_string

    for key, value in list(input_dict.items()):
        excluded = (
            (exclude_private and _is_string(key) and key.startswith('_')) or
            (exclude_capitalized and _is_string(key) and key[0].isupper()) or
            (exclude_uppercase and _is_string(key) and key.isupper() and
             len(key) > 1 and not key[1:].isdigit()) or
            (key in excluded_names) or
            (exclude_callables_and_modules and is_callable_or_module(value)) or
            (exclude_unsupported and
             not is_supported(value, check_all=check_all, filters=filters))
        )
        if not excluded:
            output_dict[key] = value
    return output_dict


#==============================================================================
# Create view to be displayed by NamespaceBrowser
#==============================================================================
REMOTE_SETTINGS = ('check_all', 'exclude_private', 'exclude_uppercase',
                   'exclude_capitalized', 'exclude_unsupported',
                   'excluded_names', 'minmax', 'show_callable_attributes',
                   'show_special_attributes', 'exclude_callables_and_modules')


def get_supported_types():
    """
    Return a dictionnary containing types lists supported by the
    namespace browser.

    Note:
    If you update this list, don't forget to update variablexplorer.rst
    in spyder-docs
    """
    from datetime import date, timedelta
    editable_types = [int, float, complex, list, set, dict, tuple, date,
                      timedelta] + list(TEXT_TYPES) + list(INT_TYPES)
    try:
        from numpy import ndarray, matrix, generic
        editable_types += [ndarray, matrix, generic]
    except:
        pass
    try:
        from pandas import DataFrame, Series, Index
        editable_types += [DataFrame, Series, Index]
    except:
        pass
    picklable_types = editable_types[:]
    try:
        from PIL import Image
        editable_types.append(Image.Image)
    except:
        pass
    return dict(picklable=picklable_types, editable=editable_types)


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
    excluded_names = list(settings['excluded_names'])
    if more_excluded_names is not None:
        excluded_names += more_excluded_names
    return globalsfilter(
        data,
        check_all=settings['check_all'],
        filters=tuple(supported_types[mode]),
        exclude_private=settings['exclude_private'],
        exclude_uppercase=settings['exclude_uppercase'],
        exclude_capitalized=settings['exclude_capitalized'],
        exclude_unsupported=settings['exclude_unsupported'],
        exclude_callables_and_modules=settings['exclude_callables_and_modules'],
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
        remote[key] = {
            'type':  get_human_readable_type(value),
            'size':  get_size(value),
            'view':  view,
            'python_type': get_type_string(value),
            'numpy_type': get_numpy_type_string(value)
        }

    return remote

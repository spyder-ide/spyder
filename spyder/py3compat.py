# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.py3compat
----------------

Transitional module providing compatibility functions intended to help
migrating from Python 2 to Python 3.

This module should be fully compatible with:
    * Python >=v2.6
    * Python 3
"""

from __future__ import print_function

import operator
import os
import sys

PY3 = sys.version[0] == '3'
PY36_OR_MORE = sys.version_info[0] >= 3 and sys.version_info[1] >= 6
PY38_OR_MORE = sys.version_info[0] >= 3 and sys.version_info[1] >= 8

#==============================================================================
# Data types
#==============================================================================

# Python 3
TEXT_TYPES = (str,)
INT_TYPES = (int,)
NUMERIC_TYPES = tuple(list(INT_TYPES) + [float])


#==============================================================================
# Renamed/Reorganized modules
#==============================================================================
# Python 3
import builtins
import configparser
try:
    import winreg
except ImportError:
    pass
from sys import maxsize
import io
import pickle
from collections.abc import MutableMapping, MutableSequence
import _thread
import reprlib
import queue as Queue
from time import perf_counter
from base64 import decodebytes


#==============================================================================
# Strings
#==============================================================================
def to_unichr(character_code):
    """
    Return the Unicode string of the character with the given Unicode code.
    """
    return chr(character_code)

def is_type_text_string(obj):
    """Return True if `obj` is type text string, False if it is anything else,
    like an instance of a class that extends the basestring class."""
    return type(obj) in [str, bytes]

def is_text_string(obj):
    """Return True if `obj` is a text string, False if it is anything else,
    like binary data (Python 3) or QString (Python 2, PyQt API #1)"""
    return isinstance(obj, str)

def is_binary_string(obj):
    """Return True if `obj` is a binary string, False if it is anything else"""
    return isinstance(obj, bytes)

def is_string(obj):
    """Return True if `obj` is a text or binary Python string object,
    False if it is anything else, like a QString (Python 2, PyQt API #1)"""
    return is_text_string(obj) or is_binary_string(obj)

def is_unicode(obj):
    """Return True if `obj` is unicode"""
    return isinstance(obj, str)

def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string"""
    if encoding is None:
        return str(obj)
    elif isinstance(obj, str):
        # In case this function is not used properly, this could happen
        return obj
    else:
        return str(obj, encoding)

def to_binary_string(obj, encoding=None):
    """Convert `obj` to binary string (bytes in Python 3, str in Python 2)"""
    return bytes(obj, 'utf-8' if encoding is None else encoding)


#==============================================================================
# Function attributes
#==============================================================================
def get_func_code(func):
    """Return function code object"""
    return func.__code__

def get_func_name(func):
    """Return function name"""
    return func.__name__

def get_func_defaults(func):
    """Return function default argument values"""
    return func.__defaults__


#==============================================================================
# Special method attributes
#==============================================================================
def get_meth_func(obj):
    """Return method function object"""
    return obj.__func__

def get_meth_class_inst(obj):
    """Return method class instance"""
    return obj.__self__

def get_meth_class(obj):
    """Return method class"""
    return obj.__self__.__class__


#==============================================================================
# Misc.
#==============================================================================
input = input
getcwd = os.getcwd
def cmp(a, b):
    return (a > b) - (a < b)
str_lower = str.lower
from itertools import zip_longest

def qbytearray_to_str(qba):
    """Convert QByteArray object to str in a way compatible with Python 2/3"""
    return str(bytes(qba.toHex().data()).decode())

# =============================================================================
# Dict funcs
# =============================================================================
def iterkeys(d, **kw):
    return iter(d.keys(**kw))

def itervalues(d, **kw):
    return iter(d.values(**kw))

def iteritems(d, **kw):
    return iter(d.items(**kw))

def iterlists(d, **kw):
    return iter(d.lists(**kw))

viewkeys = operator.methodcaller("keys")

viewvalues = operator.methodcaller("values")

viewitems = operator.methodcaller("items")


# ============================================================================
# Exceptions
# ============================================================================
ConnectionError = ConnectionError
ConnectionRefusedError = ConnectionRefusedError
TimeoutError = TimeoutError
BrokenPipeError = BrokenPipeError


if __name__ == '__main__':
    pass

# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

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

PY2 = sys.version[0] == '2'
PY3 = sys.version[0] == '3'

if PY3:
    # keep reference to builtin_mod because the kernel overrides that value
    # to forward requests to a frontend.
    def input(prompt=''):
        return builtin_mod.input(prompt)
    builtin_mod_name = "builtins"
    import builtins as builtin_mod
else:
    # keep reference to builtin_mod because the kernel overrides that value
    # to forward requests to a frontend.
    def input(prompt=''):
        return builtin_mod.raw_input(prompt)
    builtin_mod_name = "__builtin__"
    import __builtin__ as builtin_mod


#==============================================================================
# Data types
#==============================================================================
if PY2:
    # Python 2
    TEXT_TYPES = (str, unicode)
    INT_TYPES = (int, long)
else:
    # Python 3
    TEXT_TYPES = (str,)
    INT_TYPES = (int,)
NUMERIC_TYPES = tuple(list(INT_TYPES) + [float, complex])


#==============================================================================
# Renamed/Reorganized modules
#==============================================================================
if PY2:
    # Python 2
    import __builtin__ as builtins
    import ConfigParser as configparser
    try:
        import _winreg as winreg
    except ImportError:
        pass
    from sys import maxint as maxsize
    try:
        import CStringIO as io
    except ImportError:
        import StringIO as io
    try:
        import cPickle as pickle
    except ImportError:
        import pickle
    from UserDict import DictMixin as MutableMapping
    import thread as _thread
    import repr as reprlib
    import Queue
else:
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
    from collections.abc import MutableMapping
    import _thread
    import reprlib
    import queue as Queue


#==============================================================================
# Strings
#==============================================================================
def is_type_text_string(obj):
    """Return True if `obj` is type text string, False if it is anything else,
    like an instance of a class that extends the basestring class."""
    if PY2:
        # Python 2
        return type(obj) in [str, unicode]
    else:
        # Python 3
        return type(obj) in [str, bytes]

def is_text_string(obj):
    """Return True if `obj` is a text string, False if it is anything else,
    like binary data (Python 3) or QString (Python 2, PyQt API #1)"""
    if PY2:
        # Python 2
        return isinstance(obj, basestring)
    else:
        # Python 3
        return isinstance(obj, str)

def is_binary_string(obj):
    """Return True if `obj` is a binary string, False if it is anything else"""
    if PY2:
        # Python 2
        return isinstance(obj, str)
    else:
        # Python 3
        return isinstance(obj, bytes)

def is_string(obj):
    """Return True if `obj` is a text or binary Python string object,
    False if it is anything else, like a QString (Python 2, PyQt API #1)"""
    return is_text_string(obj) or is_binary_string(obj)

def is_unicode(obj):
    """Return True if `obj` is unicode"""
    if PY2:
        # Python 2
        return isinstance(obj, unicode)
    else:
        # Python 3
        return isinstance(obj, str)

def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string"""
    if PY2:
        # Python 2
        if encoding is None:
            return unicode(obj)
        else:
            return unicode(obj, encoding)
    else:
        # Python 3
        if encoding is None:
            return str(obj)
        elif isinstance(obj, str):
            # In case this function is not used properly, this could happen
            return obj
        else:
            return str(obj, encoding)

def to_binary_string(obj, encoding=None):
    """Convert `obj` to binary string (bytes in Python 3, str in Python 2)"""
    if PY2:
        # Python 2
        if encoding is None:
            return str(obj)
        else:
            return obj.encode(encoding)
    else:
        # Python 3
        return bytes(obj, 'utf-8' if encoding is None else encoding)


#==============================================================================
# Function attributes
#==============================================================================
def get_func_code(func):
    """Return function code object"""
    if PY2:
        # Python 2
        return func.func_code
    else:
        # Python 3
        return func.__code__

def get_func_name(func):
    """Return function name"""
    if PY2:
        # Python 2
        return func.func_name
    else:
        # Python 3
        return func.__name__

def get_func_defaults(func):
    """Return function default argument values"""
    if PY2:
        # Python 2
        return func.func_defaults
    else:
        # Python 3
        return func.__defaults__


#==============================================================================
# Special method attributes
#==============================================================================
def get_meth_func(obj):
    """Return method function object"""
    if PY2:
        # Python 2
        return obj.im_func
    else:
        # Python 3
        return obj.__func__

def get_meth_class_inst(obj):
    """Return method class instance"""
    if PY2:
        # Python 2
        return obj.im_self
    else:
        # Python 3
        return obj.__self__

def get_meth_class(obj):
    """Return method class"""
    if PY2:
        # Python 2
        return obj.im_class
    else:
        # Python 3
        return obj.__self__.__class__


#==============================================================================
# Misc.
#==============================================================================
if PY2:
    def _print(*objects, **options):
        end = options.get('end', '\n')
        file = options.get('file', sys.stdout)
        sep = options.get('sep', ' ')
        string = sep.join([str(obj) for obj in objects])
        print(string, file=file, end=end, sep=sep)
else:
    _print = print


if PY2:
    # Python 2
    getcwd = os.getcwdu
    cmp = cmp
    import string
    str_lower = string.lower
    from itertools import izip_longest as zip_longest
    from backports.functools_lru_cache import lru_cache
else:
    # Python 3
    getcwd = os.getcwd
    def cmp(a, b):
        return (a > b) - (a < b)
    str_lower = str.lower
    from itertools import zip_longest
    from functools import lru_cache

def qbytearray_to_str(qba):
    """Convert QByteArray object to str in a way compatible with Python 2/3"""
    return str(bytes(qba.toHex().data()).decode())

# =============================================================================
# Dict funcs
# =============================================================================
if PY3:
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
else:
    def iterkeys(d, **kw):
        return d.iterkeys(**kw)

    def itervalues(d, **kw):
        return d.itervalues(**kw)

    def iteritems(d, **kw):
        return d.iteritems(**kw)

    def iterlists(d, **kw):
        return d.iterlists(**kw)

    viewkeys = operator.methodcaller("viewkeys")

    viewvalues = operator.methodcaller("viewvalues")

    viewitems = operator.methodcaller("viewitems")

# =============================================================================
# Exceptions
# =============================================================================
if PY2:
    TimeoutError = RuntimeError
    FileNotFoundError = IOError
else:
    TimeoutError = TimeoutError
    FileNotFoundError = FileNotFoundError

if PY2:
    import re
    import tokenize
    def isidentifier(string):
        """Check if string can be a variable name."""
        return re.match(tokenize.Name + r'\Z', string) is not None

    if os.name == 'nt':
        def encode(u):
            """Try encoding with utf8."""
            if isinstance(u, unicode):
                return u.encode('utf8', 'replace')
            return u
    else:
        def encode(u):
            """Try encoding with file system encoding."""
            if isinstance(u, unicode):
                return u.encode(sys.getfilesystemencoding())
            return u
else:
    def isidentifier(string):
        """Check if string can be a variable name."""
        return string.isidentifier()

    def encode(u):
        """Encoding is not a problem in python 3."""
        return u


def compat_exec(code, globals, locals):
    # Wrap exec in a function
    exec(code, globals, locals)


if __name__ == '__main__':
    pass

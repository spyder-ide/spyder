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

import sys

PY38_OR_MORE = sys.version_info[0] >= 3 and sys.version_info[1] >= 8

#==============================================================================
# Data types
#==============================================================================

# Python 3
TEXT_TYPES = (str,)
INT_TYPES = (int,)
NUMERIC_TYPES = tuple(list(INT_TYPES) + [float])


#==============================================================================
# Strings
#==============================================================================
def is_text_string(obj):
    """Return True if `obj` is a text string, False if it is anything else,
    like binary data (Python 3) or QString (Python 2, PyQt API #1)"""
    return isinstance(obj, str)

def is_binary_string(obj):
    """Return True if `obj` is a binary string, False if it is anything else"""
    return isinstance(obj, bytes)

def is_string(obj):
    """Return True if `obj` is a text or binary Python string object,
    False if it is anything else, like a QString (PyQt API #1)"""
    return isinstance(obj, (str, bytes))

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
# Misc.
#==============================================================================
def qbytearray_to_str(qba):
    """Convert QByteArray object to str in a way compatible with Python 2/3"""
    return str(bytes(qba.toHex().data()).decode())

# =============================================================================
# Dict funcs
# =============================================================================
def iteritems(d, **kw):
    return iter(d.items(**kw))


if __name__ == '__main__':
    pass

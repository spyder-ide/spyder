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
"""

import operator
import pickle  # noqa. For compatibility with spyder-line-profiler


#==============================================================================
# Data types
#==============================================================================
# Python 3
TEXT_TYPES = (str,)
INT_TYPES = (int,)


#==============================================================================
# Strings
#==============================================================================
def is_type_text_string(obj):
    """Return True if `obj` is type text string, False if it is anything else,
    like an instance of a class that extends the basestring class."""
    return type(obj) in [str, bytes]

def is_text_string(obj):
    """Return True if `obj` is a text string, False if it is anything else,
    like binary data (Python 3) or QString (PyQt API #1)"""
    return isinstance(obj, str)

def is_binary_string(obj):
    """Return True if `obj` is a binary string, False if it is anything else"""
    return isinstance(obj, bytes)

def is_string(obj):
    """Return True if `obj` is a text or binary Python string object,
    False if it is anything else, like a QString (PyQt API #1)"""
    return is_text_string(obj) or is_binary_string(obj)

def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string"""
    if encoding is None:
        return str(obj)
    elif isinstance(obj, str):
        # In case this function is not used properly, this could happen
        return obj
    else:
        return str(obj, encoding)

def to_binary_string(obj, encoding='utf-8'):
    """Convert `obj` to binary string (bytes)"""
    return bytes(obj, encoding)

#==============================================================================
# Misc.
#==============================================================================
def qbytearray_to_str(qba):
    """Convert QByteArray object to str in a way compatible with Python 3"""
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


if __name__ == '__main__':
    pass

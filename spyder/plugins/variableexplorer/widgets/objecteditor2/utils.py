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

# Standard library imports
import logging
import six


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

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

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

# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Audrey Roy
# Copyright (c) 2016- Spyder Project Contributors
#
# Licensed under the terms of the BSD 3-clause license
# (see LICENSE.txt in this directory for details)
# -----------------------------------------------------------------------------

"""
binaryornot.check
-----------------

Main code for checking if a file is binary or text.

Adapted from binaryornot/check.py of
`BinaryOrNot <https://github.com/audreyr/binaryornot>`_.
"""

import logging

from spyder.utils.external.binaryornot.helpers import get_starting_chunk, is_binary_string


logger = logging.getLogger(__name__)


def is_binary(filename):
    """
    :param filename: File to check.
    :returns: True if it's a binary file, otherwise False.
    """
    logger.debug('is_binary: %(filename)r', locals())

    # Check if the file extension is in a list of known binary types
    binary_extensions = ['pyc', 'iso', 'zip', 'pdf']
    for ext in binary_extensions:
        if filename.endswith(ext):
            return True

    # Check if the starting chunk is a binary string
    chunk = get_starting_chunk(filename)
    return is_binary_string(chunk)

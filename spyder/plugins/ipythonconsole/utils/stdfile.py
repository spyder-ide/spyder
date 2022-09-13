# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Class to control a file where fault can be written.
"""

# Standard library imports.
import os.path as osp

# Local imports
from spyder.utils.programs import get_temp_dir


# For testing
IPYCONSOLE_TEST_DIR = None


def std_filename(connection_file, extension):
    """Filename to save kernel output."""
    json_file = osp.basename(connection_file)
    file = json_file.split('.json')[0] + extension
    if IPYCONSOLE_TEST_DIR is not None:
        return osp.join(IPYCONSOLE_TEST_DIR, file)
    try:
        return osp.join(get_temp_dir(), file)
    except (IOError, OSError):
        return None

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder font variables
"""

import os
import sys

from spyder.config.utils import is_ubuntu


#==============================================================================
# Main fonts
#==============================================================================
# Rich text fonts
SANS_SERIF = ['Sans Serif', 'DejaVu Sans', 'Bitstream Vera Sans',
              'Bitstream Charter', 'Lucida Grande', 'MS Shell Dlg 2',
              'Calibri', 'Verdana', 'Geneva', 'Lucid', 'Arial',
              'Helvetica', 'Avant Garde', 'Times', 'sans-serif']

# Plan text fonts
MONOSPACE = ['Monospace', 'DejaVu Sans Mono', 'Consolas',
             'Bitstream Vera Sans Mono', 'Andale Mono', 'Liberation Mono',
             'Courier New', 'Courier', 'monospace', 'Fixed', 'Terminal']


#==============================================================================
# Adjust font size per OS
#==============================================================================
if sys.platform == 'darwin':
    MONOSPACE = ['Menlo'] + MONOSPACE
    BIG = MEDIUM = SMALL = 11
elif os.name == 'nt':
    BIG = MEDIUM = 10
    SMALL = 9
elif is_ubuntu():
    SANS_SERIF = ['Ubuntu'] + SANS_SERIF
    MONOSPACE = ['Ubuntu Mono'] + MONOSPACE
    BIG = MEDIUM = 11
    SMALL = 10
else:
    BIG = 10
    MEDIUM = SMALL = 9

DEFAULT_SMALL_DELTA = SMALL - MEDIUM
DEFAULT_LARGE_DELTA = SMALL - BIG

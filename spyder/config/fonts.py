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
# Enums
#==============================================================================
class SpyderFontType:
    """
    Font types used in Spyder plugins and the entire application.

    Notes
    -----
    * This enum is meant to be used to get the QFont object corresponding to
      each type.
    * The names associated to the values in this enum depend on historical
      reasons that go back to Spyder 2 and are not easy to change now.
    * Monospace is the font used used in the Editor, IPython console and
      History; Interface is used by the entire Spyder app; and
      MonospaceInterface is used, for instance, by the Variable Explorer and
      corresponds to Monospace font resized to look good against the
      Interface one.
    """
    Monospace = 'font'
    Interface = 'app_font'
    MonospaceInterface = 'monospace_app_font'


#==============================================================================
# Main fonts
#==============================================================================
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
    MONOSPACE = ['Ubuntu Mono'] + MONOSPACE
    BIG = MEDIUM = 11
    SMALL = 10
else:
    BIG = 10
    MEDIUM = SMALL = 9

# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython configuration variables needed by Spyder
"""

from spyderlib.utils import programs

#==============================================================================
# Constants
#==============================================================================
SUPPORTED_IPYTHON = '>=0.13'
if programs.is_module_installed('IPython', '>=1.0'):
    IPYTHON_QT_MODULE = 'IPython.qt'
else:
    IPYTHON_QT_MODULE = 'IPython.frontend.qt'
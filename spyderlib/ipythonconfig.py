# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython configuration variables needed by Spyder
"""

from spyderlib.utils import programs


def is_qtconsole_installed():
    if programs.is_module_installed('IPython.qt'):
        return True
    elif programs.is_module_installed('IPython.frontend.qt'):
        return True
    else:
        return False

SUPPORTED_IPYTHON = '>=0.13'
IPYTHON_QT_INSTALLED = is_qtconsole_installed()

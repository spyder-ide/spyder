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
    pyzmq_installed = programs.is_module_installed('zmq')
    if programs.is_module_installed('IPython.qt') and pyzmq_installed:
        return True
    elif programs.is_module_installed('IPython.frontend.qt') and \
      pyzmq_installed:
        return True
    else:
        return False

SUPPORTED_IPYTHON = '>=0.13'
IPYTHON_QT_INSTALLED = is_qtconsole_installed()

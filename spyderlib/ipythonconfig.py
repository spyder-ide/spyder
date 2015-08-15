# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython configuration variables needed by Spyder
"""

from spyderlib.utils import programs
from spyderlib import dependencies
from spyderlib.baseconfig import _


# Constants
IPYTHON_REQVER = '>=1.0'
ZMQ_REQVER = '>=2.1.11'
QTCONSOLE_REQVER = '>=4.0'


# Dependencies
dependencies.add("IPython", _("IPython Console integration"),
                 required_version=IPYTHON_REQVER)
dependencies.add("zmq", _("IPython Console integration"),
                 required_version=ZMQ_REQVER)


# Jupyter 4.0 requirements
ipy4_installed = programs.is_module_installed('IPython', '>=4.0')
if ipy4_installed:
    dependencies.add("qtconsole", _("IPython Console integration"),
                     required_version=QTCONSOLE_REQVER)


# Auxiliary functions
def is_qtconsole_installed():
    pyzmq_installed = programs.is_module_installed('zmq')
    pygments_installed = programs.is_module_installed('pygments')
    ipyqt_installed = programs.is_module_installed('IPython.qt')

    if ipyqt_installed and pyzmq_installed and pygments_installed:
        if ipy4_installed:
            if programs.is_module_installed('qtconsole'):
                return True
            else:
                return False
        else:
            return True
    else:
        return False


# Main check for IPython presence
IPYTHON_QT_INSTALLED = is_qtconsole_installed()

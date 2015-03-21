# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
IPython configuration variables needed by Spyder
"""

import os

from spyderlib.utils import programs
from spyderlib import dependencies
from spyderlib.baseconfig import _

# Don't use spyderlib.qt.PYQT5 to avoid importing Qt here
PYQT5 = os.environ.get('QT_API', None) == 'pyqt5'

IPYTHON_REQVER = '>=1.0'
ZMQ_REQVER = '>=2.1.11'

dependencies.add("IPython", _("IPython Console integration"),
                 required_version=IPYTHON_REQVER)
dependencies.add("zmq", _("IPython Console integration"),
                 required_version=ZMQ_REQVER)

def is_qtconsole_installed():
    # Only IPython 3+ is compatible with PyQt5, so this will avoid a
    # crash for us
    # TODO: Remove this once IPython 3 is released
    if programs.is_module_installed('IPython.qt', '<3.0') and PYQT5:
        return False
    
    # Check if pyzmq is installed too, else, what's the point?
    pyzmq_installed = programs.is_module_installed('zmq', version=ZMQ_REQVER)
    pygments_installed = programs.is_module_installed('pygments')
    if programs.is_module_installed('IPython.qt') and pyzmq_installed \
      and pygments_installed:    
        return True
    else:
        return False

IPYTHON_QT_INSTALLED = is_qtconsole_installed()

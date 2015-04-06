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


IPYTHON_REQVER = '>=3.0'
ZMQ_REQVER = '>=13.0.0'

dependencies.add("IPython", _("IPython Console integration"),
                 required_version=IPYTHON_REQVER)
dependencies.add("zmq", _("IPython Console integration"),
                 required_version=ZMQ_REQVER)

def is_qtconsole_installed():
    pyzmq_installed = programs.is_module_installed('zmq', version=ZMQ_REQVER)
    pygments_installed = programs.is_module_installed('pygments')
    if programs.is_module_installed('IPython.qt', IPYTHON_REQVER) and \
      pyzmq_installed and pygments_installed:    
        return True
    else:
        return False

IPYTHON_QT_INSTALLED = is_qtconsole_installed()

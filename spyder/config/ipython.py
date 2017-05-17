# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython configuration variables needed by Spyder
"""

from spyder.utils import programs
from spyder import dependencies
from spyder.config.base import _


# Constants
QTCONSOLE_REQVER = ">=4.2.0"
ZMQ_REQVER = ">=13.0.0"
NBCONVERT_REQVER = ">=4.0"


# Dependencies
dependencies.add("qtconsole", _("Integrate the IPython console"),
                 required_version=QTCONSOLE_REQVER)
dependencies.add("nbconvert", _("Manipulate Jupyter notebooks on the Editor"),
                 required_version=NBCONVERT_REQVER)


# Auxiliary functions
def is_qtconsole_installed():
    pyzmq_installed = programs.is_module_installed('zmq', version=ZMQ_REQVER)
    pygments_installed = programs.is_module_installed('pygments')
    qtconsole_installed = programs.is_module_installed('qtconsole',
                                                       version=QTCONSOLE_REQVER)

    if pyzmq_installed and pygments_installed and qtconsole_installed:
        return True
    else:
        return False


# Main check for IPython presence
QTCONSOLE_INSTALLED = is_qtconsole_installed()

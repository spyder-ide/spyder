# -*- coding: utf-8 -*-

#==============================================================================
# The following statement is required to register this 3rd party plugin:
#==============================================================================
from pyqt.QtWidgets import QApplication
# The lines below are needed in order to prevent a segmentation fault.
# See issue #4014
app = None
if not QApplication.instance():
   app = QApplication()
from .profiler import Profiler as PLUGIN_CLASS

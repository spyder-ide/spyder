# -*- coding: utf-8 -*-

#==============================================================================
# The following statement is required to register this 3rd party plugin:
#==============================================================================
from spyder.utils.qthelpers import qapplication
# The line below is needed in order to prevent a segmentation fault.
# See issue #4014
app = qapplication()
from .profiler import Profiler as PLUGIN_CLASS

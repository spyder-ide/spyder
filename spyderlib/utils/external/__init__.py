# -*- coding: utf-8 -*-

"""
spyderlib.utils.external
========================

External libraries needed for Spyder to work.
Put here only untouched libraries, else put them in utils.
"""

import sys
from spyderlib.baseconfig import get_module_source_path
sys.path.insert(0, get_module_source_path(__name__))
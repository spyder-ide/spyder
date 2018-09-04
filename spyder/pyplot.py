# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Importing guiqwt's pyplot module or matplotlib's pyplot
"""

try:
    from guiqwt.pyplot import *
except:
    from matplotlib.pyplot import *

# -*- coding:utf-8 -*-
"""
Importing guiqwt's pyplot module or matplotlib's pyplot
"""

try:
    from guiqwt.pyplot import *
except ImportError:
    from matplotlib.pyplot import *

# -*- coding:utf-8 -*-
"""
Importing guiqwt's pyplot module or matplotlib's pyplot
"""

try:
    from guiqwt.pyplot import *
<<<<<<< HEAD
except ImportError:
=======
except (ImportError, AssertionError):
>>>>>>> 68da9235aabda2be32a6204ea08e3d1a37d3e12f
    from matplotlib.pyplot import *

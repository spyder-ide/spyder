# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

r"""
Patching PIL (Python Imaging Library) to avoid triggering the error:
AccessInit: hash collision: 3 for both 1 and 1

This error is occurring because of a bug in the PIL import mechanism.

How to reproduce this bug in a standard Python interpreter outside Spyder?
By importing PIL by two different mechanisms

Example on Windows:
===============================================================================
C:\Python27\Lib\site-packages>python
Python 2.7.2 (default, Jun 12 2011, 15:08:59) [MSC v.1500 32 bit (Intel)] on win32
Type "help", "copyright", "credits" or "license" for more information.
>>> import Image
>>> from PIL import Image
AccessInit: hash collision: 3 for both 1 and 1
===============================================================================

Another example on Windows (actually that's the same, but this is the exact
case encountered with Spyder when the global working directory is the
site-packages directory):
===============================================================================
C:\Python27\Lib\site-packages>python
Python 2.7.2 (default, Jun 12 2011, 15:08:59) [MSC v.1500 32 bit (Intel)] on win32
Type "help", "copyright", "credits" or "license" for more information.
>>> import scipy
>>> from pylab import *
AccessInit: hash collision: 3 for both 1 and 1
===============================================================================

The solution to this fix is the following patch:
===============================================================================
C:\Python27\Lib\site-packages>python
Python 2.7.2 (default, Jun 12 2011, 15:08:59) [MSC v.1500 32 bit (Intel)] on win
32
Type "help", "copyright", "credits" or "license" for more information.
>>> import Image
>>> import PIL
>>> PIL.Image = Image
>>> from PIL import Image
>>>
===============================================================================
"""

try:
    # For Pillow compatibility
    from PIL import Image
    import PIL
    PIL.Image = Image
except ImportError:
    # For PIL
    import Image
    import PIL
    PIL.Image = Image

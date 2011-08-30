# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Bootstrapping Spyder
(Executing Spyder from source checkout)

This script is a contribution from techtonik:
http://code.google.com/p/spyderlib/issues/detail?id=741
"""

import os
import subprocess
import sys

print("Executing Spyder from source checkout")

# Retrieving Mercurial revision number
DEVPATH = os.path.dirname(os.path.abspath(__file__))
try:
    output = subprocess.Popen(['hg', 'id', '-nib', DEVPATH], shell=True,
                              stdout=subprocess.PIPE).communicate()
    hgid, hgnum, hgbranch = output[0].strip().split()
    print("Revision %s:%s, Branch: %s" % (hgnum, hgid, hgbranch))
except Exception as exc:
    print("Error: Failed to get revision number from Mercurial - %s" % exc)

sys.path.insert(0, DEVPATH)
print("01. Patched sys.path with %s" % DEVPATH)

# Selecting the GUI toolkit: PySide if installed, otherwise PyQt4
# (Note: PyQt4 is still the officially supported GUI toolkit for Spyder)
try:
    import PySide
    print("02. PySide is detected, selecting (experimental)")
    os.environ['QT_API'] = 'pyside'
except:
    print("02. No PySide detected, using PyQt4 if available")

# Importing Spyder
from spyderlib import spyder
print("03. Imported Spyder %s (Qt %s via %s %s)" % \
    (spyder.__version__, spyder.qt.QtCore.__version__,
     {'pyside':'PySide', 'pyqt':'PyQt4'}[spyder.qt._modname],
     spyder.qt.__version__))

# Executing Spyder
print("04. Executing spyder.main()")
spyder.main()

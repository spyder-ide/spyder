#!/usr/bin/env python
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

# pylint: disable=C0103

import os
import subprocess
import sys
import optparse

# Parsing command line options
parser = optparse.OptionParser(
    usage="python bootstrap.py [options] [-- spyder_options]",
    epilog="Arguments for Spyder's main script are specified after the "\
           "-- symbol\n(example: `python bootstrap.py -- --debug --light`). "\
           "Type `python bootstrap.py -- --help` to read more about Spyder "\
           "options.\n")
parser.add_option('--gui', dest="gui", default=None,
                  help="GUI toolkit: pyqt (for PyQt4) or pyside (for PySide)")
options, args = parser.parse_args()
assert options.gui in (None, 'pyqt', 'pyside'), \
       "Invalid GUI toolkit option '%s'" % options.gui
# Prepare arguments for Spyder's main script
sys.argv = [sys.argv[0]] + args


print("Executing Spyder from source checkout")
DEVPATH = os.path.dirname(os.path.abspath(__file__))

# Warn if Spyder is located on non-ASCII path
# http://code.google.com/p/spyderlib/issues/detail?id=812
try:
    os.path.join(DEVPATH, u'test')
except UnicodeDecodeError:
    print("STOP: Spyder is located in the path with non-ASCII characters,")
    print("      which is known to cause problems (see issue #812).")
    raw_input("Press Enter to continue or Ctrl-C to abort...")

# Retrieving Mercurial revision number
try:
    output = subprocess.Popen('hg id -nib "%s"' % DEVPATH, shell=True,
                              stdout=subprocess.PIPE).communicate()
    hgid, hgnum, hgbranch = output[0].strip().split()
    print("Revision %s:%s, Branch: %s" % (hgnum, hgid, hgbranch))
except Exception as exc:
    print("Error: Failed to get revision number from Mercurial - %s" % exc)

sys.path.insert(0, DEVPATH)
print("01. Patched sys.path with %s" % DEVPATH)

# Selecting the GUI toolkit: PySide if installed, otherwise PyQt4
# (Note: PyQt4 is still the officially supported GUI toolkit for Spyder)
if options.gui is None:
    try:
        import PySide
        print("02. PySide is detected, selecting (experimental)")
        os.environ['QT_API'] = 'pyside'
    except:
        print("02. No PySide detected, using PyQt4 if available")
else:
    print ("02. Skipping GUI toolkit detection")
    os.environ["QT_API"] = options.gui

# Importing Spyder
from spyderlib import spyder
QT_API = spyder.qt._modname
QT_LIB = {'pyqt': 'PyQt4', 'pyside': 'PySide'}[QT_API]
if QT_API == 'pyqt':
    import sip
    try:
        QT_LIB += (" (API v%d)" % sip.getapi('QString'))
    except AttributeError:
        pass
print("03. Imported Spyder %s (Qt %s via %s %s)" % \
    (spyder.__version__, spyder.qt.QtCore.__version__,
     QT_LIB, spyder.qt.__version__))

# Executing Spyder
print("0x. Enforcing parent console (Windows only)") 
sys.argv.append("--showconsole")  # Windows only: show parent console
print("04. Executing spyder.main()")
spyder.main()

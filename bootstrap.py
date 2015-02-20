#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Bootstrapping Spyder

Detect environment and execute Spyder from source checkout
See Issue 741
"""

# pylint: disable=C0103

import time
time_start = time.time()

import os
import os.path as osp
import sys
import optparse


# --- Parse command line

parser = optparse.OptionParser(
    usage="python bootstrap.py [options] [-- spyder_options]",
    epilog="""\
Arguments for Spyder's main script are specified after the --
symbol (example: `python bootstrap.py -- --show-console`).
Type `python bootstrap.py -- --help` to read about Spyder
options.""")
parser.add_option('--gui', default=None,
                  help="GUI toolkit: pyqt (for PyQt4) or pyside (for PySide)")
parser.add_option('--hide-console', action='store_true',
                  default=False, help="Hide parent console window (Windows only)")
parser.add_option('--test', dest="test", action='store_true', default=False,
                  help="Test Spyder with a clean settings dir")
parser.add_option('--no-apport', action='store_true',
                  default=False, help="Disable Apport exception hook (Ubuntu)")
parser.add_option('--debug', action='store_true',
                  default=False, help="Run Spyder in debug mode")
options, args = parser.parse_args()

assert options.gui in (None, 'pyqt', 'pyside'), \
       "Invalid GUI toolkit option '%s'" % options.gui

# For testing purposes
if options.test:
    os.environ['SPYDER_TEST'] = 'True'

# Prepare arguments for Spyder's main script
sys.argv = [sys.argv[0]] + args


print("Executing Spyder from source checkout")
DEVPATH = osp.dirname(osp.abspath(__file__))

# To activate/deactivate certain things for development
os.environ['SPYDER_DEV'] = 'True'

# --- Test environment for surprises

# Warn if Spyder is located on non-ASCII path
# See Issue 812
try:
    osp.join(DEVPATH, 'test')
except UnicodeDecodeError:
    print("STOP: Spyder is located in the path with non-ASCII characters,")
    print("      which is known to cause problems (see issue #812).")
    try:
        input = raw_input
    except NameError:
        pass
    input("Press Enter to continue or Ctrl-C to abort...")

# Warn if we're running under 3rd party exception hook, such as
# apport_python_hook.py from Ubuntu
if sys.excepthook != sys.__excepthook__:
   if sys.excepthook.__name__ != 'apport_excepthook':
     print("WARNING: 3rd party Python exception hook is active: '%s'"
            % sys.excepthook.__name__)
   else:
     if not options.no_apport:
       print("WARNING: Ubuntu Apport exception hook is detected")
       print("         Use --no-apport option to disable it")
     else:
       sys.excepthook = sys.__excepthook__
       print("NOTICE: Ubuntu Apport exception hook is disabed")


# --- Continue

from spyderlib.utils.vcs import get_hg_revision
print("Revision %s:%s, Branch: %s" % get_hg_revision(DEVPATH))

sys.path.insert(0, DEVPATH)
print("01. Patched sys.path with %s" % DEVPATH)

EXTPATH = osp.join(DEVPATH, 'external-py' + sys.version[0])
if osp.isdir(EXTPATH):
    sys.path.insert(0, EXTPATH)
    print("                      and %s" % EXTPATH)


# Selecting the GUI toolkit: PySide if installed, otherwise PyQt4
# (Note: PyQt4 is still the officially supported GUI toolkit for Spyder)
if options.gui is None:
    try:
        import PySide  # analysis:ignore
        print("02. PySide is detected, selecting (experimental)")
        os.environ['QT_API'] = 'pyside'
    except:
        print("02. No PySide detected, using PyQt4 if available")
else:
    print ("02. Skipping GUI toolkit detection")
    os.environ['QT_API'] = options.gui


if options.debug:
    # safety check - Spyder config should not be imported at this point
    if "spyderlib.baseconfig" in sys.modules:
        sys.exit("ERROR: Can't enable debug mode - Spyder is already imported")
    print("0x. Switching debug mode on")
    os.environ["SPYDER_DEBUG"] = "True"
    # this way of interaction suxx, because there is no feedback
    # if operation is successful


# Checking versions (among other things, this has the effect of setting the
# QT_API environment variable if this has not yet been done just above)
from spyderlib import get_versions
versions = get_versions(reporev=False)
print("03. Imported Spyder %s" % versions['spyder'])
print("    [Python %s %dbits, Qt %s, %s %s on %s]" % \
      (versions['python'], versions['bitness'], versions['qt'],
       versions['qt_api'], versions['qt_api_ver'], versions['system']))


# --- Executing Spyder

if not options.hide_console and os.name == 'nt':
    print("0x. Enforcing parent console (Windows only)")
    sys.argv.append("--show-console")  # Windows only: show parent console

print("04. Executing spyder.main()")
from spyderlib import start_app

time_lapse = time.time()-time_start
print("Bootstrap completed in " +
    time.strftime("%H:%M:%S.", time.gmtime(time_lapse)) +  
    # gmtime() converts float into tuple, but loses milliseconds
    ("%.4f" % time_lapse).split('.')[1])

start_app.main()

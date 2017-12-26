#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

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
import argparse


# --- Parse command line

parser = argparse.ArgumentParser(
    usage="python bootstrap.py [options] [-- spyder_options]",
    epilog="""\
Arguments for Spyder's main script are specified after the --
symbol (example: `python bootstrap.py -- --hide-console`).
Type `python bootstrap.py -- --help` to read about Spyder
options.""")
parser.add_argument('--gui', default=None,
                  help="GUI toolkit: pyqt5 (for PyQt5), pyqt (for PyQt4) or "
                       "pyside (for PySide, deprecated)")
parser.add_argument('--show-console', action='store_true', default=False,
                  help="(Deprecated) Does nothing, now the default behavior "
                  "is to show the console")
parser.add_argument('--hide-console', action='store_true',
                  default=False, help="Hide parent console window (Windows only)")
parser.add_argument('--test', dest="test", action='store_true', default=False,
                  help="Test Spyder with a clean settings dir")
parser.add_argument('--no-apport', action='store_true',
                  default=False, help="Disable Apport exception hook (Ubuntu)")
parser.add_argument('--debug', action='store_true',
                  default=False, help="Run Spyder in debug mode")
parser.add_argument('spyder_options', nargs='*')

args = parser.parse_args()

# Store variable to be used in self.restart (restart spyder instance)
os.environ['SPYDER_BOOTSTRAP_ARGS'] = str(sys.argv[1:])

assert args.gui in (None, 'pyqt5', 'pyqt', 'pyside'), \
       "Invalid GUI toolkit option '%s'" % args.gui

# For testing purposes
if args.test:
    os.environ['SPYDER_TEST'] = 'True'

# Prepare arguments for Spyder's main script
sys.argv = [sys.argv[0]] + args.spyder_options


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
     if not args.no_apport:
       print("WARNING: Ubuntu Apport exception hook is detected")
       print("         Use --no-apport option to disable it")
     else:
       sys.excepthook = sys.__excepthook__
       print("NOTICE: Ubuntu Apport exception hook is disabed")


# --- Continue

if args.debug:
    # safety check - Spyder config should not be imported at this point
    if "spyder.config.base" in sys.modules:
        sys.exit("ERROR: Can't enable debug mode - Spyder is already imported")
    print("0x. Switching debug mode on")
    os.environ["SPYDER_DEBUG"] = "True"
    # this way of interaction suxx, because there is no feedback
    # if operation is successful


from spyder.utils.vcs import get_git_revision
print("Revision %s, Branch: %s" % get_git_revision(DEVPATH))

sys.path.insert(0, DEVPATH)
print("01. Patched sys.path with %s" % DEVPATH)


# Selecting the GUI toolkit: PyQt5 if installed, otherwise PySide or PyQt4
# (Note: PyQt4 is still the officially supported GUI toolkit for Spyder)
if args.gui is None:
    try:
        import PyQt5  # analysis:ignore
        print("02. PyQt5 is detected, selecting")
        os.environ['QT_API'] = 'pyqt5'
    except ImportError:
        try:
            import PyQt4  # analysis:ignore
            print("02. PyQt4 is detected, selecting")
            os.environ['QT_API'] = 'pyqt'
        except ImportError:
            print("02. No PyQt5 or PyQt4 detected, using PySide if available "
                  "(deprecated)")
else:
    print ("02. Skipping GUI toolkit detection")
    os.environ['QT_API'] = args.gui


# Checking versions (among other things, this has the effect of setting the
# QT_API environment variable if this has not yet been done just above)
from spyder import get_versions
versions = get_versions(reporev=False)
print("03. Imported Spyder %s" % versions['spyder'])
print("    [Python %s %dbits, Qt %s, %s %s on %s]" % \
      (versions['python'], versions['bitness'], versions['qt'],
       versions['qt_api'], versions['qt_api_ver'], versions['system']))


# Check that we have the right qtpy version
from spyder.utils import programs
if not programs.is_module_installed('qtpy', '>=1.1.0'):
    print("")
    sys.exit("ERROR: Your qtpy version is outdated. Please install qtpy "
             "1.1.0 or higher to be able to work with Spyder!")


# --- Executing Spyder

if args.show_console:
    print("(Deprecated) --show console does nothing, now the default behavior "
          "is to show the console, use --hide-console if you want to hide it")

if args.hide_console and os.name == 'nt':
    print("0x. Hiding parent console (Windows only)")
    sys.argv.append("--hide-console")  # Windows only: show parent console

print("04. Running Spyder")
from spyder.app import start

time_lapse = time.time()-time_start
print("Bootstrap completed in " +
    time.strftime("%H:%M:%S.", time.gmtime(time_lapse)) +  
    # gmtime() converts float into tuple, but loses milliseconds
    ("%.4f" % time_lapse).split('.')[1])

start.main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Bootstrap Spyder.

Execute Spyder from source checkout.
"""

# pylint: disable=C0103
# pylint: disable=C0412
# pylint: disable=C0413

# Standard library imports
import argparse
import os
import shutil
import sys
import time
from pathlib import Path

time_start = time.time()

print("Executing Spyder from source checkout")

# ---- Parse command line

parser = argparse.ArgumentParser(
    usage="python bootstrap.py [options] [-- spyder_options]",
    epilog="""\
Arguments for Spyder's main script are specified after the --
symbol (example: `python bootstrap.py -- --hide-console`).
Type `python bootstrap.py -- --help` to read about Spyder
options.""")
parser.add_argument('--gui', default=None,
                    help="GUI toolkit: pyqt5 (for PyQt5) or pyside2 "
                    "(for PySide2)")
parser.add_argument('--show-console', action='store_true', default=False,
                    help="(Deprecated) Does nothing, now the default behavior "
                    "is to show the console")
parser.add_argument('--hide-console', action='store_true', default=False,
                    help="Hide parent console window (Windows only)")
parser.add_argument('--safe-mode', dest="safe_mode",
                    action='store_true', default=False,
                    help="Start Spyder with a clean configuration directory")
parser.add_argument('--no-apport', action='store_true', default=False,
                    help="Disable Apport exception hook (Ubuntu)")
parser.add_argument('--debug', action='store_true',
                    default=False, help="Run Spyder in debug mode")
parser.add_argument('--filter-log', default='',
                    help="Comma-separated module name hierarchies whose log "
                         "messages should be shown. e.g., "
                         "spyder.plugins.completion,spyder.plugins.editor")
parser.add_argument('spyder_options', nargs='*')

args = parser.parse_args()

assert args.gui in (None, 'pyqt5', 'pyside2'), \
       "Invalid GUI toolkit option '%s'" % args.gui

# Prepare arguments for Spyder's main script
sys.argv = [sys.argv[0]] + args.spyder_options

# ---- Update os.environ

# Store variable to be used in self.restart (restart spyder instance)
os.environ['SPYDER_BOOTSTRAP_ARGS'] = str(sys.argv[1:])

# Start Spyder with a clean configuration directory for testing purposes
if args.safe_mode:
    os.environ['SPYDER_SAFE_MODE'] = 'True'

# To activate/deactivate certain things for development
os.environ['SPYDER_DEV'] = 'True'

if args.debug:
    # safety check - Spyder config should not be imported at this point
    if "spyder.config.base" in sys.modules:
        sys.exit("ERROR: Can't enable debug mode - Spyder is already imported")
    print("*. Switching debug mode on")
    os.environ["SPYDER_DEBUG"] = "3"
    if len(args.filter_log) > 0:
        print("*. Displaying log messages only from the "
              "following modules: {0}".format(args.filter_log))
    os.environ["SPYDER_FILTER_LOG"] = args.filter_log
    # this way of interaction suxx, because there is no feedback
    # if operation is successful

# Selecting the GUI toolkit: PyQt5 if installed
if args.gui is None:
    try:
        import PyQt5  # analysis:ignore
        print("*. PyQt5 is detected, selecting")
        os.environ['QT_API'] = 'pyqt5'
    except ImportError:
        sys.exit("ERROR: No PyQt5 detected!")
else:
    print("*. Skipping GUI toolkit detection")
    os.environ['QT_API'] = args.gui

# ---- Check versions

# Checking versions (among other things, this has the effect of setting the
# QT_API environment variable if this has not yet been done just above)
from spyder import get_versions
versions = get_versions(reporev=True)
print("*. Imported Spyder %s - Revision %s, Branch: %s" %
      (versions['spyder'], versions['revision'], versions['branch']))
print("    [Python %s %dbits, Qt %s, %s %s on %s]" %
      (versions['python'], versions['bitness'], versions['qt'],
       versions['qt_api'], versions['qt_api_ver'], versions['system']))

# Check that we have the right qtpy version
from spyder.utils import programs
if not programs.is_module_installed('qtpy', '>=1.1.0'):
    print("")
    sys.exit("ERROR: Your qtpy version is outdated. Please install qtpy "
             "1.1.0 or higher to be able to work with Spyder!")

# ---- Execute Spyder

if args.show_console:
    print("(Deprecated) --show console does nothing, now the default behavior "
          "is to show the console, use --hide-console if you want to hide it")

if args.hide_console and os.name == 'nt':
    print("*. Hiding parent console (Windows only)")
    sys.argv.append("--hide-console")  # Windows only: show parent console

# Reset temporary config directory if starting in --safe-mode
if args.safe_mode or os.environ.get('SPYDER_SAFE_MODE'):
    from spyder.config.base import get_conf_path  # analysis:ignore
    conf_dir = Path(get_conf_path())
    if conf_dir.is_dir():
        shutil.rmtree(conf_dir)

print("*. Running Spyder")
from spyder.app import start  # analysis:ignore

time_lapse = time.time() - time_start
print("Bootstrap completed in "
      + time.strftime("%H:%M:%S.", time.gmtime(time_lapse))
      # gmtime() converts float into tuple, but loses milliseconds
      + ("%.4f" % time_lapse).split('.')[1])

start.main()

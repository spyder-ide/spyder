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

Detect environment and execute Spyder from source checkout.
See spyder-ide/spyder#741.
"""

# pylint: disable=C0103
# pylint: disable=C0412
# pylint: disable=C0413

# Standard library imports
import atexit
import argparse
import os
import os.path as osp
import pkg_resources
import shutil
import subprocess
import sys
import time

time_start = time.time()

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

# Store variable to be used in self.restart (restart spyder instance)
os.environ['SPYDER_BOOTSTRAP_ARGS'] = str(sys.argv[1:])

assert args.gui in (None, 'pyqt5', 'pyqt', 'pyside'), \
       "Invalid GUI toolkit option '%s'" % args.gui

# Start Spyder with a clean configuration directory for testing purposes
if args.safe_mode:
    os.environ['SPYDER_SAFE_MODE'] = 'True'

# Prepare arguments for Spyder's main script
sys.argv = [sys.argv[0]] + args.spyder_options


print("Executing Spyder from source checkout")
DEVPATH = osp.dirname(osp.abspath(__file__))

# To activate/deactivate certain things for development
os.environ['SPYDER_DEV'] = 'True'

# --- Test environment for surprises

# Warn if Spyder is located on non-ASCII path
# See spyder-ide/spyder#812.
try:
    osp.join(DEVPATH, 'test')
except UnicodeDecodeError:
    print("STOP: Spyder is located in the path with non-ASCII characters,")
    print("      which is known to cause problems, see spyder-ide/spyder#812.")
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
    os.environ["SPYDER_DEBUG"] = "3"
    if len(args.filter_log) > 0:
        print("*. Displaying log messages only from the "
              "following modules: {0}".format(args.filter_log))
    os.environ["SPYDER_FILTER_LOG"] = args.filter_log
    # this way of interaction suxx, because there is no feedback
    # if operation is successful


# Add this path to the front of sys.path
sys.path.insert(0, DEVPATH)
print("*. Patched sys.path with %s" % DEVPATH)

# Add external dependencies subrepo paths to be the next entries
# (1, 2, etc) of sys.path
DEPS_PATH = osp.join(DEVPATH, 'external-deps')
i = 1
for path in os.listdir(DEPS_PATH):
    external_dep_path = osp.join(DEPS_PATH, path)
    sys.path.insert(i, external_dep_path)
    print("*. Patched sys.path with %s" % external_dep_path)
    i += 1

# Create an egg-info folder to declare the PyLS subrepo entry points.
pyls_submodule = osp.join(DEPS_PATH, 'python-language-server')
pyls_installation_dir = osp.join(pyls_submodule, '.installation-dir')
pyls_installation_egg = osp.join(
    pyls_submodule, 'python_language_server.egg-info')


def remove_pyls_installation():
    shutil.rmtree(pyls_installation_dir, ignore_errors=True)
    shutil.rmtree(pyls_installation_egg, ignore_errors=True)


if osp.exists(pyls_installation_dir) or osp.exists(pyls_installation_egg):
    # Remove any leftover installation from previous execution
    print("*. Removing previous PyLS local installation.")
    remove_pyls_installation()

# Install PyLS locally
print("*. Installing PyLS locally")
subprocess.check_output(
    [sys.executable,
     '-W',
     'ignore',
     'setup.py',
     'develop',
     '--no-deps',
     '--install-dir',
     pyls_installation_dir],
    env={**os.environ, **{'PYTHONPATH': pyls_installation_dir}},
    cwd=pyls_submodule
)

atexit.register(remove_pyls_installation)

print("*. Declaring completion providers")

# Register completion providers
fallback = pkg_resources.EntryPoint.parse(
    'fallback = spyder.plugins.completion.providers.fallback.provider:'
    'FallbackProvider')

snippets = pkg_resources.EntryPoint.parse(
    'snippets = spyder.plugins.completion.providers.snippets.provider:'
    'SnippetsProvider'
)

lsp = pkg_resources.EntryPoint.parse(
    'lsp = spyder.plugins.completion.providers.languageserver.provider:'
    'LanguageServerProvider'
)

kite = pkg_resources.EntryPoint.parse(
    'kite = spyder.plugins.completion.providers.kite.provider:'
    'KiteProvider'
)

# Create a fake Spyder distribution
d = pkg_resources.Distribution(__file__)

# Add the providers to the fake EntryPoint
d._ep_map = {
    'spyder.completions': {
        'fallback': fallback,
        'snippets': snippets,
        'lsp': lsp,
        'kite': kite
    }
}

# Add the fake distribution to the global working_set
pkg_resources.working_set.add(d, 'spyder')


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


# --- Executing Spyder

if args.show_console:
    print("(Deprecated) --show console does nothing, now the default behavior "
          "is to show the console, use --hide-console if you want to hide it")

if args.hide_console and os.name == 'nt':
    print("*. Hiding parent console (Windows only)")
    sys.argv.append("--hide-console")  # Windows only: show parent console

# Reset temporary config directory if starting in --safe-mode
if args.safe_mode or os.environ.get('SPYDER_SAFE_MODE'):
    from spyder.config.base import get_conf_path  # analysis:ignore
    conf_dir = get_conf_path()
    if osp.isdir(conf_dir):
        shutil.rmtree(conf_dir)

print("*. Running Spyder")
from spyder.app import start  # analysis:ignore

time_lapse = time.time() - time_start
print("Bootstrap completed in "
      + time.strftime("%H:%M:%S.", time.gmtime(time_lapse))
      # gmtime() converts float into tuple, but loses milliseconds
      + ("%.4f" % time_lapse).split('.')[1])

start.main()

# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

# Remove PYTHONPATH paths from sys.path before other imports to protect against
# shadowed standard libraries.
import os
import sys
if os.environ.get('PYTHONPATH'):
    for path in os.environ['PYTHONPATH'].split(os.pathsep):
        try:
            sys.path.remove(path.rstrip(os.sep))
        except ValueError:
            pass

# Standard library imports
import ctypes
import logging
import os.path as osp
import random
import socket
import time

# Prevent showing internal logging errors
# Fixes spyder-ide/spyder#15768
logging.raiseExceptions = False

# Prevent that our dependencies display warnings when not in debug mode.
# Some of them are reported in the console and others through our
# report error dialog.
# Note: The log level when debugging is set on the main window.
# Fixes spyder-ide/spyder#15163
root_logger = logging.getLogger()
root_logger.setLevel(logging.ERROR)

# Prevent a race condition with ZMQ
# See spyder-ide/spyder#5324.
import zmq

# Load GL library to prevent segmentation faults on some Linux systems
# See spyder-ide/spyder#3226 and spyder-ide/spyder#3332.
try:
    ctypes.CDLL("libGL.so.1", mode=ctypes.RTLD_GLOBAL)
except:
    pass

# Local imports
from spyder.app.cli_options import get_options
from spyder.config.base import (get_conf_path, reset_config_files,
                                running_under_pytest, is_conda_based_app)
from spyder.utils.conda import get_conda_root_prefix
from spyder.utils.external import lockfile
from spyder.py3compat import is_text_string

# Enforce correct CONDA_EXE environment variable
# Do not rely on CONDA_PYTHON_EXE or CONDA_PREFIX in case Spyder is started
# from the commandline
if is_conda_based_app():
    conda_root = get_conda_root_prefix()
    if os.name == 'nt':
        os.environ['CONDA_EXE'] = conda_root + r'\Scripts\conda.exe'
    else:
        os.environ['CONDA_EXE'] = conda_root + '/bin/conda'

# Get argv
if running_under_pytest():
    sys_argv = [sys.argv[0]]
    CLI_OPTIONS, CLI_ARGS = get_options(sys_argv)
else:
    CLI_OPTIONS, CLI_ARGS = get_options()

# Start Spyder with a clean configuration directory for testing purposes
if CLI_OPTIONS.safe_mode:
    os.environ['SPYDER_SAFE_MODE'] = 'True'

if CLI_OPTIONS.conf_dir:
    os.environ['SPYDER_CONFDIR'] = CLI_OPTIONS.conf_dir


def send_args_to_spyder(args):
    """
    Simple socket client used to send the args passed to the Spyder
    executable to an already running instance.

    Args can be Python scripts or files with these extensions: .spydata, .mat,
    .npy, or .h5, which can be imported by the Variable Explorer.
    """
    from spyder.config.manager import CONF
    port = CONF.get('main', 'open_files_port')
    print_warning = True

    # Wait ~50 secs for the server to be up
    # Taken from https://stackoverflow.com/a/4766598/438386
    for __ in range(200):
        try:
            for arg in args:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                       socket.IPPROTO_TCP)
                client.connect(("127.0.0.1", port))
                if is_text_string(arg):
                    arg = arg.encode('utf-8')
                client.send(osp.abspath(arg))
                client.close()
        except socket.error:
            # Print informative warning to let users know what Spyder is doing
            if print_warning:
                print("Waiting for the server to open files and directories "
                      "to be up (perhaps it failed to be started).")
                print_warning = False

            # Wait 250 ms before trying again
            time.sleep(0.25)
            continue
        break


def main():
    """
    Start Spyder application.

    If single instance mode is turned on (default behavior) and an instance of
    Spyder is already running, this will just parse and send command line
    options to the application.
    """
    # Parse command line options
    options, args = (CLI_OPTIONS, CLI_ARGS)

    # This is to allow reset without reading our conf file
    if options.reset_config_files:
        # <!> Remove all configuration files!
        reset_config_files()
        return

    from spyder.config.manager import CONF

    # Store variable to be used in self.restart (restart spyder instance)
    os.environ['SPYDER_ARGS'] = str(sys.argv[1:])

    #==========================================================================
    # Proper high DPI scaling is available in Qt >= 5.6.0. This attribute must
    # be set before creating the application.
    #==========================================================================
    if CONF.get('main', 'high_dpi_custom_scale_factor'):
        factors = str(CONF.get('main', 'high_dpi_custom_scale_factors'))
        f = list(filter(None, factors.split(';')))
        if len(f) == 1:
            os.environ['QT_SCALE_FACTOR'] = f[0]
        else:
            os.environ['QT_SCREEN_SCALE_FACTORS'] = factors
    else:
        os.environ['QT_SCALE_FACTOR'] = ''
        os.environ['QT_SCREEN_SCALE_FACTORS'] = ''

    if sys.platform == 'darwin':
        # Fixes launching issues with Big Sur (spyder-ide/spyder#14222)
        os.environ['QT_MAC_WANTS_LAYER'] = '1'
        # Prevent Spyder from crashing in macOS if locale is not defined
        LANG = os.environ.get('LANG')
        LC_ALL = os.environ.get('LC_ALL')
        if bool(LANG) and not bool(LC_ALL):
            LC_ALL = LANG
        elif not bool(LANG) and bool(LC_ALL):
            LANG = LC_ALL
        else:
            LANG = LC_ALL = 'en_US.UTF-8'

        os.environ['LANG'] = LANG
        os.environ['LC_ALL'] = LC_ALL

        # Don't show useless warning in the terminal where Spyder
        # was started.
        # See spyder-ide/spyder#3730.
        os.environ['EVENT_NOKQUEUE'] = '1'
    else:
        # Prevent our kernels to crash when Python fails to identify
        # the system locale.
        # Fixes spyder-ide/spyder#7051.
        try:
            from locale import getlocale
            getlocale()
        except ValueError:
            # This can fail on Windows. See spyder-ide/spyder#6886.
            try:
                os.environ['LANG'] = 'C'
                os.environ['LC_ALL'] = 'C'
            except Exception:
                pass

    if options.debug_info:
        levels = {'minimal': '2', 'verbose': '3'}
        os.environ['SPYDER_DEBUG'] = levels[options.debug_info]

    _filename = 'spyder-debug.log'
    if options.debug_output == 'file':
        _filepath = osp.realpath(_filename)
    else:
        _filepath = get_conf_path(_filename)
    os.environ['SPYDER_DEBUG_FILE'] = _filepath

    if options.paths:
        from spyder.config.base import get_conf_paths
        sys.stdout.write('\nconfig:' + '\n')
        for path in reversed(get_conf_paths()):
            sys.stdout.write('\t' + path + '\n')
        sys.stdout.write('\n' )
        return

    if (CONF.get('main', 'single_instance') and not options.new_instance
            and not options.reset_config_files):
        # Minimal delay (0.1-0.2 secs) to avoid that several
        # instances started at the same time step in their
        # own foots while trying to create the lock file
        time.sleep(random.randrange(1000, 2000, 90)/10000.)

        # Lock file creation
        lock_file = get_conf_path('spyder.lock')
        lock = lockfile.FilesystemLock(lock_file)

        # Try to lock spyder.lock. If it's *possible* to do it, then
        # there is no previous instance running and we can start a
        # new one. If *not*, then there is an instance already
        # running, which is locking that file
        try:
            lock_created = lock.lock()
        except:
            # If locking fails because of errors in the lockfile
            # module, try to remove a possibly stale spyder.lock.
            # This is reported to solve all problems with lockfile.
            # See spyder-ide/spyder#2363.
            try:
                if os.name == 'nt':
                    if osp.isdir(lock_file):
                        import shutil
                        shutil.rmtree(lock_file, ignore_errors=True)
                else:
                    if osp.islink(lock_file):
                        os.unlink(lock_file)
            except:
                pass

            # Then start Spyder as usual and *don't* continue
            # executing this script because it doesn't make
            # sense
            from spyder.app import mainwindow
            if running_under_pytest():
                return mainwindow.main(options, args)
            else:
                mainwindow.main(options, args)
                return

        if lock_created:
            # Start a new instance
            from spyder.app import mainwindow
            if running_under_pytest():
                return mainwindow.main(options, args)
            else:
                mainwindow.main(options, args)
        else:
            # Pass args to Spyder or print an informative
            # message
            if args:
                send_args_to_spyder(args)
            else:
                print("Spyder is already running. If you want to open a new \n"
                      "instance, please use the --new-instance option")
    else:
        from spyder.app import mainwindow
        if running_under_pytest():
            return mainwindow.main(options, args)
        else:
            mainwindow.main(options, args)


if __name__ == "__main__":
    main()

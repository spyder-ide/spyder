# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


# Standard library imports
import ctypes
import os
import os.path as osp
import random
import socket
import sys
import time

# To prevent a race condition with ZMQ
# See issue 5324
import zmq

# Load GL library to prevent segmentation faults on some Linux systems
# See issues 3226 and 3332
try:
    ctypes.CDLL("libGL.so.1", mode=ctypes.RTLD_GLOBAL)
except:
    pass

# Local imports
from spyder.app.cli_options import get_options
from spyder.config.base import (get_conf_path, running_in_mac_app,
                                running_under_pytest)
from spyder.config.main import CONF
from spyder.utils.external import lockfile
from spyder.py3compat import is_unicode


def send_args_to_spyder(args):
    """
    Simple socket client used to send the args passed to the Spyder
    executable to an already running instance.

    Args can be Python scripts or files with these extensions: .spydata, .mat,
    .npy, or .h5, which can be imported by the Variable Explorer.
    """
    port = CONF.get('main', 'open_files_port')

    # Wait ~50 secs for the server to be up
    # Taken from https://stackoverflow.com/a/4766598/438386
    for _x in range(200):
        try:
            for arg in args:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                       socket.IPPROTO_TCP)
                client.connect(("127.0.0.1", port))
                if is_unicode(arg):
                    arg = arg.encode('utf-8')
                client.send(osp.abspath(arg))
                client.close()
        except socket.error:
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
    if running_under_pytest():
        try:
            from unittest.mock import Mock
        except ImportError:
            from mock import Mock # Python 2

        options = Mock()
        options.new_instance = False
        options.reset_config_files = False
        options.debug_info = None
        args = None
    else:
        options, args = get_options()

    # Store variable to be used in self.restart (restart spyder instance)
    os.environ['SPYDER_ARGS'] = str(sys.argv[1:])

    #==========================================================================
    # Proper high DPI scaling is available in Qt >= 5.6.0. This attibute must
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
        # was started
        # See issue 3730
        os.environ['EVENT_NOKQUEUE'] = '1'
    else:
        # Prevent our kernels to crash when Python fails to identify
        # the system locale.
        # Fixes issue 7051.
        try:
            from locale import getlocale
            getlocale()
        except ValueError:
            # This can fail on Windows. See issue 6886
            try:
                os.environ['LANG'] = 'C'
                os.environ['LC_ALL'] = 'C'
            except Exception:
                pass

    if options.debug_info:
        levels = {'minimal': '2', 'verbose': '3'}
        os.environ['SPYDER_DEBUG'] = levels[options.debug_info]

    if CONF.get('main', 'single_instance') and not options.new_instance \
      and not options.reset_config_files and not running_in_mac_app():
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
            # This is reported to solve all problems with
            # lockfile (See issue 2363)
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
                return mainwindow.main()
            else:
                mainwindow.main()
                return

        if lock_created:
            # Start a new instance
            from spyder.app import mainwindow
            if running_under_pytest():
                return mainwindow.main()
            else:
                mainwindow.main()
        else:
            # Pass args to Spyder or print an informative
            # message
            if args:
                send_args_to_spyder(args)
            else:
                print("Spyder is already running. If you want to open a new \n"
                      "instance, please pass to it the --new-instance option")
    else:
        from spyder.app import mainwindow
        if running_under_pytest():
            return mainwindow.main()
        else:
            mainwindow.main()


if __name__ == "__main__":
    main()

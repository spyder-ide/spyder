# -*- coding: utf-8 -*-

# Std imports
import os
import os.path as osp
import random
import socket
import sys
import time

# To prevent a race condition with ZMQ
# See issue 5324
import zmq

# This import is needed to fix errors with OpenGL when installed using pip
# See issue 3332
try:
    from OpenGL import GL
except ImportError:
    # pyopengl is not present when installed using conda
    pass

# Local imports
from spyder.app.cli_options import get_options
from spyder.config.base import get_conf_path, running_in_mac_app
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
    # Taken from http://stackoverflow.com/a/4766598/438386
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

    # Prevent Spyder from crashing in macOS if locale is not defined
    if sys.platform == 'darwin':
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
            mainwindow.main()
            return

        if lock_created:
            # Start a new instance
            from spyder.app import mainwindow
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
        mainwindow.main()


if __name__ == "__main__":
    main()

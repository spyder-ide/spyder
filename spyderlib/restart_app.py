#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2015 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Restart Spyder

A helper script that allows Spyder to restart from within the application.
"""

import ast
import os
import os.path as osp
import subprocess
import sys
import time


PY2 = sys.version[0] == '2'
CLOSE_ERROR, RESET_ERROR, RESTART_ERROR = list(range(3))
SLEEP_TIME = 0.2  # Seconds


def _is_pid_running_on_windows(pid):
    """Check if a process is running on windows systems based on the pid."""
    pid = str(pid)

    # Hide flashing command prompt
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    process = subprocess.Popen(r'tasklist /fi "PID eq {0}"'.format(pid),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               startupinfo=startupinfo)
    stdoutdata, stderrdata = process.communicate()
    stdoutdata = to_text_string(stdoutdata)
    process.kill()
    check = pid in stdoutdata

    return check


def _is_pid_running_on_unix(pid):
    """Check if a process is running on unix systems based on the pid."""
    try:
        # On unix systems os.kill with a 0 as second argument only pokes the
        # process (if it exists) and does not kill it
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def is_pid_running(pid):
    """Check if a process is running based on the pid."""
    # Select the correct function depending on the OS
    if os.name == 'nt':
        return _is_pid_running_on_windows(pid)
    else:
        return _is_pid_running_on_unix(pid)


def launch_error_message(type_, error=None):
    """Launch a message box with a predefined error message.

    Parameters
    ----------
    type_ : int [CLOSE_ERROR, RESET_ERROR, RESTART_ERROR]
    """
    from spyderlib.baseconfig import _
    from spyderlib.qt.QtGui import QMessageBox, QDialog
    from spyderlib.utils import icon_manager as ima
    from spyderlib.utils.qthelpers import qapplication

    messages = {CLOSE_ERROR: _("The previous instance of Spyder has not "
                               "closed.\nRestart aborted."),
                RESET_ERROR: _("Spyder could not reset to factory defaults.\n"
                               "Restart aborted."),
                RESTART_ERROR: _("Spyder could not restart.\n"
                                 "Restart aborted.")}
    titles = {CLOSE_ERROR: _("Spyder exit error"),
              RESET_ERROR: _("Spyder reset error"),
              RESTART_ERROR: _("Spyder restart error")}

    if error:
        e = error.__repr__()
        message = messages[type_] + _("\n\n{0}".format(e))
    else:
        message = messages[type_]

    title = titles[type_]
    app = qapplication()
    resample = os.name != 'nt'
    # Resampling SVG icon only on non-Windows platforms (see Issue 1314):
    icon = ima.icon('spyder', resample=resample)
    app.setWindowIcon(icon)
    dlg = QDialog()
    dlg.setVisible(False)
    dlg.show()
    QMessageBox.warning(dlg, title, message, QMessageBox.Ok)
    raise RuntimeError(message)


# Note: Copied from py3compat because we can't rely on Spyder
# being installed when using bootstrap.py
def to_text_string(obj, encoding=None):
    """Convert `obj` to (unicode) text string"""
    if PY2:
        # Python 2
        if encoding is None:
            return unicode(obj)
        else:
            return unicode(obj, encoding)
    else:
        # Python 3
        if encoding is None:
            return str(obj)
        elif isinstance(obj, str):
            # In case this function is not used properly, this could happen
            return obj
        else:
            return str(obj, encoding)


def main():
    # Note: Variables defined in spyderlib\spyder.py 'restart()' method
    spyder_args = os.environ.pop('SPYDER_ARGS', None)
    pid = os.environ.pop('SPYDER_PID', None)
    is_bootstrap = os.environ.pop('SPYDER_IS_BOOTSTRAP', None)
    reset = os.environ.pop('SPYDER_RESET', None)

    # Get the spyder base folder based on this file
    spyder_folder = osp.split(osp.dirname(osp.abspath(__file__)))[0]

    if any([not spyder_args, not pid, not is_bootstrap, not reset]):
        error = "This script can only be called from within a Spyder instance"
        raise RuntimeError(error)

    # Variables were stored as string literals in the environment, so to use
    # them we need to parse them in a safe manner.
    is_bootstrap = ast.literal_eval(is_bootstrap)
    pid = ast.literal_eval(pid)
    args = ast.literal_eval(spyder_args)
    reset = ast.literal_eval(reset)

    # Enforce the --new-instance flag when running spyder
    if '--new-instance' not in args:
        if is_bootstrap and '--' not in args:
            args = args + ['--', '--new-instance']
        else:
            args.append('--new-instance')

    # Create the arguments needed for reseting
    if '--' in args:
        args_reset = ['--', '--reset']
    else:
        args_reset = ['--reset']

    # Arrange arguments to be passed to the restarter and reset subprocess
    args = ' '.join(args)
    args_reset = ' '.join(args_reset)

    # Get python excutable running this script
    python = sys.executable

    # Build the command
    if is_bootstrap:
        spyder = osp.join(spyder_folder, 'bootstrap.py')
    else:
        spyderlib = osp.join(spyder_folder, 'spyderlib')
        spyder = osp.join(spyderlib, 'start_app.py')

    command = '"{0}" "{1}" {2}'.format(python, spyder, args)

    # Adjust the command and/or arguments to subprocess depending on the OS
    shell = os.name != 'nt'

    # Wait for original process to end before launching the new instance
    for counter in range(60*5/SLEEP_TIME):  # Number in seconds (60*5)
        if not is_pid_running(pid):
            break
        time.sleep(SLEEP_TIME)  # Throttling control
    else:
        # The old spyder instance took too long to close and restart aborts
        launch_error_message(type_=CLOSE_ERROR)

    env = os.environ.copy()

    # Reset spyder if needed
    # -------------------------------------------------------------------------
    if reset:
        command_reset = '"{0}" "{1}" {2}'.format(python, spyder, args_reset)

        try:
            p = subprocess.Popen(command_reset, shell=shell)
            p.communicate()
            pid_reset = p.pid
        except Exception as error:
            p.kill()
            launch_error_message(type_=RESET_ERROR, error=error)

        # Wait for reset process to end before restarting
        for counter in range(60/SLEEP_TIME):  # Number in seconds (60)
            if not is_pid_running(pid_reset):
                break
            time.sleep(SLEEP_TIME)  # Throttling control
        else:
            # The rest subprocess took too long and it is killed
            p.kill()
            launch_error_message(type_=RESET_ERROR)

    # Restart
    # -------------------------------------------------------------------------
    try:
        p = subprocess.Popen(command, shell=shell, env=env)
    except Exception as error:
        p.kill()
        launch_error_message(type_=RESTART_ERROR, error=error)


if __name__ == '__main__':
    main()

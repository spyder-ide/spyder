# -*- coding: utf-8 -*-
#
# Copyright © 2015 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Restart Spyder

A helper script to allow for spyder to restart
"""

import ast
import os
import os.path as osp
import sys
import subprocess
import time

from spyderlib.py3compat import to_text_string


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
    # Adjust the command and/or arguments to subprocess depending on the OS
    if os.name == 'nt':
        return _is_pid_running_on_windows(pid)
    else:
        return _is_pid_running_on_unix(pid)


def main():
    # Variables defined in spyderlib\spyder.py 'restart()' method
    spyder_args = os.environ.pop('SPYDER_ARGS', None)
    pid = os.environ.pop('SPYDER_PID', None)
    is_bootstrap = os.environ.pop('SPYDER_IS_BOOTSTRAP', None)
    spyder_folder = os.environ.pop('SPYDER_FOLDER', None)

    if any([not spyder_args, not pid, not is_bootstrap, not spyder_folder]):
        error = "This script can only be called from within a Spyder instance"
        raise RuntimeError(error)

    # Variables were stored as string literals in the environment, so to use
    # them we need to parse them.
    is_bootstrap = ast.literal_eval(is_bootstrap)
    pid = int(pid)
    args = ast.literal_eval(spyder_args)

    # Enforce the --new-instance flag when running spyder
    if '--' not in args:
        args.append('--')

    args.append('--new-instance')

    # Arrange arguments
    args = ' '.join(args)

    python = sys.executable

    # Build the command
    if is_bootstrap:
        spyder = osp.join(spyder_folder, 'bootstrap.py')
    else:
        spyderlib = osp.join(spyder_folder, 'spyderlib')
        spyder = osp.join(spyderlib, 'start_app.py')

    command = '"{0}" "{1}" {2}'.format(python, spyder, args)

    # Adjust the command and/or arguments to subprocess depending on the OS
    if os.name == 'nt':
        shell = False
    else:
        shell = True

    # Wait for original process to end before launching the new instance
    while True:
        if not is_pid_running(pid):
            break
        time.sleep(0.2)  # Throttling control

    env = os.environ.copy()
    try:
        subprocess.Popen(command, shell=shell, env=env)
    except Exception as error:
        print(command)
        print(error)
        time.sleep(15)


if __name__ == '__main__':
    main()

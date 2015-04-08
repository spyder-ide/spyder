#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Restart Spyder

A helper script to allow for spyder to restart
"""

import os
import os.path as osp
import sys
import platform
import subprocess
import time

from spyderlib.py3compat import to_text_string


def main():
    # Variables defined in spyderlib\spyder.py 'restart()' method
    spyder_args = os.environ.pop('SPYDER_ARGS', None)
    pid = os.environ.pop('SPYDER_PID', None)
    is_bootstrap = os.environ.pop('SPYDER_IS_BOOTSTRAP', None)
    spyder_folder = os.environ.pop('SPYDER_FOLDER', None)

    if any([not spyder_args, not pid, not is_bootstrap, not spyder_folder]):
        error = "This script can only be called from within a Spyder instance"
        raise RuntimeError(error)

    # Fix variables
    args = eval(spyder_args)
    args = ' '.join(args)
    is_bootstrap = eval(is_bootstrap)
    pid = eval(pid)

    # Fix args
    # Maybe --new-instance should always be included to cope with corner cases
    # where someone has one running version without and and another with
    # If the user the one without (--new...) it would not start

    python = sys.executable

    # Build the command
    if is_bootstrap:
        spyder = osp.join(spyder_folder, 'bootstrap.py')
    else:
        spyderlib = osp.join(spyder_folder, 'spyderlib')
        spyder = osp.join(spyderlib, 'start_app.py')

    command = '"{0}" "{1}" {2}'.format(python, spyder, args)

    # Adjust the command depending on the OS
    system = platform.system().lower()
    if system.startswith('win'):
        shell = False
        is_pid_running = _is_pid_running_on_windows
    elif system.startswith('linux'):
        shell = True
        is_pid_running = _is_pid_running_on_unix
    elif system.startswith('darwin'):
        shell = True
        is_pid_running = _is_pid_running_on_unix

    # Wait for original process to end before launching the new instance
    while True:
        if not is_pid_running(pid):
            break
        time.sleep(0.2)

    env = os.environ.copy()
    try:
        subprocess.Popen(command, shell=shell, env=env)
    except Exception as error:
        print(command)
        print(error)
        time.sleep(15)


def _is_pid_running_on_windows(pid):
    """Check For the existence of a windows pid."""
    pid = str(pid)
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
    """Check For the existence of a unix pid."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


if __name__ == '__main__':
    main()

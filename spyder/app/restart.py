#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Restart Spyder

A helper script that allows to restart (and also reset) Spyder from within the
running application.
"""

# Standard library imports
import ast
import os
import os.path as osp
import subprocess
import sys
import time

# Third party imports
from qtpy import PYQT5
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QColor, QPixmap, QIcon
from qtpy.QtWidgets import QApplication, QMessageBox, QSplashScreen, QWidget

# Local imports
from spyder.config.base import _
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.encoding import to_unicode
from spyder.utils.qthelpers import qapplication
from spyder.config.manager import CONF


PY2 = sys.version[0] == '2'
IS_WINDOWS = os.name == 'nt'
SLEEP_TIME = 0.2  # Seconds for throttling control
CLOSE_ERROR, RESET_ERROR, RESTART_ERROR = [1, 2, 3]  # Spyder error codes


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
    stdoutdata = to_unicode(stdoutdata)
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


class Restarter(QWidget):
    """Widget in charge of displaying the splash information screen and the
       error messages.
    """
    def __init__(self):
        super(Restarter, self).__init__()
        self.ellipsis = ['', '.', '..', '...', '..', '.']

        # Widgets
        self.timer_ellipsis = QTimer(self)
        self.splash = QSplashScreen(QPixmap(get_image_path('splash'),
                                    'svg'))

        # Widget setup
        self.setVisible(False)

        font = self.splash.font()
        font.setPixelSize(10)
        self.splash.setFont(font)
        self.splash.show()

        self.timer_ellipsis.timeout.connect(self.animate_ellipsis)

    def _show_message(self, text):
        """Show message on splash screen."""
        self.splash.showMessage(text,
                                int(Qt.AlignBottom | Qt.AlignCenter |
                                    Qt.AlignAbsolute),
                                QColor(Qt.white))

    def animate_ellipsis(self):
        """Animate dots at the end of the splash screen message."""
        ellipsis = self.ellipsis.pop(0)
        text = ' '*len(ellipsis) + self.splash_text + ellipsis
        self.ellipsis.append(ellipsis)
        self._show_message(text)

    def set_splash_message(self, text):
        """Sets the text in the bottom of the Splash screen."""
        self.splash_text = text
        self._show_message(text)
        self.timer_ellipsis.start(500)

    def launch_error_message(self, error_type, error=None):
        """Launch a message box with a predefined error message.

        Parameters
        ----------
        error_type : int [CLOSE_ERROR, RESET_ERROR, RESTART_ERROR]
            Possible error codes when restarting/resetting spyder.
        error : Exception
            Actual Python exception error caught.
        """
        messages = {CLOSE_ERROR: _("It was not possible to close the previous "
                                   "Spyder instance.\nRestart aborted."),
                    RESET_ERROR: _("Spyder could not reset to factory "
                                   "defaults.\nRestart aborted."),
                    RESTART_ERROR: _("It was not possible to restart Spyder.\n"
                                     "Operation aborted.")}
        titles = {CLOSE_ERROR: _("Spyder exit error"),
                  RESET_ERROR: _("Spyder reset error"),
                  RESTART_ERROR: _("Spyder restart error")}

        if error:
            e = error.__repr__()
            message = messages[error_type] + "\n\n{0}".format(e)
        else:
            message = messages[error_type]

        title = titles[error_type]
        self.splash.hide()
        QMessageBox.warning(self, title, message, QMessageBox.Ok)
        raise RuntimeError(message)


def main():
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

    # Splash screen
    # -------------------------------------------------------------------------
    # Start Qt Splash to inform the user of the current status
    app = qapplication()
    restarter = Restarter()

    APP_ICON = QIcon(get_image_path("spyder"))
    app.setWindowIcon(APP_ICON)
    restarter.set_splash_message(_('Closing Spyder'))

    # Get variables
    # Note: Variables defined in app/mainwindow.py 'restart()' method
    spyder_args = os.environ.pop('SPYDER_ARGS', None)
    pid = os.environ.pop('SPYDER_PID', None)
    is_bootstrap = os.environ.pop('SPYDER_IS_BOOTSTRAP', None)
    reset = os.environ.pop('SPYDER_RESET', None)

    # Get the spyder base folder based on this file
    this_folder = osp.split(osp.dirname(osp.abspath(__file__)))[0]
    spyder_folder = osp.split(this_folder)[0]

    if not any([spyder_args, pid, is_bootstrap, reset]):
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

    # Create the arguments needed for resetting
    if '--' in args:
        args_reset = ['--', '--reset']
    else:
        args_reset = ['--reset']

    # Arrange arguments to be passed to the restarter and reset subprocess
    args = ' '.join(args)
    args_reset = ' '.join(args_reset)

    # Get python executable running this script
    python = sys.executable

    # Build the command
    if is_bootstrap:
        spyder = osp.join(spyder_folder, 'bootstrap.py')
    else:
        spyderdir = osp.join(spyder_folder, 'spyder')
        spyder = osp.join(spyderdir, 'app', 'start.py')

    command = '"{0}" "{1}" {2}'.format(python, spyder, args)

    # Adjust the command and/or arguments to subprocess depending on the OS
    shell = not IS_WINDOWS

    # Before launching a new Spyder instance we need to make sure that the
    # previous one has closed. We wait for a fixed and "reasonable" amount of
    # time and check, otherwise an error is launched
    wait_time = 90 if IS_WINDOWS else 30  # Seconds
    for counter in range(int(wait_time/SLEEP_TIME)):
        if not is_pid_running(pid):
            break
        time.sleep(SLEEP_TIME)  # Throttling control
        QApplication.processEvents()  # Needed to refresh the splash
    else:
        # The old spyder instance took too long to close and restart aborts
        restarter.launch_error_message(error_type=CLOSE_ERROR)

    env = os.environ.copy()

    # Reset Spyder (if required)
    # -------------------------------------------------------------------------
    if reset:
        restarter.set_splash_message(_('Resetting Spyder to defaults'))
        command_reset = '"{0}" "{1}" {2}'.format(python, spyder, args_reset)

        try:
            p = subprocess.Popen(command_reset, shell=shell, env=env)
        except Exception as error:
            restarter.launch_error_message(error_type=RESET_ERROR, error=error)
        else:
            p.communicate()
            pid_reset = p.pid

        # Before launching a new Spyder instance we need to make sure that the
        # reset subprocess has closed. We wait for a fixed and "reasonable"
        # amount of time and check, otherwise an error is launched.
        wait_time = 20  # Seconds
        for counter in range(int(wait_time/SLEEP_TIME)):
            if not is_pid_running(pid_reset):
                break
            time.sleep(SLEEP_TIME)  # Throttling control
            QApplication.processEvents()  # Needed to refresh the splash
        else:
            # The reset subprocess took too long and it is killed
            try:
                p.kill()
            except OSError as error:
                restarter.launch_error_message(error_type=RESET_ERROR,
                                               error=error)
            else:
                restarter.launch_error_message(error_type=RESET_ERROR)

    # Restart
    # -------------------------------------------------------------------------
    restarter.set_splash_message(_('Restarting'))
    try:
        subprocess.Popen(command, shell=shell, env=env)
    except Exception as error:
        restarter.launch_error_message(error_type=RESTART_ERROR, error=error)


if __name__ == '__main__':
    main()

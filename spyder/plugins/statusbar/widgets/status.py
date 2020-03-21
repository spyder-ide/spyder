# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# ----------------------------------------------------------------------------

"""Status bar widgets."""

# Standard library imports
import os
import subprocess

# Third party imports
from qtpy.QtCore import Qt, QSize, QTimer, Signal
from qtpy.QtGui import QFont, QIcon
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.status import BaseTimerStatus, StatusBarWidget
from spyder.config import utils


# Localization
_ = get_translation('spyder')


# =============================================================================
# Main window-related status bar widgets
# =============================================================================
class MemoryStatus(BaseTimerStatus):
    """Status bar widget for system memory usage."""

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        from spyder.utils.system import memory_usage  # analysis:ignore

    def get_value(self):
        """Return memory usage."""
        from spyder.utils.system import memory_usage
        text = '%d%%' % memory_usage()
        return 'Mem ' + text.rjust(3)

    def get_tooltip(self):
        """Return the widget tooltip text."""
        return _('Memory usage')

    def get_icon(self):
        """Return the widget tooltip text."""
        return QIcon()


class CPUStatus(BaseTimerStatus):
    """Status bar widget for system cpu usage."""

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        from spyder.utils import programs
        if not programs.is_module_installed('psutil', '>=0.2.0'):
            # The `interval` argument in `psutil.cpu_percent` function
            # was introduced in v0.2.0
            raise ImportError

    def get_value(self):
        """Return CPU usage."""
        import psutil
        text = '%d%%' % psutil.cpu_percent(interval=0)
        return 'CPU ' + text.rjust(3)

    def get_tooltip(self):
        """Return the widget tooltip text."""
        return _('CPU usage')

    def get_icon(self):
        """Return the widget tooltip text."""
        return QIcon()


class CondaStatus(StatusBarWidget):
    """Status bar widget for displaying the current conda environment."""

    def __init__(self, parent, icon=None):
        """Status bar widget for displaying the current conda environment."""
        self._interpreter = None
        super().__init__(parent, icon=self.create_icon('environment'))

    def _get_conda_env_info(self):
        """Get conda environment information."""
        try:
            out, err = subprocess.Popen(
                [self._interpreter, '-V'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ).communicate()

            out = out.decode()
            err = err.decode()
        except Exception:
            out = ''
            err = ''

        return out, err

    def _process_conda_env_info(self):
        """Process conda environment information."""
        out, err = self._get_conda_env_info()
        out = out or err  # Anaconda base python prints to stderr
        out = out.split('\n')[0]
        parts = out.split()

        if len(parts) >= 2:
            out = ' '.join(parts[:2])

        envs_folder = os.path.sep + 'envs' + os.path.sep
        if envs_folder in self._interpreter:
            if os.name == 'nt':
                env = os.path.dirname(self._interpreter)
            else:
                env = os.path.dirname(os.path.dirname(self._interpreter))
            env = os.path.basename(env)
        else:
            env = 'base'

        if utils.is_anaconda():
            text = 'conda: {env} ({version})'.format(env=env, version=out)
        else:
            text = ''

        return text

    def get_tooltip(self):
        """Override api method."""
        return self._interpreter if self._interpreter else ''

    def update_interpreter(self, interpreter):
        """Set main interpreter and update information."""
        self._interpreter = interpreter
        if utils.is_anaconda():
            text = self._process_conda_env_info()
        else:
            text = ''

        self.set_value(text)
        self.update_tooltip()


class ClockStatus(BaseTimerStatus):
    """"Add clock to statusbar in a fullscreen mode."""

    def import_test(self):
        pass

    def get_value(self):
        """Return the time."""
        from time import localtime, strftime
        text = strftime("%H:%M", localtime())

        return text.rjust(3)

    def get_tooltip(self):
        """Return the widget tooltip text."""
        return _('Clock')

    def get_icon(self):
        """Return the widget tooltip text."""
        return QIcon()


def test():
    from qtpy.QtWidgets import QMainWindow
    from spyder.utils.qthelpers import qapplication

    app = qapplication(test_time=5)
    win = QMainWindow()
    win.setWindowTitle("Status widgets test")
    win.resize(900, 300)
    status_widgets = []
    statusbar = win.statusBar()
    for status_class in (MemoryStatus, CPUStatus, ClockStatus):
        status_widget = status_class(win)
        statusbar.insertPermanentWidget(0, status_widget)
        status_widgets.append(status_widget)

    win.show()
    app.exec_()


if __name__ == "__main__":
    test()

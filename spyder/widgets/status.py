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
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.config import utils
from spyder.py3compat import PY3


class StatusBarWidget(QWidget):
    """Status bar widget base."""
    # Signals
    sig_clicked = Signal()

    def __init__(self, parent, statusbar, icon=None):
        """Status bar widget base."""
        super(StatusBarWidget, self).__init__(parent)

        # Variables
        self.value = None

        # Widget
        self._status_bar = statusbar
        self._icon = None
        self._pixmap = None
        self._icon_size = QSize(16, 16)  # Should this be adjustable?
        self.label_icon = QLabel()
        self.label_value = QLabel()

        # Layout setup
        layout = QHBoxLayout(self)
        layout.setSpacing(0)  # Reduce space between icon and label
        layout.addWidget(self.label_icon)
        layout.addWidget(self.label_value)
        layout.addSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        # Widget setup
        self.set_icon(icon)

        # See spyder-ide/spyder#9044.
        self.text_font = QFont(QFont().defaultFamily(), weight=QFont.Normal)
        self.label_value.setAlignment(Qt.AlignRight)
        self.label_value.setFont(self.text_font)

        # Setup
        statusbar.addPermanentWidget(self)
        self.set_value('')
        self.update_tooltip()

    # --- Status bar widget API
    # ------------------------------------------------------------------------
    def set_icon(self, icon):
        """Set the icon for the status bar widget."""
        self.label_icon.setVisible(icon is not None)
        if icon is not None and isinstance(icon, QIcon):
            self._icon = icon
            self._pixmap = icon.pixmap(self._icon_size)
            self.label_icon.setPixmap(self._pixmap)

    def set_value(self, value):
        """Set formatted text value."""
        self.value = value
        self.label_value.setText(value)

    def update_tooltip(self):
        """Update tooltip for widget."""
        tooltip = self.get_tooltip()
        if tooltip:
            self.label_value.setToolTip(tooltip)
            if self.label_icon:
                self.label_icon.setToolTip(tooltip)
            self.setToolTip(tooltip)

    def mouseReleaseEvent(self, event):
        """Override Qt method to allow for click signal."""
        super(StatusBarWidget, self).mousePressEvent(event)
        self.sig_clicked.emit()

    # --- API to be defined by user
    # ------------------------------------------------------------------------
    def get_tooltip(self):
        """Return the widget tooltip text."""
        return ''

    def get_icon(self):
        """Return the widget tooltip text."""
        return None


class BaseTimerStatus(StatusBarWidget):
    """Status bar widget base for widgets that update based on timers."""

    def __init__(self, parent, statusbar, icon=None):
        """Status bar widget base for widgets that update based on timers."""
        self.timer = None  # Needs to come before parent call
        super(BaseTimerStatus, self).__init__(parent, statusbar, icon=icon)
        self._interval = 2000

        # Widget setup
        fm = self.label_value.fontMetrics()
        self.label_value.setMinimumWidth(fm.width('000%'))

        # Setup
        if self.is_supported():
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_status)
            self.timer.start(self._interval)
        else:
            self.hide()

    # --- Status bar widget API
    # ------------------------------------------------------------------------
    def setVisible(self, value):
        """Override Qt method to stops timers if widget is not visible."""
        if self.timer is not None:
            if value:
                self.timer.start(self._interval)
            else:
                self.timer.stop()
        super(BaseTimerStatus, self).setVisible(value)

    def is_supported(self):
        """Return True if feature is supported."""
        try:
            self.import_test()
            return True
        except ImportError:
            return False

    def update_status(self):
        """Update status label widget, if widget is visible."""
        if self.isVisible():
            self.label_value.setText(self.get_value())

    def set_interval(self, interval):
        """Set timer interval (ms)."""
        self._interval = interval
        if self.timer is not None:
            self.timer.setInterval(interval)

    # --- API to be defined by user
    # ------------------------------------------------------------------------
    def import_test(self):
        """Raise ImportError if feature is not supported."""
        raise NotImplementedError

    def get_value(self):
        """Return formatted text value."""
        raise NotImplementedError


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

    def __init__(self, parent, statusbar, icon=None):
        """Status bar widget for displaying the current conda environment."""
        self._interpreter = None
        super(CondaStatus, self).__init__(parent, statusbar, icon=icon)

    def _get_conda_env_info(self):
        """Get conda environment information."""
        try:
            out, err = subprocess.Popen(
                [self._interpreter, '-V'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ).communicate()

            if PY3:
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
    statusbar = win.statusBar()
    status_widgets = []
    for status_class in (MemoryStatus, CPUStatus, ClockStatus):
        status_widget = status_class(win, statusbar)
        status_widgets.append(status_widget)
    win.show()
    app.exec_()


if __name__ == "__main__":
    test()

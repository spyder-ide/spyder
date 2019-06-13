# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Qt, QSize, QTimer
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QHBoxLayout, QLabel, QWidget

# Local imports
from spyder import dependencies
from spyder.config.base import _
from spyder.config.gui import get_font
from spyder.py3compat import to_text_string


if not os.name == 'nt':
    PSUTIL_REQVER = '>=0.3'
    dependencies.add("psutil", _("CPU and memory usage info in the status bar"),
                     required_version=PSUTIL_REQVER)


class StatusBarWidget(QWidget):
    """Status bar widget base."""
    TIP = None

    def __init__(self, parent, statusbar, icon=None):
        """Status bar widget base."""
        super(StatusBarWidget, self).__init__(parent)

        # Variables
        self.value = None

        # Widget
        self._icon = icon
        self._pixmap = icon.pixmap(QSize(16, 16)) if icon is not None else None
        self.label_icon = QLabel() if icon is not None else None
        self.label_value = QLabel()

        # Widget setup
        if icon is not None:
            self.label_icon.setPixmap(self._pixmap)
        self.text_font = QFont(get_font(option='font'))  # See Issue #9044
        self.text_font.setPointSize(self.font().pointSize())
        self.text_font.setBold(True)
        self.label_value.setAlignment(Qt.AlignRight)
        self.label_value.setFont(self.text_font)

        if self.TIP:
            self.setToolTip(self.TIP)
            self.label_value.setToolTip(self.TIP)

        # Layout
        layout = QHBoxLayout()
        if icon is not None:
            layout.addWidget(self.label_icon)
        layout.addWidget(self.label_value)
        layout.addSpacing(20)

        # Layout setup
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Setup
        statusbar.addPermanentWidget(self)

    def set_value(self, value):
        """Set formatted text value."""
        self.value = value
        if self.isVisible():
            self.label_value.setText(value)


class BaseTimerStatus(StatusBarWidget):
    """Status bar widget base for widgets that update based on timers."""

    def __init__(self, parent, statusbar):
        """Status bar widget base for widgets that update based on timers."""
        self.timer = None  # Needs to come before parent call
        super(BaseTimerStatus, self).__init__(parent, statusbar)
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

    def setVisible(self, value):
        """Override Qt method to stops timers if widget is not visible."""
        if self.timer is not None:
            if value:
                self.timer.start(self._interval)
            else:
                self.timer.stop()
        super(BaseTimerStatus, self).setVisible(value)

    def set_interval(self, interval):
        """Set timer interval (ms)."""
        self._interval = interval
        if self.timer is not None:
            self.timer.setInterval(interval)

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        raise NotImplementedError

    def is_supported(self):
        """Return True if feature is supported."""
        try:
            self.import_test()
            return True
        except ImportError:
            return False

    def get_value(self):
        """Return formatted text value."""
        raise NotImplementedError

    def update_status(self):
        """Update status label widget, if widget is visible."""
        if self.isVisible():
            self.label_value.setText(self.get_value())


# =============================================================================
# Main window-related status bar widgets
# =============================================================================
class MemoryStatus(BaseTimerStatus):
    """Status bar widget for system memory usage."""
    TIP = _("Memory usage")

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        from spyder.utils.system import memory_usage  # analysis:ignore

    def get_value(self):
        """Return memory usage."""
        from spyder.utils.system import memory_usage
        text = '%d%%' % memory_usage()
        return 'Mem ' + text.rjust(3)


class CPUStatus(BaseTimerStatus):
    """Status bar widget for system cpu usage."""
    TIP = _("CPU usage")

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


def test():
    from qtpy.QtWidgets import QMainWindow
    from spyder.utils.qthelpers import qapplication

    app = qapplication(test_time=5)
    win = QMainWindow()
    win.setWindowTitle("Status widgets test")
    win.resize(900, 300)
    statusbar = win.statusBar()
    status_widgets = []
    for status_class in (MemoryStatus, CPUStatus):
        status_widget = status_class(win, statusbar)
        status_widgets.append(status_widget)
    win.show()
    app.exec_()


if __name__ == "__main__":
    test()

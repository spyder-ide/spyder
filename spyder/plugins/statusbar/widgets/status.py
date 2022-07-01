# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Default status bar widgets."""

# Third party imports
import psutil

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.status import BaseTimerStatus
from spyder.utils.system import memory_usage


# Localization
_ = get_translation('spyder')


class MemoryStatus(BaseTimerStatus):
    """Status bar widget for system memory usage."""
    ID = 'memory_status'

    def get_value(self):
        """Return memory usage."""
        text = '%d%%' % memory_usage()
        return 'Mem ' + text.rjust(3)

    def get_tooltip(self):
        """Return the widget tooltip text."""
        return _('Global memory usage')


class CPUStatus(BaseTimerStatus):
    """Status bar widget for system cpu usage."""
    ID = 'cpu_status'

    def get_value(self):
        """Return CPU usage."""
        text = '%d%%' % psutil.cpu_percent(interval=0)
        return 'CPU ' + text.rjust(3)

    def get_tooltip(self):
        """Return the widget tooltip text."""
        return _('CPU usage')


class ClockStatus(BaseTimerStatus):
    """"Add clock to statusbar in a fullscreen mode."""
    ID = 'clock_status'

    def get_value(self):
        """Return the time."""
        from time import localtime, strftime
        text = strftime("%H:%M", localtime())

        return text.rjust(3)

    def get_tooltip(self):
        """Return the widget tooltip text."""
        return _('Clock')


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

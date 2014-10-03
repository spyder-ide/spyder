# -*- coding: utf-8 -*-
#
# Copyright © 2012 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Status bar widgets"""

import os

from spyderlib.qt.QtGui import QWidget, QHBoxLayout, QLabel
from spyderlib.qt.QtCore import QTimer, SIGNAL

# Local import
from spyderlib.baseconfig import _
from spyderlib.guiconfig import get_font
from spyderlib.py3compat import to_text_string
from spyderlib import dependencies


if not os.name == 'nt':
    PSUTIL_REQVER = '>=0.3'
    dependencies.add("psutil", _("CPU and memory usage info in the status bar"),
                     required_version=PSUTIL_REQVER)


class StatusBarWidget(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)

        self.label_font = font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        statusbar.addPermanentWidget(self)


#==============================================================================
# Main window-related status bar widgets
#==============================================================================
class BaseTimerStatus(StatusBarWidget):
    TITLE = None
    TIP = None
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        self.setToolTip(self.TIP)
        layout = self.layout()
        layout.addWidget(QLabel(self.TITLE))
        self.label = QLabel()
        self.label.setFont(self.label_font)
        layout.addWidget(self.label)
        layout.addSpacing(20)
        if self.is_supported():
            self.timer = QTimer()
            self.connect(self.timer, SIGNAL('timeout()'), self.update_label)
            self.timer.start(2000)
        else:
            self.timer = None
            self.hide()
    
    def set_interval(self, interval):
        """Set timer interval (ms)"""
        if self.timer is not None:
            self.timer.setInterval(interval)
    
    def import_test(self):
        """Raise ImportError if feature is not supported"""
        raise NotImplementedError

    def is_supported(self):
        """Return True if feature is supported"""
        try:
            self.import_test()
            return True
        except ImportError:
            return False
    
    def get_value(self):
        """Return value (e.g. CPU or memory usage)"""
        raise NotImplementedError
        
    def update_label(self):
        """Update status label widget, if widget is visible"""
        if self.isVisible():
            self.label.setText('%d %%' % self.get_value())

class MemoryStatus(BaseTimerStatus):
    TITLE = _("Memory:")
    TIP = _("Memory usage status: "
            "requires the `psutil` (>=v0.3) library on non-Windows platforms")
    def import_test(self):
        """Raise ImportError if feature is not supported"""
        from spyderlib.utils.system import memory_usage  # analysis:ignore

    def get_value(self):
        """Return memory usage"""
        from spyderlib.utils.system import memory_usage
        return memory_usage()

class CPUStatus(BaseTimerStatus):
    TITLE = _("CPU:")
    TIP = _("CPU usage status: requires the `psutil` (>=v0.3) library")
    def import_test(self):
        """Raise ImportError if feature is not supported"""
        from spyderlib.utils import programs
        if not programs.is_module_installed('psutil', '>=0.2.0'):
            # The `interval` argument in `psutil.cpu_percent` function
            # was introduced in v0.2.0
            raise ImportError

    def get_value(self):
        """Return CPU usage"""
        import psutil
        return psutil.cpu_percent(interval=0)


#==============================================================================
# Editor-related status bar widgets
#==============================================================================
class ReadWriteStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(_("Permissions:")))
        self.readwrite = QLabel()
        self.readwrite.setFont(self.label_font)
        layout.addWidget(self.readwrite)
        layout.addSpacing(20)
        
    def readonly_changed(self, readonly):
        readwrite = "R" if readonly else "RW"
        self.readwrite.setText(readwrite.ljust(3))

class EOLStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(_("End-of-lines:")))
        self.eol = QLabel()
        self.eol.setFont(self.label_font)
        layout.addWidget(self.eol)
        layout.addSpacing(20)
        
    def eol_changed(self, os_name):
        os_name = to_text_string(os_name)
        self.eol.setText({"nt": "CRLF", "posix": "LF"}.get(os_name, "CR"))

class EncodingStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(_("Encoding:")))
        self.encoding = QLabel()
        self.encoding.setFont(self.label_font)
        layout.addWidget(self.encoding)
        layout.addSpacing(20)
        
    def encoding_changed(self, encoding):
        self.encoding.setText(str(encoding).upper().ljust(15))

class CursorPositionStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(_("Line:")))
        self.line = QLabel()
        self.line.setFont(self.label_font)
        layout.addWidget(self.line)
        layout.addWidget(QLabel(_("Column:")))
        self.column = QLabel()
        self.column.setFont(self.label_font)
        layout.addWidget(self.column)
        self.setLayout(layout)
        
    def cursor_position_changed(self, line, index):
        self.line.setText("%-6d" % (line+1))
        self.column.setText("%-4d" % (index+1))


def test():
    from spyderlib.qt.QtGui import QMainWindow
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    win = QMainWindow()
    win.setWindowTitle("Status widgets test")
    win.resize(900, 300)
    statusbar = win.statusBar()
    swidgets = []
    for klass in (ReadWriteStatus, EOLStatus, EncodingStatus,
                  CursorPositionStatus, MemoryStatus, CPUStatus):
        swidget = klass(win, statusbar)
        swidgets.append(swidget)
    win.show()
    app.exec_()
    
if __name__ == "__main__":
    test()

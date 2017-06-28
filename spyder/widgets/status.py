# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import os

# Third party imports
from qtpy.QtCore import Qt, QTimer
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

    def __init__(self, parent, statusbar):
        """Status bar widget base."""
        super(StatusBarWidget, self).__init__(parent)
        self.label_font = get_font(option='rich_font')
        self.label_font.setPointSize(self.font().pointSize())
        self.label_font.setBold(True)

        # Layouts
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Setup
        statusbar.addPermanentWidget(self)


# =============================================================================
# Main window-related status bar widgets
# =============================================================================
class BaseTimerStatus(StatusBarWidget):
    """Status bar widget base for widgets that update based on timers."""

    TITLE = None
    TIP = None

    def __init__(self, parent, statusbar):
        """Status bar widget base for widgets that update based on timers."""
        super(BaseTimerStatus, self).__init__(parent, statusbar)

        # Widgets
        self.label = QLabel(self.TITLE)
        self.value = QLabel()

        # Widget setup
        self.setToolTip(self.TIP)
        self.value.setAlignment(Qt.AlignRight)
        self.value.setFont(self.label_font)
        fm = self.value.fontMetrics()
        self.value.setMinimumWidth(fm.width('000%'))

        # Layout
        layout = self.layout()
        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addSpacing(20)

        # Setup
        if self.is_supported():
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_label)
            self.timer.start(2000)
        else:
            self.timer = None
            self.hide()
    
    def set_interval(self, interval):
        """Set timer interval (ms)."""
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
        """Return value (e.g. CPU or memory usage)."""
        raise NotImplementedError
        
    def update_label(self):
        """Update status label widget, if widget is visible."""
        if self.isVisible():
            self.value.setText('%d %%' % self.get_value())


class MemoryStatus(BaseTimerStatus):
    """Status bar widget for system memory usage."""

    TITLE = _("Memory:")
    TIP = _("Memory usage status: "
            "requires the `psutil` (>=v0.3) library on non-Windows platforms")

    def import_test(self):
        """Raise ImportError if feature is not supported."""
        from spyder.utils.system import memory_usage  # analysis:ignore

    def get_value(self):
        """Return memory usage."""
        from spyder.utils.system import memory_usage
        return memory_usage()


class CPUStatus(BaseTimerStatus):
    """Status bar widget for system cpu usage."""

    TITLE = _("CPU:")
    TIP = _("CPU usage status: requires the `psutil` (>=v0.3) library")

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
        return psutil.cpu_percent(interval=0)


# =============================================================================
# Editor-related status bar widgets
# =============================================================================
class ReadWriteStatus(StatusBarWidget):    
    """Status bar widget for current file read/write mode."""

    def __init__(self, parent, statusbar):
        """Status bar widget for current file read/write mode."""
        super(ReadWriteStatus, self).__init__(parent, statusbar)

        # Widget
        self.label = QLabel(_("Permissions:"))
        self.readwrite = QLabel()

        # Widget setup
        self.label.setAlignment(Qt.AlignRight)
        self.readwrite.setFont(self.label_font)

        # Layouts
        layout = self.layout()
        layout.addWidget(self.label)
        layout.addWidget(self.readwrite)
        layout.addSpacing(20)
        
    def readonly_changed(self, readonly):
        """Update read/write file status."""
        readwrite = "R" if readonly else "RW"
        self.readwrite.setText(readwrite.ljust(3))


class EOLStatus(StatusBarWidget):
    """Status bar widget for the current file end of line."""

    def __init__(self, parent, statusbar):
        """Status bar widget for the current file end of line."""
        super(EOLStatus, self).__init__(parent, statusbar)

        # Widget
        self.label = QLabel(_("End-of-lines:"))
        self.eol = QLabel()

        # Widget setup
        self.label.setAlignment(Qt.AlignRight)
        self.eol.setFont(self.label_font)

        # Layouts
        layout = self.layout()
        layout.addWidget(self.label)
        layout.addWidget(self.eol)
        layout.addSpacing(20)
        
    def eol_changed(self, os_name):
        """Update end of line status."""
        os_name = to_text_string(os_name)
        self.eol.setText({"nt": "CRLF", "posix": "LF"}.get(os_name, "CR"))


class EncodingStatus(StatusBarWidget):
    """Status bar widget for the current file encoding."""

    def __init__(self, parent, statusbar):
        """Status bar widget for the current file encoding."""
        super(EncodingStatus, self).__init__(parent, statusbar)

        # Widgets
        self.label = QLabel(_("Encoding:"))
        self.encoding = QLabel()

        # Widget setup
        self.label.setAlignment(Qt.AlignRight)
        self.encoding.setFont(self.label_font)

        # Layouts
        layout = self.layout()
        layout.addWidget(self.label)
        layout.addWidget(self.encoding)
        layout.addSpacing(20)
        
    def encoding_changed(self, encoding):
        """Update encoding of current file."""
        self.encoding.setText(str(encoding).upper().ljust(15))


class CursorPositionStatus(StatusBarWidget):
    """Status bar widget for the current file cursor postion."""

    def __init__(self, parent, statusbar):
        """Status bar widget for the current file cursor postion."""
        super(CursorPositionStatus, self).__init__(parent, statusbar)

        # Widget
        self.label_line = QLabel(_("Line:"))
        self.label_column = QLabel(_("Column:"))
        self.column = QLabel()
        self.line = QLabel()

        # Widget setup
        self.line.setFont(self.label_font)
        self.column.setFont(self.label_font)

        # Layout
        layout = self.layout()
        layout.addWidget(self.label_line)
        layout.addWidget(self.line)
        layout.addWidget(self.label_column)
        layout.addWidget(self.column)
        self.setLayout(layout)
        
    def cursor_position_changed(self, line, index):
        """Update cursos position."""
        self.line.setText("%-6d" % (line+1))
        self.column.setText("%-4d" % (index+1))


def test():
    from qtpy.QtWidgets import QMainWindow
    from spyder.utils.qthelpers import qapplication

    app = qapplication(test_time=5)
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

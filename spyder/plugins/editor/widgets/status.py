# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Local imports
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.widgets.status import StatusBarWidget


class ReadWriteStatus(StatusBarWidget):
    """Status bar widget for current file read/write mode."""
    TIP = _("File permissions")

    def update_readonly(self, readonly):
        """Update read/write file status."""
        value = "R" if readonly else "RW"
        self.set_value(value.ljust(3))


class EOLStatus(StatusBarWidget):
    """Status bar widget for the current file end of line."""
    TIP = _("End of line")

    def update_eol(self, os_name):
        """Update end of line status."""
        os_name = to_text_string(os_name)
        value = {"nt": "CRLF", "posix": "LF"}.get(os_name, "CR")
        self.set_value(value)


class EncodingStatus(StatusBarWidget):
    """Status bar widget for the current file encoding."""
    TIP = _("Encoding")

    def update_encoding(self, encoding):
        """Update encoding of current file."""
        value = str(encoding).upper()
        self.set_value(value)


class CursorPositionStatus(StatusBarWidget):
    """Status bar widget for the current file cursor postion."""
    TIP = _("Cursor position")

    def update_cursor_position(self, line, index):
        """Update cursor position."""
        value = 'Line {}, Col {}'.format(line + 1, index + 1)
        self.set_value(value)


def test():
    from qtpy.QtWidgets import QMainWindow
    from spyder.utils.qthelpers import qapplication

    app = qapplication(test_time=5)
    win = QMainWindow()
    win.setWindowTitle("Status widgets test")
    win.resize(900, 300)
    statusbar = win.statusBar()
    status_widgets = []
    for status_class in (ReadWriteStatus, EOLStatus, EncodingStatus,
                         CursorPositionStatus):
        status_widget = status_class(win, statusbar)
        status_widgets.append(status_widget)
    win.show()
    app.exec_()


if __name__ == "__main__":
    test()

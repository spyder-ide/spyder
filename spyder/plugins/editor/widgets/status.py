# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import os.path as osp

# Local imports
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.workers import WorkerManager
from spyder.utils.vcs import get_git_refs
from spyder.widgets.status import StatusBarWidget


class ReadWriteStatus(StatusBarWidget):
    """Status bar widget for current file read/write mode."""

    def update_readonly(self, readonly):
        """Update read/write file status."""
        value = "R" if readonly else "RW"
        self.set_value(value.ljust(3))

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("File permissions")


class EOLStatus(StatusBarWidget):
    """Status bar widget for the current file end of line."""

    def update_eol(self, os_name):
        """Update end of line status."""
        os_name = to_text_string(os_name)
        value = {"nt": "CRLF", "posix": "LF"}.get(os_name, "CR")
        self.set_value(value)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("File EOL Status")


class EncodingStatus(StatusBarWidget):
    """Status bar widget for the current file encoding."""

    def update_encoding(self, encoding):
        """Update encoding of current file."""
        value = str(encoding).upper()
        self.set_value(value)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Encoding")


class CursorPositionStatus(StatusBarWidget):
    """Status bar widget for the current file cursor postion."""

    def update_cursor_position(self, line, index):
        """Update cursor position."""
        value = 'Line {}, Col {}'.format(line + 1, index + 1)
        self.set_value(value)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Cursor position")


class VCSStatus(StatusBarWidget):
    """Status bar widget for system vcs."""

    def __init__(self, parent, statusbar):
        super(VCSStatus, self).__init__(parent, statusbar,
                                        icon=ima.icon('code_fork'))
        self._worker_manager = WorkerManager(max_threads=1)
        self._git_is_working = None
        self._git_job_queue = None
        self._last_git_job = None

    def update_vcs_state(self, idx, fname, fname2):
        """Update vcs status."""
        self.update_vcs(fname, None)

    def update_vcs(self, fname, index, force=False):
        """Update vcs status."""
        if self._last_git_job == (fname, index) and not force:
            self._git_job_queue = None
            return

        if self._git_is_working:
            self._git_job_queue = (fname, index)
        else:
            self._worker_manager.terminate_all()
            worker = self._worker_manager.create_python_worker(
                self.get_git_refs, fname)
            worker.sig_finished.connect(self.process_git_data)
            self._last_git_job = (fname, index)
            self._git_job_queue = None
            self._git_is_working = True
            worker.start()

    def get_git_refs(self, fname):
        """Get Git active branch, state, branches (plus tags)."""
        return get_git_refs(osp.dirname(fname))

    def process_git_data(self, worker, output, error):
        """Receive data from git and update gui."""
        branches, branch, files_modified = output

        text = branch if branch else ''
        if len(files_modified):
            text = text + ' [{}]'.format(len(files_modified))
        self.setVisible(bool(branch))
        self.set_value(text)

        self._git_is_working = False
        if self._git_job_queue:
            self.update_vcs(*self._git_job_queue)

    def change_branch(self):
        """Change current branch."""
        pass

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Git branch")


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

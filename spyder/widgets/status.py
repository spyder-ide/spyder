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
import os.path as osp
import sys

# Third party imports
from qtpy.QtCore import Qt, QPoint, QSize, QTimer, Signal
from qtpy.QtGui import QFont, QIcon
from qtpy.QtWidgets import QHBoxLayout, QLabel, QMenu, QWidget

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.utils.conda import get_list_conda_envs
from spyder.utils.programs import get_interpreter_info
from spyder.utils.pyenv import get_list_pyenv_envs
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_waitspinner)
from spyder.utils.workers import WorkerManager


class StatusBarWidget(QWidget):
    """Status bar widget base."""
    # Signals
    sig_clicked = Signal()

    def __init__(self, parent, statusbar, icon=None, spinner=False):
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
        self.spinner = None
        if spinner:
            self.spinner = create_waitspinner(size=14, parent=self)

        # Layout setup
        layout = QHBoxLayout(self)
        layout.setSpacing(0)  # Reduce space between icon and label
        layout.addWidget(self.label_icon)
        layout.addWidget(self.label_value)
        if spinner:
            layout.addWidget(self.spinner)
            self.spinner.hide()
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


class InterpreterStatus(BaseTimerStatus):
    """Status bar widget for displaying the current conda environment."""

    def __init__(self, parent, statusbar, icon=None, interpreter=None):
        """Status bar widget for displaying the current conda environment."""
        self._interpreter = interpreter
        super(InterpreterStatus, self).__init__(parent, statusbar, icon=icon)

        self.main = parent
        self.env_actions = []
        self.path_to_env = {}
        self.envs = {}
        self.value = ''

        self.menu = QMenu(self)
        self.sig_clicked.connect(self.show_menu)

        # Worker to compute envs in a thread
        self._worker_manager = WorkerManager(max_threads=1)

        # Timer to get envs every minute
        self._get_envs_timer = QTimer(self)
        self._get_envs_timer.setInterval(60000)
        self._get_envs_timer.timeout.connect(self.get_envs)
        self._get_envs_timer.start()

        # Update the list of envs at startup
        self.get_envs()

    def import_test(self):
        pass

    def get_value(self):
        """
        Switch to default interpreter if current env was removed or
        update Python version of current one.
        """
        env_dir = self._get_env_dir(self._interpreter)

        if not osp.isdir(env_dir):
            # Env was removed on Mac or Linux
            CONF.set('main_interpreter', 'custom', False)
            CONF.set('main_interpreter', 'default', True)
            self.update_interpreter(sys.executable)
        elif not osp.isfile(self._interpreter):
            # This can happen on Windows because the interpreter was
            # renamed to .conda_trash
            if not osp.isdir(osp.join(env_dir, 'conda-meta')):
                # If conda-meta is missing, it means the env was removed
                CONF.set('main_interpreter', 'custom', False)
                CONF.set('main_interpreter', 'default', True)
                self.update_interpreter(sys.executable)
            else:
                # If not, it means the interpreter is being updated so
                # we need to update its version
                self.get_envs()
        else:
            # We need to do this in case the Python version was
            # changed in the env
            if self._interpreter in self.path_to_env:
                self.update_interpreter()

        return self.value

    def _get_env_dir(self, interpreter):
        """Get env directory from interpreter executable."""
        if os.name == 'nt':
            return osp.dirname(interpreter)
        else:
            return osp.dirname(osp.dirname(interpreter))

    def _get_envs(self):
        """Get the list of environments in the system."""
        # Compute info of default interpreter to have it available in
        # case we need to switch to it. This will avoid lags when
        # doing that in get_value.
        if sys.executable not in self.path_to_env:
            self._get_env_info(sys.executable)

        # Get envs
        conda_env = get_list_conda_envs()
        pyenv_env = get_list_pyenv_envs()
        return {**conda_env, **pyenv_env}

    def get_envs(self):
        """
        Get the list of environments in a thread to keep them up to
        date.
        """
        self._worker_manager.terminate_all()
        worker = self._worker_manager.create_python_worker(self._get_envs)
        worker.sig_finished.connect(self.update_envs)
        worker.start()

    def update_envs(self, worker, output, error):
        """Update the list of environments in the system."""
        self.envs.update(**output)
        for env in list(self.envs.keys()):
            path, version = self.envs[env]
            # Save paths in lowercase on Windows to avoid issues with
            # capitalization.
            path = path.lower() if os.name == 'nt' else path
            self.path_to_env[path] = env

        self.update_interpreter()

    def show_menu(self):
        """Display a menu when clicking on the widget."""
        menu = self.menu
        menu.clear()
        text = _("Change default environment in Preferences...")
        change_action = create_action(
            self,
            text=text,
            triggered=self.open_interpreter_preferences,
        )
        add_actions(menu, [change_action])
        rect = self.contentsRect()
        os_height = 7 if os.name == 'nt' else 12
        pos = self.mapToGlobal(
                rect.topLeft() + QPoint(-40, -rect.height() - os_height))
        menu.popup(pos)

    def open_interpreter_preferences(self):
        """Open the Preferences dialog in the Python interpreter section."""
        self.main.show_preferences()
        dlg = self.main.prefs_dialog_instance
        index = dlg.get_index_by_name("main_interpreter")
        dlg.set_current_index(index)

    def _get_env_info(self, path):
        """Get environment information."""
        path = path.lower() if os.name == 'nt' else path
        try:
            name = self.path_to_env[path]
        except KeyError:
            win_app_path = osp.join(
                'AppData', 'Local', 'Programs', 'spyder')
            if 'Spyder.app' in path or win_app_path in path:
                name = 'internal'
            elif 'conda' in path:
                name = 'conda'
            elif 'pyenv' in path:
                name = 'pyenv'
            else:
                name = 'custom'
            version = get_interpreter_info(path)
            self.path_to_env[path] = name
            self.envs[name] = (path, version)
        __, version = self.envs[name]
        return f'{name} ({version})'

    def get_tooltip(self):
        """Override api method."""
        return self._interpreter if self._interpreter else ''

    def update_interpreter(self, interpreter=None):
        """Set main interpreter and update information."""
        if interpreter:
            self._interpreter = interpreter
        self.value = self._get_env_info(self._interpreter)
        self.set_value(self.value)
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

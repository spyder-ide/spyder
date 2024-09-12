# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import functools
import logging
import sys
import textwrap

# Third-party imports
from IPython.core import release as ipython_release
from qtpy.QtCore import Signal
from spyder_kernels.comms.frontendcomm import CommError
from spyder_kernels.utils.pythonenv import PythonEnvInfo, PythonEnvType

# Local imports
from spyder.api.shellconnect.status import ShellConnectStatusBarWidget
from spyder.api.translations import _
from spyder.config.base import running_in_ci


logger = logging.getLogger(__name__)


class MatplotlibStatus(ShellConnectStatusBarWidget):
    """Status bar widget for current Matplotlib backend."""

    ID = "matplotlib_status"
    CONF_SECTION = 'ipython_console'
    INTERACT_ON_CLICK = True

    def __init__(self, parent):
        super().__init__(parent)

        self._gui = None
        self._interactive_gui = None

        # Signals
        self.sig_clicked.connect(self.toggle_matplotlib)

    # ---- StatusBarWidget API
    # -------------------------------------------------------------------------
    def get_tooltip(self):
        """Return localized tooltip for widget."""
        msg = _(
            "Click to toggle between inline and interactive Matplotlib "
            "plotting"
        )
        msg = '\n'.join(textwrap.wrap(msg, width=40))
        return msg

    def get_icon(self):
        return self.create_icon('plot')

    # ---- Public API
    # -------------------------------------------------------------------------
    def toggle_matplotlib(self):
        """Toggle matplotlib interactive backend."""
        if self.current_shellwidget is None or self._gui is None:
            return

        if self._gui != "inline":
            # Switch to inline for any backend that is not inline
            backend = "inline"
            self._interactive_gui = self._gui
        else:
            if self._interactive_gui is None:
                # Use the auto backend in case the interactive backend hasn't
                # been set yet
                backend = "auto"
            else:
                # Always use the interactive backend otherwise
                backend = self._interactive_gui

        sw = self.current_shellwidget
        sw.execute("%matplotlib " + backend)
        is_spyder_kernel = sw.is_spyder_kernel

        if not is_spyder_kernel:
            self.update_matplotlib_gui(backend)

    def update_matplotlib_gui(self, gui, shellwidget=None):
        """Update matplotlib interactive."""
        if shellwidget is None:
            shellwidget = self.current_shellwidget
            if shellwidget is None:
                return

        if shellwidget in self.shellwidget_to_status:
            self.shellwidget_to_status[shellwidget] = gui
            if shellwidget == self.current_shellwidget:
                self.update_status(gui)

    # ---- ShellConnectStatusBarWidget API
    # -------------------------------------------------------------------------
    def update_status(self, gui):
        """Update interactive state."""
        logger.debug(f"Setting Matplotlib backend to {gui}")

        if self._interactive_gui is None and gui != "inline":
            self._interactive_gui = gui
        self._gui = gui

        if gui == "inline":
            text = _("Inline")
        elif gui == "auto":
            text = _("Automatic")
        elif gui == "macosx":
            text = "macOS"
        else:
            text = gui.capitalize()

        self.set_value(text)

    def config_spyder_kernel(self, shellwidget):
        shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "update_matplotlib_gui",
            functools.partial(
                self.update_matplotlib_gui, shellwidget=shellwidget
            )
        )
        shellwidget.set_kernel_configuration("update_gui", True)

    def on_kernel_start(self, shellwidget):
        """Actions to take when the kernel starts."""
        # Reset value of interactive backend
        self._interactive_gui = None

        # Avoid errors when running our test suite on Mac and Windows.
        # On Windows the following error appears:
        # `spyder_kernels.comms.commbase.CommError: The comm is not connected.`
        if running_in_ci() and not sys.platform.startswith("linux"):
            mpl_backend = "inline"
        else:
            # Needed when the comm is not connected.
            # Fixes spyder-ide/spyder#22194
            try:
                mpl_backend = shellwidget.get_matplotlib_backend()
            except CommError:
                mpl_backend = None

        # Associate detected backend to shellwidget
        self.shellwidget_to_status[shellwidget] = mpl_backend

        # Hide widget if Matplotlib is not available or failed to import in the
        # kernel
        if mpl_backend is None:
            self.hide()
        else:
            self.set_shellwidget(shellwidget)
            self.show()

        # Ask the kernel to update the current backend, in case it has changed
        shellwidget.set_kernel_configuration("update_gui", True)

    def remove_shellwidget(self, shellwidget):
        """
        Overridden method to remove the call handler registered by this widget.
        """
        shellwidget.kernel_handler.kernel_comm.unregister_call_handler(
            "update_matplotlib_gui"
        )
        super().remove_shellwidget(shellwidget)


class PythonEnvironmentStatus(ShellConnectStatusBarWidget):
    """
    Status bar widget for displaying the Python environment used by the current
    console.
    """

    ID = 'pythonenv_status'
    CONF_SECTION = 'ipython_console'

    sig_interpreter_changed = Signal(str)

    def __init__(self, parent):
        self._current_env_info: PythonEnvInfo | None = None
        super().__init__(parent)

    # ---- StatusBarWidget API
    # -------------------------------------------------------------------------
    def get_tooltip(self):
        return self._current_env_info["path"] if self._current_env_info else ""

    # ---- ShellConnectStatusBarWidget API
    # -------------------------------------------------------------------------
    def update_status(self, env_info: dict):
        """Update env info."""
        if (
            # There's no need to emit this signal for remote consoles because
            # other plugins can only react to local interpreter changes.
            not self.current_shellwidget.is_remote()
            and env_info != self._current_env_info
        ):
            new_interpreter = env_info["path"]
            logger.debug(f"Console interpreter changed to {new_interpreter}")
            self.sig_interpreter_changed.emit(new_interpreter)

        self._current_env_info = env_info

        if env_info["env_type"] == PythonEnvType.Conda:
            env_type = "Conda"
        elif env_info["env_type"] == PythonEnvType.PyEnv:
            env_type = "Pyenv"
        else:
            env_type = _("Custom")

        # The format to display is:
        # env_type: env_name (Python python_version)
        text = (
            env_type
            + ": "
            + env_info["name"]
            + " (Python "
            + env_info["python_version"]
            + ")"
        )
        self.set_value(text)

    def on_kernel_start(self, shellwidget):
        """Actions to take when the kernel starts."""
        # Avoid errors when running our test suite on Mac and Windows.
        # On Windows the following error appears:
        # `spyder_kernels.comms.commbase.CommError: The comm is not connected.`
        if running_in_ci() and not sys.platform.startswith("linux"):
            env_info = PythonEnvInfo(
                path=sys.executable,
                env_type=PythonEnvType.Conda,
                name="foo",
                python_version=".".join(
                    [str(n) for n in sys.version_info[:3]]
                ),
                ipython_version=ipython_release.version,
                sys_version=sys.version,
            )
        else:
            # Handle any possible error.
            try:
                env_info = shellwidget.get_pythonenv_info()
            except Exception:
                env_info = None

        # Associate env info to shellwidget
        self.shellwidget_to_status[shellwidget] = env_info

        # Update status
        if env_info is None:
            self.hide()
        else:
            self.set_shellwidget(shellwidget)
            self.show()

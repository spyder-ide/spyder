# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Standard library imports
import functools
import sys
import textwrap

# Third-party imports
from spyder_kernels.comms.frontendcomm import CommError

# Local imports
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.translations import _
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import running_in_ci


class MatplotlibStatus(StatusBarWidget, ShellConnectMixin):
    """Status bar widget for current Matplotlib backend."""

    ID = "matplotlib_status"
    CONF_SECTION = 'ipython_console'
    INTERACT_ON_CLICK = True

    def __init__(self, parent):
        super().__init__(parent)
        self._gui = None
        self._interactive_gui = None
        self._shellwidget_dict = {}
        self._current_id = None

        # Signals
        self.sig_clicked.connect(self.toggle_matplotlib)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        msg = _(
            "Click to toggle between inline and interactive Matplotlib "
            "plotting"
        )
        msg = '\n'.join(textwrap.wrap(msg, width=40))
        return msg

    def toggle_matplotlib(self):
        """Toggle matplotlib interactive backend."""
        if self._current_id is None or self._gui == 'failed':
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

        sw = self._shellwidget_dict[self._current_id]["widget"]
        sw.execute("%matplotlib " + backend)
        is_spyder_kernel = self._shellwidget_dict[self._current_id][
            "widget"].is_spyder_kernel

        if not is_spyder_kernel:
            self.update_matplotlib_gui(backend)

    def update_matplotlib_gui(self, gui, shellwidget_id=None):
        """Update matplotlib interactive."""
        if shellwidget_id is None:
            shellwidget_id = self._current_id
            if shellwidget_id is None:
                return

        if shellwidget_id in self._shellwidget_dict:
            self._shellwidget_dict[shellwidget_id]["gui"] = gui
            if shellwidget_id == self._current_id:
                self.update_status(gui)

    def update_status(self, gui):
        """Update interactive state."""
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

    def add_shellwidget(self, shellwidget):
        """Add shellwidget."""
        shellwidget.sig_config_spyder_kernel.connect(
            functools.partial(self.config_spyder_kernel, shellwidget)
        )
        shellwidget.kernel_handler.sig_kernel_is_ready.connect(
            # We can't use functools.partial here because it gives memory leaks
            # in Python versions older than 3.10
            lambda sw=shellwidget: self.on_kernel_start(sw)
        )

        backend = self.get_conf('pylab/backend')
        swid = id(shellwidget)
        self._shellwidget_dict[swid] = {
            "gui": backend,
            "widget": shellwidget,
        }
        self.set_shellwidget(shellwidget)

    def config_spyder_kernel(self, shellwidget):
        shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "update_matplotlib_gui",
            functools.partial(
                self.update_matplotlib_gui, shellwidget_id=id(shellwidget)
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

        # Hide widget if Matplotlib is not available or failed to import
        if mpl_backend is None:
            gui = "failed"
            self._shellwidget_dict[id(shellwidget)]['gui'] = gui
            self.hide()
        else:
            self.show()

        # Ask the kernel to update the current backend, in case it has changed
        shellwidget.set_kernel_configuration("update_gui", True)

    def set_shellwidget(self, shellwidget):
        """Set current shellwidget."""
        self._current_id = None
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidget_dict:
            gui = self._shellwidget_dict[shellwidget_id]["gui"]
            if gui == "failed":
                # This means the console failed to start or Matplotlib is not
                # installed in the kernel. So, we don't need to show this
                # widget in those cases.
                self.hide()
            else:
                self.show()
                self.update_status(gui)
                self._current_id = shellwidget_id

    def remove_shellwidget(self, shellwidget):
        """Remove shellwidget."""
        shellwidget.kernel_handler.kernel_comm.unregister_call_handler(
            "update_matplotlib_gui"
        )
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidget_dict:
            del self._shellwidget_dict[shellwidget_id]

    def add_errored_shellwidget(self, shellwidget):
        """Add errored shellwidget."""
        swid = id(shellwidget)
        self._shellwidget_dict[swid] = {
            "gui": 'failed',
            "widget": shellwidget,
        }
        self.set_shellwidget(shellwidget)

    def get_icon(self):
        return self.create_icon('plot')

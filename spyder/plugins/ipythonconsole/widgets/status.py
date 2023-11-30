# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""

# Local imports
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.base import _


class MatplotlibStatus(StatusBarWidget, ShellConnectMixin):
    """Status bar widget for current Matplotlib backend."""

    ID = "matplotlib_status"
    CONF_SECTION = 'ipython_console'

    def __init__(self, parent):
        super().__init__(parent)
        self._gui = None
        self._shellwidget_dict = {}
        self._current_id = None

        # Signals
        self.sig_clicked.connect(self.toggle_matplotlib)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Click to toggle between inline and interactive plotting")

    def toggle_matplotlib(self):
        """Toggle matplotlib interactive backend."""
        if self._current_id is None or self._gui == 'failed':
            return
        backend = "inline" if self._gui != "inline" else "auto"
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
                self.update(gui)

    def update(self, gui):
        """Update interactive state."""
        self._gui = gui
        if gui == "inline":
            text = _("Inline")
        elif gui == 'failed':
            text = _('No backend')
        else:
            text = _("Interactive")
        self.set_value(text)

    def add_shellwidget(self, shellwidget):
        """Add shellwidget."""
        shellwidget.sig_config_spyder_kernel.connect(
            lambda sw=shellwidget: self.config_spyder_kernel(sw)
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
            lambda gui, sid=id(shellwidget):
                self.update_matplotlib_gui(gui, sid)
        )
        shellwidget.set_kernel_configuration("update_gui", True)

    def set_shellwidget(self, shellwidget):
        """Set current shellwidget."""
        self._current_id = None
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidget_dict:
            self.update(self._shellwidget_dict[shellwidget_id]["gui"])
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

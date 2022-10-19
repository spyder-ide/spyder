# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""
# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.api.widgets.status import StatusBarWidget
from spyder_kernels.utils.mpl import MPL_BACKENDS_FROM_SPYDER
from spyder.api.shellconnect.mixins import ShellConnectMixin


class MatplotlibStatus(StatusBarWidget, ShellConnectMixin):
    """Status bar widget for current matplotlib mode."""

    ID = "matplotlib_status"

    def __init__(self, parent):
        super(MatplotlibStatus, self).__init__(
            parent)
        self._gui = None
        self._shellwidget_dict = {}
        self._current_id = None
        # Signals
        self.sig_clicked.connect(self.toggle_matplotlib)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Matplotlib interactive.")

    def toggle_matplotlib(self):
        """Toggle matplotlib ineractive."""
        if self._current_id is None:
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
        self.set_value(_("Matplotlib: {}").format(gui))

    def add_shellwidget(self, shellwidget):
        """Add shellwidget."""
        shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "update_matplotlib_gui",
            lambda gui, sid=id(shellwidget):
                self.update_matplotlib_gui(gui, sid))
        backend = MPL_BACKENDS_FROM_SPYDER[
            str(CONF.get('ipython_console', 'pylab/backend'))]
        swid = id(shellwidget)
        self._shellwidget_dict[swid] = {
            "gui": backend,
            "widget": shellwidget,
            }
        self.set_shellwidget(shellwidget)

    def set_shellwidget(self, shellwidget):
        """Set current shellwidget."""
        self._current_id = None
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidget_dict:
            self.update(self._shellwidget_dict[shellwidget_id]["gui"])
            self._current_id = shellwidget_id

    def remove_shellwidget(self, shellwidget):
        """Remove shellwidget."""
        shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "update_matplotlib_gui", None)
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidget_dict:
            del self._shellwidget_dict[shellwidget_id]

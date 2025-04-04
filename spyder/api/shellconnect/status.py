# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Status bar widget that shows content that comes from the IPython console.
"""

# Standard library imports
import functools

# Local imports
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.widgets.status import StatusBarWidget


class ShellConnectStatusBarWidget(StatusBarWidget, ShellConnectMixin):
    """
    Base class for status bar widgets whose info depends on the current shell.
    """

    def __init__(self, parent):
        super().__init__(parent)

        # Mapping from shellwidgets to their corresponding statuses
        self.shellwidget_to_status = {}

        # Current associated shellwidget
        self.current_shellwidget = None

    # ---- Public API
    # -------------------------------------------------------------------------
    def update_status(self, status):
        """
        Actions to take to update the widget status after switching consoles.
        """
        raise NotImplementedError

    def on_kernel_start(self, shellwidget):
        """Actions to take when the kernel starts."""
        raise NotImplementedError

    def config_spyder_kernel(self, shellwidget):
        """Actions to take to configure the kernel."""
        pass

    # ---- ShellConnectMixin API
    # -------------------------------------------------------------------------
    def set_shellwidget(self, shellwidget):
        """
        Actions to take when setting (i.e. giving focus to) a shellwidget.
        """
        self.current_shellwidget = None
        if shellwidget in self.shellwidget_to_status:
            status = self.shellwidget_to_status[shellwidget]
            if status is None:
                # This means the console failed to start or there was a problem
                # obtaining the status from the kernel. So, we don't need to
                # show this widget in those cases.
                self.hide()
            else:
                self.show()
                self.current_shellwidget = shellwidget
                self.update_status(status)

    def add_shellwidget(self, shellwidget):
        """Actions to take when adding a shellwidget."""
        shellwidget.sig_config_spyder_kernel.connect(
            functools.partial(self.config_spyder_kernel, shellwidget)
        )
        shellwidget.kernel_handler.sig_kernel_is_ready.connect(
            # We can't use functools.partial here because it gives memory leaks
            # in Python versions older than 3.10
            lambda sw=shellwidget: self.on_kernel_start(sw)
        )

        self.shellwidget_to_status[shellwidget] = None
        self.set_shellwidget(shellwidget)

    def remove_shellwidget(self, shellwidget):
        """Actions to take when removing a shellwidget."""
        if shellwidget in self.shellwidget_to_status:
            self.shellwidget_to_status.pop(shellwidget)

    def add_errored_shellwidget(self, shellwidget):
        """Actions to take when a shellwidget errored."""
        self.shellwidget_to_status[shellwidget] = None
        self.set_shellwidget(shellwidget)

# -----------------------------------------------------------------------------
# Copyright (c) 2024- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Status bar widget to show content from the IPython console.
"""

from __future__ import annotations

# Standard library imports
import functools
from typing import TYPE_CHECKING, Any

# Local imports
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.widgets.status import StatusBarWidget

if TYPE_CHECKING:
    import spyder.plugins.ipythonconsole.widgets
    from spyder.api.widgets.main_widget import PluginMainWidget


class ShellConnectStatusBarWidget(StatusBarWidget, ShellConnectMixin):
    """
    Base class for status bar widgets whose info depends on the current shell.
    """

    def __init__(self, parent: PluginMainWidget) -> None:
        """
        Create a new status bar widget to display content from a shell widget.

        Parameters
        ----------
        parent : PluginMainWidget
            The parent widget to this one.

        Returns
        -------
        None
        """
        super().__init__(parent)

        self.shellwidget_to_status: dict[
            spyder.plugins.ipythonconsole.widgets.ShellWidget, Any
        ] = {}
        """
        Mapping from shell widgets to their corresponding statuses.

        The specific type of status information stored will depend on
        what the implementing class needs to display.
        """

        self.current_shellwidget: (
            spyder.plugins.ipythonconsole.widgets.ShellWidget | None
        ) = None
        """Currently active associated shell widget."""

    # ---- Public API
    # -------------------------------------------------------------------------
    def update_status(self, status: Any):
        """
        Actions to take to update the widget status after switching consoles.

        Parameters
        ----------
        status : Any
            The shell widget status information needed by the status widget.
            To be defined by the implementing class.
        """
        raise NotImplementedError

    def on_kernel_start(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Actions to take after the kernel starts.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget whose kernel was started.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def config_spyder_kernel(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Actions to take to configure the kernel.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget whose kernel will be configured.

        Returns
        -------
        None
        """
        pass

    # ---- ShellConnectMixin API
    # -------------------------------------------------------------------------
    def set_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Actions to take when setting (i.e. giving focus to) a shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that will be given focus.

        Returns
        -------
        None
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

    def add_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Actions to take when adding a shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that will be added.

        Returns
        -------
        None
        """
        shellwidget.sig_config_spyder_kernel.connect(
            functools.partial(self.config_spyder_kernel, shellwidget)
        )
        shellwidget.sig_kernel_is_ready.connect(
            # We can't use functools.partial here because it gives memory leaks
            # in Python versions older than 3.10
            lambda sw=shellwidget: self.on_kernel_start(sw)
        )

        self.shellwidget_to_status[shellwidget] = None
        self.set_shellwidget(shellwidget)

    def remove_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Actions to take when removing a shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that will have its associated widget removed.

        Returns
        -------
        None
        """
        if shellwidget in self.shellwidget_to_status:
            self.shellwidget_to_status.pop(shellwidget)

    def add_errored_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Actions to take when a shell widget has failed with an error.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that failed with an error.

        Returns
        -------
        None
        """
        self.shellwidget_to_status[shellwidget] = None
        self.set_shellwidget(shellwidget)

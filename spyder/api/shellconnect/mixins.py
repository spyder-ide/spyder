# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Mixins for plugins/widgets that are connected to the IPython console.
"""

from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugin_registration.decorators import (
    on_plugin_available,
    on_plugin_teardown,
)
from spyder.api.plugins import Plugins

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

    import spyder.plugins.ipythonconsole.plugin
    import spyder.plugins.ipythonconsole.widgets


class ShellConnectMixin:
    """
    Mixin to connect any widget or object to the shell widgets in the IPython
    console.
    """

    # ---- Connection to the IPython console
    # -------------------------------------------------------------------------
    def register_ipythonconsole(
        self,
        ipythonconsole: spyder.plugins.ipythonconsole.plugin.IPythonConsole,
    ) -> None:
        """Register signals from the console."""
        ipythonconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipythonconsole.sig_shellwidget_created.connect(self.add_shellwidget)
        ipythonconsole.sig_shellwidget_deleted.connect(self.remove_shellwidget)
        ipythonconsole.sig_shellwidget_errored.connect(
            self.add_errored_shellwidget
        )

    def unregister_ipythonconsole(
        self,
        ipythonconsole: spyder.plugins.ipythonconsole.plugin.IPythonConsole,
    ) -> None:
        """Unregister signals from the console."""
        ipythonconsole.sig_shellwidget_changed.disconnect(self.set_shellwidget)
        ipythonconsole.sig_shellwidget_created.disconnect(self.add_shellwidget)
        ipythonconsole.sig_shellwidget_deleted.disconnect(
            self.remove_shellwidget
        )
        ipythonconsole.sig_shellwidget_errored.disconnect(
            self.add_errored_shellwidget
        )

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Update the current shellwidget."""
        raise NotImplementedError

    def add_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Add a new shellwidget to be registered."""
        raise NotImplementedError

    def remove_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Remove a registered shellwidget."""
        raise NotImplementedError

    def add_errored_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """Register a new shellwidget whose kernel failed to start."""
        raise NotImplementedError


class ShellConnectWidgetForStackMixin:
    """
    Mixin for widgets that will be added to the stacked widget part of
    ShellConnectMainWidget.
    """

    sig_show_empty_message_requested = Signal(bool)
    """
    Signal to request that the empty message will be shown/hidden.

    Parameters
    ----------
    show_empty_message: bool
        Whether show the empty message or this widget must be shown.
    """

    def __init__(self) -> None:
        # This attribute is necessary to track if this widget has content to
        # display or not.
        self.is_empty = True


class ShellConnectPluginMixin(ShellConnectMixin):
    """
    Mixin to connect a plugin composed of stacked widgets to the shell widgets
    in the IPython console.

    It is assumed that self.get_widget() returns an instance of
    ShellConnectMainWidget.
    """

    # ---- Connection to the IPython console
    # -------------------------------------------------------------------------
    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self) -> None:
        """Connect to the IPython console."""
        ipythonconsole = self.get_plugin(Plugins.IPythonConsole)
        self.register_ipythonconsole(ipythonconsole)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self) -> None:
        """Disconnect from the IPython console."""
        ipythonconsole = self.get_plugin(Plugins.IPythonConsole)
        self.unregister_ipythonconsole(ipythonconsole)

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Update the current shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget.
        """
        self.get_widget().set_shellwidget(shellwidget)

    def add_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Add a new shellwidget to be registered.

        This function registers a new widget to display content that
        comes from shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget.
        """
        self.get_widget().add_shellwidget(shellwidget)

    def remove_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Remove a registered shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget.
        """
        self.get_widget().remove_shellwidget(shellwidget)

    def add_errored_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Add a new shellwidget whose kernel failed to start.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget.
        """
        self.get_widget().add_errored_shellwidget(shellwidget)

    def current_widget(self) -> QWidget:
        """
        Return the current widget displayed at the moment.

        Returns
        -------
        current_widget: QWidget
            The widget displayed in the current tab.
        """
        return self.get_widget().current_widget()

    def get_widget_for_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> QWidget:
        """
        Return the widget registered with the given shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget.

        Returns
        -------
        current_widget: QWidget
            The widget corresponding to the shellwidget, or None if not found.
        """
        return self.get_widget().get_widget_for_shellwidget(shellwidget)

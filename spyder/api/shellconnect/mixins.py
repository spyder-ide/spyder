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
    Mixin to connect any widget or object to an IPython Console shell widget.
    """

    # ---- Connection to the IPython console
    # -------------------------------------------------------------------------
    def register_ipythonconsole(
        self,
        ipythonconsole: spyder.plugins.ipythonconsole.plugin.IPythonConsole,
    ) -> None:
        """
        Connect this object to the relevant signals of the IPython Console.

        Parameters
        ----------
        ipythonconsole : spyder.plugins.ipythonconsole.plugin.IPythonConsole
            The IPython Console to connect this object to the signals of.

        Returns
        -------
        None
        """
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
        """
        Disconnect this object from the relevant signals of the IPython Console.

        Parameters
        ----------
        ipythonconsole : spyder.plugins.ipythonconsole.plugin.IPythonConsole
            The IPython Console to disconnect this object from the signals of.

        Returns
        -------
        None
        """
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
        """
        Set as active the stack widget associated to the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that corresponds to the stacked widget to set
            as currently active.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def add_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Create a new object associated with the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to associate the new widget to.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def remove_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Remove the object associated to a given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to remove the associated object of.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def add_errored_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Register an error widget if the shell widget's kernel failed to start.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to associate with a new error widget.

        Returns
        -------
        None
        """
        raise NotImplementedError


class ShellConnectWidgetForStackMixin:
    """
    Mixin for widgets added to a stack of those connected to different shells.

    Used for the stacked widgets of
    :class:`~spyder.api.shellconnect.main_widget.ShellConnectMainWidget`.
    """

    sig_show_empty_message_requested: Signal = Signal(bool)
    """
    Request that the empty message be shown/hidden.

    Parameters
    ----------
    show_empty_message: bool
        ``True`` to show the empty message; ``False`` for the normal widget.
    """

    def __init__(self) -> None:
        """
        Set up attributes on the mixin.

        Returns
        -------
        None
        """

        self.is_empty: bool = True
        """
        If the current widget has content to show.

        This attribute is necessary to track whether this widget has content
        to display.
        """


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
        """
        Connect this object to the relevant signals of the IPython Console.

        Returns
        -------
        None
        """
        ipythonconsole = self.get_plugin(Plugins.IPythonConsole)
        self.register_ipythonconsole(ipythonconsole)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self) -> None:
        """
        Disconnect this object from the relevant signals of the IPython Console.

        Returns
        -------
        None
        """
        ipythonconsole = self.get_plugin(Plugins.IPythonConsole)
        self.unregister_ipythonconsole(ipythonconsole)

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Set as active the stack widget associated to the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that corresponds to the stacked widget to set
            as currently active.

        Returns
        -------
        None
        """
        self.get_widget().set_shellwidget(shellwidget)

    def add_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Create a new widget in the stack associated to a given shell widget.

        This method registers a new widget to display the content that
        is associated with the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to associate the new widget to.

        Returns
        -------
        None
        """
        self.get_widget().add_shellwidget(shellwidget)

    def remove_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Remove the widget associated to a given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to remove the associated widget of.

        Returns
        -------
        None
        """
        self.get_widget().remove_shellwidget(shellwidget)

    def add_errored_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Add an error widget for a shell widget whose kernel failed to start.

        This is necessary to show a meaningful message when switching to
        consoles with dead kernels.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to associate with a new error widget.

        Returns
        -------
        None
        """
        self.get_widget().add_errored_shellwidget(shellwidget)

    def current_widget(self) -> QWidget:
        """
        Get the widget corresponding to the currently active console tab.

        Returns
        -------
        QWidget
            The current widget in the stack, associated with the active
            :class:`~spyder.plugins.ipythonconsole.widgets.ShellWidget`
            (i.e. :guilabel:`IPython Console` tab).
        """
        return self.get_widget().current_widget()

    def get_widget_for_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> QWidget:
        """
        Retrieve the stacked widget corresponding to the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to return the associated widget of.

        Returns
        -------
        QWidget | None
            The widget in the stack associated with ``shellwidget``,
            or ``None`` if not found.
        """
        return self.get_widget().get_widget_for_shellwidget(shellwidget)

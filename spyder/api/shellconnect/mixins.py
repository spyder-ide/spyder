# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Mixin to connect a plugin to the IPython console.
"""

from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.plugins import Plugins


class ShellConnectMixin:
    """
    Mixin to connect a plugin composed of stacked widgets to the shell
    widgets in the IPython console.

    It is assumed that self.get_widget() returns an instance of
    ShellConnectMainWidget
    """

    # ---- Connection to the IPython console
    # -------------------------------------------------------------------------
    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        """Connect to the IPython console."""
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        self.register_ipythonconsole(ipyconsole)

    def register_ipythonconsole(self, ipyconsole):
        """Register the console."""
        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.connect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.connect(self.remove_shellwidget)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self):
        """Disconnect from the IPython console."""
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        self.unregister_ipythonconsole(ipyconsole)

    def unregister_ipythonconsole(self, ipyconsole):
        """Unregister the console."""

        ipyconsole.sig_shellwidget_changed.disconnect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.disconnect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.disconnect(self.remove_shellwidget)

    # ---- Public API
    # -------------------------------------------------------------------------
    def set_shellwidget(self, shellwidget):
        """
        Update the current shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().set_shellwidget(shellwidget)

    def add_shellwidget(self, shellwidget):
        """
        Add a new shellwidget to be registered.

        This function registers a new widget to display content that
        comes from shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().add_shellwidget(shellwidget)

    def remove_shellwidget(self, shellwidget):
        """
        Remove the registered shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().remove_shellwidget(shellwidget)

    def current_widget(self):
        """
        Return the current widget displayed at the moment.

        Returns
        -------
        current_widget: QWidget
            The widget displayed in the current tab.
        """
        return self.get_widget().current_widget()

    def get_widget_for_shellwidget(self, shellwidget):
        """
        Return the widget registered with the given shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.

        Returns
        -------
        current_widget: QWidget
            The widget corresponding to the shellwidget, or None if not found.
        """
        return self.get_widget().get_widget_for_shellwidget(shellwidget)

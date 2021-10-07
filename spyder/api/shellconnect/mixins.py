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

        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.connect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.connect(self.remove_shellwidget)
        ipyconsole.sig_external_spyder_kernel_connected.connect(
            self.on_connection_to_external_spyder_kernel)

    @on_plugin_teardown(plugin=Plugins.IPythonConsole)
    def on_ipython_console_teardown(self):
        """Disconnect from the IPython console."""
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        ipyconsole.sig_shellwidget_changed.disconnect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.disconnect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.disconnect(self.remove_shellwidget)
        ipyconsole.sig_external_spyder_kernel_connected.disconnect(
            self.on_connection_to_external_spyder_kernel)

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

    def on_connection_to_external_spyder_kernel(self, shellwidget):
        """
        Actions to take when the IPython console connects to an
        external Spyder kernel.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget that was connected to the external Spyder
            kernel.
        """
        pass

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
classes to connect to a shellwidget.
"""


class ShellConnectMixin:
    """
    Manager to connect a stacked widget to a shell widget.

    It is assumed that self.get_widget() returns a child of
    ShellConnectMainWidget
    """

    def register_ipythonconsole(self, ipyconsole):
        """Connect to ipyconsole."""
        # Signals
        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.connect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.connect(self.remove_shellwidget)

    def unregister_ipythonconsole(self, ipyconsole):
        """Disconnect from ipyconsole."""
        # Signals
        ipyconsole.sig_shellwidget_changed.disconnect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.disconnect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.disconnect(self.remove_shellwidget)

    # ---- Public API
    # ------------------------------------------------------------------------
    def set_shellwidget(self, shellwidget):
        """
        Update the current shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().set_shellwidget(shellwidget)

    def add_shellwidget(self, shellwidget, external):
        """
        Add a new shellwidget to be registered.

        This function registers a new NamespaceBrowser for browsing variables
        in the shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        external: bool
            True if the kernel is external
        """
        self.get_widget().add_shellwidget(shellwidget)

    def remove_shellwidget(self, shellwidget, external):
        """
        Remove the shellwidget registered.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        external: bool
            True if the kernel is external
        """
        self.get_widget().remove_shellwidget(shellwidget)

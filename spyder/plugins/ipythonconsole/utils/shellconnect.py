# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
classes to connect to a shellwidget.
"""

# Third party imports
from qtpy.QtWidgets import (
    QStackedWidget, QVBoxLayout)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget

# Localization
_ = get_translation('spyder')


class ShellConnectManager():
    """
    Manager to connect a stacked widget to a shell widget.

    It is assumed that self.get_widget() returns a child of
    StackedShellConnectWidget
    """

    def register_ipyconsole(self, ipyconsole):
        """Connect to ipyconsole."""
        # Signals
        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.connect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.connect(
            self.remove_shellwidget)

    def unregister_ipyconsole(self, ipyconsole):
        """Disconnect from ipyconsole."""
        # Signals
        ipyconsole.sig_shellwidget_changed.disconnect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.disconnect(self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.disconnect(
            self.remove_shellwidget)

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


class StackedShellConnectWidget(PluginMainWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Widgets
        self._stack = QStackedWidget(self)
        self._shellwidgets = {}

        # Layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        self.setLayout(layout)

    def update_style(self):
        self._stack.setStyleSheet(
            "QStackedWidget {padding: 0px; border: 0px}")

    # ---- Stack accesors
    # ------------------------------------------------------------------------

    def count(self):
        """
        Return the number of widgets in the stack.

        Returns
        -------
        int
            The number of widgets in the stack.
        """
        return self._stack.count()

    def current_widget(self):
        """
        Return the current figure browser widget in the stack.

        Returns
        -------
        spyder.plugins.plots.widgets.figurebrowser.FigureBrowser
            The current widget.
        """
        return self._stack.currentWidget()

    def get_focus_widget(self):
        return self.current_widget()

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """
        Register shell.

        This function creates a new Widget.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self._shellwidgets:
            nsb = self.new_widget(shellwidget)
            self._stack.addWidget(nsb)
            self._shellwidgets[shellwidget_id] = nsb
            self.set_shellwidget(shellwidget)
            self.update_actions()

    def remove_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets.pop(shellwidget_id)
            self._stack.removeWidget(nsb)
            self.close_widget(nsb)

    def set_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        old_nsb = self.current_widget()
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets[shellwidget_id]
            self.switch_widget(nsb, old_nsb)
            self._stack.setCurrentWidget(nsb)

    def new_widget(self, shellwidget):
        raise NotImplementedError

    def close_widget(self, nsb):
        raise NotImplementedError

    def switch_widget(self, nsb, old_nsb):
        raise NotImplementedError

    def refresh(self):
        if self.count():
            nsb = self.current_widget()
            nsb.refresh()

    def update_actions(self):
        nsb = self.current_widget()

        for __, action in self.get_actions().items():
            if action:
                # IMPORTANT: Since we are defining the main actions in here
                # and the context is WidgetWithChildrenShortcut we need to
                # assign the same actions to the children widgets in order
                # for shortcuts to work
                if nsb:
                    nsb_actions = nsb.actions()
                    if action not in nsb_actions:
                        nsb.addAction(action)

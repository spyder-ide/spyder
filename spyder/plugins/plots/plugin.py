# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Plots Plugin.
"""

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.translations import get_translation
from spyder.plugins.plots.widgets.main_widget import PlotsWidget


# Localization
_ = get_translation('spyder')


class Plots(SpyderDockablePlugin):
    """
    Plots plugin.
    """
    NAME = 'plots'
    REQUIRES = [Plugins.IPythonConsole]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = PlotsWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Plots')

    def get_description(self):
        return _('Display, explore and save console generated plots.')

    def get_icon(self):
        return self.create_icon('hist')

    def on_initialize(self):
        # If a figure is loaded, raise the dockwidget the first time
        # a plot is generated.
        self.get_widget().sig_figure_loaded.connect(self._on_first_plot)

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Signals
        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_created.connect(
            self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.connect(
            self.remove_shellwidget)

    def unregister(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Signals
        ipyconsole.sig_shellwidget_created.disconnect(
            self.add_shellwidget)
        ipyconsole.sig_shellwidget_deleted.connect(
            self.remove_shellwidget)

    # ---- Public API
    # ------------------------------------------------------------------------
    def current_widget(self):
        """
        Return the current widget displayed at the moment.

        Returns
        -------
        spyder.plugins.plots.widgets.figurebrowser.FigureBrowser
            The current figure browser widget.
        """
        return self.get_widget().current_widget()

    def add_shellwidget(self, shellwidget):
        """
        Add a new shellwidget to be registered with the Plots plugin.

        This function registers a new FigureBrowser for browsing the figures
        in the shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().add_shellwidget(shellwidget)

    def remove_shellwidget(self, shellwidget):
        """
        Remove the shellwidget registered with the plots plugin.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().remove_shellwidget(shellwidget)

    def set_shellwidget(self, shellwidget):
        """
        Update the current shellwidget displayed with the plots plugin.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().set_shellwidget(shellwidget)

    # ---- Private API
    # ------------------------------------------------------------------------
    def _on_first_plot(self):
        """Actions to execute after the first plot is generated."""
        # Only switch when inline plotting is muted. This avoids
        # showing the plugin when users want to only see plots in
        # the IPython console.
        # Fixes spyder-ide/spyder#15467
        if self.get_conf('mute_inline_plotting'):
            self.switch_to_plugin(force_focus=False)

        # We only give raise to the plugin once per session, to let users
        # know that plots are displayed in this plugin.
        # Fixes spyder-ide/spyder#15705
        self.get_widget().sig_figure_loaded.disconnect(self._on_first_plot)

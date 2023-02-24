# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Plots Plugin.
"""

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.translations import _
from spyder.plugins.plots.widgets.main_widget import PlotsWidget


class Plots(SpyderDockablePlugin, ShellConnectMixin):
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
    @staticmethod
    def get_name():
        return _('Plots')

    def get_description(self):
        return _('Display, explore and save console generated plots.')

    def get_icon(self):
        return self.create_icon('hist')

    def on_initialize(self):
        # If a figure is loaded, raise the dockwidget the first time
        # a plot is generated.
        self.get_widget().sig_figure_loaded.connect(self._on_first_plot)

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

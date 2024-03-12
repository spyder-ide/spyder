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
from spyder.api.shellconnect.mixins import ShellConnectPluginMixin
from spyder.api.translations import _
from spyder.plugins.plots.widgets.main_widget import PlotsWidget


class Plots(SpyderDockablePlugin, ShellConnectPluginMixin):
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

    @staticmethod
    def get_description():
        return _('View, browse and save generated figures.')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('plot')

    def on_initialize(self):
        # If a figure is loaded, raise the dockwidget the first time
        # a plot is generated.
        self.get_widget().sig_figure_loaded.connect(self._on_first_plot)

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_plot(self, fig, fmt, shellwidget):
        """
        Add a plot to the specified figure browser.

        Add the plot to the figure browser with the given shellwidget. Also,
        bring the plugin to the front and raise the window that it is in so
        that the plot is shown.

        If no figure browser with the given shellwidget exists, then nothing
        happens.
        """
        self.switch_to_plugin(force_focus=False)
        self.get_widget().window().raise_()
        self.get_widget().add_plot(fig, fmt, shellwidget)

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

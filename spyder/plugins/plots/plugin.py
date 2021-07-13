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
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.translations import get_translation
from spyder.plugins.plots.widgets.main_widget import PlotsWidget

# Localization
_ = get_translation('spyder')


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

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Plots')

    def get_description(self):
        return _('Display, explore and save console generated plots.')

    def get_icon(self):
        return self.create_icon('hist')

    def on_initialize(self):
        # If a figure is loaded raise the dockwidget but do not give focus
        self.get_widget().sig_figure_loaded.connect(
            lambda: self.switch_to_plugin(force_focus=False))

    @on_plugin_available(plugin=Plugins.IPythonConsole)
    def on_ipython_console_available(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Register IPython console.
        self.register_ipythonconsole(ipyconsole)

    def unregister(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Unregister IPython console.
        self.unregister_ipythonconsole(ipyconsole)

    def switch_to_plugin(self, force_focus=False):
        # Only switch when inline plotting is muted. This avoids
        # showing the plugin when users want to only see plots in
        # the IPython console.
        # Fixes spyder-ide/spyder#15467
        if self.get_conf('mute_inline_plotting'):
            super().switch_to_plugin(force_focus=force_focus)

    # --- Public API
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

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Plots Plugin"""


# Third party imports
from qtpy.QtWidgets import QStackedWidget, QGridLayout

# Local imports
from spyder.config.base import _
from spyder.config.gui import is_dark_interface
from spyder.api.plugins import SpyderPluginWidget
from spyder.utils import icon_manager as ima
from spyder.plugins.plots.widgets.figurebrowser import FigureBrowser


if is_dark_interface():
    MAIN_BG_COLOR = '#19232D'
else:
    MAIN_BG_COLOR = 'white'


class Plots(SpyderPluginWidget):
    """Plots plugin."""

    CONF_SECTION = 'plots'
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        # Widgets
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("QStackedWidget{padding: 0px; border: 0px}")
        self.shellwidgets = {}

        # Layout
        layout = QGridLayout(self)
        layout.addWidget(self.stack)

    def get_settings(self):
        """Retrieve all Plots configuration settings."""
        return {name: self.get_option(name) for name in
                ['mute_inline_plotting', 'show_plot_outline',
                 'auto_fit_plotting']}

    # ---- Stack accesors
    def set_current_widget(self, fig_browser):
        """
        Set the currently visible fig_browser in the stack widget, refresh the
        actions of the cog menu button and move it to the layout of the new
        fig_browser.
        """
        self.stack.setCurrentWidget(fig_browser)
        # We update the actions of the options button (cog menu) and
        # we move it to the layout of the current widget.
        self._refresh_actions()
        fig_browser.setup_options_button()

    def current_widget(self):
        return self.stack.currentWidget()

    def count(self):
        return self.stack.count()

    def remove_widget(self, fig_browser):
        self.stack.removeWidget(fig_browser)

    def add_widget(self, fig_browser):
        self.stack.addWidget(fig_browser)

    # ---- Public API
    def add_shellwidget(self, shellwidget):
        """
        Register shell with figure explorer.

        This function opens a new FigureBrowser for browsing the figures
        in the shell.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self.shellwidgets:
            self.options_button.setVisible(True)
            fig_browser = FigureBrowser(
                self, options_button=self.options_button,
                background_color=MAIN_BG_COLOR)
            fig_browser.set_shellwidget(shellwidget)
            fig_browser.setup(**self.get_settings())
            fig_browser.sig_option_changed.connect(
                self.sig_option_changed.emit)
            fig_browser.thumbnails_sb.redirect_stdio.connect(
                self.main.redirect_internalshell_stdio)
            self.register_widget_shortcuts(fig_browser)
            self.add_widget(fig_browser)
            self.shellwidgets[shellwidget_id] = fig_browser
            self.set_shellwidget_from_id(shellwidget_id)
            return fig_browser

    def remove_shellwidget(self, shellwidget_id):
        # If shellwidget_id is not in self.shellwidgets, it simply means
        # that shell was not a Python-based console (it was a terminal)
        if shellwidget_id in self.shellwidgets:
            fig_browser = self.shellwidgets.pop(shellwidget_id)
            self.remove_widget(fig_browser)
            fig_browser.close()

    def set_shellwidget_from_id(self, shellwidget_id):
        if shellwidget_id in self.shellwidgets:
            fig_browser = self.shellwidgets[shellwidget_id]
            self.set_current_widget(fig_browser)

    # ---- SpyderPluginWidget API
    def get_plugin_title(self):
        """Return widget title"""
        return _('Plots')

    def get_plugin_icon(self):
        """Return plugin icon"""
        return ima.icon('hist')

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.current_widget()

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return self.current_widget().actions if self.current_widget() else []

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        for fig_browser in list(self.shellwidgets.values()):
            fig_browser.setup(**self.get_settings())

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.variableexplorer)

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Figure Explorer Plugin"""


# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QGroupBox, QStackedWidget, QGridLayout

# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.preferences import PluginConfigPage
from spyder.utils import icon_manager as ima
from spyder.widgets.figurebrowser import FigureBrowser


class FigureExplorerConfigPage(PluginConfigPage):

    def setup_page(self):
        pass


class FigureExplorer(SpyderPluginWidget):
    """Figure Explorer plugin."""

    CONF_SECTION = 'figure_explorer'
    CONFIGWIDGET_CLASS = FigureExplorerConfigPage
    sig_option_changed = Signal(str, object)

    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        # Widgets
        self.stack = QStackedWidget(self)
        self.shellwidgets = {}

        # Layout
        layout = QGridLayout(self)
        layout.addWidget(self.stack)

        # Initialize plugin
        self.initialize_plugin()

    # ---- Stack accesors

    def set_current_widget(self, fig_browser):
        self.stack.setCurrentWidget(fig_browser)
        self.refresh_actions()
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
            fig_browser = FigureBrowser(self,
                                        options_button=self.options_button,
                                        plugin_actions=[self.undock_action])
            fig_browser.set_shellwidget(shellwidget)
            fig_browser.setup()
            fig_browser.thumnails_sb.redirect_stdio.connect(
                self.main.redirect_internalshell_stdio)
            # fig_browser.setup(**self.get_settings())
            # fig_browser.sig_option_changed.connect(self.change_option)
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
        return _('Figure explorer')

    def get_plugin_icon(self):
        """Return plugin icon"""
        return ima.icon('hist')

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.current_widget()

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def refresh_plugin(self):
        """Refresh widget"""
        pass

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        if not self.current_widget():
            return []
        else:
            return self.current_widget().actions

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        for fig_browser in list(self.shellwidgets.values()):
            pass
            # fig_browser.setup(**self.get_settings())

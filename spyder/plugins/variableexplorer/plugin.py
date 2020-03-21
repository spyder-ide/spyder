# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Variable Explorer Plugin.
"""

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.plugins.variableexplorer.confpage import VariableExplorerConfigPage
from spyder.plugins.variableexplorer.widgets.main import VariableExplorerWidget


# Localization
_ = get_translation('spyder')


class VariableExplorer(SpyderDockablePlugin):
    """
    Variable explorer plugin.
    """
    NAME = 'variable_explorer'
    WIDGET_CLASS = VariableExplorerWidget
    REQUIRES = [Plugins.IPythonConsole]
    TABIFY = None
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = VariableExplorerConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False
    CONF_FROM_OPTIONS = {
        'show_reset_namespace_warning':
            ('ipython_console', 'show_reset_namespace_warning'),
        'blank_spaces': ('editor', 'blank_spaces'),
        'scroll_past_end': ('editor', 'scroll_past_end'),
        'color_theme': ('appearance', 'selected'),
    }

    def get_name(self):
        return _('Variable explorer')

    def get_description(self):
        return _('Display, explore load and save variables in the current '
                 'namespace.')

    def get_icon(self):
        return self.create_icon('dictedit')

    def register(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Signals
        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_process_started.connect(
            self.add_shellwidget)
        ipyconsole.sig_shellwidget_process_finished.connect(
            self.remove_shellwidget)

        widget = self.get_widget()
        widget.sig_free_memory_requested.connect(
            self.sig_free_memory_requested)

    def unregister(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)

        # Signals
        if ipyconsole:
            widget = self.get_widget()
            if widget:
                ipyconsole.sig_shellwidget_changed.disconnect(
                    widget.set_shellwidget)
                ipyconsole.sig_shellwidget_process_started.disconnect(
                    widget.add_shellwidget)
                ipyconsole.sig_shellwidget_process_finished.disconnect(
                    widget.remove_shellwidget)

    # --- Exposed API from the PluginMainWidget
    # ------------------------------------------------------------------------
    def current_widget(self):
        return self.get_widget().current_widget()

    def set_shellwidget(self, shelwidget):
        self.get_widget().set_shellwidget(shelwidget)

    def add_shellwidget(self, shelwidget):
        self.get_widget().add_shellwidget(shelwidget)

    def remove_shellwidget(self, shelwidget):
        self.get_widget().remove_shellwidget(shelwidget)

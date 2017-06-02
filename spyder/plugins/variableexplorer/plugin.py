# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Variable Explorer Plugin"""

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QStackedWidget, QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.utils import icon_manager as ima
from spyder.plugins.variableexplorer.widgets.namespacebrowser import NamespaceBrowser
from spyder.plugins.variableexplorer.widgets.utils import REMOTE_SETTINGS
from spyder.plugins.variableexplorer.confpage import VariableExplorerConfigPage


class VariableExplorer(SpyderPluginWidget):
    """Variable Explorer plugin."""

    CONF_SECTION = 'variable_explorer'
    CONFIGWIDGET_CLASS = VariableExplorerConfigPage
    sig_option_changed = Signal(str, object)

    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        # Widgets
        self.stack = QStackedWidget(self)
        self.shellwidgets = {}

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

        # Initialize plugin
        self.initialize_plugin()

    def get_settings(self):
        """
        Retrieve all Variable Explorer configuration settings.
        
        Specifically, return the settings in CONF_SECTION with keys in 
        REMOTE_SETTINGS, and the setting 'dataframe_format'.
        
        Returns:
            dict: settings
        """
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = self.get_option(name)

        # dataframe_format is stored without percent sign in config
        # to avoid interference with ConfigParser's interpolation
        name = 'dataframe_format'
        settings[name] = '%{0}'.format(self.get_option(name))
        return settings

    @Slot(str, object)
    def change_option(self, option_name, new_value):
        """
        Change a config option.

        This function is called if sig_option_changed is received. If the
        option changed is the dataframe format, then the leading '%' character
        is stripped (because it can't be stored in the user config). Then,
        the signal is emitted again, so that the new value is saved in the
        user config.
        """
        if option_name == 'dataframe_format':
            assert new_value.startswith('%')
            new_value = new_value[1:]
        self.sig_option_changed.emit(option_name, new_value)

    # ----- Stack accesors ----------------------------------------------------
    def set_current_widget(self, nsb):
        self.stack.setCurrentWidget(nsb)

    def current_widget(self):
        return self.stack.currentWidget()

    def count(self):
        return self.stack.count()

    def remove_widget(self, nsb):
        self.stack.removeWidget(nsb)

    def add_widget(self, nsb):
        self.stack.addWidget(nsb)

    # ----- Public API --------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """
        Register shell with variable explorer.

        This function opens a new NamespaceBrowser for browsing the variables
        in the shell.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self.shellwidgets:
            nsb = NamespaceBrowser(self)
            nsb.set_shellwidget(shellwidget)
            nsb.setup(**self.get_settings())
            nsb.sig_option_changed.connect(self.change_option)
            self.add_widget(nsb)
            self.shellwidgets[shellwidget_id] = nsb
            self.set_shellwidget_from_id(shellwidget_id)
            return nsb
        
    def remove_shellwidget(self, shellwidget_id):
        # If shellwidget_id is not in self.shellwidgets, it simply means
        # that shell was not a Python-based console (it was a terminal)
        if shellwidget_id in self.shellwidgets:
            nsb = self.shellwidgets.pop(shellwidget_id)
            self.remove_widget(nsb)
            nsb.close()
    
    def set_shellwidget_from_id(self, shellwidget_id):
        if shellwidget_id in self.shellwidgets:
            nsb = self.shellwidgets[shellwidget_id]
            self.set_current_widget(nsb)

    def import_data(self, fname):
        """Import data in current namespace"""
        if self.count():
            nsb = self.current_widget()
            nsb.refresh_table()
            nsb.import_data(filenames=fname)
            if self.dockwidget and not self.ismaximized:
                self.dockwidget.setVisible(True)
                self.dockwidget.raise_()

    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('Variable explorer')

    def get_plugin_icon(self):
        """Return plugin icon"""
        return ima.icon('dictedit')
    
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
        return []
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)
        
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        for nsb in list(self.shellwidgets.values()):
            nsb.setup(**self.get_settings())

# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Namespace Browser Plugin"""

import sys

from PyQt4.QtGui import QStackedWidget, QGroupBox, QVBoxLayout
from PyQt4.QtCore import SIGNAL

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.config import CONF, get_icon
from spyderlib.utils import programs
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage
from spyderlib.widgets.externalshell.monitor import REMOTE_SETTINGS
from spyderlib.widgets.externalshell.namespacebrowser import NamespaceBrowser


class VariableExplorerConfigPage(PluginConfigPage):
    def setup_page(self):
        ar_group = QGroupBox(self.tr("Autorefresh"))
        ar_box = self.create_checkbox(self.tr("Enable autorefresh"),
                                      'autorefresh/enable')
        ar_spin = self.create_spinbox(self.tr("Refresh interval: "),
                                      self.tr(" ms"), 'autorefresh/timeout',
                                      min_=100, max_=1000000, step=100)
        
        filter_group = QGroupBox(self.tr("Filter"))
        filter_data = [
            ('exclude_private', self.tr("Exclude private references")),
            ('exclude_upper', self.tr("Exclude capitalized references")),
            ('exclude_unsupported', self.tr("Exclude unsupported data types")),
                ]
        filter_boxes = [self.create_checkbox(text, option)
                        for option, text in filter_data]

        display_group = QGroupBox(self.tr("Display"))
        display_data = [
            ('truncate', self.tr("Truncate values")),
            ('collvalue', self.tr("Show collection contents")),
            ('inplace', self.tr("Always edit in-place")),
                ]
        if programs.is_module_installed('numpy'):
            display_data.append( ('minmax', self.tr("Show arrays min/max")) )
        display_boxes = [self.create_checkbox(text, option)
                         for option, text in display_data]
        
        ar_layout = QVBoxLayout()
        ar_layout.addWidget(ar_box)
        ar_layout.addWidget(ar_spin)
        ar_group.setLayout(ar_layout)
        
        filter_layout = QVBoxLayout()
        for box in filter_boxes:
            filter_layout.addWidget(box)
        filter_group.setLayout(filter_layout)

        display_layout = QVBoxLayout()
        for box in display_boxes:
            display_layout.addWidget(box)
        display_group.setLayout(display_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(ar_group)
        vlayout.addWidget(filter_group)
        vlayout.addWidget(display_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class VariableExplorer(QStackedWidget, SpyderPluginMixin):
    """
    Variable Explorer Plugin
    """
    CONF_SECTION = 'variable_explorer'
    CONFIGWIDGET_CLASS = VariableExplorerConfigPage
    def __init__(self, parent):
        QStackedWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
        self.shellwidgets = {}

    @staticmethod
    def get_settings():
        """
        Return Variable Explorer settings dictionary
        (i.e. namespace browser settings according to Spyder's configuration file)
        """
        settings = {}
        for name in REMOTE_SETTINGS:
            settings[name] = CONF.get(VariableExplorer.CONF_SECTION, name)
        settings['autorefresh'] = CONF.get(VariableExplorer.CONF_SECTION,
                                           'autorefresh/enable')
        return settings
        
    #------ Public API ---------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        # Add shell only once: this method may be called two times in a row 
        # by the External console plugin (dev. convenience)
        from spyderlib.widgets.externalshell import systemshell
        if isinstance(shellwidget, systemshell.ExternalSystemShell):
            return
        if shellwidget_id not in self.shellwidgets:
            nsb = NamespaceBrowser(self)
            nsb.setup(**VariableExplorer.get_settings())
            nsb.set_shellwidget(shellwidget)
            self.connect(nsb, SIGNAL('option_changed'),
                         lambda option, value:
                         self.emit(SIGNAL('option_changed'), option, value))
            self.addWidget(nsb)
            self.shellwidgets[shellwidget_id] = nsb
            shellwidget.set_namespacebrowser(nsb)
        
    def remove_shellwidget(self, shellwidget_id):
        # If shellwidget_id is not in self.shellwidgets, it simply means
        # that shell was not a Python/IPython-based console (it was a terminal)
        if shellwidget_id in self.shellwidgets:
            nsb = self.shellwidgets.pop(shellwidget_id)
            self.removeWidget(nsb)
            nsb.close()
    
    def set_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self.shellwidgets:
            self.setCurrentWidget(self.shellwidgets[shellwidget_id])
            
    def import_data(self, fname):
        """Import data in current namespace"""
        if self.count():
            nsb = self.currentWidget()
            nsb.refresh_table()
            nsb.import_data(fname)
            if self.dockwidget and not self.ismaximized:
                self.dockwidget.setVisible(True)
                self.dockwidget.raise_()

    #------ SpyderPluginMixin API ---------------------------------------------
    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        SpyderPluginMixin.visibility_changed(self, enable)
        for nsb in self.shellwidgets.values():
            nsb.visibility_changed(enable and nsb is self.currentWidget())
    
    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('Variable explorer')

    def get_plugin_icon(self):
        """Return plugin icon"""
        return get_icon('dictedit.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.currentWidget()
        
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
        self.main.extconsole.set_variableexplorer(self)
        self.main.add_dockwidget(self)
        if self.main.explorer is not None:
            self.connect(self.main.explorer, SIGNAL("import_data(QString)"),
                         self.import_data)
        if self.main.projectexplorer is not None:
            self.connect(self.main.projectexplorer,
                         SIGNAL("import_data(QString)"), self.import_data)
        
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        for nsb in self.shellwidgets.values():
            nsb.setup(**VariableExplorer.get_settings())
        ar_timeout = self.get_option('autorefresh/timeout')
        for shellwidget in self.main.extconsole.shellwidgets:
            shellwidget.set_autorefresh_timeout(ar_timeout)

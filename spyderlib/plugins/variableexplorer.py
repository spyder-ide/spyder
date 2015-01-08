# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Namespace Browser Plugin"""

from spyderlib.qt.QtGui import QStackedWidget, QGroupBox, QVBoxLayout
from spyderlib.qt.QtCore import Signal

# Local imports
from spyderlib.baseconfig import _
from spyderlib.config import CONF
from spyderlib.utils.qthelpers import get_icon
from spyderlib.utils import programs
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage
from spyderlib.widgets.externalshell.monitor import REMOTE_SETTINGS
from spyderlib.widgets.externalshell.namespacebrowser import NamespaceBrowser


class VariableExplorerConfigPage(PluginConfigPage):
    def setup_page(self):
        ar_group = QGroupBox(_("Autorefresh"))
        ar_box = self.create_checkbox(_("Enable autorefresh"),
                                      'autorefresh')
        ar_spin = self.create_spinbox(_("Refresh interval: "),
                                      _(" ms"), 'autorefresh/timeout',
                                      min_=100, max_=1000000, step=100)
        
        filter_group = QGroupBox(_("Filter"))
        filter_data = [
            ('exclude_private', _("Exclude private references")),
            ('exclude_capitalized', _("Exclude capitalized references")),
            ('exclude_uppercase', _("Exclude all-uppercase references")),
            ('exclude_unsupported', _("Exclude unsupported data types")),
                ]
        filter_boxes = [self.create_checkbox(text, option)
                        for option, text in filter_data]

        display_group = QGroupBox(_("Display"))
        display_data = [('truncate', _("Truncate values"), '')]
        if programs.is_module_installed('numpy'):
            display_data.append(('minmax', _("Show arrays min/max"), ''))
        display_data.append(
            ('remote_editing', _("Edit data in the remote process"),
             _("Editors are opened in the remote process for NumPy "
               "arrays, PIL images, lists, tuples and dictionaries.\n"
               "This avoids transfering large amount of data between "
               "the remote process and Spyder (through the socket)."))
                            )
        display_boxes = [self.create_checkbox(text, option, tip=tip)
                         for option, text, tip in display_data]
        
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
    sig_option_changed = Signal(str, object)
    def __init__(self, parent):
        QStackedWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)
        self.shellwidgets = {}

        # Initialize plugin
        self.initialize_plugin()

    @staticmethod
    def get_settings():
        """
        Return Variable Explorer settings dictionary
        (i.e. namespace browser settings according to Spyder's configuration file)
        """
        settings = {}
#        CONF.load_from_ini() # necessary only when called from another process
        for name in REMOTE_SETTINGS:
            settings[name] = CONF.get(VariableExplorer.CONF_SECTION, name)
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
            nsb.set_shellwidget(shellwidget)
            nsb.setup(**VariableExplorer.get_settings())
            nsb.sig_option_changed.connect(self.sig_option_changed.emit)
            self.addWidget(nsb)
            self.shellwidgets[shellwidget_id] = nsb
            self.set_shellwidget_from_id(shellwidget_id)
            return nsb
        
    def remove_shellwidget(self, shellwidget_id):
        # If shellwidget_id is not in self.shellwidgets, it simply means
        # that shell was not a Python-based console (it was a terminal)
        if shellwidget_id in self.shellwidgets:
            nsb = self.shellwidgets.pop(shellwidget_id)
            self.removeWidget(nsb)
            nsb.close()
    
    def set_shellwidget_from_id(self, shellwidget_id):
        if shellwidget_id in self.shellwidgets:
            nsb = self.shellwidgets[shellwidget_id]
            self.setCurrentWidget(nsb)
            if self.isvisible:
                nsb.visibility_changed(True)
            
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
        for nsb in list(self.shellwidgets.values()):
            nsb.visibility_changed(enable and nsb is self.currentWidget())
    
    #------ SpyderPluginWidget API ---------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('Variable explorer')

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
        
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        for nsb in list(self.shellwidgets.values()):
            nsb.setup(**VariableExplorer.get_settings())
        ar_timeout = self.get_option('autorefresh/timeout')
        for shellwidget in self.main.extconsole.shellwidgets:
            shellwidget.set_autorefresh_timeout(ar_timeout)
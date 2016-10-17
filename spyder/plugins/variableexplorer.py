# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Variable Explorer Plugin"""

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QGroupBox, QStackedWidget, QVBoxLayout, QWidget

# Local imports
from spyder.config.base import _
from spyder.config.main import CONF
from spyder.plugins import SpyderPluginMixin
from spyder.plugins.configdialog import PluginConfigPage
from spyder.utils import programs
from spyder.utils import icon_manager as ima
from spyder.widgets.variableexplorer.namespacebrowser import NamespaceBrowser
from spyder.widgets.variableexplorer.utils import REMOTE_SETTINGS


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
        display_data = []
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


class VariableExplorer(QWidget, SpyderPluginMixin):
    """
    Variable Explorer Plugin
    """
    CONF_SECTION = 'variable_explorer'
    CONFIGWIDGET_CLASS = VariableExplorerConfigPage
    sig_option_changed = Signal(str, object)

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        SpyderPluginMixin.__init__(self, parent)

        # Widgets
        self.stack = QStackedWidget(self)
        self.shellwidgets = {}

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

        # Initialize plugin
        self.initialize_plugin()

    @staticmethod
    def get_settings():
        """
        Retrieve all Variable Explorer configuration settings
        
        Specifically, return the settings in CONF_SECTION with keys in 
        REMOTE_SETTINGS, and the setting 'dataframe_format'.
        
        Returns:
            dict: settings
        """
        settings = {}
#        CONF.load_from_ini() # necessary only when called from another process
        for name in REMOTE_SETTINGS:
            settings[name] = CONF.get(VariableExplorer.CONF_SECTION, name)

        # dataframe_format is stored without percent sign in config
        # to avoid interference with ConfigParser's interpolation
        name = 'dataframe_format'
        settings[name] = '%' + CONF.get(VariableExplorer.CONF_SECTION, name)
        return settings

    @Slot(str, object)
    def change_option(self, option_name, new_value):
        """
        Change a config option

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
        # Add shell only once: this method may be called two times in a row
        # by the External console plugin (dev. convenience)
        from spyder.widgets.externalshell import systemshell
        if isinstance(shellwidget, systemshell.ExternalSystemShell):
            return
        if shellwidget_id not in self.shellwidgets:
            nsb = NamespaceBrowser(self)
            nsb.set_shellwidget(shellwidget)
            nsb.setup(**VariableExplorer.get_settings())
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
            if self.isvisible:
                nsb.visibility_changed(True)

    def import_data(self, fname):
        """Import data in current namespace"""
        if self.count():
            nsb = self.current_widget()
            nsb.refresh_table()
            nsb.import_data(filenames=fname)
            if self.dockwidget and not self.ismaximized:
                self.dockwidget.setVisible(True)
                self.dockwidget.raise_()

    #------ SpyderPluginMixin API ---------------------------------------------
    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        SpyderPluginMixin.visibility_changed(self, enable)
        for nsb in list(self.shellwidgets.values()):
            nsb.visibility_changed(enable and nsb is self.current_widget())
    
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
        self.main.extconsole.set_variableexplorer(self)
        self.main.add_dockwidget(self)
        
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        for nsb in list(self.shellwidgets.values()):
            nsb.setup(**VariableExplorer.get_settings())
        ar_timeout = self.get_option('autorefresh/timeout')
        for shellwidget in self.main.extconsole.shellwidgets:
            shellwidget.set_autorefresh_timeout(ar_timeout)

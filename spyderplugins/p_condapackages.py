# -*- coding:utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Conda Package Manager Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import QVBoxLayout, QGroupBox
from spyderlib.qt.QtCore import SIGNAL

# Local imports
from spyderlib.baseconfig import get_translation
_ = get_translation("p_condapackages", dirname="spyderplugins")
from spyderlib.utils.qthelpers import get_icon
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage

from spyderplugins.widgets.condapackagesgui import (CondaPackagesWidget, 
                                                    CONDA_PATH)


class CondaPackagesConfigPage(PluginConfigPage):
    """ """
    def setup_page(self):
        settings_group = QGroupBox(_("Settings"))
        confirm_box = self.create_checkbox(_("Confirm before taking action"),
                                        'confirm_action', default=True)

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(confirm_box)
        settings_group.setLayout(settings_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(settings_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class CondaPackages(CondaPackagesWidget, SpyderPluginMixin):
    """Conda package manager based on conda and conda-api """
    CONF_SECTION = 'condapackages'
    CONFIGWIDGET_CLASS = CondaPackagesConfigPage

    def __init__(self, parent=None):
        CondaPackagesWidget.__init__(self, parent=parent)
        SpyderPluginMixin.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()

    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Conda package manager")

    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('condapackages.png')

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.search_box

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.inspector, self)
        self.dockwidget.hide()

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
#        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
#                     self.main.editor.load)
#        self.connect(self, SIGNAL('redirect_stdio(bool)'),
#                     self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)
        
    def refresh_plugin(self):
        """Refresh pylint widget"""
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
            
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        pass
        
    #------ Public API --------------------------------------------------------


#==============================================================================
# The following statements are required to register this 3rd party plugin:
#==============================================================================
if CONDA_PATH:
    PLUGIN_CLASS = CondaPackages

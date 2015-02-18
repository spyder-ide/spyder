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

from spyderlib.qt.QtCore import Qt
from spyderlib.qt.QtGui import QVBoxLayout, QGroupBox, QGridLayout

# Local imports
from spyderlib.baseconfig import get_translation, DEV
_ = get_translation("p_condapackages", dirname="spyderplugins")
from spyderlib.utils.qthelpers import get_icon
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage

from spyderplugins.widgets.condapackagesgui import (CondaPackagesWidget,
                                                    CONDA_PATH)


class CondaPackagesConfigPage(PluginConfigPage):
    """ """
    def setup_page(self):
        network_group = QGroupBox(_("Network settings"))
        self.checkbox_proxy = self.create_checkbox(_("Use network proxy"),
                                                   'use_proxy_flag',
                                                   default=False)
        server = self.create_lineedit(_('Server'), 'server', default='',
                                      alignment=Qt.Horizontal)
        port = self.create_lineedit(_('Port'), 'port', default='',
                                    alignment=Qt.Horizontal)
        user = self.create_lineedit(_('User'), 'user', default='',
                                    alignment=Qt.Horizontal)
        password = self.create_lineedit(_('Password'), 'password', default='',
                                        alignment=Qt.Horizontal)

        self.widgets = [server, port, user, password]

        network_layout = QGridLayout()
        network_layout.addWidget(self.checkbox_proxy, 0, 0)
        network_layout.addWidget(server, 1, 0)
        network_layout.addWidget(port, 1, 1)
        network_layout.addWidget(user, 2, 0)
        network_layout.addWidget(password, 2, 1)
        network_group.setLayout(network_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(network_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)

        # signals
        self.checkbox_proxy.clicked.connect(self.proxy_settings)
        self.proxy_settings()

    def proxy_settings(self):
        """ """
        state = self.checkbox_proxy.checkState()
        disabled = True

        if state == 2:
            disabled = False
        elif state == 0:
            disabled = True

        for widget in self.widgets:
            widget.setDisabled(disabled)


class CondaPackages(CondaPackagesWidget, SpyderPluginMixin):
    """Conda package manager based on conda and conda-api """
    CONF_SECTION = 'condapackages'
    CONFIGWIDGET_CLASS = CondaPackagesConfigPage

    def __init__(self, parent=None):
        CondaPackagesWidget.__init__(self, parent=parent)
        SpyderPluginMixin.__init__(self, parent)

        # Initialize plugin
        self.initialize_plugin()

    # ------ SpyderPluginWidget API -------------------------------------------
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
        return self.textbox_search

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.inspector, self)
        self.dockwidget.hide()

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.add_dockwidget(self)

    def refresh_plugin(self):
        """Refresh pylint widget"""
        pass

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        pass

    # ------ Public API -------------------------------------------------------


# =============================================================================
# The following statements are required to register this 3rd party plugin:
# =============================================================================
# Only register plugin if conda is found on the system
if CONDA_PATH and DEV:
    PLUGIN_CLASS = CondaPackages

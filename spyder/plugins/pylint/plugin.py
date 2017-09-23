# -*- coding:utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pylint Code Analysis Plugin."""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QGroupBox, QInputDialog, QLabel, QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.preferences import PluginConfigPage
from spyder.utils import icon_manager as ima
from spyder.utils.programs import is_module_installed
from spyder.utils.qthelpers import create_action, MENU_SEPARATOR
from .widgets.pylintgui import PylintWidget


class PylintConfigPage(PluginConfigPage):
    def setup_page(self):
        settings_group = QGroupBox(_("Settings"))
        save_box = self.create_checkbox(_("Save file before analyzing it"),
                                        'save_before', default=True)
        
        hist_group = QGroupBox(_("History"))
        hist_label1 = QLabel(_("The following option will be applied at next "
                               "startup."))
        hist_label1.setWordWrap(True)
        hist_spin = self.create_spinbox(_("History: "),
                            _(" results"), 'max_entries', default=50,
                            min_=10, max_=1000000, step=10)

        results_group = QGroupBox(_("Results"))
        results_label1 = QLabel(_("Results are stored here:"))
        results_label1.setWordWrap(True)

        # Warning: do not try to regroup the following QLabel contents with 
        # widgets above -- this string was isolated here in a single QLabel
        # on purpose: to fix Issue 863
        results_label2 = QLabel(PylintWidget.DATAPATH)

        results_label2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        results_label2.setWordWrap(True)

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(save_box)
        settings_group.setLayout(settings_layout)

        hist_layout = QVBoxLayout()
        hist_layout.addWidget(hist_label1)
        hist_layout.addWidget(hist_spin)
        hist_group.setLayout(hist_layout)

        results_layout = QVBoxLayout()
        results_layout.addWidget(results_label1)
        results_layout.addWidget(results_label2)
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(settings_group)
        vlayout.addWidget(hist_group)
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)


class Pylint(SpyderPluginWidget):
    """Python source code analysis based on pylint."""

    CONF_SECTION = 'pylint'
    CONFIGWIDGET_CLASS = PylintConfigPage

    def __init__(self, parent=None):
        SpyderPluginWidget.__init__(self, parent)

        max_entries = self.get_option('max_entries', 50)
        self.pylint = PylintWidget(self, max_entries=max_entries)

        layout = QVBoxLayout()
        layout.addWidget(self.pylint)
        self.setLayout(layout)
        
        # Initialize plugin
        self.initialize_plugin()
        
    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Static code analysis")

    def get_plugin_icon(self):
        """Return widget icon"""
        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        return ima.icon('pylint', icon_path=path)

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.pylint.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        # Font
        history_action = create_action(self, _("History..."),
                                       None, ima.icon('history'),
                                       _("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        self.pylint.treewidget.common_actions += (None, history_action)
        return []

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.help, self)
        self.dockwidget.hide()

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.pylint.treewidget.sig_edit_goto.connect(self.main.editor.load)
        self.pylint.redirect_stdio.connect(
            self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)
        
        pylint_act = create_action(self, _("Run static code analysis"),
                                   triggered=self.run_pylint)
        pylint_act.setEnabled(is_module_installed('pylint'))
        self.register_shortcut(pylint_act, context="Pylint",
                               name="Run analysis")
        
        self.main.source_menu_actions += [MENU_SEPARATOR, pylint_act]
        self.main.editor.pythonfile_dependent_actions += [pylint_act]

    def refresh_plugin(self):
        """Refresh pylint widget"""
        self.pylint.remove_obsolete_items()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
            
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        # The history depth option will be applied at 
        # next Spyder startup, which is soon enough
        pass
        
    #------ Public API --------------------------------------------------------
    @Slot()
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInt(self, _('History'),
                                       _('Maximum entries'),
                                       self.get_option('max_entries'),
                                       10, 10000)
        if valid:
            self.set_option('max_entries', depth)

    @Slot()
    def run_pylint(self):
        """Run pylint code analysis"""
        if self.get_option('save_before', True)\
           and not self.main.editor.save():
            return
        self.analyze( self.main.editor.get_current_filename() )
        
    def analyze(self, filename):
        """Reimplement analyze method"""
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        self.pylint.analyze(filename)

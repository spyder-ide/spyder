# -*- coding:utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Pylint Code Analysis Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from spyderlib.qt.QtGui import QInputDialog, QVBoxLayout, QGroupBox, QLabel
from spyderlib.qt.QtCore import SIGNAL, Qt

# Local imports
from spyderlib.baseconfig import get_translation
_ = get_translation("p_pylint", dirname="spyderplugins")
from spyderlib.utils.qthelpers import get_icon, create_action
from spyderlib.plugins import SpyderPluginMixin, PluginConfigPage

from spyderplugins.widgets.pylintgui import PylintWidget, PYLINT_PATH


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


class Pylint(PylintWidget, SpyderPluginMixin):
    """Python source code analysis based on pylint"""
    CONF_SECTION = 'pylint'
    CONFIGWIDGET_CLASS = PylintConfigPage
    def __init__(self, parent=None):
        PylintWidget.__init__(self, parent=parent,
                              max_entries=self.get_option('max_entries', 50))
        SpyderPluginMixin.__init__(self, parent)
        
        # Initialize plugin
        self.initialize_plugin()
        
    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Static code analysis")
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('pylint.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.treewidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        # Font
        history_action = create_action(self, _("History..."),
                                       None, 'history.png',
                                       _("Set history maximum entries"),
                                       triggered=self.change_history_depth)
        self.treewidget.common_actions += (None, history_action)
        return []

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.inspector, self)
        self.dockwidget.hide()

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self, SIGNAL("edit_goto(QString,int,QString)"),
                     self.main.editor.load)
        self.connect(self, SIGNAL('redirect_stdio(bool)'),
                     self.main.redirect_internalshell_stdio)
        self.main.add_dockwidget(self)
        
        pylint_act = create_action(self, _("Run static code analysis"),
                                   triggered=self.run_pylint)
        pylint_act.setEnabled(PYLINT_PATH is not None)
        self.register_shortcut(pylint_act, context="Pylint",
                               name="Run analysis")
        
        self.main.source_menu_actions += [None, pylint_act]
        self.main.editor.pythonfile_dependent_actions += [pylint_act]

    def refresh_plugin(self):
        """Refresh pylint widget"""
        self.remove_obsolete_items()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
            
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        # The history depth option will be applied at 
        # next Spyder startup, which is soon enough
        pass
        
    #------ Public API --------------------------------------------------------
    def change_history_depth(self):
        "Change history max entries"""
        depth, valid = QInputDialog.getInteger(self, _('History'),
                                       _('Maximum entries'),
                                       self.get_option('max_entries'),
                                       10, 10000)
        if valid:
            self.set_option('max_entries', depth)
        
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
        PylintWidget.analyze(self, filename)


#==============================================================================
# The following statements are required to register this 3rd party plugin:
#==============================================================================
PLUGIN_CLASS = Pylint


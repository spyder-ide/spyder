# -*- coding:utf-8 -*-
#
# Copyright © 2012 Jed Ludlow
# Based loosely on p_pylint.py by Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Breakpoint Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Local imports
from spyderlib.config.base import get_translation
from spyderlib.utils import icon_manager as ima
from spyderlib.utils.qthelpers import create_action
from spyderlib.plugins import SpyderPluginMixin
from spyderlib.py3compat import to_text_string, is_text_string
from .widgets.breakpointsgui import BreakpointWidget

_ = get_translation("breakpoints", "spyplugins.ui.breakpoints")


class Breakpoints(BreakpointWidget, SpyderPluginMixin):
    """Breakpoint list"""
    CONF_SECTION = 'breakpoints'

#    CONFIGWIDGET_CLASS = BreakpointConfigPage
    def __init__(self, parent=None):
        BreakpointWidget.__init__(self, parent=parent)
        SpyderPluginMixin.__init__(self, parent)
        
        # Initialize plugin
        self.initialize_plugin()
        self.set_data()
    
    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Breakpoints")
    
    def get_plugin_icon(self):
        """Return widget icon"""
        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        return ima.icon('profiler', icon_path=path)
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.dictwidget
    
    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return []

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.main.tabify_plugins(self.main.help, self)

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.edit_goto.connect(self.main.editor.load)
        #self.redirect_stdio.connect(self.main.redirect_internalshell_stdio)
        self.clear_all_breakpoints.connect(
                                        self.main.editor.clear_all_breakpoints)
        self.clear_breakpoint.connect(self.main.editor.clear_breakpoint)
        self.main.editor.breakpoints_saved.connect(self.set_data)
        self.set_or_edit_conditional_breakpoint.connect(
                           self.main.editor.set_or_edit_conditional_breakpoint)
        
        self.main.add_dockwidget(self)
        
        list_action = create_action(self, _("List breakpoints"),
                                   triggered=self.show)
        list_action.setEnabled(True)
        
        # A fancy way to insert the action into the Breakpoints menu under
        # the assumption that Breakpoints is the first QMenu in the list.
        for item in self.main.debug_menu_actions:
            try:
                menu_title = item.title()
            except AttributeError:
                pass
            else:
                # Depending on Qt API version, could get a QString or 
                # unicode from title()
                if not is_text_string(menu_title): # string is a QString
                    menu_title = to_text_string(menu_title.toUtf8)
                item.addAction(list_action)
                # If we've reached this point it means we've located the 
                # first QMenu in the run_menu. Since there might be other
                # QMenu entries in run_menu, we'll break so that the
                # breakpoint action is only inserted once into the run_menu.
                break
        self.main.editor.pythonfile_dependent_actions += [list_action]

    def refresh_plugin(self):
        """Refresh widget"""
        pass
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        return True
            
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        pass
        
    def show(self):
        """Show the breakpoints dockwidget"""
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()

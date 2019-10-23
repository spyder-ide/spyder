# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""Breakpoint Plugin."""


# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtWidgets import QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import create_action
from spyder.api.plugins import SpyderPluginWidget

from .widgets.breakpointsgui import BreakpointWidget


class Breakpoints(SpyderPluginWidget):
    """Breakpoint list"""
    CONF_SECTION = 'breakpoints'
    CONF_FILE = False

    def __init__(self, parent=None):
        """Initialization."""
        SpyderPluginWidget.__init__(self, parent)

        self.breakpoints = BreakpointWidget(self,
                                            options_button=self.options_button)

        layout = QVBoxLayout()
        layout.addWidget(self.breakpoints)
        self.setLayout(layout)

        self.breakpoints.set_data()

        path = osp.join(self.PLUGIN_PATH, self.IMG_PATH)
        self.icon = ima.icon('breakpoints', icon_path=path)

    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _("Breakpoints")

    def get_plugin_icon(self):
        """Return widget icon"""
        return self.icon

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.breakpoints.dictwidget

    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.help)

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.breakpoints.edit_goto.connect(self.main.editor.load)
        #self.redirect_stdio.connect(self.main.redirect_internalshell_stdio)
        self.breakpoints.clear_all_breakpoints.connect(
                                        self.main.editor.clear_all_breakpoints)
        self.breakpoints.clear_breakpoint.connect(
            self.main.editor.clear_breakpoint)
        self.main.editor.breakpoints_saved.connect(self.breakpoints.set_data)
        self.breakpoints.set_or_edit_conditional_breakpoint.connect(
                           self.main.editor.set_or_edit_conditional_breakpoint)

        self.add_dockwidget()

        list_action = create_action(self, _("List breakpoints"),
                                    triggered=self.show, icon=self.icon)
        list_action.setEnabled(True)
        pos = self.main.debug_menu_actions.index('list_breakpoints')
        self.main.debug_menu_actions.insert(pos, list_action)
        self.main.editor.pythonfile_dependent_actions += [list_action]

    def show(self):
        """Show the breakpoints dockwidget"""
        self.switch_to_plugin()

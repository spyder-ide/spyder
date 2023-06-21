# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Breakpoint Plugin.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.breakpoints.widgets.main_widget import BreakpointWidget
from spyder.plugins.mainmenu.api import ApplicationMenus, DebugMenuSections


# --- Constants
# ----------------------------------------------------------------------------
class BreakpointsActions:
    ListBreakpoints = 'list_breakpoints_action'


# --- Plugin
# ----------------------------------------------------------------------------
class Breakpoints(SpyderDockablePlugin):
    """
    Breakpoint list Plugin.
    """
    NAME = 'breakpoints'
    REQUIRES = [Plugins.Editor, Plugins.Debugger]
    OPTIONAL = [Plugins.MainMenu]
    TABIFY = [Plugins.Help]
    WIDGET_CLASS = BreakpointWidget
    CONF_SECTION = NAME
    CONF_FILE = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_clear_all_breakpoints_requested = Signal()
    """
    This signal is emitted to send a request to clear all assigned
    breakpoints.
    """

    sig_clear_breakpoint_requested = Signal(str, int)
    """
    This signal is emitted to send a request to clear a single breakpoint.

    Parameters
    ----------
    filename: str
        The path to filename containing the breakpoint.
    line_number: int
        The line number of the breakpoint.
    """

    sig_edit_goto_requested = Signal(str, int, str)
    """
    Send a request to open a file in the editor at a given row and word.

    Parameters
    ----------
    filename: str
        The path to the filename containing the breakpoint.
    line_number: int
        The line number of the breakpoint.
    word: str
        Text `word` to select on given `line_number`.
    """

    sig_conditional_breakpoint_requested = Signal()
    """
    Send a request to set/edit a condition on a single selected breakpoint.
    """

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Breakpoints")

    def get_description(self):
        return _("Manage code breakpoints in a unified pane.")

    def get_icon(self):
        return self.create_icon('breakpoints')

    def on_initialize(self):
        widget = self.get_widget()

        widget.sig_clear_all_breakpoints_requested.connect(
            self.sig_clear_all_breakpoints_requested)
        widget.sig_clear_breakpoint_requested.connect(
            self.sig_clear_breakpoint_requested)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_conditional_breakpoint_requested.connect(
            self.sig_conditional_breakpoint_requested)

        self.create_action(
            BreakpointsActions.ListBreakpoints,
            _("List breakpoints"),
            triggered=self.switch_to_plugin,
            icon=self.get_icon(),
        )

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        list_action = self.get_action(BreakpointsActions.ListBreakpoints)

        widget.sig_edit_goto_requested.connect(editor.load)

        # TODO: Fix location once the sections are defined
        editor.pythonfile_dependent_actions += [list_action]

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        list_action = self.get_action(BreakpointsActions.ListBreakpoints)

        widget.sig_edit_goto_requested.disconnect(editor.load)
        editor.pythonfile_dependent_actions.remove(list_action)

    @on_plugin_available(plugin=Plugins.Debugger)
    def on_debugger_available(self):
        debugger = self.get_plugin(Plugins.Debugger)
        widget = self.get_widget()
        debugger.get_widget().sig_breakpoints_saved.connect(self.set_data)

        widget.sig_clear_all_breakpoints_requested.connect(
            debugger.clear_all_breakpoints)
        widget.sig_clear_breakpoint_requested.connect(
            debugger.clear_breakpoint)
        widget.sig_conditional_breakpoint_requested.connect(
            debugger._set_or_edit_conditional_breakpoint)

    @on_plugin_teardown(plugin=Plugins.Debugger)
    def on_debugger_teardown(self):
        debugger = self.get_plugin(Plugins.Debugger)
        widget = self.get_widget()
        debugger.get_widget().sig_breakpoints_saved.disconnect(self.set_data)

        widget.sig_clear_all_breakpoints_requested.disconnect(
            debugger.clear_all_breakpoints)
        widget.sig_clear_breakpoint_requested.disconnect(
            debugger.clear_breakpoint)
        widget.sig_conditional_breakpoint_requested.disconnect(
            debugger._set_or_edit_conditional_breakpoint)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        list_action = self.get_action(BreakpointsActions.ListBreakpoints)
        mainmenu.add_item_to_application_menu(
            list_action,
            menu_id=ApplicationMenus.Debug,
            section=DebugMenuSections.ListBreakpoints)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            BreakpointsActions.ListBreakpoints,
            menu_id=ApplicationMenus.Debug)

    # --- Private API
    # ------------------------------------------------------------------------
    def _load_data(self):
        """
        Load breakpoint data from configuration file.
        """
        breakpoints_dict = self.get_conf(
            "breakpoints",
            default={},
            section='debugger',
        )
        for filename in list(breakpoints_dict.keys()):
            if not osp.isfile(filename):
                breakpoints_dict.pop(filename)
                continue
            # Make sure we don't have the same file under different names
            new_filename = osp.normcase(filename)
            if new_filename != filename:
                bp = breakpoints_dict.pop(filename)
                if new_filename in breakpoints_dict:
                    breakpoints_dict[new_filename].extend(bp)
                else:
                    breakpoints_dict[new_filename] = bp

        return breakpoints_dict

    # --- Public API
    # ------------------------------------------------------------------------
    def set_data(self, data=None):
        """
        Set breakpoint data on widget.

        Parameters
        ----------
        data: dict, optional
            Breakpoint data to use. If None, data from the configuration
            will be loaded. Default is None.
        """
        if data is None:
            data = self._load_data()

        self.get_widget().set_data(data)

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
from spyder.api.translations import get_translation
from spyder.plugins.breakpoints.widgets.main_widget import BreakpointWidget
from spyder.plugins.mainmenu.api import ApplicationMenus

# Localization
_ = get_translation('spyder')


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
    REQUIRES = [Plugins.Editor]
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
    def get_name(self):
        return _("Breakpoints")

    def get_description(self):
        return _("Manage code breakpoints in a unified pane.")

    def get_icon(self):
        return self.create_icon('breakpoints')

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        mainmenu = self.get_plugin(Plugins.MainMenu)

        # TODO: change name of this signal on editor
        editor.breakpoints_saved.connect(self.set_data)
        widget.sig_clear_all_breakpoints_requested.connect(
            editor.clear_all_breakpoints)
        widget.sig_clear_breakpoint_requested.connect(editor.clear_breakpoint)
        widget.sig_edit_goto_requested.connect(editor.load)
        widget.sig_conditional_breakpoint_requested.connect(
            editor.set_or_edit_conditional_breakpoint)

        widget.sig_clear_all_breakpoints_requested.connect(
            self.sig_clear_all_breakpoints_requested)
        widget.sig_clear_breakpoint_requested.connect(
            self.sig_clear_breakpoint_requested)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_conditional_breakpoint_requested.connect(
            self.sig_conditional_breakpoint_requested)

        list_action = self.create_action(
            BreakpointsActions.ListBreakpoints,
            _("List breakpoints"),
            triggered=lambda: self.switch_to_plugin(),
            icon=self.get_icon(),
        )

        if mainmenu:
            debug_menu = mainmenu.get_application_menu(ApplicationMenus.Debug)
            mainmenu.add_item_to_application_menu(list_action, debug_menu)

        # TODO: Fix location once the sections are defined
        editor.pythonfile_dependent_actions += [list_action]

    # --- Private API
    # ------------------------------------------------------------------------
    def _load_data(self):
        """
        Load breakpoint data from configuration file.
        """
        breakpoints_dict = self.get_conf(
            'breakpoints',
            default={},
            section='run',
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

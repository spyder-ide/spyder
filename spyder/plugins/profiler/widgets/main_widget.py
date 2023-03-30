# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# based on pylintgui.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler widget.

See the official documentation on python profiling:
https://docs.python.org/3/library/profile.html
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.compat import getopenfilename, getsavefilename
from qtpy.QtCore import Signal

# Local imports
from spyder.api.translations import _
from spyder.utils.misc import getcwd_or_home
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.plugins.profiler.widgets.profiler_data_tree import (
    ProfilerSubWidget)



class ProfilerWidgetActions:
    # Triggers
    Clear = 'clear_action'
    Collapse = 'collapse_action'
    Expand = 'expand_action'
    ToggleTreeDirection = "tree_direction_action"
    ToggleBuiltins = "toggle_builtins_action"
    Home = "HomeAction"
    SlowLocal = 'slow_local_action'
    LoadData = 'load_data_action'
    SaveData = 'save_data_action'
    Search = "find_action"
    Undo = "undo_action"
    Redo = "redo_action"


class ProfilerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class ProfilerContextMenuSections:
    Locals = 'locals_section'


class ProfilerWidgetContextMenuActions:
    ShowCallees = "show_callees_action"
    ShowCallers = "show_callers_action"


class ProfilerWidgetMainToolbarSections:
    Main = 'main_section'


class ProfilerWidgetInformationToolbarItems:
    Stretcher = 'stretcher'


# --- Widgets
# ----------------------------------------------------------------------------
class ProfilerWidget(ShellConnectMainWidget):
    """
    Profiler widget.
    """

    # --- Signals
    # ------------------------------------------------------------------------
    sig_edit_goto_requested = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Profiler')

    def setup(self):
        self.collapse_action = self.create_action(
            ProfilerWidgetActions.Collapse,
            text=_('Collapse'),
            tip=_('Collapse one level up'),
            icon=self.create_icon('collapse'),
            triggered=lambda x=None: self.current_widget(
                ).data_tree.change_view(-1),
        )
        self.expand_action = self.create_action(
            ProfilerWidgetActions.Expand,
            text=_('Expand'),
            tip=_('Expand one level down'),
            icon=self.create_icon('expand'),
            triggered=lambda x=None: self.current_widget(
                ).data_tree.change_view(1),
        )
        self.home_action = self.create_action(
            ProfilerWidgetActions.Home,
            text=_("Reset tree"),
            tip=_('Go back to full tree'),
            icon=self.create_icon('home'),
            triggered=self.home_tree,
        )
        self.toggle_tree_action = self.create_action(
            ProfilerWidgetActions.ToggleTreeDirection,
            text=_("Switch tree direction"),
            tip=_('Switch tree direction between callers and callees'),
            icon=self.create_icon('swap'),
            toggled=self.toggle_tree,
        )
        self.slow_local_action = self.create_action(
            ProfilerWidgetActions.SlowLocal,
            text=_("Show items with large local time"),
            tip=_('Show items with large local time'),
            icon=self.create_icon('slow'),
            triggered=self.slow_local_tree,
        )
        self.toggle_builtins_action = self.create_action(
            ProfilerWidgetActions.ToggleBuiltins,
            text=_("Hide builtins"),
            tip=_('Hide builtins'),
            icon=self.create_icon('hide'),
            toggled=self.toggle_builtins,
        )
        self.save_action = self.create_action(
            ProfilerWidgetActions.SaveData,
            text=_("Save data"),
            tip=_('Save profiling data'),
            icon=self.create_icon('filesave'),
            triggered=self.save_data,
        )
        self.load_action = self.create_action(
            ProfilerWidgetActions.LoadData,
            text=_("Load data"),
            tip=_('Load profiling data for comparison'),
            icon=self.create_icon('fileimport'),
            triggered=self.load_data,
        )
        self.clear_action = self.create_action(
            ProfilerWidgetActions.Clear,
            text=_("Clear comparison"),
            tip=_("Clear comparison"),
            icon=self.create_icon('editdelete'),
            triggered=self.clear,
        )
        self.clear_action.setEnabled(False)
        search_action = self.create_action(
            ProfilerWidgetActions.Search,
            text=_("Search"),
            icon=self.create_icon('find'),
            toggled=self.toggle_finder,
            register_shortcut=True
        )
        undo_action = self.create_action(
            ProfilerWidgetActions.Undo,
            text=_("Previous View"),
            icon=self.create_icon('undo'),
            triggered=self.undo,
            register_shortcut=True
        )
        redo_action = self.create_action(
            ProfilerWidgetActions.Redo,
            text=_("Next View"),
            icon=self.create_icon('redo'),
            triggered=self.redo,
            register_shortcut=True
        )
        main_toolbar = self.get_main_toolbar()

        for item in [
                self.home_action,
                undo_action,
                redo_action,
                self.collapse_action,
                self.expand_action,
                self.toggle_tree_action,
                self.toggle_builtins_action,
                self.slow_local_action,
                search_action,
                self.create_stretcher(
                    id_=ProfilerWidgetInformationToolbarItems.Stretcher),
                self.save_action,
                self.load_action,
                self.clear_action
                ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=ProfilerWidgetMainToolbarSections.Main,
            )
        # ---- Context menu actions
        self.show_callees_action = self.create_action(
            ProfilerWidgetContextMenuActions.ShowCallees,
            _("Show callees"),
            icon=self.create_icon('2downarrow'),
            triggered=self.show_callees
        )
        self.show_callers_action = self.create_action(
            ProfilerWidgetContextMenuActions.ShowCallers,
            _("Show callers"),
            icon=self.create_icon('2uparrow'),
            triggered=self.show_callers
        )
        # ---- Context menu to show when there are frames present
        self.context_menu = self.create_menu(
            ProfilerWidgetMenus.PopulatedContextMenu)
        for item in [self.show_callers_action, self.show_callees_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=ProfilerContextMenuSections.Locals,
            )

    def update_actions(self):
        """Update actions."""
        widget = self.current_widget()
        search_action = self.get_action(ProfilerWidgetActions.Search)
        toggle_tree_action = self.get_action(
            ProfilerWidgetActions.ToggleTreeDirection)
        toggle_builtins_action = self.get_action(
            ProfilerWidgetActions.ToggleBuiltins)

        if widget is None:
            search = False
            inverted_tree = False
            ignore_builtins = False
        else:
            search = widget.finder_is_visible()
            inverted_tree = widget.data_tree.inverted_tree
            ignore_builtins = widget.data_tree.ignore_builtins

        search_action.setChecked(search)
        toggle_tree_action.setChecked(inverted_tree)
        toggle_builtins_action.setChecked(ignore_builtins)

    # --- Public API
    # ------------------------------------------------------------------------
    def home_tree(self):
        """Invert tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.home_tree()

    def toggle_tree(self, state):
        """Invert tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.inverted_tree = state
        widget.data_tree.refresh_tree()

    def toggle_builtins(self, state):
        """Invert tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.ignore_builtins = state
        widget.data_tree.refresh_tree()

    def slow_local_tree(self):
        """Show items with large local times"""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.show_slow()

    def undo(self):
        """Undo change."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.undo()

    def redo(self):
        """Redo changes."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.redo()

    def show_callers(self):
        """Invert tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.show_selected()
        if not self.toggle_tree_action.isChecked():
            self.toggle_tree_action.setChecked(True)

    def show_callees(self):
        """Invert tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.show_selected()
        if self.toggle_tree_action.isChecked():
            self.toggle_tree_action.setChecked(False)

    def save_data(self):
        """Save data."""
        widget = self.current_widget()
        if widget is None:
            return
        title = _("Save profiler result")
        filename, _selfilter = getsavefilename(
            self,
            title,
            getcwd_or_home(),
            _("Profiler result") + " (*.prof)",
        )
        extension = osp.splitext(filename)[1].lower()
        if not extension:
            # Needed to prevent trying to save a data file without extension
            # See spyder-ide/spyder#19633
            filename = filename + '.prof'

        if filename:
            widget.data_tree.save_data(filename)

    def load_data(self):
        """Compare previous saved run with last run."""
        widget = self.current_widget()
        if widget is None:
            return
        filename, _selfilter = getopenfilename(
            self,
            _("Select script to compare"),
            getcwd_or_home(),
            _("Profiler result") + " (*.prof)",
        )

        if filename:
            widget.data_tree.compare(filename)
            widget.data_tree.home_tree()
            self.clear_action.setEnabled(True)

    def clear(self):
        """Clear data in tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.data_tree.compare(None)
        widget.data_tree.home_tree()
        self.clear_action.setEnabled(False)

    def create_new_widget(self, shellwidget):
        """Create new profiler widget."""
        widget = ProfilerSubWidget(self)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_display_requested.connect(self.display_request)
        widget.set_context_menu(self.context_menu)
        widget.sig_hide_finder_requested.connect(self.hide_finder)

        shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "show_profile_file", widget.show_profile_buffer)
        widget.shellwidget = shellwidget

        return widget

    def close_widget(self, widget):
        """Close profiler widget."""
        widget.sig_edit_goto_requested.disconnect(
            self.sig_edit_goto_requested)
        widget.sig_display_requested.disconnect(self.display_request)
        widget.sig_hide_finder_requested.disconnect(self.hide_finder)

        # Unregister
        widget.shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "show_profile_file", None)
        widget.setParent(None)
        widget.close()

    def switch_widget(self, widget, old_widget):
        """Switch widget."""
        pass

    def display_request(self, widget):
        """
        Display request from ProfilerDataTree.

        Only display if this is the current widget.
        """
        if (
            self.current_widget() is widget
            and self.get_conf("switch_to_plugin")
        ):
            self.get_plugin().switch_to_plugin()

    def toggle_finder(self, checked):
        """Show or hide finder."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.toggle_finder(checked)

    def hide_finder(self):
        """Hide finder."""
        action = self.get_action(ProfilerWidgetActions.Search)
        action.setChecked(False)

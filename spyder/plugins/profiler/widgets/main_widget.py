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
import functools
import os.path as osp

# Third party imports
from qtpy.compat import getopenfilename, getsavefilename
from qtpy.QtCore import Signal
from superqt.utils import signals_blocked

# Local imports
from spyder.api.translations import _
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.plugins.profiler.widgets.profiler_data_tree import (
    ProfilerSubWidget
)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home


class ProfilerWidgetActions:
    # Triggers
    Clear = 'clear_action'
    Collapse = 'collapse_action'
    Expand = 'expand_action'
    CallersOrCallees = "callers_or_callees_action"
    ToggleBuiltins = "toggle_builtins_action"
    Home = "HomeAction"
    SlowLocal = 'slow_local_action'
    LoadData = 'load_data_action'
    SaveData = 'save_data_action'
    Search = "find_action"
    Undo = "undo_action"
    Redo = "redo_action"
    Stop = "stop_action"


class ProfilerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class ProfilerContextMenuSections:
    Locals = 'locals_section'
    Other = "other_section"


class ProfilerWidgetContextMenuActions:
    GotoDefinition = "goto_definition_action"
    ShowCallees = "show_callees_action"
    ShowCallers = "show_callers_action"


class ProfilerWidgetMainToolbarSections:
    # BrowseView = "view_section" # To be added later
    ExpandCollapse = "collapse_section"
    ChangeView = "change_view_section"
    Stop = "stop_section"


# --- Widgets
# ----------------------------------------------------------------------------
class ProfilerWidget(ShellConnectMainWidget):
    """Profiler widget."""

    # PluginMainWidget API
    ENABLE_SPINNER = True
    SHOW_MESSAGE_WHEN_EMPTY = True
    IMAGE_WHEN_EMPTY = "code-profiler"
    MESSAGE_WHEN_EMPTY = _("Code not profiled yet")
    DESCRIPTION_WHEN_EMPTY = _(
        "Profile your code to explore which functions and methods took the "
        "longest to run and were called the most, and find out where to "
        "optimize it."
    )

    # Other
    TIP_CALLERS = _("Show functions or modules that call the root item")
    TIP_CALLEES = _("Show functions or modules called by the root item")
    TIP_CALLERS_OR_CALLEES = _(
        "Show functions or modules that call an item or are called by it"
    )

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

    # ---- PluginMainWidget API
    # -------------------------------------------------------------------------
    def get_title(self):
        return _('Profiler')

    def setup(self):
        # ---- Toolbar actions
        collapse_action = self.create_action(
            ProfilerWidgetActions.Collapse,
            text=_('Collapse'),
            tip=_('Collapse one level up'),
            icon=self.create_icon('collapse'),
            triggered=self._collapse_tree,
        )
        expand_action = self.create_action(
            ProfilerWidgetActions.Expand,
            text=_('Expand'),
            tip=_('Expand one level down'),
            icon=self.create_icon('expand'),
            triggered=self._expand_tree,
        )
        callers_or_callees_action = self.create_action(
            ProfilerWidgetActions.CallersOrCallees,
            text=self.TIP_CALLERS_OR_CALLEES,
            tip=self.TIP_CALLERS_OR_CALLEES,
            icon=self.create_icon("callers_or_callees"),
            toggled=self._toggle_callers_or_callees,
        )
        slow_local_action = self.create_action(
            ProfilerWidgetActions.SlowLocal,
            text=_("Show items with large local time"),
            tip=_('Show items with large local time'),
            icon=self.create_icon('slow'),
            toggled=self._slow_local_tree,
        )
        toggle_builtins_action = self.create_action(
            ProfilerWidgetActions.ToggleBuiltins,
            text=_("Hide calls to external libraries"),
            tip=_('Hide calls to external libraries'),
            icon=self.create_icon('hide'),
            toggled=self._toggle_builtins,
        )
        save_action = self.create_action(
            ProfilerWidgetActions.SaveData,
            text=_("Save data"),
            tip=_('Save profiling data'),
            icon=self.create_icon('filesave'),
            triggered=self._save_data,
        )
        load_action = self.create_action(
            ProfilerWidgetActions.LoadData,
            text=_("Load data"),
            tip=_('Load profiling data for comparison'),
            icon=self.create_icon('fileimport'),
            triggered=self._load_data,
        )
        clear_action = self.create_action(
            ProfilerWidgetActions.Clear,
            text=_("Clear comparison"),
            tip=_("Clear comparison"),
            icon=self.create_icon('editdelete'),
            triggered=self._clear,
        )
        search_action = self.create_action(
            ProfilerWidgetActions.Search,
            text=_("Search"),
            icon=self.create_icon('find'),
            toggled=self._toggle_finder,
            register_shortcut=True
        )
        stop_action = self.create_action(
            ProfilerWidgetActions.Stop,
            text=_("Stop profiling"),
            icon=self.create_icon('stop_profile'),
            triggered=self._stop_profiling,
        )

        # This needs to be workedd out better because right now is confusing
        # and kind of unnecessary
        # undo_action = self.create_action(
        #     ProfilerWidgetActions.Undo,
        #     text=_("Previous View"),
        #     icon=self.create_icon('previous'),
        #     triggered=self._undo,
        #     register_shortcut=True
        # )
        # redo_action = self.create_action(
        #     ProfilerWidgetActions.Redo,
        #     text=_("Next View"),
        #     icon=self.create_icon('next'),
        #     triggered=self._redo,
        #     register_shortcut=True
        # )
        # home_action = self.create_action(
        #     ProfilerWidgetActions.Home,
        #     text=_("Reset tree"),
        #     tip=_('Go back to full tree'),
        #     icon=self.create_icon('home'),
        #     triggered=self._home_tree,
        # )

        # ---- Main Toolbar
        main_toolbar = self.get_main_toolbar()

        # To be added later
        # for action in [undo_action, redo_action, home_action]:
        #     self.add_item_to_toolbar(
        #         action,
        #         toolbar=main_toolbar,
        #         section=ProfilerWidgetMainToolbarSections.BrowseView,
        #     )

        for action in [collapse_action, expand_action]:
            self.add_item_to_toolbar(
                action,
                toolbar=main_toolbar,
                section=ProfilerWidgetMainToolbarSections.ExpandCollapse,
            )

        for action in [
            slow_local_action,
            toggle_builtins_action,
            callers_or_callees_action,
            search_action
        ]:
            self.add_item_to_toolbar(
                action,
                toolbar=main_toolbar,
                section=ProfilerWidgetMainToolbarSections.ChangeView,
            )

        self.add_item_to_toolbar(
            stop_action,
            toolbar=main_toolbar,
            section=ProfilerWidgetMainToolbarSections.Stop,
        )

        # ---- Corner widget
        for action in [save_action, load_action, clear_action]:
            self.add_corner_widget(action, before=self._options_button)

        # ---- Context menu actions
        show_callees_action = self.create_action(
            ProfilerWidgetContextMenuActions.ShowCallees,
            _("Show functions or modules called by this item"),
            icon=self.create_icon('callees'),
            triggered=self._show_callees
        )
        show_callers_action = self.create_action(
            ProfilerWidgetContextMenuActions.ShowCallers,
            _("Show functions or modules that call this item"),
            icon=self.create_icon('callers'),
            triggered=self._show_callers
        )
        goto_definition_action = self.create_action(
            ProfilerWidgetContextMenuActions.GotoDefinition,
            _("Go to definition"),
            icon=self.create_icon("transparent"),
            triggered=self._goto_definition
        )

        self._context_menu = self.create_menu(
            ProfilerWidgetMenus.PopulatedContextMenu
        )
        for item in [show_callers_action, show_callees_action]:
            self.add_item_to_menu(
                item,
                menu=self._context_menu,
                section=ProfilerContextMenuSections.Locals,
            )

        self.add_item_to_menu(
            goto_definition_action,
            menu=self._context_menu,
            section=ProfilerContextMenuSections.Other,
        )

    def update_actions(self):
        """Update actions."""
        widget = self.current_widget()
        search_action = self.get_action(ProfilerWidgetActions.Search)
        callers_or_callees_action = self.get_action(
            ProfilerWidgetActions.CallersOrCallees
        )
        toggle_builtins_action = self.get_action(
            ProfilerWidgetActions.ToggleBuiltins
        )
        slow_local_action = self.get_action(ProfilerWidgetActions.SlowLocal)
        stop_action = self.get_action(ProfilerWidgetActions.Stop)

        widget_inactive = (
            widget is None or self.is_current_widget_error_message()
        )
        if widget_inactive:
            search = False
            callers_or_callees_enabled = False
            ignore_builtins = False
            show_slow = False
            stop = False
            self.stop_spinner()
        else:
            search = widget.finder_is_visible()
            callers_or_callees_enabled = widget.callers_or_callees_enabled
            ignore_builtins = widget.ignore_builtins
            show_slow = widget.show_slow
            stop = widget.is_profiling

        toggle_builtins_action.setChecked(ignore_builtins)
        stop_action.setEnabled(stop)

        # Showing callers/callees can't be combined with slow locals and search
        # because they give different views, so we need to disable them.
        if callers_or_callees_enabled:
            # Automatically toggle the action
            callers_or_callees_action.setEnabled(True)
            callers_or_callees_action.setChecked(True)

            # This prevents an additional call to update_actions because
            # refresh_tree emits at the end sig_refresh
            with signals_blocked(widget):
                widget.refresh_tree()

            # Adjust button's tooltip and icon
            show_callers = widget.inverted_tree
            callers_or_callees_action.setToolTip(
                self.TIP_CALLERS if show_callers else self.TIP_CALLEES
            )
            callers_or_callees_action.setIcon(
                ima.icon("callers" if show_callers else "callees")
            )

            # Disable slow locals
            widget.show_slow = False
            with signals_blocked(slow_local_action):
                slow_local_action.setChecked(False)
                slow_local_action.setEnabled(False)

            # Disable search and hide finder widget
            with signals_blocked(search_action):
                search_action.setChecked(False)
                search_action.setEnabled(False)

            with signals_blocked(widget.finder):
                widget.finder.set_visible(False)

            # We expand the tree so that users can easily inspect callers or
            # callees
            self._expand_tree()
        else:
            search_action.setChecked(search)
            slow_local_action.setChecked(show_slow)

            # Recreate custom view if we're showing slow locals or searching
            # for something
            if not widget_inactive and widget.recreate_custom_view:
                # Reset state for next time
                widget.recreate_custom_view = False

                if search:
                    search_text = widget.finder_text()
                    if search_text:
                        widget.do_find(search_text)
                elif show_slow:
                    self._slow_local_tree(True)

            if callers_or_callees_action.isEnabled():
                # Change icon and tooltip when the button is inactive
                callers_or_callees_action.setToolTip(
                    self.TIP_CALLERS_OR_CALLEES
                )
                callers_or_callees_action.setIcon(
                    ima.icon("callers_or_callees")
                )

                # Untoggle the button
                with signals_blocked(callers_or_callees_action):
                    callers_or_callees_action.setChecked(False)
                    callers_or_callees_action.setEnabled(False)

        if not widget_inactive:
            if widget.is_profiling:
                self.start_spinner()
            else:
                self.stop_spinner()

        # Home, undo and redo are disabled for now because they are confusing
        # and kind of unnecessary
        # can_redo = False
        # can_undo = False

        tree_empty = True
        can_clear = False
        if not widget_inactive:
            tree_empty = widget.profdata is None
            # can_undo = len(widget.data_tree.history) > 1
            # can_redo = len(widget.data_tree.redo_history) > 0
            can_clear = widget.compare_data is not None

        for action_name in [
            ProfilerWidgetActions.Collapse,
            ProfilerWidgetActions.Expand,
            ProfilerWidgetActions.ToggleBuiltins,
            # ProfilerWidgetActions.Home,
            ProfilerWidgetActions.SlowLocal,
            ProfilerWidgetActions.SaveData,
            ProfilerWidgetActions.LoadData,
            ProfilerWidgetActions.Search,
        ]:
            action = self.get_action(action_name)
            if action_name in [
                ProfilerWidgetActions.SlowLocal,
                ProfilerWidgetActions.Search,
            ]:
                action.setEnabled(
                    not tree_empty and not callers_or_callees_enabled
                )
            elif action_name == ProfilerWidgetActions.LoadData:
                action.setEnabled(not widget_inactive)
            else:
                action.setEnabled(not tree_empty)

        # undo_action = self.get_action(ProfilerWidgetActions.Undo)
        # redo_action = self.get_action(ProfilerWidgetActions.Redo)

        # undo_action.setEnabled(can_undo)
        # redo_action.setEnabled(can_redo)

        clear_action = self.get_action(ProfilerWidgetActions.Clear)
        clear_action.setEnabled(can_clear)

    # ---- ShellConnectPluginMixin API
    # -------------------------------------------------------------------------
    def create_new_widget(self, shellwidget):
        """Create new profiler widget."""
        widget = ProfilerSubWidget(self)
        widget.sig_display_requested.connect(self._display_request)
        widget.sig_refresh.connect(self.update_actions)
        widget.set_context_menu(self._context_menu)
        widget.sig_hide_finder_requested.connect(self._hide_finder)
        widget.sig_show_empty_message_requested.connect(
            self.switch_empty_message
        )

        shellwidget.register_kernel_call_handler(
            "show_profile_file", widget.show_profile_buffer
        )
        shellwidget.register_kernel_call_handler(
            "start_profiling", self._start_profiling
        )
        widget.on_kernel_ready_callback = functools.partial(
            self._on_kernel_ready, widget
        )
        shellwidget.sig_kernel_is_ready.connect(
            widget.on_kernel_ready_callback
        )

        widget.shellwidget = shellwidget
        return widget

    def close_widget(self, widget):
        """Close profiler widget."""
        widget.sig_refresh.disconnect(self.update_actions)
        widget.sig_display_requested.disconnect(self._display_request)
        widget.sig_hide_finder_requested.disconnect(self._hide_finder)

        # Unregister
        widget.shellwidget.unregister_kernel_call_handler("show_profile_file")
        widget.shellwidget.unregister_kernel_call_handler("start_profiling")
        widget.shellwidget.sig_kernel_is_ready.disconnect(
            widget.on_kernel_ready_callback
        )
        widget.setParent(None)
        widget.close()

    def switch_widget(self, widget, old_widget):
        """Switch widget."""
        pass

    def switch_empty_message(self, value: bool):
        """
        Override this method to prevent hiding the empty message if profiling
        finishes in another console but the current one has no content to show.
        """
        widget = self.current_widget()
        if widget is None:
            return

        if value:
            self.show_empty_message()
        else:
            if widget.profdata is not None:
                self.show_content_widget()

    def current_widget(self) -> ProfilerSubWidget:
        """Override to add typing."""
        return super().current_widget()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _start_profiling(self):
        self.start_spinner()

        stop_action = self.get_action(ProfilerWidgetActions.Stop)
        stop_action.setEnabled(True)

        widget = self.current_widget()
        if widget is None:
            return

        widget.is_profiling = True

        # Check if we're showing slow locals or searching for something to
        # recreate the custom view after new results arrive.
        if widget.show_slow or (
            widget.finder_is_visible() and widget.finder_text()
        ):
            widget.recreate_custom_view = True

        # Reset state of callers/callees view because the new results couldn't
        # contain the selected item.
        widget.callers_or_callees_enabled = False
        widget.inverted_tree = False

    def _stop_profiling(self):
        widget = self.current_widget()
        if widget is None:
            return

        if widget.is_profiling:
            self.stop_spinner()

            stop_action = self.get_action(ProfilerWidgetActions.Stop)
            stop_action.setEnabled(False)

            widget.shellwidget.request_interrupt_kernel()
            widget.is_profiling = False

    def _home_tree(self):
        """Show home tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.home_tree()

    def _toggle_callers_or_callees(self, state):
        """
        Toggle filter for callers or callees.

        Notes
        -----
        * The toogle state is handled automatically by update_actions.
        * After users untoggle the button, they'll return to the initial view.
        """
        widget = self.current_widget()
        if widget is None:
            return

        if not state:
            widget.callers_or_callees_enabled = False
            widget.inverted_tree = False
            self._home_tree()

    def _collapse_tree(self):
        self.current_widget().change_view(-1)

    def _expand_tree(self):
        self.current_widget().change_view(1)

    def _toggle_builtins(self, state):
        """Toggle builtins."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.ignore_builtins = state
        widget.refresh_tree()

    def _slow_local_tree(self, state):
        """Show items with large local times"""
        widget = self.current_widget()
        if widget is None:
            return

        widget.show_slow = state
        if state:
            widget.show_slow_items()
        else:
            self._home_tree()

    def _undo(self):
        """Undo change."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.undo()

    def _redo(self):
        """Redo changes."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.redo()

    def _show_callers(self):
        """Show callers."""
        widget = self.current_widget()
        if widget is None:
            return

        widget.inverted_tree = True
        widget.show_selected()

    def _show_callees(self):
        """Show callees."""
        widget = self.current_widget()
        if widget is None:
            return

        widget.inverted_tree = False
        widget.show_selected()

    def _goto_definition(self):
        widget = self.current_widget()
        if widget is None:
            return

        item = widget.currentItem()
        if osp.isfile(item.filename):
            self.sig_edit_goto_requested.emit(
                item.filename, item.line_number, ""
            )

    def _save_data(self):
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
            widget.save_data(filename)

    def _load_data(self):
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
            widget.compare(filename)
            widget.home_tree()
            self.update_actions()

    def _clear(self):
        """Clear data in tree."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.compare(None)
        widget.home_tree()
        self.update_actions()

    def _display_request(self, widget):
        """
        Display request from ProfilerDataTree.

        Only display if this is the current widget.
        """
        self.update_actions()
        self._stop_profiling()

        if (
            self.current_widget() is widget
            and self.get_conf("switch_to_plugin")
        ):
            self.get_plugin().switch_to_plugin()

    def _toggle_finder(self, checked):
        """Show or hide finder."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.toggle_finder(checked)

    def _hide_finder(self):
        """Hide finder."""
        action = self.get_action(ProfilerWidgetActions.Search)
        action.setChecked(False)

    def _on_kernel_ready(self, widget: ProfilerSubWidget):
        self._stop_profiling()
        widget.set_pane_empty(True)

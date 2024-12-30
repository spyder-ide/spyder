# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Debugger Main Plugin Widget.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QHBoxLayout, QSplitter

# Local imports
import qstylizer.style
from spyder.api.config.decorators import on_conf_change
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.api.plugins import Plugins
from spyder.api.translations import _
from spyder.plugins.debugger.widgets.framesbrowser import (
    FramesBrowser, FramesBrowserState)
from spyder.plugins.debugger.widgets.breakpoint_table_view import (
    BreakpointTableView, BreakpointTableViewActions)
from spyder.plugins.toolbar.api import ApplicationToolbars
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import APP_TOOLBAR_STYLESHEET


# =============================================================================
# ---- Constants
# =============================================================================
class DebuggerWidgetActions:
    # Triggers
    Search = 'search'
    Inspect = 'inspect'
    EnterDebug = 'enter_debug'
    InterrupAndDebug = "interrupt_and_debug"
    Next = "next"
    Continue = "continue"
    Step = "step"
    Return = "return"
    Stop = "stop"
    GotoCursor = "go to editor"

    # Toggles
    ToggleExcludeInternal = 'toggle_exclude_internal_action'


class DebuggerBreakpointActions:
    ToggleBreakpoint = 'toggle breakpoint'
    ToggleConditionalBreakpoint = 'toggle conditional breakpoint'
    ClearAllBreakpoints = 'clear all breakpoints'
    ShowBreakpointsTable = 'show breakpoint table'
    ToggleBreakpointsTable = 'toggle breakpoint table'


class DebuggerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'


class DebuggerWidgetMainToolBarSections:
    Control = 'control_section'
    InteractWithConsole = "interact_with_console_section"
    Extras = "extras_section"


class DebuggerWidgetToolbarItems:
    ToolbarStretcher = 'toolbar_stretcher'


class DebuggerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class DebuggerContextMenuSections:
    Locals = 'locals_section'


# =============================================================================
# ---- Widgets
# =============================================================================
class DebuggerWidget(ShellConnectMainWidget):

    # Signals
    sig_edit_goto = Signal(str, int, str)
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

    sig_breakpoints_saved = Signal()
    """Breakpoints have been saved"""

    sig_toggle_breakpoints = Signal()
    """Add or remove a breakpoint on the current line."""

    sig_toggle_conditional_breakpoints = Signal()
    """Add or remove a conditional breakpoint on the current line."""

    sig_clear_all_breakpoints = Signal()
    """Clear all breakpoints in all files."""

    sig_clear_breakpoint = Signal(str, int)
    """
    Clear single breakpoint.

    Parameters
    ----------
    filename: str
        The filename
    line_number: int
        The line number
    """

    sig_pdb_state_changed = Signal(bool)
    """
    This signal is emitted every time a Pdb interaction happens.

    Parameters
    ----------
    pdb_state: bool
        Whether the debugger is waiting for input
    """

    sig_load_pdb_file = Signal(str, int)
    """
    This signal is emitted when Pdb reaches a new line.

    Parameters
    ----------
    filename: str
        The filename the debugger stepped in
    line_number: int
        The line number the debugger stepped in
    """

    sig_switch_to_plugin_requested = Signal()
    """
    This signal will request to change the focus to the plugin.
    """

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent, set_layout=False)

        # Widgets
        self.breakpoints_table = BreakpointTableView(self, {})
        self.breakpoints_table.hide()

        # Splitter
        self.splitter = QSplitter(self)
        self.splitter.addWidget(self._stack)
        self.splitter.addWidget(self.breakpoints_table)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.setChildrenCollapsible(True)

        # This is necessary so that the border radius is maintained when
        # showing/hiding the breakpoints table
        self.splitter.setStyleSheet(
            f"border-radius: {SpyderPalette.SIZE_BORDER_RADIUS}"
        )

        # To manipulate the control debugger buttons in the Debug toolbar
        self._control_debugger_toolbar_widgets = []
        self._app_toolbar_button_width = (
            int(APP_TOOLBAR_STYLESHEET.BUTTON_WIDTH.split("px")[0])
        )

        # Layout
        # Create the layout.
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.setLayout(layout)

        # Signals
        bpt = self.breakpoints_table
        bpt.sig_clear_all_breakpoints_requested.connect(
            self.sig_clear_all_breakpoints)
        bpt.sig_clear_breakpoint_requested.connect(
            self.sig_clear_breakpoint)
        bpt.sig_edit_goto_requested.connect(self.sig_edit_goto)
        bpt.sig_conditional_breakpoint_requested.connect(
            self.sig_toggle_conditional_breakpoints)
        self.sig_breakpoints_saved.connect(self.set_data)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Debugger')

    def get_focus_widget(self):
        return self.current_widget()

    def setup(self):
        """Setup the widget."""

        self.breakpoints_table.setup()
        self.set_data()

        # ---- Options menu actions
        exclude_internal_action = self.create_action(
            DebuggerWidgetActions.ToggleExcludeInternal,
            text=_("Exclude internal frames when inspecting execution"),
            tip=_("Exclude frames that are not part of the user code"),
            toggled=True,
            option='exclude_internal',
        )

        # ---- Toolbar actions
        search_action = self.create_action(
            DebuggerWidgetActions.Search,
            text=_("Search frames"),
            icon=self.create_icon('find'),
            toggled=self.toggle_finder,
            register_shortcut=True
        )

        inspect_action = self.create_action(
            DebuggerWidgetActions.Inspect,
            text=_("Inspect execution"),
            icon=self.create_icon('show'),
            triggered=self.capture_frames,
            register_shortcut=True,
        )

        enter_debug_action = self.create_action(
            DebuggerWidgetActions.EnterDebug,
            text=_("Start debugging after last error"),
            icon=self.create_icon("postmortem_debug"),
            triggered=self.enter_debugger_after_exception,
            register_shortcut=True,
        )

        interrupt_and_debug_action = self.create_action(
            DebuggerWidgetActions.InterrupAndDebug,
            text=_("Interrupt execution and start the debugger"),
            icon=self.create_icon("interrupt_and_debug"),
            triggered=self.interrupt_and_debug,
            register_shortcut=True,
        )

        next_action = self.create_action(
            DebuggerWidgetActions.Next,
            text=_("Execute current line"),
            icon=self.create_icon('arrow-step-over'),
            triggered=lambda: self.debug_command("next"),
            register_shortcut=True
        )

        continue_action = self.create_action(
            DebuggerWidgetActions.Continue,
            text=_("Continue execution until next breakpoint"),
            icon=self.create_icon('arrow-continue'),
            triggered=lambda: self.debug_command("continue"),
            register_shortcut=True
        )

        step_action = self.create_action(
            DebuggerWidgetActions.Step,
            text=_("Step into function or method"),
            icon=self.create_icon('arrow-step-in'),
            triggered=lambda: self.debug_command("step"),
            register_shortcut=True
        )

        return_action = self.create_action(
            DebuggerWidgetActions.Return,
            text=_("Execute until function or method returns"),
            icon=self.create_icon('arrow-step-out'),
            triggered=lambda: self.debug_command("return"),
            register_shortcut=True
        )

        stop_action = self.create_action(
            DebuggerWidgetActions.Stop,
            text=_("Stop debugging"),
            icon=self.create_icon('stop_debug'),
            triggered=self.stop_debugging,
            register_shortcut=True
        )

        goto_cursor_action = self.create_action(
            DebuggerWidgetActions.GotoCursor,
            text=_(
                "Show the file and line where the debugger is placed in the "
                "editor"
            ),
            icon=self.create_icon("go_to_editor"),
            triggered=self.goto_current_step,
            register_shortcut=True,
        )

        self.create_action(
            DebuggerBreakpointActions.ToggleBreakpoint,
            text=_("Set/Clear breakpoint"),
            tip=_("Set/Clear breakpoint"),
            icon=self.create_icon('breakpoint_big'),
            triggered=self.sig_toggle_breakpoints,
            register_shortcut=True,
        )

        self.create_action(
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
            text=_("Set/Edit conditional breakpoint"),
            tip=_("Set/Edit conditional breakpoint"),
            icon=self.create_icon('breakpoint_cond_big'),
            triggered=self.sig_toggle_conditional_breakpoints,
            register_shortcut=True,
        )

        self.create_action(
            DebuggerBreakpointActions.ClearAllBreakpoints,
            text=_("Clear breakpoints in all files"),
            tip=_("Clear breakpoints in all files"),
            triggered=self.sig_clear_all_breakpoints
        )

        self.create_action(
            DebuggerBreakpointActions.ShowBreakpointsTable,
            _("List breakpoints"),
            triggered=self.list_breakpoints,
        )

        toggle_breakpoints_action = self.create_action(
            DebuggerBreakpointActions.ToggleBreakpointsTable,
            _("Show breakpoints"),
            icon=self.create_icon("list_breakpoints"),
            toggled=True,
            initial=self.get_conf('breakpoints_table_visible'),
            option='breakpoints_table_visible'
        )

        # Options menu
        options_menu = self.get_options_menu()
        for item in [exclude_internal_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=DebuggerWidgetOptionsMenuSections.Display,
            )

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [
            next_action,
            continue_action,
            step_action,
            return_action,
            stop_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=DebuggerWidgetMainToolBarSections.Control,
            )

        for item in [
            enter_debug_action,
            interrupt_and_debug_action,
            inspect_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=DebuggerWidgetMainToolBarSections.InteractWithConsole,
            )

        stretcher = self.create_stretcher(
            DebuggerWidgetToolbarItems.ToolbarStretcher
        )
        for item in [
            goto_cursor_action,
            search_action,
            stretcher,
            toggle_breakpoints_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=DebuggerWidgetMainToolBarSections.Extras,
            )

    def update_actions(self):
        """Update actions."""
        try:
            search_action = self.get_action(DebuggerWidgetActions.Search)
            enter_debug_action = self.get_action(
                DebuggerWidgetActions.EnterDebug
            )
            interrupt_and_debug_action = self.get_action(
                DebuggerWidgetActions.InterrupAndDebug
            )
            inspect_action = self.get_action(
                DebuggerWidgetActions.Inspect
            )

            widget = self.current_widget()
            if self.is_current_widget_empty() or widget is None:
                search_action.setEnabled(False)
                post_mortem = False
                executing = False
                pdb_prompt = False
                is_debugging = False
            else:
                search_action.setEnabled(True)
                search_action.setChecked(widget.finder_is_visible())
                post_mortem = widget.state == FramesBrowserState.Error
                sw = widget.shellwidget
                executing = sw._executing
                pdb_prompt = sw.is_waiting_pdb_input()
                is_debugging = sw.is_debugging()

            enter_debug_action.setEnabled(post_mortem and not executing)
            interrupt_and_debug_action.setEnabled(executing)
            inspect_action.setEnabled(executing)

            for action_name in [
                    DebuggerWidgetActions.Next,
                    DebuggerWidgetActions.Continue,
                    DebuggerWidgetActions.Step,
                    DebuggerWidgetActions.Return,
                    DebuggerWidgetActions.Stop,
                    DebuggerWidgetActions.GotoCursor]:
                action = self.get_action(action_name)
                action.setEnabled(pdb_prompt)

            self._set_visible_control_debugger_buttons(
                pdb_prompt or is_debugging
            )

            rows = self.breakpoints_table.selectionModel().selectedRows()
            initial_row = rows[0] if rows else None

            enabled = (
                bool(self.breakpoints_table.model.breakpoints)
                and initial_row is not None
            )
            clear_action = self.get_action(
                BreakpointTableViewActions.ClearBreakpoint)
            edit_action = self.get_action(
                BreakpointTableViewActions.EditBreakpoint)
            clear_action.setEnabled(enabled)
            edit_action.setEnabled(enabled)
        except RuntimeError:
            pass

    @on_conf_change(option='breakpoints_table_visible')
    def on_breakpoints_table_option_update(self, value):
        action = self.get_action(
            DebuggerBreakpointActions.ToggleBreakpointsTable)

        if value:
            self.breakpoints_table.show()
            action.setToolTip(_("Hide breakpoints"))
            action.setText(_("Hide breakpoints"))
            self._update_stylesheet(is_table_shown=True)
        else:
            self.breakpoints_table.hide()
            action.setToolTip(_("Show breakpoints"))
            action.setText(_("Show breakpoints"))
            self._update_stylesheet(is_table_shown=False)

    # ---- ShellConnectMainWidget API
    # ------------------------------------------------------------------------
    def create_new_widget(self, shellwidget):
        """Create a new widget."""
        widget = FramesBrowser(self, shellwidget=shellwidget)

        widget.sig_edit_goto.connect(self.sig_edit_goto)
        widget.sig_hide_finder_requested.connect(self.hide_finder)
        widget.sig_update_actions_requested.connect(self.update_actions)

        shellwidget.sig_prompt_ready.connect(widget.clear_if_needed)
        shellwidget.sig_pdb_prompt_ready.connect(widget.clear_if_needed)

        shellwidget.sig_prompt_ready.connect(self.update_actions)
        shellwidget.sig_pdb_prompt_ready.connect(self.update_actions)
        shellwidget.executing.connect(self.update_actions)

        shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "show_traceback", widget.show_exception)
        shellwidget.sig_pdb_stack.connect(widget.set_from_pdb)
        shellwidget.sig_config_spyder_kernel.connect(
            widget.on_config_kernel)

        widget.setup()

        self.sig_breakpoints_saved.connect(widget.set_breakpoints)

        shellwidget.sig_pdb_state_changed.connect(self.sig_pdb_state_changed)
        shellwidget.sig_pdb_step.connect(widget.pdb_has_stopped)

        widget.sig_load_pdb_file.connect(self.sig_load_pdb_file)

        return widget

    def switch_widget(self, widget, old_widget):
        """Set the current FramesBrowser."""
        if not self.is_current_widget_empty():
            sw = widget.shellwidget
            state = sw.is_waiting_pdb_input()
            self.sig_pdb_state_changed.emit(state)

    def close_widget(self, widget):
        """Close widget."""
        widget.sig_edit_goto.disconnect(self.sig_edit_goto)
        widget.sig_hide_finder_requested.disconnect(self.hide_finder)
        widget.sig_update_actions_requested.disconnect(self.update_actions)

        shellwidget = widget.shellwidget

        try:
            shellwidget.sig_prompt_ready.disconnect(widget.clear_if_needed)
            shellwidget.sig_prompt_ready.disconnect(self.update_actions)
        except (TypeError, RuntimeError):
            # disconnect was called elsewhere without argument
            pass

        shellwidget.sig_pdb_prompt_ready.disconnect(widget.clear_if_needed)
        shellwidget.sig_pdb_prompt_ready.disconnect(self.update_actions)
        shellwidget.executing.disconnect(self.update_actions)

        shellwidget.kernel_handler.kernel_comm.unregister_call_handler(
            "show_traceback")
        shellwidget.sig_pdb_stack.disconnect(widget.set_from_pdb)
        shellwidget.sig_config_spyder_kernel.disconnect(
            widget.on_config_kernel)
        widget.on_unconfig_kernel()
        self.sig_breakpoints_saved.disconnect(widget.set_breakpoints)
        shellwidget.sig_pdb_state_changed.disconnect(
            self.sig_pdb_state_changed)

        shellwidget.sig_pdb_step.disconnect(widget.pdb_has_stopped)
        widget.sig_load_pdb_file.disconnect(self.sig_load_pdb_file)

        widget.close()
        widget.setParent(None)

    # ---- Public API
    # ------------------------------------------------------------------------
    def goto_current_step(self):
        """Go to last pdb step."""
        fname, lineno = self.get_pdb_last_step()
        if fname:
            self.sig_load_pdb_file.emit(fname, lineno)

    def print_debug_file_msg(self):
        """Print message in the current console when a file can't be closed."""
        widget = self.current_widget()
        if widget is None:
            return False
        sw = widget.shellwidget
        debug_msg = _('The current file cannot be closed because it is '
                      'in debug mode.')
        sw.append_html_message(debug_msg, before_prompt=True)

    def set_pdb_take_focus(self, take_focus):
        """
        Set whether current Pdb session should take focus when stopping on the
        next call.
        """
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return False
        widget.shellwidget._pdb_take_focus = take_focus

    @Slot(bool)
    def toggle_finder(self, checked):
        """Show or hide finder."""
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return
        widget.toggle_finder(checked)

    def get_pdb_state(self):
        """Get debugging state of the current console."""
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return False
        sw = widget.shellwidget
        if sw is not None:
            return sw.is_waiting_pdb_input()
        return False

    def get_pdb_last_step(self):
        """Get last pdb step of the current console."""
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return None, None
        sw = widget.shellwidget
        if sw is not None:
            return sw.get_pdb_last_step()
        return None, None

    @Slot()
    def hide_finder(self):
        """Hide finder."""
        action = self.get_action(DebuggerWidgetActions.Search)
        action.setChecked(False)

    def enter_debugger_after_exception(self):
        """Enter the debugger after an exception."""
        widget = self.current_widget()
        if widget is None:
            return

        # Enter the debugger
        sw = widget.shellwidget
        if widget.state == FramesBrowserState.Error:
            # Debug the last exception
            sw.execute("%debug")
            return

    def interrupt_and_debug(self):
        """
        If the shell is executing, interrupt execution and enter debugger.
        """
        widget = self.current_widget()
        if widget is None:
            return

        # Enter the debugger
        sw = widget.shellwidget
        if sw._executing:
            sw.call_kernel(
                interrupt=True, callback=widget.show_pdb_preview
                ).get_current_frames(
                    ignore_internal_threads=True
                )

            sw.call_kernel(interrupt=True).request_pdb_stop()
            return

    def capture_frames(self):
        """Refresh frames table"""
        widget = self.current_widget()
        if widget is None:
            return
        if widget.shellwidget.is_waiting_pdb_input():
            # Disabled while waiting pdb input as the pdb stack is shown
            return
        widget.shellwidget.call_kernel(
            interrupt=True, callback=widget.show_captured_frames
            ).get_current_frames(
                ignore_internal_threads=self.get_conf("exclude_internal")
            )

    def stop_debugging(self):
        """Stop debugging"""
        self.sig_unmaximize_plugin_requested.emit()
        widget = self.current_widget()
        if widget is None:
            return
        widget.shellwidget.stop_debugging()

    def debug_command(self, command):
        """Debug actions"""
        self.sig_unmaximize_plugin_requested.emit()
        widget = self.current_widget()
        if widget is None:
            return
        widget.shellwidget.pdb_execute_command(command)

    def load_data(self):
        """
        Load breakpoint data from configuration file.
        """
        breakpoints_dict = self.get_conf(
            "breakpoints",
            default={},
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
            data = self.load_data()
        self.breakpoints_table.set_data(data)

    def list_breakpoints(self):
        """Show breakpoints state and switch to plugin."""
        self.set_conf('breakpoints_table_visible', True)
        self.sig_switch_to_plugin_requested.emit()

    def update_splitter_widths(self, base_width):
        """
        Update the splitter widths to provide the breakpoints table with a
        reasonable initial width.

        Parameters
        ----------
        base_width: int
            The available widget width.
        """
        if (base_width // 3) > self.breakpoints_table.MIN_INITIAL_WIDTH:
            table_width = base_width // 3
        else:
            table_width = self.breakpoints_table.MIN_INITIAL_WIDTH

        if base_width - table_width > 0:
            self.splitter.setSizes([base_width - table_width, table_width])

    def on_debug_toolbar_rendered(self):
        """Actions to take when the Debug toolbar is rendered."""
        debug_toolbar = self.get_toolbar(
            ApplicationToolbars.Debug, plugin=Plugins.Toolbar
        )

        # Get widgets corresponding to control debugger actions in the Debug
        # toolbar
        for action_id in [
            DebuggerWidgetActions.Next,
            DebuggerWidgetActions.Step,
            DebuggerWidgetActions.Return,
            DebuggerWidgetActions.Continue,
            DebuggerWidgetActions.Stop,
        ]:
            action = self.get_action(action_id)
            widget = debug_toolbar.widgetForAction(action)

            # Hide widgets by default because no debugging session is
            # active at startup
            widget.setFixedWidth(0)

            # Save widgets in this list to manipulate them later
            self._control_debugger_toolbar_widgets.append(widget)

    # ---- Private API
    # ------------------------------------------------------------------------
    def _update_stylesheet(self, is_table_shown=False):
        """Update stylesheet when the breakpoints table is shown/hidden."""
        # Remove right border radius for stack when table is shown and restore
        # it when hidden.
        if is_table_shown:
            border_radius = '0px'
        else:
            border_radius = SpyderPalette.SIZE_BORDER_RADIUS

        css = qstylizer.style.StyleSheet()
        css.setValues(
            borderTopRightRadius=f'{border_radius}',
            borderBottomRightRadius=f'{border_radius}',
        )
        self._stack.setStyleSheet(css.toString())

    def _set_visible_control_debugger_buttons(self, visible: bool):
        """Show/hide control debugger buttons in the Debug toolbar."""
        for widget in self._control_debugger_toolbar_widgets:
            if visible:
                widget.setFixedWidth(self._app_toolbar_button_width)
            else:
                widget.setFixedWidth(0)

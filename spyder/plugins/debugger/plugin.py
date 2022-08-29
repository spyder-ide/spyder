# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Debugger Plugin."""

# Third-party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.config.base import _
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.plugins.debugger.confpage import DebuggerConfigPage
from spyder.plugins.debugger.widgets.main_widget import (
    DebuggerWidget, DebuggerWidgetActions)
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.utils.qthelpers import MENU_SEPARATOR
from spyder.config.manager import CONF
from spyder.plugins.mainmenu.api import ApplicationMenus
from spyder.plugins.debugger.utils.breakpointsmanager import (
    BreakpointsManager, clear_all_breakpoints, clear_breakpoint)


class Debugger(SpyderDockablePlugin, ShellConnectMixin):
    """Debugger plugin."""

    NAME = 'debugger'
    REQUIRES = [Plugins.IPythonConsole, Plugins.Preferences]
    OPTIONAL = [Plugins.Editor, Plugins.VariableExplorer, Plugins.MainMenu]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = DebuggerWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = DebuggerConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Debugger')

    def get_description(self):
        return _('Display and explore frames while debugging.')

    def get_icon(self):
        return self.create_icon('dictedit')

    def on_initialize(self):
        pass

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()

        # The editor is avilable, connect signal.
        widget.edit_goto.connect(editor.load)
        widget.sig_debug_file.connect(self.debug_file)
        widget.sig_debug_cell.connect(self.debug_cell)
        widget.sig_toggle_breakpoints.connect(self.set_or_clear_breakpoint)
        widget.sig_toggle_conditional_breakpoints.connect(
            self.set_or_edit_conditional_breakpoint)
        widget.sig_clear_all_breakpoints.connect(self.clear_all_breakpoints)

        editor.sig_codeeditor_created.connect(self.add_codeeditor)
        editor.sig_codeeditor_changed.connect(self.update_codeeditor)
        editor.sig_codeeditor_deleted.connect(self.remove_codeeditor)

        # Apply shortcuts to editor and add actions to pythonfile list
        editor_shortcuts = [
            DebuggerWidgetActions.DebugCurrentFile,
            DebuggerWidgetActions.DebugCurrentCell,
            DebuggerWidgetActions.ToggleBreakpoint,
            DebuggerWidgetActions.ToggleConditionalBreakpoint,
        ]
        for name in editor_shortcuts:
            action = widget.get_action(name)
            CONF.config_shortcut(
                action.trigger,
                context=self.CONF_SECTION,
                name=name,
                parent=editor)
            editor.pythonfile_dependent_actions += [action]

        # Add buttons to toolbar
        for name in [
                DebuggerWidgetActions.DebugCurrentFile,
                DebuggerWidgetActions.DebugCurrentCell]:
            action = widget.get_action(name)
            self.main.debug_toolbar_actions += [action]

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()

        widget.edit_goto.disconnect(editor.load)
        widget.sig_debug_file.disconnect(self.debug_file)
        widget.sig_debug_cell.disconnect(self.debug_cell)
        widget.sig_toggle_breakpoints.disconnect(self.set_or_clear_breakpoint)
        widget.sig_toggle_conditional_breakpoints.disconnect(
            self.set_or_edit_conditional_breakpoint)
        widget.sig_clear_all_breakpoints.disconnect(self.clear_all_breakpoints)

        editor.sig_codeeditor_created.disconnect(self.add_codeeditor)
        editor.sig_codeeditor_changed.disconnect(self.update_codeeditor)
        editor.sig_codeeditor_deleted.disconnect(self.remove_codeeditor)

        # Remove editor actions
        editor_shortcuts = [
            DebuggerWidgetActions.DebugCurrentFile,
            DebuggerWidgetActions.DebugCurrentCell,
            DebuggerWidgetActions.ToggleBreakpoint,
            DebuggerWidgetActions.ToggleConditionalBreakpoint,
        ]
        for name in editor_shortcuts:
            action = widget.get_action(name)
            editor.pythonfile_dependent_actions.remove(action)

        # Remove buttons from toolbar
        names = [
            DebuggerWidgetActions.DebugCurrentFile,
            DebuggerWidgetActions.DebugCurrentCell,
            ]
        for name in names:
            action = widget.get_action(name)
            self.main.debug_toolbar_actions.remove(action)

    @on_plugin_available(plugin=Plugins.VariableExplorer)
    def on_variable_explorer_available(self):
        self.get_widget().sig_show_namespace.connect(
            self.show_namespace_in_variable_explorer)

    @on_plugin_teardown(plugin=Plugins.VariableExplorer)
    def on_variable_explorer_teardown(self):
        self.get_widget().sig_show_namespace.disconnect(
            self.show_namespace_in_variable_explorer)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        widget = self.get_widget()
        names = [
            DebuggerWidgetActions.DebugCurrentFile,
            DebuggerWidgetActions.DebugCurrentCell,
            MENU_SEPARATOR,
            DebuggerWidgetActions.ToggleBreakpoint,
            DebuggerWidgetActions.ToggleConditionalBreakpoint,
            DebuggerWidgetActions.ClearAllBreakpoints,
            MENU_SEPARATOR,
            ]

        debug_menu_actions = []

        for name in names:
            if name is MENU_SEPARATOR:
                action = name
            else:
                action = widget.get_action(name)
            debug_menu_actions.append(action)

        self.main.debug_menu_actions = (
            debug_menu_actions + self.main.debug_menu_actions)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        names = [
            DebuggerWidgetActions.DebugCurrentFile,
            DebuggerWidgetActions.DebugCurrentCell,
            DebuggerWidgetActions.ToggleBreakpoint,
            DebuggerWidgetActions.ToggleConditionalBreakpoint,
            DebuggerWidgetActions.ClearAllBreakpoints
            ]
        for name in names:
            mainmenu.remove_item_from_application_menu(
                name,
                menu_id=ApplicationMenus.Debug
            )

    # ---- Public API
    # ------------------------------------------------------------------------
    @Slot()
    def debug_file(self):
        """
        Debug current script.
        Should only be called when an editor is avilable.
        """
        editor = self.get_plugin(Plugins.Editor)
        editor.switch_to_plugin()
        editor.run_file(method="debugfile")

    @Slot()
    def debug_cell(self):
        '''
        Debug Current cell.
        Should only be called when an editor is avilable.
        '''
        editor = self.get_plugin(Plugins.Editor)
        editor.run_cell(method="debugcell")

    def show_namespace_in_variable_explorer(self, namespace, shellwidget):
        """
        Find the right variable explorer widget and show the namespace.

        This should only be called when there is a Variable explorer
        """
        variable_explorer = self.get_plugin(Plugins.VariableExplorer)
        if variable_explorer is None:
            return
        nsb = variable_explorer.get_widget_for_shellwidget(shellwidget)
        nsb.process_remote_view(namespace)

    def add_shellwidget(self, shellwidget):
        """
        Add a new shellwidget to be registered.

        This function registers a new widget to display content that
        comes from shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        super().add_shellwidget(shellwidget)
        self.get_widget().sig_breakpoints_saved.connect(
            shellwidget.set_breakpoints)
        shellwidget.sig_pdb_state_changed.connect(
            self.update_current_codeeditor_pdb_state)

    def remove_shellwidget(self, shellwidget):
        """
        Remove the registered shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        super().remove_shellwidget(shellwidget)
        self.get_widget().sig_breakpoints_saved.disconnect(
            shellwidget.set_breakpoints)
        shellwidget.sig_pdb_state_changed.disconnect(
            self.update_current_codeeditor_pdb_state)

    def add_codeeditor(self, codeeditor):
        codeeditor.breakpoints_manager = BreakpointsManager(codeeditor)
        codeeditor.breakpoints_manager.sig_breakpoints_saved.connect(
            self.get_widget().sig_breakpoints_saved)

    def remove_codeeditor(self, codeeditor):
        codeeditor.breakpoints_manager.sig_breakpoints_saved.disconnect(
            self.get_widget().sig_breakpoints_saved)
        codeeditor.breakpoints_manager = None

    def update_current_codeeditor_pdb_state(self, pdb_state, pdb_last_step):
        current_editor = self.get_current_editor()
        if current_editor is None:
            return
        current_editor.breakpoints_manager.update_pdb_state(
            pdb_state, pdb_last_step)

    def update_codeeditor(self, codeeditor):
        if codeeditor.filename is None:
            # Not setup yet
            return
        # Update debugging state
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        if ipyconsole is None:
            return
        pdb_state = ipyconsole.get_pdb_state()
        pdb_last_step = ipyconsole.get_pdb_last_step()
        codeeditor.breakpoints_manager.update_pdb_state(
            pdb_state, pdb_last_step)

    def get_current_editor(self):
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None
        return editor.get_current_editor()

    def get_current_editorstack(self):
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None
        return editor.get_current_editorstack()

    @Slot()
    def set_or_clear_breakpoint(self):
        """Set/Clear breakpoint"""
        current_editor = self.get_current_editor()
        if current_editor is None:
            return
        current_editor.breakpoints_manager.toogle_breakpoint()

    @Slot()
    def set_or_edit_conditional_breakpoint(self):
        """Set/Edit conditional breakpoint"""
        current_editor = self.get_current_editor()
        if current_editor is None:
            return
        current_editor.breakpoints_manager.toogle_breakpoint(
            edit_condition=True)

    @Slot()
    def clear_all_breakpoints(self):
        """Clear breakpoints in all files"""
        clear_all_breakpoints()
        self.get_widget().sig_breakpoints_saved.emit()

        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            for data in editorstack.data:
                data.editor.breakpoints_manager.clear_breakpoints()

    def clear_breakpoint(self, filename, lineno):
        """Remove a single breakpoint"""
        clear_breakpoint(filename, lineno)
        self.get_widget().sig_breakpoints_saved.emit()

        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None

        editorstack = editor.get_current_editorstack()
        if editorstack is not None:
            index = editor.is_file_opened(filename)
            if index is not None:
                editorstack.data[
                    index].editor.breakpoints_manager.toogle_breakpoint(lineno)

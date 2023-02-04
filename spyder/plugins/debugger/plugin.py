# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Debugger Plugin."""

# Standard library imports
import os.path as osp

# Third-party imports
from qtpy.QtCore import Slot

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.translations import get_translation
from spyder.config.manager import CONF
from spyder.plugins.debugger.confpage import DebuggerConfigPage
from spyder.plugins.debugger.utils.breakpointsmanager import (
    BreakpointsManager, clear_all_breakpoints, clear_breakpoint)
from spyder.plugins.debugger.widgets.main_widget import (
    DebuggerBreakpointActions, DebuggerToolbarActions, DebuggerWidget,
    DebuggerWidgetActions)
from spyder.plugins.editor.utils.editor import get_file_language
from spyder.plugins.editor.utils.languages import ALL_LANGUAGES
from spyder.plugins.ipythonconsole.api import IPythonConsolePyConfiguration
from spyder.plugins.mainmenu.api import ApplicationMenus, DebugMenuSections
from spyder.plugins.run.api import (
    WorkingDirOpts, WorkingDirSource, RunExecutionParameters,
    ExtendedRunExecutionParameters)
from spyder.plugins.toolbar.api import ApplicationToolbars


# Localization
_ = get_translation("spyder")


class Debugger(SpyderDockablePlugin, ShellConnectMixin):
    """Debugger plugin."""

    NAME = 'debugger'
    REQUIRES = [Plugins.IPythonConsole, Plugins.Preferences]
    OPTIONAL = [Plugins.Editor, Plugins.MainMenu, Plugins.Toolbar,
                Plugins.VariableExplorer]
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
        widget = self.get_widget()
        widget.sig_pdb_state_changed.connect(
            self._update_current_codeeditor_pdb_state)
        widget.sig_debug_file.connect(self.debug_file)
        widget.sig_debug_cell.connect(self.debug_cell)
        widget.sig_debug_selection.connect(self.debug_selection)
        widget.sig_toggle_breakpoints.connect(self._set_or_clear_breakpoint)
        widget.sig_toggle_conditional_breakpoints.connect(
            self._set_or_edit_conditional_breakpoint)
        widget.sig_clear_all_breakpoints.connect(self.clear_all_breakpoints)

        widget.sig_load_pdb_file.connect(
            self._load_pdb_file_in_editor)

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

        # The editor is available, connect signals.
        widget.sig_edit_goto.connect(editor.load)
        editor.sig_codeeditor_created.connect(self._add_codeeditor)
        editor.sig_codeeditor_changed.connect(self._update_codeeditor)
        editor.sig_codeeditor_deleted.connect(self._remove_codeeditor)

        # Apply shortcuts to editor and add actions to pythonfile list
        editor_shortcuts = [
            DebuggerToolbarActions.DebugCurrentFile,
            DebuggerToolbarActions.DebugCurrentCell,
            DebuggerToolbarActions.DebugCurrentSelection,
            DebuggerBreakpointActions.ToggleBreakpoint,
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
        ]
        for name in editor_shortcuts:
            action = self.get_action(name)
            CONF.config_shortcut(
                action.trigger,
                context=self.CONF_SECTION,
                name=name,
                parent=editor
            )
            editor.pythonfile_dependent_actions += [action]

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        widget = self.get_widget()

        widget.sig_edit_goto.disconnect(editor.load)

        editor.sig_codeeditor_created.disconnect(self._add_codeeditor)
        editor.sig_codeeditor_changed.disconnect(self._update_codeeditor)
        editor.sig_codeeditor_deleted.disconnect(self._remove_codeeditor)

        # Remove editor actions
        editor_shortcuts = [
            DebuggerToolbarActions.DebugCurrentFile,
            DebuggerToolbarActions.DebugCurrentCell,
            DebuggerToolbarActions.DebugCurrentSelection,
            DebuggerBreakpointActions.ToggleBreakpoint,
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
        ]
        for name in editor_shortcuts:
            action = self.get_action(name)
            editor.pythonfile_dependent_actions.remove(action)

    @on_plugin_available(plugin=Plugins.VariableExplorer)
    def on_variable_explorer_available(self):
        self.get_widget().sig_show_namespace.connect(
            self._show_namespace_in_variable_explorer)

    @on_plugin_teardown(plugin=Plugins.VariableExplorer)
    def on_variable_explorer_teardown(self):
        self.get_widget().sig_show_namespace.disconnect(
            self._show_namespace_in_variable_explorer)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        # StartDebug section
        for action in [DebuggerToolbarActions.DebugCurrentFile,
                       DebuggerToolbarActions.DebugCurrentCell,
                       DebuggerToolbarActions.DebugCurrentSelection]:
            mainmenu.add_item_to_application_menu(
                self.get_action(action),
                menu_id=ApplicationMenus.Debug,
                section=DebugMenuSections.StartDebug,
                before_section=DebugMenuSections.ControlDebug)

        # ControlDebug section
        for action in [DebuggerWidgetActions.Next,
                       DebuggerWidgetActions.Step,
                       DebuggerWidgetActions.Return,
                       DebuggerWidgetActions.Continue,
                       DebuggerWidgetActions.Stop]:
            mainmenu.add_item_to_application_menu(
                self.get_action(action),
                menu_id=ApplicationMenus.Debug,
                section=DebugMenuSections.ControlDebug,
                before_section=DebugMenuSections.EditBreakpoints)

        # Breakpoints section
        for action in [DebuggerBreakpointActions.ToggleBreakpoint,
                       DebuggerBreakpointActions.ToggleConditionalBreakpoint,
                       DebuggerBreakpointActions.ClearAllBreakpoints]:
            mainmenu.add_item_to_application_menu(
                self.get_action(action),
                menu_id=ApplicationMenus.Debug,
                section=DebugMenuSections.EditBreakpoints,
                before_section=DebugMenuSections.ListBreakpoints)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        names = [
            DebuggerToolbarActions.DebugCurrentFile,
            DebuggerToolbarActions.DebugCurrentCell,
            DebuggerToolbarActions.DebugCurrentSelection,
            DebuggerWidgetActions.Next,
            DebuggerWidgetActions.Step,
            DebuggerWidgetActions.Return,
            DebuggerWidgetActions.Continue,
            DebuggerWidgetActions.Stop,
            DebuggerBreakpointActions.ToggleBreakpoint,
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
            DebuggerBreakpointActions.ClearAllBreakpoints
        ]
        for name in names:
            mainmenu.remove_item_from_application_menu(
                name,
                menu_id=ApplicationMenus.Debug
            )

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        toolbar = self.get_plugin(Plugins.Toolbar)

        for action in [DebuggerToolbarActions.DebugCurrentFile,
                       DebuggerToolbarActions.DebugCurrentCell,
                       DebuggerToolbarActions.DebugCurrentSelection]:
            toolbar.add_item_to_application_toolbar(
                self.get_action(action),
                toolbar_id=ApplicationToolbars.Debug
            )

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)

        for action in [DebuggerToolbarActions.DebugCurrentFile,
                       DebuggerToolbarActions.DebugCurrentCell,
                       DebuggerToolbarActions.DebugCurrentSelection]:
            toolbar.remove_item_from_application_toolbar(
                action,
                toolbar_id=ApplicationToolbars.Debug
            )

    # ---- Private API
    # ------------------------------------------------------------------------
    def _load_pdb_file_in_editor(self, fname, lineno):
        """Load file using processevents."""
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return

        # Prevent keyboard input from accidentally entering the
        # editor during repeated, rapid entry of debugging commands.
        editor.load(fname, lineno, processevents=False)

    def _show_namespace_in_variable_explorer(self, namespace, shellwidget):
        """
        Find the right variable explorer widget and show the namespace.

        This should only be called when there is a Variable explorer
        """
        variable_explorer = self.get_plugin(Plugins.VariableExplorer)
        if variable_explorer is None:
            return
        nsb = variable_explorer.get_widget_for_shellwidget(shellwidget)
        nsb.process_remote_view(namespace)

    def _is_python_editor(self, codeeditor):
        """Check if the editor is a python editor."""
        if codeeditor.filename is None:
            return False
        txt = codeeditor.get_text_with_eol()
        language = get_file_language(codeeditor.filename, txt)
        return language.lower() in ALL_LANGUAGES["Python"]

    def _connect_codeeditor(self, codeeditor):
        """Connect a code editor."""
        codeeditor.breakpoints_manager = BreakpointsManager(codeeditor)
        codeeditor.breakpoints_manager.sig_breakpoints_saved.connect(
            self.get_widget().sig_breakpoints_saved)

    def _disconnect_codeeditor(self, codeeditor):
        """Connect a code editor."""
        codeeditor.breakpoints_manager.sig_breakpoints_saved.disconnect(
            self.get_widget().sig_breakpoints_saved)
        codeeditor.breakpoints_manager = None

    @Slot(str)
    def _filename_changed(self, filename):
        """Change filename."""
        codeeditor = self._get_editor_for_filename(filename)
        if codeeditor is None:
            return

        if codeeditor.breakpoints_manager is None:
            # Was not a python editor
            if self._is_python_editor(codeeditor):
                self._connect_codeeditor(codeeditor)
        else:
            # Was a python editor
            if self._is_python_editor(codeeditor):
                codeeditor.breakpoints_manager.set_filename(filename)
            else:
                self._disconnect_codeeditor(codeeditor)

    @Slot(object)
    def _add_codeeditor(self, codeeditor):
        """
        Add a new codeeditor.
        """
        codeeditor.sig_filename_changed.connect(self._filename_changed)
        codeeditor.breakpoints_manager = None
        if self._is_python_editor(codeeditor):
            self._connect_codeeditor(codeeditor)

    @Slot(object)
    def _remove_codeeditor(self, codeeditor):
        """
        Remove a codeeditor.
        """
        codeeditor.sig_filename_changed.disconnect(self._filename_changed)
        if codeeditor.breakpoints_manager is not None:
            self._disconnect_codeeditor(codeeditor)

    @Slot(object)
    def _update_codeeditor(self, codeeditor):
        """
        Focus codeeditor has changed.
        """
        if (
            codeeditor.filename is None or
            codeeditor.breakpoints_manager is None
        ):
            return

        # Update debugging state
        widget = self.get_widget()
        pdb_state = widget.get_pdb_state()
        filename, lineno = widget.get_pdb_last_step()
        codeeditor.breakpoints_manager.update_pdb_state(
            pdb_state, filename, lineno)

    @Slot(bool)
    def _update_current_codeeditor_pdb_state(self, pdb_state):
        """
        The pdb state has changed.
        """
        codeeditor = self._get_current_editor()
        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return
        filename, line_number = self.get_widget().get_pdb_last_step()
        codeeditor.breakpoints_manager.update_pdb_state(
            pdb_state, filename, line_number)

    def _get_current_editor(self):
        """
        Get current codeeditor.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None
        return editor.get_current_editor()

    def _get_editor_for_filename(self, filename):
        """Get editor for filename."""
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None
        return editor._get_editor(filename)

    def _get_current_editorstack(self):
        """
        Get current editorstack.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor is None:
            return None
        return editor.get_current_editorstack()

    @Slot()
    def _set_or_clear_breakpoint(self):
        """Set/Clear breakpoint"""
        codeeditor = self._get_current_editor()
        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return
        codeeditor.breakpoints_manager.toogle_breakpoint()

    @Slot()
    def _set_or_edit_conditional_breakpoint(self):
        """Set/Edit conditional breakpoint"""
        codeeditor = self._get_current_editor()
        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return
        codeeditor.breakpoints_manager.toogle_breakpoint(
            edit_condition=True)

    # ---- Public API
    # ------------------------------------------------------------------------
    @Slot()
    def debug_file(self):
        """
        Debug current file.

        It should only be called when an editor is available.
        """
        editor = self.get_plugin(Plugins.Editor, error=False)
        if not editor:
            return

        editor.switch_to_plugin()

        # TODO: This is a temporary measure to debug files whilst the debug API
        # is defined.
        current_fname = editor.get_current_filename()
        fname_uuid = editor.id_per_file[current_fname]
        run_conf = editor.get_run_configuration(fname_uuid)
        fname_params = self.main.run.get_last_used_executor_parameters(
            fname_uuid)
        selected = None
        if fname_params['executor'] == self.main.ipyconsole.NAME:
            selected = fname_params['selected']
        if selected is None:
            ipy_params = IPythonConsolePyConfiguration(
                current=True, post_mortem=False,
                python_args_enabled=False, python_args='',
                clear_namespace=False, console_namespace=False)
            wdir_opts = WorkingDirOpts(
                source=WorkingDirSource.CurrentDirectory,
                path=osp.dirname(current_fname))

            exec_conf = RunExecutionParameters(
                working_dir=wdir_opts, executor_params=ipy_params)
            ext_exec_conf = ExtendedRunExecutionParameters(
                uuid=None, name=None, params=exec_conf)
        else:
            run_plugin = self.main.run
            all_exec_conf = run_plugin.get_executor_configuration_parameters(
                self.main.ipyconsole.NAME, 'py', RunContext.File
            )
            all_exec_conf = all_exec_conf['params']
            ext_exec_conf = all_exec_conf[selected]

        ext_exec_conf['params']['executor_params']['debug'] = True
        self.main.run.run_configuration(
            self.main.ipyconsole.NAME, run_conf, ext_exec_conf)

    @Slot()
    def debug_cell(self):
        """
        Debug current cell.

        It should only be called when an editor is available.
        """
        editor = self.get_plugin(Plugins.Editor, error=False)
        if editor:
            editor.run_cell(method="debugcell")

    @Slot()
    def debug_selection(self):
        """
        Debug current selection or line.

        It should only be called when an editor is available.
        """
        # FIXME: This is broken!
        editor = self.get_plugin(Plugins.Editor, error=False)
        if editor:
            editor.run_selection(prefix="%%debug\n")

    @Slot()
    def clear_all_breakpoints(self):
        """Clear breakpoints in all files"""
        clear_all_breakpoints()
        self.get_widget().sig_breakpoints_saved.emit()

        editorstack = self._get_current_editorstack()
        if editorstack is not None:
            for data in editorstack.data:
                if data.editor.breakpoints_manager is not None:
                    data.editor.breakpoints_manager.clear_breakpoints()

    @Slot(str, int)
    def clear_breakpoint(self, filename, lineno):
        """Remove a single breakpoint"""
        clear_breakpoint(filename, lineno)
        self.get_widget().sig_breakpoints_saved.emit()

        codeeditor = self._get_editor_for_filename(filename)

        if codeeditor is None or codeeditor.breakpoints_manager is None:
            return None

        codeeditor.breakpoints_manager.toogle_breakpoint(lineno)

    def can_close_file(self, filename=None):
        """
        Check if a file can be closed taking into account debugging state.
        """
        if not self.get_conf('pdb_prevent_closing'):
            return True

        widget = self.get_widget()

        debugging = widget.get_pdb_state()
        if not debugging:
            return True

        pdb_fname, __ = widget.get_pdb_last_step()

        if pdb_fname and filename:
            if osp.normcase(pdb_fname) == osp.normcase(filename):
                widget.print_debug_file_msg()
                return False
            return True

        widget.print_debug_file_msg()
        return False

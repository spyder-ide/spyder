# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console plugin based on QtConsole.
"""

# Standard library imports
import os
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.translations import get_translation
from spyder.config.base import get_conf_path
from spyder.plugins.ipythonconsole.confpage import IPythonConsoleConfigPage
from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget)
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, ConsolesMenuSections, HelpMenuSections)
from spyder.utils.programs import get_temp_dir

# Localization
_ = get_translation('spyder')


class IPythonConsole(SpyderDockablePlugin):
    """
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget
    """

    # This is required for the new API
    NAME = 'ipython_console'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [Plugins.Editor, Plugins.History, Plugins.MainMenu]
    TABIFY = [Plugins.History]
    WIDGET_CLASS = IPythonConsoleWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = IPythonConsoleConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # Signals
    sig_append_to_history_requested = Signal(str, str)
    """
    This signal is emitted when the plugin requires to add commands to a
    history file.
    Parameters
    ----------
    filename: str
        History file filename.
    text: str
        Text to append to the history file.
    """

    sig_history_requested = Signal(str)
    """
    This signal is emitted when the plugin wants a specific history file
    to be shown.
    """

    sig_focus_changed = Signal()
    """
    This signal is emitted when the plugin focus changes.
    """

    sig_edit_goto_requested = Signal((str, int, str), (str, int, str, bool))
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

    sig_pdb_state_changed = Signal(bool, dict)
    """
    This signal is emitted when the debugging state changes.
    Parameters
    ----------
    waiting_pdb_input: bool
        If the debugging session is waiting for input.
    pdb_last_step: dict
        Dictionary with the information of the last step done
        in the debugging session.
    """

    sig_shellwidget_created = Signal(object)
    """
    This signal is emitted when a shellwidget is connected to
    a kernel.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_shellwidget_deleted = Signal(object)
    """
    This signal is emitted when a shellwidget is disconnected from
    a kernel.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_shellwidget_changed = Signal(object)
    """
    This signal is emitted when the current shellwidget changes.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_external_spyder_kernel_connected = Signal(object)
    """
    This signal is emitted when we connect to an external Spyder kernel.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet that was connected to the kernel.
    """

    sig_render_plain_text_requested = Signal(str)
    """
    This signal is emitted to request a plain text help render.

    Parameters
    ----------
    plain_text: str
        The plain text to render.
    """

    sig_render_rich_text_requested = Signal(str, bool)
    """
    This signal is emitted to request a rich text help render.

    Parameters
    ----------
    rich_text: str
        The rich text.
    collapse: bool
        If the text contains collapsed sections, show them closed (True) or
        open (False).
    """

    sig_help_requested = Signal(dict)
    """
    This signal is emitted to request help on a given object `name`.

    Parameters
    ----------
    help_data: dict
        Example `{'name': str, 'ignore_unknown': bool}`.
    """

    sig_current_directory_changed = Signal(str)
    """
    This signal is emitted when the current directory of the active shell
    widget has changed.

    Parameters
    ----------
    working_directory: str
        The new working directory path.
    """

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('IPython console')

    def get_description(self):
        return _('IPython console')

    def get_icon(self):
        return self.create_icon('ipython_console')

    def on_initialize(self):
        widget = self.get_widget()
        widget.sig_append_to_history_requested.connect(
            self.sig_append_to_history_requested)
        widget.sig_focus_changed.connect(self.sig_focus_changed)
        widget.sig_history_requested.connect(self.sig_history_requested)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_edit_goto_requested[str, int, str, bool].connect(
            self.sig_edit_goto_requested[str, int, str, bool])
        widget.sig_pdb_state_changed.connect(self.sig_pdb_state_changed)
        widget.sig_shellwidget_created.connect(self.sig_shellwidget_created)
        widget.sig_shellwidget_deleted.connect(self.sig_shellwidget_deleted)
        widget.sig_shellwidget_changed.connect(self.sig_shellwidget_changed)
        widget.sig_external_spyder_kernel_connected.connect(
            self.sig_external_spyder_kernel_connected)
        widget.sig_render_plain_text_requested.connect(
            self.sig_render_plain_text_requested)
        widget.sig_render_rich_text_requested.connect(
            self.sig_render_rich_text_requested)
        widget.sig_help_requested.connect(self.sig_help_requested)
        widget.sig_current_directory_changed.connect(
            self.sig_current_directory_changed)
        widget.sig_exception_occurred.connect(self.sig_exception_occurred)

        # Update kernels if python path is changed
        self.main.sig_pythonpath_changed.connect(self.update_path)

        self.sig_focus_changed.connect(self.main.plugin_focus_changed)
        self._remove_old_stderr_files()

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        widget = self.get_widget()
        mainmenu = self.get_plugin(Plugins.MainMenu)

        # Add signal to update actions state before showing the menu
        console_menu = mainmenu.get_application_menu(
            ApplicationMenus.Consoles)
        console_menu.aboutToShow.connect(
            widget.update_execution_state_kernel)

        # Main menu actions for the IPython Console
        new_consoles_actions = [
            widget.create_client_action, widget.special_console_menu,
            widget.connect_to_kernel_action]
        restart_connect_consoles_actions = [
            widget.interrupt_action,
            widget.restart_action,
            widget.reset_action]

        # Console menu
        for console_new_action in new_consoles_actions:
            mainmenu.add_item_to_application_menu(
                console_new_action,
                menu_id=ApplicationMenus.Consoles,
                section=ConsolesMenuSections.New,
                omit_id=True)

        for console_action in restart_connect_consoles_actions:
            mainmenu.add_item_to_application_menu(
                console_action,
                menu_id=ApplicationMenus.Consoles,
                section=ConsolesMenuSections.Restart,
                omit_id=True)

        # IPython documentation
        mainmenu.add_item_to_application_menu(
            self.get_widget().ipython_menu,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.ExternalDocumentation,
            before_section=HelpMenuSections.About,
            omit_id=True)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        self.sig_edit_goto_requested.connect(editor.load)
        self.sig_edit_goto_requested[str, int, str, bool].connect(
            lambda fname, lineno, word, processevents:
                editor.load(fname, lineno, word, processevents=processevents))
        editor.breakpoints_saved.connect(self.set_spyder_breakpoints)
        editor.run_in_current_ipyclient.connect(self.run_script)
        editor.run_cell_in_ipyclient.connect(self.run_cell)
        editor.debug_cell_in_ipyclient.connect(self.debug_cell)

        # Connect Editor debug action with Console
        self.sig_pdb_state_changed.connect(editor.update_pdb_state)
        editor.exec_in_extconsole.connect(self.execute_code_and_focus_editor)
        editor.sig_file_debug_message_requested.connect(
            self.print_debug_file_msg)

    @on_plugin_available(plugin=Plugins.History)
    def on_history_available(self):
        # Show history file if no console is visible
        if not self.get_widget().is_visible:
            history = self.get_plugin(Plugins.History)
            history.add_history(get_conf_path('history.py'))

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font()
        rich_font = self.get_font(rich_text=True)
        self.get_widget().update_font(font, rich_font)

    def on_close(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.get_widget().mainwindow_close = True
        return self.get_widget().close_clients()

    def on_mainwindow_visible(self):
        self.get_widget().create_new_client(give_focus=False)

    # --- Private methods
    # ------------------------------------------------------------------------
    def _remove_old_stderr_files(self):
        """
        Remove stderr files left by previous Spyder instances.

        This is only required on Windows because we can't
        clean up stderr files while Spyder is running on it.
        """
        if os.name == 'nt':
            tmpdir = get_temp_dir()
            for fname in os.listdir(tmpdir):
                if osp.splitext(fname)[1] == '.stderr':
                    try:
                        os.remove(osp.join(tmpdir, fname))
                    except Exception:
                        pass

    # --- Public API
    # ------------------------------------------------------------------------

    # ---- For client widgets
    def get_clients(self):
        """Return clients list"""
        return self.get_widget().get_clients()

    def get_focus_client(self):
        """Return current client with focus, if any"""
        return self.get_widget().get_focus_client()

    def get_current_client(self):
        """Return the currently selected client"""
        return self.get_widget().get_current_client()

    def get_current_shellwidget(self):
        """Return the shellwidget of the current client"""
        return self.get_widget().get_current_shellwidget()

    def create_new_client(self, give_focus=True, filename='', is_cython=False,
                          is_pylab=False, is_sympy=False, given_name=None):
        """Create a new client."""
        self.get_widget().create_new_client(
            give_focus=give_focus,
            filename=filename,
            is_cython=is_cython,
            is_pylab=is_pylab,
            is_sympy=is_sympy,
            given_name=given_name)

    def create_client_for_file(self, filename, is_cython=False):
        """
        Create a client widget to execute code related to a file

        Parameters
        ----------
        filename : str
            File to be executed.
        is_cython : bool, optional
            If the execution is for a cython file. The default is False.

        Returns
        -------
        None.

        """
        self.get_widget().create_client_for_file(filename, is_cython=is_cython)

    def get_client_for_file(self, filename):
        """Get client associated with a given file."""
        return self.get_widget().get_client_for_file(filename)

    def create_client_from_path(self, path):
        """
        Create a new console with `path` set as the current working directory.
        Parameters
        ----------
        path: str
            Path to use as working directory in new console.
        """
        self.get_widget().create_client_from_path(path)

    def close_client(self, index=None, client=None, force=False):
        """Close client tab from index or widget (or close current tab)"""
        self.get_widget().close_client(index=index, client=client, force=force)

    # ---- For execution and debugging
    def run_script(self, filename, wdir, args, debug, post_mortem,
                   current_client, clear_variables, console_namespace):
        """Run script in current or dedicated client"""
        self.get_widget().run_script(
            filename,
            wdir,
            args,
            debug,
            post_mortem,
            current_client,
            clear_variables,
            console_namespace)

    def run_cell(self, code, cell_name, filename, run_cell_copy,
                 function='runcell'):
        """Run cell in current or dedicated client."""
        self.get_widget().run_cell(
            code, cell_name, filename, run_cell_copy, function=function)

    def debug_cell(self, code, cell_name, filename, run_cell_copy):
        """Debug current cell."""
        self.get_widget().run_cell(
            code, cell_name, filename, run_cell_copy, function='debugcell')

    def execute_code(self, lines, current_client=True, clear_variables=False):
        """Execute code instructions."""
        self.get_widget().execute_code(
            lines,
            current_client=current_client,
            clear_variables=clear_variables)

    def execute_code_and_focus_editor(self, lines, focus_to_editor=True):
        """
        Execute lines in IPython console and eventually set focus
        to the Editor.
        """
        console = self
        console.switch_to_plugin()
        console.execute_code(lines)
        # TODO: Change after editor migration
        if focus_to_editor and self.main.editor:
            self.main.editor.switch_to_plugin()

    def stop_debugging(self):
        """Stop debugging in the current console."""
        self.get_widget().stop_debugging()

    def get_pdb_state(self):
        """Get debugging state of the current console."""
        return self.get_widget().get_pdb_state()

    def get_pdb_last_step(self):
        """Get last pdb step of the current console."""
        return self.get_widget().get_pdb_last_step()

    def pdb_execute_command(self, command):
        """
        Send command to the pdb kernel if possible.
        """
        self.get_widget().pdb_execute_command(command)

    def print_debug_file_msg(self):
        """
        Print message in the current console when a file can't be closed.

        Returns
        -------
        None.

        """
        self.get_widget().print_debug_file_msg()

    # ---- For working directory and path management
    def set_current_client_working_directory(self, directory):
        """Set current client working directory."""
        self.get_widget().set_current_client_working_directory(directory)

    def set_working_directory(self, dirname):
        """Set current working directory.
        In the workingdirectory and explorer plugins.
        """
        self.get_widget().set_working_directory(dirname)

    def update_working_directory(self):
        """Update working directory to console cwd."""
        self.get_widget().update_working_directory()

    def update_path(self, path_dict, new_path_dict):
        """Update path on consoles."""
        self.get_widget().update_path(path_dict, new_path_dict)

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into all clients"""
        self.get_widget().set_spyder_breakpoints()

    def restart(self):
        """
        Restart the console

        This is needed when we switch projects to update PYTHONPATH
        and the selected interpreter
        """
        self.get_widget().restart()

    def restart_kernel(self):
        """
        Restart the current client kernel

        Returns
        -------
        None.

        """
        self.get_widget().restart_kernel()

    # ---- For documentation and help -----------------------------------------
    def show_intro(self):
        """Show intro to IPython help."""
        self.get_widget().show_intro()

    def show_guiref(self):
        """Show qtconsole help."""
        self.get_widget().show_guiref()

    def show_quickref(self):
        """Show IPython Cheat Sheet."""
        self.get_widget().show_quickref()

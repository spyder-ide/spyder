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
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.ipythonconsole.confpage import IPythonConsoleConfigPage
from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget, IPythonConsoleWidgetOptionsMenus)
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, ConsolesMenuSections, HelpMenuSections)
from spyder.utils.programs import get_temp_dir


class IPythonConsole(SpyderDockablePlugin):
    """
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget
    """

    # This is required for the new API
    NAME = 'ipython_console'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [Plugins.Editor, Plugins.History, Plugins.MainMenu,
                Plugins.Projects, Plugins.PythonpathManager,
                Plugins.WorkingDirectory]
    TABIFY = [Plugins.History]
    WIDGET_CLASS = IPythonConsoleWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = IPythonConsoleConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False
    RAISE_AND_FOCUS = True

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

    Parameters
    ----------
    path: str
        Path to history file.
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
    processevents: bool
        True if the code editor need to process qt events when loading the
        requested file.
    """

    sig_edit_new = Signal(str)
    """
    This signal will request to create a new file in a code editor.

    Parameters
    ----------
    path: str
        Path to file.
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

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
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
        widget.sig_switch_to_plugin_requested.connect(self.switch_to_plugin)
        widget.sig_history_requested.connect(self.sig_history_requested)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_edit_goto_requested[str, int, str, bool].connect(
            self.sig_edit_goto_requested[str, int, str, bool])
        widget.sig_edit_new.connect(self.sig_edit_new)
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

        self.sig_focus_changed.connect(self.main.plugin_focus_changed)
        self._remove_old_std_files()

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
            widget.update_actions)

        # Main menu actions for the IPython Console
        new_consoles_actions = [
            widget.create_client_action,
            widget.special_console_menu,
            widget.connect_to_kernel_action
        ]

        restart_connect_consoles_actions = [
            widget.interrupt_action,
            widget.restart_action,
            widget.reset_action
        ]

        # Console menu
        for console_new_action in new_consoles_actions:
            mainmenu.add_item_to_application_menu(
                console_new_action,
                menu_id=ApplicationMenus.Consoles,
                section=ConsolesMenuSections.New,
            )

        for console_action in restart_connect_consoles_actions:
            mainmenu.add_item_to_application_menu(
                console_action,
                menu_id=ApplicationMenus.Consoles,
                section=ConsolesMenuSections.Restart,
            )

        # IPython documentation
        mainmenu.add_item_to_application_menu(
            self.get_widget().ipython_menu,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.ExternalDocumentation,
            before_section=HelpMenuSections.About,
        )

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        self.sig_edit_goto_requested.connect(editor.load)
        self.sig_edit_goto_requested[str, int, str, bool].connect(
            self._load_file_in_editor)
        self.sig_edit_new.connect(editor.new)
        editor.breakpoints_saved.connect(self.set_spyder_breakpoints)
        editor.run_in_current_ipyclient.connect(self.run_script)
        editor.run_cell_in_ipyclient.connect(self.run_cell)
        editor.debug_cell_in_ipyclient.connect(self.debug_cell)

        # Connect Editor debug action with Console
        self.sig_pdb_state_changed.connect(editor.update_pdb_state)
        editor.exec_in_extconsole.connect(self.run_selection)
        editor.sig_file_debug_message_requested.connect(
            self.print_debug_file_msg)

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._on_project_loaded)
        projects.sig_project_closed.connect(self._on_project_closed)

    @on_plugin_available(plugin=Plugins.WorkingDirectory)
    def on_working_directory_available(self):
        working_directory = self.get_plugin(Plugins.WorkingDirectory)
        working_directory.sig_current_directory_changed.connect(
            self.save_working_directory)

    @on_plugin_available(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_available(self):
        pythonpath_manager = self.get_plugin(Plugins.PythonpathManager)
        pythonpath_manager.sig_pythonpath_changed.connect(self.update_path)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_application_menu(ApplicationMenus.Consoles)

        # IPython documentation menu
        mainmenu.remove_item_from_application_menu(
            IPythonConsoleWidgetOptionsMenus.Documentation,
            menu_id=ApplicationMenus.Help
         )

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        self.sig_edit_goto_requested.disconnect(editor.load)
        self.sig_edit_goto_requested[str, int, str, bool].disconnect(
            self._load_file_in_editor)
        self.sig_edit_new.disconnect(editor.new)
        editor.breakpoints_saved.disconnect(self.set_spyder_breakpoints)
        editor.run_in_current_ipyclient.disconnect(self.run_script)
        editor.run_cell_in_ipyclient.disconnect(self.run_cell)
        editor.debug_cell_in_ipyclient.disconnect(self.debug_cell)

        # Connect Editor debug action with Console
        self.sig_pdb_state_changed.disconnect(editor.update_pdb_state)
        editor.exec_in_extconsole.disconnect(self.run_selection)
        editor.sig_file_debug_message_requested.disconnect(
            self.print_debug_file_msg)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._on_project_loaded)
        projects.sig_project_closed.disconnect(self._on_project_closed)

    @on_plugin_teardown(plugin=Plugins.WorkingDirectory)
    def on_working_directory_teardown(self):
        working_directory = self.get_plugin(Plugins.WorkingDirectory)
        working_directory.sig_current_directory_changed.disconnect(
            self.save_working_directory)

    @on_plugin_teardown(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_teardown(self):
        pythonpath_manager = self.get_plugin(Plugins.PythonpathManager)
        pythonpath_manager.sig_pythonpath_changed.disconnect(self.update_path)

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font()
        rich_font = self.get_font(rich_text=True)
        self.get_widget().update_font(font, rich_font)

    def on_close(self, cancelable=False):
        """Perform actions when plugin is closed"""
        self.get_widget().mainwindow_close = True
        return self.get_widget().close_all_clients()

    def on_mainwindow_visible(self):
        self.create_new_client(give_focus=False)

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _load_file_in_editor(self, fname, lineno, word, processevents):
        editor = self.get_plugin(Plugins.Editor)
        editor.load(fname, lineno, word, processevents=processevents)

    def _on_project_loaded(self):
        projects = self.get_plugin(Plugins.Projects)
        self.get_widget().update_active_project_path(
            projects.get_active_project_path())

    def _on_project_closed(self):
        self.get_widget().update_active_project_path(None)

    def _remove_old_std_files(self):
        """
        Remove std files left by previous Spyder instances.

        This is only required on Windows because we can't
        clean up std files while Spyder is running on that
        platform.
        """
        if os.name == 'nt':
            tmpdir = get_temp_dir()
            for fname in os.listdir(tmpdir):
                if osp.splitext(fname)[1] in ('.stderr', '.stdout', '.fault'):
                    try:
                        os.remove(osp.join(tmpdir, fname))
                    except Exception:
                        pass

    # ---- Public API
    # -------------------------------------------------------------------------

    # ---- Spyder Kernels handlers registry functionality
    def register_spyder_kernel_call_handler(self, handler_id, handler):
        """
        Register a callback for it to be available for the kernels of new
        clients.

        Parameters
        ----------
        handler_id : str
            Handler name to be registered and that will be used to
            call the respective handler in the Spyder kernel.
        handler : func
            Callback function that will be called when the kernel calls
            the handler.

        Returns
        -------
        None.
        """
        self.get_widget().register_spyder_kernel_call_handler(
            handler_id, handler)

    def unregister_spyder_kernel_call_handler(self, handler_id):
        """
        Unregister/remove a handler for not be added to new clients kernels

        Parameters
        ----------
        handler_id : str
            Handler name that was registered and that will be removed
            from the Spyder kernel available handlers.

        Returns
        -------
        None.
        """
        self.get_widget().unregister_spyder_kernel_call_handler(handler_id)

    # ---- For client widgets
    def get_clients(self):
        """Return clients list"""
        return self.get_widget().clients

    def get_focus_client(self):
        """Return current client with focus, if any"""
        return self.get_widget().get_focus_client()

    def get_current_client(self):
        """Return the currently selected client"""
        return self.get_widget().get_current_client()

    def get_current_shellwidget(self):
        """Return the shellwidget of the current client"""
        return self.get_widget().get_current_shellwidget()

    def rename_client_tab(self, client, given_name):
        """
        Rename a client's tab.

        Parameters
        ----------
        client: spyder.plugins.ipythonconsole.widgets.client.ClientWidget
            Client to rename.
        given_name: str
            New name to be given to the client's tab.

        Returns
        -------
        None.
        """
        self.get_widget().rename_client_tab(client, given_name)

    def create_new_client(self, give_focus=True, filename='', is_cython=False,
                          is_pylab=False, is_sympy=False, given_name=None):
        """
        Create a new client.

        Parameters
        ----------
        give_focus : bool, optional
            True if the new client should gain the window
            focus, False otherwise. The default is True.
        filename : str, optional
            Filename associated with the client. The default is ''.
        is_cython : bool, optional
            True if the client is expected to preload Cython support,
            False otherwise. The default is False.
        is_pylab : bool, optional
            True if the client is expected to preload PyLab support,
            False otherwise. The default is False.
        is_sympy : bool, optional
            True if the client is expected to preload Sympy support,
            False otherwise. The default is False.
        given_name : str, optional
            Initial name displayed in the tab of the client.
            The default is None.

        Returns
        -------
        None.
        """
        self.get_widget().create_new_client(
            give_focus=give_focus,
            filename=filename,
            is_cython=is_cython,
            is_pylab=is_pylab,
            is_sympy=is_sympy,
            given_name=given_name)

    def create_client_for_file(self, filename, is_cython=False):
        """
        Create a client widget to execute code related to a file.

        Parameters
        ----------
        filename : str
            File to be executed.
        is_cython : bool, optional
            If the execution is for a Cython file. The default is False.

        Returns
        -------
        None.
        """
        self.get_widget().create_client_for_file(filename, is_cython=is_cython)

    def create_client_for_kernel(self, connection_file, hostname=None,
                                 sshkey=None, password=None):
        """
        Create a client connected to an existing kernel.

        Parameters
        ----------
        connection_file: str
            Json file that has the kernel's connection info.
        hostname: str, optional
            Name or IP address of the remote machine where the kernel was
            started. When this is provided, it's also necessary to pass either
            the ``sshkey`` or ``password`` arguments.
        sshkey: str, optional
            SSH key file to connect to the remote machine where the kernel is
            running.
        password: str, optional
            Password to authenticate to the remote machine where the kernel is
            running.

        Returns
        -------
        None.
        """
        self.get_widget().create_client_for_kernel(
            connection_file, hostname, sshkey, password)

    def get_client_for_file(self, filename):
        """Get client associated with a given file name."""
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

    def close_client(self, index=None, client=None, ask_recursive=True):
        """Close client tab from index or client (or close current tab)"""
        self.get_widget().close_client(index=index, client=client,
                                       ask_recursive=ask_recursive)

    # ---- For execution and debugging
    def run_script(self, filename, wdir, args='', debug=False,
                   post_mortem=False, current_client=True,
                   clear_variables=False, console_namespace=False,
                   focus_to_editor=True):
        """
        Run script in current or dedicated client.

        Parameters
        ----------
        filename : str
            Path to file that will be run.
        wdir : str
            Working directory from where the file should be run.
        args : str, optional
            Arguments defined to run the file.
        debug : bool, optional
            True if the run if for debugging the file,
            False for just running it.
        post_mortem : bool, optional
            True if in case of error the execution should enter in
            post-mortem mode, False otherwise.
        current_client : bool, optional
            True if the execution should be done in the current client,
            False if the execution needs to be done in a dedicated client.
        clear_variables : bool, optional
            True if all the variables should be removed before execution,
            False otherwise.
        console_namespace : bool, optional
            True if the console namespace should be used, False otherwise.
        focus_to_editor: bool, optional
            Leave focus in the editor after execution.

        Returns
        -------
        None.
        """
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().run_script(
            filename,
            wdir,
            args,
            debug,
            post_mortem,
            current_client,
            clear_variables,
            console_namespace,
            focus_to_editor)

    def run_cell(self, code, cell_name, filename, run_cell_copy,
                 focus_to_editor, function='runcell'):
        """
        Run cell in current or dedicated client.

        Parameters
        ----------
        code : str
            Piece of code to run that corresponds to a cell in case
            `run_cell_copy` is True.
        cell_name : str or int
            Cell name or index.
        filename : str
            Path of the file where the cell to execute is located.
        run_cell_copy : bool
            True if the cell should be executed line by line,
            False if the provided `function` should be used.
        focus_to_editor: bool
            Whether to give focus to the editor after running the cell. If
            False, focus is given to the console.
        function : str, optional
            Name handler of the kernel function to be used to execute the cell
            in case `run_cell_copy` is False.
            The default is 'runcell'.

        Returns
        -------
        None.
        """
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().run_cell(
            code, cell_name, filename, run_cell_copy, focus_to_editor,
            function=function)

    def debug_cell(self, code, cell_name, filename, run_cell_copy,
                   focus_to_editor):
        """
        Debug current cell.

        Parameters
        ----------
        code : str
            Piece of code to run that corresponds to a cell in case
            `run_cell_copy` is True.
        cell_name : str or int
            Cell name or index.
        filename : str
            Path of the file where the cell to execute is located.
        run_cell_copy : bool
            True if the cell should be executed line by line,
            False if the `debugcell` kernel function should be used.
        focus_to_editor: bool
            Whether to give focus to the editor after debugging the cell. If
            False, focus is given to the console.

        Returns
        -------
        None.
        """
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().debug_cell(code, cell_name, filename, run_cell_copy,
                                     focus_to_editor)

    def execute_code(self, lines, current_client=True, clear_variables=False):
        """
        Execute code instructions.

        Parameters
        ----------
        lines : str
            Code lines to execute.
        current_client : bool, optional
            True if the execution should be done in the current client.
            The default is True.
        clear_variables : bool, optional
            True if before the execution the variables should be cleared.
            The default is False.

        Returns
        -------
        None.
        """
        self.get_widget().execute_code(
            lines,
            current_client=current_client,
            clear_variables=clear_variables)

    def run_selection(self, lines, focus_to_editor=True):
        """Execute selected lines in the current console."""
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().execute_code(lines, set_focus=not focus_to_editor)

    def stop_debugging(self):
        """Stop debugging in the current console."""
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().stop_debugging()

    def get_pdb_state(self):
        """Get debugging state of the current console."""
        return self.get_widget().get_pdb_state()

    def get_pdb_last_step(self):
        """Get last pdb step of the current console."""
        return self.get_widget().get_pdb_last_step()

    def pdb_execute_command(self, command, focus_to_editor):
        """
        Send command to the pdb kernel if possible.

        Parameters
        ----------
        command : str
            Command to execute by the pdb kernel.
        focus_to_editor: bool
            Leave focus in editor after the command is executed.

        Returns
        -------
        None.
        """
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().pdb_execute_command(command, focus_to_editor)

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
        """
        Set current client working directory.

        Parameters
        ----------
        directory : str
            Path for the new current working directory.

        Returns
        -------
        None.
        """
        self.get_widget().set_current_client_working_directory(directory)

    def set_working_directory(self, dirname):
        """
        Set current working directory in the Working Directory and Files
        plugins.

        Parameters
        ----------
        dirname : str
            Path to the new current working directory.

        Returns
        -------
        None.
        """
        self.get_widget().set_working_directory(dirname)

    @Slot(str)
    def save_working_directory(self, dirname):
        """
        Save current working directory on the main widget to start new clients.

        Parameters
        ----------
        new_dir: str
            Path to the new current working directory.
        """
        self.get_widget().save_working_directory(dirname)

    def update_working_directory(self):
        """Update working directory to console current working directory."""
        self.get_widget().update_working_directory()

    def update_path(self, path_dict, new_path_dict):
        """
        Update path on consoles.

        Both parameters have as keys paths and as value if the path
        should be used/is active (True) or not (False)

        Parameters
        ----------
        path_dict : dict
            Corresponds to the previous state of the PYTHONPATH.
        new_path_dict : dict
            Corresponds to the new state of the PYTHONPATH.

        Returns
        -------
        None.
        """
        self.get_widget().update_path(path_dict, new_path_dict)

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into all clients"""
        self.get_widget().set_spyder_breakpoints()

    def restart(self):
        """
        Restart the console.

        This is needed when we switch projects to update PYTHONPATH
        and the selected interpreter.
        """
        self.get_widget().restart()

    def restart_kernel(self):
        """
        Restart the current client's kernel.

        Returns
        -------
        None.
        """
        self.get_widget().restart_kernel()

    # ---- For documentation and help
    def show_intro(self):
        """Show intro to IPython help."""
        self.get_widget().show_intro()

    def show_guiref(self):
        """Show qtconsole help."""
        self.get_widget().show_guiref()

    def show_quickref(self):
        """Show IPython Cheat Sheet."""
        self.get_widget().show_quickref()

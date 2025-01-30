# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console plugin based on QtConsole.
"""

# Standard library imports
import sys
from typing import List

# Third party imports
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.fonts import SpyderFontType
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.ipythonconsole.api import (
    IPythonConsolePyConfiguration,
    IPythonConsoleWidgetMenus
)
from spyder.plugins.ipythonconsole.confpage import IPythonConsoleConfigPage
from spyder.plugins.ipythonconsole.widgets.run_conf import IPythonConfigOptions
from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget
)
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, ConsolesMenuSections, HelpMenuSections)
from spyder.plugins.run.api import (
    RunContext, RunExecutor, RunConfiguration,
    ExtendedRunExecutionParameters, RunResult, run_execute)
from spyder.plugins.editor.api.run import CellRun, FileRun, SelectionRun


class IPythonConsole(SpyderDockablePlugin, RunExecutor):
    """
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget
    """

    # This is required for the new API
    NAME = 'ipython_console'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [
        Plugins.Editor,
        Plugins.History,
        Plugins.MainInterpreter,
        Plugins.MainMenu,
        Plugins.Projects,
        Plugins.PythonpathManager,
        Plugins.RemoteClient,
        Plugins.Run,
        Plugins.StatusBar,
        Plugins.WorkingDirectory,
    ]
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

    sig_edit_new = Signal(str)
    """
    This signal will request to create a new file in a code editor.

    Parameters
    ----------
    path: str
        Path to file.
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

    sig_shellwidget_errored = Signal(object)
    """
    This signal is emitted when the current shellwidget failed to start.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
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

    sig_interpreter_changed = Signal(str)
    """
    This signal is emitted when the interpreter of the active shell widget has
    changed.

    Parameters
    ----------
    path: str
        Path to the new interpreter.
    """

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('IPython console')

    @staticmethod
    def get_description():
        return _(
            "Run Python files, cells, code and commands interactively."
        )

    @classmethod
    def get_icon(cls):
        return cls.create_icon('ipython_console')

    def on_initialize(self):
        widget = self.get_widget()

        # Main widget signals
        widget.sig_append_to_history_requested.connect(
            self.sig_append_to_history_requested)
        widget.sig_switch_to_plugin_requested.connect(self.switch_to_plugin)
        widget.sig_history_requested.connect(self.sig_history_requested)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_edit_new.connect(self.sig_edit_new)
        widget.sig_shellwidget_created.connect(self.sig_shellwidget_created)
        widget.sig_shellwidget_deleted.connect(self.sig_shellwidget_deleted)
        widget.sig_shellwidget_changed.connect(self.sig_shellwidget_changed)
        widget.sig_shellwidget_errored.connect(self.sig_shellwidget_errored)
        widget.sig_render_plain_text_requested.connect(
            self.sig_render_plain_text_requested)
        widget.sig_render_rich_text_requested.connect(
            self.sig_render_rich_text_requested)
        widget.sig_help_requested.connect(self.sig_help_requested)
        widget.sig_current_directory_changed.connect(
            self.sig_current_directory_changed)
        widget.sig_interpreter_changed.connect(
            self.sig_interpreter_changed
        )

        # Run configurations
        self.cython_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'pyx',
            'contexts': [
                {'name': 'File'}
            ]
        }

        self.python_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'py',
            'contexts': [
                {'name': 'File'},
                {'name': 'Cell'},
                {'name': 'Selection'},
            ]
        }

        self.ipython_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'ipy',
            'contexts': [
                {'name': 'File'},
                {'name': 'Cell'},
                {'name': 'Selection'},
            ]
        }

        self.executor_configuration = [
            {
                'input_extension': 'py',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 0
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 0
            },
            {
                'input_extension': 'py',
                'context': {'name': 'Cell'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 0
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'Cell'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 0
            },
            {
                'input_extension': 'py',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 0
            },
            {
                'input_extension': 'ipy',
                'context': {'name': 'Selection'},
                'output_formats': [],
                'configuration_widget': None,
                'requires_cwd': True,
                'priority': 0
            },
            {
                'input_extension': 'pyx',
                'context': {'name': 'File'},
                'output_formats': [],
                'configuration_widget': IPythonConfigOptions,
                'requires_cwd': True,
                'priority': 0
            },
        ]

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        # Add status widgets
        statusbar = self.get_plugin(Plugins.StatusBar)

        pythonenv_status = self.get_widget().pythonenv_status
        statusbar.add_status_widget(pythonenv_status)
        pythonenv_status.register_ipythonconsole(self)

        matplotlib_status = self.get_widget().matplotlib_status
        statusbar.add_status_widget(matplotlib_status)
        matplotlib_status.register_ipythonconsole(self)

    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        # Remove status widgets
        statusbar = self.get_plugin(Plugins.StatusBar)

        pythonenv_status = self.get_widget().pythonenv_status
        pythonenv_status.unregister_ipythonconsole(self)
        statusbar.remove_status_widget(pythonenv_status.ID)

        matplotlib_status = self.get_widget().matplotlib_status
        matplotlib_status.unregister_ipythonconsole(self)
        statusbar.remove_status_widget(matplotlib_status.ID)

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
        console_menu.aboutToShow.connect(widget.update_actions)

        if sys.platform == "darwin":
            # Avoid changing the aspect of the tabs context menu when it's
            # visible and the user shows the console menu at the same time.
            console_menu.aboutToShow.connect(
                lambda: widget.tabwidget.menu.hide()
            )

        # Main menu actions for the IPython Console
        new_consoles_actions = [
            widget.create_client_action,
            widget.console_environment_menu,
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
        self.sig_edit_new.connect(editor.new)

        for run_config in [
            self.python_editor_run_configuration,
            self.ipython_editor_run_configuration,
            self.cython_editor_run_configuration
        ]:
            editor.add_supported_run_configuration(run_config)

    @on_plugin_available(plugin=Plugins.Projects)
    def on_projects_available(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.connect(self._on_project_loaded)
        projects.sig_project_closed.connect(self._on_project_closed)

    @on_plugin_available(plugin=Plugins.Run)
    def on_run_available(self):
        run = self.get_plugin(Plugins.Run)
        run.register_executor_configuration(self, self.executor_configuration)

    @on_plugin_available(plugin=Plugins.WorkingDirectory)
    def on_working_directory_available(self):
        working_directory = self.get_plugin(Plugins.WorkingDirectory)
        working_directory.sig_current_directory_changed.connect(
            self.save_working_directory)

    @on_plugin_available(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_available(self):
        pythonpath_manager = self.get_plugin(Plugins.PythonpathManager)
        pythonpath_manager.sig_pythonpath_changed.connect(self.update_path)

    @on_plugin_available(plugin=Plugins.RemoteClient)
    def on_remote_client_available(self):
        remote_client = self.get_plugin(Plugins.RemoteClient)
        remote_client.sig_server_stopped.connect(self._close_remote_clients)
        remote_client.sig_server_renamed.connect(self._rename_remote_clients)

    @on_plugin_available(plugin=Plugins.MainInterpreter)
    def on_main_interpreter_available(self):
        main_interpreter = self.get_plugin(Plugins.MainInterpreter)
        main_interpreter.sig_environments_updated.connect(self._update_envs)

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
            IPythonConsoleWidgetMenus.Documentation,
            menu_id=ApplicationMenus.Help
         )

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        self.sig_edit_goto_requested.disconnect(editor.load)
        self.sig_edit_new.disconnect(editor.new)

        for run_config in [
            self.python_editor_run_configuration,
            self.ipython_editor_run_configuration,
            self.cython_editor_run_configuration
        ]:
            editor.remove_supported_run_configuration(run_config)

    @on_plugin_teardown(plugin=Plugins.Projects)
    def on_projects_teardown(self):
        projects = self.get_plugin(Plugins.Projects)
        projects.sig_project_loaded.disconnect(self._on_project_loaded)
        projects.sig_project_closed.disconnect(self._on_project_closed)

    @on_plugin_teardown(plugin=Plugins.Run)
    def on_run_teardown(self):
        run = self.get_plugin(Plugins.Run)
        run.deregister_executor_configuration(
            self, self.executor_configuration)

    @on_plugin_teardown(plugin=Plugins.WorkingDirectory)
    def on_working_directory_teardown(self):
        working_directory = self.get_plugin(Plugins.WorkingDirectory)
        working_directory.sig_current_directory_changed.disconnect(
            self.save_working_directory)

    @on_plugin_teardown(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_teardown(self):
        pythonpath_manager = self.get_plugin(Plugins.PythonpathManager)
        pythonpath_manager.sig_pythonpath_changed.disconnect(self.update_path)

    @on_plugin_teardown(plugin=Plugins.RemoteClient)
    def on_remote_client_teardown(self):
        remote_client = self.get_plugin(Plugins.RemoteClient)
        remote_client.sig_server_stopped.disconnect(self._close_remote_clients)
        remote_client.sig_server_renamed.disconnect(
            self._rename_remote_clients
        )

    @on_plugin_teardown(plugin=Plugins.MainInterpreter)
    def on_main_interpreter_teardown(self):
        main_interpreter = self.get_plugin(Plugins.MainInterpreter)
        main_interpreter.sig_environments_updated.disconnect(self._update_envs)

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font(SpyderFontType.Monospace)
        app_font = self.get_font(SpyderFontType.Interface)
        self.get_widget().update_font(font, app_font)

    def on_close(self, cancelable=False):
        """Perform actions when plugin is closed"""
        self.get_widget().mainwindow_close = True
        return self.get_widget().close_all_clients()

    def on_mainwindow_visible(self):
        """
        Connect to an existing kernel if a `kernel-*.json` file is given via
        command line options. Otherwise create a new client.
        """
        cli_options = self.get_command_line_options()
        connection_file = cli_options.connection_file

        if connection_file is not None:
            cf_path = self.get_widget().find_connection_file(connection_file)
            if cf_path is None:
                # Show an error if the connection file passed on the command
                # line doesn't exist (find_connection_file returns None in that
                # case).
                self.create_new_client(give_focus=False)
                client = self.get_current_client()
                client.show_kernel_connection_error()
            else:
                self.create_client_for_kernel(cf_path, give_focus=False)
        else:
            self.create_new_client(give_focus=False)

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _on_project_loaded(self, path):
        self.get_widget().update_active_project_path(path)

    def _on_project_closed(self):
        self.get_widget().update_active_project_path(None)

    def _close_remote_clients(self, server_id):
        self.get_widget().close_remote_clients(server_id)

    def _rename_remote_clients(self, server_id):
        self.get_widget().rename_remote_clients(server_id)

    def _update_envs(self, envs):
        self.get_widget().update_envs(envs)

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

    def set_current_shellwidget(self, shellwidget):
        """Activate client associated to given shellwidget."""
        self.get_widget().select_tab(shellwidget)

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

    def create_new_client(self, give_focus=True, filename='', special=None,
                          given_name=None, path_to_custom_interpreter=None):
        """
        Create a new client.

        Parameters
        ----------
        give_focus : bool, optional
            True if the new client should gain the window
            focus, False otherwise. The default is True.
        filename : str, optional
            Filename associated with the client. The default is ''.
        special : str, optional
            Type of special support to preload. It can be "pylab", "cython",
            "sympy", or None.
        given_name : str, optional
            Initial name displayed in the tab of the client.
            The default is None.
        path_to_custom_interpreter : str, optional
            Path to a custom interpreter the client should use regardless of
            the interpreter selected in Spyder Preferences.
            The default is None.

        Returns
        -------
        None.
        """
        self.get_widget().create_new_client(
            give_focus=give_focus,
            filename=filename,
            special=special,
            given_name=given_name,
            path_to_custom_interpreter=path_to_custom_interpreter)

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

    def create_client_for_kernel(
        self,
        connection_file,
        hostname=None,
        sshkey=None,
        password=None,
        server_id=None,
        give_focus=False,
        can_close=True,
    ):
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
        server_id: str, optional
            The remote server id to which this client is connected to.
        give_focus : bool, optional
            True if the new client should gain the window
            focus, False otherwise. The default is True.
        can_close: bool, optional
            Whether the client can be closed. This is useful to prevent closing
            the client that will be connected to a remote kernel before the
            connection is established.

        Returns
        -------
        client: ClientWidget
            The created client.
        """
        return self.get_widget().create_client_for_kernel(
            connection_file,
            hostname,
            sshkey,
            password,
            server_id,
            give_focus,
            can_close,
        )

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

    # ---- For execution
    @run_execute(context=RunContext.File)
    def exec_files(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        exec_params = conf['params']
        cwd_opts = exec_params['working_dir']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']

        run_input: FileRun = input['run_input']
        filename = run_input['path']
        wdir = cwd_opts['path']
        args = params['python_args']
        post_mortem = params['post_mortem']
        current_client = params['current']
        clear_variables = params['clear_namespace']
        console_namespace = params['console_namespace']
        run_method = params.get('run_method', 'runfile')

        self.run_script(
            filename,
            wdir,
            args,
            post_mortem,
            current_client,
            clear_variables,
            console_namespace,
            method=run_method,
        )

        return []

    @run_execute(context=RunContext.Selection)
    def exec_selection(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        run_input: SelectionRun = input['run_input']
        text = run_input['selection']
        self.run_selection(text)

    @run_execute(context=RunContext.Cell)
    def exec_cell(
        self,
        input: RunConfiguration,
        conf: ExtendedRunExecutionParameters
    ) -> List[RunResult]:

        run_input: CellRun = input['run_input']
        cell_text = run_input['cell']

        if run_input['copy']:
            self.run_selection(cell_text)
            return

        cell_name = run_input['cell_name']
        filename = run_input['path']

        exec_params = conf['params']
        params: IPythonConsolePyConfiguration = exec_params['executor_params']
        run_method = params.get('run_method', 'runcell')
        self.run_cell(cell_text, cell_name, filename,
                      method=run_method)

    # ---- For execution and debugging
    def run_script(self, filename, wdir, args='',
                   post_mortem=False, current_client=True,
                   clear_variables=False, console_namespace=False,
                   method=None):
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
        method : str or None
            Method to run the file. It must accept the same arguments as
            `runfile`.

        Returns
        -------
        None.
        """
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().run_script(
            filename,
            wdir,
            args,
            post_mortem,
            current_client,
            clear_variables,
            console_namespace,
            method
        )

    def run_cell(self, code, cell_name, filename, method='runcell'):
        """
        Run cell in current or dedicated client.

        Parameters
        ----------
        code : str
            Piece of code to run that corresponds to a cell.
        cell_name : str or int
            Cell name or index.
        filename : str
            Path of the file where the cell to execute is located.
        method : str, optional
            Name handler of the kernel function to be used to execute the cell.
            The default is 'runcell'.

        Returns
        -------
        None.
        """
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().run_cell(code, cell_name, filename, method=method)

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

    def run_selection(self, lines):
        """Execute selected lines in the current console."""
        self.sig_unmaximize_plugin_requested.emit()
        self.get_widget().execute_code(lines)

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

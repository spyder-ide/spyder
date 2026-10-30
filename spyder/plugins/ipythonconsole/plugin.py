# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console plugin based on QtConsole.
"""

# Standard library imports
from concurrent.futures import Future
from functools import cached_property
import os.path as osp
import re
import shlex
import sys
from typing import List, Optional, Union

# Third party imports
from qtpy.QtCore import QTimer, Signal, Slot
from superqt.utils import qdebounced

# Local imports
from spyder.api.fonts import SpyderFontType
from spyder.api.plugins import (
    ExposedCallError,
    Plugins,
    SpyderDockablePlugin,
    current_caller,
    expose,
)
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import _
from spyder.plugins.application.api import ApplicationActions
from spyder.plugins.ipythonconsole.api import (
    IPythonConsolePyConfiguration,
    IPythonConsoleWidgetActions,
    IPythonConsoleWidgetMenus,
    RemoteConsolesMenus
)
from spyder.plugins.ipythonconsole.confpage import IPythonConsoleConfigPage
from spyder.plugins.ipythonconsole.utils.execution import (
    DEFAULT_EXECUTE_TIMEOUT,
    NEW_CONSOLE_TIMEOUT,
    build_run_line,
    call_kernel_helper,
    check_idle,
    check_name,
    check_ready,
    get_console_id,
    get_console_state,
    request_variables,
    run_code,
)
from spyder.plugins.ipythonconsole.utils.scheduler import (
    describe_caller,
    get_scheduler,
)
from spyder.plugins.ipythonconsole.utils.kernel_helpers import (
    spyder_input_history,
    spyder_object_help,
    spyder_summarize_variable,
)
from spyder.plugins.ipythonconsole.widgets.run_conf import IPythonConfigOptions
from spyder.plugins.ipythonconsole.widgets import (
    MatplotlibStatus,
    PythonEnvironmentStatus,
)
from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget
)
from spyder.plugins.mainmenu.api import (
    ApplicationMenus,
    ConsolesMenuSections,
    HelpMenuSections,
)
from spyder.plugins.run.api import (
    ExtendedRunExecutionParameters,
    RunContext,
    RunConfiguration,
    RunExecutor,
    RunResult,
    run_execute,
)
from spyder.plugins.editor.api.run import CellRun, FileRun, SelectionRun


class IPythonConsole(SpyderDockablePlugin, RunExecutor):
    """
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget
    """

    NAME = 'ipython_console'
    REQUIRES = [
        Plugins.Application,
        Plugins.Console,
        Plugins.MainInterpreter,
        Plugins.MainMenu,
        Plugins.Preferences,
        Plugins.WorkingDirectory,
    ]
    OPTIONAL = [
        Plugins.Editor,
        Plugins.History,
        Plugins.Projects,
        Plugins.PythonpathManager,
        Plugins.RemoteClient,
        Plugins.Run,
        Plugins.StatusBar,
    ]
    TABIFY = [Plugins.History]
    WIDGET_CLASS = IPythonConsoleWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = IPythonConsoleConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False
    RAISE_AND_FOCUS = True
    CAN_HANDLE_EDIT_ACTIONS = True
    CAN_HANDLE_SEARCH_ACTIONS = True

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

    sig_current_directory_changed = Signal(str, str)
    """
    This signal is emitted when the current directory of the active shell
    widget has changed.

    Parameters
    ----------
    working_directory: str
        The new working directory path.
    server_id: str
        The server identification from where the working directory is reachable.
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

    def __init__(self, parent, configuration=None):
        SpyderDockablePlugin.__init__(self, parent, configuration)

        # Combined with RunExecutor via multiple inheritance; set up its
        # state here since SpyderDockablePlugin.__init__ doesn't call
        # RunExecutor.__init__ (which would also re-init the QObject part).
        self.setup_run_executor()

    # ---- SpyderDockablePlugin API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('IPython Console')

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

        self._is_remote_consoles_menu_added = False

        # Outside callers (e.g. AI agents) that created consoles, by id
        self._console_creators = {}

        # Schedulers follow the user's typing from the start, so outside code
        # doesn't interrupt them
        widget.sig_shellwidget_created.connect(get_scheduler)

        # Main widget signals
        # Connect signal to open preferences
        widget.sig_open_preferences_requested.connect(
            self._open_interpreter_preferences
        )
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

        self.pyw_editor_run_configuration = {
            'origin': self.NAME,
            'extension': 'pyw',
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
                'input_extension': 'pyw',
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
                'input_extension': 'pyw',
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
                'input_extension': 'pyw',
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

    @on_plugin_available(plugin=Plugins.Application)
    def on_application_available(self) -> None:
        widget = self.get_widget()
        widget.sig_edit_action_enabled.connect(self._enable_edit_action)

        # Enable Select All edit action
        self._enable_edit_action(ApplicationActions.SelectAll, True)

        # Setup Search actions
        self._enable_search_action(ApplicationActions.FindText, True)
        self._enable_search_action(ApplicationActions.FindNext, True)
        self._enable_search_action(ApplicationActions.FindPrevious, True)
        # Replace action is set disabled since the `FindReplace` widget created
        # by the main widget has `enable_replace=False`
        self._enable_search_action(ApplicationActions.ReplaceText, False)

    @on_plugin_teardown(plugin=Plugins.Application)
    def on_application_teardown(self) -> None:
        widget = self.get_widget()
        widget.sig_edit_action_enabled.disconnect(self._enable_edit_action)

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        # Add status widgets
        statusbar = self.get_plugin(Plugins.StatusBar)
        widget = self.get_widget()

        pythonenv_status = PythonEnvironmentStatus(widget)
        statusbar.add_status_widget(pythonenv_status)
        pythonenv_status.register_ipythonconsole(self)
        pythonenv_status.sig_interpreter_changed.connect(
            widget.sig_interpreter_changed
        )
        pythonenv_status.sig_open_preferences_requested.connect(
            widget.sig_open_preferences_requested
        )

        matplotlib_status = MatplotlibStatus(widget)
        statusbar.add_status_widget(matplotlib_status)
        matplotlib_status.register_ipythonconsole(self)

    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        # Remove status widgets
        statusbar = self.get_plugin(Plugins.StatusBar)
        widget = self.get_widget()

        pythonenv_status = statusbar.get_status_widget(
            PythonEnvironmentStatus.ID
        )
        pythonenv_status.sig_interpreter_changed.disconnect(
            widget.sig_interpreter_changed
        )
        pythonenv_status.sig_open_preferences_requested.disconnect(
            widget.sig_open_preferences_requested
        )
        pythonenv_status.unregister_ipythonconsole(self)
        statusbar.remove_status_widget(PythonEnvironmentStatus.ID)

        matplotlib_status = statusbar.get_status_widget(MatplotlibStatus.ID)
        matplotlib_status.unregister_ipythonconsole(self)
        statusbar.remove_status_widget(MatplotlibStatus.ID)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        widget = self.get_widget()
        mainmenu = self.get_plugin(Plugins.MainMenu)

        # Connect state check/update logic for edit actions
        edit_menu = mainmenu.get_application_menu(ApplicationMenus.Edit)
        edit_menu.aboutToShow.connect(widget.update_edit_menu)

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
            before_section=HelpMenuSections.Support,
        )

        # Add remote console submenu
        if (
            self.is_plugin_available(Plugins.RemoteClient)
            and not self._is_remote_consoles_menu_added
        ):
            self._add_remote_consoles_menu()

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        self.sig_edit_goto_requested.connect(editor.load)
        self.sig_edit_new.connect(editor.new)

        for run_config in [
            self.python_editor_run_configuration,
            self.ipython_editor_run_configuration,
            self.cython_editor_run_configuration,
            self.pyw_editor_run_configuration
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
            self._save_working_directory
        )
        working_directory.sig_current_directory_changed.connect(
            self.set_current_client_working_directory
        )

    @on_plugin_available(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_available(self):
        pythonpath_manager = self.get_plugin(Plugins.PythonpathManager)
        pythonpath_manager.sig_pythonpath_changed.connect(self.update_path)

    @on_plugin_available(plugin=Plugins.RemoteClient)
    def on_remote_client_available(self):
        self._remote_client.sig_server_stopped.connect(
            self._close_remote_clients
        )
        self._remote_client.sig_server_renamed.connect(
            self._rename_remote_clients
        )
        self._remote_client.sig_server_changed.connect(
            self._on_remote_server_changed
        )
        self._remote_client.sig_connection_established.connect(
            self._on_remote_server_connected
        )
        self._remote_client.sig_connection_lost.connect(
            self._on_remote_server_disconnected
        )

        if (
            self.is_plugin_available(Plugins.MainMenu)
            and not self._is_remote_consoles_menu_added
        ):
            self._add_remote_consoles_menu()

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
        widget = self.get_widget()
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_application_menu(ApplicationMenus.Consoles)

        # Disconnect state check/update logic for edit actions
        edit_menu = mainmenu.get_application_menu(ApplicationMenus.Edit)
        edit_menu.aboutToShow.disconnect(widget.update_edit_menu)

        # IPython documentation menu
        mainmenu.remove_item_from_application_menu(
            IPythonConsoleWidgetMenus.Documentation,
            menu_id=ApplicationMenus.Help
        )

        if self._is_remote_consoles_menu_added:
            mainmenu.remove_item_from_application_menu(
                RemoteConsolesMenus.RemoteConsoles,
                menu_id=ApplicationMenus.Consoles,
            )

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        self.sig_edit_goto_requested.disconnect(editor.load)
        self.sig_edit_new.disconnect(editor.new)

        for run_config in [
            self.python_editor_run_configuration,
            self.ipython_editor_run_configuration,
            self.cython_editor_run_configuration,
            self.pyw_editor_run_configuration
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
            self._save_working_directory
        )
        working_directory.sig_current_directory_changed.disconnect(
            self.set_current_client_working_directory
        )

    @on_plugin_teardown(plugin=Plugins.PythonpathManager)
    def on_pythonpath_manager_teardown(self):
        pythonpath_manager = self.get_plugin(Plugins.PythonpathManager)
        pythonpath_manager.sig_pythonpath_changed.disconnect(self.update_path)

    @on_plugin_teardown(plugin=Plugins.RemoteClient)
    def on_remote_client_teardown(self):
        self._remote_client.sig_server_stopped.disconnect(
            self._close_remote_clients
        )
        self._remote_client.sig_server_renamed.disconnect(
            self._rename_remote_clients
        )
        self._remote_client.sig_server_changed.disconnect(
            self._on_remote_server_changed
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
        projects = self.get_plugin(Plugins.Projects)

        if connection_file is not None:
            # Projects plugin will not restart a console in this case, even if
            # there is a current project path, so go ahead and start a console.
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
        elif projects is not None and projects.get_active_project():
            # If there is a current project path, the Projects plugin will
            # start a console
            pass
        else:
            # If there is no current project path, Projects plugin will not
            # restart a console, so go ahead and start a console
            self.create_new_client(give_focus=False)

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _on_project_loaded(self, path):
        self.get_widget().update_active_project_path(path)

    def _on_project_closed(self):
        self.get_widget().update_active_project_path(None)

    def _update_envs(self, envs):
        self.get_widget().update_envs(envs)

    def _open_interpreter_preferences(self):
        """Open the Preferences dialog in the main interpreter section."""
        self._main.show_preferences()
        preferences = self._main.preferences
        container = preferences.get_container()
        dlg = container.dialog
        index = dlg.get_index_by_name("main_interpreter")
        dlg.set_current_index(index)

    def _save_working_directory(self, dirname):
        """
        Save current working directory on the main widget to start new clients.

        Parameters
        ----------
        new_dir: str
            Path to the new current working directory.
        """
        self.get_widget().save_working_directory(dirname)

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
        jupyter_api = None
        files_api = None
        if server_id is not None:
            jupyter_api = self._remote_client.get_jupyter_api(server_id)
            files_api = self._remote_client.get_file_api(server_id)()

        return self.get_widget().create_client_for_kernel(
            connection_file=connection_file,
            hostname=hostname,
            sshkey=sshkey,
            password=password,
            jupyter_api=jupyter_api,
            files_api=files_api,
            give_focus=give_focus,
            can_close=can_close,
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

    def undo(self) -> None:
        return self.get_widget().current_client_undo()

    def redo(self) -> None:
        return self.get_widget().current_client_redo()

    def cut(self) -> None:
        return self.get_widget().current_client_cut()

    def copy(self) -> None:
        return self.get_widget().current_client_copy()

    def paste(self) -> None:
        return self.get_widget().current_client_paste()

    def select_all(self) -> None:
        return self.get_widget().current_client_select_all()

    def find(self) -> None:
        find_widget = self.get_widget().find_widget
        find_widget.show()
        find_widget.search_text.setFocus()

    def find_next(self) -> None:
        self.get_widget().find_widget.find_next()

    def find_previous(self) -> None:
        self.get_widget().find_widget.find_previous()

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
            cell_text = re.sub(r'(^\s*\n)|(\n\s*$)', '', cell_text)
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
    @qdebounced(timeout=100)
    def set_current_client_working_directory(
        self, directory: str,
        sender_plugin: Optional[str] = None,
        server_id: Optional[str] = None,
    ):
        """
        Set current client working directory.

        Parameters
        ----------
        directory : str
            Path for the new current working directory.
        sender_plugin: str
            Name of the plugin that requested changing the working directory.
            Default is None, which means this plugin did it.

        Returns
        -------
        None.
        """
        # Only update the cwd if this plugin didn't request changing it
        if sender_plugin != self.NAME:
            self.get_widget().set_current_client_working_directory(
                directory, server_id
            )

    def update_path(self, new_path, prioritize):
        """
        Update path on consoles.

        Both parameters have as keys paths and as value if the path
        should be used/is active (True) or not (False)

        Parameters
        ----------
        new_path : list of str
            New state of the Python path handled by Spyder.
        prioritize : bool
            Whether to prioritize Python path in sys.path

        Returns
        -------
        None.
        """
        self.get_widget().update_path(new_path, prioritize)

    # ---- For restarts
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

    # ---- For outside callers (e.g. AI agents)
    # -------------------------------------------------------------------------
    def get_console_shellwidget(self, console_id: Optional[str] = None):
        """
        Get the shellwidget of a console.

        Parameters
        ----------
        console_id : str, optional
            Id of the console, as returned by :meth:`list_consoles` (e.g.
            ``1/A``). By default, the current console.

        Returns
        -------
        ShellWidget or None
            The console's shellwidget, or ``None`` if there's no console
            with that id.
        """
        if console_id is None:
            client = self.get_current_client()
            return client.shellwidget if client is not None else None

        for client in self.get_clients():
            if get_console_id(client) == console_id:
                return client.shellwidget
        return None

    def get_console_id(self, shellwidget=None) -> Optional[str]:
        """
        Get the id of a console (e.g. ``1/A``), as used by the exposed
        methods, from its shellwidget. By default, the current console.
        """
        if shellwidget is None:
            shellwidget = self.get_current_shellwidget()
        client = getattr(shellwidget, "ipyclient", None)
        return get_console_id(client) if client is not None else None

    @expose(read_only=True)
    def list_consoles(self) -> list:
        """
        List the IPython consoles open in Spyder, with their id, name, state
        (idle, busy, debugging or starting), working directory (where
        relative paths in code run there are resolved), which one is the
        current console, who is running code in it (``user``, ``you`` or
        the name of another agent), how many runs are waiting for it, and
        who created it if an agent did (with new_console).
        """
        caller = current_caller()
        current = self.get_current_client()
        consoles = []
        for client in self.get_clients():
            console_id = get_console_id(client)
            shellwidget = client.shellwidget
            scheduler = get_scheduler(shellwidget)

            running_for = None
            if scheduler.is_running_outside_code():
                running_for = self._describe_for(
                    scheduler.get_running_caller(), caller
                )
            elif shellwidget._executing or shellwidget.is_debugging():
                running_for = "user"

            creator = self._console_creators.get(console_id)
            consoles.append(
                {
                    "id": console_id,
                    "name": client.get_name(),
                    "state": get_console_state(shellwidget),
                    "cwd": shellwidget.get_cwd() or None,
                    "current": client is current,
                    "running_for": running_for,
                    "waiting_runs": scheduler.get_waiting(),
                    "created_by": (
                        self._describe_for(creator, caller)
                        if creator is not None
                        else None
                    ),
                }
            )
        return consoles

    @staticmethod
    def _describe_for(who, caller) -> str:
        """Name of ``who`` for ``caller``: ``you`` if it's the same."""
        if who is not None and who == caller:
            return "you"
        return describe_caller(who)

    @expose(name="execute_code")
    def execute_code_with_output(
        self,
        code: str,
        console_id: Optional[str] = None,
        timeout: float = DEFAULT_EXECUTE_TIMEOUT,
    ) -> Future:
        """
        Run Python code in one of Spyder's IPython consoles and get its
        output (stdout, stderr, results and tracebacks) and the figures it
        displays, as images.

        The code runs in the user's live kernel, so variables persist between
        calls, and the user sees the code and its output in the console.
        IPython magics are supported. Figures also appear in Spyder's Plots
        pane.

        If the console is busy (e.g. the user or another agent is running
        code in it), the code waits for it to be free. The user goes first:
        the code doesn't start while they're typing in the console.

        Parameters
        ----------
        code : str
            Python code to run.
        console_id : str, optional
            Id of the console to use, as returned by list_consoles. By
            default, the console currently selected in Spyder.
        timeout : float, optional
            Seconds to wait for the console to be free and the code to finish
            before returning the output collected so far. The code keeps
            running, but it doesn't run if the console is still busy.

        Returns
        -------
        Future
            Resolved with a dict with the ``output`` text, whether the code
            ``raised_exception``, the ``images`` it displayed and ``notes``
            about how the execution ended (e.g. if it's still running).
        """
        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        return run_code(shellwidget, code, timeout)

    @expose
    def interrupt_console(self, console_id: Optional[str] = None) -> str:
        """
        Interrupt the code you're running in an IPython console, like
        pressing Ctrl+C, and cancel your code that is waiting for the
        console. Code run by the user or other agents can't be interrupted.

        Parameters
        ----------
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        """
        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)

        caller = current_caller()
        scheduler = get_scheduler(shellwidget)
        cancelled = scheduler.cancel(caller)
        messages = []
        if cancelled:
            messages.append(f"Cancelled {cancelled} waiting run(s).")

        busy = shellwidget._executing or shellwidget.is_debugging()
        if not busy:
            messages.append("No code was running.")
        elif caller is None or (
            scheduler.is_running_outside_code()
            and scheduler.get_running_caller() == caller
        ):
            # Keep the user's runs waiting in Spyder's queue (e.g. a file
            # they ran with F5), which interrupting the kernel clears
            execute_queue = list(shellwidget._execute_queue)
            shellwidget.interrupt_kernel()
            if caller is not None:
                shellwidget._execute_queue = execute_queue
            messages.append("Interrupted the code.")
        else:
            activity = scheduler.describe_activity()
            message = (
                f"The code running wasn't started by you ({activity}), so "
                f"it wasn't interrupted. Ask the user to stop it if needed."
            )
            if not cancelled:
                raise ExposedCallError(message)
            messages.append(message)

        return " ".join(messages)

    @expose(read_only=True)
    def list_variables(self, console_id: Optional[str] = None) -> Future:
        """
        List the variables defined in an IPython console, with their type,
        size and a short preview of their value, as shown in Spyder's
        Variable Explorer. Use execute_code to inspect a variable in more
        detail.

        Parameters
        ----------
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.

        Returns
        -------
        Future
            Resolved with a list of dicts with the ``name``, ``type``,
            ``size`` and ``value`` of each variable.
        """
        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        check_idle(shellwidget)
        return request_variables(shellwidget)

    @expose
    def new_console(
        self,
        name: Optional[str] = None,
        wdir: Optional[str] = None,
    ) -> Future:
        """
        Open a new IPython console with its own kernel, e.g. to run long or
        risky computations without blocking or changing the user's console.
        It doesn't share variables with other consoles. The console the user
        has selected doesn't change, so pass the returned id as console_id
        to the other tools to use it.

        Parameters
        ----------
        name : str, optional
            Name for the console's tab, e.g. the agent's name.
        wdir : str, optional
            Working directory of the new console. By default, the one Spyder
            uses for new consoles.

        Returns
        -------
        Future
            Resolved with the ``id`` and ``name`` of the console once its
            kernel is ready.
        """
        if wdir is not None and not osp.isdir(wdir):
            raise ExposedCallError(f"{wdir} is not a directory.")

        previous = self.get_current_shellwidget()
        client = self.get_widget().create_new_client(
            give_focus=False, given_name=name, initial_cwd=wdir
        )
        if client is None:
            raise ExposedCallError("The console couldn't be created.")
        if current_caller() is not None:
            self._console_creators[get_console_id(client)] = current_caller()

        # Keep the console the user is working in selected
        if previous is not None:
            self.set_current_shellwidget(previous)

        future: Future = Future()
        shellwidget = client.shellwidget
        timer = QTimer(shellwidget)
        timer.setSingleShot(True)

        def finish(error=None):
            timer.stop()
            try:
                shellwidget.sig_prompt_ready.disconnect(on_ready)
            except (TypeError, RuntimeError):
                pass
            if future.done():
                return
            if error is not None:
                future.set_exception(ExposedCallError(error))
            else:
                future.set_result(
                    {"id": get_console_id(client), "name": client.get_name()}
                )

        def on_ready():
            if shellwidget.spyder_kernel_ready:
                finish()

        shellwidget.sig_prompt_ready.connect(on_ready)
        timer.timeout.connect(
            lambda: finish(
                "The console's kernel didn't start in time. Check the "
                "console for errors."
            )
        )
        timer.start(NEW_CONSOLE_TIMEOUT * 1000)
        return future

    @expose(read_only=True)
    def inspect_variable(
        self, name: str, console_id: Optional[str] = None
    ) -> Future:
        """
        Get a summary of a variable in an IPython console without running
        code in it: the type and, depending on it, the shape, dtypes, missing
        values, first rows and statistics (DataFrames and Series), the
        shape, dtype and range (arrays), the length and a preview
        (collections) or the repr (other objects).

        Parameters
        ----------
        name : str
            Name of the variable, or an attribute of it (e.g. ``df`` or
            ``model.coef_``).
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        """
        check_name(name)
        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        check_idle(shellwidget)
        return call_kernel_helper(
            shellwidget, spyder_summarize_variable, repr(name), "globals()"
        )

    @expose(read_only=True)
    def get_object_help(
        self, name: str, console_id: Optional[str] = None
    ) -> Future:
        """
        Get the signature, docstring, module and package version of a
        function, class or module, as installed in the environment of an
        IPython console. Objects don't need to be imported in the console
        (e.g. ``pandas.DataFrame.merge``).

        Parameters
        ----------
        name : str
            Name of the object, e.g. ``np.linspace`` or
            ``pandas.DataFrame.merge``.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        """
        check_name(name)
        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        check_idle(shellwidget)
        return call_kernel_helper(
            shellwidget, spyder_object_help, repr(name), "globals()"
        )

    @expose(read_only=True)
    def get_console_history(
        self, count: int = 50, console_id: Optional[str] = None
    ) -> Future:
        """
        Get the last inputs run in an IPython console since its kernel
        started (by the user or with execute_code), oldest first. Use it to
        see what the user did, e.g. to turn it into a script.

        Parameters
        ----------
        count : int, optional
            Number of inputs to get.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        """
        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        check_idle(shellwidget)
        return call_kernel_helper(
            shellwidget, spyder_input_history, str(int(count))
        )

    @expose
    def run_file(
        self,
        filename: str,
        args: str = "",
        wdir: Optional[str] = None,
        console_id: Optional[str] = None,
        timeout: float = DEFAULT_EXECUTE_TIMEOUT,
    ) -> Future:
        """
        Run a Python file in an IPython console, like pressing F5 in Spyder,
        and get its output. If the file is open in the Editor, its current
        contents run, including unsaved changes.

        Parameters
        ----------
        filename : str
            Absolute path of the file.
        args : str, optional
            Command line arguments for the file.
        wdir : str, optional
            Working directory to run the file in. By default, the file's
            directory.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        timeout : float, optional
            Seconds to wait for the console to be free and the file to finish
            before returning the output collected so far. It keeps running.

        Returns
        -------
        Future
            Resolved like the one of ``execute_code_with_output``.
        """
        filename = osp.abspath(filename)
        if not osp.isfile(filename):
            raise ExposedCallError(f"{filename} doesn't exist.")

        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)

        line = build_run_line(shellwidget, filename, args, wdir)
        return run_code(shellwidget, line, timeout)

    @expose(name="run_cell")
    def run_cell_with_output(
        self,
        filename: str,
        cell: Union[int, str],
        console_id: Optional[str] = None,
        timeout: float = DEFAULT_EXECUTE_TIMEOUT,
    ) -> Future:
        """
        Run a cell (a block delimited by ``# %%`` comments) of a file open in
        the Editor in an IPython console, like pressing Shift+Enter in Spyder,
        and get its output. The cell's current contents in the Editor run,
        including unsaved changes.

        Parameters
        ----------
        filename : str
            Absolute path of the file. It's opened in the Editor if needed.
        cell : int or str
            Index of the cell (0-based, the code before the first ``# %%``
            is cell 0 if there's any) or its name (the text after ``# %%``).
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        timeout : float, optional
            Seconds to wait for the console to be free and the cell to finish
            before returning the output collected so far. It keeps running.

        Returns
        -------
        Future
            Resolved like the one of ``execute_code_with_output``.
        """
        filename = osp.abspath(filename)
        if not osp.isfile(filename):
            raise ExposedCallError(f"{filename} doesn't exist.")

        shellwidget = self.get_console_shellwidget(console_id)
        check_ready(shellwidget, console_id)
        if not shellwidget.is_spyder_kernel:
            raise ExposedCallError(
                "The console is not running a Spyder kernel, so it can't run "
                "cells. Use execute_code with the cell's code instead."
            )

        # The kernel gets the cell's code from the Editor
        editor = self.get_plugin(Plugins.Editor, error=False)
        if editor is None:
            raise ExposedCallError("Running cells needs Spyder's Editor.")
        if editor.get_codeeditor_for_filename(filename) is None:
            editor.load(filename)

        option = "-i" if isinstance(cell, int) else "-n"
        line = "%runcell " + shlex.join([option, str(cell), filename])
        return run_code(shellwidget, line, timeout)

    # ---- For the Remote client plugin
    # -------------------------------------------------------------------------
    @cached_property
    def _remote_client(self):
        return self.get_plugin(Plugins.RemoteClient)

    def _add_remote_consoles_menu(self):
        """Add remote consoles submenu to the Consoles menu."""
        widget = self.get_widget()
        widget.setup_remote_consoles_submenu(render=False)

        menu = widget.get_menu(RemoteConsolesMenus.RemoteConsoles)
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            menu,
            menu_id=ApplicationMenus.Consoles,
            section=ConsolesMenuSections.New,
            before=IPythonConsoleWidgetActions.ConnectToKernel,
        )

        self._is_remote_consoles_menu_added = True

    @Slot(str)
    def _close_remote_clients(self, server_id):
        self.get_widget().close_remote_clients(server_id)

    @Slot(str)
    def _rename_remote_clients(self, server_id):
        self.get_widget().rename_remote_clients(server_id)

    @Slot()
    def _on_remote_server_changed(self):
        self.get_widget().setup_remote_consoles_submenu()

    @Slot(str)
    def _on_remote_server_connected(self, server_id):
        self.get_widget().setup_server_consoles_submenu(server_id)

    @Slot(str)
    def _on_remote_server_disconnected(self, server_id):
        # Try to reconnect any remote consoles bound to this server before
        # altering menus.
        self.get_widget().reconnect_remote_clients(server_id)
        self.get_widget().clear_server_consoles_submenu(server_id)

    # ---- Methods related to the Application plugin
    # ------------------------------------------------------------------------
    def _enable_edit_action(self, action_name: str, enabled: bool) -> None:
        """Enable or disable edit action for this plugin."""
        application = self.get_plugin(Plugins.Application, error=False)
        if application:
            application.enable_edit_action(action_name, enabled, self.NAME)

    def _enable_search_action(self, action_name: str, enabled: bool) -> None:
        """Enable or disable search action for this plugin."""
        application = self.get_plugin(Plugins.Application, error=False)
        if application:
            application.enable_search_action(action_name, enabled, self.NAME)

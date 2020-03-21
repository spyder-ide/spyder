# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console main widget based on QtConsole.
"""

# Standard library imports
import os
import os.path as osp
import sys
import traceback
import uuid

# Third party imports
from jupyter_client.connect import find_connection_file
from jupyter_core.paths import jupyter_config_dir, jupyter_runtime_dir
from qtconsole.client import QtKernelClient
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import (QActionGroup, QApplication, QHBoxLayout,
                            QMessageBox, QVBoxLayout, QWidget, QLabel,
                            QApplication)
from traitlets.config.loader import Config, load_pyconfig_files
from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.widgets import PluginMainWidget
from spyder.api.translations import get_translation
from spyder.config.base import (get_conf_path, get_home_dir,
                                running_under_pytest)
from spyder.config.gui import is_dark_interface
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
from spyder.plugins.ipythonconsole.utils.style import create_qss_style
from spyder.plugins.ipythonconsole.widgets import (ClientWidget,
                                                   KernelConnectionDialog)
from spyder.plugins.ipythonconsole.widgets.client import ClientWidgetActions
from spyder.py3compat import PY38_OR_MORE
from spyder.utils import encoding
from spyder.utils import programs, sourcecode
from spyder.utils.misc import get_error_match, remove_backslashes
from spyder.widgets.browser import WebView
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.tabs import Tabs


# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
if is_dark_interface():
    MAIN_BG_COLOR = '#19232D'
else:
    MAIN_BG_COLOR = 'white'


class IPythonConsoleWidgetActions:
    CreateNewClient = 'create_new_client_action'
    CreateCythonClient = 'create_cython_client_action'
    CreateSymPyClient = 'create_sympy_client_action'
    CreatePyLabClient = 'create_pylab_client_action'
    Restart = 'restart_action'
    RemoveAllVariables = 'remove_all_variables_action'
    Interrupt = 'interrupt_action'
    ConnectToKernel = 'connect_to_kernel_action'
    RenameTab = 'rename_tab_action'
    InspectObject = 'inspect_object_action'
    ClearConsole = 'clear_console_action'
    NewTab = 'new_tab_action'
    ResetNamespace = 'reset_namespace_action'
    ArrayInline = 'arrya_iniline_action'
    ArrayTable = 'arrya_table_action'
    ClearLine = 'clear_line'


class IPythonConsoleWidgetOptionsMenus:
    SpecialConsoles = 'special_consoles_submenu'


class IPythonConsoleWidgetConsolesMenusSection:
    Main = 'main_section'


class IPythonConsoleWidgetOptionsMenuSections:
    Consoles = 'consoles_section'
    Edit = 'edit_section'
    View = 'view_section'


# --- Widgets
# ----------------------------------------------------------------------------
class IPythonConsoleWidget(PluginMainWidget):
    """
    IPython Console main widget

    This is a widget with tabs where each one is a ClientWidget
    """
    DEFAULT_OPTIONS = {
        'ask_before_closing': False,
        'ask_before_restart': True,
        'buffer_size': 500,
        'color_scheme': 'spyder/dark',
        'css_path': '',
        'completion_type': 0,
        'connect_to_help': False,
        'connection_settings': {},
        'use_default_main_interpreter': sys.executable,
        'in_prompt': '',
        'main_interpreter_executable': None,
        'out_prompt': '',
        'pylab/autoload': False,
        'save_all_before_run': True,
        'show_calltips': True,
        'show_banner': True,
        'show_elapsed_time': False,
        'show_reset_namespace_warning': True,
        'symbolic_math': False,
        'use_pager': False,
        'pylab': True,
        # Debugger
        'breakpoints': {},
        'pdb_ignore_lib': False,
        'pdb_execute_events': False,
        # Workingdir
        'console/use_project_or_home_directory': False,
        'console/use_fixed_directory': False,
        'console/use_cwd': True,
        'console/fixed_directory': get_home_dir(),
        'startup/use_fixed_directory': False,
        'startup/fixed_directory': get_home_dir(),
        # Kernel Spec
        'pylab/backend': 0,
        'pylab/inline/figure_format': 0,
        'pylab/inline/resolution': 72,
        'pylab/inline/width': 6,
        'pylab/inline/height': 4,
        'pylab/inline/bbox_inches': True,
        'startup/run_lines': '',
        'startup/use_run_file': False,
        'startup/run_file': '',
        'greedy_completer': False,
        'jedi_completer': False,
        'autocall': 0,
        'hide_cmd_windows': True,
        # Testing options
        '_testing': False,
        '_test_dir': None,
        '_test_no_stderr': False,
    }

    # Signals
    sig_current_tab_changed = Signal()
    """
    This signal is emitted when a tab changes.
    """

    sig_working_directory_changed = Signal(str)
    """
    This signal is emitted when the current working directory changes.

    Parameters
    ----------
    new_working_directory: str
        Working directory path.
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

    sig_focus_changed = Signal()
    """
    FIXME:
    """

    sig_pdb_state_changed = Signal(bool, dict)
    """
    FIXME:
    """

    sig_spyder_python_path_update_requested = Signal()
    """
    FIXME:
    """

    sig_exception_occurred = Signal(dict)
    """
    FIXME:
    """

    sig_shellwidget_process_started = Signal(object)
    """
    This signal is emitted when a shellwidget process starts.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_shellwidget_process_finished = Signal(object)
    """
    This signal is emitted when a shellwidget process finishes.

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

    sig_history_requested = Signal(str)
    """
    FIXME:
    """

    sig_append_to_history_requested = Signal(str, str)
    """
    FIXME:
    """

    sig_render_plain_text_requested = Signal(str)
    """
    FIXME:
    """

    sig_render_rich_text_requested = Signal(str, bool)
    """
    FIXME:
    """

    sig_help_requested = Signal(dict)
    """
    FIXME:
    """

    # Error messages
    permission_error_msg = _(
        "The directory {} is not writable and it is required to create "
        "IPython consoles. Please make it writable."
    )

    def __init__(self, name, plugin, parent, options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent, options)

        # Attributes
        self._font = None
        self._rich_font = None
        self.clients = []
        self.client_running_state = {}
        self.client_time_state = {}
        self.filenames = []
        self.menu_actions = None
        self.master_clients = 0
        self.mainwindow_close = False
        self.create_new_client_if_empty = True
        self.css_path = self.get_option('css_path')
        self.run_cell_filename = None
        self.interrupt_action = None

        # Attrs for testing
        self._testing = self.get_option('_testing')
        self._test_dir = self.get_option('_test_dir')
        self._test_no_stderr = self.get_option('_test_no_stderr')

        # Create temp dir on testing to save kernel errors
        if self._test_dir is not None:
            if not osp.isdir(osp.join(self._test_dir)):
                os.makedirs(osp.join(self._test_dir))

        # Widgets
        self.time_label = QLabel("")
        self.stop_button = self.create_toolbutton(
            'interrupt',
            text=_("Interrupt kernel"),
            tip=_("Interrupt kernel"),
            icon=self.create_icon('stop'),
            triggered=self.interrupt_kernel,
        )
        self.reset_button = self.create_toolbutton(
            'reset',
            text=_("Remove all variables"),
            tip=_("Remove all variables from kernel namespace"),
            icon=self.create_icon("editdelete"),
            triggered=self.reset_kernel,
        )
        self.infowidget = WebView(self)
        self.tabwidget = Tabs(
            self,
            # menu=self._options_menu,  # FIXME:
            # actions=self.menu_actions,
            rename_tabs=True,
            split_char='/',
            split_index=0,
        )
        self.find_widget = FindReplace(self)
        self.tabwidget.hide()
        self.find_widget.hide()
        self.infowidget.hide()

        # Widget setup
        self.setAcceptDrops(True)
        self.infowidget.set_background_color(MAIN_BG_COLOR)
        self.tabwidget.set_close_function(self.close_client)
        # if (hasattr(self.tabwidget, 'setDocumentMode')
        #         and not sys.platform == 'darwin'):
        #     # Don't set document mode to true on OSX because it generates
        #     # a crash when the console is detached from the main window
        #     # Fixes spyder-ide/spyder#561.
        #     self.tabwidget.setDocumentMode(True)

        # Layout
        layout = QVBoxLayout()
        if sys.platform == 'darwin':
            tab_container = QWidget()
            tab_container.setObjectName('tab-container')
            tab_layout = QHBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabwidget)
            layout.addWidget(tab_container)
        else:
            layout.addWidget(self.tabwidget)

        layout.addWidget(self.infowidget)
        layout.addWidget(self.find_widget)
        self.setLayout(layout)

        # Signals
        self.tabwidget.currentChanged.connect(self.refresh)
        self.tabwidget.currentChanged.connect(self.sig_current_tab_changed)
        self.tabwidget.sig_tab_moved.connect(self.move_tab)
        self.tabwidget.sig_name_changed.connect(self.rename_tabs_after_change)

        # Needed to start Spyder in Windows with Python 3.8
        # See spyder-ide/spyder#11880
        self._init_asyncio_patch()

        self.sig_exception_occurred.connect(lambda data: print(data))

    # --- PLuginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('IPython console')

    def get_focus_widget(self):
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client.get_control()

    def setup(self, options=DEFAULT_OPTIONS):
        create_client_action = self.create_action(
            IPythonConsoleWidgetActions.CreateNewClient,
            text=_("New console (default settings)"),
            icon=self.create_icon('ipython_console'),
            triggered=self.create_new_client,
        )
        restart_action = self.create_action(
            IPythonConsoleWidgetActions.Restart,
            text=_("Restart kernel"),
            icon=self.create_icon('restart'),
            triggered=self.restart_kernel,
        )
        reset_action = self.create_action(
            IPythonConsoleWidgetActions.RemoveAllVariables,
            text=_("Remove all variables"),
            icon=self.create_icon('editdelete'),
            triggered=self.reset_kernel,
        )
        self.interrupt_action = self.create_action(
            IPythonConsoleWidgetActions.Interrupt,
            text=_("Interrupt kernel"),
            icon=self.create_icon('stop'),
            triggered=self.interrupt_kernel,
        )
        connect_to_kernel_action = self.create_action(
            IPythonConsoleWidgetActions.ConnectToKernel,
            text=_("Connect to an existing kernel"),
            tip=_("Open a new IPython console connected to an existing "
                  "kernel"),
            triggered=self.create_client_for_kernel,
        )
        rename_tab_action = self.create_action(
            IPythonConsoleWidgetActions.RenameTab,
            text=_("Rename tab"),
            icon=self.create_icon('rename'),
            triggered=self.tab_name_editor,
        )

        # From client:
        env_action = self.create_action(
            ClientWidgetActions.ShowEnvironmentVariables,
            text=_("Show environment variables"),
            icon=self.create_icon('environ'),
            triggered=self.request_env,
        )

        syspath_action = self.create_action(
            ClientWidgetActions.ShowSystemPath,
            text=_("Show sys.path contents"),
            icon=self.create_icon('syspath'),
            triggered=self.request_syspath,
        )

        self.show_time_action = self.create_action(
            ClientWidgetActions.ToggleElapsedTime,
            text=_("Show elapsed time"),
            toggled=lambda val: self.set_option('show_elapsed_time', val),
            initial=self.get_option('show_elapsed_time')
        )

        options_menu = self.get_options_menu()
        consoles_submenu = self.create_menu(
            IPythonConsoleWidgetOptionsMenus.SpecialConsoles,
            _('Special consoles'))

        for item in [create_client_action, consoles_submenu,
                     connect_to_kernel_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=IPythonConsoleWidgetOptionsMenuSections.Consoles,
            )

        for item in [self.interrupt_action, restart_action, reset_action,
                     rename_tab_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=IPythonConsoleWidgetOptionsMenuSections.Edit,
            )

        for item in [env_action, syspath_action, self.show_time_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=IPythonConsoleWidgetOptionsMenuSections.View,
            )

        self.update_execution_state_kernel()

        # inspect_action = self.create_action(
        #     IPythonConsoleWidgetActions.InspectObject,
        #     text=_('Inspect current object'),
        #     triggered=self.inspect_current_object,
        # )
        # clear_console_action = self.create_action(
        #     IPythonConsoleWidgetActions.ClearConsole,
        #     text=_('Clear shell'),
        #     triggered=self.clear_console,
        #     shortcut_context='console',
        # )
        # new_tab_action = self.create_action(
        #     IPythonConsoleWidgetActions.NewTab,
        #     triggered=self.new_client,
        #     text=_('new tab'),
        # )
        # reset_namespace_action = self.create_action(
        #     IPythonConsoleWidgetActions.ResetNamespace,
        #     text=_('reset namespace'),
        #     triggered=lambda: self._reset_namespace(),
        # )
        # array_inline_action = self.create_action(
        #     IPythonConsoleWidgetActions.ArrayInline,
        #     text=_('enter array inline'),
        #     triggered=self._control.enter_array_inline,
        #     shortcut_context='array_builder',
        # )
        # array_table_action = self.create_action(
        #     IPythonConsoleWidgetActions.ArrayTable,
        #     self._control.enter_array_table,
        #     text=_('enter array table'),
        #     shortcut_context='array_builder',
        # )
        # clear_line_action = self.create_action(
        #     IPythonConsoleWidgetActions.ClearLine,
        #     text='clear line',
        #     triggered=self.ipyclient.clear_line,
        #     shortcut_context='console',
        # )

        # self.add_corner_widget(
        #     PluginMainWidgetWidgets.Spinner,
        #     self._spinner,
        # )

        # Check for a current client. Since it manages more actions.
        # FIXME: what does thi mean?
        # client = self.get_current_client()
        # if client:
        #     return client.get_options_menu()

        self.setup_python(options)
        self.add_corner_widget('reset', self.reset_button)
        self.add_corner_widget('start_interrupt', self.stop_button)
        self.add_corner_widget('timer', self.time_label)

    def update_actions(self):
        # FIXME: Propagate actions to children. Check with Cmd+I to display
        # help!
        client = self.get_current_client()
        running = self.client_running_state.get(client, False)

        if self.get_option("show_elapsed_time"):
            time_text = self.client_time_state.get(client, "")
            self.time_label.setText(time_text)

        self.stop_button.setEnabled(running)
        self.interrupt_action.setEnabled(running)

        # This avoids disabling automatically the button when
        # re-running files on dedicated consoles.
        # See spyder-ide/spyder#5958.
        if client and not client.shellwidget._executing:
            self.stop_button.setDisabled(True)
            self.interrupt_action.setDisabled(True)

    def on_option_update(self, option, value):
        # FIXME: Is this needed?
        if option == 'breakpoints':
            self.set_spyder_breakpoints()
        elif option == 'pdb_ignore_lib':
            self.set_pdb_ignore_lib()
        elif option == 'pdb_execute_events':
            self.set_pdb_execute_events()
        elif option == 'show_elapsed_time':
            self.time_label.setVisible(value)

    # --- Private API
    # ------------------------------------------------------------------------
    def _update_client_time(self, client, text):
        self.client_time_state[client] = text
        self.update_actions()

    def _update_client_state(self, client, running=False):
        self.client_running_state[client] = running
        self.update_actions()

    def _init_asyncio_patch(self):
        """
        Same workaround fix as https://github.com/ipython/ipykernel/pull/456
        Set default asyncio policy to be compatible with tornado
        Tornado 6 (at least) is not compatible with the default
        asyncio implementation on Windows
        Pick the older SelectorEventLoopPolicy on Windows
        if the known-incompatible default policy is in use.
        Do this as early as possible to make it a low priority and overrideable
        ref: https://github.com/tornadoweb/tornado/issues/2608
        TODO: if/when tornado supports the defaults in asyncio,
               remove and bump tornado requirement for py38
        Based on: jupyter/qtconsole#406
        """
        if os.name == 'nt' and PY38_OR_MORE:
            import asyncio
            try:
                from asyncio import (
                    WindowsProactorEventLoopPolicy,
                    WindowsSelectorEventLoopPolicy,
                )
            except ImportError:
                # not affected
                pass
            else:
                if isinstance(
                        asyncio.get_event_loop_policy(),
                        WindowsProactorEventLoopPolicy):
                    # WindowsProactorEventLoopPolicy is not compatible
                    # with tornado 6 fallback to the pre-3.8
                    # default of Selector
                    asyncio.set_event_loop_policy(
                        WindowsSelectorEventLoopPolicy())

    def _new_connection_file(self):
        """
        Generate a new connection file.

        Taken from jupyter_client/console_app.py
        Licensed under the BSD license
        """
        # Check if jupyter_runtime_dir exists (Spyder addition)
        if not osp.isdir(jupyter_runtime_dir()):
            try:
                os.makedirs(jupyter_runtime_dir())
            except (IOError, OSError):
                return None

        connection_file = ''
        while not connection_file:
            ident = str(uuid.uuid4()).split('-')[-1]
            connection_file = osp.join(jupyter_runtime_dir(),
                                       'kernel-%s.json' % ident)
            connection_file = (connection_file
                               if not os.path.exists(connection_file) else '')

        return connection_file

    def _create_client_for_kernel(self, connection_file, hostname, sshkey,
                                  password):
        # Verifying if the connection file exists
        try:
            cf_path = osp.dirname(connection_file)
            cf_filename = osp.basename(connection_file)

            # To change a possible empty string to None
            cf_path = cf_path if cf_path else None
            connection_file = find_connection_file(filename=cf_filename,
                                                   path=cf_path)
        except (IOError, UnboundLocalError):
            QMessageBox.critical(
                self,
                _('IPython'),
                _("Unable to connect to <b>%s</b>") % connection_file,
            )
            return

        # Getting the master id that corresponds to the client
        # (i.e. the i in i/A)
        master_id = None
        given_name = None
        external_kernel = False
        slave_ord = ord('A') - 1
        kernel_manager = None

        for cl in self.get_clients():
            if connection_file in cl.connection_file:
                if cl.get_kernel() is not None:
                    kernel_manager = cl.get_kernel()

                connection_file = cl.connection_file
                if master_id is None:
                    master_id = cl.id_['int_id']

                given_name = cl.given_name
                new_slave_ord = ord(cl.id_['str_id'])
                if new_slave_ord > slave_ord:
                    slave_ord = new_slave_ord

        # If we couldn't find a client with the same connection file,
        # it means this is a new master client
        if master_id is None:
            self.master_clients += 1
            master_id = str(self.master_clients)
            external_kernel = True

        # Set full client name
        client_id = dict(int_id=master_id, str_id=chr(slave_ord + 1))

        # Creating the client
        show_elapsed_time = self.get_option('show_elapsed_time')
        reset_warning = self.get_option('show_reset_namespace_warning')
        ask_before_restart = self.get_option('ask_before_restart')

        client = ClientWidget(
            self,
            id_=client_id,
            given_name=given_name,
            history_filename=get_conf_path('history.py'),
            config_options=self.config_options(),
            additional_options=self.additional_options(),
            interpreter_versions=self.interpreter_versions(),
            connection_file=connection_file,
            menu_actions=self.menu_actions,
            hostname=hostname,
            external_kernel=external_kernel,
            slave=True,
            show_elapsed_time=show_elapsed_time,
            reset_warning=reset_warning,
            ask_before_restart=ask_before_restart,
            css_path=self.css_path,
        )

        # Change stderr_dir if requested
        if self._test_dir is not None:
            client.stderr_dir = self._test_dir

        # Create kernel client
        kernel_client = QtKernelClient(connection_file=connection_file)

        # This is needed for issue spyder-ide/spyder#9304.
        try:
            kernel_client.load_connection_file()
        except Exception as e:
            QMessageBox.critical(
                self,
                _('Connection error'),
                _("An error occurred while trying to load "
                  "the kernel connection file. The error "
                  "was:\n\n") + str(e),
            )
            return

        if hostname is not None:
            try:
                connection_info = dict(
                    ip=kernel_client.ip,
                    shell_port=kernel_client.shell_port,
                    iopub_port=kernel_client.iopub_port,
                    stdin_port=kernel_client.stdin_port,
                    hb_port=kernel_client.hb_port,
                )
                newports = self.tunnel_to_kernel(connection_info, hostname,
                                                 sshkey, password)
                (kernel_client.shell_port,
                 kernel_client.iopub_port,
                 kernel_client.stdin_port,
                 kernel_client.hb_port) = newports
            except Exception as e:
                QMessageBox.critical(
                    self,
                    _('Connection error'),
                    _("Could not open ssh tunnel. The "
                      "error was:\n\n") + str(e),
                )
                return

        # Assign kernel manager and client to shellwidget
        kernel_client.start_channels()
        shellwidget = client.shellwidget
        shellwidget.set_kernel_client_and_manager(
            kernel_client, kernel_manager)

        shellwidget.sig_exception_occurred.connect(
            self.sig_exception_occurred)

        if external_kernel:
            shellwidget.sig_is_spykernel.connect(
                self.connect_external_kernel)
            shellwidget.is_spyder_kernel()

        # Set elapsed time, if possible
        if not external_kernel:
            self.set_elapsed_time(client)

        # Adding a new tab for the client
        self.add_tab(client, name=client.get_name())

        # Register client
        self.register_client(client)

    def _process_started(self, client):
        self.sig_shellwidget_process_started.emit(client.shellwidget)

    def _process_finished(self, client):
        try:
            self.sig_shellwidget_process_finished.emit(client.shellwidget)
        except RuntimeError:
            pass

    # --- API
    # ------------------------------------------------------------------------
    def update_font(self, font, rich_font):
        self._font = font
        self._rich_font = rich_font

        if self.infowidget:
            self.infowidget.set_font(rich_font)

        for client in self.clients:
            client.set_font(font)

    def close_clients(self):
        for client in self.clients:
            client.shutdown()
            client.remove_stderr_file()
            client.dialog_manager.close_all()
            client.close()

    # def toggle_view(self, checked):
    #     """Toggle view"""
    #     if checked:
    #         self.dockwidget.show()
    #         self.dockwidget.raise_()
    #         # Start a client in case there are none shown
    #         if not self.clients:
    #             if self.main.is_setting_up:
    #                 self.create_new_client(give_focus=False)
    #             else:
    #                 self.create_new_client(give_focus=True)
    #     else:
    #         self.dockwidget.hide()

    def refresh(self):
        """Refresh tabwidget."""
        client = None
        if self.tabwidget.count():
            client = self.tabwidget.currentWidget()

            # Decide what to show for each client
            if client.info_page != client.blank_page:
                # Show info_page if it has content
                client.set_info_page()
                client.shellwidget.hide()
                client.layout.addWidget(self.infowidget)
                self.infowidget.show()
            else:
                self.infowidget.hide()
                client.shellwidget.show()

            # Give focus to the control widget of the selected tab
            control = client.get_control()
            control.setFocus()

            # # Create corner widgets
            # buttons = [[b, -7] for b in client.get_toolbar_buttons()]
            # buttons = sum(buttons, [])[:-1]
            # widgets = [client.create_time_label()] + buttons
        else:
            control = None
            widgets = []

        # self.tabwidget.set_corner_widgets({Qt.TopRightCorner: widgets})
        self.find_widget.set_editor(control)

        if client:
            sw = client.shellwidget
            self.sig_shellwidget_changed.emit(sw)
            self.sig_pdb_state_changed.emit(sw.in_debug_loop(),
                                            sw.get_pdb_last_step())

        self.update_tabs_text()
        self.update_actions()

        # FIXME:
        # self.sig_update_plugin_title.emit()

    # --- API (for clients)
    # ------------------------------------------------------------------------
    def get_clients(self):
        """Return clients list."""
        return [cl for cl in self.clients if isinstance(cl, ClientWidget)]

    def get_focus_client(self):
        """Return current client with focus, if any."""
        widget = QApplication.focusWidget()
        for client in self.get_clients():
            if widget is client or widget is client.get_control():
                return client

    def get_current_client(self):
        """Return the currently selected client."""
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client

    def get_current_shellwidget(self):
        """Return the shellwidget of the current client."""
        client = self.get_current_client()
        if client is not None:
            return client.shellwidget

    def run_cell(self, code, cell_name, filename, run_cell_copy,
                 function='runcell'):
        """Run cell in current or dedicated client."""

        def norm(text):
            return remove_backslashes(str(text))

        self.run_cell_filename = filename

        # Select client to execute code on it
        client = self.get_client_for_file(filename)
        if client is None:
            client = self.get_current_client()

        if client is not None:
            # Internal kernels, use runcell
            if client.get_kernel() is not None and not run_cell_copy:
                line = str("{}({}, '{}')").format(
                    str(function),
                    repr(cell_name),
                    norm(filename).replace("'", r"\'"),
                )

            # External kernels and run_cell_copy, just execute the code
            else:
                line = code.strip()

            try:
                if client.shellwidget._executing:
                    # Don't allow multiple executions when there's
                    # still an execution taking place
                    # Fixes spyder-ide/spyder#7293.
                    pass
                elif (client.shellwidget.in_debug_loop()):
                    client.shellwidget.pdb_execute('!' + line)
                else:
                    self.execute_code(line)
            except AttributeError:
                pass

            self.change_visibility(True)
        else:
            # XXX: not sure it can really happen
            QMessageBox.warning(
                self,
                _('Warning'),
                _("No IPython console is currently available "
                  "to run <b>{}</b>.<br><br>Please open a new "
                  "one and try again.").format(osp.basename(filename)),
                QMessageBox.Ok,
            )

    def debug_cell(self, code, cell_name, filename, run_cell_copy):
        """Debug current cell."""
        self.run_cell(code, cell_name, filename, run_cell_copy, 'debugcell')

    def set_current_client_working_directory(self, directory):
        """Set current client working directory."""
        shellwidget = self.get_current_shellwidget()
        if shellwidget is not None:
            shellwidget.set_cwd(directory)

    # name is wrong since this is triggered by a child, but
    # calling this directly will not change the child shells.
    # def set_working_directory(self, dirname):
    #     """
    #     Set current working directory.

    #     Emit a signal so other plugin can act accordingly.
    #     """
    #     if dirname:
    #         self.sig_current_working_directory_changed.emit(dirname)
    #     #     self.main.workingdirectory.chdir(dirname,
    #                                            refresh_explorer=True,
    #     #                                      refresh_console=False)

    def update_working_directory(self):
        """Update working directory to console cwd."""
        shellwidget = self.get_current_shellwidget()
        if shellwidget is not None:
            shellwidget.update_cwd()

    def update_path(self, path_dict, new_path_dict):
        """Update path on consoles."""
        for client in self.get_clients():
            shell = client.shellwidget
            if shell is not None:
                self.sig_spyder_python_path_update_requested.emit()
                # self.main.get_spyder_pythonpath()
                shell.update_syspath(path_dict, new_path_dict)

    def execute_code(self, lines, current_client=True, clear_variables=False):
        """Execute code instructions."""
        sw = self.get_current_shellwidget()
        if sw is not None:
            if not current_client:
                # Clear console and reset namespace for dedicated clients.
                # See spyder-ide/spyder#5748.
                try:
                    sw.sig_prompt_ready.disconnect()
                except TypeError:
                    pass

                sw.reset_namespace(warning=False)
            elif current_client and clear_variables:
                sw.reset_namespace(warning=False)

            # Needed to handle an error when kernel_client is none.
            # See spyder-ide/spyder#6308.
            try:
                sw.execute(str(lines))
            except AttributeError:
                pass

            self.activateWindow()
            self.get_current_client().get_control().setFocus()

    def pdb_execute(self, line, hidden=False, echo_code=False):
        sw = self.get_current_shellwidget()
        if sw is not None:
            # Needed to handle an error when kernel_client is None.
            # See spyder-ide/spyder#7578.
            try:
                sw.set_pdb_echo_code(echo_code)
                sw.pdb_execute(line, hidden)
            except AttributeError:
                pass

    def get_pdb_state(self):
        """Get debugging state of the current console."""
        sw = self.get_current_shellwidget()
        if sw is not None:
            return sw.in_debug_loop()

        return False

    def get_pdb_last_step(self):
        """Get last pdb step of the current console."""
        sw = self.get_current_shellwidget()
        if sw is not None:
            return sw.get_pdb_last_step()

        return {}

    def check_pdb_state(self):
        """
        Check if actions need to be taken checking the last pdb state.
        """
        pdb_state = self.get_pdb_state()
        if pdb_state:
            pdb_last_step = self.get_pdb_last_step()
            sw = self.get_current_shellwidget()
            if 'fname' in pdb_last_step and sw is not None:
                fname = pdb_last_step['fname']
                line = pdb_last_step['lineno']
                self.pdb_has_stopped(fname, line, sw)

    @Slot()
    @Slot(bool)
    @Slot(str)
    @Slot(bool, str)
    @Slot(bool, bool)
    @Slot(bool, str, bool)
    def create_new_client(self, give_focus=True, filename='', is_cython=False,
                          is_pylab=False, is_sympy=False, given_name=None):
        """Create a new client."""
        self.tabwidget.show()
        self.master_clients += 1
        client_id = dict(int_id=str(self.master_clients),
                         str_id='A')
        cf = self._new_connection_file()
        show_elapsed_time = self.get_option('show_elapsed_time')
        reset_warning = self.get_option('show_reset_namespace_warning')
        ask_before_restart = self.get_option('ask_before_restart')
        client = ClientWidget(
            self,
            id_=client_id,
            history_filename=get_conf_path('history.py'),
            config_options=self.config_options(),
            additional_options=self.additional_options(
                is_pylab=is_pylab,
                is_sympy=is_sympy,
            ),
            interpreter_versions=self.interpreter_versions(),
            connection_file=cf,
            # menu_actions=self.menu_actions,
            # options_button=self.options_button,
            show_elapsed_time=show_elapsed_time,
            reset_warning=reset_warning,
            given_name=given_name,
            ask_before_restart=ask_before_restart,
            css_path=self.css_path,
        )

        # Change stderr_dir if requested
        if self._test_dir is not None:
            client.stderr_dir = self._test_dir

        self.add_tab(client, name=client.get_name(), filename=filename)

        if cf is None:
            error_msg = self.permission_error_msg.format(jupyter_runtime_dir())
            client.show_kernel_error(error_msg)
            return

        # Check if ipykernel is present in the external interpreter.
        # Else we won't be able to create a client
        if not self.get_option('use_default_main_interpreter'):
            pyexec = self.get_option('main_interpreter_executable')
            has_spyder_kernels = programs.is_module_installed(
                'spyder_kernels',
                interpreter=pyexec,
                version='>=2.0.0.dev0')

            if not has_spyder_kernels and not running_under_pytest():
                client.show_kernel_error(
                    _("Your Python environment or installation doesn't have "
                      "the <tt>spyder-kernels</tt> module or the right "
                      "version of it installed (>= 2.0.0dev0). "
                      "Without this module is not possible for Spyder to "
                      "create a console for you.<br><br>"
                      "You can install it by running in a system terminal:"
                      "<br><br>"
                      "<tt>conda install spyder-kernels</tt>"
                      "<br><br>or<br><br>"
                      "<tt>pip install spyder-kernels</tt>")
                )
                return

        self.connect_client_to_kernel(client, is_cython=is_cython,
                                      is_pylab=is_pylab, is_sympy=is_sympy)

        if client.shellwidget.kernel_manager is None:
            return

        self.register_client(client)

    @Slot()
    def create_client_for_kernel(self):
        """Create a client connected to an existing kernel."""
        connection_settings = self.get_option("connection_settings")
        connect_output = KernelConnectionDialog.get_connection_parameters(
            self, connection_settings=connection_settings)

        (connection_file, hostname, sshkey, password, ok,
         new_connection_settings) = connect_output

        if connection_settings != new_connection_settings:
            self.set_option("connection_settings", new_connection_settings)

        if not ok:
            return
        else:
            self._create_client_for_kernel(connection_file, hostname, sshkey,
                                           password)

    def connect_client_to_kernel(self, client, is_cython=False,
                                 is_pylab=False, is_sympy=False):
        """Connect a client to its kernel."""
        connection_file = client.connection_file
        stderr_handle = None if self._test_no_stderr else client.stderr_handle
        km, kc = self.create_kernel_manager_and_kernel_client(
            connection_file,
            stderr_handle,
            is_cython=is_cython,
            is_pylab=is_pylab,
            is_sympy=is_sympy,
        )

        # An error occurred if this is True
        if isinstance(km, str) and kc is None:
            client.shellwidget.kernel_manager = None
            client.show_kernel_error(km)
            return

        # This avoids a recurrent, spurious NameError when running our
        # tests in our CIs
        if not self._testing:
            kc.started_channels.connect(
                lambda c=client: self._process_started(c))
            kc.stopped_channels.connect(
                lambda c=client: self._process_finished(c))

        kc.start_channels(shell=True, iopub=True)

        shellwidget = client.shellwidget
        shellwidget.set_kernel_client_and_manager(kc, km)

        # FIXME:
        shellwidget.sig_exception_occurred.connect(
            self.sig_exception_occurred)

    @Slot(object, object)
    def edit_file(self, filename, line):
        """Handle %edit magic petitions."""
        if encoding.is_text_file(filename):
            # The default line number sent by ipykernel is always the last
            # one, but we prefer to use the first.
            self.sig_edit_goto_requested.emit(filename, 1, '')

    def config_options(self):
        """
        Generate a Trailets Config instance for shell widgets using our
        config system.

        This lets us create each widget with its own config.
        """
        # ---- Jupyter config ----
        try:
            full_cfg = load_pyconfig_files(['jupyter_qtconsole_config.py'],
                                           jupyter_config_dir())

            # From the full config we only select the JupyterWidget section
            # because the others have no effect here.
            cfg = Config({'JupyterWidget': full_cfg.JupyterWidget})
        except Exception:
            cfg = Config()

        # ---- Spyder config ----
        spy_cfg = Config()

        # Make the pager widget a rich one (i.e a QTextEdit)
        spy_cfg.JupyterWidget.kind = 'rich'

        # Gui completion widget
        completion_type_o = self.get_option('completion_type')
        completions = {0: "droplist", 1: "ncurses", 2: "plain"}
        spy_cfg.JupyterWidget.gui_completion = completions[completion_type_o]

        # Pager
        pager_o = self.get_option('use_pager')
        if pager_o:
            spy_cfg.JupyterWidget.paging = 'inside'
        else:
            spy_cfg.JupyterWidget.paging = 'none'

        # Calltips
        calltips_o = self.get_option('show_calltips')
        spy_cfg.JupyterWidget.enable_calltips = calltips_o

        # Buffer size
        buffer_size_o = self.get_option('buffer_size')
        spy_cfg.JupyterWidget.buffer_size = buffer_size_o

        # Prompts
        in_prompt_o = self.get_option('in_prompt')
        out_prompt_o = self.get_option('out_prompt')
        if in_prompt_o:
            spy_cfg.JupyterWidget.in_prompt = in_prompt_o

        if out_prompt_o:
            spy_cfg.JupyterWidget.out_prompt = out_prompt_o

        # Style
        color_scheme = self.get_option('color_scheme')
        style_sheet = create_qss_style(color_scheme)[0]
        spy_cfg.JupyterWidget.style_sheet = style_sheet
        spy_cfg.JupyterWidget.syntax_style = color_scheme

        # Merge QtConsole and Spyder configs. Spyder prefs will have
        # prevalence over QtConsole ones
        cfg._merge(spy_cfg)
        return cfg

    def register_client(self, client, give_focus=True):
        """Register new client."""
        client.configure_shellwidget(give_focus=give_focus)
        client.sig_time_updated.connect(
            lambda text: self._update_client_time(client, text))
        client.sig_executed.connect(
            lambda: self._update_client_state(client, running=False))
        client.sig_executing.connect(
            lambda: self._update_client_state(client, running=True))

        # Local vars
        shellwidget = client.shellwidget
        control = shellwidget._control
        page_control = shellwidget._page_control

        # Create new clients with Ctrl+T shortcut
        shellwidget.new_client.connect(self.create_new_client)

        # For tracebacks
        control.go_to_error.connect(self.go_to_error)

        # For help requests
        control.set_help_enabled(self.get_option('connect_to_help'))
        control.sig_help_requested.connect(self.sig_help_requested)

        shellwidget.sig_pdb_step.connect(
            lambda fname, lineno, shellwidget=shellwidget:
                self.pdb_has_stopped(fname, lineno, shellwidget))
        shellwidget.sig_pdb_state_changed.connect(self.sig_pdb_state_changed)

        # To handle %edit magic petitions
        shellwidget.custom_edit_requested.connect(self.edit_file)

        # Set shell cwd according to preferences
        cwd_path = ""
        if self.get_option('console/use_project_or_home_directory'):
            cwd_path = get_home_dir()
            # FIXME: Calling the main window and projects!
            # if (self.main.projects is not None and
            #         self.main.projects.get_active_project() is not None):
            #     cwd_path = self.main.projects.get_active_project_path()
        elif self.get_option('startup/use_fixed_directory'):
            cwd_path = self.get_option('startup/fixed_directory')
        elif self.get_option('console/use_fixed_directory'):
            cwd_path = self.get_option('console/fixed_directory')

        # FIXME: remove main
        # if osp.isdir(cwd_path) and self.main is not None:
        if osp.isdir(cwd_path):
            shellwidget.set_cwd(cwd_path)
            if give_focus:
                # Syncronice cwd with explorer and cwd widget
                shellwidget.update_cwd()

        # Emit history handling signals
        self.sig_history_requested.emit(client.history_filename)
        client.sig_append_to_history_requested.connect(
            self.sig_append_to_history_requested)

        # Set font for client
        if self._font is not None:
            client.set_font(self._font)

        # Connect focus signal to client's control widget
        control.sig_focus_changed.connect(self.sig_focus_changed)

        shellwidget.sig_working_directory_changed.connect(
            self.sig_working_directory_changed)

        # Update the find widget if focus changes between control and
        # page_control
        self.find_widget.set_editor(control)
        if page_control:
            control.sig_visibility_changed.connect(self.refresh)
            page_control.sig_focus_changed.connect(self.sig_focus_changed)
            page_control.sig_visibility_changed.connect(self.refresh)
            page_control.sig_find_widget_requested.connect(
                self.find_widget.show)

    def close_client(self, index=None, client=None, force=False):
        """Close client tab from index or widget (or close current tab)."""
        if not self.tabwidget.count():
            return

        if client is not None:
            index = self.tabwidget.indexOf(client)
            # if index is not found in tabwidget it's because this client was
            # already closed and the call was performed by the exit callback
            if index == -1:
                return

        if index is None and client is None:
            index = self.tabwidget.currentIndex()

        if index is not None:
            client = self.tabwidget.widget(index)

        # Needed to handle a RuntimeError. See spyder-ide/spyder#5568.
        try:
            # Close client
            client.stop_button_click_handler()
        except RuntimeError:
            pass

        # Disconnect timer needed to update elapsed time
        try:
            client.timer.timeout.disconnect(client.update_time)
        except (RuntimeError, TypeError):
            pass

        # Check if related clients or kernels are opened
        # and eventually ask before closing them
        if not self.mainwindow_close and not force:
            close_all = True
            if self.get_option('ask_before_closing'):
                close = QMessageBox.question(
                    self,
                    self.get_title(),
                    _("Do you want to close this console?"),
                    QMessageBox.Yes | QMessageBox.No,
                )

                if close == QMessageBox.No:
                    return

            if len(self.get_related_clients(client)) > 0:
                close_all = QMessageBox.question(
                    self,
                    self.get_title(),
                    _("Do you want to close all other consoles connected "
                      "to the same kernel as this one?"),
                    QMessageBox.Yes | QMessageBox.No,
                )

            client.shutdown()
            if close_all == QMessageBox.Yes:
                self.close_related_clients(client)

        # if there aren't related clients we can remove stderr_file
        related_clients = self.get_related_clients(client)
        if len(related_clients) == 0 and osp.exists(client.stderr_file):
            client.remove_stderr_file()

        client.dialog_manager.close_all()
        client.close()

        # Note: client index may have changed after closing related widgets
        self.tabwidget.removeTab(self.tabwidget.indexOf(client))
        self.clients.remove(client)

        # This is needed to prevent that hanged consoles make reference
        # to an index that doesn't exist. See spyder-ide/spyder#4881
        try:
            self.filenames.pop(index)
        except IndexError:
            pass

        self.update_tabs_text()

        # Create a new client if the console is about to become empty
        if not self.tabwidget.count() and self.create_new_client_if_empty:
            self.create_new_client()

        # FIXME:
        # self.sig_update_plugin_title.emit()

    def get_client_index_from_id(self, client_id):
        """Return client index from id."""
        for index, client in enumerate(self.clients):
            if id(client) == client_id:
                return index

    def get_related_clients(self, client):
        """
        Get all clients that are connected to the same kernel as `client`.
        """
        related_clients = []
        for cl in self.get_clients():
            if cl.connection_file == client.connection_file and \
              cl is not client:
                related_clients.append(cl)

        return related_clients

    def close_related_clients(self, client):
        """Close all clients related to *client*, except itself."""
        related_clients = self.get_related_clients(client)
        for cl in related_clients:
            self.close_client(client=cl, force=True)

    def restart(self):
        """
        Restart the console.

        This is needed when we switch projects to update PYTHONPATH
        and the selected interpreter
        """
        self.master_clients = 0
        self.create_new_client_if_empty = False
        for __ in range(len(self.clients)):
            client = self.clients[-1]
            try:
                client.shutdown()
            except Exception as e:
                QMessageBox.warning(
                    self,
                    _('Warning'),
                    _("It was not possible to restart the IPython console "
                      "when switching to this project. The error was<br><br>"
                      "<tt>{0}</tt>").format(e),
                    QMessageBox.Ok,
                )

            self.close_client(client=client, force=True)

        self.create_new_client(give_focus=False)
        self.create_new_client_if_empty = True

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into all clients."""
        for cl in self.clients:
            cl.shellwidget.set_spyder_breakpoints()

    def set_pdb_ignore_lib(self):
        """Set pdb_ignore_lib into all clients."""
        for cl in self.clients:
            cl.shellwidget.set_pdb_ignore_lib()

    def set_pdb_execute_events(self):
        """Set pdb_execute_events into all clients."""
        for cl in self.clients:
            cl.shellwidget.set_pdb_execute_events()

    @Slot(str)
    def create_client_from_path(self, path):
        """Create a client with its cwd pointing to path."""
        self.create_new_client()
        sw = self.get_current_shellwidget()
        sw.set_cwd(path)

    def create_client_for_file(self, filename, is_cython=False):
        """Create a client to execute code related to a file."""
        # Create client
        self.create_new_client(filename=filename, is_cython=is_cython)

        # Don't increase the count of master clients
        self.master_clients -= 1

        # Rename client tab with filename
        client = self.get_current_client()
        client.allow_rename = False
        tab_text = self.disambiguate_fname(filename)
        self.rename_client_tab(client, tab_text)

    def get_client_for_file(self, filename):
        """Get client associated with a given file."""
        client = None
        for idx, cl in enumerate(self.get_clients()):
            if self.filenames[idx] == filename:
                self.tabwidget.setCurrentIndex(idx)
                client = cl
                break

        return client

    def set_elapsed_time(self, client):
        """Set elapsed time for slave clients."""
        related_clients = self.get_related_clients(client)
        for cl in related_clients:
            if cl.timer is not None:
                client.t0 = cl.t0
                client.timer.start(1000)
                break

    # --- Public API (for kernels)
    # ------------------------------------------------------------------------
    def ssh_tunnel(self, *args, **kwargs):
        if os.name == 'nt':
            return zmqtunnel.paramiko_tunnel(*args, **kwargs)
        else:
            return openssh_tunnel(self, *args, **kwargs)

    def tunnel_to_kernel(self, connection_info, hostname, sshkey=None,
                         password=None, timeout=10):
        """
        Tunnel connections to a kernel via ssh.

        Remote ports are specified in the connection info ci.
        """
        lports = zmqtunnel.select_random_ports(4)
        rports = (connection_info['shell_port'], connection_info['iopub_port'],
                  connection_info['stdin_port'], connection_info['hb_port'])
        remote_ip = connection_info['ip']

        for lp, rp in zip(lports, rports):
            self.ssh_tunnel(lp, rp, hostname, remote_ip, sshkey, password,
                            timeout)

        return tuple(lports)

    def create_kernel_spec(self, is_cython=False,
                           is_pylab=False, is_sympy=False):
        """Create a kernel spec for our own kernels"""
        # Before creating our kernel spec, we always need to set this value in
        # spyder.ini
        # FIXME: Why?
        self.sig_spyder_python_path_update_requested.emit()

        # FIXME: This file uses the CONF directly. Probably a good idea to
        # decouple it
        return SpyderKernelSpec(is_cython=is_cython,
                                is_pylab=is_pylab,
                                is_sympy=is_sympy)

    def create_kernel_manager_and_kernel_client(self, connection_file,
                                                stderr_handle,
                                                is_cython=False,
                                                is_pylab=False,
                                                is_sympy=False):
        """Create kernel manager and client."""
        # Kernel spec
        kernel_spec = self.create_kernel_spec(is_cython=is_cython,
                                              is_pylab=is_pylab,
                                              is_sympy=is_sympy)

        # Kernel manager
        try:
            kernel_manager = SpyderKernelManager(
                connection_file=connection_file,
                config=None,
                autorestart=True,
            )
        except Exception:
            error_msg = _("The error is:<br><br>"
                          "<tt>{}</tt>").format(traceback.format_exc())
            return (error_msg, None)

        kernel_manager._kernel_spec = kernel_spec

        # Catch any error generated when trying to start the kernel.
        # See spyder-ide/spyder#7302.
        try:
            kernel_manager.start_kernel(stderr=stderr_handle)
        except Exception:
            error_msg = _("The error is:<br><br>"
                          "<tt>{}</tt>").format(traceback.format_exc())
            return (error_msg, None)

        # Kernel client
        kernel_client = kernel_manager.client()

        # Increase time to detect if a kernel is alive.
        # See spyder-ide/spyder#3444.
        kernel_client.hb_channel.time_to_dead = 45.0

        return kernel_manager, kernel_client

    def restart_kernel(self):
        """Restart kernel of current client."""
        client = self.get_current_client()
        if client is not None:
            self.change_visibility(True)
            client.restart_kernel()

    def reset_kernel(self):
        """Reset kernel of current client."""
        client = self.get_current_client()
        if client is not None:
            self.change_visibility(True)
            client.reset_namespace()

    def interrupt_kernel(self):
        """Interrupt kernel of current client."""
        self.stop_button.setEnabled(False)
        client = self.get_current_client()
        if client is not None:
            self.change_visibility(True)
            client.stop_button_click_handler()

    def update_execution_state_kernel(self):
        """Update actions following the execution state of the kernel."""
        client = self.get_current_client()
        if client is not None:
            executing = client.stop_button.isEnabled()
            self.interrupt_action.setEnabled(executing)

    def connect_external_kernel(self, shellwidget):
        """
        Connect an external kernel to the Variable Explorer, Help and
        Plots, but only if it is a Spyder kernel.
        """
        sw = shellwidget
        kc = shellwidget.kernel_client

        self.sig_shellwidget_process_started.emit(sw)
        kc.stopped_channels.connect(
            lambda sw=sw: self.sig_shellwidget_process_finished.emit(sw))
        sw.set_namespace_view_settings()
        sw.refresh_namespacebrowser()

    # --- Public API (for tabs)
    # ------------------------------------------------------------------------
    def add_tab(self, widget, name, filename=''):
        """Add tab."""
        self.clients.append(widget)
        index = self.tabwidget.addTab(widget, name)
        self.filenames.insert(index, filename)
        self.tabwidget.setCurrentIndex(index)

        # FIXME:
        # if self.dockwidget and not self.main.is_setting_up:
        if self.dockwidget:
            self.change_visibility(True)

        self.activateWindow()
        widget.get_control().setFocus()
        self.update_tabs_text()

    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget).
        """
        filename = self.filenames.pop(index_from)
        client = self.clients.pop(index_from)
        self.filenames.insert(index_to, filename)
        self.clients.insert(index_to, client)
        self.update_tabs_text()

        # FIXME:
        # self.sig_update_plugin_title.emit()

    def disambiguate_fname(self, fname):
        """Generate a file name without ambiguation."""
        files_path_list = [filename for filename in self.filenames
                           if filename]
        return sourcecode.disambiguate_fname(files_path_list, fname)

    def update_tabs_text(self):
        """Update the text from the tabs."""
        # This is needed to prevent that hanged consoles make reference
        # to an index that doesn't exist. See spyder-ide/spyder#4881.
        try:
            for index, fname in enumerate(self.filenames):
                client = self.clients[index]
                if fname:
                    self.rename_client_tab(client,
                                           self.disambiguate_fname(fname))
                else:
                    self.rename_client_tab(client, None)
        except IndexError:
            pass

    def rename_client_tab(self, client, given_name):
        """Rename client's tab."""
        index = self.get_client_index_from_id(id(client))

        if given_name is not None:
            client.given_name = given_name

        self.tabwidget.setTabText(index, client.get_name())

    def rename_tabs_after_change(self, given_name):
        """Rename tabs after a change in name."""
        client = self.get_current_client()

        # Prevent renames that want to assign the same name of
        # a previous tab
        repeated = False
        for cl in self.get_clients():
            if id(client) != id(cl) and given_name == cl.given_name:
                repeated = True
                break

        # Rename current client tab to add str_id
        if client.allow_rename and u'/' not in given_name and not repeated:
            self.rename_client_tab(client, given_name)
        else:
            self.rename_client_tab(client, None)

        # Rename related clients
        if client.allow_rename and u'/' not in given_name and not repeated:
            for cl in self.get_related_clients(client):
                self.rename_client_tab(cl, given_name)

    def tab_name_editor(self):
        """Trigger the tab name editor."""
        index = self.tabwidget.currentIndex()
        self.tabwidget.tabBar().tab_name_editor.edit_tab(index)

    def request_env(self):
        client = self.get_current_client()
        if client:
            client.request_env()

    def request_syspath(self):
        client = self.get_current_client()
        if client:
            client.request_syspath()

    # --- Python specific API
    # ------------------------------------------------------------------------
    def setup_python(self, options=DEFAULT_OPTIONS):
        create_pylab_action = self.create_action(
            IPythonConsoleWidgetActions.CreatePyLabClient,
            text=_("New Pylab console (data plotting)"),
            icon=self.create_icon('ipython_console'),
            triggered=self.create_pylab_client,
        )
        create_sympy_action = self.create_action(
            IPythonConsoleWidgetActions.CreateSymPyClient,
            text=_("New SymPy console (symbolic math)"),
            icon=self.create_icon('ipython_console'),
            triggered=self.create_sympy_client,
        )
        create_cython_action = self.create_action(
            IPythonConsoleWidgetActions.CreateCythonClient,
            _("New Cython console (Python with C extensions)"),
            icon=self.create_icon('ipython_console'),
            triggered=self.create_cython_client,
        )

        consoles_menu = self.get_menu(
            IPythonConsoleWidgetOptionsMenus.SpecialConsoles)
        self.add_item_to_menu(
            create_pylab_action,
            menu=consoles_menu,
            section=IPythonConsoleWidgetConsolesMenusSection.Main,
        )
        self.add_item_to_menu(
            create_sympy_action,
            menu=consoles_menu,
            section=IPythonConsoleWidgetConsolesMenusSection.Main,
        )
        self.add_item_to_menu(
            create_cython_action,
            menu=consoles_menu,
            section=IPythonConsoleWidgetConsolesMenusSection.Main,
        )

    def go_to_error(self, text):
        """Go to error if relevant."""
        match = get_error_match(str(text))
        if match:
            fname, lnb = match.groups()
            if ("<ipython-input-" in fname and
                    self.run_cell_filename is not None):
                fname = self.run_cell_filename
            # This is needed to fix issue spyder-ide/spyder#9217.
            try:
                self.sig_edit_goto_requested.emit(
                    osp.abspath(fname), int(lnb), '')
            except ValueError:
                pass

    def show_intro(self):
        """Show intro to IPython help."""
        from IPython.core.usage import interactive_usage

        self.sig_render_rich_text_requested.emit(interactive_usage, False)

    @Slot()
    def show_guiref(self):
        """Show qtconsole help."""
        from qtconsole.usage import gui_reference

        self.sig_render_rich_text_requested.emit(gui_reference, True)

    @Slot()
    def show_quickref(self):
        """Show IPython Cheat Sheet."""
        from IPython.core.usage import quick_reference

        self.sig_render_plain_text_requested.emit(quick_reference)

    def create_pylab_client(self):
        """Force creation of Pylab client."""
        self.create_new_client(is_pylab=True, given_name="Pylab")

    def create_sympy_client(self):
        """Force creation of SymPy client."""
        self.create_new_client(is_sympy=True, given_name="SymPy")

    def create_cython_client(self):
        """Force creation of Cython client."""
        self.create_new_client(is_cython=True, given_name="Cython")

    def interpreter_versions(self):
        """Python and IPython versions used by clients."""
        if self.get_option('use_default_main_interpreter'):
            from IPython.core import release
            versions = dict(
                python_version=sys.version,
                ipython_version=release.version
            )
        else:
            import subprocess
            versions = {}
            pyexec = self.get_option('main_interpreter_executable')
            py_cmd = u'%s -c "import sys; print(sys.version)"' % pyexec
            ipy_cmd = (
                u'%s -c "import IPython.core.release as r; print(r.version)"'
                % pyexec
            )
            for cmd in [py_cmd, ipy_cmd]:
                try:
                    proc = programs.run_shell_command(cmd)
                    output, _err = proc.communicate()
                except subprocess.CalledProcessError:
                    output = ''

                output = output.decode().split('\n')[0].strip()
                if 'IPython' in cmd:
                    versions['ipython_version'] = output
                else:
                    versions['python_version'] = output

        return versions

    def additional_options(self, is_pylab=False, is_sympy=False):
        """
        Additional options for shell widgets that are not defined
        in JupyterWidget config options.
        """
        options = dict(
            pylab=self.get_option('pylab'),
            autoload_pylab=self.get_option('pylab/autoload'),
            sympy=self.get_option('symbolic_math'),
            show_banner=self.get_option('show_banner')
        )

        if is_pylab is True:
            options['autoload_pylab'] = True
            options['sympy'] = False

        if is_sympy is True:
            options['autoload_pylab'] = False
            options['sympy'] = True

        return options

    def run_script(self, filename, wdir, args, debug, post_mortem,
                   current_client, clear_variables, console_namespace):
        """Run script in current or dedicated client."""
        norm = lambda text: remove_backslashes(str(text))

        # Run Cython files in a dedicated console
        is_cython = osp.splitext(filename)[1] == '.pyx'
        if is_cython:
            current_client = False

        # Select client to execute code on it
        is_new_client = False
        if current_client:
            client = self.get_current_client()
        else:
            client = self.get_client_for_file(filename)
            if client is None:
                self.create_client_for_file(filename, is_cython=is_cython)
                client = self.get_current_client()
                is_new_client = True

        if client is not None:
            # Internal kernels, use runfile
            if (client.get_kernel() is not None or
                    client.shellwidget.is_spyder_kernel()):
                line = "%s('%s'" % ('debugfile' if debug else 'runfile',
                                    norm(filename))
                if args:
                    line += ", args='%s'" % norm(args)

                if wdir:
                    line += ", wdir='%s'" % norm(wdir)

                if post_mortem:
                    line += ", post_mortem=True"

                if console_namespace:
                    line += ", current_namespace=True"

                line += ")"
            else:  # External, non spyder-kernels, use %run
                line = "%run "
                if debug:
                    line += "-d "

                line += "\"%s\"" % str(filename)
                if args:
                    line += " %s" % norm(args)

            try:
                if client.shellwidget._executing:
                    # Don't allow multiple executions when there's
                    # still an execution taking place
                    # Fixes spyder-ide/spyder#7293.
                    pass
                elif (client.shellwidget.in_debug_loop()):
                    client.shellwidget.pdb_execute('!' + line)
                elif current_client:
                    self.execute_code(line, current_client, clear_variables)
                else:
                    if is_new_client:
                        client.shellwidget.silent_execute('%clear')
                    else:
                        client.shellwidget.execute('%clear')

                    client.shellwidget.sig_prompt_ready.connect(
                            lambda: self.execute_code(line, current_client,
                                                      clear_variables))
            except AttributeError:
                pass

            self.change_visibility(True)
        else:
            # XXX: not sure it can really happen
            QMessageBox.warning(
                self,
                _('Warning'),
                _("No IPython console is currently available to run <b>%s</b>."
                  "<br><br>Please open a new one and try again."
                  ) % osp.basename(filename),
                QMessageBox.Ok,
            )

    def pdb_has_stopped(self, fname, lineno, shellwidget):
        """Python debugger has just stopped at frame (fname, lineno)."""
        # This is a unique form of the sig_edit_goto_requested signal that is
        # intended to prevent keyboard input from accidentally entering the
        # editor during repeated, rapid entry of debugging commands.
        self.sig_edit_goto_requested[str, int, str, bool].emit(
            fname, lineno, '', False)
        self.activateWindow()
        shellwidget._control.setFocus()

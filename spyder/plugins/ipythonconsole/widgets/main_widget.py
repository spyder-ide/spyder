# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console main widget based on QtConsole.
"""

# Standard library imports
import logging
import os
import os.path as osp
import sys
import traceback
import uuid

# Third-party imports
from jupyter_client.connect import find_connection_file
from jupyter_core.paths import jupyter_config_dir, jupyter_runtime_dir
import qstylizer.style
from qtconsole.client import QtKernelClient
from qtpy.QtCore import Signal, Slot
from qtpy.QtGui import QColor
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget)
from traitlets.config.loader import Config, load_pyconfig_files
from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.widgets.menus import MENU_SEPARATOR
from spyder.config.base import (
    get_conf_path, get_home_dir, running_under_pytest)
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
from spyder.plugins.ipythonconsole.utils.style import create_qss_style
from spyder.plugins.ipythonconsole.widgets import (
    ClientWidget, ConsoleRestartDialog, COMPLETION_WIDGET_TYPE,
    KernelConnectionDialog, PageControlWidget, ShellWidget)
from spyder.utils import encoding, programs, sourcecode
from spyder.utils.misc import get_error_match, remove_backslashes
from spyder.utils.palette import QStylePalette
from spyder.widgets.browser import FrameWebView
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.tabs import Tabs
from spyder.plugins.ipythonconsole.utils.stdfile import StdFile


# Logging
logger = logging.getLogger(__name__)


# =============================================================================
# ---- Constants
# =============================================================================
MAIN_BG_COLOR = QStylePalette.COLOR_BACKGROUND_1


class IPythonConsoleWidgetActions:
    # Clients creation
    CreateNewClient = 'new tab'
    CreateCythonClient = 'create cython client'
    CreateSymPyClient = 'create cympy client'
    CreatePyLabClient = 'create pylab client'

    # Current console actions
    ClearConsole = 'Clear shell'
    ClearLine = 'clear line'
    ConnectToKernel = 'connect to kernel'
    Interrupt = 'interrupt kernel'
    InspectObject = 'Inspect current object'
    Restart = 'Restart kernel'
    ResetNamespace = 'reset namespace'
    ShowEnvironmentVariables = 'Show environment variables'
    ShowSystemPath = 'show system path'
    ToggleElapsedTime = 'toggle elapsed time'
    Quit = 'exit'

    # Tabs
    RenameTab = 'rename tab'

    # Variables display
    ArrayInline = 'enter array inline'
    ArrayTable = 'enter array table'

    # Documentation and help
    IPythonDocumentation = 'ipython documentation'
    ConsoleHelp = 'console help'
    QuickReference = 'quick reference'


class IPythonConsoleWidgetOptionsMenus:
    SpecialConsoles = 'special_consoles_submenu'
    Documentation = 'documentation_submenu'


class IPythonConsoleWidgetOptionsMenuSections:
    Consoles = 'consoles_section'
    Edit = 'edit_section'
    View = 'view_section'


class IPythonConsoleWidgetMenus:
    TabsContextMenu = 'tabs_context_menu'


class IPythonConsoleWidgetTabsContextMenuSections:
    Consoles = 'tabs_consoles_section'
    Edit = 'tabs_edit_section'


# --- Widgets
# ----------------------------------------------------------------------------
class IPythonConsoleWidget(PluginMainWidget):
    """
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget.
    """

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

    sig_switch_to_plugin_requested = Signal()
    """
    This signal will request to change the focus to the plugin.
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
    This signal is emitted when a shellwidget is created.

    Parameters
    ----------
    shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
        The shellwigdet.
    """

    sig_shellwidget_deleted = Signal(object)
    """
    This signal is emitted when a shellwidget is deleted/removed.

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

    # Error messages
    PERMISSION_ERROR_MSG = _("The directory {} is not writable and it is "
                             "required to create IPython consoles. Please "
                             "make it writable.")

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        self.menu_actions = None
        self.master_clients = 0
        self.clients = []
        self.filenames = []
        self.mainwindow_close = False
        self.active_project_path = None
        self.create_new_client_if_empty = True
        self.css_path = self.get_conf('css_path', section='appearance')
        self.run_cell_filename = None
        self.interrupt_action = None
        self.initial_conf_options = self.get_conf_options()
        self.registered_spyder_kernel_handlers = {}

        # Disable infowidget if requested by the user
        self.enable_infowidget = True
        if plugin:
            cli_options = plugin.get_command_line_options()
            if cli_options.no_web_widgets:
                self.enable_infowidget = False

        # Attrs for testing
        self._testing = bool(os.environ.get('IPYCONSOLE_TESTING'))
        self._test_dir = os.environ.get('IPYCONSOLE_TEST_DIR')
        self._test_no_stderr = os.environ.get('IPYCONSOLE_TEST_NO_STDERR')

        # Create temp dir on testing to save kernel errors
        if self._test_dir:
            if not osp.isdir(osp.join(self._test_dir)):
                os.makedirs(osp.join(self._test_dir))

        layout = QVBoxLayout()
        layout.setSpacing(0)

        self.tabwidget = Tabs(self, rename_tabs=True, split_char='/',
                              split_index=0)
        if (hasattr(self.tabwidget, 'setDocumentMode')
                and not sys.platform == 'darwin'):
            # Don't set document mode to true on OSX because it generates
            # a crash when the console is detached from the main window
            # Fixes spyder-ide/spyder#561.
            self.tabwidget.setDocumentMode(True)
        self.tabwidget.currentChanged.connect(
            lambda idx: self.refresh_container(give_focus=True))
        self.tabwidget.tabBar().tabMoved.connect(self.move_tab)
        self.tabwidget.tabBar().sig_name_changed.connect(
            self.rename_tabs_after_change)
        self.tabwidget.set_close_function(self.close_client)

        if sys.platform == 'darwin':
            tab_container = QWidget()
            tab_container.setObjectName('tab-container')
            tab_layout = QHBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabwidget)
            layout.addWidget(tab_container)
        else:
            layout.addWidget(self.tabwidget)

        # Info widget
        if self.enable_infowidget:
            self.infowidget = FrameWebView(self)
            if WEBENGINE:
                self.infowidget.page().setBackgroundColor(
                    QColor(MAIN_BG_COLOR))
            else:
                self.infowidget.setStyleSheet(
                    "background:{}".format(MAIN_BG_COLOR))
            layout.addWidget(self.infowidget)
        else:
            self.infowidget = None

        # Label to inform users how to get out of the pager
        self.pager_label = QLabel(_("Press <b>Q</b> to exit pager"), self)
        pager_label_css = qstylizer.style.StyleSheet()
        pager_label_css.setValues(**{
            'background-color': f'{QStylePalette.COLOR_ACCENT_2}',
            'color': f'{QStylePalette.COLOR_TEXT_1}',
            'margin': '0px 1px 4px 1px',
            'padding': '5px',
            'qproperty-alignment': 'AlignCenter'
        })
        self.pager_label.setStyleSheet(pager_label_css.toString())
        self.pager_label.hide()
        layout.addWidget(self.pager_label)

        # Find/replace widget
        self.find_widget = FindReplace(self)
        self.find_widget.hide()
        layout.addWidget(self.find_widget)

        self.setLayout(layout)

        # Accepting drops
        self.setAcceptDrops(True)

        # Needed to start Spyder in Windows with Python 3.8
        # See spyder-ide/spyder#11880
        self._init_asyncio_patch()

        # To cache kernel properties
        self._cached_kernel_properties = None

        # Initial value for the current working directory
        self._current_working_directory = get_home_dir()

    def on_close(self):
        self.mainwindow_close = True
        self.close_all_clients()

    # ---- PluginMainWidget API and settings handling
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('IPython Console')

    def get_focus_widget(self):
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client.get_control()

    def setup(self):
        # --- Options menu actions
        self.create_client_action = self.create_action(
            IPythonConsoleWidgetActions.CreateNewClient,
            text=_("New console (default settings)"),
            icon=self.create_icon('ipython_console'),
            triggered=self.create_new_client,
            register_shortcut=True
        )
        self.restart_action = self.create_action(
            IPythonConsoleWidgetActions.Restart,
            text=_("Restart kernel"),
            icon=self.create_icon('restart'),
            triggered=self.restart_kernel,
            register_shortcut=True
        )
        self.reset_action = self.create_action(
            IPythonConsoleWidgetActions.ResetNamespace,
            text=_("Remove all variables"),
            icon=self.create_icon('editdelete'),
            triggered=self.reset_namespace,
            register_shortcut=True
        )
        self.interrupt_action = self.create_action(
            IPythonConsoleWidgetActions.Interrupt,
            text=_("Interrupt kernel"),
            icon=self.create_icon('stop'),
            triggered=self.interrupt_kernel,
        )
        self.connect_to_kernel_action = self.create_action(
            IPythonConsoleWidgetActions.ConnectToKernel,
            text=_("Connect to an existing kernel"),
            tip=_("Open a new IPython console connected to an existing "
                  "kernel"),
            triggered=self._create_client_for_kernel,
        )
        self.rename_tab_action = self.create_action(
            IPythonConsoleWidgetActions.RenameTab,
            text=_("Rename tab"),
            icon=self.create_icon('rename'),
            triggered=self.tab_name_editor,
        )

        # --- For the client
        self.env_action = self.create_action(
            IPythonConsoleWidgetActions.ShowEnvironmentVariables,
            text=_("Show environment variables"),
            icon=self.create_icon('environ'),
            triggered=lambda:
                self.get_current_shellwidget().request_env()
                if self.get_current_shellwidget() else None,
        )

        self.syspath_action = self.create_action(
            IPythonConsoleWidgetActions.ShowSystemPath,
            text=_("Show sys.path contents"),
            icon=self.create_icon('syspath'),
            triggered=lambda:
                self.get_current_shellwidget().request_syspath()
                if self.get_current_shellwidget() else None,
        )

        self.show_time_action = self.create_action(
            IPythonConsoleWidgetActions.ToggleElapsedTime,
            text=_("Show elapsed time"),
            toggled=self.set_show_elapsed_time_current_client,
            initial=self.get_conf('show_elapsed_time')
        )

        # --- Context menu actions
        # TODO: Shortcut registration not working
        self.inspect_action = self.create_action(
            IPythonConsoleWidgetActions.InspectObject,
            text=_("Inspect current object"),
            icon=self.create_icon('MessageBoxInformation'),
            triggered=self.current_client_inspect_object,
            register_shortcut=True)

        self.clear_line_action = self.create_action(
            IPythonConsoleWidgetActions.ClearLine,
            text=_("Clear line or block"),
            triggered=self.current_client_clear_line,
            register_shortcut=True)

        self.clear_console_action = self.create_action(
            IPythonConsoleWidgetActions.ClearConsole,
            text=_("Clear console"),
            triggered=self.current_client_clear_console,
            register_shortcut=True)

        self.quit_action = self.create_action(
            IPythonConsoleWidgetActions.Quit,
            _("&Quit"),
            icon=self.create_icon('exit'),
            triggered=self.current_client_quit)

        # --- Other actions with shortcuts
        self.array_table_action = self.create_action(
            IPythonConsoleWidgetActions.ArrayTable,
            text=_("Enter array table"),
            triggered=self.current_client_enter_array_table,
            register_shortcut=True)

        self.array_inline_action = self.create_action(
            IPythonConsoleWidgetActions.ArrayInline,
            text=_("Enter array inline"),
            triggered=self.current_client_enter_array_inline,
            register_shortcut=True)

        self.context_menu_actions = (
            MENU_SEPARATOR,
            self.inspect_action,
            self.clear_line_action,
            self.clear_console_action,
            self.reset_action,
            self.array_table_action,
            self.array_inline_action,
            MENU_SEPARATOR,
            self.quit_action
        )

        # --- Setting options menu
        options_menu = self.get_options_menu()
        self.special_console_menu = self.create_menu(
            IPythonConsoleWidgetOptionsMenus.SpecialConsoles,
            _('Special consoles'))

        for item in [
                self.create_client_action,
                self.special_console_menu,
                self.connect_to_kernel_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=IPythonConsoleWidgetOptionsMenuSections.Consoles,
            )

        for item in [
                self.interrupt_action,
                self.restart_action,
                self.reset_action,
                self.rename_tab_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=IPythonConsoleWidgetOptionsMenuSections.Edit,
            )

        for item in [
                self.env_action,
                self.syspath_action,
                self.show_time_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=IPythonConsoleWidgetOptionsMenuSections.View,
            )

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

        for item in [
                create_pylab_action,
                create_sympy_action,
                create_cython_action]:
            self.add_item_to_menu(
                item,
                menu=self.special_console_menu
            )

        # --- Widgets for the tab corner
        self.reset_button = self.create_toolbutton(
            'reset',
            text=_("Remove all variables"),
            tip=_("Remove all variables from kernel namespace"),
            icon=self.create_icon("editdelete"),
            triggered=self.reset_namespace,
        )
        self.stop_button = self.create_toolbutton(
            'interrupt',
            text=_("Interrupt kernel"),
            tip=_("Interrupt kernel"),
            icon=self.create_icon('stop'),
            triggered=self.interrupt_kernel,
        )
        self.time_label = QLabel("")

        # --- Add tab corner widgets.
        self.add_corner_widget('timer', self.time_label)
        self.add_corner_widget('reset', self.reset_button)
        self.add_corner_widget('start_interrupt', self.stop_button)

        # --- Tabs context menu
        tabs_context_menu = self.create_menu(
            IPythonConsoleWidgetMenus.TabsContextMenu)

        for item in [
                self.create_client_action,
                self.special_console_menu,
                self.connect_to_kernel_action]:
            self.add_item_to_menu(
                item,
                menu=tabs_context_menu,
                section=IPythonConsoleWidgetTabsContextMenuSections.Consoles,
            )

        for item in [
                self.interrupt_action,
                self.restart_action,
                self.reset_action,
                self.rename_tab_action]:
            self.add_item_to_menu(
                item,
                menu=tabs_context_menu,
                section=IPythonConsoleWidgetTabsContextMenuSections.Edit,
            )

        self.tabwidget.menu = tabs_context_menu

        # --- Create IPython documentation menu
        self.ipython_menu = self.create_menu(
            menu_id=IPythonConsoleWidgetOptionsMenus.Documentation,
            title=_("IPython documentation"))
        intro_action = self.create_action(
            IPythonConsoleWidgetActions.IPythonDocumentation,
            text=_("Intro to IPython"),
            triggered=self.show_intro
        )
        quickref_action = self.create_action(
            IPythonConsoleWidgetActions.QuickReference,
            text=_("Quick reference"),
            triggered=self.show_quickref
        )
        guiref_action = self.create_action(
            IPythonConsoleWidgetActions.ConsoleHelp,
            text=_("Console help"),
            triggered=self.show_guiref
        )

        for help_action in [
                intro_action, guiref_action, quickref_action]:
            self.ipython_menu.add_action(help_action)

    def set_show_elapsed_time_current_client(self, state):
        if self.get_current_client():
            client = self.get_current_client()
            client.set_show_elapsed_time(state)
            self.refresh_container()

    def update_actions(self):
        client = self.get_current_client()
        if client is not None:
            # Executing state
            executing = client.is_client_executing()
            self.interrupt_action.setEnabled(executing)
            self.stop_button.setEnabled(executing)

            # Client is loading or showing a kernel error
            if (
                client.infowidget is not None
                and client.info_page is not None
            ):
                error_or_loading = client.info_page != client.blank_page
                self.restart_action.setEnabled(not error_or_loading)
                self.reset_action.setEnabled(not error_or_loading)
                self.env_action.setEnabled(not error_or_loading)
                self.syspath_action.setEnabled(not error_or_loading)
                self.show_time_action.setEnabled(not error_or_loading)

    # ---- GUI options
    @on_conf_change(section='help', option='connect/ipython_console')
    def change_clients_help_connection(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.get_control().set_help_enabled,
                value)

    @on_conf_change(section='appearance', option=['selected', 'ui_theme'])
    def change_clients_color_scheme(self, option, value):
        if option == 'ui_theme':
            value = self.get_conf('selected', section='appearance')

        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.set_color_scheme,
                value)

    @on_conf_change(option='show_elapsed_time')
    def change_clients_show_elapsed_time(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.set_show_elapsed_time,
                value)
        if self.get_current_client():
            self.refresh_container()

    @on_conf_change(option='show_reset_namespace_warning')
    def change_clients_show_reset_namespace_warning(self, value):
        for idx, client in enumerate(self.clients):
            def change_client_reset_warning(value=value):
                client.reset_warning = value
            self._change_client_conf(
                client,
                change_client_reset_warning,
                value)

    @on_conf_change(option='ask_before_restart')
    def change_clients_ask_before_restart(self, value):
        for idx, client in enumerate(self.clients):
            def change_client_ask_before_restart(value=value):
                client.ask_before_restart = value
            self._change_client_conf(
                client,
                change_client_ask_before_restart,
                value)

    @on_conf_change(option='ask_before_closing')
    def change_clients_ask_before_closing(self, value):
        for idx, client in enumerate(self.clients):
            def change_client_ask_before_closing(value=value):
                client.ask_before_closing = value
            self._change_client_conf(
                client,
                change_client_ask_before_closing,
                value)

    @on_conf_change(option='show_calltips')
    def change_clients_show_calltips(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_show_calltips,
                value)

    @on_conf_change(option='buffer_size')
    def change_clients_buffer_size(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_buffer_size,
                value)

    @on_conf_change(option='completion_type')
    def change_clients_completion_type(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget._set_completion_widget,
                COMPLETION_WIDGET_TYPE[value])

    # ---- Advanced GUI options
    @on_conf_change(option='in_prompt')
    def change_clients_in_prompt(self, value):
        if bool(value):
            for idx, client in enumerate(self.clients):
                self._change_client_conf(
                    client,
                    client.shellwidget.set_in_prompt,
                    value)

    @on_conf_change(option='out_prompt')
    def change_clients_out_prompt(self, value):
        if bool(value):
            for idx, client in enumerate(self.clients):
                self._change_client_conf(
                    client,
                    client.shellwidget.set_out_prompt,
                    value)

    # ---- Advanced options
    @on_conf_change(option='greedy_completer')
    def change_clients_greedy_completer(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_greedy_completer,
                value)

    @on_conf_change(option='jedi_completer')
    def change_clients_jedi_completer(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_jedi_completer,
                value)

    @on_conf_change(option='autocall')
    def change_clients_autocall(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_autocall,
                value)

    # ---- Debugging options
    @on_conf_change(option='pdb_ignore_lib')
    def change_clients_pdb_ignore_lib(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_pdb_ignore_lib,
                value)

    @on_conf_change(option='pdb_execute_events')
    def change_clients_pdb_execute_events(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_pdb_execute_events,
                value)

    @on_conf_change(option='pdb_use_exclamation_mark')
    def change_clients_pdb_use_exclamation_mark(self, value):
        for idx, client in enumerate(self.clients):
            self._change_client_conf(
                client,
                client.shellwidget.set_pdb_use_exclamation_mark,
                value)

    @on_conf_change(option=[
        'symbolic_math', 'hide_cmd_windows',
        'startup/run_lines', 'startup/use_run_file', 'startup/run_file',
        'pylab', 'pylab/backend', 'pylab/autoload',
        'pylab/inline/figure_format', 'pylab/inline/resolution',
        'pylab/inline/width', 'pylab/inline/height',
        'pylab/inline/bbox_inches'])
    def change_possible_restart_and_mpl_conf(self, option, value):
        """
        Apply options that possibly require a kernel restart or related to
        Matplotlib inline backend options.
        """
        # Check that we are not triggering validations in the initial
        # notification sent when Spyder is starting or when another option
        # already required a restart and the restart dialog was shown
        if not self._testing:
            if option in self.initial_conf_options:
                self.initial_conf_options.remove(option)
                return

        restart_needed = False
        restart_options = []
        # Startup options (needs a restart)
        run_lines_n = 'startup/run_lines'
        use_run_file_n = 'startup/use_run_file'
        run_file_n = 'startup/run_file'

        # Graphic options
        pylab_n = 'pylab'
        pylab_o = self.get_conf(pylab_n)
        pylab_backend_n = 'pylab/backend'

        # Advanced options (needs a restart)
        symbolic_math_n = 'symbolic_math'
        hide_cmd_windows_n = 'hide_cmd_windows'

        restart_options += [run_lines_n, use_run_file_n, run_file_n,
                            symbolic_math_n, hide_cmd_windows_n]
        restart_needed = option in restart_options

        inline_backend = 0
        pylab_restart = False
        clients_backend_require_restart = [False] * len(self.clients)
        current_client = self.get_current_client()
        current_client_backend_require_restart = False
        if pylab_o and pylab_backend_n == option and current_client:
            pylab_backend_o = self.get_conf(pylab_backend_n)

            # Check if clients require a restart due to a change in
            # interactive backend.
            clients_backend_require_restart = []
            for client in self.clients:
                interactive_backend = (
                    client.shellwidget.get_mpl_interactive_backend())

                if (
                    # No restart is needed if the new backend is inline
                    pylab_backend_o != inline_backend and
                    # There was an error getting the interactive backend in
                    # the kernel, so we can't proceed.
                    interactive_backend is not None and
                    # There has to be an interactive backend (i.e. different
                    # from inline) set in the kernel before. Else, a restart
                    # is not necessary.
                    interactive_backend != inline_backend and
                    # The interactive backend to switch to has to be different
                    # from the current one
                    interactive_backend != pylab_backend_o
                ):
                    clients_backend_require_restart.append(True)

                    # Detect if current client requires restart
                    if id(client) == id(current_client):
                        current_client_backend_require_restart = True

                        # For testing
                        if self._testing:
                            os.environ['BACKEND_REQUIRE_RESTART'] = 'true'
                else:
                    clients_backend_require_restart.append(False)

            pylab_restart = any(clients_backend_require_restart)

        if (restart_needed or pylab_restart) and not running_under_pytest():
            self.initial_conf_options = self.get_conf_options()
            self.initial_conf_options.remove(option)
            restart_dialog = ConsoleRestartDialog(self)
            restart_dialog.exec_()
            (restart_all, restart_current,
             no_restart) = restart_dialog.get_action_value()
        else:
            restart_all = False
            restart_current = False
            no_restart = True

        # Apply settings
        options = {option: value}
        for idx, client in enumerate(self.clients):
            restart = (
                (pylab_restart and clients_backend_require_restart[idx]) or
                restart_needed
            )

            if not (restart and restart_all) or no_restart:
                sw = client.shellwidget
                if sw.is_debugging() and sw._executing:
                    # Apply conf when the next Pdb prompt is available
                    def change_client_mpl_conf(o=options, c=client):
                        self._change_client_mpl_conf(o, c)
                        sw.sig_pdb_prompt_ready.disconnect(
                            change_client_mpl_conf)

                    sw.sig_pdb_prompt_ready.connect(change_client_mpl_conf)
                else:
                    self._change_client_mpl_conf(options, client)
            elif restart and restart_all:
                current_ask_before_restart = client.ask_before_restart
                client.ask_before_restart = False
                client.restart_kernel()
                client.ask_before_restart = current_ask_before_restart

        if (((pylab_restart and current_client_backend_require_restart)
             or restart_needed) and restart_current and current_client):
            current_client_ask_before_restart = (
                current_client.ask_before_restart)
            current_client.ask_before_restart = False
            current_client.restart_kernel()
            current_client.ask_before_restart = (
                current_client_ask_before_restart)

    # ---- Private methods
    # -------------------------------------------------------------------------
    def _change_client_conf(self, client, client_conf_func, value):
        """
        Change a client configuration option, taking into account if it is
        in a debugging session.

        Parameters
        ----------
        client : ClientWidget
            Client to update configuration.
        client_conf_func : Callable
            Client method to use to change the configuration.
        value : any
            New value for the client configuration.

        Returns
        -------
        None.

        """
        sw = client.shellwidget
        if not client.is_client_executing():
            client_conf_func(value)
        elif client.shellwidget.is_debugging():
            def change_conf(c=client, ccf=client_conf_func, value=value):
                ccf(value)
                c.shellwidget.sig_pdb_prompt_ready.disconnect(change_conf)
            sw.sig_pdb_prompt_ready.connect(change_conf)
        else:
            def change_conf(c=client, ccf=client_conf_func, value=value):
                ccf(value)
                c.shellwidget.sig_prompt_ready.disconnect(change_conf)
            sw.sig_prompt_ready.connect(change_conf)

    def _change_client_mpl_conf(self, options, client):
        """Apply Matplotlib related configurations to a client."""
        # Matplotlib options
        pylab_n = 'pylab'
        pylab_o = self.get_conf(pylab_n)
        pylab_autoload_n = 'pylab/autoload'
        pylab_backend_n = 'pylab/backend'
        inline_backend_figure_format_n = 'pylab/inline/figure_format'
        inline_backend_resolution_n = 'pylab/inline/resolution'
        inline_backend_width_n = 'pylab/inline/width'
        inline_backend_height_n = 'pylab/inline/height'
        inline_backend_bbox_inches_n = 'pylab/inline/bbox_inches'

        # Client widgets
        sw = client.shellwidget
        if pylab_o:
            if pylab_backend_n in options or pylab_autoload_n in options:
                pylab_autoload_o = self.get_conf(pylab_autoload_n)
                pylab_backend_o = self.get_conf(pylab_backend_n)
                sw.set_matplotlib_backend(pylab_backend_o, pylab_autoload_o)
            if inline_backend_figure_format_n in options:
                inline_backend_figure_format_o = self.get_conf(
                    inline_backend_figure_format_n)
                sw.set_mpl_inline_figure_format(inline_backend_figure_format_o)
            if inline_backend_resolution_n in options:
                inline_backend_resolution_o = self.get_conf(
                    inline_backend_resolution_n)
                sw.set_mpl_inline_resolution(inline_backend_resolution_o)
            if (inline_backend_width_n in options or
                    inline_backend_height_n in options):
                inline_backend_width_o = self.get_conf(
                    inline_backend_width_n)
                inline_backend_height_o = self.get_conf(
                    inline_backend_height_n)
                sw.set_mpl_inline_figure_size(
                    inline_backend_width_o, inline_backend_height_o)
            if inline_backend_bbox_inches_n in options:
                inline_backend_bbox_inches_o = self.get_conf(
                    inline_backend_bbox_inches_n)
                sw.set_mpl_inline_bbox_inches(inline_backend_bbox_inches_o)

    def _init_asyncio_patch(self):
        """
        - This was fixed in Tornado 6.1!
        - Same workaround fix as ipython/ipykernel#564
        - ref: tornadoweb/tornado#2608
        - On Python 3.8+, Tornado 6.0 is not compatible with the default
          asyncio implementation on Windows. Pick the older
          SelectorEventLoopPolicy if the known-incompatible default policy is
          in use.
        - Do this as early as possible to make it a low priority and
          overrideable.
        """
        if os.name == 'nt' and sys.version_info[:2] >= (3, 8):
            # Tests on Linux hang if we don't leave this import here.
            import tornado
            if tornado.version_info >= (6, 1):
                return

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
        Generate a new connection file

        Taken from jupyter_client/console_app.py
        Licensed under the BSD license
        """
        # Check if jupyter_runtime_dir exists (Spyder addition)
        if not osp.isdir(jupyter_runtime_dir()):
            try:
                os.makedirs(jupyter_runtime_dir())
            except (IOError, OSError):
                return None
        cf = ''
        while not cf:
            ident = str(uuid.uuid4()).split('-')[-1]
            cf = os.path.join(jupyter_runtime_dir(), 'kernel-%s.json' % ident)
            cf = cf if not os.path.exists(cf) else ''
        return cf

    def _shellwidget_started(self, client):
        self.sig_shellwidget_created.emit(client.shellwidget)

    def _shellwidget_deleted(self, client):
        try:
            self.sig_shellwidget_deleted.emit(client.shellwidget)
        except RuntimeError:
            pass

    @Slot()
    def _create_client_for_kernel(self):
        """Create a client connected to an existing kernel"""
        connect_output = KernelConnectionDialog.get_connection_parameters(self)
        (connection_file, hostname, sshkey, password, ok) = connect_output
        if not ok:
            return
        else:
            self.create_client_for_kernel(connection_file, hostname, sshkey,
                                          password)

    # ---- Public API
    # -------------------------------------------------------------------------

    # ---- General
    # -------------------------------------------------------------------------
    def update_font(self, font, rich_font):
        self._font = font
        self._rich_font = rich_font

        if self.enable_infowidget:
            self.infowidget.set_font(rich_font)

        for client in self.clients:
            client.set_font(font)

    def refresh_container(self, give_focus=False):
        """
        Refresh interface depending on the current widget client available.

        Refreshes corner widgets and actions as well as the info widget and
        sets the shellwdiget and client signals
        """
        client = None
        if self.tabwidget.count():
            for instance_client in self.clients:
                try:
                    instance_client.timer.timeout.disconnect()
                except (RuntimeError, TypeError):
                    pass

            client = self.tabwidget.currentWidget()

            # Decide what to show for each client
            if (client.info_page != client.blank_page and
                    self.enable_infowidget):
                # Show info_page if it has content
                client.set_info_page()
                client.shellwidget.hide()
                client.layout.addWidget(self.infowidget)
                self.infowidget.show()
            else:
                if self.enable_infowidget:
                    self.infowidget.hide()
                client.shellwidget.show()

            # Get reference for the control widget of the selected tab
            # and give focus if needed
            control = client.get_control()
            if give_focus:
                control.setFocus()

            if isinstance(control, PageControlWidget):
                self.pager_label.show()
            else:
                self.pager_label.hide()

            # Setup elapsed time
            show_elapsed_time = client.show_elapsed_time
            self.show_time_action.setChecked(show_elapsed_time)
            client.timer.timeout.connect(client.show_time)
        else:
            control = None
        self.find_widget.set_editor(control)

        if client:
            sw = client.shellwidget
            self.sig_pdb_state_changed.emit(
                sw.is_waiting_pdb_input(), sw.get_pdb_last_step())
            self.sig_shellwidget_changed.emit(sw)

            # This is necessary to sync the current client cwd with the working
            # directory displayed by other plugins in Spyder (e.g. Files).
            # NOTE: Instead of emitting sig_current_directory_changed directly,
            # we call on_working_directory_changed to validate that the cwd
            # exists (this couldn't be the case for remote kernels).
            if sw.get_cwd() != self.get_working_directory():
                self.on_working_directory_changed(sw.get_cwd())

        self.update_tabs_text()
        self.update_actions()

    # ---- For tabs
    # -------------------------------------------------------------------------
    def add_tab(self, client, name, filename='', give_focus=True):
        """Add tab."""
        if not isinstance(client, ClientWidget):
            return
        self.clients.append(client)
        index = self.tabwidget.addTab(client, name)
        self.filenames.insert(index, filename)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget and give_focus:
            self.sig_switch_to_plugin_requested.emit()
        self.activateWindow()
        client.get_control().setFocus()
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
        """Rename a client's tab."""
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
        for cl in self.clients:
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

    # --- For clients
    # -------------------------------------------------------------------------

    # ---- For magics and configurations
    @Slot(object, object)
    def edit_file(self, filename, line):
        """Handle %edit magic petitions."""
        if not osp.isfile(filename):
            self.sig_edit_new.emit(filename)
        if encoding.is_text_file(filename):
            # The default line number sent by ipykernel is always the last
            # one, but we prefer to use the first.
            self.sig_edit_goto_requested.emit(filename, 1, '')

    def config_options(self):
        """
        Generate a Trailets Config instance for shell widgets using our
        config system

        This lets us create each widget with its own config
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
        completion_type_o = self.get_conf('completion_type')
        completions = COMPLETION_WIDGET_TYPE
        spy_cfg.JupyterWidget.gui_completion = completions[completion_type_o]

        # Calltips
        calltips_o = self.get_conf('show_calltips')
        spy_cfg.JupyterWidget.enable_calltips = calltips_o

        # Buffer size
        buffer_size_o = self.get_conf('buffer_size')
        spy_cfg.JupyterWidget.buffer_size = buffer_size_o

        # Prompts
        in_prompt_o = self.get_conf('in_prompt')
        out_prompt_o = self.get_conf('out_prompt')
        if bool(in_prompt_o):
            spy_cfg.JupyterWidget.in_prompt = in_prompt_o
        if bool(out_prompt_o):
            spy_cfg.JupyterWidget.out_prompt = out_prompt_o

        # Style
        color_scheme = self.get_conf('selected', section='appearance')
        style_sheet = create_qss_style(color_scheme)[0]
        spy_cfg.JupyterWidget.style_sheet = style_sheet
        spy_cfg.JupyterWidget.syntax_style = color_scheme

        # Merge QtConsole and Spyder configs. Spyder prefs will have
        # prevalence over QtConsole ones
        cfg._merge(spy_cfg)
        return cfg

    def interpreter_versions(self):
        """Python and IPython versions used by clients"""
        if self.get_conf('default', section='main_interpreter'):
            from IPython.core import release
            versions = dict(
                python_version=sys.version,
                ipython_version=release.version
            )
        else:
            import subprocess
            versions = {}
            pyexec = self.get_conf('executable', section='main_interpreter')
            py_cmd = u'%s -c "import sys; print(sys.version)"' % pyexec
            ipy_cmd = (
                u'%s -c "import IPython.core.release as r; print(r.version)"'
                % pyexec
            )
            for cmd in [py_cmd, ipy_cmd]:
                try:
                    # Use clean environment
                    proc = programs.run_shell_command(cmd, env={})
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
        in JupyterWidget config options
        """
        options = dict(
            pylab=self.get_conf('pylab'),
            autoload_pylab=self.get_conf('pylab/autoload'),
            sympy=self.get_conf('symbolic_math'),
            show_banner=self.get_conf('show_banner')
        )

        if is_pylab is True:
            options['autoload_pylab'] = True
            options['sympy'] = False
        if is_sympy is True:
            options['autoload_pylab'] = False
            options['sympy'] = True

        return options

    # ---- For client widgets
    def set_client_elapsed_time(self, client):
        """Set elapsed time for slave clients."""
        related_clients = self.get_related_clients(client)
        for cl in related_clients:
            if cl.timer is not None:
                client.t0 = cl.t0
                client.timer.timeout.connect(client.show_time)
                client.timer.start(1000)
                break

    def get_focus_client(self):
        """Return current client with focus, if any"""
        widget = QApplication.focusWidget()
        for client in self.clients:
            if widget is client or widget is client.get_control():
                return client

    def get_current_client(self):
        """Return the currently selected client"""
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client

    def get_current_shellwidget(self):
        """Return the shellwidget of the current client"""
        client = self.get_current_client()
        if client is not None:
            return client.shellwidget

    @Slot()
    @Slot(bool)
    @Slot(str)
    @Slot(bool, str)
    @Slot(bool, bool)
    @Slot(bool, str, bool)
    def create_new_client(self, give_focus=True, filename='', is_cython=False,
                          is_pylab=False, is_sympy=False, given_name=None,
                          cache=True, initial_cwd=None):
        """Create a new client"""
        self.master_clients += 1
        client_id = dict(int_id=str(self.master_clients),
                         str_id='A')
        std_dir = self._test_dir if self._test_dir else None
        cf, km, kc, stderr_obj, stdout_obj = self.get_new_kernel(
            is_cython, is_pylab, is_sympy, std_dir=std_dir, cache=cache)

        if cf is not None:
            fault_obj = StdFile(cf, '.fault', std_dir)
        else:
            fault_obj = None

        show_elapsed_time = self.get_conf('show_elapsed_time')
        reset_warning = self.get_conf('show_reset_namespace_warning')
        ask_before_restart = self.get_conf('ask_before_restart')
        ask_before_closing = self.get_conf('ask_before_closing')
        client = ClientWidget(self, id_=client_id,
                              history_filename=get_conf_path('history.py'),
                              config_options=self.config_options(),
                              additional_options=self.additional_options(
                                      is_pylab=is_pylab,
                                      is_sympy=is_sympy),
                              interpreter_versions=self.interpreter_versions(),
                              connection_file=cf,
                              context_menu_actions=self.context_menu_actions,
                              show_elapsed_time=show_elapsed_time,
                              reset_warning=reset_warning,
                              given_name=given_name,
                              give_focus=give_focus,
                              ask_before_restart=ask_before_restart,
                              ask_before_closing=ask_before_closing,
                              css_path=self.css_path,
                              handlers=self.registered_spyder_kernel_handlers,
                              stderr_obj=stderr_obj,
                              stdout_obj=stdout_obj,
                              fault_obj=fault_obj,
                              initial_cwd=initial_cwd)

        self.add_tab(
            client, name=client.get_name(), filename=filename,
            give_focus=give_focus)

        if cf is None:
            error_msg = self.PERMISSION_ERROR_MSG.format(jupyter_runtime_dir())
            client.show_kernel_error(error_msg)
            return

        # Check if ipykernel is present in the external interpreter.
        # Else we won't be able to create a client
        if not client.has_spyder_kernels():
            return

        self.connect_client_to_kernel(client, km, kc)
        if client.shellwidget.kernel_manager is None:
            return
        self.register_client(client, give_focus=give_focus)
        return client

    def create_client_for_kernel(self, connection_file, hostname, sshkey,
                                 password):
        """Create a client connected to an existing kernel."""
        # Verifying if the connection file exists
        try:
            cf_path = osp.dirname(connection_file)
            cf_filename = osp.basename(connection_file)
            # To change a possible empty string to None
            cf_path = cf_path if cf_path else None
            connection_file = find_connection_file(filename=cf_filename,
                                                   path=cf_path)
            if os.path.splitext(connection_file)[1] != ".json":
                # There might be a file with the same id in the path.
                connection_file = find_connection_file(
                    filename=cf_filename + ".json", path=cf_path)
        except (IOError, UnboundLocalError):
            QMessageBox.critical(self, _('IPython'),
                                 _("Unable to connect to "
                                   "<b>%s</b>") % connection_file)
            return

        # Getting the master id that corresponds to the client
        # (i.e. the i in i/A)
        master_id = None
        given_name = None
        is_external_kernel = True
        known_spyder_kernel = False
        slave_ord = ord('A') - 1
        kernel_manager = None
        stderr_obj = None
        stdout_obj = None
        fault_obj = None

        for cl in self.clients:
            if connection_file in cl.connection_file:
                if cl.get_kernel() is not None:
                    kernel_manager = cl.get_kernel()
                connection_file = cl.connection_file
                if master_id is None:
                    master_id = cl.id_['int_id']
                    is_external_kernel = cl.shellwidget.is_external_kernel
                    known_spyder_kernel = cl.shellwidget.is_spyder_kernel
                    if cl.stderr_obj:
                        stderr_obj = cl.stderr_obj.copy()
                    if cl.stdout_obj:
                        stdout_obj = cl.stdout_obj.copy()
                    if cl.fault_obj:
                        fault_obj = cl.fault_obj.copy()
                given_name = cl.given_name
                new_slave_ord = ord(cl.id_['str_id'])
                if new_slave_ord > slave_ord:
                    slave_ord = new_slave_ord

        # If we couldn't find a client with the same connection file,
        # it means this is a new master client
        if master_id is None:
            self.master_clients += 1
            master_id = str(self.master_clients)

        # Set full client name
        client_id = dict(int_id=master_id,
                         str_id=chr(slave_ord + 1))

        # Creating the client
        show_elapsed_time = self.get_conf('show_elapsed_time')
        reset_warning = self.get_conf('show_reset_namespace_warning')
        ask_before_restart = self.get_conf('ask_before_restart')
        client = ClientWidget(self,
                              id_=client_id,
                              given_name=given_name,
                              history_filename=get_conf_path('history.py'),
                              config_options=self.config_options(),
                              additional_options=self.additional_options(),
                              interpreter_versions=self.interpreter_versions(),
                              connection_file=connection_file,
                              context_menu_actions=self.context_menu_actions,
                              hostname=hostname,
                              is_external_kernel=is_external_kernel,
                              is_spyder_kernel=known_spyder_kernel,
                              show_elapsed_time=show_elapsed_time,
                              reset_warning=reset_warning,
                              ask_before_restart=ask_before_restart,
                              css_path=self.css_path,
                              handlers=self.registered_spyder_kernel_handlers,
                              stderr_obj=stderr_obj,
                              stdout_obj=stdout_obj,
                              fault_obj=fault_obj)

        # Create kernel client
        kernel_client = QtKernelClient(connection_file=connection_file)

        # This is needed for issue spyder-ide/spyder#9304.
        try:
            kernel_client.load_connection_file()
        except Exception as e:
            QMessageBox.critical(self, _('Connection error'),
                                 _("An error occurred while trying to load "
                                   "the kernel connection file. The error "
                                   "was:\n\n") + str(e))
            return

        if hostname is not None:
            try:
                connection_info = dict(
                    ip=kernel_client.ip,
                    shell_port=kernel_client.shell_port,
                    iopub_port=kernel_client.iopub_port,
                    stdin_port=kernel_client.stdin_port,
                    hb_port=kernel_client.hb_port)
                newports = self.tunnel_to_kernel(connection_info, hostname,
                                                 sshkey, password)
                (kernel_client.shell_port,
                 kernel_client.iopub_port,
                 kernel_client.stdin_port,
                 kernel_client.hb_port) = newports
                # Save parameters to connect comm later
                kernel_client.ssh_parameters = (hostname, sshkey, password)
            except Exception as e:
                QMessageBox.critical(self, _('Connection error'),
                                     _("Could not open ssh tunnel. The "
                                       "error was:\n\n") + str(e))
                return

        # Assign kernel manager and client to shellwidget
        kernel_client.start_channels()
        shellwidget = client.shellwidget
        shellwidget.set_kernel_client_and_manager(
            kernel_client, kernel_manager)
        shellwidget.sig_exception_occurred.connect(
            self.sig_exception_occurred)

        if not known_spyder_kernel:
            shellwidget.sig_is_spykernel.connect(
                self.connect_external_spyder_kernel)
            shellwidget.check_spyder_kernel()

        self.sig_shellwidget_created.emit(shellwidget)
        kernel_client.stopped_channels.connect(
            lambda: self.sig_shellwidget_deleted.emit(shellwidget))

        # Set elapsed time, if possible
        if not is_external_kernel:
            self.set_client_elapsed_time(client)

        # Adding a new tab for the client
        self.add_tab(client, name=client.get_name())

        # Register client
        self.register_client(client)

    def create_pylab_client(self):
        """Force creation of Pylab client"""
        self.create_new_client(is_pylab=True, given_name="Pylab")

    def create_sympy_client(self):
        """Force creation of SymPy client"""
        self.create_new_client(is_sympy=True, given_name="SymPy")

    def create_cython_client(self):
        """Force creation of Cython client"""
        self.create_new_client(is_cython=True, given_name="Cython")

    def get_new_kernel(self, is_cython=False, is_pylab=False,
                       is_sympy=False, std_dir=None, cache=True):
        """Get a new kernel, and cache one for next time."""
        # Cache another kernel for next time.
        kernel_spec = self.create_kernel_spec(
            is_cython=is_cython,
            is_pylab=is_pylab,
            is_sympy=is_sympy
        )

        new_kernel = self.create_new_kernel(kernel_spec, std_dir)

        if new_kernel[2] is None or not cache:
            # error or remove/don't use cache if requested
            self.close_cached_kernel()
            return new_kernel

        # Check cached kernel has the same configuration as is being asked
        cached_kernel = None
        if self._cached_kernel_properties is not None:
            (cached_spec,
             cached_env,
             cached_argv,
             cached_dir,
             cached_kernel) = self._cached_kernel_properties
            # Call interrupt_mode so the dict will be the same
            kernel_spec.interrupt_mode
            cached_spec.interrupt_mode
            valid = (std_dir == cached_dir
                     and cached_spec.__dict__ == kernel_spec.__dict__
                     and kernel_spec.argv == cached_argv
                     and kernel_spec.env == cached_env)
            if not valid:
                # Close the kernel
                self.close_cached_kernel()
                cached_kernel = None

        # Cache the new kernel
        self._cached_kernel_properties = (
            kernel_spec,
            kernel_spec.env,
            kernel_spec.argv,
            std_dir,
            new_kernel)

        if cached_kernel is None:
            return self.create_new_kernel(kernel_spec, std_dir)

        return cached_kernel

    def close_cached_kernel(self):
        """Close the cached kernel."""
        if self._cached_kernel_properties is None:
            return
        cached_kernel = self._cached_kernel_properties[-1]
        _, kernel_manager, _, stderr_obj, stdout_obj = cached_kernel
        kernel_manager.stop_restarter()
        kernel_manager.shutdown_kernel(now=True)
        self._cached_kernel_properties = None
        if stderr_obj:
            stderr_obj.remove()
        if stdout_obj:
            stdout_obj.remove()

    def create_new_kernel(self, kernel_spec, std_dir=None):
        """Create a new kernel."""
        connection_file = self._new_connection_file()
        if connection_file is None:
            return None, None, None, None, None

        stderr_obj = None
        stderr_handle = None
        stdout_obj = None
        stdout_handle = None
        if not self._test_no_stderr:
            stderr_obj = StdFile(connection_file, '.stderr', std_dir)
            stderr_handle = stderr_obj.handle
            stdout_obj = StdFile(connection_file, '.stdout', std_dir)
            stdout_handle = stdout_obj.handle

        km, kc = self.create_kernel_manager_and_kernel_client(
            connection_file,
            stderr_handle,
            stdout_handle,
            kernel_spec,
        )
        return connection_file, km, kc, stderr_obj, stdout_obj

    def connect_client_to_kernel(self, client, km, kc):
        """Connect a client to its kernel."""
        # An error occurred if this is True
        if isinstance(km, str) and kc is None:
            client.shellwidget.kernel_manager = None
            client.show_kernel_error(km)
            return

        # This avoids a recurrent, spurious NameError when running our
        # tests in our CIs
        if not self._testing:
            kc.stopped_channels.connect(
                lambda c=client: self._shellwidget_deleted(c))

        kc.start_channels(shell=True, iopub=True)

        shellwidget = client.shellwidget
        shellwidget.set_kernel_client_and_manager(kc, km)

        shellwidget.sig_exception_occurred.connect(
            self.sig_exception_occurred)

        # _shellwidget_started() – which emits sig_shellwidget_created() – must
        # be called *after* set_kernel_client_and_manager() has been called.
        # This is required so that plugins can rely on a initialized shell
        # widget in their implementation of
        # ShellConnectMainWidget.create_new_widget() (e.g. if they need to
        # communicate with the kernel using the shell widget kernel client).
        #
        # NOTE kc.started_channels() signal must not be used to emit
        # sig_shellwidget_created(): kc.start_channels()
        # (QtKernelClientMixin.start_channels() from qtconsole module) emits the
        # started_channels() signal. Slots connected to this signal are called
        # directly from within start_channels() [1], i.e. before the shell
        # widget’s initialization by set_kernel_client_and_manager().
        #
        # [1] Assuming no threads are involved, i.e. the signal-slot connection
        # type is Qt.DirectConnection.
        self._shellwidget_started(client)

    @Slot(str)
    def create_client_from_path(self, path):
        """Create a client with its cwd pointing to path."""
        self.create_new_client(initial_cwd=path)

    def create_client_for_file(self, filename, is_cython=False):
        """Create a client to execute code related to a file."""
        # Create client
        client = self.create_new_client(
            filename=filename, is_cython=is_cython)

        # Don't increase the count of master clients
        self.master_clients -= 1

        # Rename client tab with filename
        client.allow_rename = False
        tab_text = self.disambiguate_fname(filename)
        self.rename_client_tab(client, tab_text)

        return client

    def get_client_for_file(self, filename):
        """Get client associated with a given file."""
        client = None
        for idx, cl in enumerate(self.clients):
            if self.filenames[idx] == filename:
                self.tabwidget.setCurrentIndex(idx)
                client = cl
                break
        return client

    def register_client(self, client, give_focus=True):
        """Register new client"""
        client.configure_shellwidget(give_focus=give_focus)

        # Local vars
        shellwidget = client.shellwidget
        control = shellwidget._control

        # Create new clients with Ctrl+T shortcut
        shellwidget.sig_new_client.connect(self.create_new_client)

        # For tracebacks
        control.sig_go_to_error_requested.connect(self.go_to_error)

        # For help requests
        control.sig_help_requested.connect(self.sig_help_requested)

        shellwidget.sig_pdb_step.connect(
            lambda fname, lineno, shellwidget=shellwidget:
            self.pdb_has_stopped(fname, lineno, shellwidget))
        shellwidget.sig_pdb_state_changed.connect(self.sig_pdb_state_changed)

        # To handle %edit magic petitions
        shellwidget.custom_edit_requested.connect(self.edit_file)

        # Connect client to history log
        self.sig_history_requested.emit(client.history_filename)
        client.sig_append_to_history_requested.connect(
            self.sig_append_to_history_requested)

        # Set font for client
        client.set_font(self._font)

        # Set editor for the find widget
        self.find_widget.set_editor(control)

        # Connect to working directory
        shellwidget.sig_working_directory_changed.connect(
            self.on_working_directory_changed)

        # Connect client execution state to be reflected in the interface
        client.sig_execution_state_changed.connect(self.update_actions)

        # Show time label
        client.sig_time_label.connect(self.time_label.setText)

    def close_client(self, index=None, client=None, ask_recursive=True):
        """Close client tab from index or widget (or close current tab)"""
        if not self.tabwidget.count():
            return
        if client is not None:
            if client not in self.clients:
                # Client already closed
                return
            index = self.tabwidget.indexOf(client)
            # if index is not found in tabwidget it's because this client was
            # already closed and the call was performed by the exit callback
            if index == -1:
                return
        if index is None and client is None:
            index = self.tabwidget.currentIndex()
        if index is not None:
            client = self.tabwidget.widget(index)

        # Check if related clients or kernels are opened
        # and eventually ask before closing them
        if not self.mainwindow_close and ask_recursive:
            close_all = True
            if client.ask_before_closing:
                close = QMessageBox.question(
                    self,
                    self._plugin.get_name(),
                    _("Do you want to close this console?"),
                    QMessageBox.Yes | QMessageBox.No)
                if close == QMessageBox.No:
                    return
            if len(self.get_related_clients(client)) > 0:
                close_all = QMessageBox.question(
                    self,
                    self._plugin.get_name(),
                    _("Do you want to close all other consoles connected "
                      "to the same kernel as this one?"),
                    QMessageBox.Yes | QMessageBox.No)

            if close_all == QMessageBox.Yes:
                self.close_related_clients(client)

        # Note: client index may have changed after closing related widgets
        self.tabwidget.removeTab(self.tabwidget.indexOf(client))
        self.clients.remove(client)
        is_last_client = len(self.get_related_clients(client)) == 0
        client.close_client(is_last_client)

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

    def close_all_clients(self):
        """
        Perform close actions for each running client.

        Returns
        -------
        bool
            If the closing action was succesful.
        """
        # IMPORTANT: **Do not** change this way of closing clients, which uses
        # a copy of `self.clients`, because it preserves the main window layout
        # when Spyder is closed.
        # Fixes spyder-ide/spyder#19084
        open_clients = self.clients.copy()
        for client in self.clients:
            is_last_client = (
                len(self.get_related_clients(client, open_clients)) == 0)
            client.close_client(is_last_client)
            open_clients.remove(client)

        # Close all closing shellwidgets.
        ShellWidget.wait_all_shutdown()

        # Close cached kernel
        self.close_cached_kernel()
        self.filenames = []
        return True

    def get_client_index_from_id(self, client_id):
        """Return client index from id"""
        for index, client in enumerate(self.clients):
            if id(client) == client_id:
                return index

    def get_related_clients(self, client, clients_list=None):
        """
        Get all other clients that are connected to the same kernel as `client`
        """
        if clients_list is None:
            clients_list = self.clients
        related_clients = []
        for cl in clients_list:
            if (cl.connection_file == client.connection_file and
                    cl is not client):
                related_clients.append(cl)
        return related_clients

    def close_related_clients(self, client):
        """Close all clients related to *client*, except itself"""
        related_clients = self.get_related_clients(client)
        for client in related_clients:
            self.close_client(client=client, ask_recursive=False)

    def restart(self):
        """
        Restart the console

        This is needed when we switch projects to update PYTHONPATH
        and the selected interpreter
        """
        self.master_clients = 0
        self.create_new_client_if_empty = False
        for i in range(len(self.clients)):
            client = self.clients[-1]
            self.close_client(client=client, ask_recursive=False)
        self.create_new_client(give_focus=False, cache=False)
        self.create_new_client_if_empty = True

    def current_client_inspect_object(self):
        client = self.get_current_client()
        if client:
            client.inspect_object()

    def current_client_clear_line(self):
        client = self.get_current_client()
        if client:
            client.clear_line()

    def current_client_clear_console(self):
        client = self.get_current_client()
        if client:
            client.clear_console()

    def current_client_quit(self):
        client = self.get_current_client()
        if client:
            client.exit_callback()

    def current_client_enter_array_inline(self):
        client = self.get_current_client()
        if client:
            client.enter_array_inline()

    def current_client_enter_array_table(self):
        client = self.get_current_client()
        if client:
            client.enter_array_table()

    # ---- For kernels
    # -------------------------------------------------------------------------
    def register_spyder_kernel_call_handler(self, handler_id, handler):
        """
        Register a callback for it to be available for newly created
        client kernels.

        Parameters
        ----------
        handler_id : str
            Handler name to be registered and that will be used to
            call the respective handler from the Spyder kernel.
        handler : func
            Callback function that will be called when the kernel request
            the handler_id identifier.

        Returns
        -------
        None.
        """
        self.registered_spyder_kernel_handlers[handler_id] = handler

    def unregister_spyder_kernel_call_handler(self, handler_id):
        """
        Unregister and remove a handler to not be added to newly created
        client kernels.

        Parameters
        ----------
        handler_id : str
            Handler name that was registered and will be removed from
            the Spyder kernel available handlers.

        Returns
        -------
        None.
        """
        self.registered_spyder_kernel_handlers.pop(handler_id, None)

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
        return SpyderKernelSpec(is_cython=is_cython,
                                is_pylab=is_pylab,
                                is_sympy=is_sympy)

    def create_kernel_manager_and_kernel_client(self, connection_file,
                                                stderr_handle,
                                                stdout_handle,
                                                kernel_spec):
        """Create kernel manager and client."""
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
            kernel_manager.start_kernel(stderr=stderr_handle,
                                        stdout=stdout_handle,
                                        env=kernel_spec.env)
        except Exception:
            error_msg = _("The error is:<br><br>"
                          "<tt>{}</tt>").format(traceback.format_exc())
            return (error_msg, None)

        # Kernel client
        kernel_client = kernel_manager.client()

        # Increase time (in seconds) to detect if a kernel is alive.
        # See spyder-ide/spyder#3444.
        kernel_client.hb_channel.time_to_dead = 25.0

        return kernel_manager, kernel_client

    def restart_kernel(self):
        """Restart kernel of current client."""
        client = self.get_current_client()
        if client is not None:
            self.sig_switch_to_plugin_requested.emit()
            client.restart_kernel()

    def reset_namespace(self):
        """Reset namespace of current client."""
        client = self.get_current_client()
        if client is not None:
            self.sig_switch_to_plugin_requested.emit()
            client.reset_namespace()

    def interrupt_kernel(self):
        """Interrupt kernel of current client."""
        client = self.get_current_client()
        if client is not None:
            self.sig_switch_to_plugin_requested.emit()
            client.stop_button_click_handler()

    def connect_external_spyder_kernel(self, shellwidget):
        """Connect to an external Spyder kernel."""
        shellwidget.is_spyder_kernel = True
        shellwidget.spyder_kernel_comm.open_comm(shellwidget.kernel_client)
        self.sig_shellwidget_changed.emit(shellwidget)
        self.sig_external_spyder_kernel_connected.emit(shellwidget)

    # ---- For running and debugging
    # --------------------------------------------------------------------------

    # ---- For general debugging
    def pdb_has_stopped(self, fname, lineno, shellwidget):
        """Python debugger has just stopped at frame (fname, lineno)"""
        # This is a unique form of the sig_edit_goto_requested signal that
        # is intended to prevent keyboard input from accidentally entering the
        # editor during repeated, rapid entry of debugging commands.
        self.sig_edit_goto_requested[str, int, str, bool].emit(
            fname, lineno, '', False)

        # Give focus to console if requested
        if shellwidget._pdb_focus_to_editor:
            # Next focus to editor was enabled
            shellwidget._pdb_focus_to_editor = False
        else:
            self.activateWindow()
            shellwidget._control.setFocus()

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into all clients"""
        for cl in self.clients:
            cl.shellwidget.set_spyder_breakpoints()

    def pdb_execute_command(self, command, focus_to_editor):
        """
        Send command to the pdb kernel if possible.
        """
        sw = self.get_current_shellwidget()
        if sw is not None:
            # Needed to handle an error when kernel_client is None.
            # See spyder-ide/spyder#7578.
            try:
                sw.pdb_execute_command(command, focus_to_editor)
            except AttributeError:
                pass

    def stop_debugging(self):
        """Stop debugging"""
        sw = self.get_current_shellwidget()
        if sw is not None:
            sw.stop_debugging()

    def get_pdb_state(self):
        """Get debugging state of the current console."""
        sw = self.get_current_shellwidget()
        if sw is not None:
            return sw.is_waiting_pdb_input()
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

    def print_debug_file_msg(self):
        """Print message in the current console when a file can't be closed."""
        debug_msg = _('The current file cannot be closed because it is '
                      'in debug mode.')
        self.get_current_client().shellwidget.append_html_message(
            debug_msg, before_prompt=True)

    # ---- For cells
    def run_cell(self, code, cell_name, filename, run_cell_copy,
                 focus_to_editor, function='runcell'):
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
                line = (str(
                        "{}({}, '{}')").format(
                                str(function),
                                repr(cell_name),
                                norm(filename).replace("'", r"\'")))

                if function == "debugcell":
                    # To keep focus in editor after running debugfile
                    client.shellwidget._pdb_focus_to_editor = focus_to_editor
            # External kernels and run_cell_copy, just execute the code
            else:
                line = code.strip()

            try:
                self.execute_code(line, set_focus=not focus_to_editor)
            except AttributeError:
                pass

            # This is necessary to prevent raising the console if the editor
            # and console are tabified next to each other and the 'Maintain
            # focus in the editor' option is enabled.
            # Fixes spyder-ide/spyder#17028
            if not focus_to_editor:
                self.sig_switch_to_plugin_requested.emit()
        else:
            # XXX: not sure it can really happen
            QMessageBox.warning(
                self,
                _('Warning'),
                _("No IPython console is currently available "
                  "to run <b>{}</b>.<br><br>Please open a new "
                  "one and try again.").format(osp.basename(filename)),
                QMessageBox.Ok
            )

    def debug_cell(self, code, cell_name, filename, run_cell_copy,
                   focus_to_editor):
        """Debug current cell."""
        self.run_cell(code, cell_name, filename, run_cell_copy,
                      focus_to_editor, 'debugcell')

    # ---- For scripts
    def run_script(self, filename, wdir, args, debug, post_mortem,
                   current_client, clear_variables, console_namespace,
                   focus_to_editor):
        """Run script in current or dedicated client"""
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
                client = self.create_client_for_file(
                    filename, is_cython=is_cython)
                is_new_client = True

        if client is not None:
            # If spyder-kernels, use runfile
            if client.shellwidget.is_spyder_kernel:
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

                if debug:
                    # To keep focus in editor after running debugfile
                    client.shellwidget._pdb_focus_to_editor = focus_to_editor
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
                elif current_client:
                    self.execute_code(line, current_client, clear_variables,
                                      set_focus=not focus_to_editor)
                else:
                    if is_new_client:
                        client.shellwidget.silent_execute('%clear')
                    else:
                        client.shellwidget.execute('%clear')
                    client.shellwidget.sig_prompt_ready.connect(
                        lambda: self.execute_code(
                            line, current_client, clear_variables,
                            set_focus=not focus_to_editor,
                            shellwidget=client.shellwidget
                        )
                    )
            except AttributeError:
                pass

            # Show plugin after execution if focus is going to be given to it.
            if not focus_to_editor:
                self.sig_switch_to_plugin_requested.emit()
        else:
            # XXX: not sure it can really happen
            QMessageBox.warning(
                self,
                _('Warning'),
                _("No IPython console is currently available to run <b>%s</b>."
                  "<br><br>Please open a new one and try again."
                  ) % osp.basename(filename),
                QMessageBox.Ok
            )

    # ---- For working directory and path management
    def set_working_directory(self, dirname):
        """
        Set current working directory in the Working Directory and Files
        plugins.
        """
        if osp.isdir(dirname):
            self.sig_current_directory_changed.emit(dirname)

    def save_working_directory(self, dirname):
        """
        Save current working directory when changed by the Working Directory
        plugin.
        """
        self._current_working_directory = dirname

    def get_working_directory(self):
        """Get saved value of current working directory."""
        return self._current_working_directory

    def set_current_client_working_directory(self, directory):
        """Set current client working directory."""
        shellwidget = self.get_current_shellwidget()
        if shellwidget is not None:
            shellwidget.set_cwd(directory)

    def on_working_directory_changed(self, dirname):
        """
        Notify that the working directory was changed in the current console
        to other plugins.
        """
        if dirname and osp.isdir(dirname):
            self.sig_current_directory_changed.emit(dirname)

    def update_working_directory(self):
        """Update working directory to console cwd."""
        shellwidget = self.get_current_shellwidget()
        if shellwidget is not None:
            shellwidget.update_cwd()

    def update_path(self, path_dict, new_path_dict):
        """Update path on consoles."""
        logger.debug("Update sys.path in all console clients")
        for client in self.clients:
            shell = client.shellwidget
            if shell is not None:
                shell.update_syspath(path_dict, new_path_dict)

    def get_active_project_path(self):
        """Get the active project path."""
        return self.active_project_path

    def update_active_project_path(self, active_project_path):
        """
        Update the active project path attribute used to set the current
        working directory on the shells in case a project is active

        Parameters
        ----------
        active_project_path : str
            Root path of the active project if any.

        Returns
        -------
        None.
        """
        self.active_project_path = active_project_path

    # ---- For execution
    def execute_code(self, lines, current_client=True, clear_variables=False,
                     set_focus=True, shellwidget=None):
        """Execute code instructions."""
        if current_client:
            sw = self.get_current_shellwidget()
        else:
            sw = shellwidget
        if sw is not None:
            if not current_client:
                # Clear console and reset namespace for
                # dedicated clients.
                # See spyder-ide/spyder#5748.
                try:
                    sw.sig_prompt_ready.disconnect()
                except TypeError:
                    pass
                if clear_variables:
                    sw.reset_namespace(warning=False)
            elif current_client and clear_variables:
                sw.reset_namespace(warning=False)

            # Needed to handle an error when kernel_client is none.
            # See spyder-ide/spyder#6308.
            try:
                sw.execute(str(lines))
            except AttributeError:
                pass

            if set_focus:
                # The `activateWindow` call below needs to be inside this `if`
                # to avoid giving focus to the console when it's undocked,
                # users are running code from the editor and the 'Maintain
                # focus in the editor' option is enabled.
                # Fixes spyder-ide/spyder#3221
                self.activateWindow()

                # Gives focus to the current client
                focus_widget = self.get_focus_widget()
                if focus_widget:
                    focus_widget.setFocus()

    # ---- For error handling
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(str(text))
        if match:
            fname, lnb = match.groups()
            if (
                "<ipython-input-" in fname
                and self.run_cell_filename is not None
            ):
                fname = self.run_cell_filename

            # For IPython 8+ tracebacks.
            # Fixes spyder-ide/spyder#20407
            if '~' in fname:
                fname = osp.expanduser(fname)

            # This is needed to fix issue spyder-ide/spyder#9217.
            try:
                self.sig_edit_goto_requested.emit(
                    osp.abspath(fname), int(lnb), '')
            except ValueError:
                pass

    # ---- For documentation and help using the Help plugin
    # ------------------------------------------------------------------------
    @Slot()
    def show_intro(self):
        """Show intro to IPython help"""
        from IPython.core.usage import interactive_usage
        self.sig_render_rich_text_requested.emit(interactive_usage, False)

    @Slot()
    def show_guiref(self):
        """Show qtconsole help"""
        from qtconsole.usage import gui_reference
        self.sig_render_rich_text_requested.emit(gui_reference, True)

    @Slot()
    def show_quickref(self):
        """Show IPython Cheat Sheet"""
        from IPython.core.usage import quick_reference
        self.sig_render_plain_text_requested.emit(quick_reference)

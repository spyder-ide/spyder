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

# Third-party imports
from jupyter_client.connect import find_connection_file
from jupyter_core.paths import jupyter_config_dir
from qtpy.QtCore import Signal, Slot
from qtpy.QtGui import QColor
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget)
from traitlets.config.loader import Config, load_pyconfig_files

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.api.widgets.menus import MENU_SEPARATOR
from spyder.config.base import (
    get_home_dir, running_under_pytest)
from spyder.plugins.ipythonconsole.utils.kernel_handler import KernelHandler
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.plugins.ipythonconsole.utils.style import create_qss_style
from spyder.plugins.ipythonconsole.widgets import (
    ClientWidget, ConsoleRestartDialog, COMPLETION_WIDGET_TYPE,
    KernelConnectionDialog, PageControlWidget)
from spyder.plugins.ipythonconsole.widgets.mixins import CachedKernelMixin
from spyder.py3compat import PY38_OR_MORE
from spyder.utils import encoding, programs, sourcecode
from spyder.utils.misc import get_error_match, remove_backslashes
from spyder.utils.palette import QStylePalette
from spyder.widgets.browser import FrameWebView
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.tabs import Tabs


# Localization
_ = get_translation('spyder')

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


class IPythonConsoleWidgetConsolesMenusSection:
    Main = 'main_section'


class IPythonConsoleWidgetOptionsMenuSections:
    Consoles = 'consoles_section'
    Edit = 'edit_section'
    View = 'view_section'


# --- Widgets
# ----------------------------------------------------------------------------
class IPythonConsoleWidget(PluginMainWidget, CachedKernelMixin):
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

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        self.menu_actions = None
        self.master_clients = 0
        self.clients = []
        self.filenames = []
        self.mainwindow_close = False
        self.active_project_path = None
        self.create_new_client_if_empty = True
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
        self.pager_label.setStyleSheet(
            f"background-color: {QStylePalette.COLOR_ACCENT_2};"
            f"color: {QStylePalette.COLOR_TEXT_1};"
            "margin: 0px 1px 4px 1px;"
            "padding: 5px;"
            "qproperty-alignment: AlignCenter;"
        )
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
        # Options menu actions
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

        # For the client
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

        # Context menu actions
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

        # Other actions with shortcuts
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
                menu=self.special_console_menu,
                section=IPythonConsoleWidgetConsolesMenusSection.Main,
            )

        # Widgets for the tab corner
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

        # Add tab corner widgets.
        self.add_corner_widget('timer', self.time_label)
        self.add_corner_widget('reset', self.reset_button)
        self.add_corner_widget('start_interrupt', self.stop_button)

        # Create IPython documentation menu
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
            executing = client.is_client_executing()
            self.interrupt_action.setEnabled(executing)
            self.stop_button.setEnabled(executing)

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
                self.restart_kernel(client, ask_before_restart=False)

        if (
            (
                (pylab_restart and current_client_backend_require_restart)
                 or restart_needed
            )
            and restart_current
            and current_client
        ):
            self.restart_kernel(current_client, ask_before_restart=False)

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
        if os.name == 'nt' and PY38_OR_MORE:
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

    @Slot()
    def _create_client_for_kernel(self):
        """Create a client connected to an existing kernel"""
        connect_output = KernelConnectionDialog.get_connection_parameters(self)
        (connection_file, hostname, sshkey, password, ok) = connect_output
        if not ok:
            return

        try:
            # Fix path
            connection_file = self.find_connection_file(connection_file)
        except (IOError, UnboundLocalError):
            QMessageBox.critical(self, _('IPython'),
                                 _("Unable to connect to "
                                   "<b>%s</b>") % connection_file)
            return

        self.create_client_for_kernel(
            connection_file, hostname, sshkey, password)

    def find_connection_file(self, connection_file):
        """Fix connection file path."""
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
        return connection_file

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
        sets the shellwidget and client signals
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

        # Register client
        self.register_client(client)

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

        client = ClientWidget(
            self,
            id_=client_id,
            config_options=self.config_options(),
            additional_options=self.additional_options(
                    is_pylab=is_pylab,
                    is_sympy=is_sympy),
            interpreter_versions=self.interpreter_versions(),
            context_menu_actions=self.context_menu_actions,
            given_name=given_name,
            give_focus=give_focus,
            handlers=self.registered_spyder_kernel_handlers,
            initial_cwd=initial_cwd,
        )

        # Add client to widget
        self.add_tab(
            client, name=client.get_name(), filename=filename,
            give_focus=give_focus)

        # Create new kernel
        kernel_spec = SpyderKernelSpec(
            is_cython=is_cython,
            is_pylab=is_pylab,
            is_sympy=is_sympy
        )

        try:
            kernel_handler = self.get_cached_kernel(kernel_spec, cache=cache)
        except Exception as e:
            client.show_kernel_error(e)
            return

        # Connect kernel to client
        client.connect_kernel(kernel_handler)
        return client

    def create_client_for_kernel(self, connection_file, hostname, sshkey,
                                 password):
        """Create a client connected to an existing kernel."""
        given_name = None
        master_client = None

        related_clients = []
        for cl in self.clients:
            if connection_file in cl.connection_file:
                if (
                    cl.kernel_handler is not None and
                    hostname == cl.kernel_handler.hostname and
                    sshkey == cl.kernel_handler.sshkey and
                    password == cl.kernel_handler.password
                ):
                    related_clients.append(cl)

        if len(related_clients) > 0:
            # Get master client
            master_client = related_clients[0]
            given_name = master_client.given_name
            slave_ord = ord('A') - 1
            for cl in related_clients:
                new_slave_ord = ord(cl.id_['str_id'])
                if new_slave_ord > slave_ord:
                    slave_ord = new_slave_ord

            # Set full client name
            client_id = dict(int_id=master_client.id_['int_id'],
                             str_id=chr(slave_ord + 1))
        else:
            # If we couldn't find a client with the same connection file,
            # it means this is a new master client
            self.master_clients += 1

            # Set full client name
            client_id = dict(int_id=str(self.master_clients), str_id='A')

        # Creating the client
        client = ClientWidget(
            self,
            id_=client_id,
            given_name=given_name,
            config_options=self.config_options(),
            additional_options=self.additional_options(),
            interpreter_versions=self.interpreter_versions(),
            context_menu_actions=self.context_menu_actions,
            handlers=self.registered_spyder_kernel_handlers
        )

        # add hostname for get_name
        client.hostname = hostname

        # Adding a new tab for the client
        self.add_tab(client, name=client.get_name())

        # Set elapsed time, if possible
        if master_client is not None:
            client.t0 = master_client.t0
            client.timer.timeout.connect(client.show_time)
            client.timer.start(1000)

        try:
            # Get new client for kernel
            if master_client is not None:
                kernel_handler = master_client.kernel_handler.copy()
            else:
                kernel_handler = KernelHandler.from_connection_file(
                    connection_file, hostname, sshkey, password)
        except Exception as e:
            client.show_kernel_error(e)
            return

        # Connect kernel
        client.connect_kernel(kernel_handler)

    def create_pylab_client(self):
        """Force creation of Pylab client"""
        self.create_new_client(is_pylab=True, given_name="Pylab")

    def create_sympy_client(self):
        """Force creation of SymPy client"""
        self.create_new_client(is_sympy=True, given_name="SymPy")

    def create_cython_client(self):
        """Force creation of Cython client"""
        self.create_new_client(is_cython=True, given_name="Cython")

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

    def register_client(self, client):
        """Register new client"""
        client.connect_shellwidget_signals()

        # Local vars
        shellwidget = client.shellwidget
        control = shellwidget._control

        # Create new clients with Ctrl+T shortcut
        shellwidget.new_client.connect(self.create_new_client)

        # For tracebacks
        control.sig_go_to_error_requested.connect(self.go_to_error)

        # For help requests
        control.sig_help_requested.connect(self.sig_help_requested)

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

        # Exception handling
        shellwidget.sig_exception_occurred.connect(
            self.sig_exception_occurred)

        # Closing Shellwidget
        shellwidget.sig_shellwidget_deleted.connect(
            self.sig_shellwidget_deleted)
        shellwidget.sig_shellwidget_created.connect(
            self.sig_shellwidget_created)

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
            if self.get_conf('ask_before_closing'):
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

        # Wait for all KernelHandler's to shutdown.
        for client in self.clients:
            if client.kernel_handler:
                client.kernel_handler.wait_shutdown_thread()

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

    @Slot()
    def restart_kernel(self, client=None, ask_before_restart=True):
        """Restart kernel of current client."""
        if client is None:
            client = self.get_current_client()
        if client is None:
            return

        self.sig_switch_to_plugin_requested.emit()

        ask_before_restart = (
            ask_before_restart and self.get_conf('ask_before_restart'))

        do_restart = True
        if ask_before_restart and not running_under_pytest():
            message = _('Are you sure you want to restart the kernel?')
            buttons = QMessageBox.Yes | QMessageBox.No
            result = QMessageBox.question(
                self, _('Restart kernel?'), message, buttons)
            do_restart = result == QMessageBox.Yes

        if not do_restart:
            return

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

    # ---- For cells
    def run_cell(self, code, cell_name, filename, run_cell_copy,
                 method='runcell', focus_to_editor=False):
        """Run cell in current or dedicated client."""

        def norm(text):
            return remove_backslashes(str(text))

        self.run_cell_filename = filename

        # Select client to execute code on it
        client = self.get_client_for_file(filename)
        if client is None:
            client = self.get_current_client()

        if client is not None:
            is_spyder_kernel = client.shellwidget.is_spyder_kernel

            # Only use copy for runcell
            if method == 'runcell' and (run_cell_copy or not is_spyder_kernel):
                # Use copy of cell
                line = code.strip()
            elif is_spyder_kernel:
                # Use custom function
                line = (str(
                        "{}({}, '{}')").format(
                                str(method),
                                repr(cell_name),
                                norm(filename).replace("'", r"\'")))

                if method == "debugcell":
                    # To keep focus in editor after running debugfile
                    client.shellwidget._pdb_focus_to_editor = focus_to_editor
            # External kernels and run_cell_copy, just execute the code
            else:
                # Can not use custom function on non-spyder kernels
                client.shellwidget.append_html_message(
                    _("The console is not running a Spyder-kernel, so it "
                      "can't execute <b>{}</b>.<br><br>"
                      "Please use a Spyder-kernel for this.").format(method),
                    before_prompt=True
                )
                return

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

    # ---- For scripts
    def run_script(self, filename, wdir, args, post_mortem, current_client,
                   clear_variables, console_namespace, focus_to_editor,
                   method=None, force_wdir=False):
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
                client = self.create_client_for_file(
                    filename, is_cython=is_cython)
                is_new_client = True

        if client is not None:
            if method is None:
                method = "runfile"
            # If spyder-kernels, use runfile
            if client.shellwidget.is_spyder_kernel:
                line = method + "('%s'" % (norm(filename))
                if args:
                    line += ", args='%s'" % norm(args)
                if (
                    wdir and client.shellwidget.is_external_kernel
                    and not force_wdir
                ):
                    # No working directory for external kernels
                    wdir = ''
                if wdir:
                    line += ", wdir='%s'" % norm(wdir)
                if post_mortem:
                    line += ", post_mortem=True"
                if console_namespace:
                    line += ", current_namespace=True"
                line += ")"

                if method == "debugfile":
                    # To keep focus in editor after running debugfile
                    client.shellwidget._pdb_focus_to_editor = focus_to_editor
            elif method in ["runfile", "debugfile"]:
                # External, non spyder-kernels, use %run
                line = "%run "
                if method == "debugfile":
                    line += "-d "
                line += "\"%s\"" % str(filename)
                if args:
                    line += " %s" % norm(args)
            else:
                client.shellwidget.append_html_message(
                    _("The console is not running a Spyder-kernel, so it "
                      "can't execute <b>{}</b>.<br><br>"
                      "Please use a Spyder-kernel for this.").format(method),
                    before_prompt=True
                )
                return

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
            if ("<ipython-input-" in fname and
                    self.run_cell_filename is not None):
                fname = self.run_cell_filename
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

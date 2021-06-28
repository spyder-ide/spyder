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

# Third-party imports
from jupyter_client.connect import find_connection_file
from jupyter_core.paths import jupyter_config_dir, jupyter_runtime_dir
from qtconsole.client import QtKernelClient
from qtpy.QtCore import Slot
from qtpy.QtGui import QColor
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget)
from zmq.ssh import tunnel as zmqtunnel


# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.base import (
    get_conf_path, get_home_dir, running_under_pytest)
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
from spyder.plugins.ipythonconsole.widgets.client import ClientWidgetActions
from spyder.plugins.ipythonconsole.widgets import (
    ClientWidget, ConsoleRestartDialog, KernelConnectionDialog,
    PageControlWidget)
# TODO: Remove to_text_string calls and other PY2 compatibility logic
from spyder.py3compat import is_string, to_text_string, PY2, PY38_OR_MORE
from spyder.utils import programs, sourcecode
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
    CreateNewClient = 'create_new_client_action'
    CreateCythonClient = 'create_cython_client_action'
    CreateSymPyClient = 'create_sympy_client_action'
    CreatePyLabClient = 'create_pylab_client_action'
    
    # Current console actions
    ClearConsole = 'clear_console_action'
    ClearLine = 'clear_line'
    ConnectToKernel = 'connect_to_kernel_action'
    Interrupt = 'interrupt_action'
    InspectObject = 'inspect_object_action'
    Restart = 'restart_action'
    RemoveAllVariables = 'remove_all_variables_action'
    ResetNamespace = 'reset_namespace_action'

    # Tabs
    RenameTab = 'rename_tab_action'
    NewTab = 'new_tab_action'

    # Variables display
    ArrayInline = 'array_iniline_action'
    ArrayTable = 'array_table_action'


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
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget
    """

    # Error messages
    permission_error_msg = _("The directory {} is not writable and it is "
                             "required to create IPython consoles. Please "
                             "make it writable.")
    
    def __init__ (self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)
        
        self.tabwidget = None
        self.menu_actions = None
        self.master_clients = 0
        self.clients = []
        self.filenames = []
        self.mainwindow_close = False
        self.create_new_client_if_empty = True
        self.css_path = self.get_conf('css_path', section='appearance')
        self.run_cell_filename = None
        self.interrupt_action = None

        # Attrs for testing
        self._testing = self.get_conf('testing')
        self._test_dir = self.get_conf('test_dir')
        self._test_no_stderr = self.get_conf('test_no_stderr')

        # Create temp dir on testing to save kernel errors
        if self._test_dir is not None:
            if not osp.isdir(osp.join(self._test_dir)):
                os.makedirs(osp.join(self._test_dir))

        layout = QVBoxLayout()
        layout.setSpacing(0)
        self.tabwidget = Tabs(self, menu=self._options_menu,
                              actions=self.menu_actions,
                              rename_tabs=True,
                              split_char='/', split_index=0)
        if hasattr(self.tabwidget, 'setDocumentMode')\
           and not sys.platform == 'darwin':
            # Don't set document mode to true on OSX because it generates
            # a crash when the console is detached from the main window
            # Fixes spyder-ide/spyder#561.
            self.tabwidget.setDocumentMode(True)
        self.tabwidget.currentChanged.connect(self.refresh_plugin)
        self.tabwidget.tabBar().tabMoved.connect(self.move_tab)
        self.tabwidget.tabBar().sig_name_changed.connect(
            self.rename_tabs_after_change)

        self.tabwidget.set_close_function(self.close_client)

        self.main.editor.sig_file_debug_message_requested.connect(
            self.print_debug_file_msg)

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
        self.infowidget = FrameWebView(self)
        if WEBENGINE:
            self.infowidget.page().setBackgroundColor(QColor(MAIN_BG_COLOR))
        else:
            self.infowidget.setStyleSheet(
                "background:{}".format(MAIN_BG_COLOR))
        self.set_infowidget_font()
        layout.addWidget(self.infowidget)

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
        self.register_widget_shortcuts(self.find_widget)
        layout.addWidget(self.find_widget)

        self.setLayout(layout)

        # Accepting drops
        self.setAcceptDrops(True)

        # Needed to start Spyder in Windows with Python 3.8
        # See spyder-ide/spyder#11880
        self._init_asyncio_patch()

    
    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('IPython Console')

    def get_focus_widget(self):
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client.get_control()

    def setup(self):
        # ---- Options menu actions
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
        self.add_corner_widget('reset', self.reset_button)
        self.add_corner_widget('start_interrupt', self.stop_button)
        self.add_corner_widget('timer', self.time_label)

        # Check for a current client. Since it manages more actions.
        # TODO: Check other actions that are defined at client level
        # client = self.get_current_client()
        # if client:
        #     return client.get_options_menu()

    def update_style(self):
        font = self.get_font()
        for client in self.clients:
            client.set_font(font)

    def update_actions(self):
        pass

    # ---- Private API
    # -------------------------------------------------------------------------
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
        if self.main.variableexplorer is not None:
            self.main.variableexplorer.add_shellwidget(client.shellwidget)

        self.sig_shellwidget_created.emit(client.shellwidget)

    def _shellwidget_deleted(self, client):
        if self.main.variableexplorer is not None:
            self.main.variableexplorer.remove_shellwidget(client.shellwidget)

        self.sig_shellwidget_deleted.emit(client.shellwidget)

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
            QMessageBox.critical(self, _('IPython'),
                                 _("Unable to connect to "
                                   "<b>%s</b>") % connection_file)
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
            master_id = to_text_string(self.master_clients)
            external_kernel = True

        # Set full client name
        client_id = dict(int_id=master_id,
                         str_id=chr(slave_ord + 1))

        # Creating the client
        show_elapsed_time = self.get_option('show_elapsed_time')
        reset_warning = self.get_option('show_reset_namespace_warning')
        ask_before_restart = self.get_option('ask_before_restart')
        client = ClientWidget(self,
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
                              css_path=self.css_path)

        # Change stderr_dir if requested
        if self.test_dir is not None:
            client.stderr_dir = self.test_dir

        # Create kernel client
        kernel_client = QtKernelClient(connection_file=connection_file)

        # This is needed for issue spyder-ide/spyder#9304.
        try:
            kernel_client.load_connection_file()
        except Exception as e:
            QMessageBox.critical(self, _('Connection error'),
                                 _("An error occurred while trying to load "
                                   "the kernel connection file. The error "
                                   "was:\n\n") + to_text_string(e))
            return

        if hostname is not None:
            try:
                connection_info = dict(ip = kernel_client.ip,
                                       shell_port = kernel_client.shell_port,
                                       iopub_port = kernel_client.iopub_port,
                                       stdin_port = kernel_client.stdin_port,
                                       hb_port = kernel_client.hb_port)
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
                                     "error was:\n\n") + to_text_string(e))
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
            shellwidget.check_spyder_kernel()

        # Set elapsed time, if possible
        if not external_kernel:
            self.set_elapsed_time(client)

        # Adding a new tab for the client
        self.add_tab(client, name=client.get_name())

        # Register client
        self.register_client(client)


    # ---- Public API
    # -------------------------------------------------------------------------
    
    # ---- General
    # -------------------------------------------------------------------------
    def update_font(self, font, rich_font):
        self._font = font
        self._rich_font = rich_font

        if self.infowidget:
            self.infowidget.set_font(rich_font)

        for client in self.clients:
            client.set_font(font)

    # --- For clients
    # -------------------------------------------------------------------------
    def get_clients(self):
        """Return clients list"""
        return [cl for cl in self.clients if isinstance(cl, ClientWidget)]

    def get_focus_client(self):
        """Return current client with focus, if any"""
        widget = QApplication.focusWidget()
        for client in self.get_clients():
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
                          is_pylab=False, is_sympy=False, given_name=None):
        """Create a new client"""
        self.master_clients += 1
        client_id = dict(int_id=to_text_string(self.master_clients),
                         str_id='A')
        cf = self._new_connection_file()
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
                              menu_actions=self.menu_actions,
                              options_button=self.options_button,
                              show_elapsed_time=show_elapsed_time,
                              reset_warning=reset_warning,
                              given_name=given_name,
                              ask_before_restart=ask_before_restart,
                              ask_before_closing=ask_before_closing,
                              css_path=self.css_path)

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
        if not self.get_conf('default', section='main_interpreter'):
            pyexec = self.get_conf('executable', section='main_interpreter')
            has_spyder_kernels = programs.is_module_installed(
                'spyder_kernels',
                interpreter=pyexec,
                version='>=2.0.1;<2.1.0')
            if not has_spyder_kernels and not running_under_pytest():
                client.show_kernel_error(
                    _("Your Python environment or installation doesn't have "
                      "the <tt>spyder-kernels</tt> module or the right "
                      "version of it installed (>= 2.0.1 and < 2.1.0). "
                      "Without this module is not possible for Spyder to "
                      "create a console for you.<br><br>"
                      "You can install it by running in a system terminal:"
                      "<br><br>"
                      "<tt>conda install spyder-kernels=2.0</tt>"
                      "<br><br>or<br><br>"
                      "<tt>pip install spyder-kernels==2.0.*</tt>")
                )
                return

        self.connect_client_to_kernel(client, is_cython=is_cython,
                                      is_pylab=is_pylab, is_sympy=is_sympy)
        if client.shellwidget.kernel_manager is None:
            return
        self.register_client(client, give_focus=give_focus)

    def create_pylab_client(self):
        """Force creation of Pylab client"""
        self.create_new_client(is_pylab=True, given_name="Pylab")

    def create_sympy_client(self):
        """Force creation of SymPy client"""
        self.create_new_client(is_sympy=True, given_name="SymPy")

    def create_cython_client(self):
        """Force creation of Cython client"""
        self.create_new_client(is_cython=True, given_name="Cython")

    @Slot()
    def create_client_for_kernel(self):
        """Create a client connected to an existing kernel"""
        connect_output = KernelConnectionDialog.get_connection_parameters(self)
        (connection_file, hostname, sshkey, password, ok) = connect_output
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
                lambda c=client: self._shellwidget_started(c))
            kc.stopped_channels.connect(
                lambda c=client: self._shellwidget_deleted(c))

        kc.start_channels(shell=True, iopub=True)

        shellwidget = client.shellwidget
        shellwidget.set_kernel_client_and_manager(kc, km)

        # FIXME:
        shellwidget.sig_exception_occurred.connect(
            self.sig_exception_occurred)

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

    # ---- For kernels    
    # -------------------------------------------------------------------------
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
        # Before creating our kernel spec, we always need to
        # set this value in spyder.ini
        self.set_conf(
            'spyder_pythonpath',
            self.main.get_spyder_pythonpath(),
            section='main')
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
            kernel_manager.start_kernel(stderr=stderr_handle,
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
            self.switch_to_plugin()
            client.restart_kernel()

    def reset_kernel(self):
        """Reset kernel of current client."""
        client = self.get_current_client()
        if client is not None:
            self.switch_to_plugin()
            client.reset_namespace()

    def interrupt_kernel(self):
        """Interrupt kernel of current client."""
        client = self.get_current_client()
        if client is not None:
            self.switch_to_plugin()
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
        self.sig_shellwidget_changed.emit(sw)

        if self.main.variableexplorer is not None:
            self.main.variableexplorer.add_shellwidget(sw)
            sw.set_namespace_view_settings()
            sw.refresh_namespacebrowser()
            kc.stopped_channels.connect(lambda :
                self.main.variableexplorer.remove_shellwidget(id(sw)))

        if self.main.plots is not None:
            self.main.plots.add_shellwidget(sw)
            kc.stopped_channels.connect(lambda :
                self.main.plots.remove_shellwidget(id(sw)))
    

    def run_script(self, filename, wdir, args, debug, post_mortem,
                   current_client, clear_variables, console_namespace):
        """Run script in current or dedicated client"""
        norm = lambda text: remove_backslashes(to_text_string(text))

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
            # If spyder-kernels, use runfile
            if client.shellwidget.is_spyder_kernel():
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
                line += "\"%s\"" % to_text_string(filename)
                if args:
                    line += " %s" % norm(args)

            try:
                if client.shellwidget._executing:
                    # Don't allow multiple executions when there's
                    # still an execution taking place
                    # Fixes spyder-ide/spyder#7293.
                    pass
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
            self.switch_to_plugin()
        else:
            #XXX: not sure it can really happen
            QMessageBox.warning(self, _('Warning'),
                _("No IPython console is currently available to run <b>%s</b>."
                  "<br><br>Please open a new one and try again."
                  ) % osp.basename(filename), QMessageBox.Ok)


   
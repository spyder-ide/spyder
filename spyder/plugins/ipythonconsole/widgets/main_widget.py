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
from jupyter_core.paths import jupyter_config_dir, jupyter_runtime_dir
from qtpy.QtCore import Slot
from qtpy.QtGui import QColor
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QWidget)


# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.base import (
    get_conf_path, get_home_dir, running_under_pytest)
from spyder.plugins.ipythonconsole.widgets.client import ClientWidgetActions
from spyder.plugins.ipythonconsole.widgets import (
    ClientWidget, ConsoleRestartDialog, KernelConnectionDialog,
    PageControlWidget)
from spyder.py3compat import is_string, to_text_string, PY2, PY38_OR_MORE
from spyder.utils import programs, sourcecode
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
    ArrayInline = 'arrya_iniline_action'
    ArrayTable = 'arrya_table_action'


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
        self.testing = self.get_conf('testing')
        self.test_dir = self.get_conf('test_dir')
        self.test_no_stderr = self.get_conf('test_no_stderr')

        # Create temp dir on testing to save kernel errors
        if self.test_dir is not None:
            if not osp.isdir(osp.join(self.test_dir)):
                os.makedirs(osp.join(self.test_dir))

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


    #----- Public API ---
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
        if self.test_dir is not None:
            client.stderr_dir = self.test_dir

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


    #------ Private API -------------------------------------------------------
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

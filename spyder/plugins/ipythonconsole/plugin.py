# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console plugin based on QtConsole.
"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

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
from qtpy.QtGui import QColor
from qtpy.QtWebEngineWidgets import WEBENGINE
from qtpy.QtWidgets import (QActionGroup, QApplication, QHBoxLayout, QLabel,
                            QMenu, QMessageBox, QVBoxLayout, QWidget)
from traitlets.config.loader import Config, load_pyconfig_files
from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.plugins import Plugins, SpyderPluginWidget
from spyder.config.base import (_, get_conf_path, get_home_dir,
                                running_under_pytest)
from spyder.config.gui import get_font
from spyder.config.manager import CONF
from spyder.plugins.ipythonconsole.confpage import IPythonConsoleConfigPage
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
from spyder.plugins.ipythonconsole.utils.style import create_qss_style
from spyder.plugins.ipythonconsole.widgets import (
    ClientWidget, ConsoleRestartDialog, KernelConnectionDialog,
    PageControlWidget)
from spyder.py3compat import is_string, to_text_string, PY2, PY38_OR_MORE
from spyder.utils import encoding
from spyder.utils.icon_manager import ima
from spyder.utils import programs, sourcecode
from spyder.utils.misc import get_error_match, remove_backslashes
from spyder.utils.palette import QStylePalette
from spyder.utils.programs import get_temp_dir
from spyder.utils.qthelpers import MENU_SEPARATOR, add_actions, create_action
from spyder.widgets.browser import WebView
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.tabs import Tabs


MAIN_BG_COLOR = QStylePalette.COLOR_BACKGROUND_1

class IPythonConsole(SpyderPluginWidget):
    """
    IPython Console plugin

    This is a widget with tabs where each one is a ClientWidget
    """
    CONF_SECTION = 'ipython_console'
    CONFIGWIDGET_CLASS = IPythonConsoleConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # This is required for the new API
    NAME = 'ipython_console'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [Plugins.Editor, Plugins.History]

    # Signals
    focus_changed = Signal()
    edit_goto = Signal((str, int, str), (str, int, str, bool))
    sig_pdb_state = Signal(bool, dict)

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
    permission_error_msg = _("The directory {} is not writable and it is "
                             "required to create IPython consoles. Please "
                             "make it writable.")

    def __init__(self, parent, testing=False, test_dir=None,
                 test_no_stderr=False, css_path=None):
        """Ipython Console constructor."""
        SpyderPluginWidget.__init__(self, parent)

        self.tabwidget = None
        self.menu_actions = None
        self.master_clients = 0
        self.clients = []
        self.filenames = []
        self.mainwindow_close = False
        self.create_new_client_if_empty = True
        self.css_path = css_path
        self.run_cell_filename = None
        self.interrupt_action = None

        # Attrs for testing
        self.testing = testing
        self.test_dir = test_dir
        self.test_no_stderr = test_no_stderr

        # Create temp dir on testing to save kernel errors
        if self.test_dir is not None:
            if not osp.isdir(osp.join(test_dir)):
                os.makedirs(osp.join(test_dir))

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
        self.tabwidget.tabBar().sig_change_name.connect(
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
        self.infowidget = WebView(self)
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
            "margin: 0px 4px 4px 4px;"
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

    #------ SpyderPluginMixin API ---------------------------------------------
    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font()
        for client in self.clients:
            client.set_font(font)

    def _apply_gui_plugin_settings(self, options, client):
        """Apply GUI related configurations to a client."""
        # GUI options
        font_n = 'plugin_font'
        help_n = 'connect_to_oi'
        color_scheme_n = 'color_scheme_name'
        show_time_n = 'show_elapsed_time'
        reset_namespace_n = 'show_reset_namespace_warning'
        ask_before_restart_n = 'ask_before_restart'
        ask_before_closing_n = 'ask_before_closing'
        show_calltips_n = 'show_calltips'
        buffer_size_n = 'buffer_size'
        completion_type_n = 'completion_type'

        # Advanced GUI options
        in_prompt_n = 'in_prompt'
        out_prompt_n = 'out_prompt'

        # Client widgets
        control = client.get_control()
        sw = client.shellwidget
        if font_n in options:
            font_o = self.get_font()
            client.set_font(font_o)
        if help_n in options and control is not None:
            help_o = CONF.get('help', 'connect/ipython_console')
            control.set_help_enabled(help_o)
        if color_scheme_n in options:
            color_scheme_o = CONF.get('appearance', 'selected')
            client.set_color_scheme(color_scheme_o)
        if show_time_n in options:
            show_time_o = self.get_option(show_time_n)
            client.show_time_action.setChecked(show_time_o)
            client.set_elapsed_time_visible(show_time_o)
        if reset_namespace_n in options:
            reset_namespace_o = self.get_option(reset_namespace_n)
            client.reset_warning = reset_namespace_o
        if ask_before_restart_n in options:
            ask_before_restart_o = self.get_option(ask_before_restart_n)
            client.ask_before_restart = ask_before_restart_o
        if ask_before_closing_n in options:
            ask_before_closing_o = self.get_option(ask_before_closing_n)
            client.ask_before_closing = ask_before_closing_o
        if show_calltips_n in options:
            show_calltips_o = self.get_option(show_calltips_n)
            sw.set_show_calltips(show_calltips_o)
        if buffer_size_n in options:
            buffer_size_o = self.get_option(buffer_size_n)
            sw.set_buffer_size(buffer_size_o)
        if completion_type_n in options:
            completion_type_o = self.get_option(completion_type_n)
            completions = {0: "droplist", 1: "ncurses", 2: "plain"}
            sw._set_completion_widget(completions[completion_type_o])

        # Advanced GUI options
        if in_prompt_n in options:
            in_prompt_o = self.get_option(in_prompt_n)
            sw.set_in_prompt(in_prompt_o)
        if out_prompt_n in options:
            out_prompt_o = self.get_option(out_prompt_n)
            sw.set_out_prompt(out_prompt_o)

    def _apply_mpl_plugin_settings(self, options, client):
        """Apply Matplotlib related configurations to a client."""
        # Matplotlib options
        pylab_n = 'pylab'
        pylab_o = self.get_option(pylab_n)
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
                pylab_autoload_o = self.get_option(pylab_autoload_n)
                pylab_backend_o = self.get_option(pylab_backend_n)
                sw.set_matplotlib_backend(pylab_backend_o, pylab_autoload_o)
            if inline_backend_figure_format_n in options:
                inline_backend_figure_format_o = self.get_option(
                    inline_backend_figure_format_n)
                sw.set_mpl_inline_figure_format(inline_backend_figure_format_o)
            if inline_backend_resolution_n in options:
                inline_backend_resolution_o = self.get_option(
                    inline_backend_resolution_n)
                sw.set_mpl_inline_resolution(inline_backend_resolution_o)
            if (inline_backend_width_n in options or
                    inline_backend_height_n in options):
                inline_backend_width_o = self.get_option(
                    inline_backend_width_n)
                inline_backend_height_o = self.get_option(
                    inline_backend_height_n)
                sw.set_mpl_inline_figure_size(
                    inline_backend_width_o, inline_backend_height_o)
            if inline_backend_bbox_inches_n in options:
                inline_backend_bbox_inches_o = self.get_option(
                    inline_backend_bbox_inches_n)
                sw.set_mpl_inline_bbox_inches(inline_backend_bbox_inches_o)

    def _apply_advanced_plugin_settings(self, options, client):
        """Apply advanced configurations to a client."""
        # Advanced options
        greedy_completer_n = 'greedy_completer'
        jedi_completer_n = 'jedi_completer'
        autocall_n = 'autocall'

        # Client widget
        sw = client.shellwidget
        if greedy_completer_n in options:
            greedy_completer_o = self.get_option(greedy_completer_n)
            sw.set_greedy_completer(greedy_completer_o)
        if jedi_completer_n in options:
            jedi_completer_o = self.get_option(jedi_completer_n)
            sw.set_jedi_completer(jedi_completer_o)
        if autocall_n in options:
            autocall_o = self.get_option(autocall_n)
            sw.set_autocall(autocall_o)

    def _apply_pdb_plugin_settings(self, options, client):
        """Apply debugging configurations to a client."""
        # Debugging options
        pdb_ignore_lib_n = 'pdb_ignore_lib'
        pdb_execute_events_n = 'pdb_execute_events'
        pdb_use_exclamation_mark_n = 'pdb_use_exclamation_mark'

        # Client widget
        sw = client.shellwidget
        if pdb_ignore_lib_n in options:
            pdb_ignore_lib_o = self.get_option(pdb_ignore_lib_n)
            sw.set_pdb_ignore_lib(pdb_ignore_lib_o)
        if pdb_execute_events_n in options:
            pdb_execute_events_o = self.get_option(pdb_execute_events_n)
            sw.set_pdb_execute_events(pdb_execute_events_o)
        if pdb_use_exclamation_mark_n in options:
            pdb_use_exclamation_mark_o = self.get_option(
                pdb_use_exclamation_mark_n)
            sw.set_pdb_use_exclamation_mark(pdb_use_exclamation_mark_o)

    def apply_plugin_settings_to_client(
            self, options, client, disconnect_ready_signal=False):
        """Apply given plugin settings to the given client."""
        # GUI options
        self._apply_gui_plugin_settings(options, client)

        # Matplotlib options
        self._apply_mpl_plugin_settings(options, client)

        # Advanced options
        self._apply_advanced_plugin_settings(options, client)

        # Debugging options
        self._apply_pdb_plugin_settings(options, client)

        if disconnect_ready_signal:
            client.shellwidget.sig_pdb_prompt_ready.disconnect()

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings."""
        restart_needed = False
        restart_options = []

        # Startup options (needs a restart)
        run_lines_n = 'startup/run_lines'
        use_run_file_n = 'startup/use_run_file'
        run_file_n = 'startup/run_file'

        # Graphic options
        pylab_n = 'pylab'
        pylab_o = self.get_option(pylab_n)
        pylab_backend_n = 'pylab/backend'
        inline_backend = 0
        pylab_restart = False
        client_backend_not_inline = [False] * len(self.clients)
        if pylab_o and pylab_backend_n in options:
            pylab_backend_o = self.get_option(pylab_backend_n)
            client_backend_not_inline = [
                client.shellwidget.get_matplotlib_backend() != inline_backend
                for client in self.clients]
            current_client_backend_not_inline = (
                self.get_current_client().shellwidget.get_matplotlib_backend()
                != inline_backend)
            pylab_restart = (
                any(client_backend_not_inline) and
                pylab_backend_o != inline_backend)

        # Advanced options (needs a restart)
        symbolic_math_n = 'symbolic_math'
        hide_cmd_windows_n = 'hide_cmd_windows'

        restart_options += [run_lines_n, use_run_file_n, run_file_n,
                            symbolic_math_n, hide_cmd_windows_n]

        restart_needed = any([restart_option in options
                              for restart_option in restart_options])

        if (restart_needed or pylab_restart) and not running_under_pytest():
            restart_dialog = ConsoleRestartDialog(self)
            restart_dialog.exec_()
            (restart_all, restart_current,
             no_restart) = restart_dialog.get_action_value()
        else:
            restart_all = False
            restart_current = False
            no_restart = True

        # Apply settings
        for idx, client in enumerate(self.clients):
            restart = ((pylab_restart and client_backend_not_inline[idx]) or
                       restart_needed)
            if not (restart and restart_all) or no_restart:
                sw = client.shellwidget
                if sw.is_debugging() and sw._executing:
                    # Apply settings when the next Pdb prompt is available
                    sw.sig_pdb_prompt_ready.connect(
                        lambda o=options, c=client:
                            self.apply_plugin_settings_to_client(
                                o, c, disconnect_ready_signal=True)
                        )
                else:
                    self.apply_plugin_settings_to_client(options, client)
            elif restart and restart_all:
                client.ask_before_restart = False
                client.restart_kernel()

        if (((pylab_restart and current_client_backend_not_inline)
             or restart_needed) and restart_current):
            current_client = self.get_current_client()
            current_client.ask_before_restart = False
            current_client.restart_kernel()

    def toggle_view(self, checked):
        """Toggle view"""
        if checked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            # Start a client in case there are none shown
            if not self.clients:
                if self.main.is_setting_up:
                    self.create_new_client(give_focus=False)
                else:
                    self.create_new_client(give_focus=True)
        else:
            self.dockwidget.hide()

    #------ SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('IPython console')

    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('ipython_console')

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        client = self.tabwidget.currentWidget()
        if client is not None:
            return client.get_control()

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.mainwindow_close = True
        for client in self.clients:
            client.shutdown()
            client.remove_stderr_file()
            client.dialog_manager.close_all()
            client.close()
        return True

    def refresh_plugin(self):
        """Refresh tabwidget"""
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

            if isinstance(control, PageControlWidget):
                self.pager_label.show()
            else:
                self.pager_label.hide()

            # Create corner widgets
            buttons = [[b, -7] for b in client.get_toolbar_buttons()]
            buttons = sum(buttons, [])[:-1]
            widgets = [client.create_time_label()] + buttons
        else:
            control = None
            widgets = []
        self.find_widget.set_editor(control)
        self.tabwidget.set_corner_widgets({Qt.TopRightCorner: widgets})

        if client:
            sw = client.shellwidget
            self.main.variableexplorer.set_shellwidget(sw)
            self.sig_pdb_state.emit(
                sw.is_waiting_pdb_input(), sw.get_pdb_last_step())
            self.sig_shellwidget_changed.emit(sw)

        self.update_tabs_text()
        self.sig_update_plugin_title.emit()

    def get_plugin_actions(self):
        """Return a list of actions related to plugin."""
        create_client_action = create_action(
                                   self,
                                   _("New console (default settings)"),
                                   icon=ima.icon('ipython_console'),
                                   triggered=self.create_new_client,
                                   context=Qt.WidgetWithChildrenShortcut)
        self.register_shortcut(create_client_action, context="ipython_console",
                               name="New tab")

        create_pylab_action = create_action(
                                   self,
                                   _("New Pylab console (data plotting)"),
                                   icon=ima.icon('ipython_console'),
                                   triggered=self.create_pylab_client,
                                   context=Qt.WidgetWithChildrenShortcut)

        create_sympy_action = create_action(
                                   self,
                                   _("New SymPy console (symbolic math)"),
                                   icon=ima.icon('ipython_console'),
                                   triggered=self.create_sympy_client,
                                   context=Qt.WidgetWithChildrenShortcut)

        create_cython_action = create_action(
                                   self,
                                   _("New Cython console (Python with "
                                     "C extensions)"),
                                   icon=ima.icon('ipython_console'),
                                   triggered=self.create_cython_client,
                                   context=Qt.WidgetWithChildrenShortcut)
        special_console_action_group = QActionGroup(self)
        special_console_actions = (create_pylab_action, create_sympy_action,
                                   create_cython_action)
        add_actions(special_console_action_group, special_console_actions)
        special_console_menu = QMenu(_("New special console"), self)
        add_actions(special_console_menu, special_console_actions)

        restart_action = create_action(self, _("Restart kernel"),
                                       icon=ima.icon('restart'),
                                       triggered=self.restart_kernel,
                                       context=Qt.WidgetWithChildrenShortcut)

        reset_action = create_action(self, _("Remove all variables"),
                                     icon=ima.icon('editdelete'),
                                     triggered=self.reset_kernel,
                                     context=Qt.WidgetWithChildrenShortcut)
        self.register_shortcut(reset_action, context="ipython_console",
                               name="Reset namespace")

        if self.interrupt_action is None:
            self.interrupt_action = create_action(
                self, _("Interrupt kernel"),
                icon=ima.icon('stop'),
                triggered=self.interrupt_kernel,
                context=Qt.WidgetWithChildrenShortcut)

        self.register_shortcut(restart_action, context="ipython_console",
                               name="Restart kernel")

        connect_to_kernel_action = create_action(self,
               _("Connect to an existing kernel"), None, None,
               _("Open a new IPython console connected to an existing kernel"),
               triggered=self.create_client_for_kernel)

        rename_tab_action = create_action(self, _("Rename tab"),
                                       icon=ima.icon('rename'),
                                       triggered=self.tab_name_editor)

        # Add the action to the 'Consoles' menu on the main window
        main_consoles_menu = self.main.consoles_menu_actions
        main_consoles_menu.insert(0, create_client_action)
        main_consoles_menu += [special_console_menu, connect_to_kernel_action,
                               MENU_SEPARATOR,
                               self.interrupt_action, restart_action,
                               reset_action]

        # Plugin actions
        self.menu_actions = [create_client_action, special_console_menu,
                             connect_to_kernel_action,
                             MENU_SEPARATOR,
                             self.interrupt_action,
                             restart_action, reset_action, rename_tab_action]

        self.update_execution_state_kernel()

        # Check for a current client. Since it manages more actions.
        client = self.get_current_client()
        if client:
            return client.get_options_menu()
        return self.menu_actions

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.add_dockwidget()

        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.edit_goto.connect(self.main.editor.load)
        self.edit_goto[str, int, str, bool].connect(
                         lambda fname, lineno, word, processevents:
                         self.main.editor.load(fname, lineno, word,
                                               processevents=processevents))
        self.main.editor.breakpoints_saved.connect(self.set_spyder_breakpoints)
        self.main.editor.run_in_current_ipyclient.connect(self.run_script)
        self.main.editor.run_cell_in_ipyclient.connect(self.run_cell)
        self.main.editor.debug_cell_in_ipyclient.connect(self.debug_cell)
        self.tabwidget.currentChanged.connect(self.update_working_directory)
        self.tabwidget.currentChanged.connect(self.check_pdb_state)
        self._remove_old_stderr_files()

        # Update kernels if python path is changed
        self.main.sig_pythonpath_changed.connect(self.update_path)

    #------ Public API (for clients) ------------------------------------------
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

    def run_cell(self, code, cell_name, filename, run_cell_copy,
                 function='runcell'):
        """Run cell in current or dedicated client."""

        def norm(text):
            return remove_backslashes(to_text_string(text))

        self.run_cell_filename = filename

        # Select client to execute code on it
        client = self.get_client_for_file(filename)
        if client is None:
            client = self.get_current_client()

        if client is not None:
            # Internal kernels, use runcell
            if client.get_kernel() is not None and not run_cell_copy:
                line = (to_text_string(
                        "{}({}, '{}')").format(
                                to_text_string(function),
                                repr(cell_name),
                                norm(filename).replace("'", r"\'")))

            # External kernels and run_cell_copy, just execute the code
            else:
                line = code.strip()

            try:
                self.execute_code(line)
            except AttributeError:
                pass
            self._visibility_changed(True)
            self.raise_()
        else:
            # XXX: not sure it can really happen
            QMessageBox.warning(self, _('Warning'),
                                _("No IPython console is currently available "
                                  "to run <b>{}</b>.<br><br>Please open a new "
                                  "one and try again."
                                  ).format(osp.basename(filename)),
                                QMessageBox.Ok)

    def debug_cell(self, code, cell_name, filename, run_cell_copy):
        """Debug current cell."""
        self.run_cell(code, cell_name, filename, run_cell_copy, 'debugcell')

    def set_current_client_working_directory(self, directory):
        """Set current client working directory."""
        shellwidget = self.get_current_shellwidget()
        if shellwidget is not None:
            shellwidget.set_cwd(directory)

    def set_working_directory(self, dirname):
        """Set current working directory.
        In the workingdirectory and explorer plugins.
        """
        if osp.isdir(dirname):
            self.sig_current_directory_changed.emit(dirname)

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
                self.main.get_spyder_pythonpath()
                shell.update_syspath(path_dict, new_path_dict)

    def execute_code(self, lines, current_client=True, clear_variables=False):
        """Execute code instructions."""
        sw = self.get_current_shellwidget()
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
                sw.execute(to_text_string(lines))
            except AttributeError:
                pass
            self.activateWindow()
            self.get_current_client().get_control().setFocus()

    def pdb_execute_command(self, command):
        """
        Send command to the pdb kernel if possible.
        """

        sw = self.get_current_shellwidget()
        if sw is not None:
            # Needed to handle an error when kernel_client is None.
            # See spyder-ide/spyder#7578.
            try:
                sw.pdb_execute_command(command)
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
        show_elapsed_time = self.get_option('show_elapsed_time')
        reset_warning = self.get_option('show_reset_namespace_warning')
        ask_before_restart = self.get_option('ask_before_restart')
        ask_before_closing = self.get_option('ask_before_closing')
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
        if not CONF.get('main_interpreter', 'default'):
            pyexec = CONF.get('main_interpreter', 'executable')
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
                      "<tt>conda install spyder-kernels</tt>"
                      "<br><br>or<br><br>"
                      "<tt>pip install spyder-kernels</tt>")
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
        """Connect a client to its kernel"""
        connection_file = client.connection_file
        stderr_handle = None if self.test_no_stderr else client.stderr_handle
        km, kc = self.create_kernel_manager_and_kernel_client(
                     connection_file,
                     stderr_handle,
                     is_cython=is_cython,
                     is_pylab=is_pylab,
                     is_sympy=is_sympy)

        # An error occurred if this is True
        if is_string(km) and kc is None:
            client.shellwidget.kernel_manager = None
            client.show_kernel_error(km)
            return

        # This avoids a recurrent, spurious NameError when running our
        # tests in our CIs
        if not self.testing:
            kc.started_channels.connect(
                lambda c=client: self.process_started(c))
            kc.stopped_channels.connect(
                lambda c=client: self.process_finished(c))
        kc.start_channels(shell=True, iopub=True)

        shellwidget = client.shellwidget
        shellwidget.set_kernel_client_and_manager(kc, km)
        shellwidget.sig_exception_occurred.connect(
            self.main.console.handle_exception)

    @Slot(object, object)
    def edit_file(self, filename, line):
        """Handle %edit magic petitions."""
        if encoding.is_text_file(filename):
            # The default line number sent by ipykernel is always the last
            # one, but we prefer to use the first.
            self.edit_goto.emit(filename, 1, '')

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
        except:
            cfg = Config()

        # ---- Spyder config ----
        spy_cfg = Config()

        # Make the pager widget a rich one (i.e a QTextEdit)
        spy_cfg.JupyterWidget.kind = 'rich'

        # Gui completion widget
        completion_type_o = self.get_option('completion_type')
        completions = {0: "droplist", 1: "ncurses", 2: "plain"}
        spy_cfg.JupyterWidget.gui_completion = completions[completion_type_o]

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
        color_scheme = CONF.get('appearance', 'selected')
        style_sheet = create_qss_style(color_scheme)[0]
        spy_cfg.JupyterWidget.style_sheet = style_sheet
        spy_cfg.JupyterWidget.syntax_style = color_scheme

        # Merge QtConsole and Spyder configs. Spyder prefs will have
        # prevalence over QtConsole ones
        cfg._merge(spy_cfg)
        return cfg

    def interpreter_versions(self):
        """Python and IPython versions used by clients"""
        if CONF.get('main_interpreter', 'default'):
            from IPython.core import release
            versions = dict(
                python_version = sys.version,
                ipython_version = release.version
            )
        else:
            import subprocess
            versions = {}
            pyexec = CONF.get('main_interpreter', 'executable')
            py_cmd = u'%s -c "import sys; print(sys.version)"' % pyexec
            ipy_cmd = (
                u'%s -c "import IPython.core.release as r; print(r.version)"'
                % pyexec
            )
            for cmd in [py_cmd, ipy_cmd]:
                if PY2:
                    # We need to encode as run_shell_command will treat the
                    # string as str
                    cmd = cmd.encode('utf-8')

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

    def register_client(self, client, give_focus=True):
        """Register new client"""
        client.configure_shellwidget(give_focus=give_focus)

        # Local vars
        shellwidget = client.shellwidget
        control = shellwidget._control

        # Create new clients with Ctrl+T shortcut
        shellwidget.new_client.connect(self.create_new_client)

        # For tracebacks
        control.go_to_error.connect(self.go_to_error)

        # For help requests
        control.sig_help_requested.connect(self.sig_help_requested)

        shellwidget.sig_pdb_step.connect(
                              lambda fname, lineno, shellwidget=shellwidget:
                              self.pdb_has_stopped(fname, lineno, shellwidget))
        shellwidget.sig_pdb_state.connect(self.sig_pdb_state)

        # To handle %edit magic petitions
        shellwidget.custom_edit_requested.connect(self.edit_file)

        # Set shell cwd according to preferences
        cwd_path = ''
        if CONF.get('workingdir', 'console/use_project_or_home_directory'):
            cwd_path = get_home_dir()
            if (self.main.projects is not None and
                    self.main.projects.get_active_project() is not None):
                cwd_path = self.main.projects.get_active_project_path()
        elif CONF.get('workingdir', 'startup/use_fixed_directory'):
            cwd_path = CONF.get('workingdir', 'startup/fixed_directory',
                                default=get_home_dir())
        elif CONF.get('workingdir', 'console/use_fixed_directory'):
            cwd_path = CONF.get('workingdir', 'console/fixed_directory')

        if osp.isdir(cwd_path) and self.main is not None:
            shellwidget.set_cwd(cwd_path)
            if give_focus:
                # Syncronice cwd with explorer and cwd widget
                shellwidget.update_cwd()

        # Connect client to our history log
        if self.main.historylog is not None:
            self.main.historylog.add_history(client.history_filename)
            client.append_to_history.connect(
                self.main.historylog.append_to_history)

        # Set font for client
        client.set_font(self.get_font())

        # Set editor for the find widget
        self.find_widget.set_editor(control)

        # Connect to working directory
        shellwidget.sig_change_cwd.connect(self.set_working_directory)

    def close_client(self, index=None, client=None, force=False):
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

        # Needed to handle a RuntimeError. See spyder-ide/spyder#5568.
        try:
            # Close client
            client.stop_button_click_handler()
        except RuntimeError:
            pass

        # Disconnect timer needed to update elapsed time
        try:
            client.timer.timeout.disconnect(client.show_time)
        except (RuntimeError, TypeError):
            pass

        # Check if related clients or kernels are opened
        # and eventually ask before closing them
        if not self.mainwindow_close and not force:
            close_all = True
            if client.ask_before_closing:
                close = QMessageBox.question(self, self.get_plugin_title(),
                                       _("Do you want to close this console?"),
                                       QMessageBox.Yes | QMessageBox.No)
                if close == QMessageBox.No:
                    return
            if len(self.get_related_clients(client)) > 0:
                close_all = QMessageBox.question(self, self.get_plugin_title(),
                         _("Do you want to close all other consoles connected "
                           "to the same kernel as this one?"),
                           QMessageBox.Yes | QMessageBox.No)

            client.shutdown()
            if close_all == QMessageBox.Yes:
                self.close_related_clients(client)

        # if there aren't related clients we can remove stderr_file
        related_clients = self.get_related_clients(client)
        if len(related_clients) == 0:
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

        self.sig_update_plugin_title.emit()

    def get_client_index_from_id(self, client_id):
        """Return client index from id"""
        for index, client in enumerate(self.clients):
            if id(client) == client_id:
                return index

    def get_related_clients(self, client):
        """
        Get all other clients that are connected to the same kernel as `client`
        """
        related_clients = []
        for cl in self.get_clients():
            if cl.connection_file == client.connection_file and \
              cl is not client:
                related_clients.append(cl)
        return related_clients

    def close_related_clients(self, client):
        """Close all clients related to *client*, except itself"""
        related_clients = self.get_related_clients(client)
        for cl in related_clients:
            self.close_client(client=cl, force=True)

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
            try:
                client.shutdown()
            except Exception as e:
                QMessageBox.warning(self, _('Warning'),
                    _("It was not possible to restart the IPython console "
                      "when switching to this project. The error was<br><br>"
                      "<tt>{0}</tt>").format(e), QMessageBox.Ok)
            self.close_client(client=client, force=True)
        self.create_new_client(give_focus=False)
        self.create_new_client_if_empty = True

    def pdb_has_stopped(self, fname, lineno, shellwidget):
        """Python debugger has just stopped at frame (fname, lineno)"""
        # This is a unique form of the edit_goto signal that is intended to
        # prevent keyboard input from accidentally entering the editor
        # during repeated, rapid entry of debugging commands.
        self.edit_goto[str, int, str, bool].emit(fname, lineno, '', False)
        self.activateWindow()
        shellwidget._control.setFocus()

    def set_spyder_breakpoints(self):
        """Set Spyder breakpoints into all clients"""
        for cl in self.clients:
            cl.shellwidget.set_spyder_breakpoints()

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
                client.create_time_label()
                client.t0 = cl.t0
                client.timer.timeout.connect(client.show_time)
                client.timer.start(1000)
                break

    def set_infowidget_font(self):
        """Set font for infowidget"""
        font = get_font(option='rich_font')
        self.infowidget.set_font(font)

    #------ Public API (for kernels) ------------------------------------------
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
        CONF.set('main', 'spyder_pythonpath',
                 self.main.get_spyder_pythonpath())
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

    #------ Public API (for tabs) ---------------------------------------------
    def add_tab(self, widget, name, filename=''):
        """Add tab"""
        self.clients.append(widget)
        index = self.tabwidget.addTab(widget, name)
        self.filenames.insert(index, filename)
        self.tabwidget.setCurrentIndex(index)
        if self.dockwidget and not self.main.is_setting_up:
            self.switch_to_plugin()
        self.activateWindow()
        widget.get_control().setFocus()
        self.update_tabs_text()

    def move_tab(self, index_from, index_to):
        """
        Move tab (tabs themselves have already been moved by the tabwidget)
        """
        filename = self.filenames.pop(index_from)
        client = self.clients.pop(index_from)
        self.filenames.insert(index_to, filename)
        self.clients.insert(index_to, client)
        self.update_tabs_text()
        self.sig_update_plugin_title.emit()

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
        """Rename client's tab"""
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
        if client.allow_rename and not u'/' in given_name and not repeated:
            self.rename_client_tab(client, given_name)
        else:
            self.rename_client_tab(client, None)

        # Rename related clients
        if client.allow_rename and not u'/' in given_name and not repeated:
            for cl in self.get_related_clients(client):
                self.rename_client_tab(cl, given_name)

    def tab_name_editor(self):
        """Trigger the tab name editor."""
        index = self.tabwidget.currentIndex()
        self.tabwidget.tabBar().tab_name_editor.edit_tab(index)

    #------ Public API (for help) ---------------------------------------------
    def go_to_error(self, text):
        """Go to error if relevant"""
        match = get_error_match(to_text_string(text))
        if match:
            fname, lnb = match.groups()
            if ("<ipython-input-" in fname and
                    self.run_cell_filename is not None):
                fname = self.run_cell_filename
            # This is needed to fix issue spyder-ide/spyder#9217.
            try:
                self.edit_goto.emit(osp.abspath(fname), int(lnb), '')
            except ValueError:
                pass

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

    def process_started(self, client):
        if self.main.variableexplorer is not None:
            self.main.variableexplorer.add_shellwidget(client.shellwidget)

        self.sig_shellwidget_process_started.emit(client.shellwidget)

    def process_finished(self, client):
        if self.main.variableexplorer is not None:
            self.main.variableexplorer.remove_shellwidget(client.shellwidget)

        self.sig_shellwidget_process_finished.emit(client.shellwidget)

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
            self.main.console.handle_exception)

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

    def print_debug_file_msg(self):
        """Print message in the current console when a file can't be closed."""
        debug_msg = _('<br><hr>'
                      '\nThe current file cannot be closed because it is '
                      'in debug mode. \n'
                      '<hr><br>')
        self.get_current_client().shellwidget._append_html(
                    debug_msg, before_prompt=True)

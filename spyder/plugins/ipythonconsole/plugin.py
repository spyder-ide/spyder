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
# import sys
# import traceback
# import uuid

# Third party imports
# from jupyter_client.connect import find_connection_file
# from jupyter_core.paths import jupyter_config_dir, jupyter_runtime_dir
# from qtconsole.client import QtKernelClient
from qtpy.QtCore import Signal  # Qt, Slot
# from qtpy.QtGui import QColor
# from qtpy.QtWebEngineWidgets import WEBENGINE
# from qtpy.QtWidgets import (QActionGroup, QApplication, QHBoxLayout, QLabel,
#                             QMenu, QMessageBox, QVBoxLayout, QWidget)
# from traitlets.config.loader import Config, load_pyconfig_files
# from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
# from spyder.api.widgets.menus import SpyderMenu
# from spyder.config.base import (_, get_conf_path, get_home_dir,
#                                 running_under_pytest)
# from spyder.config.gui import get_font
# from spyder.config.manager import CONF
from spyder.plugins.ipythonconsole.confpage import IPythonConsoleConfigPage
# from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
# from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
# from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
# from spyder.plugins.ipythonconsole.utils.style import create_qss_style
# from spyder.plugins.ipythonconsole.widgets import (
#     ClientWidget, ConsoleRestartDialog, KernelConnectionDialog,
#     PageControlWidget)
from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget)
from spyder.plugins.mainmenu.api import (
    ApplicationMenus, ConsolesMenuSections, HelpMenuSections)
# from spyder.py3compat import is_string, to_text_string, PY2, PY38_OR_MORE
# from spyder.utils import encoding
# from spyder.utils.icon_manager import ima
# from spyder.utils import programs, sourcecode
# from spyder.utils.misc import get_error_match, remove_backslashes
# from spyder.utils.palette import QStylePalette
from spyder.utils.programs import get_temp_dir
# from spyder.utils.qthelpers import MENU_SEPARATOR, add_actions, create_action
# from spyder.widgets.browser import FrameWebView
# from spyder.widgets.findreplace import FindReplace
# from spyder.widgets.tabs import Tabs


# MAIN_BG_COLOR = QStylePalette.COLOR_BACKGROUND_1

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
    sig_focus_changed = Signal()
    sig_history_requested = Signal(str)
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

    # Remove when this plugin is migrated
    # sig_exception_occurred = Signal(dict)

    # Error messages
    # permission_error_msg = _("The directory {} is not writable and it is "
    #                          "required to create IPython consoles. Please "
    #                          "make it writable.")

    # def __init__(self, parent, testing=False, test_dir=None,
    #              test_no_stderr=False):
    #     """Ipython Console constructor."""
    #     SpyderPluginWidget.__init__(self, parent)

    #     self.tabwidget = None
    #     self.menu_actions = None
    #     self.master_clients = 0
    #     self.clients = []
    #     self.filenames = []
    #     self.mainwindow_close = False
    #     self.create_new_client_if_empty = True
    #     self.css_path = CONF.get('appearance', 'css_path')
    #     self.run_cell_filename = None
    #     self.interrupt_action = None

    #     # Attrs for testing
    #     self.testing = testing
    #     self.test_dir = test_dir
    #     self.test_no_stderr = test_no_stderr

    #     # Create temp dir on testing to save kernel errors
    #     if self.test_dir is not None:
    #         if not osp.isdir(osp.join(test_dir)):
    #             os.makedirs(osp.join(test_dir))

    #     layout = QVBoxLayout()
    #     layout.setSpacing(0)
    #     self.tabwidget = Tabs(self, menu=self._options_menu,
    #                           actions=self.menu_actions,
    #                           rename_tabs=True,
    #                           split_char='/', split_index=0)
    #     if hasattr(self.tabwidget, 'setDocumentMode')\
    #        and not sys.platform == 'darwin':
    #         # Don't set document mode to true on OSX because it generates
    #         # a crash when the console is detached from the main window
    #         # Fixes spyder-ide/spyder#561.
    #         self.tabwidget.setDocumentMode(True)
    #     self.tabwidget.currentChanged.connect(self.refresh_plugin)
    #     self.tabwidget.tabBar().tabMoved.connect(self.move_tab)
    #     self.tabwidget.tabBar().sig_name_changed.connect(
    #         self.rename_tabs_after_change)

    #     self.tabwidget.set_close_function(self.close_client)

    #     self.main.editor.sig_file_debug_message_requested.connect(
    #         self.print_debug_file_msg)

    #     if sys.platform == 'darwin':
    #         tab_container = QWidget()
    #         tab_container.setObjectName('tab-container')
    #         tab_layout = QHBoxLayout(tab_container)
    #         tab_layout.setContentsMargins(0, 0, 0, 0)
    #         tab_layout.addWidget(self.tabwidget)
    #         layout.addWidget(tab_container)
    #     else:
    #         layout.addWidget(self.tabwidget)

    #     # Info widget
    #     self.infowidget = FrameWebView(self)
    #     if WEBENGINE:
    #         self.infowidget.page().setBackgroundColor(QColor(MAIN_BG_COLOR))
    #     else:
    #         self.infowidget.setStyleSheet(
    #             "background:{}".format(MAIN_BG_COLOR))
    #     self.set_infowidget_font()
    #     layout.addWidget(self.infowidget)

    #     # Label to inform users how to get out of the pager
    #     self.pager_label = QLabel(_("Press <b>Q</b> to exit pager"), self)
    #     self.pager_label.setStyleSheet(
    #         f"background-color: {QStylePalette.COLOR_ACCENT_2};"
    #         f"color: {QStylePalette.COLOR_TEXT_1};"
    #         "margin: 0px 1px 4px 1px;"
    #         "padding: 5px;"
    #         "qproperty-alignment: AlignCenter;"
    #     )
    #     self.pager_label.hide()
    #     layout.addWidget(self.pager_label)

    #     # Find/replace widget
    #     self.find_widget = FindReplace(self)
    #     self.find_widget.hide()
    #     self.register_widget_shortcuts(self.find_widget)
    #     layout.addWidget(self.find_widget)

    #     self.setLayout(layout)

    #     # Accepting drops
    #     self.setAcceptDrops(True)

    #     # Needed to start Spyder in Windows with Python 3.8
    #     # See spyder-ide/spyder#11880
    #     self._init_asyncio_patch()

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('IPython console')

    def get_description(self):
        return _('IPython console')

    def get_icon(self):
        return self.create_icon('ipython_console')

    def register(self):
        # TODO: Check main_widget signals connection
        widget = self.get_widget()
        widget.sig_history_requested.connect(self.sig_history_requested)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_pdb_state_changed.connect(self.sig_pdb_state_changed)
        widget.sig_shellwidget_created.connect(self.sig_shellwidget_created)
        widget.sig_shellwidget_deleted.connect(self.sig_shellwidget_deleted)
        widget.sig_shellwidget_changed.connect(self.sig_shellwidget_changed)
        widget.sig_render_plain_text_requested.connect(
            self.sig_render_plain_text_requested)
        widget.sig_render_rich_text_requested.connect(
            self.sig_render_rich_text_requested)
        widget.sig_help_requested.connect(self.sig_help_requested)
        widget.sig_current_directory_changed.connect(
            self.sig_current_directory_changed)
        # TODO: Add action to mainmenu
        # Add actions to the 'Consoles' menu on the main window
        console_menu = self.main.mainmenu.get_application_menu("consoles_menu")
        console_menu.aboutToShow.connect(
            widget.update_execution_state_kernel)
        new_consoles_actions = [
            widget.create_client_action, widget.special_console_menu,
            widget.connect_to_kernel_action]
        restart_connect_consoles_actions = [
            widget.interrupt_action,
            widget.restart_action,
            widget.reset_action]
        for console_new_action in new_consoles_actions:
            self.main.mainmenu.add_item_to_application_menu(
                console_new_action,
                menu_id=ApplicationMenus.Consoles,
                section=ConsolesMenuSections.New)
        for console_restart_connect_action in restart_connect_consoles_actions:
            self.main.mainmenu.add_item_to_application_menu(
                console_restart_connect_action,
                menu_id=ApplicationMenus.Consoles,
                section=ConsolesMenuSections.Restart)

        # IPython documentation
        self.main.mainmenu.add_item_to_application_menu(
            self.get_widget().ipython_menu,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.ExternalDocumentation,
            before_section=HelpMenuSections.About)

        # TODO: Check Editor connections
        if self.main.editor:
            self.sig_edit_goto_requested.connect(self.main.editor.load)
            self.sig_edit_goto_requested[str, int, str, bool].connect(
                             lambda fname, lineno, word, processevents:
                             self.main.editor.load(
                                 fname, lineno, word,
                                 processevents=processevents))
            self.main.editor.breakpoints_saved.connect(
                self.set_spyder_breakpoints)
            self.main.editor.run_in_current_ipyclient.connect(self.run_script)
            self.main.editor.run_cell_in_ipyclient.connect(self.run_cell)
            self.main.editor.debug_cell_in_ipyclient.connect(self.debug_cell)
            # Connect Editor debug action with Console
            self.sig_pdb_state_changed.connect(
                self.main.editor.update_pdb_state)
            self.main.editor.exec_in_extconsole.connect(
                self.execute_code_and_focus_editor)
        # self.tabwidget.currentChanged.connect(self.update_working_directory)
        # self.tabwidget.currentChanged.connect(self.check_pdb_state)

        # Update kernels if python path is changed
        self.main.sig_pythonpath_changed.connect(self.update_path)

        self.sig_focus_changed.connect(self.main.plugin_focus_changed)
        self._remove_old_stderr_files()

        # Show history file if no console is visible
        # if not self.get_widget()._isvisible and self.main.historylog:
        #     self.main.historylog.add_history(get_conf_path('history.py'))

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_font()
        # for client in self.clients:
        #     client.set_font(font)
        rich_font = self.get_font(rich_text=True)
        self.get_widget().update_font(font, rich_font)

    def on_close(self, cancelable=False):
        self.get_widget().mainwindow_close = True
        self.get_widget().close_clients()
        return True

    def on_mainwindow_visible(self):
        self.get_widget().create_new_client(give_focus=False)

    # ----- SpyderPluginMixin API ---------------------------------------------

    # def _apply_gui_plugin_settings(self, options, client):
    #     """Apply GUI related configurations to a client."""
    #     # GUI options
    #     font_n = 'plugin_font'
    #     help_n = 'connect_to_oi'
    #     color_scheme_n = 'color_scheme_name'
    #     show_time_n = 'show_elapsed_time'
    #     reset_namespace_n = 'show_reset_namespace_warning'
    #     ask_before_restart_n = 'ask_before_restart'
    #     ask_before_closing_n = 'ask_before_closing'
    #     show_calltips_n = 'show_calltips'
    #     buffer_size_n = 'buffer_size'
    #     completion_type_n = 'completion_type'

    #     # Advanced GUI options
    #     in_prompt_n = 'in_prompt'
    #     out_prompt_n = 'out_prompt'

    #     # Client widgets
    #     control = client.get_control()
    #     sw = client.shellwidget
    #     if font_n in options:
    #         font_o = self.get_font()
    #         client.set_font(font_o)
    #     if help_n in options and control is not None:
    #         help_o = CONF.get('help', 'connect/ipython_console')
    #         control.set_help_enabled(help_o)
    #     if color_scheme_n in options:
    #         color_scheme_o = CONF.get('appearance', 'selected')
    #         client.set_color_scheme(color_scheme_o)
    #     if show_time_n in options:
    #         show_time_o = self.get_option(show_time_n)
    #         client.show_time_action.setChecked(show_time_o)
    #         client.set_elapsed_time_visible(show_time_o)
    #     if reset_namespace_n in options:
    #         reset_namespace_o = self.get_option(reset_namespace_n)
    #         client.reset_warning = reset_namespace_o
    #     if ask_before_restart_n in options:
    #         ask_before_restart_o = self.get_option(ask_before_restart_n)
    #         client.ask_before_restart = ask_before_restart_o
    #     if ask_before_closing_n in options:
    #         ask_before_closing_o = self.get_option(ask_before_closing_n)
    #         client.ask_before_closing = ask_before_closing_o
    #     if show_calltips_n in options:
    #         show_calltips_o = self.get_option(show_calltips_n)
    #         sw.set_show_calltips(show_calltips_o)
    #     if buffer_size_n in options:
    #         buffer_size_o = self.get_option(buffer_size_n)
    #         sw.set_buffer_size(buffer_size_o)
    #     if completion_type_n in options:
    #         completion_type_o = self.get_option(completion_type_n)
    #         completions = {0: "droplist", 1: "ncurses", 2: "plain"}
    #         sw._set_completion_widget(completions[completion_type_o])

    #     # Advanced GUI options
    #     if in_prompt_n in options:
    #         in_prompt_o = self.get_option(in_prompt_n)
    #         sw.set_in_prompt(in_prompt_o)
    #     if out_prompt_n in options:
    #         out_prompt_o = self.get_option(out_prompt_n)
    #         sw.set_out_prompt(out_prompt_o)

    # def _apply_mpl_plugin_settings(self, options, client):
    #     """Apply Matplotlib related configurations to a client."""
    #     # Matplotlib options
    #     pylab_n = 'pylab'
    #     pylab_o = self.get_option(pylab_n)
    #     pylab_autoload_n = 'pylab/autoload'
    #     pylab_backend_n = 'pylab/backend'
    #     inline_backend_figure_format_n = 'pylab/inline/figure_format'
    #     inline_backend_resolution_n = 'pylab/inline/resolution'
    #     inline_backend_width_n = 'pylab/inline/width'
    #     inline_backend_height_n = 'pylab/inline/height'
    #     inline_backend_bbox_inches_n = 'pylab/inline/bbox_inches'

    #     # Client widgets
    #     sw = client.shellwidget
    #     if pylab_o:
    #         if pylab_backend_n in options or pylab_autoload_n in options:
    #             pylab_autoload_o = self.get_option(pylab_autoload_n)
    #             pylab_backend_o = self.get_option(pylab_backend_n)
    #             sw.set_matplotlib_backend(pylab_backend_o, pylab_autoload_o)
    #         if inline_backend_figure_format_n in options:
    #             inline_backend_figure_format_o = self.get_option(
    #                 inline_backend_figure_format_n)
    #             sw.set_mpl_inline_figure_format(inline_backend_figure_format_o)
    #         if inline_backend_resolution_n in options:
    #             inline_backend_resolution_o = self.get_option(
    #                 inline_backend_resolution_n)
    #             sw.set_mpl_inline_resolution(inline_backend_resolution_o)
    #         if (inline_backend_width_n in options or
    #                 inline_backend_height_n in options):
    #             inline_backend_width_o = self.get_option(
    #                 inline_backend_width_n)
    #             inline_backend_height_o = self.get_option(
    #                 inline_backend_height_n)
    #             sw.set_mpl_inline_figure_size(
    #                 inline_backend_width_o, inline_backend_height_o)
    #         if inline_backend_bbox_inches_n in options:
    #             inline_backend_bbox_inches_o = self.get_option(
    #                 inline_backend_bbox_inches_n)
    #             sw.set_mpl_inline_bbox_inches(inline_backend_bbox_inches_o)

    # def _apply_advanced_plugin_settings(self, options, client):
    #     """Apply advanced configurations to a client."""
    #     # Advanced options
    #     greedy_completer_n = 'greedy_completer'
    #     jedi_completer_n = 'jedi_completer'
    #     autocall_n = 'autocall'

    #     # Client widget
    #     sw = client.shellwidget
    #     if greedy_completer_n in options:
    #         greedy_completer_o = self.get_option(greedy_completer_n)
    #         sw.set_greedy_completer(greedy_completer_o)
    #     if jedi_completer_n in options:
    #         jedi_completer_o = self.get_option(jedi_completer_n)
    #         sw.set_jedi_completer(jedi_completer_o)
    #     if autocall_n in options:
    #         autocall_o = self.get_option(autocall_n)
    #         sw.set_autocall(autocall_o)

    # def _apply_pdb_plugin_settings(self, options, client):
    #     """Apply debugging configurations to a client."""
    #     # Debugging options
    #     pdb_ignore_lib_n = 'pdb_ignore_lib'
    #     pdb_execute_events_n = 'pdb_execute_events'
    #     pdb_use_exclamation_mark_n = 'pdb_use_exclamation_mark'

    #     # Client widget
    #     sw = client.shellwidget
    #     if pdb_ignore_lib_n in options:
    #         pdb_ignore_lib_o = self.get_option(pdb_ignore_lib_n)
    #         sw.set_pdb_ignore_lib(pdb_ignore_lib_o)
    #     if pdb_execute_events_n in options:
    #         pdb_execute_events_o = self.get_option(pdb_execute_events_n)
    #         sw.set_pdb_execute_events(pdb_execute_events_o)
    #     if pdb_use_exclamation_mark_n in options:
    #         pdb_use_exclamation_mark_o = self.get_option(
    #             pdb_use_exclamation_mark_n)
    #         sw.set_pdb_use_exclamation_mark(pdb_use_exclamation_mark_o)

    # def apply_plugin_settings_to_client(
    #         self, options, client, disconnect_ready_signal=False):
    #     """Apply given plugin settings to the given client."""
    #     # GUI options
    #     self._apply_gui_plugin_settings(options, client)

    #     # Matplotlib options
    #     self._apply_mpl_plugin_settings(options, client)

    #     # Advanced options
    #     self._apply_advanced_plugin_settings(options, client)

    #     # Debugging options
    #     self._apply_pdb_plugin_settings(options, client)

    #     if disconnect_ready_signal:
    #         client.shellwidget.sig_pdb_prompt_ready.disconnect()

    # def apply_plugin_settings(self, options):
    #     """Apply configuration file's plugin settings."""
    #     restart_needed = False
    #     restart_options = []

    #     # Startup options (needs a restart)
    #     run_lines_n = 'startup/run_lines'
    #     use_run_file_n = 'startup/use_run_file'
    #     run_file_n = 'startup/run_file'

    #     # Graphic options
    #     pylab_n = 'pylab'
    #     pylab_o = self.get_option(pylab_n)
    #     pylab_backend_n = 'pylab/backend'
    #     inline_backend = 0
    #     pylab_restart = False
    #     client_backend_not_inline = [False] * len(self.clients)
    #     if pylab_o and pylab_backend_n in options:
    #         pylab_backend_o = self.get_option(pylab_backend_n)
    #         client_backend_not_inline = [
    #             client.shellwidget.get_matplotlib_backend() != inline_backend
    #             for client in self.clients]
    #         current_client_backend_not_inline = (
    #             self.get_current_client().shellwidget.get_matplotlib_backend()
    #             != inline_backend)
    #         pylab_restart = (
    #             any(client_backend_not_inline) and
    #             pylab_backend_o != inline_backend)

    #     # Advanced options (needs a restart)
    #     symbolic_math_n = 'symbolic_math'
    #     hide_cmd_windows_n = 'hide_cmd_windows'

    #     restart_options += [run_lines_n, use_run_file_n, run_file_n,
    #                         symbolic_math_n, hide_cmd_windows_n]

    #     restart_needed = any([restart_option in options
    #                           for restart_option in restart_options])

    #     if (restart_needed or pylab_restart) and not running_under_pytest():
    #         restart_dialog = ConsoleRestartDialog(self)
    #         restart_dialog.exec_()
    #         (restart_all, restart_current,
    #          no_restart) = restart_dialog.get_action_value()
    #     else:
    #         restart_all = False
    #         restart_current = False
    #         no_restart = True

    #     # Apply settings
    #     for idx, client in enumerate(self.clients):
    #         restart = ((pylab_restart and client_backend_not_inline[idx]) or
    #                    restart_needed)
    #         if not (restart and restart_all) or no_restart:
    #             sw = client.shellwidget
    #             if sw.is_debugging() and sw._executing:
    #                 # Apply settings when the next Pdb prompt is available
    #                 sw.sig_pdb_prompt_ready.connect(
    #                     lambda o=options, c=client:
    #                         self.apply_plugin_settings_to_client(
    #                             o, c, disconnect_ready_signal=True)
    #                     )
    #             else:
    #                 self.apply_plugin_settings_to_client(options, client)
    #         elif restart and restart_all:
    #             client.ask_before_restart = False
    #             client.restart_kernel()

    #     if (((pylab_restart and current_client_backend_not_inline)
    #          or restart_needed) and restart_current):
    #         current_client = self.get_current_client()
    #         current_client.ask_before_restart = False
    #         current_client.restart_kernel()

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

    # ------ SpyderPluginWidget API -------------------------------------------
    # def get_plugin_title(self):
    #     """Return widget title"""
    #     return _('IPython console')

    # def get_plugin_icon(self):
    #     """Return widget icon"""
    #     return ima.icon('ipython_console')

    # def get_focus_widget(self):
    #     """
    #     Return the widget to give focus to when
    #     this plugin's dockwidget is raised on top-level
    #     """
    #     client = self.tabwidget.currentWidget()
    #     if client is not None:
    #         return client.get_control()

    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        self.mainwindow_close = True
        for client in self.clients:
            client.shutdown()
            client.remove_stderr_file()
            client.dialog_manager.close_all()
            client.close()
        return True

    # def refresh_plugin(self):
    #     """Refresh tabwidget"""
    #     client = None
    #     if self.tabwidget.count():
    #         client = self.tabwidget.currentWidget()

    #         # Decide what to show for each client
    #         if client.info_page != client.blank_page:
    #             # Show info_page if it has content
    #             client.set_info_page()
    #             client.shellwidget.hide()
    #             client.layout.addWidget(self.infowidget)
    #             self.infowidget.show()
    #         else:
    #             self.infowidget.hide()
    #             client.shellwidget.show()

    #         # Give focus to the control widget of the selected tab
    #         control = client.get_control()
    #         control.setFocus()

    #         if isinstance(control, PageControlWidget):
    #             self.pager_label.show()
    #         else:
    #             self.pager_label.hide()

    #         # Create corner widgets
    #         buttons = [[b, -7] for b in client.get_toolbar_buttons()]
    #         buttons = sum(buttons, [])[:-1]
    #         widgets = [client.create_time_label()] + buttons
    #     else:
    #         control = None
    #         widgets = []
    #     self.find_widget.set_editor(control)
    #     self.tabwidget.set_corner_widgets({Qt.TopRightCorner: widgets})

    #     if client:
    #         sw = client.shellwidget
    #         self.main.variableexplorer.set_shellwidget(sw)
    #         self.sig_pdb_state_changed.emit(
    #             sw.is_waiting_pdb_input(), sw.get_pdb_last_step())
    #         self.sig_shellwidget_changed.emit(sw)

    #     self.update_tabs_text()
    #     self.sig_update_plugin_title.emit()

    # def get_plugin_actions(self):
    #     """Return a list of actions related to plugin."""
    #     create_client_action = create_action(
    #                                self,
    #                                _("New console (default settings)"),
    #                                icon=ima.icon('ipython_console'),
    #                                triggered=self.create_new_client,
    #                                context=Qt.WidgetWithChildrenShortcut)
    #     self.register_shortcut(create_client_action, context="ipython_console",
    #                            name="New tab")

    #     create_pylab_action = create_action(
    #                                self,
    #                                _("New Pylab console (data plotting)"),
    #                                icon=ima.icon('ipython_console'),
    #                                triggered=self.create_pylab_client,
    #                                context=Qt.WidgetWithChildrenShortcut)

    #     create_sympy_action = create_action(
    #                                self,
    #                                _("New SymPy console (symbolic math)"),
    #                                icon=ima.icon('ipython_console'),
    #                                triggered=self.create_sympy_client,
    #                                context=Qt.WidgetWithChildrenShortcut)

    #     create_cython_action = create_action(
    #                                self,
    #                                _("New Cython console (Python with "
    #                                  "C extensions)"),
    #                                icon=ima.icon('ipython_console'),
    #                                triggered=self.create_cython_client,
    #                                context=Qt.WidgetWithChildrenShortcut)
    #     special_console_action_group = QActionGroup(self)
    #     special_console_actions = (create_pylab_action, create_sympy_action,
    #                                create_cython_action)
    #     add_actions(special_console_action_group, special_console_actions)
    #     special_console_menu = QMenu(_("New special console"), self)
    #     add_actions(special_console_menu, special_console_actions)

    #     restart_action = create_action(self, _("Restart kernel"),
    #                                    icon=ima.icon('restart'),
    #                                    triggered=self.restart_kernel,
    #                                    context=Qt.WidgetWithChildrenShortcut)

    #     reset_action = create_action(self, _("Remove all variables"),
    #                                  icon=ima.icon('editdelete'),
    #                                  triggered=self.reset_kernel,
    #                                  context=Qt.WidgetWithChildrenShortcut)
    #     self.register_shortcut(reset_action, context="ipython_console",
    #                            name="Reset namespace")

    #     if self.interrupt_action is None:
    #         self.interrupt_action = create_action(
    #             self, _("Interrupt kernel"),
    #             icon=ima.icon('stop'),
    #             triggered=self.interrupt_kernel,
    #             context=Qt.WidgetWithChildrenShortcut)

    #     self.register_shortcut(restart_action, context="ipython_console",
    #                            name="Restart kernel")

    #     connect_to_kernel_action = create_action(self,
    #            _("Connect to an existing kernel"), None, None,
    #            _("Open a new IPython console connected to an existing kernel"),
    #            triggered=self.create_client_for_kernel)

    #     rename_tab_action = create_action(self, _("Rename tab"),
    #                                    icon=ima.icon('rename'),
    #                                    triggered=self.tab_name_editor)

    #     # Add actions to the 'Consoles' menu on the main window
    #     console_menu = self.main.mainmenu.get_application_menu("consoles_menu")
    #     console_menu.aboutToShow.connect(self.update_execution_state_kernel)
    #     new_consoles_actions = [
    #         create_client_action, special_console_menu,
    #         connect_to_kernel_action]
    #     restart_connect_consoles_actions = [
    #         self.interrupt_action, restart_action, reset_action]
    #     for console_new_action in new_consoles_actions:
    #         self.main.mainmenu.add_item_to_application_menu(
    #             console_new_action,
    #             menu_id=ApplicationMenus.Consoles,
    #             section=ConsolesMenuSections.New)
    #     for console_restart_connect_action in restart_connect_consoles_actions:
    #         self.main.mainmenu.add_item_to_application_menu(
    #             console_restart_connect_action,
    #             menu_id=ApplicationMenus.Consoles,
    #             section=ConsolesMenuSections.Restart)

    #     # IPython documentation
    #     self.ipython_menu = SpyderMenu(
    #         parent=self,
    #         title=_("IPython documentation"))
    #     intro_action = create_action(
    #         self,
    #         _("Intro to IPython"),
    #         triggered=self.show_intro)
    #     quickref_action = create_action(
    #         self,
    #         _("Quick reference"),
    #         triggered=self.show_quickref)
    #     guiref_action = create_action(
    #         self,
    #         _("Console help"),
    #         triggered=self.show_guiref)
    #     add_actions(
    #         self.ipython_menu,
    #         (intro_action, guiref_action, quickref_action))
    #     self.main.mainmenu.add_item_to_application_menu(
    #         self.ipython_menu,
    #         menu_id=ApplicationMenus.Help,
    #         section=HelpMenuSections.ExternalDocumentation,
    #         before_section=HelpMenuSections.About)

    #     # Plugin actions
    #     self.menu_actions = [create_client_action, special_console_menu,
    #                          connect_to_kernel_action,
    #                          MENU_SEPARATOR,
    #                          self.interrupt_action,
    #                          restart_action, reset_action, rename_tab_action]

    #     self.update_execution_state_kernel()

    #     # Check for a current client. Since it manages more actions.
    #     client = self.get_current_client()
    #     if client:
    #         return client.get_options_menu()
    #     return self.menu_actions

    # def register_plugin(self):
    #     """Register plugin in Spyder's main window"""
    #     self.add_dockwidget()

    #     self.sig_focus_changed.connect(self.main.plugin_focus_changed)
    #     if self.main.editor:
    #         self.sig_edit_goto_requested.connect(self.main.editor.load)
    #         self.sig_edit_goto_requested[str, int, str, bool].connect(
    #                          lambda fname, lineno, word, processevents:
    #                          self.main.editor.load(
    #                              fname, lineno, word,
    #                              processevents=processevents))
    #         self.main.editor.breakpoints_saved.connect(
    #             self.set_spyder_breakpoints)
    #         self.main.editor.run_in_current_ipyclient.connect(self.run_script)
    #         self.main.editor.run_cell_in_ipyclient.connect(self.run_cell)
    #         self.main.editor.debug_cell_in_ipyclient.connect(self.debug_cell)
    #         # Connect Editor debug action with Console
    #         self.sig_pdb_state_changed.connect(
    #             self.main.editor.update_pdb_state)
    #         self.main.editor.exec_in_extconsole.connect(
    #             self.execute_code_and_focus_editor)
    #     self.tabwidget.currentChanged.connect(self.update_working_directory)
    #     self.tabwidget.currentChanged.connect(self.check_pdb_state)
    #     self._remove_old_stderr_files()

    #     # Update kernels if python path is changed
    #     self.main.sig_pythonpath_changed.connect(self.update_path)

    #     # Show history file if no console is visible
    #     if not self._isvisible and self.main.historylog:
    #         self.main.historylog.add_history(get_conf_path('history.py'))

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

    # def set_elapsed_time(self, client):
    #     """Set elapsed time for slave clients."""
    #     related_clients = self.get_related_clients(client)
    #     for cl in related_clients:
    #         if cl.timer is not None:
    #             client.create_time_label()
    #             client.t0 = cl.t0
    #             client.timer.timeout.connect(client.show_time)
    #             client.timer.start(1000)
    #             break

    # def set_infowidget_font(self):
    #     """Set font for infowidget"""
    #     font = get_font(option='rich_font')
    #     self.infowidget.set_font(font)

    #------ Public API (for kernels) ------------------------------------------
    # def ssh_tunnel(self, *args, **kwargs):
    #     if os.name == 'nt':
    #         return zmqtunnel.paramiko_tunnel(*args, **kwargs)
    #     else:
    #         return openssh_tunnel(self, *args, **kwargs)

    # def tunnel_to_kernel(self, connection_info, hostname, sshkey=None,
    #                      password=None, timeout=10):
    #     """
    #     Tunnel connections to a kernel via ssh.

    #     Remote ports are specified in the connection info ci.
    #     """
    #     lports = zmqtunnel.select_random_ports(4)
    #     rports = (connection_info['shell_port'], connection_info['iopub_port'],
    #               connection_info['stdin_port'], connection_info['hb_port'])
    #     remote_ip = connection_info['ip']
    #     for lp, rp in zip(lports, rports):
    #         self.ssh_tunnel(lp, rp, hostname, remote_ip, sshkey, password,
    #                         timeout)
    #     return tuple(lports)

    # def create_kernel_spec(self, is_cython=False,
    #                        is_pylab=False, is_sympy=False):
    #     """Create a kernel spec for our own kernels"""
    #     # Before creating our kernel spec, we always need to
    #     # set this value in spyder.ini
    #     CONF.set('main', 'spyder_pythonpath',
    #              self.main.get_spyder_pythonpath())
    #     return SpyderKernelSpec(is_cython=is_cython,
    #                             is_pylab=is_pylab,
    #                             is_sympy=is_sympy)

    # def create_kernel_manager_and_kernel_client(self, connection_file,
    #                                             stderr_handle,
    #                                             is_cython=False,
    #                                             is_pylab=False,
    #                                             is_sympy=False):
    #     """Create kernel manager and client."""
    #     # Kernel spec
    #     kernel_spec = self.create_kernel_spec(is_cython=is_cython,
    #                                           is_pylab=is_pylab,
    #                                           is_sympy=is_sympy)

    #     # Kernel manager
    #     try:
    #         kernel_manager = SpyderKernelManager(
    #             connection_file=connection_file,
    #             config=None,
    #             autorestart=True,
    #         )
    #     except Exception:
    #         error_msg = _("The error is:<br><br>"
    #                       "<tt>{}</tt>").format(traceback.format_exc())
    #         return (error_msg, None)
    #     kernel_manager._kernel_spec = kernel_spec

    #     # Catch any error generated when trying to start the kernel.
    #     # See spyder-ide/spyder#7302.
    #     try:
    #         kernel_manager.start_kernel(stderr=stderr_handle,
    #                                     env=kernel_spec.env)
    #     except Exception:
    #         error_msg = _("The error is:<br><br>"
    #                       "<tt>{}</tt>").format(traceback.format_exc())
    #         return (error_msg, None)

    #     # Kernel client
    #     kernel_client = kernel_manager.client()

    #     # Increase time (in seconds) to detect if a kernel is alive.
    #     # See spyder-ide/spyder#3444.
    #     kernel_client.hb_channel.time_to_dead = 25.0

    #     return kernel_manager, kernel_client

    # def restart_kernel(self):
    #     """Restart kernel of current client."""
    #     client = self.get_current_client()
    #     if client is not None:
    #         self.switch_to_plugin()
    #         client.restart_kernel()

    # def reset_kernel(self):
    #     """Reset kernel of current client."""
    #     client = self.get_current_client()
    #     if client is not None:
    #         self.switch_to_plugin()
    #         client.reset_namespace()

    # def interrupt_kernel(self):
    #     """Interrupt kernel of current client."""
    #     client = self.get_current_client()
    #     if client is not None:
    #         self.switch_to_plugin()
    #         client.stop_button_click_handler()

    # def update_execution_state_kernel(self):
    #     """Update actions following the execution state of the kernel."""
    #     client = self.get_current_client()
    #     if client is not None:
    #         executing = client.stop_button.isEnabled()
    #         self.interrupt_action.setEnabled(executing)

    # def connect_external_kernel(self, shellwidget):
    #     """
    #     Connect an external kernel to the Variable Explorer, Help and
    #     Plots, but only if it is a Spyder kernel.
    #     """
    #     sw = shellwidget
    #     kc = shellwidget.kernel_client
    #     self.sig_shellwidget_changed.emit(sw)

    #     if self.main.variableexplorer is not None:
    #         self.main.variableexplorer.add_shellwidget(sw)
    #         sw.set_namespace_view_settings()
    #         sw.refresh_namespacebrowser()
    #         kc.stopped_channels.connect(lambda :
    #             self.main.variableexplorer.remove_shellwidget(id(sw)))

    #     if self.main.plots is not None:
    #         self.main.plots.add_shellwidget(sw)
    #         kc.stopped_channels.connect(lambda :
    #             self.main.plots.remove_shellwidget(id(sw)))

    # #------ Public API (for tabs) ---------------------------------------------
    # def add_tab(self, widget, name, filename=''):
    #     """Add tab"""
    #     self.clients.append(widget)
    #     index = self.tabwidget.addTab(widget, name)
    #     self.filenames.insert(index, filename)
    #     self.tabwidget.setCurrentIndex(index)
    #     if self.dockwidget and not self.main.is_setting_up:
    #         self.switch_to_plugin()
    #     self.activateWindow()
    #     widget.get_control().setFocus()
    #     self.update_tabs_text()

    # def move_tab(self, index_from, index_to):
    #     """
    #     Move tab (tabs themselves have already been moved by the tabwidget)
    #     """
    #     filename = self.filenames.pop(index_from)
    #     client = self.clients.pop(index_from)
    #     self.filenames.insert(index_to, filename)
    #     self.clients.insert(index_to, client)
    #     self.update_tabs_text()
    #     self.sig_update_plugin_title.emit()

    # def disambiguate_fname(self, fname):
    #     """Generate a file name without ambiguation."""
    #     files_path_list = [filename for filename in self.filenames
    #                        if filename]
    #     return sourcecode.disambiguate_fname(files_path_list, fname)

    # def update_tabs_text(self):
    #     """Update the text from the tabs."""
    #     # This is needed to prevent that hanged consoles make reference
    #     # to an index that doesn't exist. See spyder-ide/spyder#4881.
    #     try:
    #         for index, fname in enumerate(self.filenames):
    #             client = self.clients[index]
    #             if fname:
    #                 self.rename_client_tab(client,
    #                                        self.disambiguate_fname(fname))
    #             else:
    #                 self.rename_client_tab(client, None)
    #     except IndexError:
    #         pass

    # def rename_client_tab(self, client, given_name):
    #     """Rename client's tab"""
    #     index = self.get_client_index_from_id(id(client))

    #     if given_name is not None:
    #         client.given_name = given_name
    #     self.tabwidget.setTabText(index, client.get_name())

    # def rename_tabs_after_change(self, given_name):
    #     """Rename tabs after a change in name."""
    #     client = self.get_current_client()

    #     # Prevent renames that want to assign the same name of
    #     # a previous tab
    #     repeated = False
    #     for cl in self.get_clients():
    #         if id(client) != id(cl) and given_name == cl.given_name:
    #             repeated = True
    #             break

    #     # Rename current client tab to add str_id
    #     if client.allow_rename and not u'/' in given_name and not repeated:
    #         self.rename_client_tab(client, given_name)
    #     else:
    #         self.rename_client_tab(client, None)

    #     # Rename related clients
    #     if client.allow_rename and not u'/' in given_name and not repeated:
    #         for cl in self.get_related_clients(client):
    #             self.rename_client_tab(cl, given_name)

    # def tab_name_editor(self):
    #     """Trigger the tab name editor."""
    #     index = self.tabwidget.currentIndex()
    #     self.tabwidget.tabBar().tab_name_editor.edit_tab(index)

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

    #------ Private API -------------------------------------------------------
    # def _init_asyncio_patch(self):
    #     """
    #     - This was fixed in Tornado 6.1!
    #     - Same workaround fix as ipython/ipykernel#564
    #     - ref: tornadoweb/tornado#2608
    #     - On Python 3.8+, Tornado 6.0 is not compatible with the default
    #       asyncio implementation on Windows. Pick the older
    #       SelectorEventLoopPolicy if the known-incompatible default policy is
    #       in use.
    #     - Do this as early as possible to make it a low priority and
    #       overrideable.
    #     """
    #     if os.name == 'nt' and PY38_OR_MORE:
    #         # Tests on Linux hang if we don't leave this import here.
    #         import tornado
    #         if tornado.version_info >= (6, 1):
    #             return

    #         import asyncio
    #         try:
    #             from asyncio import (
    #                 WindowsProactorEventLoopPolicy,
    #                 WindowsSelectorEventLoopPolicy,
    #             )
    #         except ImportError:
    #             # not affected
    #             pass
    #         else:
    #             if isinstance(
    #                     asyncio.get_event_loop_policy(),
    #                     WindowsProactorEventLoopPolicy):
    #                 # WindowsProactorEventLoopPolicy is not compatible
    #                 # with tornado 6 fallback to the pre-3.8
    #                 # default of Selector
    #                 asyncio.set_event_loop_policy(
    #                     WindowsSelectorEventLoopPolicy())

    # def _new_connection_file(self):
    #     """
    #     Generate a new connection file

    #     Taken from jupyter_client/console_app.py
    #     Licensed under the BSD license
    #     """
    #     # Check if jupyter_runtime_dir exists (Spyder addition)
    #     if not osp.isdir(jupyter_runtime_dir()):
    #         try:
    #             os.makedirs(jupyter_runtime_dir())
    #         except (IOError, OSError):
    #             return None
    #     cf = ''
    #     while not cf:
    #         ident = str(uuid.uuid4()).split('-')[-1]
    #         cf = os.path.join(jupyter_runtime_dir(), 'kernel-%s.json' % ident)
    #         cf = cf if not os.path.exists(cf) else ''
    #     return cf

    # def shellwidget_started(self, client):
    #     if self.main.variableexplorer is not None:
    #         self.main.variableexplorer.add_shellwidget(client.shellwidget)

    #     self.sig_shellwidget_created.emit(client.shellwidget)

    # def shellwidget_deleted(self, client):
    #     if self.main.variableexplorer is not None:
    #         self.main.variableexplorer.remove_shellwidget(client.shellwidget)

    #     self.sig_shellwidget_deleted.emit(client.shellwidget)

    # def _create_client_for_kernel(self, connection_file, hostname, sshkey,
    #                               password):
    #     # Verifying if the connection file exists
    #     try:
    #         cf_path = osp.dirname(connection_file)
    #         cf_filename = osp.basename(connection_file)
    #         # To change a possible empty string to None
    #         cf_path = cf_path if cf_path else None
    #         connection_file = find_connection_file(filename=cf_filename,
    #                                                path=cf_path)
    #     except (IOError, UnboundLocalError):
    #         QMessageBox.critical(self, _('IPython'),
    #                              _("Unable to connect to "
    #                                "<b>%s</b>") % connection_file)
    #         return

    #     # Getting the master id that corresponds to the client
    #     # (i.e. the i in i/A)
    #     master_id = None
    #     given_name = None
    #     external_kernel = False
    #     slave_ord = ord('A') - 1
    #     kernel_manager = None

    #     for cl in self.get_clients():
    #         if connection_file in cl.connection_file:
    #             if cl.get_kernel() is not None:
    #                 kernel_manager = cl.get_kernel()
    #             connection_file = cl.connection_file
    #             if master_id is None:
    #                 master_id = cl.id_['int_id']
    #             given_name = cl.given_name
    #             new_slave_ord = ord(cl.id_['str_id'])
    #             if new_slave_ord > slave_ord:
    #                 slave_ord = new_slave_ord

    #     # If we couldn't find a client with the same connection file,
    #     # it means this is a new master client
    #     if master_id is None:
    #         self.master_clients += 1
    #         master_id = to_text_string(self.master_clients)
    #         external_kernel = True

    #     # Set full client name
    #     client_id = dict(int_id=master_id,
    #                      str_id=chr(slave_ord + 1))

    #     # Creating the client
    #     show_elapsed_time = self.get_option('show_elapsed_time')
    #     reset_warning = self.get_option('show_reset_namespace_warning')
    #     ask_before_restart = self.get_option('ask_before_restart')
    #     client = ClientWidget(self,
    #                           id_=client_id,
    #                           given_name=given_name,
    #                           history_filename=get_conf_path('history.py'),
    #                           config_options=self.config_options(),
    #                           additional_options=self.additional_options(),
    #                           interpreter_versions=self.interpreter_versions(),
    #                           connection_file=connection_file,
    #                           menu_actions=self.menu_actions,
    #                           hostname=hostname,
    #                           external_kernel=external_kernel,
    #                           slave=True,
    #                           show_elapsed_time=show_elapsed_time,
    #                           reset_warning=reset_warning,
    #                           ask_before_restart=ask_before_restart,
    #                           css_path=self.css_path)

    #     # Change stderr_dir if requested
    #     if self.test_dir is not None:
    #         client.stderr_dir = self.test_dir

    #     # Create kernel client
    #     kernel_client = QtKernelClient(connection_file=connection_file)

    #     # This is needed for issue spyder-ide/spyder#9304.
    #     try:
    #         kernel_client.load_connection_file()
    #     except Exception as e:
    #         QMessageBox.critical(self, _('Connection error'),
    #                              _("An error occurred while trying to load "
    #                                "the kernel connection file. The error "
    #                                "was:\n\n") + to_text_string(e))
    #         return

    #     if hostname is not None:
    #         try:
    #             connection_info = dict(ip = kernel_client.ip,
    #                                    shell_port = kernel_client.shell_port,
    #                                    iopub_port = kernel_client.iopub_port,
    #                                    stdin_port = kernel_client.stdin_port,
    #                                    hb_port = kernel_client.hb_port)
    #             newports = self.tunnel_to_kernel(connection_info, hostname,
    #                                              sshkey, password)
    #             (kernel_client.shell_port,
    #              kernel_client.iopub_port,
    #              kernel_client.stdin_port,
    #              kernel_client.hb_port) = newports
    #             # Save parameters to connect comm later
    #             kernel_client.ssh_parameters = (hostname, sshkey, password)
    #         except Exception as e:
    #             QMessageBox.critical(self, _('Connection error'),
    #                                _("Could not open ssh tunnel. The "
    #                                  "error was:\n\n") + to_text_string(e))
    #             return

    #     # Assign kernel manager and client to shellwidget
    #     kernel_client.start_channels()
    #     shellwidget = client.shellwidget
    #     shellwidget.set_kernel_client_and_manager(
    #         kernel_client, kernel_manager)
    #     shellwidget.sig_exception_occurred.connect(
    #         self.sig_exception_occurred)

    #     if external_kernel:
    #         shellwidget.sig_is_spykernel.connect(
    #             self.connect_external_kernel)
    #         shellwidget.check_spyder_kernel()

    #     # Set elapsed time, if possible
    #     if not external_kernel:
    #         self.set_elapsed_time(client)

    #     # Adding a new tab for the client
    #     self.add_tab(client, name=client.get_name())

    #     # Register client
    #     self.register_client(client)

    # def print_debug_file_msg(self):
    #     """Print message in the current console when a file can't be closed."""
    #     debug_msg = _('The current file cannot be closed because it is '
    #                   'in debug mode.')
    #     self.get_current_client().shellwidget.append_html_message(
    #                 debug_msg, before_prompt=True)

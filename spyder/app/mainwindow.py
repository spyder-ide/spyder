# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder, the Scientific Python Development Environment
=====================================================

Developed and maintained by the Spyder Project
Contributors

Copyright © Spyder Project Contributors
Licensed under the terms of the MIT License
(see spyder/__init__.py for details)
"""

# =============================================================================
# Stdlib imports
# =============================================================================
from __future__ import print_function
from collections import OrderedDict
from enum import Enum
import errno
import gc
import logging
import os
import os.path as osp
import re
import shutil
import signal
import socket
import glob
import subprocess
import sys
import threading
import traceback
import importlib

#==============================================================================
# Check requirements before proceeding
#==============================================================================
from spyder import requirements
requirements.check_path()
requirements.check_qt()
requirements.check_spyder_kernels()

#==============================================================================
# Third-party imports
#==============================================================================
from qtpy import API, PYQT5
from qtpy.compat import from_qvariant
from qtpy.QtCore import (QByteArray, QCoreApplication, QPoint, QSize, Qt,
                         QThread, QTimer, QUrl, Signal, Slot,
                         qInstallMessageHandler)
from qtpy.QtGui import QColor, QDesktopServices, QIcon, QKeySequence
from qtpy.QtWidgets import (QAction, QApplication, QDesktopWidget, QDockWidget,
                            QMainWindow, QMenu, QMessageBox, QShortcut,
                            QStyleFactory, QCheckBox)

# Avoid a "Cannot mix incompatible Qt library" error on Windows platforms
from qtpy import QtSvg  # analysis:ignore

# Avoid a bug in Qt: https://bugreports.qt.io/browse/QTBUG-46720
from qtpy import QtWebEngineWidgets  # analysis:ignore

import qdarkstyle
from qtawesome.iconic_font import FontError

#==============================================================================
# Local imports
# NOTE: Move (if possible) import's of widgets and plugins exactly where they
# are needed in MainWindow to speed up perceived startup time (i.e. the time
# from clicking the Spyder icon to showing the splash screen).
#==============================================================================
from spyder import (__version__, __project_url__, __forum_url__,
                    __trouble_url__, get_versions, __docs_url__)
from spyder import dependencies
from spyder.app import tour
from spyder.app.utils import (create_splash_screen, delete_lsp_log_files,
                              get_python_doc_path, qt_message_handler,
                              setup_logging, set_opengl_implementation, Spy)
from spyder.config.base import (_, DEV, get_conf_path, get_debug_level,
                                get_home_dir, get_image_path, get_module_path,
                                get_module_source_path, get_safe_mode,
                                is_pynsist, running_in_mac_app,
                                running_under_pytest, STDERR)
from spyder.config.gui import is_dark_font_color
from spyder.config.main import OPEN_FILES_PORT
from spyder.config.manager import CONF
from spyder.config.utils import IMPORT_EXT, is_anaconda, is_gtk_desktop
from spyder.otherplugins import get_spyderplugins_mods
from spyder.py3compat import (configparser as cp, is_text_string,
                              PY3, qbytearray_to_str, to_text_string)
from spyder.utils import encoding, programs
from spyder.utils import icon_manager as ima
from spyder.utils.misc import (select_port, getcwd_or_home,
                               get_python_executable)
from spyder.utils.programs import is_module_installed
from spyder.utils.qthelpers import (create_action, add_actions, get_icon,
                                    create_program_action, DialogManager,
                                    create_python_script_action, file_uri,
                                    MENU_SEPARATOR, qapplication, start_file)
from spyder.otherplugins import get_spyderplugins_mods
from spyder.app import tour
from spyder.app.solver import find_external_plugins, solve_plugin_dependencies

# Spyder API Imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import Plugins, SpyderPluginV2, SpyderDockablePlugin

#==============================================================================
# Windows only local imports
#==============================================================================
set_attached_console_visible = None
is_attached_console_visible = None
set_windows_appusermodelid = None
if os.name == 'nt':
    from spyder.utils.windows import (set_attached_console_visible,
                                      is_attached_console_visible,
                                      set_windows_appusermodelid)

#==============================================================================
# Constants
#==============================================================================
# Module logger
logger = logging.getLogger(__name__)

# Keeping a reference to the original sys.exit before patching it
ORIGINAL_SYS_EXIT = sys.exit

# Get the cwd before initializing WorkingDirectory, which sets it to the one
# used in the last session
CWD = getcwd_or_home()

# Set the index for the default tour
DEFAULT_TOUR = 0

#==============================================================================
# Install Qt messaage handler
#==============================================================================
qInstallMessageHandler(qt_message_handler)

#==============================================================================
# Main Window
#==============================================================================
class MainWindow(QMainWindow):
    """Spyder main window"""
    DOCKOPTIONS = (
        QMainWindow.AllowTabbedDocks | QMainWindow.AllowNestedDocks |
        QMainWindow.AnimatedDocks
    )
    SPYDER_PATH = get_conf_path('path')
    SPYDER_NOT_ACTIVE_PATH = get_conf_path('not_active_path')
    DEFAULT_LAYOUTS = 4

    # Signals
    restore_scrollbar_position = Signal()
    sig_setup_finished = Signal()
    all_actions_defined = Signal()
    # type: (OrderedDict, OrderedDict)
    sig_pythonpath_changed = Signal(object, object)
    sig_main_interpreter_changed = Signal()
    sig_open_external_file = Signal(str)
    sig_resized = Signal("QResizeEvent")     # Related to interactive tour
    sig_moved = Signal("QMoveEvent")         # Related to interactive tour
    sig_layout_setup_ready = Signal(object)  # Related to default layouts

    # --- Plugin handling methods
    # ------------------------------------------------------------------------
    def get_plugin(self, plugin_name):
        """
        Return a plugin instance by providing the plugin class.
        """
        for name, plugin in self._PLUGINS.items():
            if plugin_name == name:
                return plugin
        else:
            raise SpyderAPIError('Plugin "{}" not found!'.format(plugin_name))

    def show_status_message(self, message, timeout):
        """
        Show a status message in Spyder Main Window.
        """
        status_bar = self.statusBar()
        if status_bar.isVisible():
            status_bar.showMessage(message, timeout)

    def show_plugin_compatibility_message(self, message):
        """
        Show a compatibility message.
        """
        messageBox = QMessageBox(self)
        messageBox.setWindowModality(Qt.NonModal)
        messageBox.setAttribute(Qt.WA_DeleteOnClose)
        messageBox.setWindowTitle(_('Compatibility Check'))
        messageBox.setText(message)
        messageBox.setStandardButtons(QMessageBox.Ok)
        messageBox.show()

    def add_plugin(self, plugin, external=False):
        """
        Add plugin to plugins dictionary.
        """
        self._PLUGINS[plugin.CONF_SECTION] = plugin
        if external:
            self._EXTERNAL_PLUGINS[plugin.CONF_SECTION] = plugin
        else:
            self._INTERNAL_PLUGINS[plugin.CONF_SECTION] = plugin

    def register_plugin(self, plugin, external=False):
        """
        Register a plugin in Spyder Main Window.
        """
        self.set_splash(_("Loading {}...".format(plugin.get_name())))
        logger.info("Loading {}...".format(plugin.NAME))

        # Check plugin compatibility
        is_compatible, message = plugin.check_compatibility()
        plugin.is_compatible = is_compatible
        plugin.get_description()

        if not is_compatible:
            self.show_compatibility_message(message)
            return

        # Signals
        plugin.sig_exception_occurred.connect(self.handle_exception)
        plugin.sig_free_memory_requested.connect(self.free_memory)
        plugin.sig_quit_requested.connect(self.close)
        plugin.sig_restart_requested.connect(self.restart)
        plugin.sig_redirect_stdio_requested.connect(
            self.redirect_internalshell_stdio)
        plugin.sig_status_message_requested.connect(self.show_status_message)

        if isinstance(plugin, SpyderDockablePlugin):
            plugin.sig_focus_changed.connect(self.plugin_focus_changed)
            plugin.sig_switch_to_plugin_requested.connect(
                self.switch_to_plugin)
            plugin.sig_update_ancestor_requested.connect(
                lambda: plugin.set_ancestor(self))

        # Register plugin
        plugin._register()
        plugin.register()

        if isinstance(plugin, SpyderDockablePlugin):
            # Add dockwidget
            self.add_dockwidget(plugin)

            # Update margins
            margin = 0
            if CONF.get('main', 'use_custom_margin'):
                margin = CONF.get('main', 'custom_margin')
            plugin.update_margins(margin)

        self.add_plugin(plugin, external=external)

        logger.info("Registering shortcuts for {}...".format(plugin.NAME))
        for action_name, action in plugin.get_actions().items():
            context = (getattr(action, 'shortcut_context', plugin.NAME)
                       or plugin.NAME)

            if getattr(action, 'register_shortcut', True):
                if isinstance(action_name, Enum):
                    action_name = action_name.value

                self.register_shortcut(action, context, action_name)

        if isinstance(plugin, SpyderDockablePlugin):
            try:
                context = '_'
                name = 'switch to {}'.format(plugin.CONF_SECTION)
                shortcut = CONF.get_shortcut(context, name,
                                             plugin_name=plugin.CONF_SECTION)
            except (cp.NoSectionError, cp.NoOptionError):
                shortcut = None

            sc = QShortcut(QKeySequence(), self,
                           lambda: self.switch_to_plugin(plugin))
            sc.setContext(Qt.ApplicationShortcut)
            plugin._shortcut = sc

            self.register_shortcut(sc, context, name)
            self.register_shortcut(plugin.toggle_view_action, context, name)

    def unregister_plugin(self, plugin):
        """
        Unregister a plugin from the Spyder Main Window.
        """
        logger.info("Unloading {}...".format(plugin.NAME))

        # Disconnect all slots
        signals = [
            plugin.sig_quit_requested,
            plugin.sig_redirect_stdio,
            plugin.sig_status_message_requested,
        ]
        for signal in signals:
            try:
                signal.disconnect()
            except TypeError:
                pass

        # Unregister shortcuts for actions
        logger.info("Unregistering shortcuts for {}...".format(plugin.NAME))
        for action_name, action in plugin.get_actions().items():
            context = (getattr(action, 'shortcut_context', plugin.NAME)
                       or plugin.NAME)
            self.unregister_shortcut(action, context, action_name)

        # Unregister switch to shortcut
        try:
            context = '_'
            name = 'switch to {}'.format(plugin.CONF_SECTION)
            shortcut = CONF.get_shortcut(context, name,
                                         plugin_name=plugin.CONF_SECTION)
        except Exception:
            pass

        if shortcut is not None:
            self.unregister_shortcut(
                plugin._shortcut,
                context,
                "Switch to {}".format(plugin.CONF_SECTION),
            )

        # Remove dockwidget
        logger.info("Removing {} dockwidget...".format(plugin.NAME))
        self.remove_dockwidget(plugin)

        plugin.unregister()
        plugin._unregister()

    def create_plugin_conf_widget(self, plugin):
        """
        Create configuration dialog box page widget.
        """
        config_dialog = self.prefs_dialog_instance
        if plugin.CONF_WIDGET_CLASS is not None and config_dialog is not None:
            conf_widget = plugin.CONF_WIDGET_CLASS(plugin, config_dialog)
            conf_widget.initialize()
            return conf_widget

    def switch_to_plugin(self, plugin, force_focus=None):
        """
        Switch to this plugin.

        Notes
        -----
        This operation unmaximizes the current plugin (if any), raises
        this plugin to view (if it's hidden) and gives it focus (if
        possible).
        """
        try:
            # New API
            if (self.last_plugin is not None
                    and self.last_plugin.get_widget().is_maximized
                    and self.last_plugin is not plugin):
                self.maximize_dockwidget()
        except AttributeError:
            # Old API
            if (self.last_plugin is not None and self.last_plugin._ismaximized
                    and self.last_plugin is not plugin):
                self.maximize_dockwidget()

        try:
            # New API
            if not plugin.toggle_view_action.isChecked():
                plugin.toggle_view_action.setChecked(True)
                plugin.get_widget().is_visible = False
        except AttributeError:
            # Old API
            if not plugin._toggle_view_action.isChecked():
                plugin._toggle_view_action.setChecked(True)
                plugin._widget._is_visible = False

        plugin.change_visibility(True, force_focus=force_focus)

    def remove_dockwidget(self, plugin):
        """
        Remove a plugin QDockWidget from the main window.
        """
        self.removeDockWidget(plugin.dockwidget)
        self.widgetlist.remove(plugin)

    def tabify_plugin(self, plugin):
        """
        Tabify the plugin using the list of possible TABIFY options.

        Only do this if the dockwidget does not have more dockwidgets
        in the same position and if the plugin is using the New API.
        """
        def tabify_helper(plugin, next_to_plugins):
            for next_to_plugin in next_to_plugins:
                try:
                    self.tabify_plugins(next_to_plugin, plugin)
                    break
                except SpyderAPIError as err:
                    logger.error(err)

        # If TABIFY not defined use the [Console]
        tabify = getattr(plugin, 'TABIFY', [self.get_plugin(Plugins.Console)])
        if not isinstance(tabify, list):
            next_to_plugins = [tabify]
        else:
            next_to_plugins = tabify

        # Get the actual plugins from the names
        next_to_plugins = [self.get_plugin(p) for p in next_to_plugins]

        # First time plugin starts
        if plugin.get_conf('first_time', True):
            if (isinstance(plugin, SpyderDockablePlugin)
                    and plugin.NAME != Plugins.Console):
                logger.info(
                    "Tabify {} dockwidget for the first time...".format(
                        plugin.NAME))
                tabify_helper(plugin, next_to_plugins)

            plugin.set_conf('enable', True)
            plugin.set_conf('first_time', False)
        else:
            # This is needed to ensure new plugins are placed correctly
            # without the need for a layout reset.
            logger.info("Tabify {} dockwidget...".format(plugin.NAME))
            # Check if plugin has no other dockwidgets in the same position
            if not bool(self.tabifiedDockWidgets(plugin.dockwidget)):
                tabify_helper(plugin, next_to_plugins)

    def handle_exception(self, error_data):
        """
        This method will call the handle exception method of the Console
        plugin. It is provided as a signal on the Plugin API for convenience,
        so that plugin do not need to explicitly call the Console plugin.

        Parameters
        ----------
        error_data: dict
            The dictionary containing error data. The expected keys are:
            >>> error_data= {
                "text": str,
                "is_traceback": bool,
                "repo": str,
                "title": str,
                "label": str,
                "steps": str,
            }

        Notes
        -----
        The `is_traceback` key indicates if `text` contains plain text or a
        Python error traceback.

        The `title` and `repo` keys indicate how the error data should
        customize the report dialog and Github error submission.

        The `label` and `steps` keys allow customizing the content of the
        error dialog.
        """
        if self.console:
            self.console.handle_exception(error_data)

    def __init__(self, splash=None, options=None):
        QMainWindow.__init__(self)
        qapp = QApplication.instance()

        if running_under_pytest():
            self._proxy_style = None
        else:
            from spyder.utils.qthelpers import SpyderProxyStyle
            # None is needed, see: https://bugreports.qt.io/browse/PYSIDE-922
            self._proxy_style = SpyderProxyStyle(None)

        if PYQT5:
            # Enabling scaling for high dpi
            qapp.setAttribute(Qt.AA_UseHighDpiPixmaps)

        self.default_style = str(qapp.style().objectName())

        self.init_workdir = options.working_directory
        self.profile = options.profile
        self.multithreaded = options.multithreaded
        self.new_instance = options.new_instance
        if options.project is not None and not running_in_mac_app():
            self.open_project = osp.normpath(osp.join(CWD, options.project))
        else:
            self.open_project = None
        self.window_title = options.window_title

        logger.info("Start of MainWindow constructor")

        def signal_handler(signum, frame=None):
            """Handler for signals."""
            sys.stdout.write('Handling signal: %s\n' % signum)
            sys.stdout.flush()
            QApplication.quit()

        if os.name == "nt":
            try:
                import win32api
                win32api.SetConsoleCtrlHandler(signal_handler, True)
            except ImportError:
                pass
        else:
            signal.signal(signal.SIGTERM, signal_handler)
            if not DEV:
                # Make spyder quit when presing ctrl+C in the console
                # In DEV Ctrl+C doesn't quit, because it helps to
                # capture the traceback when spyder freezes
                signal.signal(signal.SIGINT, signal_handler)

        # Use a custom Qt stylesheet
        if sys.platform == 'darwin':
            spy_path = get_module_source_path('spyder')
            img_path = osp.join(spy_path, 'images')
            mac_style = open(osp.join(spy_path, 'app', 'mac_stylesheet.qss')).read()
            mac_style = mac_style.replace('$IMAGE_PATH', img_path)
            self.setStyleSheet(mac_style)

        # Shortcut management data
        self.shortcut_data = []

        # Handle Spyder path
        self.path = ()
        self.not_active_path = ()
        self.project_path = ()

        # New API
        self._APPLICATION_TOOLBARS = OrderedDict()
        self._STATUS_WIDGETS = OrderedDict()
        self._PLUGINS = OrderedDict()
        self._EXTERNAL_PLUGINS = OrderedDict()
        self._INTERNAL_PLUGINS = OrderedDict()

        # Plugins
        self.console = None
        self.workingdirectory = None
        self.editor = None
        self.explorer = None
        self.help = None
        self.onlinehelp = None
        self.projects = None
        self.outlineexplorer = None
        self.historylog = None
        self.ipyconsole = None
        self.variableexplorer = None
        self.plots = None
        self.findinfiles = None
        self.thirdparty_plugins = []

        # Tour  # TODO: Should I consider it a plugin?? or?
        self.tour = None
        self.tours_available = None
        self.tour_dialog = None

        # File switcher
        self.switcher = None

        # Preferences
        self.prefs_dialog_size = None
        self.prefs_dialog_instance = None

        # Quick Layouts and Dialogs
        from spyder.preferences.layoutdialog import (LayoutSaveDialog,
                                                 LayoutSettingsDialog)
        self.dialog_layout_save = LayoutSaveDialog
        self.dialog_layout_settings = LayoutSettingsDialog

        # Actions
        self.lock_interface_action = None
        self.close_dockwidget_action = None
        self.undo_action = None
        self.redo_action = None
        self.copy_action = None
        self.cut_action = None
        self.paste_action = None
        self.selectall_action = None
        self.maximize_action = None
        self.fullscreen_action = None

        # Menu bars
        self.edit_menu = None
        self.edit_menu_actions = []
        self.search_menu = None
        self.search_menu_actions = []
        self.source_menu = None
        self.source_menu_actions = []
        self.run_menu = None
        self.run_menu_actions = []
        self.debug_menu = None
        self.debug_menu_actions = []
        self.consoles_menu = None
        self.consoles_menu_actions = []
        self.projects_menu = None
        self.projects_menu_actions = []

        self.plugins_menu = None
        self.plugins_menu_actions = []

        # TODO: Move to corresponding Plugins
        self.main_toolbar = None
        self.main_toolbar_actions = []
        self.file_toolbar = None
        self.file_toolbar_actions = []
        self.run_toolbar = None
        self.run_toolbar_actions = []
        self.debug_toolbar = None
        self.debug_toolbar_actions = []

        self.menus = []

        if running_under_pytest():
            # Show errors in internal console when testing.
            CONF.set('main', 'show_internal_errors', False)

        # Set window title
        self.set_window_title()

        self.CURSORBLINK_OSDEFAULT = QApplication.cursorFlashTime()

        if set_windows_appusermodelid != None:
            res = set_windows_appusermodelid()
            logger.info("appusermodelid: %s", res)

        # Setting QTimer if running in travis
        test_app = os.environ.get('TEST_CI_APP')
        if test_app is not None:
            app = qapplication()
            timer_shutdown_time = 30000
            self.timer_shutdown = QTimer(self)
            self.timer_shutdown.timeout.connect(app.quit)
            self.timer_shutdown.start(timer_shutdown_time)

        # Showing splash screen
        self.splash = splash
        if CONF.get('main', 'current_version', '') != __version__:
            CONF.set('main', 'current_version', __version__)
            # Execute here the actions to be performed only once after
            # each update (there is nothing there for now, but it could
            # be useful some day...)

        # List of satellite widgets (registered in add_dockwidget):
        self.widgetlist = []

        # Flags used if closing() is called by the exit() shell command
        self.already_closed = False
        self.is_starting_up = True
        self.is_setting_up = True

        self.interface_locked = CONF.get('main', 'panes_locked')
        self.floating_dockwidgets = []
        self.window_size = None
        self.window_position = None
        self.state_before_maximizing = None
        self.current_quick_layout = None
        self.previous_layout_settings = None  # TODO: related to quick layouts
        self.last_plugin = None
        self.fullscreen_flag = None  # isFullscreen does not work as expected
        # The following flag remember the maximized state even when
        # the window is in fullscreen mode:
        self.maximized_flag = None
        # The following flag is used to restore window's geometry when
        # toggling out of fullscreen mode in Windows.
        self.saved_normal_geometry = None

        # To keep track of the last focused widget
        self.last_focused_widget = None
        self.previous_focused_widget = None

        # Keep track of dpi message
        self.show_dpi_message = True

        # Server to open external files on a single instance
        # This is needed in order to handle socket creation problems.
        # See spyder-ide/spyder#4132.
        if os.name == 'nt':
            try:
                self.open_files_server = socket.socket(socket.AF_INET,
                                                       socket.SOCK_STREAM,
                                                       socket.IPPROTO_TCP)
            except OSError as e:
                self.open_files_server = None
                QMessageBox.warning(None, "Spyder",
                         _("An error occurred while creating a socket needed "
                           "by Spyder. Please, try to run as an Administrator "
                           "from cmd.exe the following command and then "
                           "restart your computer: <br><br><span "
                           "style=\'color: #555555\'><b>netsh winsock reset"
                           "</b></span><br>"))
        else:
            self.open_files_server = socket.socket(socket.AF_INET,
                                                   socket.SOCK_STREAM,
                                                   socket.IPPROTO_TCP)

        # To show the message about starting the tour
        self.sig_setup_finished.connect(self.show_tour_message)

        # Apply main window settings
        self.apply_settings()

        # To set all dockwidgets tabs to be on top (in case we want to do it
        # in the future)
        # self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)

        logger.info("End of MainWindow constructor")

    # --- Window setup
    def _update_shortcuts_in_panes_menu(self, show=True):
        """
        Display the shortcut for the "Switch to plugin..." on the toggle view
        action of the plugins displayed in the Help/Panes menu.

        Notes
        -----
        SpyderDockablePlugins provide two actions that function as a single
        action. The `Switch to Plugin...` action has an assignable shortcut
        via the shortcut preferences. The `Plugin toggle View` in the `View`
        application menu, uses a custom `Toggle view action` that displays the
        shortcut assigned to the `Switch to Plugin...` action, but is not
        triggered by that shortcut.
        """
        for plugin_id, plugin in self._PLUGINS.items():
            if isinstance(plugin, SpyderDockablePlugin):
                try:
                    # New API
                    action = plugin.toggle_view_action
                except AttributeError:
                    # Old API
                    action = plugin._toggle_view_action

                if show:
                    section = plugin.CONF_SECTION
                    try:
                        context = '_'
                        name = 'switch to {}'.format(section)
                        shortcut = CONF.get_shortcut(
                            context, name, plugin_name=section)
                    except (cp.NoSectionError, cp.NoOptionError):
                        shortcut = QKeySequence()
                else:
                    shortcut = QKeySequence()

                action.setShortcut(shortcut)

    def setup(self):
        """Setup main window."""
        # TODO: Remove circular dependency between help and ipython console
        # and remove this import. Help plugin should take care of it
        from spyder.plugins.help.utils.sphinxify import CSS_PATH, DARK_CSS_PATH
        logger.info("*** Start of MainWindow setup ***")
        logger.info("Updating PYTHONPATH")
        path_dict = self.get_spyder_pythonpath_dict()
        self.update_python_path(path_dict)

        logger.info("Applying theme configuration...")
        ui_theme = CONF.get('appearance', 'ui_theme')
        color_scheme = CONF.get('appearance', 'selected')

        if ui_theme == 'dark':
            if not running_under_pytest():
                # Set style proxy to fix combobox popup on mac and qdark
                qapp = QApplication.instance()
                qapp.setStyle(self._proxy_style)
            dark_qss = qdarkstyle.load_stylesheet_from_environment()
            self.setStyleSheet(dark_qss)
            self.statusBar().setStyleSheet(dark_qss)
            css_path = DARK_CSS_PATH
        elif ui_theme == 'automatic':
            if not is_dark_font_color(color_scheme):
                if not running_under_pytest():
                    # Set style proxy to fix combobox popup on mac and qdark
                    qapp = QApplication.instance()
                    qapp.setStyle(self._proxy_style)
                dark_qss = qdarkstyle.load_stylesheet_from_environment()
                self.setStyleSheet(dark_qss)
                self.statusBar().setStyleSheet(dark_qss)
                css_path = DARK_CSS_PATH
            else:
                css_path = CSS_PATH
        else:
            css_path = CSS_PATH

        # Main menu plugin
        from spyder.api.widgets.menus import SpyderMenu
        from spyder.plugins.mainmenu.plugin import MainMenu
        from spyder.plugins.mainmenu.api import (
            ApplicationMenus, HelpMenuSections, ViewMenuSections,
            ToolsMenuSections, FileMenuSections)
        self.mainmenu = MainMenu(self, configuration=CONF)
        self.register_plugin(self.mainmenu)

        # Toolbar plugin
        from spyder.plugins.toolbar.plugin import Toolbar
        self.toolbar = Toolbar(self, configuration=CONF)
        self.register_plugin(self.toolbar)

        # Preferences plugin
        from spyder.plugins.preferences.plugin import Preferences
        self.preferences = Preferences(self, configuration=CONF)
        self.register_plugin(self.preferences)

        # Shortcuts plugin
        from spyder.plugins.shortcuts.plugin import Shortcuts
        self.shortcuts = Shortcuts(self, configuration=CONF)
        self.register_plugin(self.shortcuts)

        logger.info("Creating core actions...")
        # TODO: Change registration to use MainMenus
        self.close_dockwidget_action = create_action(
            self, icon=ima.icon('close_pane'),
            text=_("Close current pane"),
            triggered=self.close_current_dockwidget,
            context=Qt.ApplicationShortcut
        )
        self.register_shortcut(self.close_dockwidget_action, "_",
                               "Close pane")
        self.lock_interface_action = create_action(
            self,
            (_("Unlock panes and toolbars") if self.interface_locked else
             _("Lock panes and toolbars")),
            icon=ima.icon('lock' if self.interface_locked else 'lock_open'),
            triggered=lambda checked:
                self.toggle_lock(not self.interface_locked),
            context=Qt.ApplicationShortcut)
        self.register_shortcut(self.lock_interface_action, "_",
                               "Lock unlock panes")
        # custom layouts shortcuts
        self.toggle_next_layout_action = create_action(self,
                                    _("Use next layout"),
                                    triggered=self.toggle_next_layout,
                                    context=Qt.ApplicationShortcut)
        self.toggle_previous_layout_action = create_action(self,
                                    _("Use previous layout"),
                                    triggered=self.toggle_previous_layout,
                                    context=Qt.ApplicationShortcut)
        self.register_shortcut(self.toggle_next_layout_action, "_",
                               "Use next layout")
        self.register_shortcut(self.toggle_previous_layout_action, "_",
                               "Use previous layout")
        # Switcher shortcuts
        self.file_switcher_action = create_action(
                                    self,
                                    _('File switcher...'),
                                    icon=ima.icon('filelist'),
                                    tip=_('Fast switch between files'),
                                    triggered=self.open_switcher,
                                    context=Qt.ApplicationShortcut)
        self.register_shortcut(self.file_switcher_action, context="_",
                               name="File switcher")
        self.symbol_finder_action = create_action(
                                    self, _('Symbol finder...'),
                                    icon=ima.icon('symbol_find'),
                                    tip=_('Fast symbol search in file'),
                                    triggered=self.open_symbolfinder,
                                    context=Qt.ApplicationShortcut)
        self.register_shortcut(self.symbol_finder_action, context="_",
                               name="symbol finder", add_shortcut_to_tip=True)
        self.file_toolbar_actions = [self.file_switcher_action,
                                     self.symbol_finder_action]

        def create_edit_action(text, tr_text, icon):
            textseq = text.split(' ')
            method_name = textseq[0].lower()+"".join(textseq[1:])
            action = create_action(self, tr_text,
                                   icon=icon,
                                   triggered=self.global_callback,
                                   data=method_name,
                                   context=Qt.WidgetShortcut)
            self.register_shortcut(action, "Editor", text)
            return action

        self.undo_action = create_edit_action('Undo', _('Undo'),
                                              ima.icon('undo'))
        self.redo_action = create_edit_action('Redo', _('Redo'),
                                              ima.icon('redo'))
        self.copy_action = create_edit_action('Copy', _('Copy'),
                                              ima.icon('editcopy'))
        self.cut_action = create_edit_action('Cut', _('Cut'),
                                             ima.icon('editcut'))
        self.paste_action = create_edit_action('Paste', _('Paste'),
                                               ima.icon('editpaste'))
        self.selectall_action = create_edit_action("Select All",
                                                   _("Select All"),
                                                   ima.icon('selectall'))

        self.edit_menu_actions = [self.undo_action, self.redo_action,
                                  None, self.cut_action, self.copy_action,
                                  self.paste_action, self.selectall_action]

        # Menus
        # TODO: Remove when all menus are migrated to use the Main Menu Plugin
        logger.info("Creating Menus...")
        mainmenu = self.mainmenu
        self.edit_menu = mainmenu.get_application_menu("edit_menu")
        self.search_menu = mainmenu.get_application_menu("search_menu")
        self.source_menu = mainmenu.get_application_menu("source_menu")
        self.source_menu.aboutToShow.connect(self.update_source_menu)
        self.run_menu = mainmenu.get_application_menu("run_menu")
        self.debug_menu = mainmenu.get_application_menu("debug_menu")
        self.consoles_menu = mainmenu.get_application_menu("consoles_menu")
        self.consoles_menu.aboutToShow.connect(
                self.update_execution_state_kernel)
        self.projects_menu = mainmenu.get_application_menu("projects_menu")
        self.projects_menu.aboutToShow.connect(self.valid_project)

        # Toolbars
        logger.info("Creating toolbars...")
        toolbar = self.toolbar
        self.file_toolbar = toolbar.get_application_toolbar("file_toolbar")
        self.run_toolbar = toolbar.get_application_toolbar("run_toolbar")
        self.debug_toolbar = toolbar.get_application_toolbar("debug_toolbar")
        self.main_toolbar = toolbar.get_application_toolbar("main_toolbar")

        # Status bar
        status = self.statusBar()
        status.setObjectName("StatusBar")
        status.showMessage(_("Welcome to Spyder!"), 5000)

        # Switcher instance
        logger.info("Loading switcher...")
        self.create_switcher()

        message = _(
            "Spyder Internal Console\n\n"
            "This console is used to report application\n"
            "internal errors and to inspect Spyder\n"
            "internals with the following commands:\n"
            "  spy.app, spy.window, dir(spy)\n\n"
            "Please don't use it to run your code\n\n"
        )
        CONF.set('internal_console', 'message', message)
        CONF.set('internal_console', 'multithreaded', self.multithreaded)
        CONF.set('internal_console', 'profile', self.profile)
        CONF.set('internal_console', 'commands', [])
        CONF.set('internal_console', 'namespace', {})
        CONF.set('internal_console', 'show_internal_errors', True)

        # Internal console plugin
        from spyder.plugins.console.plugin import Console
        self.console = Console(self, configuration=CONF)
        self.register_plugin(self.console)

        # StatusBar plugin
        from spyder.plugins.statusbar.plugin import StatusBar
        self.statusbar = StatusBar(self, configuration=CONF)
        self.register_plugin(self.statusbar)

        # Run plugin
        from spyder.plugins.run.plugin import Run
        self.run = Run(self, configuration=CONF)
        self.register_plugin(self.run)

        # Appearance plugin
        from spyder.plugins.appearance.plugin import Appearance
        self.appearance = Appearance(self, configuration=CONF)
        self.register_plugin(self.appearance)

        # Main interpreter
        from spyder.plugins.maininterpreter.plugin import MainInterpreter
        self.maininterpreter = MainInterpreter(self, configuration=CONF)
        self.register_plugin(self.maininterpreter)

        # Code completion client initialization
        from spyder.plugins.completion.plugin import CompletionPlugin
        self.completions = CompletionPlugin(self, configuration=CONF)
        self.register_plugin(self.completions)

        # Outline explorer widget
        if CONF.get('outline_explorer', 'enable'):
            self.set_splash(_("Loading outline explorer..."))
            from spyder.plugins.outlineexplorer.plugin import OutlineExplorer
            self.outlineexplorer = OutlineExplorer(self)
            self.outlineexplorer.register_plugin()
            self.add_plugin(self.outlineexplorer)

        # Editor plugin
        self.set_splash(_("Loading editor..."))
        from spyder.plugins.editor.plugin import Editor
        self.editor = Editor(self)
        self.editor.register_plugin()
        self.add_plugin(self.editor)

        self.preferences.register_plugin_preferences(self.editor)

        switcher_actions = [
            self.file_switcher_action,
            self.symbol_finder_action
        ]
        for switcher_action in switcher_actions:
            self.mainmenu.add_item_to_application_menu(
                    switcher_action,
                    menu_id=ApplicationMenus.File,
                    section=FileMenuSections.Switcher,
                    before_section=FileMenuSections.Restart)
        self.set_splash("")

        # IPython console
        self.set_splash(_("Loading IPython console..."))
        from spyder.plugins.ipythonconsole.plugin import IPythonConsole
        self.ipyconsole = IPythonConsole(self, css_path=css_path)
        self.ipyconsole.register_plugin()
        self.add_plugin(self.ipyconsole)
        self.preferences.register_plugin_preferences(self.ipyconsole)

        # Variable Explorer
        self.set_splash(_("Loading Variable Explorer..."))
        from spyder.plugins.variableexplorer.plugin import VariableExplorer
        self.variableexplorer = VariableExplorer(self, configuration=CONF)
        self.register_plugin(self.variableexplorer)

        # Help plugin
        # TODO: There is a circular dependency between help and ipython since
        # ipython console uses css_path.
        if CONF.get('help', 'enable'):
            CONF.set('help', 'css_path', css_path)
            from spyder.plugins.help.plugin import Help
            self.help = Help(self, configuration=CONF)
            self.register_plugin(self.help)

        # Application plugin
        from spyder.plugins.application.plugin import Application
        self.application = Application(self, configuration=CONF)
        self.register_plugin(self.application)

        # Tools + External Tools (some of this depends on the Application
        # plugin)
        spyder_path_action = create_action(self,
                                _("PYTHONPATH manager"),
                                None, icon=ima.icon('pythonpath'),
                                triggered=self.show_path_manager,
                                tip=_("PYTHONPATH manager"),
                                menurole=QAction.ApplicationSpecificRole)
        from spyder.plugins.application.plugin import (
            ApplicationActions, WinUserEnvDialog)
        winenv_action = None
        if WinUserEnvDialog:
            winenv_action = self.application.get_action(
                ApplicationActions.SpyderWindowsEnvVariables)
        self.mainmenu.add_item_to_application_menu(
            spyder_path_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Tools,
            before=winenv_action
        )
        if get_debug_level() >= 3:
            self.menu_lsp_logs = QMenu(_("LSP logs"))
            self.menu_lsp_logs.aboutToShow.connect(self.update_lsp_logs)
            self.mainmenu.add_item_to_application_menu(
                self.menu_lsp_logs,
                menu_id=ApplicationMenus.Tools)

        # Maximize current plugin
        self.maximize_action = create_action(self, '',
                                        triggered=self.maximize_dockwidget,
                                        context=Qt.ApplicationShortcut)
        self.register_shortcut(self.maximize_action, "_", "Maximize pane")
        self.__update_maximize_action()

        # Fullscreen mode
        self.fullscreen_action = create_action(self,
                                        _("Fullscreen mode"),
                                        triggered=self.toggle_fullscreen,
                                        context=Qt.ApplicationShortcut)
        if sys.platform == 'darwin':
            self.fullscreen_action.setEnabled(False)
            self.fullscreen_action.setToolTip(_("For fullscreen mode use "
                                               "macOS built-in feature"))
        else:
            self.register_shortcut(
                self.fullscreen_action,
                "_",
                "Fullscreen mode",
                add_shortcut_to_tip=True
            )

        # Main toolbar
        from spyder.plugins.toolbar.api import (
            ApplicationToolbars, MainToolbarSections)
        for main_layout_action in [self.maximize_action,
                                   self.fullscreen_action]:
            self.toolbar.add_item_to_application_toolbar(
                main_layout_action,
                toolbar_id=ApplicationToolbars.Main,
                section=MainToolbarSections.LayoutSection,
                before_section=MainToolbarSections.ApplicationSection)

        self.toolbar.add_item_to_application_toolbar(
            spyder_path_action,
            toolbar_id=ApplicationToolbars.Main,
            section=MainToolbarSections.ApplicationSection
        )

        # History log widget
        if CONF.get('historylog', 'enable'):
            from spyder.plugins.history.plugin import HistoryLog
            self.historylog = HistoryLog(self, configuration=CONF)
            self.register_plugin(self.historylog)

        # Figure browser
        self.set_splash(_("Loading figure browser..."))
        from spyder.plugins.plots.plugin import Plots
        self.plots = Plots(self, configuration=CONF)
        self.register_plugin(self.plots)

        # Explorer
        if CONF.get('explorer', 'enable'):
            from spyder.plugins.explorer.plugin import Explorer
            self.explorer = Explorer(self, configuration=CONF)
            self.register_plugin(self.explorer)

        # Online help widget
        if CONF.get('onlinehelp', 'enable'):
            from spyder.plugins.onlinehelp.plugin import OnlineHelp
            self.onlinehelp = OnlineHelp(self, configuration=CONF)
            self.register_plugin(self.onlinehelp)

        # Working directory plugin
        from spyder.plugins.workingdirectory.plugin import WorkingDirectory
        CONF.set('workingdir', 'init_workdir', self.init_workdir)
        self.workingdirectory = WorkingDirectory(self, configuration=CONF)
        self.register_plugin(self.workingdirectory)

        # Project explorer widget
        self.set_splash(_("Loading project explorer..."))
        from spyder.plugins.projects.plugin import Projects
        self.projects = Projects(self)
        self.projects.register_plugin()
        self.project_path = self.projects.get_pythonpath(at_start=True)
        self.add_plugin(self.projects)

        # Find in files
        if CONF.get('find_in_files', 'enable'):
            from spyder.plugins.findinfiles.plugin import FindInFiles
            self.findinfiles = FindInFiles(self, configuration=CONF)
            self.register_plugin(self.findinfiles)

        # Breakpoints
        if CONF.get('breakpoints', 'enable'):
            from spyder.plugins.breakpoints.plugin import Breakpoints
            self.breakpoints = Breakpoints(self, configuration=CONF)
            self.register_plugin(self.breakpoints)
            self.thirdparty_plugins.append(self.breakpoints)

        # Profiler plugin
        if CONF.get('profiler', 'enable'):
            from spyder.plugins.profiler.plugin import Profiler
            self.profiler = Profiler(self, configuration=CONF)
            self.register_plugin(self.profiler)
            self.thirdparty_plugins.append(self.profiler)

        # Code analysis
        if CONF.get("pylint", "enable"):
            from spyder.plugins.pylint.plugin import Pylint
            self.pylint = Pylint(self, configuration=CONF)
            self.register_plugin(self.pylint)
            self.thirdparty_plugins.append(self.pylint)

        self.set_splash(_("Loading third-party plugins..."))
        for mod in get_spyderplugins_mods():
            try:
                plugin = mod.PLUGIN_CLASS(self)
                if plugin.check_compatibility()[0]:
                    if hasattr(plugin, 'CONFIGWIDGET_CLASS'):
                        self.preferences.register_plugin_preferences(plugin)

                    if hasattr(plugin, 'COMPLETION_PROVIDER_NAME'):
                        self.completions.register_completion_plugin(plugin)
                    else:
                        self.thirdparty_plugins.append(plugin)
                        plugin.register_plugin()

                    # Add to dependencies dialog
                    module = mod.__name__
                    name = module.replace('_', '-')
                    if plugin.DESCRIPTION:
                        description = plugin.DESCRIPTION
                    else:
                        description = plugin.get_plugin_title()

                    dependencies.add(module, name, description,
                                     '', None, kind=dependencies.PLUGIN)
            except TypeError:
                # Fixes spyder-ide/spyder#13977
                pass
            except Exception as error:
                print("%s: %s" % (mod, str(error)), file=STDERR)
                traceback.print_exc(file=STDERR)

        # New API: Load and register external plugins
        external_plugins = find_external_plugins()
        plugin_deps = solve_plugin_dependencies(external_plugins.values())
        for plugin_class in plugin_deps:
            if issubclass(plugin_class, SpyderPluginV2):
                try:
                    plugin_instance = plugin_class(
                        self,
                        configuration=CONF,
                    )
                    self.register_plugin(plugin_instance, external=True)

                    # These attributes come from spyder.app.solver
                    module = plugin_class._spyder_module_name
                    package_name = plugin_class._spyder_package_name
                    version = plugin_class._spyder_version
                    description = plugin_instance.get_description()
                    dependencies.add(module, package_name, description,
                                     version, None, kind=dependencies.PLUGIN)
                except Exception as error:
                    print("%s: %s" % (plugin_class, str(error)), file=STDERR)
                    traceback.print_exc(file=STDERR)

        self.set_splash(_("Setting up main window..."))

        # Help menu
        # TODO: Once all the related plugins are migrated, and they add
        # their own actions, this can be removed.
        #----- Tours
        # TODO: Move to plugin
        self.tour = tour.AnimatedTour(self)
        # self.tours_menu = QMenu(_("Interactive tours"), self)
        # self.tour_menu_actions = []
        # # TODO: Only show intro tour for now. When we are close to finish
        # # 3.0, we will finish and show the other tour
        self.tours_available = tour.get_tours(DEFAULT_TOUR)

        for i, tour_available in enumerate(self.tours_available):
            self.tours_available[i]['last'] = 0
            tour_name = tour_available['name']

        #     def trigger(i=i, self=self):  # closure needed!
        #         return lambda: self.show_tour(i)

        #     temp_action = create_action(self, tour_name, tip="",
        #                                 triggered=trigger())
        #     self.tour_menu_actions += [temp_action]

        # self.tours_menu.addActions(self.tour_menu_actions)
        self.tour_action = create_action(
            self,
            self.tours_available[DEFAULT_TOUR]['name'],
            tip=_("Interactive tour introducing Spyder's panes and features"),
            triggered=lambda: self.show_tour(DEFAULT_TOUR))
        self.mainmenu.add_item_to_application_menu(
            self.tour_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.Documentation)

        # TODO: Move to plugin

        # IPython documentation
        if self.help is not None:
            self.ipython_menu = SpyderMenu(
                parent=self,
                title=_("IPython documentation"))
            intro_action = create_action(
                self,
                _("Intro to IPython"),
                triggered=self.ipyconsole.show_intro)
            quickref_action = create_action(
                self,
                _("Quick reference"),
                triggered=self.ipyconsole.show_quickref)
            guiref_action = create_action(
                self,
                _("Console help"),
                triggered=self.ipyconsole.show_guiref)
            add_actions(
                self.ipython_menu,
                (intro_action, guiref_action, quickref_action))
            self.mainmenu.add_item_to_application_menu(
                self.ipython_menu,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.ExternalDocumentation,
                before_section=HelpMenuSections.About)

        # ----- View
        # View menu
        # Menus
        self.plugins_menu = SpyderMenu(parent=self, title=_("Panes"))
        self.quick_layout_menu = SpyderMenu(
            parent=self,
            title=_("Window layouts"))
        self.quick_layout_set_menu()

        # Panes section
        self.mainmenu.add_item_to_application_menu(
                self.plugins_menu,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Pane)
        self.mainmenu.add_item_to_application_menu(
                self.lock_interface_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Pane)
        self.mainmenu.add_item_to_application_menu(
                self.close_dockwidget_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Pane)
        self.mainmenu.add_item_to_application_menu(
                self.maximize_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Pane)
        # Toolbar section
        self.mainmenu.add_item_to_application_menu(
                self.toolbar.toolbars_menu,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Toolbar)
        self.mainmenu.add_item_to_application_menu(
                self.toolbar.show_toolbars_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Toolbar)
        # Layout section
        self.mainmenu.add_item_to_application_menu(
                self.quick_layout_menu,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Layout)
        self.mainmenu.add_item_to_application_menu(
                self.toggle_previous_layout_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Layout)
        self.mainmenu.add_item_to_application_menu(
                self.toggle_next_layout_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Layout)
        # Bottom section
        self.mainmenu.add_item_to_application_menu(
                self.fullscreen_action,
                menu_id=ApplicationMenus.View,
                section=ViewMenuSections.Bottom)

        # TODO: Migrate to use the MainMenu Plugin instead of list of actions
        # Filling out menu/toolbar entries:
        add_actions(self.edit_menu, self.edit_menu_actions)
        add_actions(self.search_menu, self.search_menu_actions)
        add_actions(self.source_menu, self.source_menu_actions)
        add_actions(self.run_menu, self.run_menu_actions)
        add_actions(self.debug_menu, self.debug_menu_actions)
        add_actions(self.consoles_menu, self.consoles_menu_actions)
        add_actions(self.projects_menu, self.projects_menu_actions)

        # Emitting the signal notifying plugins that main window menu and
        # toolbar actions are all defined:
        self.all_actions_defined.emit()

        # Window set-up
        logger.info("Setting up window...")
        self.setup_layout(default=False)

        # Menu about to show
        for child in self.menuBar().children():
            if isinstance(child, QMenu):
                try:
                    child.aboutToShow.connect(self.update_edit_menu)
                    child.aboutToShow.connect(self.update_search_menu)
                except TypeError:
                    pass

        logger.info("*** End of MainWindow setup ***")
        self.is_starting_up = False

        for plugin, plugin_instance in self._EXTERNAL_PLUGINS.items():
            if isinstance(plugin, SpyderDockablePlugin):
                self.tabify_plugin(plugin_instance)
                plugin_instance.toggle_view(False)

    def update_lsp_logs(self):
        """Create an action for each lsp log file."""
        self.menu_lsp_logs.clear()
        lsp_logs = []
        regex = re.compile(r'.*_.*_(\d+)[.]log')
        files = glob.glob(osp.join(get_conf_path('lsp_logs'), '*.log'))
        for f in files:
            action = create_action(self, f, triggered=self.editor.load)
            action.setData(f)
            lsp_logs.append(action)
        add_actions(self.menu_lsp_logs, lsp_logs)

    def post_visible_setup(self):
        """Actions to be performed only after the main window's `show` method
        was triggered"""
        for __, plugin in self._PLUGINS.items():
            try:
                plugin.on_mainwindow_visible()
            except AttributeError:
                pass

        self.restore_scrollbar_position.emit()

        logger.info('Deleting previous Spyder instance LSP logs...')
        delete_lsp_log_files()

        # Workaround for spyder-ide/spyder#880.
        # QDockWidget objects are not painted if restored as floating
        # windows, so we must dock them before showing the mainwindow,
        # then set them again as floating windows here.
        for widget in self.floating_dockwidgets:
            widget.setFloating(True)

        # Server to maintain just one Spyder instance and open files in it if
        # the user tries to start other instances with
        # $ spyder foo.py
        if (CONF.get('main', 'single_instance') and not self.new_instance
                and self.open_files_server):
            t = threading.Thread(target=self.start_open_files_server)
            t.setDaemon(True)
            t.start()

            # Connect the window to the signal emitted by the previous server
            # when it gets a client connected to it
            self.sig_open_external_file.connect(self.open_external_file)

        # Create Plugins and toolbars submenus
        self.create_plugins_menu()

        # Update lock status
        self.toggle_lock(self.interface_locked)

        # Hide Internal Console so that people don't use it instead of
        # the External or IPython ones
        if self.console.dockwidget.isVisible() and DEV is None:
            self.console.toggle_view_action.setChecked(False)
            self.console.dockwidget.hide()

        # Show Help and Consoles by default
        plugins_to_show = [self.ipyconsole]
        if self.help is not None:
            plugins_to_show.append(self.help)
        for plugin in plugins_to_show:
            if plugin.dockwidget.isVisible():
                plugin.dockwidget.raise_()

        # Show history file if no console is visible
        if not self.ipyconsole._isvisible:
            self.historylog.add_history(get_conf_path('history.py'))

        # Process pending events and hide splash before loading the
        # previous session.
        QApplication.processEvents()
        if self.splash is not None:
            self.splash.hide()

        if self.open_project:
            if not running_in_mac_app():
                self.projects.open_project(
                    self.open_project, workdir=self.init_workdir
                )
        else:
            # Load last project if a project was active when Spyder
            # was closed
            self.projects.reopen_last_project()

            # If no project is active, load last session
            if self.projects.get_active_project() is None:
                self.editor.setup_open_files(close_previous_files=False)

        # Connect Editor debug action with Console
        self.ipyconsole.sig_pdb_state.connect(self.editor.update_pdb_state)

        # Raise the menuBar to the top of the main window widget's stack
        # Fixes spyder-ide/spyder#3887.
        self.menuBar().raise_()

        # Handle DPI scale and window changes to show a restart message.
        # Don't activate this functionality on macOS because it's being
        # triggered in the wrong situations.
        # See spyder-ide/spyder#11846
        if not sys.platform == 'darwin':
            window = self.window().windowHandle()
            window.screenChanged.connect(self.handle_new_screen)
            screen = self.window().windowHandle().screen()
            self.current_dpi = screen.logicalDotsPerInch()
            screen.logicalDotsPerInchChanged.connect(
                self.show_dpi_change_message)

        # Notify that the setup of the mainwindow was finished
        self.is_setting_up = False
        self.sig_setup_finished.emit()

    def handle_new_screen(self, new_screen):
        """Connect DPI signals for new screen."""
        if new_screen is not None:
            new_screen_dpi = new_screen.logicalDotsPerInch()
            if self.current_dpi != new_screen_dpi:
                self.show_dpi_change_message(new_screen_dpi)
            else:
                new_screen.logicalDotsPerInchChanged.connect(
                    self.show_dpi_change_message)

    def handle_dpi_change_response(self, result, dpi):
        """Handle dpi change message dialog result."""
        if self.dpi_change_dismiss_box.isChecked():
            self.show_dpi_message = False
            self.dpi_change_dismiss_box = None
        if result == 0:  # Restart button was clicked
            # Activate HDPI auto-scaling option since is needed for a
            # proper display when using OS scaling
            CONF.set('main', 'normal_screen_resolution', False)
            CONF.set('main', 'high_dpi_scaling', True)
            CONF.set('main', 'high_dpi_custom_scale_factor', False)
            self.restart()
        else:
            # Update current dpi for future checks
            self.current_dpi = dpi

    def show_dpi_change_message(self, dpi):
        """Show message to restart Spyder since the DPI scale changed."""
        if not self.show_dpi_message:
            return

        if self.current_dpi != dpi:
            # Check the window state to not show the message if the window
            # is in fullscreen mode.
            window = self.window().windowHandle()
            if (window.windowState() == Qt.WindowFullScreen and
                    sys.platform == 'darwin'):
                return

            self.dpi_change_dismiss_box = QCheckBox(
                _("Hide this message during the current session"),
                self
            )

            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setText(
                _
                ("A monitor scale change was detected. <br><br>"
                 "We recommend restarting Spyder to ensure that it's properly "
                 "displayed. If you don't want to do that, please be sure to "
                 "activate the option<br><br><tt>Enable auto high DPI scaling"
                 "</tt><br><br>in <tt>Preferences > General > Interface</tt>, "
                 "in case Spyder is not displayed correctly.<br><br>"
                 "Do you want to restart Spyder?"))
            msgbox.addButton(_('Restart now'), QMessageBox.NoRole)
            dismiss_button = msgbox.addButton(
                _('Dismiss'), QMessageBox.NoRole)
            msgbox.setCheckBox(self.dpi_change_dismiss_box)
            msgbox.setDefaultButton(dismiss_button)
            msgbox.finished.connect(
                lambda result: self.handle_dpi_change_response(result, dpi))
            msgbox.open()

    def set_window_title(self):
        """Set window title."""
        if DEV is not None:
            title = u"Spyder %s (Python %s.%s)" % (__version__,
                                                   sys.version_info[0],
                                                   sys.version_info[1])
        elif running_in_mac_app() or is_pynsist():
            title = "Spyder"
        else:
            title = u"Spyder (Python %s.%s)" % (sys.version_info[0],
                                                sys.version_info[1])

        if get_debug_level():
            title += u" [DEBUG MODE %d]" % get_debug_level()

        if self.window_title is not None:
            title += u' -- ' + to_text_string(self.window_title)

        if self.projects is not None:
            path = self.projects.get_active_project_path()
            if path:
                path = path.replace(get_home_dir(), u'~')
                title = u'{0} - {1}'.format(path, title)

        self.base_title = title
        self.setWindowTitle(self.base_title)

    def load_window_settings(self, prefix, default=False, section='main'):
        """
        Load window layout settings from userconfig-based configuration
        with `prefix`, under `section`.

        Parameters
        ----------
        default: bool
            If True, do not restore inner layout.
        """
        get_func = CONF.get_default if default else CONF.get
        window_size = get_func(section, prefix + 'size')
        prefs_dialog_size = get_func(section, prefix + 'prefs_dialog_size')
        if default:
            hexstate = None
        else:
            hexstate = get_func(section, prefix + 'state', None)

        pos = get_func(section, prefix + 'position')

        # It's necessary to verify if the window/position value is valid
        # with the current screen. See spyder-ide/spyder#3748.
        width = pos[0]
        height = pos[1]
        screen_shape = QApplication.desktop().geometry()
        current_width = screen_shape.width()
        current_height = screen_shape.height()
        if current_width < width or current_height < height:
            pos = CONF.get_default(section, prefix + 'position')

        is_maximized = get_func(section, prefix + 'is_maximized')
        is_fullscreen = get_func(section, prefix + 'is_fullscreen')
        return (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
                is_fullscreen)

    def get_window_settings(self):
        """
        Return current window settings.

        Symmetric to the 'set_window_settings' setter.
        """
        window_size = (self.window_size.width(), self.window_size.height())
        is_fullscreen = self.isFullScreen()
        if is_fullscreen:
            is_maximized = self.maximized_flag
        else:
            is_maximized = self.isMaximized()
        pos = (self.window_position.x(), self.window_position.y())
        prefs_dialog_size = (self.prefs_dialog_size.width(),
                             self.prefs_dialog_size.height())
        hexstate = qbytearray_to_str(self.saveState(version=2))
        return (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
                is_fullscreen)

    def set_window_settings(self, hexstate, window_size, prefs_dialog_size,
                            pos, is_maximized, is_fullscreen):
        """
        Set window settings.

        Symmetric to the 'get_window_settings' accessor.
        """
        self.setUpdatesEnabled(False)
        self.window_size = QSize(window_size[0], window_size[1]) # width,height
        self.prefs_dialog_size = QSize(prefs_dialog_size[0],
                                       prefs_dialog_size[1]) # width,height
        self.window_position = QPoint(pos[0], pos[1]) # x,y
        self.setWindowState(Qt.WindowNoState)
        self.resize(self.window_size)
        self.move(self.window_position)

        # Window layout
        if hexstate:
            hexstate_valid = self.restoreState(
                QByteArray().fromHex(str(hexstate).encode('utf-8')),
                version=2
            )

            # Check layout validity. Spyder 4 uses the version 1 state,
            # whereas Spyder 5 will use version 2 state. For more info see the
            # version argument for QMainWindow.restoreState:
            # https://doc.qt.io/qt-5/qmainwindow.html#restoreState
            if not hexstate_valid:
                self.setUpdatesEnabled(True)
                self.setup_layout(default=True)
                return
            # Workaround for spyder-ide/spyder#880.
            # QDockWidget objects are not painted if restored as floating
            # windows, so we must dock them before showing the mainwindow.
            for widget in self.children():
                if isinstance(widget, QDockWidget) and widget.isFloating():
                    self.floating_dockwidgets.append(widget)
                    widget.setFloating(False)

        # Is fullscreen?
        if is_fullscreen:
            self.setWindowState(Qt.WindowFullScreen)
        self.__update_fullscreen_action()

        # Is maximized?
        if is_fullscreen:
            self.maximized_flag = is_maximized
        elif is_maximized:
            self.setWindowState(Qt.WindowMaximized)
        self.setUpdatesEnabled(True)

    def save_current_window_settings(self, prefix, section='main',
                                     none_state=False):
        """
        Save current window settings with `prefix` in
        the userconfig-based configuration, under `section`.
        """
        # Use current size and position when saving window settings.
        # Fixes spyder-ide/spyder#13882
        win_size = self.size()
        pos = self.pos()
        prefs_size = self.prefs_dialog_size

        CONF.set(section, prefix + 'size',
                 (win_size.width(), win_size.height()))
        CONF.set(section, prefix + 'prefs_dialog_size',
                 (prefs_size.width(), prefs_size.height()))
        CONF.set(section, prefix + 'is_maximized', self.isMaximized())
        CONF.set(section, prefix + 'is_fullscreen', self.isFullScreen())
        CONF.set(section, prefix + 'position', (pos.x(), pos.y()))
        self.maximize_dockwidget(restore=True)# Restore non-maximized layout
        if none_state:
            CONF.set(section, prefix + 'state', None)
        else:
            qba = self.saveState()
            CONF.set(section, prefix + 'state', qbytearray_to_str(qba))
        CONF.set(section, prefix + 'statusbar',
                 not self.statusBar().isHidden())

    def tabify_plugins(self, first, second):
        """Tabify plugin dockwidgets"""
        self.tabifyDockWidget(first.dockwidget, second.dockwidget)

    # --- Layouts
    def setup_layout(self, default=False):
        """Setup window layout"""
        prefix = 'window' + '/'
        settings = self.load_window_settings(prefix, default)
        hexstate = settings[0]

        self.first_spyder_run = False
        if hexstate is None:
            # First Spyder execution:
            self.setWindowState(Qt.WindowMaximized)
            self.first_spyder_run = True
            self.setup_default_layouts('default', settings)

            # Now that the initial setup is done, copy the window settings,
            # except for the hexstate in the quick layouts sections for the
            # default layouts.
            # Order and name of the default layouts is found in config.py
            section = 'quick_layouts'
            get_func = CONF.get_default if default else CONF.get
            order = get_func(section, 'order')

            # restore the original defaults if reset layouts is called
            if default:
                CONF.set(section, 'active', order)
                CONF.set(section, 'order', order)
                CONF.set(section, 'names', order)

            for index, name, in enumerate(order):
                prefix = 'layout_{0}/'.format(index)
                self.save_current_window_settings(prefix, section,
                                                  none_state=True)

            # store the initial layout as the default in spyder
            prefix = 'layout_default/'
            section = 'quick_layouts'
            self.save_current_window_settings(prefix, section, none_state=True)
            self.current_quick_layout = 'default'

            # Regenerate menu
            self.quick_layout_set_menu()

        self.set_window_settings(*settings)

        # Old API
        for plugin in (self.widgetlist + self.thirdparty_plugins):
            try:
                plugin._initialize_plugin_in_mainwindow_layout()
            except AttributeError:
                pass
            except Exception as error:
                print("%s: %s" % (plugin, str(error)), file=STDERR)
                traceback.print_exc(file=STDERR)

    def setup_default_layouts(self, index, settings):
        """Setup default layouts when run for the first time."""
        self.setUpdatesEnabled(False)

        first_spyder_run = bool(self.first_spyder_run)  # Store copy

        if first_spyder_run:
            self.set_window_settings(*settings)
        else:
            if self.last_plugin:
                if self.last_plugin._ismaximized:
                    self.maximize_dockwidget(restore=True)

            if not (self.isMaximized() or self.maximized_flag):
                self.showMaximized()

            min_width = self.minimumWidth()
            max_width = self.maximumWidth()
            base_width = self.width()
            self.setFixedWidth(base_width)

        # IMPORTANT: order has to be the same as defined in the config file
        MATLAB, RSTUDIO, VERTICAL, HORIZONTAL = range(self.DEFAULT_LAYOUTS)

        # Define widgets locally
        editor = self.editor
        console_ipy = self.ipyconsole
        console_int = self.console
        outline = self.outlineexplorer
        explorer_project = self.projects
        explorer_file = self.explorer
        explorer_variable = self.variableexplorer
        plots = self.plots
        history = self.historylog
        finder = self.findinfiles
        help_plugin = self.help
        helper = self.onlinehelp
        plugins = self.thirdparty_plugins

        # Stored for tests
        global_hidden_widgets = [finder, console_int, explorer_project,
                                 helper] + plugins
        # Layout definition
        # --------------------------------------------------------------------
        # Layouts are organized by columns, each column is organized by rows.
        # Widths have to accumulate to 100 (except if hidden), height per
        # column has to accumulate to 100 as well

        # Spyder Default Initial Layout
        s_layout = {
            'widgets': [
                # Column 0
                [[explorer_project]],
                # Column 1
                [[editor]],
                # Column 2
                [[outline]],
                # Column 3
                [[help_plugin, explorer_variable, plots,     # Row 0
                  helper, explorer_file, finder] + plugins,
                 [console_int, console_ipy, history]]        # Row 1
                ],
            'width fraction': [15,            # Column 0 width
                               45,            # Column 1 width
                                5,            # Column 2 width
                               45],           # Column 3 width
            'height fraction': [[100],          # Column 0, row heights
                                [100],          # Column 1, row heights
                                [100],          # Column 2, row heights
                                [46, 54]],  # Column 3, row heights
            'hidden widgets': [outline] + global_hidden_widgets,
            'hidden toolbars': [],
        }

        # RStudio
        r_layout = {
            'widgets': [
                # column 0
                [[editor],                            # Row 0
                 [console_ipy, console_int]],         # Row 1
                # column 1
                [[explorer_variable, plots, history,  # Row 0
                  outline, finder] + plugins,
                 [explorer_file, explorer_project,    # Row 1
                  help_plugin, helper]]
                ],
            'width fraction': [55,            # Column 0 width
                               45],           # Column 1 width
            'height fraction': [[55, 45],   # Column 0, row heights
                                [55, 45]],  # Column 1, row heights
            'hidden widgets': [outline] + global_hidden_widgets,
            'hidden toolbars': [],
        }

        # Matlab
        m_layout = {
            'widgets': [
                # column 0
                [[explorer_file, explorer_project],
                 [outline]],
                # column 1
                [[editor],
                 [console_ipy, console_int]],
                # column 2
                [[explorer_variable, plots, finder] + plugins,
                 [history, help_plugin, helper]]
                ],
            'width fraction': [10,            # Column 0 width
                               45,            # Column 1 width
                               45],           # Column 2 width
            'height fraction': [[55, 45],   # Column 0, row heights
                                [55, 45],   # Column 1, row heights
                                [55, 45]],  # Column 2, row heights
            'hidden widgets': global_hidden_widgets,
            'hidden toolbars': [],
        }

        # Vertically split
        v_layout = {
            'widgets': [
                # column 0
                [[editor],                                  # Row 0
                 [console_ipy, console_int, explorer_file,  # Row 1
                  explorer_project, help_plugin, explorer_variable, plots,
                  history, outline, finder, helper] + plugins]
                ],
            'width fraction': [100],            # Column 0 width
            'height fraction': [[55, 45]],  # Column 0, row heights
            'hidden widgets': [outline] + global_hidden_widgets,
            'hidden toolbars': [],
        }

        # Horizontally split
        h_layout = {
            'widgets': [
                # column 0
                [[editor]],                                 # Row 0
                # column 1
                [[console_ipy, console_int, explorer_file,  # Row 0
                  explorer_project, help_plugin, explorer_variable, plots,
                  history, outline, finder, helper] + plugins]
                ],
            'width fraction': [55,      # Column 0 width
                               45],     # Column 1 width
            'height fraction': [[100],    # Column 0, row heights
                                [100]],   # Column 1, row heights
            'hidden widgets': [outline] + global_hidden_widgets,
            'hidden toolbars': []
        }

        # Layout selection
        layouts = {
            'default': s_layout,
            RSTUDIO: r_layout,
            MATLAB: m_layout,
            VERTICAL: v_layout,
            HORIZONTAL: h_layout,
        }

        layout = layouts[index]

        # Remove None from widgets layout
        widgets_layout = layout['widgets']
        widgets_layout_clean = []
        for column in widgets_layout:
            clean_col = []
            for row in column:
                clean_row = [w for w in row if w is not None]
                if clean_row:
                    clean_col.append(clean_row)
            if clean_col:
                widgets_layout_clean.append(clean_col)

        # Flatten widgets list
        widgets = []
        for column in widgets_layout_clean:
            for row in column:
                for widget in row:
                    widgets.append(widget)

        # We use both directions to ensure proper update when moving from
        # 'Horizontal Split' to 'Spyder Default'
        # This also seems to help on random cases where the display seems
        # 'empty'
        for direction in (Qt.Vertical, Qt.Horizontal):
            # Arrange the widgets in one direction
            for idx in range(len(widgets) - 1):
                first, second = widgets[idx], widgets[idx+1]
                if first is not None and second is not None:
                    self.splitDockWidget(first.dockwidget, second.dockwidget,
                                         direction)

        # Arrange the widgets in the other direction
        for column in widgets_layout_clean:
            for idx in range(len(column) - 1):
                first_row, second_row = column[idx], column[idx+1]
                self.splitDockWidget(first_row[0].dockwidget,
                                     second_row[0].dockwidget,
                                     Qt.Vertical)

        # Tabify
        for column in widgets_layout_clean:
            for row in column:
                for idx in range(len(row) - 1):
                    first, second = row[idx], row[idx+1]
                    self.tabify_plugins(first, second)

                # Raise front widget per row
                row[0].dockwidget.show()
                row[0].dockwidget.raise_()

        # Set dockwidget widths
        width_fractions = layout['width fraction']
        if len(width_fractions) > 1:
            _widgets = [col[0][0].dockwidget for col in widgets_layout]
            self.resizeDocks(_widgets, width_fractions, Qt.Horizontal)

        # Set dockwidget heights
        height_fractions = layout['height fraction']
        for idx, column in enumerate(widgets_layout_clean):
            if len(column) > 1:
                _widgets = [row[0].dockwidget for row in column]
                self.resizeDocks(_widgets, height_fractions[idx], Qt.Vertical)

        # Hide toolbars
        hidden_toolbars = layout['hidden toolbars']
        for toolbar in hidden_toolbars:
            if toolbar is not None:
                toolbar.close()

        # Hide widgets
        hidden_widgets = layout['hidden widgets']
        for widget in hidden_widgets:
            if widget is not None:
                widget.dockwidget.close()

        if first_spyder_run:
            self.first_spyder_run = False
        else:
            self.setMinimumWidth(min_width)
            self.setMaximumWidth(max_width)

            if not (self.isMaximized() or self.maximized_flag):
                self.showMaximized()

        self.setUpdatesEnabled(True)
        self.sig_layout_setup_ready.emit(layout)

        return layout

    @Slot()
    def toggle_previous_layout(self):
        """ """
        self.toggle_layout('previous')

    @Slot()
    def toggle_next_layout(self):
        """ """
        self.toggle_layout('next')

    def toggle_layout(self, direction='next'):
        names = CONF.get('quick_layouts', 'names')
        order = CONF.get('quick_layouts', 'order')
        active = CONF.get('quick_layouts', 'active')

        if len(active) == 0:
            return

        layout_index = ['default']
        for name in order:
            if name in active:
                layout_index.append(names.index(name))

        current_layout = self.current_quick_layout
        dic = {'next': 1, 'previous': -1}

        if current_layout is None:
            # Start from default
            current_layout = 'default'

        if current_layout in layout_index:
            current_index = layout_index.index(current_layout)
        else:
            current_index = 0

        new_index = (current_index + dic[direction]) % len(layout_index)
        self.quick_layout_switch(layout_index[new_index])

    def quick_layout_set_menu(self):
        names = CONF.get('quick_layouts', 'names')
        order = CONF.get('quick_layouts', 'order')
        active = CONF.get('quick_layouts', 'active')

        ql_actions = []

        ql_actions = [create_action(self, _('Spyder Default Layout'),
                                    triggered=lambda:
                                    self.quick_layout_switch('default'))]
        for name in order:
            if name in active:
                index = names.index(name)

                # closure required so lambda works with the default parameter
                def trigger(i=index, self=self):
                    return lambda: self.quick_layout_switch(i)

                qli_act = create_action(self, name, triggered=trigger())
                # closure above replaces the following which stopped working
                # qli_act = create_action(self, name, triggered=lambda i=index:
                #     self.quick_layout_switch(i)

                ql_actions += [qli_act]

        self.ql_save = create_action(self, _("Save current layout"),
                                     triggered=lambda:
                                     self.quick_layout_save(),
                                     context=Qt.ApplicationShortcut)
        self.ql_preferences = create_action(self, _("Layout preferences"),
                                            triggered=lambda:
                                            self.quick_layout_settings(),
                                            context=Qt.ApplicationShortcut)
        self.ql_reset = create_action(self, _('Reset to spyder default'),
                                      triggered=self.reset_window_layout)

        self.register_shortcut(self.ql_save, "_", "Save current layout")
        self.register_shortcut(self.ql_preferences, "_", "Layout preferences")

        ql_actions += [None]
        ql_actions += [self.ql_save, self.ql_preferences, self.ql_reset]

        self.quick_layout_menu.clear()
        add_actions(self.quick_layout_menu, ql_actions)

        if len(order) == 0:
            self.ql_preferences.setEnabled(False)
        else:
            self.ql_preferences.setEnabled(True)

    @Slot()
    def reset_window_layout(self):
        """Reset window layout to default"""
        answer = QMessageBox.warning(self, _("Warning"),
                     _("Window layout will be reset to default settings: "
                       "this affects window position, size and dockwidgets.\n"
                       "Do you want to continue?"),
                     QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.setup_layout(default=True)

    def quick_layout_save(self):
        """Save layout dialog"""
        names = CONF.get('quick_layouts', 'names')
        order = CONF.get('quick_layouts', 'order')
        active = CONF.get('quick_layouts', 'active')

        dlg = self.dialog_layout_save(self, names)

        if dlg.exec_():
            name = dlg.combo_box.currentText()

            if name in names:
                answer = QMessageBox.warning(
                    self,
                    _("Warning"),
                    _("<b>%s</b> will be overwritten. Do you want to "
                      "continue?") % name,
                    QMessageBox.Yes | QMessageBox.No
                )
                index = order.index(name)
            else:
                answer = True
                if None in names:
                    index = names.index(None)
                    names[index] = name
                else:
                    index = len(names)
                    names.append(name)
                order.append(name)

            # Always make active a new layout even if it overwrites an inactive
            # layout
            if name not in active:
                active.append(name)

            if answer:
                self.save_current_window_settings('layout_{}/'.format(index),
                                                  section='quick_layouts')
                CONF.set('quick_layouts', 'names', names)
                CONF.set('quick_layouts', 'order', order)
                CONF.set('quick_layouts', 'active', active)
                self.quick_layout_set_menu()

    def quick_layout_settings(self):
        """Layout settings dialog"""
        section = 'quick_layouts'
        names = CONF.get(section, 'names')
        order = CONF.get(section, 'order')
        active = CONF.get(section, 'active')

        dlg = self.dialog_layout_settings(self, names, order, active)
        if dlg.exec_():
            CONF.set(section, 'names', dlg.names)
            CONF.set(section, 'order', dlg.order)
            CONF.set(section, 'active', dlg.active)
            self.quick_layout_set_menu()

    def quick_layout_switch(self, index):
        """Switch to quick layout number *index*"""
        section = 'quick_layouts'

        try:
            settings = self.load_window_settings('layout_{}/'.format(index),
                                                 section=section)
            (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
             is_fullscreen) = settings

            # The default layouts will always be regenerated unless there was
            # an overwrite, either by rewriting with same name, or by deleting
            # and then creating a new one
            if hexstate is None:
                # The value for hexstate shouldn't be None for a custom saved
                # layout (ie, where the index is greater than the number of
                # defaults).  See spyder-ide/spyder#6202.
                if index != 'default' and index >= self.DEFAULT_LAYOUTS:
                    QMessageBox.critical(
                            self, _("Warning"),
                            _("Error opening the custom layout.  Please close"
                              " Spyder and try again.  If the issue persists,"
                              " then you must use 'Reset to Spyder default' "
                              "from the layout menu."))
                    return
                self.setup_default_layouts(index, settings)
        except cp.NoOptionError:
            QMessageBox.critical(self, _("Warning"),
                                 _("Quick switch layout #%s has not yet "
                                   "been defined.") % str(index))
            return
        self.set_window_settings(*settings)
        self.current_quick_layout = index

        # make sure the flags are correctly set for visible panes
        for plugin in (self.widgetlist + self.thirdparty_plugins):
            try:
                action = plugin._toggle_view_action
            except AttributeError:
                # New API
                action = plugin.toggle_view_action
            action.setChecked(plugin.dockwidget.isVisible())

    # TODO: To be removed after all actions are moved to their corresponding
    # plugins
    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_shortcut_to_tip=True, plugin_name=None):
        self.shortcuts.register_shortcut(
            qaction_or_qshortcut,
            context,
            name,
            add_shortcut_to_tip=add_shortcut_to_tip,
            plugin_name=plugin_name,
        )

    # --- Other
    def update_execution_state_kernel(self):
        """Handle execution state of the current console."""
        try:
            self.ipyconsole.update_execution_state_kernel()
        except AttributeError:
            return

    def valid_project(self):
        """Handle an invalid active project."""
        try:
            path = self.projects.get_active_project_path()
        except AttributeError:
            return

        if bool(path):
            if not self.projects.is_valid_project(path):
                if path:
                    QMessageBox.critical(
                        self,
                        _('Error'),
                        _("<b>{}</b> is no longer a valid Spyder project! "
                          "Since it is the current active project, it will "
                          "be closed automatically.").format(path))
                self.projects.close_project()

    def update_source_menu(self):
        """Update source menu options that vary dynamically."""
        # This is necessary to avoid an error at startup.
        # Fixes spyder-ide/spyder#14901
        try:
            self.editor.refresh_formatter_name()
        except AttributeError:
            pass

    def free_memory(self):
        """Free memory after event."""
        gc.collect()

    def plugin_focus_changed(self):
        """Focus has changed from one plugin to another"""
        self.update_edit_menu()
        self.update_search_menu()

    def show_shortcuts(self, menu):
        """Show action shortcuts in menu."""
        menu_actions = menu.actions()
        for action in menu_actions:
            if getattr(action, '_shown_shortcut', False):
                # This is a SpyderAction
                if action._shown_shortcut is not None:
                    action.setShortcut(action._shown_shortcut)
            elif action.menu() is not None:
                # This is submenu, so we need to call this again
                self.show_shortcuts(action.menu())
            else:
                # We don't need to do anything for other elements
                continue

    def hide_shortcuts(self, menu):
        """Hide action shortcuts in menu."""
        menu_actions = menu.actions()
        for action in menu_actions:
            if getattr(action, '_shown_shortcut', False):
                # This is a SpyderAction
                if action._shown_shortcut is not None:
                    action.setShortcut(QKeySequence())
            elif action.menu() is not None:
                # This is submenu, so we need to call this again
                self.hide_shortcuts(action.menu())
            else:
                # We don't need to do anything for other elements
                continue

    def hide_options_menus(self):
        """Hide options menu when menubar is pressed in macOS."""
        for plugin in self.widgetlist + self.thirdparty_plugins:
            if plugin.CONF_SECTION == 'editor':
                editorstack = self.editor.get_current_editorstack()
                editorstack.menu.hide()
            else:
                try:
                    # New API
                    plugin.options_menu.hide()
                except AttributeError:
                    # Old API
                    plugin._options_menu.hide()

    def get_focus_widget_properties(self):
        """Get properties of focus widget
        Returns tuple (widget, properties) where properties is a tuple of
        booleans: (is_console, not_readonly, readwrite_editor)"""
        from spyder.plugins.editor.widgets.base import TextEditBaseWidget
        from spyder.plugins.ipythonconsole.widgets import ControlWidget
        widget = QApplication.focusWidget()

        textedit_properties = None
        if isinstance(widget, (TextEditBaseWidget, ControlWidget)):
            console = isinstance(widget, ControlWidget)
            not_readonly = not widget.isReadOnly()
            readwrite_editor = not_readonly and not console
            textedit_properties = (console, not_readonly, readwrite_editor)
        return widget, textedit_properties

    def update_edit_menu(self):
        """Update edit menu"""
        widget, textedit_properties = self.get_focus_widget_properties()
        if textedit_properties is None: # widget is not an editor/console
            return
        # !!! Below this line, widget is expected to be a QPlainTextEdit
        #     instance
        console, not_readonly, readwrite_editor = textedit_properties

        # Editor has focus and there is no file opened in it
        if (not console and not_readonly and self.editor
                and not self.editor.is_file_opened()):
            return

        # Disabling all actions to begin with
        for child in self.edit_menu.actions():
            child.setEnabled(False)

        self.selectall_action.setEnabled(True)

        # Undo, redo
        self.undo_action.setEnabled( readwrite_editor \
                                     and widget.document().isUndoAvailable() )
        self.redo_action.setEnabled( readwrite_editor \
                                     and widget.document().isRedoAvailable() )

        # Copy, cut, paste, delete
        has_selection = widget.has_selected_text()
        self.copy_action.setEnabled(has_selection)
        self.cut_action.setEnabled(has_selection and not_readonly)
        self.paste_action.setEnabled(not_readonly)

        # Comment, uncomment, indent, unindent...
        if not console and not_readonly:
            # This is the editor and current file is writable
            if self.editor:
                for action in self.editor.edit_menu_actions:
                    action.setEnabled(True)

    def update_search_menu(self):
        """Update search menu"""
        # Disabling all actions except the last one
        # (which is Find in files) to begin with
        for child in self.search_menu.actions()[:-1]:
            child.setEnabled(False)

        widget, textedit_properties = self.get_focus_widget_properties()
        if textedit_properties is None: # widget is not an editor/console
            return

        # !!! Below this line, widget is expected to be a QPlainTextEdit
        #     instance
        console, not_readonly, readwrite_editor = textedit_properties

        # Find actions only trigger an effect in the Editor
        if not console:
            for action in self.search_menu.actions():
                try:
                    action.setEnabled(True)
                except RuntimeError:
                    pass

        # Disable the replace action for read-only files
        if len(self.search_menu_actions) > 3:
            self.search_menu_actions[3].setEnabled(readwrite_editor)

    def create_plugins_menu(self):
        order = ['editor', 'ipython_console', 'variable_explorer',
                 'help', 'plots', None, 'explorer', 'outline_explorer',
                 'project_explorer', 'find_in_files', None, 'historylog',
                 'profiler', 'breakpoints', 'pylint', None,
                 'onlinehelp', 'internal_console', None]

        for plugin in self.widgetlist:
            try:
                # New API
                action = plugin.toggle_view_action
            except AttributeError:
                # Old API
                action = plugin._toggle_view_action

            if action:
                action.setChecked(plugin.dockwidget.isVisible())

            try:
                name = plugin.CONF_SECTION
                pos = order.index(name)
            except ValueError:
                pos = None

            if pos is not None:
                order[pos] = action
            else:
                order.append(action)

        actions = order[:]
        for action in order:
            if type(action) is str:
                actions.remove(action)

        self.plugins_menu_actions = actions
        add_actions(self.plugins_menu, actions)

    def createPopupMenu(self):
        return self.application.get_application_context_menu(parent=self)

    def set_splash(self, message):
        """Set splash message"""
        if self.splash is None:
            return
        if message:
            logger.info(message)
        self.splash.show()
        self.splash.showMessage(message,
                                int(Qt.AlignBottom | Qt.AlignCenter |
                                    Qt.AlignAbsolute),
                                QColor(Qt.white))
        QApplication.processEvents()

    def closeEvent(self, event):
        """closeEvent reimplementation"""
        if self.closing(True):
            event.accept()
        else:
            event.ignore()

    def resizeEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.fullscreen_flag:
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)

        # To be used by the tour to be able to resize
        self.sig_resized.emit(event)

    def moveEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.fullscreen_flag:
            self.window_position = self.pos()
        QMainWindow.moveEvent(self, event)

        # To be used by the tour to be able to move
        self.sig_moved.emit(event)

    def hideEvent(self, event):
        """Reimplement Qt method"""
        try:
            for plugin in (self.widgetlist + self.thirdparty_plugins):
                # TODO: Remove old API
                try:
                    # New API
                    if plugin.get_widget().isAncestorOf(
                            self.last_focused_widget):
                        plugin.change_visibility(True)
                except AttributeError:
                    # Old API
                    if plugin.isAncestorOf(self.last_focused_widget):
                        plugin._visibility_changed(True)

            QMainWindow.hideEvent(self, event)
        except RuntimeError:
            QMainWindow.hideEvent(self, event)

    def change_last_focused_widget(self, old, now):
        """To keep track of to the last focused widget"""
        if (now is None and QApplication.activeWindow() is not None):
            QApplication.activeWindow().setFocus()
            self.last_focused_widget = QApplication.focusWidget()
        elif now is not None:
            self.last_focused_widget = now

        self.previous_focused_widget =  old

    def closing(self, cancelable=False):
        """Exit tasks"""
        if self.already_closed or self.is_starting_up:
            return True

        if cancelable and CONF.get('main', 'prompt_on_exit'):
            reply = QMessageBox.critical(self, 'Spyder',
                                         'Do you really want to exit?',
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return False

        if CONF.get('main', 'single_instance') and self.open_files_server:
            self.open_files_server.close()

        # Internal plugins
        for plugin in (self.widgetlist + self.thirdparty_plugins):
            # New API
            try:
                if isinstance(plugin, SpyderDockablePlugin):
                    plugin.close_window()
                if not plugin.on_close(cancelable):
                    return False
            except AttributeError:
                pass

            # Old API
            try:
                plugin._close_window()
                if not plugin.closing_plugin(cancelable):
                    return False
            except AttributeError:
                pass

        # New API: External plugins
        for plugin_name, plugin in self._EXTERNAL_PLUGINS.items():
            try:
                if isinstance(plugin, SpyderDockablePlugin):
                    plugin.close_window()

                if not plugin.on_close(cancelable):
                    return False
            except AttributeError as e:
                logger.error(str(e))

        # Save window settings *after* closing all plugin windows, in order
        # to show them in their previous locations in the next session.
        # Fixes spyder-ide/spyder#12139
        prefix = 'window' + '/'
        self.save_current_window_settings(prefix)

        self.already_closed = True
        return True

    def add_dockwidget(self, plugin):
        """
        Add a plugin QDockWidget to the main window.
        """
        try:
            # New API
            if plugin.is_compatible:
                dockwidget, location = plugin.create_dockwidget(self)
                self.addDockWidget(location, dockwidget)
                self.widgetlist.append(plugin)
        except AttributeError:
            # Old API
            if plugin._is_compatible:
                dockwidget, location = plugin._create_dockwidget()
                self.addDockWidget(location, dockwidget)
                self.widgetlist.append(plugin)

    @Slot()
    def close_current_dockwidget(self):
        widget = QApplication.focusWidget()
        for plugin in (self.widgetlist + self.thirdparty_plugins):
            # TODO: remove old API
            try:
                # New API
                if plugin.get_widget().isAncestorOf(widget):
                    plugin._toggle_view_action.setChecked(False)
                break
            except AttributeError:
                # Old API
                if plugin.isAncestorOf(widget):
                    plugin._toggle_view_action.setChecked(False)
                break

    def toggle_lock(self, value):
        """Lock/Unlock dockwidgets and toolbars"""
        self.interface_locked = value
        CONF.set('main', 'panes_locked', value)
        self.lock_interface_action.setIcon(
            ima.icon('lock' if self.interface_locked else 'lock_open'))
        self.lock_interface_action.setText(
            _("Unlock panes and toolbars") if self.interface_locked else
            _("Lock panes and toolbars"))

        # Apply lock to panes
        for plugin in (self.widgetlist + self.thirdparty_plugins):
            if self.interface_locked:
                if plugin.dockwidget.isFloating():
                    plugin.dockwidget.setFloating(False)

                plugin.dockwidget.remove_title_bar()
            else:
                plugin.dockwidget.set_title_bar()

        # Apply lock to toolbars
        # TODO: Move to layouts plugin (which will depend on Toolbar
        # and MainMenu)
        for toolbar in self.toolbar.toolbarslist:
            if self.interface_locked:
                toolbar.setMovable(False)
            else:
                toolbar.setMovable(True)

    def __update_maximize_action(self):
        if self.state_before_maximizing is None:
            text = _("Maximize current pane")
            tip = _("Maximize current pane")
            icon = ima.icon('maximize')
        else:
            text = _("Restore current pane")
            tip = _("Restore pane to its original size")
            icon = ima.icon('unmaximize')
        self.maximize_action.setText(text)
        self.maximize_action.setIcon(icon)
        self.maximize_action.setToolTip(tip)

    @Slot()
    @Slot(bool)
    def maximize_dockwidget(self, restore=False):
        """Shortcut: Ctrl+Alt+Shift+M
        First call: maximize current dockwidget
        Second call (or restore=True): restore original window layout"""
        if self.state_before_maximizing is None:
            if restore:
                return

            # Select plugin to maximize
            self.state_before_maximizing = self.saveState()
            focus_widget = QApplication.focusWidget()

            for plugin in (self.widgetlist + self.thirdparty_plugins):
                plugin.dockwidget.hide()

                try:
                    # New API
                    if plugin.get_widget().isAncestorOf(focus_widget):
                        self.last_plugin = plugin
                except Exception:
                    # Old API
                    if plugin.isAncestorOf(focus_widget):
                        self.last_plugin = plugin

            # Only plugins that have a dockwidget are part of widgetlist,
            # so last_plugin can be None after the above "for" cycle.
            # For example, this happens if, after Spyder has started, focus
            # is set to the Working directory toolbar (which doesn't have
            # a dockwidget) and then you press the Maximize button
            if self.last_plugin is None:
                # Using the Editor as default plugin to maximize
                self.last_plugin = self.editor

            # Maximize last_plugin
            self.last_plugin.dockwidget.toggleViewAction().setDisabled(True)
            try:
                # New API
                self.setCentralWidget(self.last_plugin.get_widget())
            except AttributeError:
                # Old API
                self.setCentralWidget(self.last_plugin)

            self.last_plugin._ismaximized = True

            # Workaround to solve an issue with editor's outline explorer:
            # (otherwise the whole plugin is hidden and so is the outline explorer
            #  and the latter won't be refreshed if not visible)
            try:
                # New API
                self.last_plugin.get_widget().show()
                self.last_plugin.change_visibility(True)
            except AttributeError:
                # Old API
                self.last_plugin.show()
                self.last_plugin._visibility_changed(True)

            if self.last_plugin is self.editor:
                # Automatically show the outline if the editor was maximized:
                self.addDockWidget(Qt.RightDockWidgetArea,
                                   self.outlineexplorer.dockwidget)
                self.outlineexplorer.dockwidget.show()
        else:
            # Restore original layout (before maximizing current dockwidget)
            try:
                # New API
                self.last_plugin.dockwidget.setWidget(
                    self.last_plugin.get_widget())
            except AttributeError:
                # Old API
                self.last_plugin.dockwidget.setWidget(self.last_plugin)

            self.last_plugin.dockwidget.toggleViewAction().setEnabled(True)
            self.setCentralWidget(None)

            try:
                # New API
                self.last_plugin.get_widget().is_maximized = False
            except AttributeError:
                # Old API
                self.last_plugin._ismaximized = False

            self.restoreState(self.state_before_maximizing)
            self.state_before_maximizing = None
            try:
                # New API
                self.last_plugin.get_widget().get_focus_widget().setFocus()
            except AttributeError:
                # Old API
                self.last_plugin.get_focus_widget().setFocus()

        self.__update_maximize_action()

    def __update_fullscreen_action(self):
        if self.fullscreen_flag:
            icon = ima.icon('window_nofullscreen')
        else:
            icon = ima.icon('window_fullscreen')
        if is_text_string(icon):
            icon = get_icon(icon)
        self.fullscreen_action.setIcon(icon)

    @Slot()
    def toggle_fullscreen(self):
        if self.fullscreen_flag:
            self.fullscreen_flag = False
            if os.name == 'nt':
                self.setWindowFlags(
                    self.windowFlags()
                    ^ (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint))
                self.setGeometry(self.saved_normal_geometry)
            self.showNormal()
            if self.maximized_flag:
                self.showMaximized()
        else:
            self.maximized_flag = self.isMaximized()
            self.fullscreen_flag = True
            self.saved_normal_geometry = self.normalGeometry()
            if os.name == 'nt':
                # Due to limitations of the Windows DWM, compositing is not
                # handled correctly for OpenGL based windows when going into
                # full screen mode, so we need to use this workaround.
                # See spyder-ide/spyder#4291.
                self.setWindowFlags(self.windowFlags()
                                    | Qt.FramelessWindowHint
                                    | Qt.WindowStaysOnTopHint)

                screen_number = QDesktopWidget().screenNumber(self)
                if screen_number < 0:
                    screen_number = 0

                r = QApplication.desktop().screenGeometry(screen_number)
                self.setGeometry(
                    r.left() - 1, r.top() - 1, r.width() + 2, r.height() + 2)
                self.showNormal()
            else:
                self.showFullScreen()
        self.__update_fullscreen_action()

    def add_to_toolbar(self, toolbar, widget):
        """Add widget actions to toolbar"""
        actions = widget.toolbar_actions
        if actions is not None:
            add_actions(toolbar, actions)

    @Slot()
    def global_callback(self):
        """Global callback"""
        widget = QApplication.focusWidget()
        action = self.sender()
        callback = from_qvariant(action.data(), to_text_string)
        from spyder.plugins.editor.widgets.base import TextEditBaseWidget
        from spyder.plugins.ipythonconsole.widgets import ControlWidget

        if isinstance(widget, (TextEditBaseWidget, ControlWidget)):
            getattr(widget, callback)()
        else:
            return

    def redirect_internalshell_stdio(self, state):
        if state:
            self.console.redirect_stds()
        else:
            self.console.restore_stds()

    def open_external_console(self, fname, wdir, args, interact, debug, python,
                              python_args, systerm, post_mortem=False):
        """Open external console"""
        if systerm:
            # Running script in an external system terminal
            try:
                if CONF.get('main_interpreter', 'default'):
                    executable = get_python_executable()
                else:
                    executable = CONF.get('main_interpreter', 'executable')
                programs.run_python_script_in_terminal(
                        fname, wdir, args, interact, debug, python_args,
                        executable)
            except NotImplementedError:
                QMessageBox.critical(self, _("Run"),
                                     _("Running an external system terminal "
                                       "is not supported on platform %s."
                                       ) % os.name)

    def execute_in_external_console(self, lines, focus_to_editor):
        """
        Execute lines in IPython console and eventually set focus
        to the Editor.
        """
        console = self.ipyconsole
        console.switch_to_plugin()
        console.execute_code(lines)
        if focus_to_editor:
            self.editor.switch_to_plugin()

    def open_file(self, fname, external=False):
        """
        Open filename with the appropriate application
        Redirect to the right widget (txt -> editor, spydata -> workspace, ...)
        or open file outside Spyder (if extension is not supported)
        """
        fname = to_text_string(fname)
        ext = osp.splitext(fname)[1]
        if encoding.is_text_file(fname):
            self.editor.load(fname)
        elif self.variableexplorer is not None and ext in IMPORT_EXT:
            self.variableexplorer.import_data(fname)
        elif not external:
            fname = file_uri(fname)
            start_file(fname)

    def open_external_file(self, fname):
        """
        Open external files that can be handled either by the Editor or the
        variable explorer inside Spyder.
        """
        # Check that file exists
        fname = encoding.to_unicode_from_fs(fname)
        if osp.exists(osp.join(CWD, fname)):
            fpath = osp.join(CWD, fname)
        elif osp.exists(fname):
            fpath = fname
        else:
            return

        # Don't open script that starts Spyder at startup.
        # Fixes issue spyder-ide/spyder#14483
        if sys.platform == 'darwin' and 'bin/spyder' in fname:
            return

        if osp.isfile(fpath):
            self.open_file(fpath, external=True)
        elif osp.isdir(fpath):
            QMessageBox.warning(
                self, _("Error"),
                _('To open <code>{fpath}</code> as a project with Spyder, '
                  'please use <code>spyder -p "{fname}"</code>.')
                .format(fpath=osp.normpath(fpath), fname=fname)
            )

    # --- Path Manager
    # ------------------------------------------------------------------------
    def load_python_path(self):
        """Load path stored in Spyder configuration folder."""
        if osp.isfile(self.SPYDER_PATH):
            path, _x = encoding.readlines(self.SPYDER_PATH)
            self.path = tuple(name for name in path if osp.isdir(name))

        if osp.isfile(self.SPYDER_NOT_ACTIVE_PATH):
            not_active_path, _x = encoding.readlines(
                self.SPYDER_NOT_ACTIVE_PATH)
            self.not_active_path = tuple(name for name in not_active_path
                                         if osp.isdir(name))

    def save_python_path(self, new_path_dict):
        """
        Save path in Spyder configuration folder.

        `new_path_dict` is an OrderedDict that has the new paths as keys and
        the state as values. The state is `True` for active and `False` for
        inactive.
        """
        path = [p for p in new_path_dict]
        not_active_path = [p for p in new_path_dict if not new_path_dict[p]]
        try:
            encoding.writelines(path, self.SPYDER_PATH)
            encoding.writelines(not_active_path, self.SPYDER_NOT_ACTIVE_PATH)
        except EnvironmentError as e:
            logger.error(str(e))
        CONF.set('main', 'spyder_pythonpath', self.get_spyder_pythonpath())

    def get_spyder_pythonpath_dict(self):
        """
        Return Spyder PYTHONPATH.

        The returned ordered dictionary has the paths as keys and the state
        as values. The state is `True` for active and `False` for inactive.

        Example:
            OrderedDict([('/some/path, True), ('/some/other/path, False)])
        """
        self.load_python_path()

        path_dict = OrderedDict()
        for path in self.path:
            path_dict[path] = path not in self.not_active_path

        for path in self.project_path:
            path_dict[path] = True

        return path_dict

    def get_spyder_pythonpath(self):
        """
        Return Spyder PYTHONPATH.
        """
        path_dict = self.get_spyder_pythonpath_dict()
        path = [k for k, v in path_dict.items() if v]
        return path

    def update_python_path(self, new_path_dict):
        """Update python path on Spyder interpreter and kernels."""
        # Load previous path
        path_dict = self.get_spyder_pythonpath_dict()

        # Save path
        if path_dict != new_path_dict:
            # It doesn't include the project_path
            self.save_python_path(new_path_dict)

        # Load new path
        new_path_dict_p = self.get_spyder_pythonpath_dict()  # Includes project

        # Update Spyder interpreter
        for path in path_dict:
            while path in sys.path:
                sys.path.remove(path)

        for path, active in reversed(new_path_dict_p.items()):
            if active:
                sys.path.insert(1, path)

        # Any plugin that needs to do some work based on this signal should
        # connect to it on plugin registration
        self.sig_pythonpath_changed.emit(path_dict, new_path_dict_p)

    @Slot()
    def show_path_manager(self):
        """Show path manager dialog."""
        from spyder.widgets.pathmanager import PathManager
        read_only_path = tuple(self.projects.get_pythonpath())
        dialog = PathManager(self, self.path, read_only_path,
                             self.not_active_path, sync=True)
        self._path_manager = dialog
        dialog.sig_path_changed.connect(self.update_python_path)
        dialog.redirect_stdio.connect(self.redirect_internalshell_stdio)
        dialog.show()

    def pythonpath_changed(self):
        """Project's PYTHONPATH contribution has changed."""
        self.project_path = tuple(self.projects.get_pythonpath())
        path_dict = self.get_spyder_pythonpath_dict()
        self.update_python_path(path_dict)

    #---- Preferences
    def apply_settings(self):
        """Apply main window settings."""
        qapp = QApplication.instance()

        # Set 'gtk+' as the default theme in Gtk-based desktops
        # Fixes spyder-ide/spyder#2036.
        if is_gtk_desktop() and ('GTK+' in QStyleFactory.keys()):
            try:
                qapp.setStyle('gtk+')
            except:
                pass
        else:
            style_name = CONF.get('appearance', 'windows_style',
                                  self.default_style)
            style = QStyleFactory.create(style_name)
            if style is not None:
                style.setProperty('name', style_name)
                qapp.setStyle(style)

        default = self.DOCKOPTIONS
        if CONF.get('main', 'vertical_tabs'):
            default = default|QMainWindow.VerticalTabs
        self.setDockOptions(default)

        self.apply_panes_settings()

        if CONF.get('main', 'use_custom_cursor_blinking'):
            qapp.setCursorFlashTime(
                CONF.get('main', 'custom_cursor_blinking'))
        else:
            qapp.setCursorFlashTime(self.CURSORBLINK_OSDEFAULT)

    def apply_panes_settings(self):
        """Update dockwidgets features settings."""
        for plugin in (self.widgetlist + self.thirdparty_plugins):
            features = plugin.dockwidget.FEATURES

            plugin.dockwidget.setFeatures(features)

            try:
                # New API
                margin = 0
                if CONF.get('main', 'use_custom_margin'):
                    margin = CONF.get('main', 'custom_margin')
                plugin.update_margins(margin)
            except AttributeError:
                # Old API
                plugin._update_margins()

    @Slot()
    def show_preferences(self):
        """Edit Spyder preferences."""
        self.preferences.open_dialog(self.prefs_dialog_size)

    def set_prefs_size(self, size):
        """Save preferences dialog size"""
        self.prefs_dialog_size = size

    # -- Open files server
    def start_open_files_server(self):
        self.open_files_server.setsockopt(socket.SOL_SOCKET,
                                          socket.SO_REUSEADDR, 1)
        port = select_port(default_port=OPEN_FILES_PORT)
        CONF.set('main', 'open_files_port', port)
        self.open_files_server.bind(('127.0.0.1', port))
        self.open_files_server.listen(20)
        while 1:  # 1 is faster than True
            try:
                req, dummy = self.open_files_server.accept()
            except socket.error as e:
                # See spyder-ide/spyder#1275 for details on why errno EINTR is
                # silently ignored here.
                eintr = errno.WSAEINTR if os.name == 'nt' else errno.EINTR
                # To avoid a traceback after closing on Windows
                if e.args[0] == eintr:
                    continue
                # handle a connection abort on close error
                enotsock = (errno.WSAENOTSOCK if os.name == 'nt'
                            else errno.ENOTSOCK)
                if e.args[0] in [errno.ECONNABORTED, enotsock]:
                    return
                raise
            fname = req.recv(1024)
            fname = fname.decode('utf-8')
            self.sig_open_external_file.emit(fname)
            req.sendall(b' ')

    # ---- Quit and restart, and reset spyder defaults
    @Slot()
    def reset_spyder(self):
        """
        Quit and reset Spyder and then Restart application.
        """
        answer = QMessageBox.warning(self, _("Warning"),
             _("Spyder will restart and reset to default settings: <br><br>"
               "Do you want to continue?"),
             QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.restart(reset=True)

    @Slot()
    def restart(self, reset=False):
        """Wrapper to handle plugins request to restart Spyder."""
        self.application.restart(reset=reset)

    # ---- Interactive Tours
    def show_tour(self, index):
        """Show interactive tour."""
        self.maximize_dockwidget(restore=True)
        frames = self.tours_available[index]
        self.tour.set_tour(index, frames, self)
        self.tour.start_tour()

    # ---- Global Switcher
    def open_switcher(self, symbol=False):
        """Open switcher dialog box."""
        if self.switcher is not None and self.switcher.isVisible():
            self.switcher.clear()
            self.switcher.hide()
            return
        if symbol:
            self.switcher.set_search_text('@')
        else:
            self.switcher.set_search_text('')
            self.switcher.setup()
        self.switcher.show()

        # Note: The +6 pixel on the top makes it look better
        # FIXME: Why is this using the toolbars menu?
        delta_top = (self.toolbar.toolbars_menu.geometry().height() +
                     self.menuBar().geometry().height() + 6)

        self.switcher.set_position(delta_top)

    def open_symbolfinder(self):
        """Open symbol list management dialog box."""
        self.open_switcher(symbol=True)

    def create_switcher(self):
        """Create switcher dialog instance."""
        if self.switcher is None:
            from spyder.widgets.switcher import Switcher
            self.switcher = Switcher(self)

        return self.switcher

    @Slot()
    def show_tour_message(self, force=False):
        """
        Show message about starting the tour the first time Spyder starts.
        """
        should_show_tour = CONF.get('main', 'show_tour_message')
        if force or (should_show_tour and not running_under_pytest()
                     and not get_safe_mode()):
            CONF.set('main', 'show_tour_message', False)
            self.tour_dialog = tour.OpenTourDialog(
                self, lambda: self.show_tour(DEFAULT_TOUR))
            self.tour_dialog.show()

    # --- For OpenGL
    def _test_setting_opengl(self, option):
        """Get the current OpenGL implementation in use"""
        if option == 'software':
            return QCoreApplication.testAttribute(Qt.AA_UseSoftwareOpenGL)
        elif option == 'desktop':
            return QCoreApplication.testAttribute(Qt.AA_UseDesktopOpenGL)
        elif option == 'gles':
            return QCoreApplication.testAttribute(Qt.AA_UseOpenGLES)


#==============================================================================
# Utilities for the 'main' function below
#==============================================================================
def create_application():
    """Create application and patch sys.exit."""
    # Our QApplication
    app = qapplication()

    # --- Set application icon
    app_icon = QIcon(get_image_path("spyder.svg"))
    app.setWindowIcon(app_icon)

    # Required for correct icon on GNOME/Wayland:
    if hasattr(app, 'setDesktopFileName'):
        app.setDesktopFileName('spyder')

    #----Monkey patching QApplication
    class FakeQApplication(QApplication):
        """Spyder's fake QApplication"""
        def __init__(self, args):
            self = app  # analysis:ignore
        @staticmethod
        def exec_():
            """Do nothing because the Qt mainloop is already running"""
            pass
    from qtpy import QtWidgets
    QtWidgets.QApplication = FakeQApplication

    # ----Monkey patching sys.exit
    def fake_sys_exit(arg=[]):
        pass
    sys.exit = fake_sys_exit

    # ----Monkey patching sys.excepthook to avoid crashes in PyQt 5.5+
    if PYQT5:
        def spy_excepthook(type_, value, tback):
            sys.__excepthook__(type_, value, tback)
        sys.excepthook = spy_excepthook

    # Removing arguments from sys.argv as in standard Python interpreter
    sys.argv = ['']

    return app


def create_window(app, splash, options, args):
    """
    Create and show Spyder's main window and start QApplication event loop.
    """
    # Main window
    main = MainWindow(splash, options)
    try:
        main.setup()
    except BaseException:
        if main.console is not None:
            try:
                main.console.exit_interpreter()
            except BaseException:
                pass
        raise

    main.show()
    main.post_visible_setup()

    if main.console:
        namespace = CONF.get('internal_console', 'namespace', {})
        main.console.start_interpreter(namespace)
        main.console.set_namespace_item('spy', Spy(app=app, window=main))

    # Propagate current configurations to all configuration observers
    CONF.notify_all_observers()

    # Don't show icons in menus for Mac
    if sys.platform == 'darwin':
        QCoreApplication.setAttribute(Qt.AA_DontShowIconsInMenus, True)

    # Open external files with our Mac app
    if running_in_mac_app():
        app.sig_open_external_file.connect(main.open_external_file)
        app._has_started = True
        if hasattr(app, '_pending_file_open'):
            if args:
                args = app._pending_file_open + args
            else:
                args = app._pending_file_open


    # Open external files passed as args
    if args:
        for a in args:
            main.open_external_file(a)

    # To give focus again to the last focused widget after restoring
    # the window
    app.focusChanged.connect(main.change_last_focused_widget)

    if not running_under_pytest():
        app.exec_()
    return main


#==============================================================================
# Main
#==============================================================================
def main(options, args):
    """Main function"""
    # **** For Pytest ****
    if running_under_pytest():
        if CONF.get('main', 'opengl') != 'automatic':
            option = CONF.get('main', 'opengl')
            set_opengl_implementation(option)

        app = create_application()
        window = create_window(app, None, options, None)
        return window

    # **** Handle hide_console option ****
    if options.show_console:
        print("(Deprecated) --show console does nothing, now the default "
              " behavior is to show the console, use --hide-console if you "
              "want to hide it")

    if set_attached_console_visible is not None:
        set_attached_console_visible(not options.hide_console
                                     or options.reset_config_files
                                     or options.reset_to_defaults
                                     or options.optimize
                                     or bool(get_debug_level()))

    # **** Set OpenGL implementation to use ****
    # This attribute must be set before creating the application.
    # See spyder-ide/spyder#11227
    if options.opengl_implementation:
        option = options.opengl_implementation
        set_opengl_implementation(option)
    else:
        if CONF.get('main', 'opengl') != 'automatic':
            option = CONF.get('main', 'opengl')
            set_opengl_implementation(option)

    # **** Set high DPI scaling ****
    # This attribute must be set before creating the application.
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling,
                                      CONF.get('main', 'high_dpi_scaling'))

    # **** Set debugging info ****
    setup_logging(options)

    # **** Create the application ****
    app = create_application()

    # **** Create splash screen ****
    splash = create_splash_screen()
    if splash is not None:
        splash.show()
        splash.showMessage(
            _("Initializing..."),
            int(Qt.AlignBottom | Qt.AlignCenter | Qt.AlignAbsolute),
            QColor(Qt.white)
        )
        QApplication.processEvents()

    if options.reset_to_defaults:
        # Reset Spyder settings to defaults
        CONF.reset_to_defaults()
        return
    elif options.optimize:
        # Optimize the whole Spyder's source code directory
        import spyder
        programs.run_python_script(module="compileall",
                                   args=[spyder.__path__[0]], p_args=['-O'])
        return

    # **** Read faulthandler log file ****
    faulthandler_file = get_conf_path('faulthandler.log')
    previous_crash = ''
    if osp.exists(faulthandler_file):
        with open(faulthandler_file, 'r') as f:
            previous_crash = f.read()

        # Remove file to not pick it up for next time.
        try:
            dst = get_conf_path('faulthandler.log.old')
            shutil.move(faulthandler_file, dst)
        except Exception:
            pass
    CONF.set('main', 'previous_crash', previous_crash)

    # **** Create main window ****
    mainwindow = None
    try:
        if PY3 and options.report_segfault:
            import faulthandler
            with open(faulthandler_file, 'w') as f:
                faulthandler.enable(file=f)
                mainwindow = create_window(app, splash, options, args)
        else:
            mainwindow = create_window(app, splash, options, args)
    except FontError:
        QMessageBox.information(None, "Spyder",
                "Spyder was unable to load the <i>Spyder 3</i> "
                "icon theme. That's why it's going to fallback to the "
                "theme used in Spyder 2.<br><br>"
                "For that, please close this window and start Spyder again.")
        CONF.set('appearance', 'icon_theme', 'spyder 2')
    if mainwindow is None:
        # An exception occurred
        if splash is not None:
            splash.hide()
        return

    ORIGINAL_SYS_EXIT()


if __name__ == "__main__":
    main()

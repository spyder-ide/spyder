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
import shutil
import signal
import socket
import sys
import threading
import traceback

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
from qtpy.compat import from_qvariant
from qtpy.QtCore import (QCoreApplication, Qt, QTimer, Signal, Slot,
                         qInstallMessageHandler)
from qtpy.QtGui import QColor, QKeySequence, QIcon
from qtpy.QtWidgets import (QApplication, QMainWindow, QMenu, QMessageBox,
                            QShortcut, QStyleFactory)

# Avoid a "Cannot mix incompatible Qt library" error on Windows platforms
from qtpy import QtSvg  # analysis:ignore

# Avoid a bug in Qt: https://bugreports.qt.io/browse/QTBUG-46720
from qtpy import QtWebEngineWidgets  # analysis:ignore

from qtawesome.iconic_font import FontError

#==============================================================================
# Local imports
# NOTE: Move (if possible) import's of widgets and plugins exactly where they
# are needed in MainWindow to speed up perceived startup time (i.e. the time
# from clicking the Spyder icon to showing the splash screen).
#==============================================================================
from spyder import __version__
from spyder import dependencies
from spyder.app.utils import (
    create_application, create_splash_screen, create_window,
    delete_debug_log_files, qt_message_handler, set_links_color, setup_logging,
    set_opengl_implementation)
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.config.base import (_, DEV, get_conf_path, get_debug_level,
                                get_home_dir, get_module_source_path,
                                is_pynsist, running_in_mac_app,
                                running_under_pytest, STDERR)
from spyder.config.gui import is_dark_font_color
from spyder.config.main import OPEN_FILES_PORT
from spyder.config.manager import CONF
from spyder.config.utils import IMPORT_EXT, is_gtk_desktop
from spyder.otherplugins import get_spyderplugins_mods
from spyder.py3compat import configparser as cp, PY3, to_text_string
from spyder.utils import encoding, programs
from spyder.utils.icon_manager import ima
from spyder.utils.misc import (select_port, getcwd_or_home,
                               get_python_executable)
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import (create_action, add_actions, file_uri,
                                    qapplication, start_file)
from spyder.utils.stylesheet import APP_STYLESHEET
from spyder.app.find_plugins import find_external_plugins, find_internal_plugins

# Spyder API Imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import (
    Plugins, SpyderPlugin, SpyderPluginV2, SpyderDockablePlugin,
    SpyderPluginWidget)

#==============================================================================
# Windows only local imports
#==============================================================================
set_attached_console_visible = None
is_attached_console_visible = None
set_windows_appusermodelid = None
if os.name == 'nt':
    from spyder.utils.windows import (set_attached_console_visible,
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
    sig_resized = Signal("QResizeEvent")
    sig_moved = Signal("QMoveEvent")
    sig_layout_setup_ready = Signal(object)  # Related to default layouts

    # ---- Plugin handling methods
    # ------------------------------------------------------------------------
    def get_plugin(self, plugin_name, error=True):
        """
        Return a plugin instance by providing the plugin class.
        """
        if plugin_name in PLUGIN_REGISTRY:
            return PLUGIN_REGISTRY.get_plugin(plugin_name)

        if error:
            raise SpyderAPIError(f'Plugin "{plugin_name}" not found!')

        return None

    def get_dockable_plugins(self):
        """Get a list of all dockable plugins."""
        dockable_plugins = []
        for plugin_name in PLUGIN_REGISTRY:
            plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
            if isinstance(plugin, (SpyderDockablePlugin, SpyderPluginWidget)):
                dockable_plugins.append((plugin_name, plugin))
        return dockable_plugins

    def is_plugin_enabled(self, plugin_name):
        """Determine if a given plugin is going to be loaded."""
        return PLUGIN_REGISTRY.is_plugin_enabled(plugin_name)

    def is_plugin_available(self, plugin_name):
        """Determine if a given plugin is going to be loaded."""
        return PLUGIN_REGISTRY.is_plugin_available(plugin_name)

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

    def register_plugin(self, plugin_name, external=False, omit_conf=False):
        """
        Register a plugin in Spyder Main Window.
        """
        plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)

        self.set_splash(_("Loading {}...").format(plugin.get_name()))
        logger.info("Loading {}...".format(plugin.NAME))

        # Check plugin compatibility
        is_compatible, message = plugin.check_compatibility()
        plugin.is_compatible = is_compatible
        plugin.get_description()

        if not is_compatible:
            self.show_compatibility_message(message)
            return

        # Connect Plugin Signals to main window methods
        plugin.sig_exception_occurred.connect(self.handle_exception)
        plugin.sig_free_memory_requested.connect(self.free_memory)
        plugin.sig_quit_requested.connect(self.close)
        plugin.sig_redirect_stdio_requested.connect(
            self.redirect_internalshell_stdio)
        plugin.sig_status_message_requested.connect(self.show_status_message)

        if isinstance(plugin, SpyderDockablePlugin):
            plugin.sig_focus_changed.connect(self.plugin_focus_changed)
            plugin.sig_switch_to_plugin_requested.connect(
                self.switch_to_plugin)
            plugin.sig_update_ancestor_requested.connect(
                lambda: plugin.set_ancestor(self))

        # Connect Main window Signals to plugin signals
        self.sig_moved.connect(plugin.sig_mainwindow_moved)
        self.sig_resized.connect(plugin.sig_mainwindow_resized)

        # Register plugin
        plugin._register(omit_conf=omit_conf)

        if isinstance(plugin, SpyderDockablePlugin):
            # Add dockwidget
            self.add_dockwidget(plugin)

            # Update margins
            margin = 0
            if CONF.get('main', 'use_custom_margin'):
                margin = CONF.get('main', 'custom_margin')
            plugin.update_margins(margin)

        if plugin_name == Plugins.Shortcuts:
            for action, context, action_name in self.shortcut_queue:
                self.register_shortcut(action, context, action_name)
            self.shortcut_queue = []

        logger.info("Registering shortcuts for {}...".format(plugin.NAME))
        for action_name, action in plugin.get_actions().items():
            context = (getattr(action, 'shortcut_context', plugin.NAME)
                       or plugin.NAME)

            if getattr(action, 'register_shortcut', True):
                if isinstance(action_name, Enum):
                    action_name = action_name.value
                if Plugins.Shortcuts in PLUGIN_REGISTRY:
                    self.register_shortcut(action, context, action_name)
                else:
                    self.shortcut_queue.append((action, context, action_name))

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

            if Plugins.Shortcuts in PLUGIN_REGISTRY:
                self.register_shortcut(sc, context, name)
                self.register_shortcut(
                    plugin.toggle_view_action, context, name)
            else:
                self.shortcut_queue.append((sc, context, name))
                self.shortcut_queue.append(
                    (plugin.toggle_view_action, context, name))

    def unregister_plugin(self, plugin):
        """
        Unregister a plugin from the Spyder Main Window.
        """
        logger.info("Unloading {}...".format(plugin.NAME))

        # Disconnect all slots
        signals = [
            plugin.sig_quit_requested,
            plugin.sig_redirect_stdio_requested,
            plugin.sig_status_message_requested,
        ]

        for sig in signals:
            try:
                sig.disconnect()
            except TypeError:
                pass

        # Unregister shortcuts for actions
        logger.info("Unregistering shortcuts for {}...".format(plugin.NAME))
        for action_name, action in plugin.get_actions().items():
            context = (getattr(action, 'shortcut_context', plugin.NAME)
                       or plugin.NAME)
            self.shortcuts.unregister_shortcut(action, context, action_name)

        # Unregister switch to shortcut
        shortcut = None
        try:
            context = '_'
            name = 'switch to {}'.format(plugin.CONF_SECTION)
            shortcut = CONF.get_shortcut(context, name,
                                         plugin_name=plugin.CONF_SECTION)
        except Exception:
            pass

        if shortcut is not None:
            self.shortcuts.unregister_shortcut(
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

    @property
    def last_plugin(self):
        """
        Get last plugin with focus if it is a dockable widget.

        If a non-dockable plugin has the focus this will return by default
        the Editor plugin.
        """
        # Needed to prevent errors with the old API at
        # spyder/plugins/base::_switch_to_plugin
        return self.layouts.get_last_plugin()

    def maximize_dockwidget(self, restore=False):
        """
        This is needed to prevent errors with the old API at
        spyder/plugins/base::_switch_to_plugin.

        See spyder-ide/spyder#15164

        Parameters
        ----------
        restore : bool, optional
            If the current dockwidget needs to be restored to its unmaximized
            state. The default is False.
        """
        self.layouts.maximize_dockwidget(restore=restore)

    def switch_to_plugin(self, plugin, force_focus=None):
        """
        Switch to this plugin.

        Notes
        -----
        This operation unmaximizes the current plugin (if any), raises
        this plugin to view (if it's hidden) and gives it focus (if
        possible).
        """
        last_plugin = self.last_plugin
        try:
            # New API
            if (last_plugin is not None
                    and last_plugin.get_widget().is_maximized
                    and last_plugin is not plugin):
                self.layouts.maximize_dockwidget()
        except AttributeError:
            # Old API
            if (last_plugin is not None and self.last_plugin._ismaximized
                    and last_plugin is not plugin):
                self.layouts.maximize_dockwidget()

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
        try:
            self.widgetlist.remove(plugin)
        except ValueError:
            pass

    def tabify_plugins(self, first, second):
        """Tabify plugin dockwigdets."""
        self.tabifyDockWidget(first.dockwidget, second.dockwidget)

    def tabify_plugin(self, plugin, default=None):
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

        # If TABIFY not defined use the [default]
        tabify = getattr(plugin, 'TABIFY', [default])
        if not isinstance(tabify, list):
            next_to_plugins = [tabify]
        else:
            next_to_plugins = tabify

        # Check if TABIFY is not a list with None as unique value or a default
        # list
        if tabify in [[None], []]:
            return False

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

                # Show external plugins
                if plugin.NAME in PLUGIN_REGISTRY.external_plugins:
                    plugin.get_widget().toggle_view(True)

            plugin.set_conf('enable', True)
            plugin.set_conf('first_time', False)
        else:
            # This is needed to ensure plugins are placed correctly when
            # switching layouts.
            logger.info("Tabify {} dockwidget...".format(plugin.NAME))
            # Check if plugin has no other dockwidgets in the same position
            if not bool(self.tabifiedDockWidgets(plugin.dockwidget)):
                tabify_helper(plugin, next_to_plugins)

        return True

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

        # Enabling scaling for high dpi
        qapp.setAttribute(Qt.AA_UseHighDpiPixmaps)

        # Set Windows app icon to use .ico file
        if os.name == "nt":
            qapp.setWindowIcon(ima.get_icon("windows_app_icon"))

        self.help = None

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
        self.shortcut_queue = []

        # Handle Spyder path
        self.path = ()
        self.not_active_path = ()
        self.project_path = ()

        # New API
        self._APPLICATION_TOOLBARS = OrderedDict()
        self._STATUS_WIDGETS = OrderedDict()
        # Mapping of new plugin identifiers vs old attributtes
        # names given for plugins or to prevent collisions with other
        # attributes, i.e layout (Qt) vs layout (SpyderPluginV2)
        self._INTERNAL_PLUGINS_MAPPING = {
            'console': Plugins.Console,
            'maininterpreter': Plugins.MainInterpreter,
            'outlineexplorer': Plugins.OutlineExplorer,
            'variableexplorer': Plugins.VariableExplorer,
            'ipyconsole': Plugins.IPythonConsole,
            'workingdirectory': Plugins.WorkingDirectory,
            'projects': Plugins.Projects,
            'findinfiles': Plugins.Find,
            'layouts': Plugins.Layout,
            }

        self.thirdparty_plugins = []

        # File switcher
        self.switcher = None

        # Preferences
        self.prefs_dialog_size = None
        self.prefs_dialog_instance = None

        # Actions
        self.undo_action = None
        self.redo_action = None
        self.copy_action = None
        self.cut_action = None
        self.paste_action = None
        self.selectall_action = None

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

        self.floating_dockwidgets = []
        self.window_size = None
        self.window_position = None

        # To keep track of the last focused widget
        self.last_focused_widget = None
        self.previous_focused_widget = None

        # Server to open external files on a single instance
        # This is needed in order to handle socket creation problems.
        # See spyder-ide/spyder#4132.
        if os.name == 'nt':
            try:
                self.open_files_server = socket.socket(socket.AF_INET,
                                                       socket.SOCK_STREAM,
                                                       socket.IPPROTO_TCP)
            except OSError:
                self.open_files_server = None
                QMessageBox.warning(None, "Spyder",
                         _("An error occurred while creating a socket needed "
                           "by Spyder. Please, try to run as an Administrator "
                           "from cmd.exe the following command and then "
                           "restart your computer: <br><br><span "
                           "style=\'color: {color}\'><b>netsh winsock reset "
                           "</b></span><br>").format(
                               color=QStylePalette.COLOR_BACKGROUND_4))
        else:
            self.open_files_server = socket.socket(socket.AF_INET,
                                                   socket.SOCK_STREAM,
                                                   socket.IPPROTO_TCP)

        # Apply main window settings
        self.apply_settings()

        # To set all dockwidgets tabs to be on top (in case we want to do it
        # in the future)
        # self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)

        logger.info("End of MainWindow constructor")

    # ---- Window setup
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
        for plugin_name in PLUGIN_REGISTRY:
            plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
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
        PLUGIN_REGISTRY.sig_plugin_ready.connect(
            lambda plugin_name, omit_conf: self.register_plugin(
                plugin_name, omit_conf=omit_conf))

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
            dark_qss = str(APP_STYLESHEET)
            self.setStyleSheet(dark_qss)
            self.statusBar().setStyleSheet(dark_qss)
            css_path = DARK_CSS_PATH

        elif ui_theme == 'light':
            if not running_under_pytest():
                # Set style proxy to fix combobox popup on mac and qdark
                qapp = QApplication.instance()
                qapp.setStyle(self._proxy_style)
            light_qss = str(APP_STYLESHEET)
            self.setStyleSheet(light_qss)
            self.statusBar().setStyleSheet(light_qss)
            css_path = CSS_PATH

        elif ui_theme == 'automatic':
            if not is_dark_font_color(color_scheme):
                if not running_under_pytest():
                    # Set style proxy to fix combobox popup on mac and qdark
                    qapp = QApplication.instance()
                    qapp.setStyle(self._proxy_style)
                dark_qss = str(APP_STYLESHEET)
                self.setStyleSheet(dark_qss)
                self.statusBar().setStyleSheet(dark_qss)
                css_path = DARK_CSS_PATH
            else:
                light_qss = str(APP_STYLESHEET)
                self.setStyleSheet(light_qss)
                self.statusBar().setStyleSheet(light_qss)
                css_path = CSS_PATH

        # Set css_path as a configuration to be used by the plugins
        CONF.set('appearance', 'css_path', css_path)

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
            "Please do not use it to run your code\n\n"
        )
        CONF.set('internal_console', 'message', message)
        CONF.set('internal_console', 'multithreaded', self.multithreaded)
        CONF.set('internal_console', 'profile', self.profile)
        CONF.set('internal_console', 'commands', [])
        CONF.set('internal_console', 'namespace', {})
        CONF.set('internal_console', 'show_internal_errors', True)

        # Working directory initialization
        CONF.set('workingdir', 'init_workdir', self.init_workdir)

        # Load and register internal and external plugins
        external_plugins = find_external_plugins()
        internal_plugins = find_internal_plugins()
        all_plugins = external_plugins.copy()
        all_plugins.update(internal_plugins.copy())

        # Determine 'enable' config for the plugins that have it
        enabled_plugins = {}
        for plugin in all_plugins.values():
            plugin_name = plugin.NAME
            plugin_main_attribute_name = (
                self._INTERNAL_PLUGINS_MAPPING[plugin_name]
                if plugin_name in self._INTERNAL_PLUGINS_MAPPING
                else plugin_name)
            try:
                if CONF.get(plugin_main_attribute_name, "enable"):
                    enabled_plugins[plugin_name] = plugin
                    PLUGIN_REGISTRY.set_plugin_enabled(plugin_name)
            except (cp.NoOptionError, cp.NoSectionError):
                enabled_plugins[plugin_name] = plugin
                PLUGIN_REGISTRY.set_plugin_enabled(plugin_name)

        # Instantiate internal Spyder 5 plugins
        for plugin_name in internal_plugins:
            if plugin_name in enabled_plugins:
                PluginClass = internal_plugins[plugin_name]
                if issubclass(PluginClass, SpyderPluginV2):
                    PLUGIN_REGISTRY.register_plugin(self, PluginClass,
                                                    external=False)

        # Instantiate internal Spyder 4 plugins
        for plugin_name in internal_plugins:
            if plugin_name in enabled_plugins:
                PluginClass = internal_plugins[plugin_name]
                if issubclass(PluginClass, SpyderPlugin):
                    if plugin_name == Plugins.IPythonConsole:
                        plugin_instance = PLUGIN_REGISTRY.register_plugin(
                            self, PluginClass, external=False)
                        plugin_instance.sig_exception_occurred.connect(
                            self.handle_exception)
                    else:
                        plugin_instance = PLUGIN_REGISTRY.register_plugin(
                            self, PluginClass, external=False)
                    self.preferences.register_plugin_preferences(
                        plugin_instance)

        # Instantiate external Spyder 5 plugins
        for plugin_name in external_plugins:
            if plugin_name in enabled_plugins:
                PluginClass = external_plugins[plugin_name]
                try:
                    plugin_instance = PLUGIN_REGISTRY.register_plugin(
                        self, PluginClass, external=True)

                    # These attributes come from spyder.app.find_plugins to
                    # add plugins to the dependencies dialog
                    module = PluginClass._spyder_module_name
                    package_name = PluginClass._spyder_package_name
                    version = PluginClass._spyder_version
                    description = plugin_instance.get_description()
                    dependencies.add(module, package_name, description,
                                     version, None, kind=dependencies.PLUGIN)
                except Exception as error:
                    print("%s: %s" % (PluginClass, str(error)), file=STDERR)
                    traceback.print_exc(file=STDERR)

        self.set_splash(_("Loading old third-party plugins..."))
        for mod in get_spyderplugins_mods():
            try:
                plugin = PLUGIN_REGISTRY.register_plugin(self, mod,
                                                         external=True)
                if plugin.check_compatibility()[0]:
                    if hasattr(plugin, 'CONFIGWIDGET_CLASS'):
                        self.preferences.register_plugin_preferences(plugin)

                    if not hasattr(plugin, 'COMPLETION_PROVIDER_NAME'):
                        self.thirdparty_plugins.append(plugin)

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

        # Set window title
        self.set_window_title()

        # Menus
        # TODO: Remove when all menus are migrated to use the Main Menu Plugin
        logger.info("Creating Menus...")
        from spyder.plugins.mainmenu.api import (
            ApplicationMenus, ToolsMenuSections, FileMenuSections)
        mainmenu = self.mainmenu
        self.edit_menu = mainmenu.get_application_menu("edit_menu")
        self.search_menu = mainmenu.get_application_menu("search_menu")
        self.source_menu = mainmenu.get_application_menu("source_menu")
        self.source_menu.aboutToShow.connect(self.update_source_menu)
        self.run_menu = mainmenu.get_application_menu("run_menu")
        self.debug_menu = mainmenu.get_application_menu("debug_menu")

        # Switcher shortcuts
        self.file_switcher_action = create_action(
                                    self,
                                    _('File switcher...'),
                                    icon=ima.icon('filelist'),
                                    tip=_('Fast switch between files'),
                                    triggered=self.open_switcher,
                                    context=Qt.ApplicationShortcut,
                                    id_='file_switcher')
        self.register_shortcut(self.file_switcher_action, context="_",
                               name="File switcher")
        self.symbol_finder_action = create_action(
                                    self, _('Symbol finder...'),
                                    icon=ima.icon('symbol_find'),
                                    tip=_('Fast symbol search in file'),
                                    triggered=self.open_symbolfinder,
                                    context=Qt.ApplicationShortcut,
                                    id_='symbol_finder')
        self.register_shortcut(self.symbol_finder_action, context="_",
                               name="symbol finder", add_shortcut_to_tip=True)

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

        self.edit_menu_actions += [self.undo_action, self.redo_action,
                                   None, self.cut_action, self.copy_action,
                                   self.paste_action, self.selectall_action,
                                   None] + self.editor.edit_menu_actions
        switcher_actions = [
            self.file_switcher_action,
            self.symbol_finder_action
        ]
        for switcher_action in switcher_actions:
            mainmenu.add_item_to_application_menu(
                    switcher_action,
                    menu_id=ApplicationMenus.File,
                    section=FileMenuSections.Switcher,
                    before_section=FileMenuSections.Restart)
        self.set_splash("")

        # Toolbars
        # TODO: Remove after finishing the migration
        logger.info("Creating toolbars...")
        toolbar = self.toolbar
        self.file_toolbar = toolbar.get_application_toolbar("file_toolbar")
        self.run_toolbar = toolbar.get_application_toolbar("run_toolbar")
        self.debug_toolbar = toolbar.get_application_toolbar("debug_toolbar")
        self.main_toolbar = toolbar.get_application_toolbar("main_toolbar")

        # Tools + External Tools (some of this depends on the Application
        # plugin)
        logger.info("Creating Tools menu...")

        spyder_path_action = create_action(
            self,
            _("PYTHONPATH manager"),
            None, icon=ima.icon('pythonpath'),
            triggered=self.show_path_manager,
            tip=_("PYTHONPATH manager"),
            id_='spyder_path_action')
        from spyder.plugins.application.container import (
            ApplicationActions, WinUserEnvDialog)
        winenv_action = None
        if WinUserEnvDialog:
            winenv_action = ApplicationActions.SpyderWindowsEnvVariables
        mainmenu.add_item_to_application_menu(
            spyder_path_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Tools,
            before=winenv_action,
            before_section=ToolsMenuSections.External
        )

        # Main toolbar
        from spyder.plugins.toolbar.api import (
            ApplicationToolbars, MainToolbarSections)
        self.toolbar.add_item_to_application_toolbar(
            spyder_path_action,
            toolbar_id=ApplicationToolbars.Main,
            section=MainToolbarSections.ApplicationSection
        )

        self.set_splash(_("Setting up main window..."))

        # TODO: Migrate to use the MainMenu Plugin instead of list of actions
        # Filling out menu/toolbar entries:
        add_actions(self.edit_menu, self.edit_menu_actions)
        add_actions(self.search_menu, self.search_menu_actions)
        add_actions(self.source_menu, self.source_menu_actions)
        add_actions(self.run_menu, self.run_menu_actions)
        add_actions(self.debug_menu, self.debug_menu_actions)

        # Emitting the signal notifying plugins that main window menu and
        # toolbar actions are all defined:
        self.all_actions_defined.emit()

    def __getattr__(self, attr):
        """
        Redefinition of __getattr__ to enable access to plugins.

        Loaded plugins can be accessed as attributes of the mainwindow
        as before, e.g self.console or self.main.console, preserving the
        same accessor as before.
        """
        # Mapping of new plugin identifiers vs old attributtes
        # names given for plugins
        if attr in self._INTERNAL_PLUGINS_MAPPING.keys():
            return self.get_plugin(self._INTERNAL_PLUGINS_MAPPING[attr])
        try:
            return self.get_plugin(attr)
        except SpyderAPIError:
            pass
        return super().__getattr__(attr)

    def pre_visible_setup(self):
        """
        Actions to be performed before the main window is visible.

        The actions here are related with setting up the main window.
        """
        logger.info("Setting up window...")

        for plugin_name in PLUGIN_REGISTRY:
            plugin_instance = PLUGIN_REGISTRY.get_plugin(plugin_name)
            try:
                plugin_instance.before_mainwindow_visible()
            except AttributeError:
                pass

        # Tabify external plugins which were installed after Spyder was
        # installed.
        # Note: This is only necessary the first time a plugin is loaded.
        # Afterwwrds, the plugin placement is recorded on the window hexstate,
        # which is loaded by the layouts plugin during the next session.
        for plugin_name in PLUGIN_REGISTRY.external_plugins:
            plugin_instance = PLUGIN_REGISTRY.get_plugin(plugin_name)
            if plugin_instance.get_conf('first_time', True):
                self.tabify_plugin(plugin_instance, Plugins.Console)

        if self.splash is not None:
            self.splash.hide()

        # Menu about to show
        for child in self.menuBar().children():
            if isinstance(child, QMenu):
                try:
                    child.aboutToShow.connect(self.update_edit_menu)
                    child.aboutToShow.connect(self.update_search_menu)
                except TypeError:
                    pass

        # Register custom layouts
        for plugin_name in PLUGIN_REGISTRY.external_plugins:
            plugin_instance = PLUGIN_REGISTRY.get_plugin(plugin_name)
            if hasattr(plugin_instance, 'CUSTOM_LAYOUTS'):
                if isinstance(plugin_instance.CUSTOM_LAYOUTS, list):
                    for custom_layout in plugin_instance.CUSTOM_LAYOUTS:
                        self.layouts.register_layout(
                            self, custom_layout)
                else:
                    logger.info(
                        'Unable to load custom layouts for {}. '
                        'Expecting a list of layout classes but got {}'
                        .format(plugin_name, plugin_instance.CUSTOM_LAYOUTS)
                    )
        self.layouts.update_layout_menu_actions()

        logger.info("*** End of MainWindow setup ***")
        self.is_starting_up = False


    def post_visible_setup(self):
        """
        Actions to be performed only after the main window's `show` method
        is triggered.
        """
        # Process pending events and hide splash before loading the
        # previous session.
        QApplication.processEvents()
        if self.splash is not None:
            self.splash.hide()

        # Call on_mainwindow_visible for all plugins.
        for plugin_name in PLUGIN_REGISTRY:
            plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
            try:
                plugin.on_mainwindow_visible()
                QApplication.processEvents()
            except AttributeError:
                pass

        self.restore_scrollbar_position.emit()

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

        # Update plugins toggle actions to show the "Switch to" plugin shortcut
        self._update_shortcuts_in_panes_menu()

        # Load project, if any.
        # TODO: Remove this reference to projects once we can send the command
        # line options to the plugins.
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

        # Raise the menuBar to the top of the main window widget's stack
        # Fixes spyder-ide/spyder#3887.
        self.menuBar().raise_()

        # To avoid regressions. We shouldn't have loaded the modules
        # below at this point.
        if DEV is not None:
            assert 'pandas' not in sys.modules
            assert 'matplotlib' not in sys.modules

        # Notify that the setup of the mainwindow was finished
        self.is_setting_up = False
        self.sig_setup_finished.emit()

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

        # TODO: Remove self.projects reference once there's an API for setting
        # window title.
        if self.projects is not None:
            path = self.projects.get_active_project_path()
            if path:
                path = path.replace(get_home_dir(), u'~')
                title = u'{0} - {1}'.format(path, title)

        self.base_title = title
        self.setWindowTitle(self.base_title)

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
        if not self.isMaximized() and not self.layouts.get_fullscreen_flag():
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)

        # To be used by the tour to be able to resize
        self.sig_resized.emit(event)

    def moveEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.layouts.get_fullscreen_flag():
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
        for plugin_name in PLUGIN_REGISTRY.external_plugins:
            plugin_instance = PLUGIN_REGISTRY.get_plugin(plugin_name)
            try:
                if isinstance(plugin_instance, SpyderDockablePlugin):
                    plugin.close_window()

                if not plugin.on_close(cancelable):
                    return False
            except AttributeError as e:
                logger.error(str(e))

        # Save window settings *after* closing all plugin windows, in order
        # to show them in their previous locations in the next session.
        # Fixes spyder-ide/spyder#12139
        prefix = 'window' + '/'
        self.layouts.save_current_window_settings(prefix)

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
            with open(self.SPYDER_PATH, 'r', encoding='utf-8') as f:
                path = f.read().splitlines()
            self.path = tuple(name for name in path if osp.isdir(name))

        if osp.isfile(self.SPYDER_NOT_ACTIVE_PATH):
            with open(self.SPYDER_NOT_ACTIVE_PATH, 'r',
                      encoding='utf-8') as f:
                not_active_path = f.read().splitlines()
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
        """Save preferences dialog size."""
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
        # FIXME: Why is this using the toolbars menu? A: To not be on top of
        # the toolbars.
        # Probably toolbars should be taken into account for this 'delta' only
        # when are visible
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
        window = create_window(MainWindow, app, None, options, None)
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
    if get_debug_level() > 0:
        delete_debug_log_files()
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

    if options.offline:
        CONF.set('ipython_console', 'info_widget', False)
        CONF.set('help', 'enable', False)
        CONF.set('onlinehelp', 'enable', False)

    # **** Set color for links ****
    set_links_color(app)

    # **** Create main window ****
    mainwindow = None
    try:
        if PY3 and options.report_segfault:
            import faulthandler
            with open(faulthandler_file, 'w') as f:
                faulthandler.enable(file=f)
                mainwindow = create_window(
                    MainWindow, app, splash, options, args
                )
        else:
            mainwindow = create_window(MainWindow, app, splash, options, args)
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

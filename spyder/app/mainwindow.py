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
from collections import OrderedDict
import configparser as cp
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
requirements.check_qt()

#==============================================================================
# Third-party imports
#==============================================================================
from qtpy.compat import from_qvariant
from qtpy.QtCore import (QCoreApplication, Qt, QTimer, Signal, Slot,
                         qInstallMessageHandler)
from qtpy.QtGui import QColor, QKeySequence
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
from spyder.app.find_plugins import (
    find_external_plugins, find_internal_plugins)
from spyder.app.utils import (
    create_application, create_splash_screen, create_window, ORIGINAL_SYS_EXIT,
    delete_debug_log_files, qt_message_handler, set_links_color, setup_logging,
    set_opengl_implementation)
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.widgets.mixins import SpyderMainWindowMixin
from spyder.config.base import (_, DEV, get_conf_path, get_debug_level,
                                get_home_dir, is_pynsist, running_in_mac_app,
                                running_under_pytest, STDERR)
from spyder.config.gui import is_dark_font_color
from spyder.config.main import OPEN_FILES_PORT
from spyder.config.manager import CONF
from spyder.config.utils import IMPORT_EXT, is_gtk_desktop
from spyder.otherplugins import get_spyderplugins_mods
from spyder.py3compat import to_text_string
from spyder.utils import encoding, programs
from spyder.utils.icon_manager import ima
from spyder.utils.misc import (select_port, getcwd_or_home,
                               get_python_executable)
from spyder.utils.palette import QStylePalette
from spyder.utils.qthelpers import (create_action, add_actions, file_uri,
                                    qapplication, start_file)
from spyder.utils.stylesheet import APP_STYLESHEET

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

#==============================================================================
# Install Qt messaage handler
#==============================================================================
qInstallMessageHandler(qt_message_handler)


#==============================================================================
# Main Window
#==============================================================================
class MainWindow(
    QMainWindow,
    SpyderMainWindowMixin,
    SpyderConfigurationAccessor
):
    """Spyder main window"""
    CONF_SECTION = 'main'

    DOCKOPTIONS = (
        QMainWindow.AllowTabbedDocks | QMainWindow.AllowNestedDocks |
        QMainWindow.AnimatedDocks
    )
    DEFAULT_LAYOUTS = 4
    INITIAL_CWD = getcwd_or_home()

    # Signals
    restore_scrollbar_position = Signal()
    sig_setup_finished = Signal()
    all_actions_defined = Signal()
    sig_open_external_file = Signal(str)
    sig_resized = Signal("QResizeEvent")
    sig_moved = Signal("QMoveEvent")
    sig_layout_setup_ready = Signal(object)  # Related to default layouts

    # To be removed in Spyder 6
    sig_pythonpath_changed = Signal(object, object)

    sig_window_state_changed = Signal(object)
    """
    This signal is emitted when the window state has changed (for instance,
    between maximized and minimized states).

    Parameters
    ----------
    window_state: Qt.WindowStates
        The window state.
    """

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
            # Use resample kwarg to prevent a blurry icon on Windows
            # See spyder-ide/spyder#18283
            qapp.setWindowIcon(ima.get_icon("windows_app_icon", resample=True))

        # Set default style
        self.default_style = str(qapp.style().objectName())

        # Save command line options for plugins to access them
        self._cli_options = options

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

        # Shortcut management data
        self.shortcut_data = []
        self.shortcut_queue = []

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
        self.file_toolbar = None
        self.file_toolbar_actions = []
        self.run_toolbar = None
        self.run_toolbar_actions = []
        self.debug_toolbar = None
        self.debug_toolbar_actions = []

        self.menus = []

        if running_under_pytest():
            # Show errors in internal console when testing.
            self.set_conf('show_internal_errors', False)

        self.CURSORBLINK_OSDEFAULT = QApplication.cursorFlashTime()

        if set_windows_appusermodelid is not None:
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
        if self.get_conf('current_version', default='') != __version__:
            self.set_conf('current_version', __version__)
            # Execute here the actions to be performed only once after
            # each update (there is nothing there for now, but it could
            # be useful some day...)

        # List of satellite widgets (registered in add_dockwidget):
        self.widgetlist = []

        # Flags used if closing() is called by the exit() shell command
        self.already_closed = False
        self.is_starting_up = True
        self.is_setting_up = True

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
                QMessageBox.warning(
                    None,
                    "Spyder",
                    _("An error occurred while creating a socket needed "
                      "by Spyder. Please, try to run as an Administrator "
                      "from cmd.exe the following command and then "
                      "restart your computer: <br><br><span "
                      "style=\'color: {color}\'><b>netsh winsock reset "
                      "</b></span><br>").format(
                          color=QStylePalette.COLOR_BACKGROUND_4)
                )
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

    # ---- Plugin handling methods
    # -------------------------------------------------------------------------
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
        """Determine if a given plugin is available."""
        return PLUGIN_REGISTRY.is_plugin_available(plugin_name)

    def show_status_message(self, message, timeout):
        """
        Show a status message in Spyder Main Window.
        """
        status_bar = self.statusBar()
        if status_bar.isVisible():
            status_bar.showMessage(message, timeout)

    def show_plugin_compatibility_message(self, plugin_name, message):
        """
        Show a compatibility message.
        """
        messageBox = QMessageBox(self)

        # Set attributes
        messageBox.setWindowModality(Qt.NonModal)
        messageBox.setAttribute(Qt.WA_DeleteOnClose)
        messageBox.setWindowTitle(_('Plugin compatibility check'))
        messageBox.setText(
            _("It was not possible to load the {} plugin. The problem "
              "was:<br><br>{}").format(plugin_name, message)
        )
        messageBox.setStandardButtons(QMessageBox.Ok)

        # Show message.
        # Note: All adjustments that require graphical properties of the widget
        # need to be done after this point.
        messageBox.show()

        # Center message
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - messageBox.width()) / 2
        y = (screen_geometry.height() - messageBox.height()) / 2
        messageBox.move(x, y)

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
            self.show_plugin_compatibility_message(plugin.get_name(), message)
            return

        # Connect plugin signals to main window methods
        plugin.sig_exception_occurred.connect(self.handle_exception)
        plugin.sig_free_memory_requested.connect(self.free_memory)
        plugin.sig_quit_requested.connect(self.close)
        plugin.sig_restart_requested.connect(self.restart)
        plugin.sig_redirect_stdio_requested.connect(
            self.redirect_internalshell_stdio)
        plugin.sig_status_message_requested.connect(self.show_status_message)
        plugin.sig_unmaximize_plugin_requested.connect(self.unmaximize_plugin)
        plugin.sig_unmaximize_plugin_requested[object].connect(
            self.unmaximize_plugin)

        if isinstance(plugin, SpyderDockablePlugin):
            plugin.sig_focus_changed.connect(self.plugin_focus_changed)
            plugin.sig_switch_to_plugin_requested.connect(
                self.switch_to_plugin)
            plugin.sig_update_ancestor_requested.connect(
                lambda: plugin.set_ancestor(self))

        # Connect Main window Signals to plugin signals
        self.sig_moved.connect(plugin.sig_mainwindow_moved)
        self.sig_resized.connect(plugin.sig_mainwindow_resized)
        self.sig_window_state_changed.connect(
            plugin.sig_mainwindow_state_changed)

        # Register plugin
        plugin._register(omit_conf=omit_conf)

        if isinstance(plugin, SpyderDockablePlugin):
            # Add dockwidget
            self.add_dockwidget(plugin)

            # Update margins
            margin = 0
            if self.get_conf('use_custom_margin'):
                margin = self.get_conf('custom_margin')
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
            except (cp.NoSectionError, cp.NoOptionError):
                pass

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
            shortcut = self.get_shortcut(
                name,
                context,
                plugin_name=plugin.CONF_SECTION
            )
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
        Switch to `plugin`.

        Notes
        -----
        This operation unmaximizes the current plugin (if any), raises
        this plugin to view (if it's hidden) and gives it focus (if
        possible).
        """
        self.layouts.switch_to_plugin(plugin, force_focus=force_focus)

    def unmaximize_plugin(self, not_this_plugin=None):
        """
        Unmaximize currently maximized plugin, if any.

        Parameters
        ----------
        not_this_plugin: SpyderDockablePlugin, optional
            Unmaximize plugin if the maximized one is `not_this_plugin`.
        """
        if not_this_plugin is None:
            self.layouts.unmaximize_dockwidget()
        else:
            self.layouts.unmaximize_other_dockwidget(
                plugin_instance=not_this_plugin)

    def remove_dockwidget(self, plugin):
        """
        Remove a plugin QDockWidget from the main window.
        """
        self.removeDockWidget(plugin.dockwidget)
        try:
            self.widgetlist.remove(plugin)
        except ValueError:
            pass

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
        console = self.get_plugin(Plugins.Console, error=False)
        if console:
            console.handle_exception(error_data)

    # ---- Window setup
    # -------------------------------------------------------------------------
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
                        shortcut = self.get_shortcut(
                            name, context, plugin_name=section)
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

        PLUGIN_REGISTRY.set_main(self)

        # TODO: Remove circular dependency between help and ipython console
        # and remove this import. Help plugin should take care of it
        from spyder.plugins.help.utils.sphinxify import CSS_PATH, DARK_CSS_PATH
        logger.info("*** Start of MainWindow setup ***")

        logger.info("Applying theme configuration...")
        ui_theme = self.get_conf('ui_theme', section='appearance')
        color_scheme = self.get_conf('selected', section='appearance')

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
        self.set_conf('css_path', css_path, section='appearance')

        # Status bar
        status = self.statusBar()
        status.setObjectName("StatusBar")
        status.showMessage(_("Welcome to Spyder!"), 5000)

        # Switcher instance
        logger.info("Loading switcher...")
        self.create_switcher()

        # Load and register internal and external plugins
        external_plugins = find_external_plugins()
        internal_plugins = find_internal_plugins()
        all_plugins = external_plugins.copy()
        all_plugins.update(internal_plugins.copy())

        # Determine 'enable' config for the plugins that have it
        enabled_plugins = {}
        registry_internal_plugins = {}
        registry_external_plugins = {}
        for plugin in all_plugins.values():
            plugin_name = plugin.NAME
            # Disable panes that use web widgets (currently Help and Online
            # Help) if the user asks for it.
            # See spyder-ide/spyder#16518
            if self._cli_options.no_web_widgets:
                if "help" in plugin_name:
                    continue
            plugin_main_attribute_name = (
                self._INTERNAL_PLUGINS_MAPPING[plugin_name]
                if plugin_name in self._INTERNAL_PLUGINS_MAPPING
                else plugin_name)
            if plugin_name in internal_plugins:
                registry_internal_plugins[plugin_name] = (
                    plugin_main_attribute_name, plugin)
            else:
                registry_external_plugins[plugin_name] = (
                    plugin_main_attribute_name, plugin)
            try:
                if self.get_conf("enable", section=plugin_main_attribute_name):
                    enabled_plugins[plugin_name] = plugin
                    PLUGIN_REGISTRY.set_plugin_enabled(plugin_name)
            except (cp.NoOptionError, cp.NoSectionError):
                enabled_plugins[plugin_name] = plugin
                PLUGIN_REGISTRY.set_plugin_enabled(plugin_name)

        PLUGIN_REGISTRY.set_all_internal_plugins(registry_internal_plugins)
        PLUGIN_REGISTRY.set_all_external_plugins(registry_external_plugins)

        # Instantiate internal Spyder 5 plugins
        for plugin_name in internal_plugins:
            if plugin_name in enabled_plugins:
                PluginClass = internal_plugins[plugin_name]
                if issubclass(PluginClass, SpyderPluginV2):
                    PLUGIN_REGISTRY.register_plugin(self, PluginClass,
                                                    external=False)

        # To be removed in Spyder 6
        ppm = self.get_plugin(Plugins.PythonpathManager)
        ppm.sig_pythonpath_changed.connect(self.sig_pythonpath_changed)

        # Instantiate internal Spyder 4 plugins
        for plugin_name in internal_plugins:
            if plugin_name in enabled_plugins:
                PluginClass = internal_plugins[plugin_name]
                if issubclass(PluginClass, SpyderPlugin):
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
            ApplicationMenus, FileMenuSections)
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
            id_='file_switcher'
        )
        self.register_shortcut(self.file_switcher_action, context="_",
                               name="File switcher")
        self.symbol_finder_action = create_action(
            self, _('Symbol finder...'),
            icon=ima.icon('symbol_find'),
            tip=_('Fast symbol search in file'),
            triggered=self.open_symbolfinder,
            context=Qt.ApplicationShortcut,
            id_='symbol_finder'
        )
        self.register_shortcut(self.symbol_finder_action, context="_",
                               name="symbol finder", add_shortcut_to_tip=True)

        def create_edit_action(text, tr_text, icon):
            textseq = text.split(' ')
            method_name = textseq[0].lower() + "".join(textseq[1:])
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
                                   None]
        if self.get_plugin(Plugins.Editor, error=False):
            self.edit_menu_actions += self.editor.edit_menu_actions

        switcher_actions = [
            self.file_switcher_action,
            self.symbol_finder_action
        ]
        for switcher_action in switcher_actions:
            mainmenu.add_item_to_application_menu(
                switcher_action,
                menu_id=ApplicationMenus.File,
                section=FileMenuSections.Switcher,
                before_section=FileMenuSections.Restart
            )
        self.set_splash("")

        # Toolbars
        # TODO: Remove after finishing the migration
        logger.info("Creating toolbars...")
        toolbar = self.toolbar
        self.file_toolbar = toolbar.get_application_toolbar("file_toolbar")
        self.run_toolbar = toolbar.get_application_toolbar("run_toolbar")
        self.debug_toolbar = toolbar.get_application_toolbar("debug_toolbar")

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
        try:
            if attr in self._INTERNAL_PLUGINS_MAPPING.keys():
                return self.get_plugin(
                    self._INTERNAL_PLUGINS_MAPPING[attr], error=False)
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
        if self.layouts is not None:
            self.layouts.register_custom_layouts()

        # Needed to ensure dockwidgets/panes layout size distribution
        # when a layout state is already present.
        # See spyder-ide/spyder#17945
        if (
            self.layouts is not None
            and self.get_conf('window/state', default=None)
        ):
            self.layouts.before_mainwindow_visible()

        # Tabify new plugins which were installed or created after Spyder ran
        # for the first time.
        # NOTE: **DO NOT** make layout changes after this point or new plugins
        # won't be tabified correctly.
        if self.layouts is not None:
            self.layouts.tabify_new_plugins()

        logger.info("*** End of MainWindow setup ***")
        self.is_starting_up = False

    def post_visible_setup(self):
        """
        Actions to be performed only after the main window's `show` method
        is triggered.
        """
        # This must be run before the main window is shown.
        # Fixes spyder-ide/spyder#12104
        self.layouts.on_mainwindow_visible()

        # Process pending events and hide splash screen before moving forward.
        QApplication.processEvents()
        if self.splash is not None:
            self.splash.hide()

        # Move the window to the primary screen if the previous location is not
        # visible to the user.
        self.move_to_primary_screen()

        # Call on_mainwindow_visible for all plugins, except Layout because it
        # needs to be called first (see above).
        for plugin_name in PLUGIN_REGISTRY:
            if plugin_name != Plugins.Layout:
                plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
                try:
                    plugin.on_mainwindow_visible()
                    QApplication.processEvents()
                except AttributeError:
                    pass

        self.restore_scrollbar_position.emit()

        # Server to maintain just one Spyder instance and open files in it if
        # the user tries to start other instances with
        # $ spyder foo.py
        if (
            self.get_conf('single_instance') and
            not self._cli_options.new_instance and
            self.open_files_server
        ):
            t = threading.Thread(target=self.start_open_files_server)
            t.daemon = True
            t.start()

            # Connect the window to the signal emitted by the previous server
            # when it gets a client connected to it
            self.sig_open_external_file.connect(self.open_external_file)

        # Update plugins toggle actions to show the "Switch to" plugin shortcut
        self._update_shortcuts_in_panes_menu()

        # Reopen last session if no project is active
        # NOTE: This needs to be after the calls to on_mainwindow_visible
        self.reopen_last_session()

        # Raise the menuBar to the top of the main window widget's stack
        # Fixes spyder-ide/spyder#3887.
        self.menuBar().raise_()

        # To avoid regressions. We shouldn't have loaded the modules
        # below at this point.
        if DEV is not None:
            assert 'pandas' not in sys.modules
            assert 'matplotlib' not in sys.modules

        # Restore undocked plugins
        self.restore_undocked_plugins()

        # Notify that the setup of the mainwindow was finished
        self.is_setting_up = False
        self.sig_setup_finished.emit()

    def reopen_last_session(self):
        """
        Reopen last session if no project is active.

        This can't be moved to on_mainwindow_visible in the editor because we
        need to let the same method on Projects run first.
        """
        projects = self.get_plugin(Plugins.Projects, error=False)
        editor = self.get_plugin(Plugins.Editor, error=False)
        reopen_last_session = False

        if projects:
            if projects.get_active_project() is None:
                reopen_last_session = True
        else:
            reopen_last_session = True

        if editor and reopen_last_session:
            logger.info("Restoring opened files from the previous session")
            editor.setup_open_files(close_previous_files=False)

    def restore_undocked_plugins(self):
        """Restore plugins that were undocked in the previous session."""
        logger.info("Restoring undocked plugins from the previous session")

        for plugin_name in PLUGIN_REGISTRY:
            plugin = PLUGIN_REGISTRY.get_plugin(plugin_name)
            if isinstance(plugin, SpyderDockablePlugin):
                if plugin.get_conf('undocked_on_window_close', default=False):
                    plugin.create_window()
            elif isinstance(plugin, SpyderPluginWidget):
                if plugin.get_option('undocked_on_window_close',
                                     default=False):
                    plugin._create_window()

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

        window_title = self._cli_options.window_title
        if window_title is not None:
            title += u' -- ' + to_text_string(window_title)

        # TODO: Remove self.projects reference once there's an API for setting
        # window title.
        projects = self.get_plugin(Plugins.Projects, error=False)
        if projects:
            path = projects.get_active_project_path()
            if path:
                path = path.replace(get_home_dir(), u'~')
                title = u'{0} - {1}'.format(path, title)

        self.base_title = title
        self.setWindowTitle(self.base_title)

    # TODO: To be removed after all actions are moved to their corresponding
    # plugins
    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_shortcut_to_tip=True, plugin_name=None):
        shortcuts = self.get_plugin(Plugins.Shortcuts, error=False)
        if shortcuts:
            shortcuts.register_shortcut(
                qaction_or_qshortcut,
                context,
                name,
                add_shortcut_to_tip=add_shortcut_to_tip,
                plugin_name=plugin_name,
            )

    def unregister_shortcut(self, qaction_or_qshortcut, context, name,
                            add_shortcut_to_tip=True, plugin_name=None):
        shortcuts = self.get_plugin(Plugins.Shortcuts, error=False)
        if shortcuts:
            shortcuts.unregister_shortcut(
                qaction_or_qshortcut,
                context,
                name,
                add_shortcut_to_tip=add_shortcut_to_tip,
                plugin_name=plugin_name,
            )

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def createPopupMenu(self):
        return self.application.get_application_context_menu(parent=self)

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
        if hasattr(self, 'layouts') and self.layouts is not None:
            if (
                not self.isMaximized()
                and not self.layouts.get_fullscreen_flag()
            ):
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

    # ---- Other
    # -------------------------------------------------------------------------
    def update_source_menu(self):
        """Update source menu options that vary dynamically."""
        # This is necessary to avoid an error at startup.
        # Fixes spyder-ide/spyder#14901
        try:
            editor = self.get_plugin(Plugins.Editor, error=False)
            if editor:
                editor.refresh_formatter_name()
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
        if textedit_properties is None:  # widget is not an editor/console
            return
        # !!! Below this line, widget is expected to be a QPlainTextEdit
        #     instance
        console, not_readonly, readwrite_editor = textedit_properties

        if hasattr(self, 'editor'):
            # Editor has focus and there is no file opened in it
            if (not console and not_readonly and self.editor
                    and not self.editor.is_file_opened()):
                return

        # Disabling all actions to begin with
        for child in self.edit_menu.actions():
            child.setEnabled(False)

        self.selectall_action.setEnabled(True)

        # Undo, redo
        self.undo_action.setEnabled(readwrite_editor
                                    and widget.document().isUndoAvailable())
        self.redo_action.setEnabled(readwrite_editor
                                    and widget.document().isRedoAvailable())

        # Copy, cut, paste, delete
        has_selection = widget.has_selected_text()
        self.copy_action.setEnabled(has_selection)
        self.cut_action.setEnabled(has_selection and not_readonly)
        self.paste_action.setEnabled(not_readonly)

        # Comment, uncomment, indent, unindent...
        if not console and not_readonly:
            # This is the editor and current file is writable
            if self.get_plugin(Plugins.Editor, error=False):
                for action in self.editor.edit_menu_actions:
                    action.setEnabled(True)

    def update_search_menu(self):
        """Update search menu"""
        # Disabling all actions except the last one
        # (which is Find in files) to begin with
        for child in self.search_menu.actions()[:-1]:
            child.setEnabled(False)

        widget, textedit_properties = self.get_focus_widget_properties()
        if textedit_properties is None:  # widget is not an editor/console
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

    def change_last_focused_widget(self, old, now):
        """To keep track of to the last focused widget"""
        if (now is None and QApplication.activeWindow() is not None):
            QApplication.activeWindow().setFocus()
            self.last_focused_widget = QApplication.focusWidget()
        elif now is not None:
            self.last_focused_widget = now

        self.previous_focused_widget =  old

    def closing(self, cancelable=False, close_immediately=False):
        """Exit tasks"""
        if self.already_closed or self.is_starting_up:
            return True

        self.layouts.save_visible_plugins()

        self.plugin_registry = PLUGIN_REGISTRY

        if cancelable and self.get_conf('prompt_on_exit'):
            reply = QMessageBox.critical(self, 'Spyder',
                                         'Do you really want to exit?',
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return False

        can_close = self.plugin_registry.delete_all_plugins(
            excluding={Plugins.Layout},
            close_immediately=close_immediately)

        if not can_close and not close_immediately:
            return False

        # Save window settings *after* closing all plugin windows, in order
        # to show them in their previous locations in the next session.
        # Fixes spyder-ide/spyder#12139
        prefix = 'window' + '/'
        if self.layouts is not None:
            self.layouts.save_current_window_settings(prefix)
            try:
                layouts_container = self.layouts.get_container()
                if layouts_container:
                    layouts_container.close()
                    layouts_container.deleteLater()
                self.layouts.deleteLater()
                self.plugin_registry.delete_plugin(
                    Plugins.Layout, teardown=False)
            except RuntimeError:
                pass

        self.already_closed = True

        if self.get_conf('single_instance') and self.open_files_server:
            self.open_files_server.close()

        QApplication.processEvents()

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
        console = self.get_plugin(Plugins.Console, error=False)
        if console:
            if state:
                console.redirect_stds()
            else:
                console.restore_stds()

    def open_external_console(self, fname, wdir, args, interact, debug, python,
                              python_args, systerm, post_mortem=False):
        """Open external console"""
        if systerm:
            # Running script in an external system terminal
            try:
                if self.get_conf('default', section='main_interpreter'):
                    executable = get_python_executable()
                else:
                    executable = self.get_conf(
                        'executable',
                        section='main_interpreter'
                    )
                pypath = self.get_conf('spyder_pythonpath', default=None,
                                       section='pythonpath_manager')
                programs.run_python_script_in_terminal(
                    fname, wdir, args, interact, debug, python_args,
                    executable, pypath
                )
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
        editor = self.get_plugin(Plugins.Editor, error=False)
        variableexplorer = self.get_plugin(
            Plugins.VariableExplorer, error=False)

        if encoding.is_text_file(fname):
            if editor:
                editor.load(fname)
        elif variableexplorer is not None and ext in IMPORT_EXT:
            variableexplorer.get_widget().import_data(fname)
        elif not external:
            fname = file_uri(fname)
            start_file(fname)

    def get_initial_working_directory(self):
        """Return the initial working directory."""
        return self.INITIAL_CWD

    def open_external_file(self, fname):
        """
        Open external files that can be handled either by the Editor or the
        variable explorer inside Spyder.
        """
        # Check that file exists
        fname = encoding.to_unicode_from_fs(fname)
        initial_cwd = self.get_initial_working_directory()
        if osp.exists(osp.join(initial_cwd, fname)):
            fpath = osp.join(initial_cwd, fname)
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

    def get_spyder_pythonpath(self):
        """
        This is here to provide compatibility for plugins that make use of the
        Pythonpath managed by Spyder.

        Notes
        -----
        This  method is going to be removed in Spyder 6.
        """
        ppm = self.get_plugin(Plugins.PythonpathManager)
        return ppm.get_spyder_pythonpath()

    # ---- Preferences
    # -------------------------------------------------------------------------
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
        if self.get_conf('vertical_tabs'):
            default = default|QMainWindow.VerticalTabs
        self.setDockOptions(default)

        self.apply_panes_settings()

        if self.get_conf('use_custom_cursor_blinking'):
            qapp.setCursorFlashTime(
                self.get_conf('custom_cursor_blinking'))
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
                if self.get_conf('use_custom_margin'):
                    margin = self.get_conf('custom_margin')
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

    # ---- Open files server
    # -------------------------------------------------------------------------
    def start_open_files_server(self):
        self.open_files_server.setsockopt(socket.SOL_SOCKET,
                                          socket.SO_REUSEADDR, 1)
        port = select_port(default_port=OPEN_FILES_PORT)
        self.set_conf('open_files_port', port)

        # This is necessary in case it's not possible to bind a port for the
        # server in the system.
        # Fixes spyder-ide/spyder#18262
        try:
            self.open_files_server.bind(('127.0.0.1', port))
        except OSError:
            self.open_files_server = None
            return

        # Number of petitions the server can queue
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
                if self.already_closed:
                    return
                raise
            fname = req.recv(1024)
            fname = fname.decode('utf-8')
            self.sig_open_external_file.emit(fname)
            req.sendall(b' ')

    # ---- Restart Spyder
    # -------------------------------------------------------------------------
    def restart(self, reset=False, close_immediately=False):
        """Wrapper to handle plugins request to restart Spyder."""
        self.application.restart(
            reset=reset, close_immediately=close_immediately)

    # ---- Global Switcher
    # -------------------------------------------------------------------------
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

    # **** Set color for links ****
    set_links_color(app)

    # **** Create main window ****
    mainwindow = None
    try:
        if options.report_segfault:
            import faulthandler
            with open(faulthandler_file, 'w') as f:
                faulthandler.enable(file=f)
                mainwindow = create_window(
                    MainWindow, app, splash, options, args
                )
        else:
            mainwindow = create_window(MainWindow, app, splash, options, args)
    except FontError:
        QMessageBox.information(
            None, "Spyder",
            "Spyder was unable to load the <i>Spyder 3</i> "
            "icon theme. That's why it's going to fallback to the "
            "theme used in Spyder 2.<br><br>"
            "For that, please close this window and start Spyder again."
        )
        CONF.set('appearance', 'icon_theme', 'spyder 2')
    if mainwindow is None:
        # An exception occurred
        if splash is not None:
            splash.hide()
        return

    ORIGINAL_SYS_EXIT()


if __name__ == "__main__":
    main()

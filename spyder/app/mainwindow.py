# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder, the Scientific PYthon Development EnviRonment
=====================================================

Developped and maintained by the Spyder Project
Contributors

Copyright © Spyder Project Contributors
Licensed under the terms of the MIT License
(see spyder/__init__.py for details)
"""

# =============================================================================
# Stdlib imports
# =============================================================================
from __future__ import print_function

import atexit
import errno
import os
import os.path as osp
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import traceback


#==============================================================================
# Keeping a reference to the original sys.exit before patching it
#==============================================================================
ORIGINAL_SYS_EXIT = sys.exit


#==============================================================================
# Check requirements
#==============================================================================
from spyder import requirements
requirements.check_path()
requirements.check_qt()


#==============================================================================
# Windows only: support for hiding console window when started with python.exe
#==============================================================================
set_attached_console_visible = None
is_attached_console_visible = None
set_windows_appusermodelid = None
if os.name == 'nt':
    from spyder.utils.windows import (set_attached_console_visible,
                                      is_attached_console_visible,
                                      set_windows_appusermodelid)


#==============================================================================
# Workaround: importing rope.base.project here, otherwise this module can't
# be imported if Spyder was executed from another folder than spyder
#==============================================================================
try:
    import rope.base.project  # analysis:ignore
except ImportError:
    pass


#==============================================================================
# Qt imports
#==============================================================================
from qtpy import API, PYQT5
from qtpy.compat import from_qvariant
from qtpy.QtCore import (QByteArray, QCoreApplication, QPoint, QSize, Qt,
                         QThread, QTimer, QUrl, Signal, Slot)
from qtpy.QtGui import QColor, QDesktopServices, QIcon, QKeySequence, QPixmap
from qtpy.QtWidgets import (QAction, QApplication, QDockWidget, QMainWindow,
                            QMenu, QMessageBox, QShortcut, QSplashScreen,
                            QStyleFactory)
# Avoid a "Cannot mix incompatible Qt library" error on Windows platforms
# when PySide is selected by the QT_API environment variable and when PyQt4
# is also installed (or any other Qt-based application prepending a directory
# containing incompatible Qt DLLs versions in PATH):
from qtpy import QtSvg  # analysis:ignore

# Avoid a bug in Qt: https://bugreports.qt.io/browse/QTBUG-46720
from qtpy import QtWebEngineWidgets  # analysis:ignore

# To catch font errors in QtAwesome
from qtawesome.iconic_font import FontError


#==============================================================================
# Proper high DPI scaling is available in Qt >= 5.6.0. This attibute must
# be set before creating the application. 
#==============================================================================
from spyder.config.main import CONF

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, CONF.get('main', 'high_dpi_scaling'))


#==============================================================================
# Create our QApplication instance here because it's needed to render the
# splash screen created below
#==============================================================================
from spyder.utils.qthelpers import qapplication, MENU_SEPARATOR
from spyder.config.base import get_image_path
MAIN_APP = qapplication()

if PYQT5:
    APP_ICON = QIcon(get_image_path("spyder.svg"))
else:
    APP_ICON = QIcon(get_image_path("spyder.png"))

MAIN_APP.setWindowIcon(APP_ICON)

#==============================================================================
# Create splash screen out of MainWindow to reduce perceived startup time. 
#==============================================================================
from spyder.config.base import _, get_image_path, DEV, PYTEST

if not PYTEST:
    SPLASH = QSplashScreen(QPixmap(get_image_path('splash.svg')))
    SPLASH_FONT = SPLASH.font()
    SPLASH_FONT.setPixelSize(10)
    SPLASH.setFont(SPLASH_FONT)
    SPLASH.show()
    SPLASH.showMessage(_("Initializing..."), Qt.AlignBottom | Qt.AlignCenter |
                    Qt.AlignAbsolute, QColor(Qt.white))
    QApplication.processEvents()
else:
    SPLASH = None

#==============================================================================
# Local utility imports
#==============================================================================
from spyder import __version__, __project_url__, __forum_url__, get_versions
from spyder.config.base import (get_conf_path, get_module_data_path,
                                get_module_source_path, STDERR, DEBUG,
                                debug_print, MAC_APP_NAME, get_home_dir,
                                running_in_mac_app, get_module_path,
                                reset_config_files)
from spyder.config.main import OPEN_FILES_PORT
from spyder.config.utils import IMPORT_EXT, is_gtk_desktop
from spyder.app.cli_options import get_options
from spyder import dependencies
from spyder.py3compat import (is_text_string, to_text_string,
                              PY3, qbytearray_to_str, configparser as cp)
from spyder.utils import encoding, programs
from spyder.utils import icon_manager as ima
from spyder.utils.introspection import module_completion
from spyder.utils.programs import is_module_installed
from spyder.utils.misc import select_port, getcwd_or_home
from spyder.widgets.fileswitcher import FileSwitcher

#==============================================================================
# Local gui imports
#==============================================================================
# NOTE: Move (if possible) import's of widgets and plugins exactly where they
# are needed in MainWindow to speed up perceived startup time (i.e. the time
# from clicking the Spyder icon to showing the splash screen).
try:
    from spyder.utils.environ import WinUserEnvDialog
except ImportError:
    WinUserEnvDialog = None  # analysis:ignore

from spyder.utils.qthelpers import (create_action, add_actions, get_icon,
                                    add_shortcut_to_tooltip,
                                    create_module_bookmark_actions,
                                    create_program_action, DialogManager,
                                    create_python_script_action, file_uri)
from spyder.config.gui import get_shortcut
from spyder.otherplugins import get_spyderplugins_mods
from spyder.app import tour


#==============================================================================
# Get the cwd before initializing WorkingDirectory, which sets it to the one
# used in the last session
#==============================================================================
CWD = getcwd_or_home()


#==============================================================================
# Spyder's main window widgets utilities
#==============================================================================
def get_python_doc_path():
    """
    Return Python documentation path
    (Windows: return the PythonXX.chm path if available)
    """
    if os.name == 'nt':
        doc_path = osp.join(sys.prefix, "Doc")
        if not osp.isdir(doc_path):
            return
        python_chm = [path for path in os.listdir(doc_path)
                      if re.match(r"(?i)Python[0-9]{3,6}.chm", path)]
        if python_chm:
            return file_uri(osp.join(doc_path, python_chm[0]))
    else:
        vinf = sys.version_info
        doc_path = '/usr/share/doc/python%d.%d/html' % (vinf[0], vinf[1])
    python_doc = osp.join(doc_path, "index.html")
    if osp.isfile(python_doc):
        return file_uri(python_doc)


def get_focus_python_shell():
    """Extract and return Python shell from widget
    Return None if *widget* is not a Python shell (e.g. IPython kernel)"""
    widget = QApplication.focusWidget()
    from spyder.widgets.shell import PythonShellWidget
    from spyder.widgets.externalshell.pythonshell import ExternalPythonShell
    if isinstance(widget, PythonShellWidget):
        return widget
    elif isinstance(widget, ExternalPythonShell):
        return widget.shell


#==============================================================================
# Main Window
#==============================================================================
class MainWindow(QMainWindow):
    """Spyder main window"""
    DOCKOPTIONS = QMainWindow.AllowTabbedDocks|QMainWindow.AllowNestedDocks
    CURSORBLINK_OSDEFAULT = QApplication.cursorFlashTime()
    SPYDER_PATH = get_conf_path('path')
    SPYDER_NOT_ACTIVE_PATH = get_conf_path('not_active_path')
    BOOKMARKS = (
         ('Python2', "https://docs.python.org/2/index.html",
          _("Python2 documentation")),
         ('Python3', "https://docs.python.org/3/index.html",
          _("Python3 documentation")),
         ('numpy', "http://docs.scipy.org/doc/",
          _("Numpy and Scipy documentation")),
         ('matplotlib', "http://matplotlib.sourceforge.net/contents.html",
          _("Matplotlib documentation")),
         ('PyQt4',
          "http://pyqt.sourceforge.net/Docs/PyQt4/",
          _("PyQt4 Reference Guide")),
         ('PyQt4',
          "http://pyqt.sourceforge.net/Docs/PyQt4/classes.html",
          _("PyQt4 API Reference")),
         ('PyQt5',
          "http://pyqt.sourceforge.net/Docs/PyQt5/",
          _("PyQt5 Reference Guide")),
         ('PyQt5',
          "http://pyqt.sourceforge.net/Docs/PyQt5/class_reference.html",
          _("PyQt5 API Reference")),
         ('winpython', "https://winpython.github.io/",
          _("WinPython"))
                )

    # Signals
    restore_scrollbar_position = Signal()
    all_actions_defined = Signal()
    sig_pythonpath_changed = Signal()
    sig_open_external_file = Signal(str)
    sig_resized = Signal("QResizeEvent")  # related to interactive tour
    sig_moved = Signal("QMoveEvent")      # related to interactive tour

    def __init__(self, options=None):
        QMainWindow.__init__(self)

        qapp = QApplication.instance()
        if PYQT5:
            # Enabling scaling for high dpi
            qapp.setAttribute(Qt.AA_UseHighDpiPixmaps)
        self.default_style = str(qapp.style().objectName())

        self.dialog_manager = DialogManager()

        self.init_workdir = options.working_directory
        self.profile = options.profile
        self.multithreaded = options.multithreaded
        self.new_instance = options.new_instance
        self.open_project = options.open_project

        self.debug_print("Start of MainWindow constructor")

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

        # Create our TEMPDIR
        if not osp.isdir(programs.TEMPDIR):
            os.mkdir(programs.TEMPDIR)

        # Shortcut management data
        self.shortcut_data = []

        # Loading Spyder path
        self.path = []
        self.not_active_path = []
        self.project_path = []
        if osp.isfile(self.SPYDER_PATH):
            self.path, _x = encoding.readlines(self.SPYDER_PATH)
            self.path = [name for name in self.path if osp.isdir(name)]
        if osp.isfile(self.SPYDER_NOT_ACTIVE_PATH):
            self.not_active_path, _x = \
                encoding.readlines(self.SPYDER_NOT_ACTIVE_PATH)
            self.not_active_path = \
                [name for name in self.not_active_path if osp.isdir(name)]
        self.remove_path_from_sys_path()
        self.add_path_to_sys_path()

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
        self.findinfiles = None
        self.thirdparty_plugins = []

        # Tour  # TODO: Should I consider it a plugin?? or?
        self.tour = None
        self.tours_available = None
        
        # File switcher
        self.fileswitcher = None

        # Check for updates Thread and Worker, refereces needed to prevent
        # segfaulting
        self.check_updates_action = None
        self.thread_updates = None
        self.worker_updates = None
        self.give_updates_feedback = True

        # Preferences
        from spyder.plugins.configdialog import (MainConfigPage, 
                                                 ColorSchemeConfigPage)
        from spyder.plugins.shortcuts import ShortcutsConfigPage
        from spyder.plugins.runconfig import RunConfigPage
        from spyder.plugins.maininterpreter import MainInterpreterConfigPage
        self.general_prefs = [MainConfigPage, ShortcutsConfigPage,
                              ColorSchemeConfigPage, MainInterpreterConfigPage,
                              RunConfigPage]
        self.prefs_index = None
        self.prefs_dialog_size = None

        # Quick Layouts and Dialogs
        from spyder.plugins.layoutdialog import (LayoutSaveDialog,
                                                 LayoutSettingsDialog)
        self.dialog_layout_save = LayoutSaveDialog
        self.dialog_layout_settings = LayoutSettingsDialog

        # Actions
        self.lock_dockwidgets_action = None
        self.show_toolbars_action = None
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
        self.file_menu = None
        self.file_menu_actions = []
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
        self.tools_menu = None
        self.tools_menu_actions = []
        self.external_tools_menu = None # We must keep a reference to this,
        # otherwise the external tools menu is lost after leaving setup method
        self.external_tools_menu_actions = []
        self.view_menu = None
        self.plugins_menu = None
        self.plugins_menu_actions = []
        self.toolbars_menu = None
        self.help_menu = None
        self.help_menu_actions = []

        # Status bar widgets
        self.mem_status = None
        self.cpu_status = None

        # Toolbars
        self.visible_toolbars = []
        self.toolbarslist = []
        self.main_toolbar = None
        self.main_toolbar_actions = []
        self.file_toolbar = None
        self.file_toolbar_actions = []
        self.edit_toolbar = None
        self.edit_toolbar_actions = []
        self.search_toolbar = None
        self.search_toolbar_actions = []
        self.source_toolbar = None
        self.source_toolbar_actions = []
        self.run_toolbar = None
        self.run_toolbar_actions = []
        self.debug_toolbar = None
        self.debug_toolbar_actions = []
        self.layout_toolbar = None
        self.layout_toolbar_actions = []


        # Set Window title and icon
        if DEV is not None:
            title = "Spyder %s (Python %s.%s)" % (__version__,
                                                  sys.version_info[0],
                                                  sys.version_info[1])
        else:
            title = "Spyder (Python %s.%s)" % (sys.version_info[0],
                                               sys.version_info[1])
        if DEBUG:
            title += " [DEBUG MODE %d]" % DEBUG
        if options.window_title is not None:
            title += ' -- ' + options.window_title

        if DEBUG or PYTEST:
            # Show errors in internal console when developing or testing.
            CONF.set('main', 'show_internal_console_if_traceback', True)


        self.base_title = title
        self.update_window_title()

        if set_windows_appusermodelid != None:
            res = set_windows_appusermodelid()
            debug_print("appusermodelid: " + str(res))

        # Setting QTimer if running in travis
        test_travis = os.environ.get('TEST_CI_APP', None)
        if test_travis is not None:
            global MAIN_APP
            timer_shutdown_time = 30000
            self.timer_shutdown = QTimer(self)
            self.timer_shutdown.timeout.connect(MAIN_APP.quit)
            self.timer_shutdown.start(timer_shutdown_time)

        # Showing splash screen
        self.splash = SPLASH
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

        self.dockwidgets_locked = CONF.get('main', 'panes_locked')
        self.floating_dockwidgets = []
        self.window_size = None
        self.window_position = None
        self.state_before_maximizing = None
        self.current_quick_layout = None
        self.previous_layout_settings = None  # TODO: related to quick layouts
        self.last_plugin = None
        self.fullscreen_flag = None # isFullscreen does not work as expected
        # The following flag remember the maximized state even when
        # the window is in fullscreen mode:
        self.maximized_flag = None

        # To keep track of the last focused widget
        self.last_focused_widget = None
        self.previous_focused_widget = None

        # Server to open external files on a single instance
        # This is needed in order to handle socket creation problems.
        # See issue 4132
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
        self.apply_settings()
        self.debug_print("End of MainWindow constructor")

    def debug_print(self, message):
        """Debug prints"""
        debug_print(message)

    #---- Window setup
    def create_toolbar(self, title, object_name, iconsize=24):
        """Create and return toolbar with *title* and *object_name*"""
        toolbar = self.addToolBar(title)
        toolbar.setObjectName(object_name)
        toolbar.setIconSize(QSize(iconsize, iconsize))
        self.toolbarslist.append(toolbar)
        return toolbar

    def setup(self):
        """Setup main window"""
        self.debug_print("*** Start of MainWindow setup ***")
        self.debug_print("  ..core actions")
        self.close_dockwidget_action = create_action(self,
                                    icon=ima.icon('DialogCloseButton'),
                                    text=_("Close current pane"),
                                    triggered=self.close_current_dockwidget,
                                    context=Qt.ApplicationShortcut)
        self.register_shortcut(self.close_dockwidget_action, "_",
                               "Close pane")
        self.lock_dockwidgets_action = create_action(self, _("Lock panes"),
                                        toggled=self.toggle_lock_dockwidgets,
                                        context=Qt.ApplicationShortcut)
        self.register_shortcut(self.lock_dockwidgets_action, "_",
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
        # File switcher shortcuts
        self.file_switcher_action = create_action(
                                    self,
                                    _('File switcher...'),
                                    icon=ima.icon('filelist'),
                                    tip=_('Fast switch between files'),
                                    triggered=self.open_fileswitcher,
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
                               name="symbol finder", add_sc_to_tip=True)
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

        namespace = None
        self.debug_print("  ..toolbars")
        # File menu/toolbar
        self.file_menu = self.menuBar().addMenu(_("&File"))
        self.file_toolbar = self.create_toolbar(_("File toolbar"),
                                                "file_toolbar")

        # Edit menu/toolbar
        self.edit_menu = self.menuBar().addMenu(_("&Edit"))
        self.edit_toolbar = self.create_toolbar(_("Edit toolbar"),
                                                "edit_toolbar")

        # Search menu/toolbar
        self.search_menu = self.menuBar().addMenu(_("&Search"))
        self.search_toolbar = self.create_toolbar(_("Search toolbar"),
                                                    "search_toolbar")

        # Source menu/toolbar
        self.source_menu = self.menuBar().addMenu(_("Sour&ce"))
        self.source_toolbar = self.create_toolbar(_("Source toolbar"),
                                                    "source_toolbar")

        # Run menu/toolbar
        self.run_menu = self.menuBar().addMenu(_("&Run"))
        self.run_toolbar = self.create_toolbar(_("Run toolbar"),
                                                "run_toolbar")

        # Debug menu/toolbar
        self.debug_menu = self.menuBar().addMenu(_("&Debug"))
        self.debug_toolbar = self.create_toolbar(_("Debug toolbar"),
                                                    "debug_toolbar")

        # Consoles menu/toolbar
        self.consoles_menu = self.menuBar().addMenu(_("C&onsoles"))

        # Projects menu
        self.projects_menu = self.menuBar().addMenu(_("&Projects"))

        # Tools menu
        self.tools_menu = self.menuBar().addMenu(_("&Tools"))

        # View menu
        self.view_menu = self.menuBar().addMenu(_("&View"))

        # Help menu
        self.help_menu = self.menuBar().addMenu(_("&Help"))

        # Status bar
        status = self.statusBar()
        status.setObjectName("StatusBar")
        status.showMessage(_("Welcome to Spyder!"), 5000)


        self.debug_print("  ..tools")
        # Tools + External Tools
        prefs_action = create_action(self, _("Pre&ferences"),
                                        icon=ima.icon('configure'),
                                        triggered=self.edit_preferences,
                                        context=Qt.ApplicationShortcut)
        self.register_shortcut(prefs_action, "_", "Preferences",
                               add_sc_to_tip=True)
        spyder_path_action = create_action(self,
                                _("PYTHONPATH manager"),
                                None, icon=ima.icon('pythonpath'),
                                triggered=self.path_manager_callback,
                                tip=_("Python Path Manager"),
                                menurole=QAction.ApplicationSpecificRole)
        update_modules_action = create_action(self,
                                    _("Update module names list"),
                                    triggered=lambda:
                                                module_completion.reset(),
                                    tip=_("Refresh list of module names "
                                            "available in PYTHONPATH"))
        reset_spyder_action = create_action(
            self, _("Reset Spyder to factory defaults"),
            triggered=self.reset_spyder)
        self.tools_menu_actions = [prefs_action, spyder_path_action]
        if WinUserEnvDialog is not None:
            winenv_action = create_action(self,
                    _("Current user environment variables..."),
                    icon='win_env.png',
                    tip=_("Show and edit current user environment "
                            "variables in Windows registry "
                            "(i.e. for all sessions)"),
                    triggered=self.win_env)
            self.tools_menu_actions.append(winenv_action)
        self.tools_menu_actions += [reset_spyder_action, MENU_SEPARATOR,
                                    update_modules_action]

        # External Tools submenu
        self.external_tools_menu = QMenu(_("External Tools"))
        self.external_tools_menu_actions = []
        # WinPython control panel
        self.wp_action = create_action(self, _("WinPython control panel"),
                    icon=get_icon('winpython.svg'),
                    triggered=lambda:
                    programs.run_python_script('winpython', 'controlpanel'))
        if os.name == 'nt' and is_module_installed('winpython'):
            self.external_tools_menu_actions.append(self.wp_action)
        # Qt-related tools
        additact = []
        for name in ("designer-qt4", "designer"):
            qtdact = create_program_action(self, _("Qt Designer"),
                                            name, 'qtdesigner.png')
            if qtdact:
                break
        for name in ("linguist-qt4", "linguist"):
            qtlact = create_program_action(self, _("Qt Linguist"),
                                            "linguist", 'qtlinguist.png')
            if qtlact:
                break
        args = ['-no-opengl'] if os.name == 'nt' else []
        qteact = create_python_script_action(self,
                                _("Qt examples"), 'qt.png', "PyQt4",
                                osp.join("examples", "demos",
                                        "qtdemo", "qtdemo"), args)
        for act in (qtdact, qtlact, qteact):
            if act:
                additact.append(act)
        if additact and is_module_installed('winpython'):
            self.external_tools_menu_actions += [None] + additact

        # Guidata and Sift
        self.debug_print("  ..sift?")
        gdgq_act = []
        # Guidata and Guiqwt don't support PyQt5 yet and they fail
        # with an AssertionError when imported using those bindings
        # (see issue 2274)
        try:
            from guidata import configtools
            from guidata import config       # analysis:ignore
            guidata_icon = configtools.get_icon('guidata.svg')
            guidata_act = create_python_script_action(self,
                                    _("guidata examples"), guidata_icon,
                                    "guidata",
                                    osp.join("tests", "__init__"))
            gdgq_act += [guidata_act]
        except (ImportError, AssertionError):
            pass
        try:
            from guidata import configtools
            from guiqwt import config  # analysis:ignore
            guiqwt_icon = configtools.get_icon('guiqwt.svg')
            guiqwt_act = create_python_script_action(self,
                            _("guiqwt examples"), guiqwt_icon, "guiqwt",
                            osp.join("tests", "__init__"))
            if guiqwt_act:
                gdgq_act += [guiqwt_act]
            sift_icon = configtools.get_icon('sift.svg')
            sift_act = create_python_script_action(self, _("Sift"),
                        sift_icon, "guiqwt", osp.join("tests", "sift"))
            if sift_act:
                gdgq_act += [sift_act]
        except (ImportError, AssertionError):
            pass
        if gdgq_act:
            self.external_tools_menu_actions += [None] + gdgq_act

        # ViTables
        vitables_act = create_program_action(self, _("ViTables"),
                                                "vitables", 'vitables.png')
        if vitables_act:
            self.external_tools_menu_actions += [None, vitables_act]

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
        self.register_shortcut(self.fullscreen_action, "_",
                               "Fullscreen mode", add_sc_to_tip=True)

        # Main toolbar
        self.main_toolbar_actions = [self.maximize_action,
                                     self.fullscreen_action,
                                     None,
                                     prefs_action, spyder_path_action]

        self.main_toolbar = self.create_toolbar(_("Main toolbar"),
                                                "main_toolbar")

        # Internal console plugin
        self.debug_print("  ..plugin: internal console")
        from spyder.plugins.console import Console
        self.console = Console(self, namespace, exitfunc=self.closing,
                            profile=self.profile,
                            multithreaded=self.multithreaded,
                            message=_("Spyder Internal Console\n\n"
                                    "This console is used to report application\n"
                                    "internal errors and to inspect Spyder\n"
                                    "internals with the following commands:\n"
                                    "  spy.app, spy.window, dir(spy)\n\n"
                                    "Please don't use it to run your code\n\n"))
        self.console.register_plugin()

        # Working directory plugin
        self.debug_print("  ..plugin: working directory")
        from spyder.plugins.workingdirectory import WorkingDirectory
        self.workingdirectory = WorkingDirectory(self, self.init_workdir, main=self)
        self.workingdirectory.register_plugin()
        self.toolbarslist.append(self.workingdirectory.toolbar)

        # Help plugin
        if CONF.get('help', 'enable'):
            self.set_splash(_("Loading help..."))
            from spyder.plugins.help import Help
            self.help = Help(self)
            self.help.register_plugin()

        # Outline explorer widget
        if CONF.get('outline_explorer', 'enable'):
            self.set_splash(_("Loading outline explorer..."))
            from spyder.plugins.outlineexplorer import OutlineExplorer
            fullpath_sorting = CONF.get('editor', 'fullpath_sorting', True)
            self.outlineexplorer = OutlineExplorer(self,
                                        fullpath_sorting=fullpath_sorting)
            self.outlineexplorer.register_plugin()

        # Editor plugin
        self.set_splash(_("Loading editor..."))
        from spyder.plugins.editor import Editor
        self.editor = Editor(self)
        self.editor.register_plugin()

        # Populating file menu entries
        quit_action = create_action(self, _("&Quit"),
                                    icon=ima.icon('exit'),
                                    tip=_("Quit"),
                                    triggered=self.console.quit,
                                    context=Qt.ApplicationShortcut)
        self.register_shortcut(quit_action, "_", "Quit")
        restart_action = create_action(self, _("&Restart"),
                                       icon=ima.icon('restart'),
                                       tip=_("Restart"),
                                       triggered=self.restart,
                                       context=Qt.ApplicationShortcut)
        self.register_shortcut(restart_action, "_", "Restart")

        self.file_menu_actions += [self.file_switcher_action,
                                   self.symbol_finder_action, None,
                                   restart_action, quit_action]
        self.set_splash("")

        self.debug_print("  ..widgets")

        # Namespace browser
        self.set_splash(_("Loading namespace browser..."))
        from spyder.plugins.variableexplorer import VariableExplorer
        self.variableexplorer = VariableExplorer(self)
        self.variableexplorer.register_plugin()

        # History log widget
        if CONF.get('historylog', 'enable'):
            self.set_splash(_("Loading history plugin..."))
            from spyder.plugins.history import HistoryLog
            self.historylog = HistoryLog(self)
            self.historylog.register_plugin()

        # IPython console
        self.set_splash(_("Loading IPython console..."))
        from spyder.plugins.ipythonconsole import IPythonConsole
        self.ipyconsole = IPythonConsole(self)
        self.ipyconsole.register_plugin()

        # Explorer
        if CONF.get('explorer', 'enable'):
            self.set_splash(_("Loading file explorer..."))
            from spyder.plugins.explorer import Explorer
            self.explorer = Explorer(self)
            self.explorer.register_plugin()

        # Online help widget
        try:    # Qt >= v4.4
            from spyder.plugins.onlinehelp import OnlineHelp
        except ImportError:    # Qt < v4.4
            OnlineHelp = None  # analysis:ignore
        if CONF.get('onlinehelp', 'enable') and OnlineHelp is not None:
            self.set_splash(_("Loading online help..."))
            self.onlinehelp = OnlineHelp(self)
            self.onlinehelp.register_plugin()

        # Project explorer widget
        self.set_splash(_("Loading project explorer..."))
        from spyder.plugins.projects import Projects
        self.projects = Projects(self)
        self.projects.register_plugin()
        self.project_path = self.projects.get_pythonpath(at_start=True)

        # Find in files
        if CONF.get('find_in_files', 'enable'):
            from spyder.plugins.findinfiles import FindInFiles
            self.findinfiles = FindInFiles(self)
            self.findinfiles.register_plugin()

        # Third-party plugins
        self.set_splash(_("Loading third-party plugins..."))
        for mod in get_spyderplugins_mods():
            try:
                plugin = mod.PLUGIN_CLASS(self)
                if plugin.check_compatibility()[0]:
                    self.thirdparty_plugins.append(plugin)
                    plugin.register_plugin()
            except Exception as error:
                print("%s: %s" % (mod, str(error)), file=STDERR)
                traceback.print_exc(file=STDERR)

        self.set_splash(_("Setting up main window..."))

        # Help menu
        dep_action = create_action(self, _("Dependencies..."),
                                    triggered=self.show_dependencies,
                                    icon=ima.icon('advanced'))
        report_action = create_action(self,
                                        _("Report issue..."),
                                        icon=ima.icon('bug'),
                                        triggered=self.report_issue)
        support_action = create_action(self,
                                        _("Spyder support..."),
                                        triggered=self.google_group)
        self.check_updates_action = create_action(self,
                                                _("Check for updates..."),
                                                triggered=self.check_updates)

        # Spyder documentation
        doc_path = get_module_data_path('spyder', relpath="doc",
                                        attr_name='DOCPATH')
        # * Trying to find the chm doc
        spyder_doc = osp.join(doc_path, "Spyderdoc.chm")
        if not osp.isfile(spyder_doc):
            spyder_doc = osp.join(doc_path, os.pardir, "Spyderdoc.chm")
        # * Trying to find the html doc
        if not osp.isfile(spyder_doc):
            spyder_doc = osp.join(doc_path, "index.html")
        # * Trying to find the development-version html doc
        if not osp.isfile(spyder_doc):
            spyder_doc = osp.join(get_module_source_path('spyder'),
                                    os.pardir, 'build', 'lib', 'spyder',
                                    'doc', "index.html")
        # * If we totally fail, point to our web build
        if not osp.isfile(spyder_doc):
            spyder_doc = 'http://pythonhosted.org/spyder'
        else:
            spyder_doc = file_uri(spyder_doc)
        doc_action = create_action(self, _("Spyder documentation"),
                                   icon=ima.icon('DialogHelpButton'),
                                   triggered=lambda:
                                   programs.start_file(spyder_doc))
        self.register_shortcut(doc_action, "_",
                               "spyder documentation")

        if self.help is not None:
            tut_action = create_action(self, _("Spyder tutorial"),
                                       triggered=self.help.show_tutorial)
        else:
            tut_action = None

        shortcuts_action = create_action(self, _("Shortcuts Summary"),
                                         shortcut="Meta+F1",
                                         triggered=self.show_shortcuts_dialog)

        #----- Tours
        self.tour = tour.AnimatedTour(self)
        self.tours_menu = QMenu(_("Interactive tours"))
        self.tour_menu_actions = []
        # TODO: Only show intro tour for now. When we are close to finish
        # 3.0, we will finish and show the other tour
        self.tours_available = tour.get_tours(0)

        for i, tour_available in enumerate(self.tours_available):
            self.tours_available[i]['last'] = 0
            tour_name = tour_available['name']

            def trigger(i=i, self=self):  # closure needed!
                return lambda: self.show_tour(i)

            temp_action = create_action(self, tour_name, tip="",
                                        triggered=trigger())
            self.tour_menu_actions += [temp_action]

        self.tours_menu.addActions(self.tour_menu_actions)

        self.help_menu_actions = [doc_action, tut_action, shortcuts_action,
                                  self.tours_menu,
                                  MENU_SEPARATOR, report_action, dep_action,
                                  self.check_updates_action, support_action,
                                  MENU_SEPARATOR]
        # Python documentation
        if get_python_doc_path() is not None:
            pydoc_act = create_action(self, _("Python documentation"),
                                triggered=lambda:
                                programs.start_file(get_python_doc_path()))
            self.help_menu_actions.append(pydoc_act)
        # IPython documentation
        if self.help is not None:
            ipython_menu = QMenu(_("IPython documentation"), self)
            intro_action = create_action(self, _("Intro to IPython"),
                                        triggered=self.ipyconsole.show_intro)
            quickref_action = create_action(self, _("Quick reference"),
                                    triggered=self.ipyconsole.show_quickref)
            guiref_action = create_action(self, _("Console help"),
                                        triggered=self.ipyconsole.show_guiref)
            add_actions(ipython_menu, (intro_action, guiref_action,
                                        quickref_action))
            self.help_menu_actions.append(ipython_menu)
        # Windows-only: documentation located in sys.prefix/Doc
        ipm_actions = []
        def add_ipm_action(text, path):
            """Add installed Python module doc action to help submenu"""
            # QAction.triggered works differently for PySide and PyQt
            path = file_uri(path)
            if not API == 'pyside':
                slot=lambda _checked, path=path: programs.start_file(path)
            else:
                slot=lambda path=path: programs.start_file(path)
            action = create_action(self, text,
                    icon='%s.png' % osp.splitext(path)[1][1:],
                    triggered=slot)
            ipm_actions.append(action)
        sysdocpth = osp.join(sys.prefix, 'Doc')
        if osp.isdir(sysdocpth): # exists on Windows, except frozen dist.
            for docfn in os.listdir(sysdocpth):
                pt = r'([a-zA-Z\_]*)(doc)?(-dev)?(-ref)?(-user)?.(chm|pdf)'
                match = re.match(pt, docfn)
                if match is not None:
                    pname = match.groups()[0]
                    if pname not in ('Python', ):
                        add_ipm_action(pname, osp.join(sysdocpth, docfn))
        # Installed Python modules submenu (Windows only)
        if ipm_actions:
            pymods_menu = QMenu(_("Installed Python modules"), self)
            add_actions(pymods_menu, ipm_actions)
            self.help_menu_actions.append(pymods_menu)
        # Online documentation
        web_resources = QMenu(_("Online documentation"))
        webres_actions = create_module_bookmark_actions(self,
                                                        self.BOOKMARKS)
        webres_actions.insert(2, None)
        webres_actions.insert(5, None)
        webres_actions.insert(8, None)
        add_actions(web_resources, webres_actions)
        self.help_menu_actions.append(web_resources)
        # Qt assistant link
        if sys.platform.startswith('linux') and not PYQT5:
            qta_exe = "assistant-qt4"
        else:
            qta_exe = "assistant"
        qta_act = create_program_action(self, _("Qt documentation"),
                                        qta_exe)
        if qta_act:
            self.help_menu_actions += [qta_act, None]
        # About Spyder
        about_action = create_action(self,
                                _("About %s...") % "Spyder",
                                icon=ima.icon('MessageBoxInformation'),
                                triggered=self.about)
        self.help_menu_actions += [MENU_SEPARATOR, about_action]

        # Status bar widgets
        from spyder.widgets.status import MemoryStatus, CPUStatus
        self.mem_status = MemoryStatus(self, status)
        self.cpu_status = CPUStatus(self, status)
        self.apply_statusbar_settings()

        # ----- View
        # View menu
        self.plugins_menu = QMenu(_("Panes"), self)

        self.toolbars_menu = QMenu(_("Toolbars"), self)
        self.quick_layout_menu = QMenu(_("Window layouts"), self)
        self.quick_layout_set_menu()

        self.view_menu.addMenu(self.plugins_menu)  # Panes
        add_actions(self.view_menu, (self.lock_dockwidgets_action,
                                     self.close_dockwidget_action,
                                     self.maximize_action,
                                     MENU_SEPARATOR))
        self.show_toolbars_action = create_action(self,
                                _("Show toolbars"),
                                triggered=self.show_toolbars,
                                context=Qt.ApplicationShortcut)
        self.register_shortcut(self.show_toolbars_action, "_",
                               "Show toolbars")
        self.view_menu.addMenu(self.toolbars_menu)
        self.view_menu.addAction(self.show_toolbars_action)
        add_actions(self.view_menu, (MENU_SEPARATOR,
                                     self.quick_layout_menu,
                                     self.toggle_previous_layout_action,
                                     self.toggle_next_layout_action,
                                     MENU_SEPARATOR,
                                     self.fullscreen_action))
        if set_attached_console_visible is not None:
            cmd_act = create_action(self,
                                _("Attached console window (debugging)"),
                                toggled=set_attached_console_visible)
            cmd_act.setChecked(is_attached_console_visible())
            add_actions(self.view_menu, (MENU_SEPARATOR, cmd_act))

        # Adding external tools action to "Tools" menu
        if self.external_tools_menu_actions:
            external_tools_act = create_action(self, _("External Tools"))
            external_tools_act.setMenu(self.external_tools_menu)
            self.tools_menu_actions += [None, external_tools_act]

        # Filling out menu/toolbar entries:
        add_actions(self.file_menu, self.file_menu_actions)
        add_actions(self.edit_menu, self.edit_menu_actions)
        add_actions(self.search_menu, self.search_menu_actions)
        add_actions(self.source_menu, self.source_menu_actions)
        add_actions(self.run_menu, self.run_menu_actions)
        add_actions(self.debug_menu, self.debug_menu_actions)
        add_actions(self.consoles_menu, self.consoles_menu_actions)
        add_actions(self.projects_menu, self.projects_menu_actions)
        add_actions(self.tools_menu, self.tools_menu_actions)
        add_actions(self.external_tools_menu,
                    self.external_tools_menu_actions)
        add_actions(self.help_menu, self.help_menu_actions)

        add_actions(self.main_toolbar, self.main_toolbar_actions)
        add_actions(self.file_toolbar, self.file_toolbar_actions)
        add_actions(self.edit_toolbar, self.edit_toolbar_actions)
        add_actions(self.search_toolbar, self.search_toolbar_actions)
        add_actions(self.source_toolbar, self.source_toolbar_actions)
        add_actions(self.debug_toolbar, self.debug_toolbar_actions)
        add_actions(self.run_toolbar, self.run_toolbar_actions)

        # Apply all defined shortcuts (plugins + 3rd-party plugins)
        self.apply_shortcuts()

        # Emitting the signal notifying plugins that main window menu and
        # toolbar actions are all defined:
        self.all_actions_defined.emit()

        # Window set-up
        self.debug_print("Setting up window...")
        self.setup_layout(default=False)

        # Show and hide shortcuts in menus for Mac.
        # This is a workaround because we can't disable shortcuts
        # by setting context=Qt.WidgetShortcut there
        if sys.platform == 'darwin':
            for name in ['file', 'edit', 'search', 'source', 'run', 'debug',
                         'projects', 'tools', 'plugins']:
                menu_object = getattr(self, name + '_menu')
                menu_object.aboutToShow.connect(
                    lambda name=name: self.show_shortcuts(name))
                menu_object.aboutToHide.connect(
                    lambda name=name: self.hide_shortcuts(name))

        if self.splash is not None:
            self.splash.hide()

        # Enabling tear off for all menus except help menu
        if CONF.get('main', 'tear_off_menus'):
            for child in self.menuBar().children():
                if isinstance(child, QMenu) and child != self.help_menu:
                    child.setTearOffEnabled(True)

        # Menu about to show
        for child in self.menuBar().children():
            if isinstance(child, QMenu):
                try:
                    child.aboutToShow.connect(self.update_edit_menu)
                except TypeError:
                    pass

        self.debug_print("*** End of MainWindow setup ***")
        self.is_starting_up = False

    def post_visible_setup(self):
        """Actions to be performed only after the main window's `show` method
        was triggered"""
        self.restore_scrollbar_position.emit()

        # Remove our temporary dir
        atexit.register(self.remove_tmpdir)

        # [Workaround for Issue 880]
        # QDockWidget objects are not painted if restored as floating
        # windows, so we must dock them before showing the mainwindow,
        # then set them again as floating windows here.
        for widget in self.floating_dockwidgets:
            widget.setFloating(True)

        # In MacOS X 10.7 our app is not displayed after initialized (I don't
        # know why because this doesn't happen when started from the terminal),
        # so we need to resort to this hack to make it appear.
        if running_in_mac_app():
            idx = __file__.index(MAC_APP_NAME)
            app_path = __file__[:idx]
            subprocess.call(['open', app_path + MAC_APP_NAME])

        # Server to maintain just one Spyder instance and open files in it if
        # the user tries to start other instances with
        # $ spyder foo.py
        if (CONF.get('main', 'single_instance') and not self.new_instance
                and self.open_files_server):
            t = threading.Thread(target=self.start_open_files_server)
            t.setDaemon(True)
            t.start()

            # Connect the window to the signal emmited by the previous server
            # when it gets a client connected to it
            self.sig_open_external_file.connect(self.open_external_file)

        # Create Plugins and toolbars submenus
        self.create_plugins_menu()
        self.create_toolbars_menu()

        # Update toolbar visibility status
        self.toolbars_visible = CONF.get('main', 'toolbars_visible')
        self.load_last_visible_toolbars()

        # Update lock status of dockidgets (panes)
        self.lock_dockwidgets_action.setChecked(self.dockwidgets_locked)
        self.apply_panes_settings()

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
        if not self.ipyconsole.isvisible:
            self.historylog.add_history(get_conf_path('history.py'))

        if self.open_project:
            self.projects.open_project(self.open_project)
        else:
            # Load last project if a project was active when Spyder
            # was closed
            self.projects.reopen_last_project()

            # If no project is active, load last session
            if self.projects.get_active_project() is None:
                self.editor.setup_open_files()

        # Check for spyder updates
        if DEV is None and CONF.get('main', 'check_updates_on_startup'):
            self.give_updates_feedback = False
            self.check_updates(startup=True)

        # Show dialog with missing dependencies
        self.report_missing_dependencies()

        # Raise the menuBar to the top of the main window widget's stack
        # (Fixes issue 3887)
        self.menuBar().raise_()
        self.is_setting_up = False

    def update_window_title(self):
        """Update main spyder window title based on projects."""
        title = self.base_title
        if self.projects is not None:
            path = self.projects.get_active_project_path()
            if path:
                path = path.replace(get_home_dir(), '~')
                title = '{0} - {1}'.format(path, title)
        self.setWindowTitle(title)

    def report_missing_dependencies(self):
        """Show a QMessageBox with a list of missing hard dependencies"""
        missing_deps = dependencies.missing_dependencies()
        if missing_deps:
            QMessageBox.critical(self, _('Error'),
                _("<b>You have missing dependencies!</b>"
                  "<br><br><tt>%s</tt><br><br>"
                  "<b>Please install them to avoid this message.</b>"
                  "<br><br>"
                  "<i>Note</i>: Spyder could work without some of these "
                  "dependencies, however to have a smooth experience when "
                  "using Spyder we <i>strongly</i> recommend you to install "
                  "all the listed missing dependencies.<br><br>"
                  "Failing to install these dependencies might result in bugs. "
                  "Please be sure that any found bugs are not the direct "
                  "result of missing dependencies, prior to reporting a new "
                  "issue."
                  ) % missing_deps, QMessageBox.Ok)

    def load_window_settings(self, prefix, default=False, section='main'):
        """Load window layout settings from userconfig-based configuration
        with *prefix*, under *section*
        default: if True, do not restore inner layout"""
        get_func = CONF.get_default if default else CONF.get
        window_size = get_func(section, prefix+'size')
        prefs_dialog_size = get_func(section, prefix+'prefs_dialog_size')
        if default:
            hexstate = None
        else:
            hexstate = get_func(section, prefix+'state', None)
        pos = get_func(section, prefix+'position')
        
        # It's necessary to verify if the window/position value is valid 
        # with the current screen. See issue 3748
        width = pos[0]
        height = pos[1]
        screen_shape = QApplication.desktop().geometry()
        current_width = screen_shape.width()
        current_height = screen_shape.height()
        if current_width < width or current_height < height:
            pos = CONF.get_default(section, prefix+'position')
        
        is_maximized =  get_func(section, prefix+'is_maximized')
        is_fullscreen = get_func(section, prefix+'is_fullscreen')
        return hexstate, window_size, prefs_dialog_size, pos, is_maximized, \
               is_fullscreen

    def get_window_settings(self):
        """Return current window settings
        Symetric to the 'set_window_settings' setter"""
        window_size = (self.window_size.width(), self.window_size.height())
        is_fullscreen = self.isFullScreen()
        if is_fullscreen:
            is_maximized = self.maximized_flag
        else:
            is_maximized = self.isMaximized()
        pos = (self.window_position.x(), self.window_position.y())
        prefs_dialog_size = (self.prefs_dialog_size.width(),
                             self.prefs_dialog_size.height())
        hexstate = qbytearray_to_str(self.saveState())
        return (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
                is_fullscreen)

    def set_window_settings(self, hexstate, window_size, prefs_dialog_size,
                            pos, is_maximized, is_fullscreen):
        """Set window settings
        Symetric to the 'get_window_settings' accessor"""
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
            self.restoreState( QByteArray().fromHex(
                    str(hexstate).encode('utf-8')) )
            # [Workaround for Issue 880]
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

    def save_current_window_settings(self, prefix, section='main'):
        """Save current window settings with *prefix* in
        the userconfig-based configuration, under *section*"""
        win_size = self.window_size
        prefs_size = self.prefs_dialog_size

        CONF.set(section, prefix+'size', (win_size.width(), win_size.height()))
        CONF.set(section, prefix+'prefs_dialog_size',
                 (prefs_size.width(), prefs_size.height()))
        CONF.set(section, prefix+'is_maximized', self.isMaximized())
        CONF.set(section, prefix+'is_fullscreen', self.isFullScreen())
        pos = self.window_position
        CONF.set(section, prefix+'position', (pos.x(), pos.y()))
        self.maximize_dockwidget(restore=True)# Restore non-maximized layout
        qba = self.saveState()
        CONF.set(section, prefix+'state', qbytearray_to_str(qba))
        CONF.set(section, prefix+'statusbar',
                    not self.statusBar().isHidden())

    def tabify_plugins(self, first, second):
        """Tabify plugin dockwigdets"""
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
                self.save_current_window_settings(prefix, section)
                CONF.set(section, prefix+'state', None)        

            # store the initial layout as the default in spyder
            prefix = 'layout_default/'
            section = 'quick_layouts'
            self.save_current_window_settings(prefix, section)
            self.current_quick_layout = 'default'
            CONF.set(section, prefix+'state', None)
            
            # Regenerate menu
            self.quick_layout_set_menu()
        self.set_window_settings(*settings)

        for plugin in self.widgetlist:
            try:
                plugin.initialize_plugin_in_mainwindow_layout()
            except Exception as error:
                print("%s: %s" % (plugin, str(error)), file=STDERR)
                traceback.print_exc(file=STDERR)
       
    def setup_default_layouts(self, index, settings):
        """Setup default layouts when run for the first time"""
        self.set_window_settings(*settings)
        self.setUpdatesEnabled(False)

        # IMPORTANT: order has to be the same as defined in the config file
        MATLAB, RSTUDIO, VERTICAL, HORIZONTAL = range(4)

        # define widgets locally
        editor = self.editor
        console_ipy = self.ipyconsole
        console_int = self.console
        outline = self.outlineexplorer
        explorer_project = self.projects
        explorer_file = self.explorer
        explorer_variable = self.variableexplorer
        history = self.historylog
        finder = self.findinfiles
        help_plugin = self.help
        helper = self.onlinehelp
        plugins = self.thirdparty_plugins

        global_hidden_widgets = [finder, console_int, explorer_project,
                                 helper] + plugins
        global_hidden_toolbars = [self.source_toolbar, self.edit_toolbar,
                                  self.search_toolbar]
        # Layout definition
        # layouts are organized by columns, each colum is organized by rows
        # widths have to add 1.0, height per column have to add 1.0
        # Spyder Default Initial Layout
        s_layout = {'widgets': [
                    # column 0
                    [[explorer_project]],
                    # column 1
                    [[editor]],
                    # column 2
                    [[outline]],
                    # column 3
                    [[help_plugin, explorer_variable, helper, explorer_file,
                      finder] + plugins,
                     [console_int, console_ipy, history]]
                    ],
                    'width fraction': [0.0,             # column 0 width
                                       0.55,            # column 1 width
                                       0.0,             # column 2 width
                                       0.45],           # column 3 width
                    'height fraction': [[1.0],          # column 0, row heights
                                        [1.0],          # column 1, row heights
                                        [1.0],          # column 2, row heights
                                        [0.46, 0.54]],  # column 3, row heights
                    'hidden widgets': [outline],
                    'hidden toolbars': [],                               
                    }
        r_layout = {'widgets': [
                    # column 0
                    [[editor],
                     [console_ipy, console_int]],
                    # column 1
                    [[explorer_variable, history, outline, finder] + plugins,
                     [explorer_file, explorer_project, help_plugin, helper]]
                    ],
                    'width fraction': [0.55,            # column 0 width
                                       0.45],           # column 1 width
                    'height fraction': [[0.55, 0.45],   # column 0, row heights
                                        [0.55, 0.45]],  # column 1, row heights
                    'hidden widgets': [outline],
                    'hidden toolbars': [],                               
                    }
        # Matlab
        m_layout = {'widgets': [
                    # column 0
                    [[explorer_file, explorer_project],
                     [outline]],
                    # column 1
                    [[editor],
                     [console_ipy, console_int]],
                    # column 2
                    [[explorer_variable, finder] + plugins,
                     [history, help_plugin, helper]]
                    ],
                    'width fraction': [0.20,            # column 0 width
                                       0.40,            # column 1 width
                                       0.40],           # column 2 width
                    'height fraction': [[0.55, 0.45],   # column 0, row heights
                                        [0.55, 0.45],   # column 1, row heights
                                        [0.55, 0.45]],  # column 2, row heights
                    'hidden widgets': [],
                    'hidden toolbars': [],
                    }
        # Vertically split
        v_layout = {'widgets': [
                    # column 0
                    [[editor],
                     [console_ipy, console_int, explorer_file,
                      explorer_project, help_plugin, explorer_variable,
                      history, outline, finder, helper] + plugins]
                    ],
                    'width fraction': [1.0],            # column 0 width
                    'height fraction': [[0.55, 0.45]],  # column 0, row heights
                    'hidden widgets': [outline],
                    'hidden toolbars': [],
                    }
        # Horizontally split
        h_layout = {'widgets': [
                    # column 0
                    [[editor]],
                    # column 1
                    [[console_ipy, console_int, explorer_file,
                      explorer_project, help_plugin, explorer_variable,
                      history, outline, finder, helper] + plugins]
                    ],
                    'width fraction': [0.55,      # column 0 width
                                       0.45],     # column 1 width
                    'height fraction': [[1.0],    # column 0, row heights
                                        [1.0]],   # column 1, row heights
                    'hidden widgets': [outline],
                    'hidden toolbars': []
                    }

        # Layout selection
        layouts = {'default': s_layout,
                   RSTUDIO: r_layout,
                   MATLAB: m_layout,
                   VERTICAL: v_layout,
                   HORIZONTAL: h_layout}

        layout = layouts[index]

        widgets_layout = layout['widgets']         
        widgets = []
        for column in widgets_layout :
            for row in column:
                for widget in row:
                    if widget is not None:
                        widgets.append(widget)

        # Make every widget visible
        for widget in widgets:
            widget.toggle_view(True)
            action = widget.toggle_view_action
            action.setChecked(widget.dockwidget.isVisible())

        # Set the widgets horizontally
        for i in range(len(widgets) - 1):
            first, second = widgets[i], widgets[i+1]
            if first is not None and second is not None:
                self.splitDockWidget(first.dockwidget, second.dockwidget,
                                     Qt.Horizontal)

        # Arrange rows vertically 
        for column in widgets_layout :
            for i in range(len(column) - 1):
                first_row, second_row = column[i], column[i+1]
                if first_row is not None and second_row is not None:
                    self.splitDockWidget(first_row[0].dockwidget,
                                         second_row[0].dockwidget,
                                         Qt.Vertical)
        # Tabify
        for column in widgets_layout :
            for row in column:
                for i in range(len(row) - 1):
                    first, second = row[i], row[i+1]
                    if first is not None and second is not None:
                        self.tabify_plugins(first, second)

                # Raise front widget per row
                row[0].dockwidget.show()
                row[0].dockwidget.raise_()

        # Hide toolbars
        hidden_toolbars = global_hidden_toolbars + layout['hidden toolbars']
        for toolbar in hidden_toolbars:
            if toolbar is not None:
                toolbar.close()

        # Hide widgets
        hidden_widgets = global_hidden_widgets + layout['hidden widgets']
        for widget in hidden_widgets:
            if widget is not None:
                widget.dockwidget.close()

        # set the width and height
        self._layout_widget_info = []
        width, height = self.window_size.width(), self.window_size.height()

        # fix column width
#        for c in range(len(widgets_layout)):
#            widget = widgets_layout[c][0][0].dockwidget
#            min_width, max_width = widget.minimumWidth(), widget.maximumWidth()
#            info = {'widget': widget,
#                    'min width': min_width,
#                    'max width': max_width}
#            self._layout_widget_info.append(info)
#            new_width = int(layout['width fraction'][c] * width * 0.95)
#            widget.setMinimumWidth(new_width)
#            widget.setMaximumWidth(new_width)
#            widget.updateGeometry()
        
        # fix column height
        for c, column in enumerate(widgets_layout):
            for r in range(len(column) - 1):
                widget = column[r][0]
                dockwidget = widget.dockwidget
                dock_min_h = dockwidget.minimumHeight()
                dock_max_h = dockwidget.maximumHeight()
                info = {'widget': widget,
                        'dock min height': dock_min_h,
                        'dock max height': dock_max_h}
                self._layout_widget_info.append(info)
                # The 0.95 factor is to adjust height based on usefull
                # estimated area in the window
                new_height = int(layout['height fraction'][c][r]*height*0.95)
                dockwidget.setMinimumHeight(new_height)
                dockwidget.setMaximumHeight(new_height)

        self._custom_layout_timer = QTimer(self)
        self._custom_layout_timer.timeout.connect(self.layout_fix_timer)
        self._custom_layout_timer.setSingleShot(True)
        self._custom_layout_timer.start(5000)

    def layout_fix_timer(self):
        """Fixes the height of docks after a new layout is set."""
        info = self._layout_widget_info
        for i in info:
            dockwidget = i['widget'].dockwidget
            if 'dock min width' in i:
                dockwidget.setMinimumWidth(i['dock min width'])
                dockwidget.setMaximumWidth(i['dock max width'])
            if 'dock min height' in i:
                dockwidget.setMinimumHeight(i['dock min height'])
                dockwidget.setMaximumHeight(i['dock max height'])
            dockwidget.updateGeometry()

        self.setUpdatesEnabled(True)

    @Slot()
    def toggle_previous_layout(self):
        """ """
        self.toggle_layout('previous')

    @Slot()
    def toggle_next_layout(self):
        """ """
        self.toggle_layout('next')

    def toggle_layout(self, direction='next'):
        """ """
        get = CONF.get
        names = get('quick_layouts', 'names')
        order = get('quick_layouts', 'order')
        active = get('quick_layouts', 'active')

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
        """ """
        get = CONF.get
        names = get('quick_layouts', 'names')
        order = get('quick_layouts', 'order')
        active = get('quick_layouts', 'active')

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
        get = CONF.get
        set_ = CONF.set
        names = get('quick_layouts', 'names')
        order = get('quick_layouts', 'order')
        active = get('quick_layouts', 'active')

        dlg = self.dialog_layout_save(self, names)

        if dlg.exec_():
            name = dlg.combo_box.currentText()

            if name in names:
                answer = QMessageBox.warning(self, _("Warning"),
                                             _("Layout <b>%s</b> will be \
                                               overwritten. Do you want to \
                                               continue?") % name,
                                             QMessageBox.Yes | QMessageBox.No)
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
                set_('quick_layouts', 'names', names)
                set_('quick_layouts', 'order', order)
                set_('quick_layouts', 'active', active)
                self.quick_layout_set_menu()

    def quick_layout_settings(self):
        """Layout settings dialog"""
        get = CONF.get
        set_ = CONF.set

        section = 'quick_layouts'

        names = get(section, 'names')
        order = get(section, 'order')
        active = get(section, 'active')

        dlg = self.dialog_layout_settings(self, names, order, active)
        if dlg.exec_():
            set_(section, 'names', dlg.names)
            set_(section, 'order', dlg.order)
            set_(section, 'active', dlg.active)
            self.quick_layout_set_menu()

    def quick_layout_switch(self, index):
        """Switch to quick layout number *index*"""
        section = 'quick_layouts'

        try:
            settings = self.load_window_settings('layout_{}/'.format(index),
                                                 section=section)
            (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
             is_fullscreen) = settings

            # The defaults layouts will alwyas be regenerated unless there was
            # an overwrite, either by rewriting with same name, or by deleting
            # and then creating a new one
            if hexstate is None:
                self.setup_default_layouts(index, settings)
        except cp.NoOptionError:
            QMessageBox.critical(self, _("Warning"),
                                 _("Quick switch layout #%s has not yet "
                                   "been defined.") % str(index))
            return
            # TODO: is there any real use in calling the previous layout
            # setting?
            # self.previous_layout_settings = self.get_window_settings()
        self.set_window_settings(*settings)
        self.current_quick_layout = index

        # make sure the flags are correctly set for visible panes
        for plugin in self.widgetlist:
            action = plugin.toggle_view_action
            action.setChecked(plugin.dockwidget.isVisible())

    # --- Show/Hide toolbars
    def _update_show_toolbars_action(self):
        """Update the text displayed in the menu entry."""
        if self.toolbars_visible:
            text = _("Hide toolbars")
            tip = _("Hide toolbars")
        else:
            text = _("Show toolbars")
            tip = _("Show toolbars")
        self.show_toolbars_action.setText(text)
        self.show_toolbars_action.setToolTip(tip)

    def save_visible_toolbars(self):
        """Saves the name of the visible toolbars in the .ini file."""
        toolbars = []
        for toolbar in self.visible_toolbars:
            toolbars.append(toolbar.objectName())
        CONF.set('main', 'last_visible_toolbars', toolbars)

    def get_visible_toolbars(self):
        """Collects the visible toolbars."""
        toolbars = []
        for toolbar in self.toolbarslist:
            if toolbar.toggleViewAction().isChecked():
                toolbars.append(toolbar)
        self.visible_toolbars = toolbars

    def load_last_visible_toolbars(self):
        """Loads the last visible toolbars from the .ini file."""
        toolbars_names = CONF.get('main', 'last_visible_toolbars', default=[])

        if toolbars_names:
            dic = {}
            for toolbar in self.toolbarslist:
                dic[toolbar.objectName()] = toolbar

            toolbars = []
            for name in toolbars_names:
                if name in dic:
                    toolbars.append(dic[name])
            self.visible_toolbars = toolbars
        else:
            self.get_visible_toolbars()
        self._update_show_toolbars_action()

    @Slot()
    def show_toolbars(self):
        """Show/Hides toolbars."""
        value = not self.toolbars_visible
        CONF.set('main', 'toolbars_visible', value)
        if value:
            self.save_visible_toolbars()
        else:
            self.get_visible_toolbars()

        for toolbar in self.visible_toolbars:
            toolbar.toggleViewAction().setChecked(value)
            toolbar.setVisible(value)

        self.toolbars_visible = value
        self._update_show_toolbars_action()

    # --- Other
    def plugin_focus_changed(self):
        """Focus has changed from one plugin to another"""
        self.update_edit_menu()
        self.update_search_menu()

    def show_shortcuts(self, menu):
        """Show action shortcuts in menu"""
        for element in getattr(self, menu + '_menu_actions'):
            if element and isinstance(element, QAction):
                if element._shown_shortcut is not None:
                    element.setShortcut(element._shown_shortcut)

    def hide_shortcuts(self, menu):
        """Hide action shortcuts in menu"""
        for element in getattr(self, menu + '_menu_actions'):
            if element and isinstance(element, QAction):
                if element._shown_shortcut is not None:
                    element.setShortcut(QKeySequence())

    def get_focus_widget_properties(self):
        """Get properties of focus widget
        Returns tuple (widget, properties) where properties is a tuple of
        booleans: (is_console, not_readonly, readwrite_editor)"""
        widget = QApplication.focusWidget()
        from spyder.widgets.shell import ShellBaseWidget
        from spyder.widgets.editor import TextEditBaseWidget
        from spyder.widgets.ipythonconsole import ControlWidget

        # if focused widget isn't valid try the last focused
        if not isinstance(widget, (ShellBaseWidget, TextEditBaseWidget,
                                   ControlWidget)):
            widget = self.previous_focused_widget

        textedit_properties = None
        if isinstance(widget, (ShellBaseWidget, TextEditBaseWidget,
                               ControlWidget)):
            console = isinstance(widget, (ShellBaseWidget, ControlWidget))
            not_readonly = not widget.isReadOnly()
            readwrite_editor = not_readonly and not console
            textedit_properties = (console, not_readonly, readwrite_editor)
        return widget, textedit_properties

    def update_edit_menu(self):
        """Update edit menu"""
        widget, textedit_properties = self.get_focus_widget_properties()
        if textedit_properties is None: # widget is not an editor/console
            return
        #!!! Below this line, widget is expected to be a QPlainTextEdit instance
        console, not_readonly, readwrite_editor = textedit_properties

        # Editor has focus and there is no file opened in it
        if not console and not_readonly and not self.editor.is_file_opened():
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
            for action in self.editor.edit_menu_actions:
                action.setEnabled(True)

    def update_search_menu(self):
        """Update search menu"""
        if self.menuBar().hasFocus():
            return

        widget, textedit_properties = self.get_focus_widget_properties()
        for action in self.editor.search_menu_actions:
            try:
                action.setEnabled(self.editor.isAncestorOf(widget))
            except RuntimeError:
                pass
        if textedit_properties is None: # widget is not an editor/console
            return
        #!!! Below this line, widget is expected to be a QPlainTextEdit instance
        _x, _y, readwrite_editor = textedit_properties
        # Disable the replace action for read-only files
        self.search_menu_actions[3].setEnabled(readwrite_editor)

    def create_plugins_menu(self):
        order = ['editor', 'console', 'ipython_console', 'variable_explorer',
                 'help', None, 'explorer', 'outline_explorer',
                 'project_explorer', 'find_in_files', None, 'historylog',
                 'profiler', 'breakpoints', 'pylint', None,
                 'onlinehelp', 'internal_console']
        for plugin in self.widgetlist:
            action = plugin.toggle_view_action
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

    def create_toolbars_menu(self):
        order = ['file_toolbar', 'run_toolbar', 'debug_toolbar',
                 'main_toolbar', 'Global working directory', None,
                 'search_toolbar', 'edit_toolbar', 'source_toolbar']
        for toolbar in self.toolbarslist:
            action = toolbar.toggleViewAction()
            name = toolbar.objectName()
            try:
                pos = order.index(name)
            except ValueError:
                pos = None
            if pos is not None:
                order[pos] = action
            else:
                order.append(action)
        add_actions(self.toolbars_menu, order)

    def createPopupMenu(self):
        menu = QMenu('', self)
        actions = self.help_menu_actions[:3] + \
                    [None, self.help_menu_actions[-1]]
        add_actions(menu, actions)
        return menu

    def set_splash(self, message):
        """Set splash message"""
        if self.splash is None:
            return
        if message:
            self.debug_print(message)
        self.splash.show()
        self.splash.showMessage(message, Qt.AlignBottom | Qt.AlignCenter |
                                Qt.AlignAbsolute, QColor(Qt.white))
        QApplication.processEvents()

    def remove_tmpdir(self):
        """Remove Spyder temporary directory"""
        if CONF.get('main', 'single_instance') and not self.new_instance:
            shutil.rmtree(programs.TEMPDIR, ignore_errors=True)

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
            for plugin in self.widgetlist:
                if plugin.isAncestorOf(self.last_focused_widget):
                    plugin.visibility_changed(True)
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
        prefix = 'window' + '/'
        self.save_current_window_settings(prefix)
        if CONF.get('main', 'single_instance') and self.open_files_server:
            self.open_files_server.close()
        for plugin in self.thirdparty_plugins:
            if not plugin.closing_plugin(cancelable):
                return False
        for widget in self.widgetlist:
            if not widget.closing_plugin(cancelable):
                return False
        self.dialog_manager.close_all()
        if self.toolbars_visible:
            self.save_visible_toolbars()
        self.already_closed = True
        return True

    def add_dockwidget(self, child):
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.create_dockwidget()
        if CONF.get('main', 'vertical_dockwidget_titlebars'):
            dockwidget.setFeatures(dockwidget.features()|
                                   QDockWidget.DockWidgetVerticalTitleBar)
        self.addDockWidget(location, dockwidget)
        self.widgetlist.append(child)

    @Slot()
    def close_current_dockwidget(self):
        widget = QApplication.focusWidget()
        for plugin in self.widgetlist:
            if plugin.isAncestorOf(widget):
                plugin.dockwidget.hide()
                break

    def toggle_lock_dockwidgets(self, value):
        """Lock/Unlock dockwidgets"""
        self.dockwidgets_locked = value
        self.apply_panes_settings()
        CONF.set('main', 'panes_locked', value)

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
            # No plugin is currently maximized: maximizing focus plugin
            self.state_before_maximizing = self.saveState()
            focus_widget = QApplication.focusWidget()
            for plugin in self.widgetlist:
                plugin.dockwidget.hide()
                if plugin.isAncestorOf(focus_widget):
                    self.last_plugin = plugin
            self.last_plugin.dockwidget.toggleViewAction().setDisabled(True)
            self.setCentralWidget(self.last_plugin)
            self.last_plugin.ismaximized = True
            # Workaround to solve an issue with editor's outline explorer:
            # (otherwise the whole plugin is hidden and so is the outline explorer
            #  and the latter won't be refreshed if not visible)
            self.last_plugin.show()
            self.last_plugin.visibility_changed(True)
            if self.last_plugin is self.editor:
                # Automatically show the outline if the editor was maximized:
                self.addDockWidget(Qt.RightDockWidgetArea,
                                   self.outlineexplorer.dockwidget)
                self.outlineexplorer.dockwidget.show()
        else:
            # Restore original layout (before maximizing current dockwidget)
            self.last_plugin.dockwidget.setWidget(self.last_plugin)
            self.last_plugin.dockwidget.toggleViewAction().setEnabled(True)
            self.setCentralWidget(None)
            self.last_plugin.ismaximized = False
            self.restoreState(self.state_before_maximizing)
            self.state_before_maximizing = None
            self.last_plugin.get_focus_widget().setFocus()
        self.__update_maximize_action()

    def __update_fullscreen_action(self):
        if self.isFullScreen():
            icon = ima.icon('window_nofullscreen')
        else:
            icon = ima.icon('window_fullscreen')
        if is_text_string(icon):
            icon = get_icon(icon)
        self.fullscreen_action.setIcon(icon)

    @Slot()
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.fullscreen_flag = False
            self.showNormal()
            if self.maximized_flag:
                self.showMaximized()
        else:
            self.maximized_flag = self.isMaximized()
            self.fullscreen_flag = True
            self.showFullScreen()
        self.__update_fullscreen_action()

    def add_to_toolbar(self, toolbar, widget):
        """Add widget actions to toolbar"""
        actions = widget.toolbar_actions
        if actions is not None:
            add_actions(toolbar, actions)

    @Slot()
    def about(self):
        """About Spyder"""
        versions = get_versions()
        # Show Mercurial revision for development version
        revlink = ''
        if versions['revision']:
            rev = versions['revision']
            revlink = " (<a href='https://github.com/spyder-ide/spyder/"\
                      "commit/%s'>Commit: %s</a>)" % (rev, rev)
        QMessageBox.about(self,
            _("About %s") % "Spyder",
            """<b>Spyder %s</b> %s
            <br>The Scientific PYthon Development EnviRonment
            <br>Copyright &copy; The Spyder Project Contributors
            <br>Licensed under the terms of the MIT License
            <p>Created by Pierre Raybaut.
            <br>Developed and maintained by the
            <a href="%s/blob/master/AUTHORS">Spyder Project Contributors</a>.
            <br>Many thanks to all the Spyder beta testers and regular users.
            <p>For bug reports and feature requests, please go
            to our <a href="%s">Github website</a>. For discussions around the
            project, please go to our <a href="%s">Google Group</a>
            <p>This project is part of a larger effort to promote and
            facilitate the use of Python for scientific and engineering
            software development. The popular Python distributions
            <a href="http://continuum.io/downloads">Anaconda</a>,
            <a href="https://winpython.github.io/">WinPython</a> and
            <a href="http://python-xy.github.io/">Python(x,y)</a>
            also contribute to this plan.
            <p>Python %s %dbits, Qt %s, %s %s on %s
            <p><small>Most of the icons for the Spyder 2 theme come from the Crystal
            Project (&copy; 2006-2007 Everaldo Coelho). Other icons for that
            theme come from <a href="http://p.yusukekamiyamane.com/"> Yusuke
            Kamiyamane</a> (all rights reserved) and from
            <a href="http://www.oxygen-icons.org/">
            The Oxygen icon theme</a></small>.
            """
            % (versions['spyder'], revlink, __project_url__,
               __project_url__, __forum_url__, versions['python'],
               versions['bitness'], versions['qt'], versions['qt_api'],
               versions['qt_api_ver'], versions['system']))

    @Slot()
    def show_dependencies(self):
        """Show Spyder's Dependencies dialog box"""
        from spyder.widgets.dependencies import DependenciesDialog
        dlg = DependenciesDialog(None)
        dlg.set_data(dependencies.DEPENDENCIES)
        dlg.exec_()

    @Slot()
    def report_issue(self, traceback=""):
        if PY3:
            from urllib.parse import quote
        else:
            from urllib import quote     # analysis:ignore
        versions = get_versions()
        # Get git revision for development version
        revision = ''
        if versions['revision']:
            revision = versions['revision']
        issue_template = """\
## Description

**What steps will reproduce the problem?**

1. 
2. 
3. 

**What is the expected output? What do you see instead?**


**Please provide any additional information below**

%s

## Version and main components

* Spyder Version: %s %s
* Python Version: %s
* Qt Versions: %s, %s %s on %s

## Dependencies
```
%s
```
""" % (traceback,
       versions['spyder'],
       revision,
       versions['python'],
       versions['qt'],
       versions['qt_api'],
       versions['qt_api_ver'],
       versions['system'],
       dependencies.status())

        url = QUrl("https://github.com/spyder-ide/spyder/issues/new")
        if PYQT5:
            from qtpy.QtCore import QUrlQuery
            query = QUrlQuery()
            query.addQueryItem("body", quote(issue_template))
            url.setQuery(query)
        else:
            url.addEncodedQueryItem("body", quote(issue_template))
            
        QDesktopServices.openUrl(url)

    @Slot()
    def google_group(self):
        url = QUrl("http://groups.google.com/group/spyderlib")
        QDesktopServices.openUrl(url)

    @Slot()
    def global_callback(self):
        """Global callback"""
        widget = QApplication.focusWidget()
        action = self.sender()
        callback = from_qvariant(action.data(), to_text_string)
        from spyder.widgets.editor import TextEditBaseWidget

        # if focused widget isn't valid try the last focused^M
        if not isinstance(widget, TextEditBaseWidget):
            widget = self.previous_focused_widget

        if isinstance(widget, TextEditBaseWidget):
            getattr(widget, callback)()

    def redirect_internalshell_stdio(self, state):
        if state:
            self.console.shell.interpreter.redirect_stds()
        else:
            self.console.shell.interpreter.restore_stds()

    def open_external_console(self, fname, wdir, args, interact, debug, python,
                              python_args, systerm, post_mortem=False):
        """Open external console"""
        if systerm:
            # Running script in an external system terminal
            try:
                programs.run_python_script_in_terminal(fname, wdir, args,
                                                interact, debug, python_args)
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
        console.visibility_changed(True)
        console.raise_()
        console.execute_code(lines)
        if focus_to_editor:
            self.editor.visibility_changed(True)

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
            programs.start_file(fname)

    def open_external_file(self, fname):
        """
        Open external files that can be handled either by the Editor or the
        variable explorer inside Spyder.
        """
        fname = encoding.to_unicode_from_fs(fname)
        if osp.isfile(fname):
            self.open_file(fname, external=True)
        elif osp.isfile(osp.join(CWD, fname)):
            self.open_file(osp.join(CWD, fname), external=True)

    # ---- PYTHONPATH management, etc.
    def get_spyder_pythonpath(self):
        """Return Spyder PYTHONPATH"""
        active_path = [p for p in self.path if p not in self.not_active_path]
        return active_path + self.project_path

    def add_path_to_sys_path(self):
        """Add Spyder path to sys.path"""
        for path in reversed(self.get_spyder_pythonpath()):
            sys.path.insert(1, path)

    def remove_path_from_sys_path(self):
        """Remove Spyder path from sys.path"""
        sys_path = sys.path
        for path in self.path:
            while path in sys_path:
                sys_path.remove(path)

    @Slot()
    def path_manager_callback(self):
        """Spyder path manager"""
        from spyder.widgets.pathmanager import PathManager
        self.remove_path_from_sys_path()
        project_path = self.projects.get_pythonpath()
        dialog = PathManager(self, self.path, project_path,
                             self.not_active_path, sync=True)
        dialog.redirect_stdio.connect(self.redirect_internalshell_stdio)
        dialog.exec_()
        self.add_path_to_sys_path()
        encoding.writelines(self.path, self.SPYDER_PATH) # Saving path
        encoding.writelines(self.not_active_path, self.SPYDER_NOT_ACTIVE_PATH)
        self.sig_pythonpath_changed.emit()

    def pythonpath_changed(self):
        """Projects PYTHONPATH contribution has changed"""
        self.remove_path_from_sys_path()
        self.project_path = self.projects.get_pythonpath()
        self.add_path_to_sys_path()
        self.sig_pythonpath_changed.emit()

    @Slot()
    def win_env(self):
        """Show Windows current user environment variables"""
        self.dialog_manager.show(WinUserEnvDialog(self))

    #---- Preferences
    def apply_settings(self):
        """Apply settings changed in 'Preferences' dialog box"""
        qapp = QApplication.instance()
        # Set 'gtk+' as the default theme in Gtk-based desktops
        # Fixes Issue 2036
        if is_gtk_desktop() and ('GTK+' in QStyleFactory.keys()):
            try:
                qapp.setStyle('gtk+')
            except:
                pass
        else:
            style_name = CONF.get('main', 'windows_style',
                                  self.default_style)
            style = QStyleFactory.create(style_name)
            if style is not None:
                style.setProperty('name', style_name)
                qapp.setStyle(style)

        default = self.DOCKOPTIONS
        if CONF.get('main', 'vertical_tabs'):
            default = default|QMainWindow.VerticalTabs
        if CONF.get('main', 'animated_docks'):
            default = default|QMainWindow.AnimatedDocks
        self.setDockOptions(default)

        self.apply_panes_settings()
        self.apply_statusbar_settings()

        if CONF.get('main', 'use_custom_cursor_blinking'):
            qapp.setCursorFlashTime(CONF.get('main', 'custom_cursor_blinking'))
        else:
            qapp.setCursorFlashTime(self.CURSORBLINK_OSDEFAULT)

    def apply_panes_settings(self):
        """Update dockwidgets features settings"""
        # Update toggle action on menu
        for child in self.widgetlist:
            features = child.FEATURES
            if CONF.get('main', 'vertical_dockwidget_titlebars'):
                features = features | QDockWidget.DockWidgetVerticalTitleBar
            if not self.dockwidgets_locked:
                features = features | QDockWidget.DockWidgetMovable
            child.dockwidget.setFeatures(features)
            child.update_margins()

    def apply_statusbar_settings(self):
        """Update status bar widgets settings"""
        show_status_bar = CONF.get('main', 'show_status_bar')
        self.statusBar().setVisible(show_status_bar)

        if show_status_bar:
            for widget, name in ((self.mem_status, 'memory_usage'),
                                 (self.cpu_status, 'cpu_usage')):
                if widget is not None:
                    widget.setVisible(CONF.get('main', '%s/enable' % name))
                    widget.set_interval(CONF.get('main', '%s/timeout' % name))
        else:
            return

    @Slot()
    def edit_preferences(self):
        """Edit Spyder preferences"""
        from spyder.plugins.configdialog import ConfigDialog
        dlg = ConfigDialog(self)
        dlg.size_change.connect(self.set_prefs_size)
        if self.prefs_dialog_size is not None:
            dlg.resize(self.prefs_dialog_size)
        for PrefPageClass in self.general_prefs:
            widget = PrefPageClass(dlg, main=self)
            widget.initialize()
            dlg.add_page(widget)
        for plugin in [self.workingdirectory, self.editor,
                       self.projects, self.ipyconsole,
                       self.historylog, self.help, self.variableexplorer,
                       self.onlinehelp, self.explorer, self.findinfiles
                       ]+self.thirdparty_plugins:
            if plugin is not None:
                try:
                    widget = plugin.create_configwidget(dlg)
                    if widget is not None:
                        dlg.add_page(widget)
                except Exception:
                    traceback.print_exc(file=sys.stderr)
        if self.prefs_index is not None:
            dlg.set_current_index(self.prefs_index)
        dlg.show()
        dlg.check_all_settings()
        dlg.pages_widget.currentChanged.connect(self.__preference_page_changed)
        dlg.exec_()

    def __preference_page_changed(self, index):
        """Preference page index has changed"""
        self.prefs_index = index

    def set_prefs_size(self, size):
        """Save preferences dialog size"""
        self.prefs_dialog_size = size

    #---- Shortcuts
    def register_shortcut(self, qaction_or_qshortcut, context, name,
                          add_sc_to_tip=False):
        """
        Register QAction or QShortcut to Spyder main application,
        with shortcut (context, name, default)
        """
        self.shortcut_data.append( (qaction_or_qshortcut, context,
                                    name, add_sc_to_tip) )

    def apply_shortcuts(self):
        """Apply shortcuts settings to all widgets/plugins"""
        toberemoved = []
        for index, (qobject, context, name,
                    add_sc_to_tip) in enumerate(self.shortcut_data):
            keyseq = QKeySequence( get_shortcut(context, name) )
            try:
                if isinstance(qobject, QAction):
                    if sys.platform == 'darwin' and \
                      qobject._shown_shortcut == 'missing':
                        qobject._shown_shortcut = keyseq
                    else:
                        qobject.setShortcut(keyseq)
                    if add_sc_to_tip:
                        add_shortcut_to_tooltip(qobject, context, name)
                elif isinstance(qobject, QShortcut):
                    qobject.setKey(keyseq)
            except RuntimeError:
                # Object has been deleted
                toberemoved.append(index)
        for index in sorted(toberemoved, reverse=True):
            self.shortcut_data.pop(index)

    @Slot()
    def show_shortcuts_dialog(self):
        from spyder.widgets.shortcutssummary import ShortcutsSummaryDialog
        dlg = ShortcutsSummaryDialog(None)
        dlg.exec_()

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
                # See Issue 1275 for details on why errno EINTR is
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
        """
        Quit and Restart Spyder application.

        If reset True it allows to reset spyder on restart.
        """
        # Get start path to use in restart script
        spyder_start_directory = get_module_path('spyder')
        restart_script = osp.join(spyder_start_directory, 'app', 'restart.py')

        # Get any initial argument passed when spyder was started
        # Note: Variables defined in bootstrap.py and spyder/app/start.py
        env = os.environ.copy()
        bootstrap_args = env.pop('SPYDER_BOOTSTRAP_ARGS', None)
        spyder_args = env.pop('SPYDER_ARGS')

        # Get current process and python running spyder
        pid = os.getpid()
        python = sys.executable

        # Check if started with bootstrap.py
        if bootstrap_args is not None:
            spyder_args = bootstrap_args
            is_bootstrap = True
        else:
            is_bootstrap = False

        # Pass variables as environment variables (str) to restarter subprocess
        env['SPYDER_ARGS'] = spyder_args
        env['SPYDER_PID'] = str(pid)
        env['SPYDER_IS_BOOTSTRAP'] = str(is_bootstrap)
        env['SPYDER_RESET'] = str(reset)

        if DEV:
            if os.name == 'nt':
                env['PYTHONPATH'] = ';'.join(sys.path)
            else:
                env['PYTHONPATH'] = ':'.join(sys.path)

        # Build the command and popen arguments depending on the OS
        if os.name == 'nt':
            # Hide flashing command prompt
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            shell = False
        else:
            startupinfo = None
            shell = True

        command = '"{0}" "{1}"'
        command = command.format(python, restart_script)

        try:
            if self.closing(True):
                subprocess.Popen(command, shell=shell, env=env,
                                 startupinfo=startupinfo)
                self.console.quit()
        except Exception as error:
            # If there is an error with subprocess, Spyder should not quit and
            # the error can be inspected in the internal console
            print(error)  # spyder: test-skip
            print(command)  # spyder: test-skip

    # ---- Interactive Tours
    def show_tour(self, index):
        """ """
        frames = self.tours_available[index]
        self.tour.set_tour(index, frames, self)
        self.tour.start_tour()

    # ---- Global File Switcher
    def open_fileswitcher(self, symbol=False):
        """Open file list management dialog box."""
        if self.fileswitcher is not None and \
          self.fileswitcher.is_visible:
            self.fileswitcher.hide()
            self.fileswitcher.is_visible = False
            return
        if symbol:
            self.fileswitcher.plugin = self.editor
            self.fileswitcher.set_search_text('@')
        else:
            self.fileswitcher.set_search_text('')
        self.fileswitcher.show()
        self.fileswitcher.is_visible = True

    def open_symbolfinder(self):
        """Open symbol list management dialog box."""
        self.open_fileswitcher(symbol=True)

    def add_to_fileswitcher(self, plugin, tabs, data, icon):
        """Add a plugin to the File Switcher."""
        if self.fileswitcher is None:
            self.fileswitcher = FileSwitcher(self, plugin, tabs, data, icon)
        else:
            self.fileswitcher.add_plugin(plugin, tabs, data, icon)

        self.fileswitcher.sig_goto_file.connect(
                plugin.get_current_tab_manager().set_stack_index)

    # ---- Check for Spyder Updates
    def _check_updates_ready(self):
        """Called by WorkerUpdates when ready"""
        from spyder.widgets.helperwidgets import MessageCheckBox

        # feedback` = False is used on startup, so only positive feedback is
        # given. `feedback` = True is used when after startup (when using the
        # menu action, and gives feeback if updates are, or are not found.
        feedback = self.give_updates_feedback

        # Get results from worker
        update_available = self.worker_updates.update_available
        latest_release = self.worker_updates.latest_release
        error_msg = self.worker_updates.error

        url_r = 'https://github.com/spyder-ide/spyder/releases'
        url_i = 'http://pythonhosted.org/spyder/installation.html'

        # Define the custom QMessageBox
        box = MessageCheckBox(icon=QMessageBox.Information,
                              parent=self)
        box.setWindowTitle(_("Spyder updates"))
        box.set_checkbox_text(_("Check for updates on startup"))
        box.setStandardButtons(QMessageBox.Ok)
        box.setDefaultButton(QMessageBox.Ok)

        # Adjust the checkbox depending on the stored configuration
        section, option = 'main', 'check_updates_on_startup'
        check_updates = CONF.get(section, option)
        box.set_checked(check_updates)

        if error_msg is not None:
            msg = error_msg
            box.setText(msg)
            box.set_check_visible(False)
            box.exec_()
            check_updates = box.is_checked()
        else:
            if update_available:
                anaconda_msg = ''
                if 'Anaconda' in sys.version or 'conda-forge' in sys.version:
                    anaconda_msg = _("<hr><b>IMPORTANT NOTE:</b> It seems "
                                     "that you are using Spyder with "
                                     "<b>Anaconda/Miniconda</b>. Please "
                                     "<b>don't</b> use <code>pip</code> to "
                                     "update it as that will probably break "
                                     "your installation.<br><br>"
                                     "Instead, please wait until new conda "
                                     "packages are available and use "
                                     "<code>conda</code> to perform the "
                                     "update.<hr>")
                msg = _("<b>Spyder %s is available!</b> <br><br>Please use "
                        "your package manager to update Spyder or go to our "
                        "<a href=\"%s\">Releases</a> page to download this "
                        "new version. <br><br>If you are not sure how to "
                        "proceed to update Spyder please refer to our "
                        " <a href=\"%s\">Installation</a> instructions."
                        "") % (latest_release, url_r, url_i)
                msg += '<br>' + anaconda_msg
                box.setText(msg)
                box.set_check_visible(True)
                box.exec_()
                check_updates = box.is_checked()
            elif feedback:
                msg = _("Spyder is up to date.")
                box.setText(msg)
                box.set_check_visible(False)
                box.exec_()
                check_updates = box.is_checked()

        # Update checkbox based on user interaction
        CONF.set(section, option, check_updates)

        # Enable check_updates_action after the thread has finished
        self.check_updates_action.setDisabled(False)

        # Provide feeback when clicking menu if check on startup is on
        self.give_updates_feedback = True

    @Slot()
    def check_updates(self, startup=False):
        """
        Check for spyder updates on github releases using a QThread.
        """
        from spyder.workers.updates import WorkerUpdates

        # Disable check_updates_action while the thread is working
        self.check_updates_action.setDisabled(True)

        if self.thread_updates is not None:
            self.thread_updates.terminate()

        self.thread_updates = QThread(self)
        self.worker_updates = WorkerUpdates(self, startup=startup)
        self.worker_updates.sig_ready.connect(self._check_updates_ready)
        self.worker_updates.sig_ready.connect(self.thread_updates.quit)
        self.worker_updates.moveToThread(self.thread_updates)
        self.thread_updates.started.connect(self.worker_updates.start)
        self.thread_updates.start()


#==============================================================================
# Utilities to create the 'main' function
#==============================================================================
def initialize():
    """Initialize Qt, patching sys.exit and eventually setting up ETS"""
    # This doesn't create our QApplication, just holds a reference to
    # MAIN_APP, created above to show our splash screen as early as
    # possible
    app = qapplication()

    # --- Set application icon
    app.setWindowIcon(APP_ICON)

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

    # Selecting Qt4 backend for Enthought Tool Suite (if installed)
    try:
        from enthought.etsconfig.api import ETSConfig
        ETSConfig.toolkit = 'qt4'
    except ImportError:
        pass

    return app


class Spy(object):
    """
    Inspect Spyder internals

    Attributes:
        app       Reference to main QApplication object
        window    Reference to spyder.MainWindow widget
    """
    def __init__(self, app, window):
        self.app = app
        self.window = window
    def __dir__(self):
        return list(self.__dict__.keys()) +\
                 [x for x in dir(self.__class__) if x[0] != '_']
    def versions(self):
        return get_versions()


def run_spyder(app, options, args):
    """
    Create and show Spyder's main window
    Start QApplication event loop
    """
    #TODO: insert here
    # Main window
    main = MainWindow(options)
    try:
        main.setup()
    except BaseException:
        if main.console is not None:
            try:
                main.console.shell.exit_interpreter()
            except BaseException:
                pass
        raise

    main.show()
    main.post_visible_setup()

    if main.console:
        main.console.shell.interpreter.namespace['spy'] = \
                                                    Spy(app=app, window=main)

    # Open external files passed as args
    if args:
        for a in args:
            main.open_external_file(a)

    # Don't show icons in menus for Mac
    if sys.platform == 'darwin':
        QCoreApplication.setAttribute(Qt.AA_DontShowIconsInMenus, True)

    # Open external files with our Mac app
    if running_in_mac_app():
        app.sig_open_external_file.connect(main.open_external_file)

    # To give focus again to the last focused widget after restoring
    # the window
    app.focusChanged.connect(main.change_last_focused_widget)

    if not PYTEST:
        app.exec_()
    return main


#==============================================================================
# Main
#==============================================================================
def main():
    """Main function"""

    # **** Collect command line options ****
    # Note regarding Options:
    # It's important to collect options before monkey patching sys.exit,
    # otherwise, argparse won't be able to exit if --help option is passed
    options, args = get_options()

    if options.show_console:
        print("(Deprecated) --show console does nothing, now the default "
              " behavior is to show the console, use --hide-console if you "
              "want to hide it")

    if set_attached_console_visible is not None:
        set_attached_console_visible(not options.hide_console
                                     or options.reset_config_files
                                     or options.reset_to_defaults
                                     or options.optimize or bool(DEBUG))

    app = initialize()
    if options.reset_config_files:
        # <!> Remove all configuration files!
        reset_config_files()
        return
    elif options.reset_to_defaults:
        # Reset Spyder settings to defaults
        CONF.reset_to_defaults(save=True)
        return
    elif options.optimize:
        # Optimize the whole Spyder's source code directory
        import spyder
        programs.run_python_script(module="compileall",
                                   args=[spyder.__path__[0]], p_args=['-O'])
        return

    # Show crash dialog
    if CONF.get('main', 'crash', False) and not DEV:
        CONF.set('main', 'crash', False)
        if SPLASH is not None:
            SPLASH.hide()
        QMessageBox.information(None, "Spyder",
            "Spyder crashed during last session.<br><br>"
            "If Spyder does not start at all and <u>before submitting a "
            "bug report</u>, please try to reset settings to defaults by "
            "running Spyder with the command line option '--reset':<br>"
            "<span style=\'color: #555555\'><b>spyder --reset</b></span>"
            "<br><br>"
            "<span style=\'color: #ff5555\'><b>Warning:</b></span> "
            "this command will remove all your Spyder configuration files "
            "located in '%s').<br><br>"
            "If restoring the default settings does not help, please take "
            "the time to search for <a href=\"%s\">known bugs</a> or "
            "<a href=\"%s\">discussions</a> matching your situation before "
            "eventually creating a new issue <a href=\"%s\">here</a>. "
            "Your feedback will always be greatly appreciated."
            "" % (get_conf_path(), __project_url__,
                  __forum_url__, __project_url__))

    # Create main window
    mainwindow = None
    try:
        mainwindow = run_spyder(app, options, args)
    except FontError as fontError:
        QMessageBox.information(None, "Spyder",
                "Spyder was unable to load the <i>Spyder 3</i> "
                "icon theme. That's why it's going to fallback to the "
                "theme used in Spyder 2.<br><br>"
                "For that, please close this window and start Spyder again.")
        CONF.set('main', 'icon_theme', 'spyder 2')
    except BaseException:
        CONF.set('main', 'crash', True)
        import traceback
        traceback.print_exc(file=STDERR)
        traceback.print_exc(file=open('spyder_crash.log', 'w'))
    if mainwindow is None:
        # An exception occured
        if SPLASH is not None:
            SPLASH.hide()
        return

    ORIGINAL_SYS_EXIT()


if __name__ == "__main__":
    main()

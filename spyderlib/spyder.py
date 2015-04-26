# -*- coding: utf-8 -*-
#
# Copyright © 2009-2013 Pierre Raybaut
# Copyright © 2013-2015 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder, the Scientific PYthon Development EnviRonment
=====================================================

Developped and maintained by the Spyder Development
Team

Copyright © 2009 - 2015 Pierre Raybaut
Copyright © 2010 - 2015 The Spyder Development Team
Licensed under the terms of the MIT License
(see spyderlib/__init__.py for details)
"""

from __future__ import print_function


#==============================================================================
# Stdlib imports
#==============================================================================
import atexit
import errno
import os
import os.path as osp
import re
import socket
import shutil
import subprocess
import sys
import threading


#==============================================================================
# Keeping a reference to the original sys.exit before patching it
#==============================================================================
ORIGINAL_SYS_EXIT = sys.exit


#==============================================================================
# Check requirements
#==============================================================================
from spyderlib import requirements
requirements.check_path()
requirements.check_qt()


#==============================================================================
# Windows only: support for hiding console window when started with python.exe
#==============================================================================
set_attached_console_visible = None
is_attached_console_visible = None
set_windows_appusermodelid = None
if os.name == 'nt':
    from spyderlib.utils.windows import (set_attached_console_visible,
                                         is_attached_console_visible,
                                         set_windows_appusermodelid)


#==============================================================================
# Workaround: importing rope.base.project here, otherwise this module can't
# be imported if Spyder was executed from another folder than spyderlib
#==============================================================================
try:
    import rope.base.project  # analysis:ignore
except ImportError:
    pass


#==============================================================================
# Qt imports
#==============================================================================
from spyderlib.qt import PYQT5
from spyderlib.qt.QtGui import (QApplication, QMainWindow, QSplashScreen,
                                QPixmap, QMessageBox, QMenu, QColor, QShortcut,
                                QKeySequence, QDockWidget, QAction,
                                QDesktopServices)
from spyderlib.qt.QtCore import (Signal, QPoint, Qt, QSize, QByteArray, QUrl,
                                 Slot, QTimer, QCoreApplication, QThread)
from spyderlib.qt.compat import (from_qvariant, getopenfilename,
                                 getsavefilename)
# Avoid a "Cannot mix incompatible Qt library" error on Windows platforms
# when PySide is selected by the QT_API environment variable and when PyQt4
# is also installed (or any other Qt-based application prepending a directory
# containing incompatible Qt DLLs versions in PATH):
from spyderlib.qt import QtSvg  # analysis:ignore


#==============================================================================
# Create our QApplication instance here because it's needed to render the
# splash screen created below
#==============================================================================
from spyderlib.utils.qthelpers import qapplication
MAIN_APP = qapplication()


#==============================================================================
# Create splash screen out of MainWindow to reduce perceived startup time. 
#==============================================================================
from spyderlib.baseconfig import _, get_image_path, DEV
SPLASH = QSplashScreen(QPixmap(get_image_path('splash.png'), 'png'))
SPLASH_FONT = SPLASH.font()
SPLASH_FONT.setPixelSize(10)
SPLASH.setFont(SPLASH_FONT)
SPLASH.show()
SPLASH.showMessage(_("Initializing..."), Qt.AlignBottom | Qt.AlignCenter |
                   Qt.AlignAbsolute, QColor(Qt.white))
QApplication.processEvents()


#==============================================================================
# Local utility imports
#==============================================================================
from spyderlib import __version__, __project_url__, __forum_url__, get_versions
from spyderlib.baseconfig import (get_conf_path, get_module_data_path,
                                  get_module_source_path, STDERR, DEBUG, DEV,
                                  debug_print, TEST, SUBFOLDER, MAC_APP_NAME,
                                  running_in_mac_app, get_module_path)
from spyderlib.config import CONF, EDIT_EXT, IMPORT_EXT, OPEN_FILES_PORT
from spyderlib.cli_options import get_options
from spyderlib import dependencies
from spyderlib.ipythonconfig import IPYTHON_QT_INSTALLED
from spyderlib.userconfig import NoDefault
from spyderlib.utils import encoding, programs
from spyderlib.utils.iofuncs import load_session, save_session, reset_session
from spyderlib.utils.programs import is_module_installed
from spyderlib.utils.introspection import module_completion
from spyderlib.utils.misc import select_port
from spyderlib.py3compat import (PY3, to_text_string, is_text_string, getcwd,
                                 u, qbytearray_to_str, configparser as cp)


#==============================================================================
# Local gui imports
#==============================================================================
# NOTE: Move (if possible) import's of widgets and plugins exactly where they
# are needed in MainWindow to speed up perceived startup time (i.e. the time
# from clicking the Spyder icon to showing the splash screen).
try:
    from spyderlib.utils.environ import WinUserEnvDialog
except ImportError:
    WinUserEnvDialog = None  # analysis:ignore

from spyderlib.utils.qthelpers import (create_action, add_actions, get_icon,
                                       get_std_icon, add_shortcut_to_tooltip,
                                       create_module_bookmark_actions,
                                       create_bookmark_action,
                                       create_program_action, DialogManager,
                                       keybinding, create_python_script_action,
                                       file_uri)
from spyderlib.guiconfig import get_shortcut, remove_deprecated_shortcuts
from spyderlib.otherplugins import get_spyderplugins_mods
from spyderlib import tour # FIXME: Better place for this?


#==============================================================================
# To save and load temp sessions
#==============================================================================
TEMP_SESSION_PATH = get_conf_path('temp.session.tar')


#==============================================================================
# Get the cwd before initializing WorkingDirectory, which sets it to the one
# used in the last session
#==============================================================================
CWD = getcwd()


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
                      if re.match(r"(?i)Python[0-9]{3}.chm", path)]
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
    from spyderlib.widgets.shell import PythonShellWidget
    from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
    if isinstance(widget, PythonShellWidget):
        return widget
    elif isinstance(widget, ExternalPythonShell):
        return widget.shell


def get_focus_widget_properties():
    """Get properties of focus widget
    Returns tuple (widget, properties) where properties is a tuple of
    booleans: (is_console, not_readonly, readwrite_editor)"""
    widget = QApplication.focusWidget()
    from spyderlib.widgets.shell import ShellBaseWidget
    from spyderlib.widgets.editor import TextEditBaseWidget
    textedit_properties = None
    if isinstance(widget, (ShellBaseWidget, TextEditBaseWidget)):
        console = isinstance(widget, ShellBaseWidget)
        not_readonly = not widget.isReadOnly()
        readwrite_editor = not_readonly and not console
        textedit_properties = (console, not_readonly, readwrite_editor)
    return widget, textedit_properties


#==============================================================================
# Qt Stylesheet for MainWindow
#==============================================================================
#TODO: Improve the stylesheet below for separator handles to be visible
#      (in Qt, these handles are by default not visible on Windows!)
STYLESHEET="""
QSplitter::handle {
    margin-left: 4px;
    margin-right: 4px;
}

QSplitter::handle:horizontal {
    width: 1px;
    border-width: 0px;
    background-color: lightgray;
}

QSplitter::handle:vertical {
    border-top: 2px ridge lightgray;
    border-bottom: 2px;
}

QMainWindow::separator:vertical {
    margin-left: 1px;
    margin-top: 25px;
    margin-bottom: 25px;
    border-left: 2px groove lightgray;
    border-right: 1px;
}

QMainWindow::separator:horizontal {
    margin-top: 1px;
    margin-left: 5px;
    margin-right: 5px;
    border-top: 2px groove lightgray;
    border-bottom: 2px;
}
"""


#==============================================================================
# Main Window
#==============================================================================
class MainWindow(QMainWindow):
    """Spyder main window"""
    DOCKOPTIONS = QMainWindow.AllowTabbedDocks|QMainWindow.AllowNestedDocks
    SPYDER_PATH = get_conf_path('path')
    BOOKMARKS = (
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
         ('xy', "http://code.google.com/p/pythonxy/",
          _("Python(x,y)")),
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
        self.default_style = str(qapp.style().objectName())

        self.dialog_manager = DialogManager()

        self.init_workdir = options.working_directory
        self.profile = options.profile
        self.multithreaded = options.multithreaded
        self.light = options.light
        self.new_instance = options.new_instance
        self.test_travis = os.environ.get('SPYDER_TEST_TRAVIS', None)

        self.debug_print("Start of MainWindow constructor")

#        self.setStyleSheet(STYLESHEET)

        # Shortcut management data
        self.shortcut_data = []

        # Loading Spyder path
        self.path = []
        self.project_path = []
        if osp.isfile(self.SPYDER_PATH):
            self.path, _x = encoding.readlines(self.SPYDER_PATH)
            self.path = [name for name in self.path if osp.isdir(name)]
        self.remove_path_from_sys_path()
        self.add_path_to_sys_path()
        self.load_temp_session_action = create_action(self,
                                        _("Reload last session"),
                                        triggered=lambda:
                                        self.load_session(TEMP_SESSION_PATH))
        self.load_session_action = create_action(self,
                                        _("Load session..."),
                                        None, 'fileopen.png',
                                        triggered=self.load_session,
                                        tip=_("Load Spyder session"))
        self.save_session_action = create_action(self,
                                        _("Save session and quit..."),
                                        None, 'filesaveas.png',
                                        triggered=self.save_session,
                                        tip=_("Save current session "
                                              "and quit application"))

        # Plugins
        self.console = None
        self.workingdirectory = None
        self.editor = None
        self.explorer = None
        self.inspector = None
        self.onlinehelp = None
        self.projectexplorer = None
        self.outlineexplorer = None
        self.historylog = None
        self.extconsole = None
        self.ipyconsole = None
        self.variableexplorer = None
        self.findinfiles = None
        self.thirdparty_plugins = []

        # Tour  # TODO: Should I consider it a plugin?? or?
        self.tour = None
        self.tours_available = None

        # Check for updates Thread and Worker, refereces needed to prevent
        # segfaulting
        self.check_updates_action = None
        self.thread_updates = None
        self.worker_updates = None
        self.give_updates_feedback = True

        # Preferences
        from spyderlib.plugins.configdialog import (MainConfigPage,
                                                    ColorSchemeConfigPage)
        from spyderlib.plugins.shortcuts import ShortcutsConfigPage
        from spyderlib.plugins.runconfig import RunConfigPage
        self.general_prefs = [MainConfigPage, ShortcutsConfigPage,
                              ColorSchemeConfigPage, RunConfigPage]
        self.prefs_index = None
        self.prefs_dialog_size = None

        # Quick Layouts and Dialogs
        from spyderlib.plugins.layoutdialog import (LayoutSaveDialog,
                                                    LayoutSettingsDialog)
        self.dialog_layout_save = LayoutSaveDialog
        self.dialog_layout_settings = LayoutSettingsDialog

        # Actions
        self.close_dockwidget_action = None
        self.lock_dockwidget_action = None
        self.find_action = None
        self.find_next_action = None
        self.find_previous_action = None
        self.replace_action = None
        self.undo_action = None
        self.redo_action = None
        self.copy_action = None
        self.cut_action = None
        self.paste_action = None
        self.delete_action = None
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
        self.tools_menu = None
        self.tools_menu_actions = []
        self.external_tools_menu = None # We must keep a reference to this,
        # otherwise the external tools menu is lost after leaving setup method
        self.external_tools_menu_actions = []
        self.view_menu = None
        self.plugins_menu = None
        self.toolbars_menu = None
        self.help_menu = None
        self.help_menu_actions = []

        # Status bar widgets
        self.mem_status = None
        self.cpu_status = None

        # Toolbars
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
        self.setWindowTitle(title)
        icon_name = 'spyder_light.svg' if self.light else 'spyder.svg'
        # Resampling SVG icon only on non-Windows platforms (see Issue 1314):
        self.setWindowIcon(get_icon(icon_name, resample=os.name != 'nt'))
        if set_windows_appusermodelid != None:
            res = set_windows_appusermodelid()
            debug_print("appusermodelid: " + str(res))

        # Setting QTimer if running in travis
        if self.test_travis is not None:
            global MAIN_APP
            timer_shutdown_time = int(os.environ['SPYDER_TEST_TRAVIS_TIMER'])
            self.timer_shutdown = QTimer(self)
            self.timer_shutdown.timeout.connect(MAIN_APP.quit)
            self.timer_shutdown.start(timer_shutdown_time)

        # Showing splash screen
        self.splash = SPLASH
        if not self.light:
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

        self.dockwidgets_locked = False
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

        # Session manager
        self.next_session_name = None
        self.save_session_name = None

        # Track which console plugin type had last focus
        # True: Console plugin
        # False: IPython console plugin
        self.last_console_plugin_focus_was_python = True

        # To keep track of the last focused widget
        self.last_focused_widget = None

        # Server to open external files on a single instance
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
        toolbar.setIconSize( QSize(iconsize, iconsize) )
        self.toolbarslist.append(toolbar)
        return toolbar

    def setup(self):
        """Setup main window"""
        self.debug_print("*** Start of MainWindow setup ***")
        if not self.light:
            self.debug_print("  ..core actions")
            self.close_dockwidget_action = create_action(self,
                                        _("Close current pane"),
                                        triggered=self.close_current_dockwidget,
                                        context=Qt.ApplicationShortcut)
            self.register_shortcut(self.close_dockwidget_action, "_",
                                   "Close pane")

            # custom layouts shortcuts
            self.toggle_next_layout_action = create_action(self,
                                        _("Toggle next layout"),
                                        triggered=self.toggle_next_layout,
                                        context=Qt.ApplicationShortcut)
            self.toggle_previous_layout_action = create_action(self,
                                        _("Toggle previous layout"),
                                        triggered=self.toggle_previous_layout,
                                        context=Qt.ApplicationShortcut)
            self.register_shortcut(self.toggle_next_layout_action, "_",
                                   "Toggle next layout")
            self.register_shortcut(self.toggle_previous_layout_action, "_",
                                   "Toggle previous layout")


            _text = _("&Find text")
            self.find_action = create_action(self, _text, icon='find.png',
                                             tip=_text, triggered=self.find,
                                             context=Qt.WidgetShortcut)
            self.register_shortcut(self.find_action, "Editor", "Find text")
            self.find_next_action = create_action(self, _("Find &next"),
                  icon='findnext.png', triggered=self.find_next,
                  context=Qt.WidgetShortcut)
            self.register_shortcut(self.find_next_action, "Editor",
                                   "Find next")
            self.find_previous_action = create_action(self,
                        _("Find &previous"),
                        icon='findprevious.png', triggered=self.find_previous,
                        context=Qt.WidgetShortcut)
            self.register_shortcut(self.find_previous_action, "Editor",
                                   "Find previous")
            _text = _("&Replace text")
            self.replace_action = create_action(self, _text, icon='replace.png',
                                            tip=_text, triggered=self.replace,
                                            context=Qt.WidgetShortcut)
            self.register_shortcut(self.replace_action, "Editor",
                                   "Replace text")
            def create_edit_action(text, tr_text, icon_name):
                textseq = text.split(' ')
                method_name = textseq[0].lower()+"".join(textseq[1:])
                return create_action(self, tr_text,
                                     shortcut=keybinding(text.replace(' ', '')),
                                     icon=get_icon(icon_name),
                                     triggered=self.global_callback,
                                     data=method_name,
                                     context=Qt.WidgetShortcut)
            self.undo_action = create_edit_action("Undo", _("Undo"),
                                                  'undo.png')
            self.redo_action = create_edit_action("Redo", _("Redo"), 'redo.png')
            self.copy_action = create_edit_action("Copy", _("Copy"),
                                                  'editcopy.png')
            self.cut_action = create_edit_action("Cut", _("Cut"), 'editcut.png')
            self.paste_action = create_edit_action("Paste", _("Paste"),
                                                   'editpaste.png')
            self.delete_action = create_edit_action("Delete", _("Delete"),
                                                    'editdelete.png')
            self.selectall_action = create_edit_action("Select All",
                                                       _("Select All"),
                                                       'selectall.png')
            self.edit_menu_actions = [self.undo_action, self.redo_action,
                                      None, self.cut_action, self.copy_action,
                                      self.paste_action, self.delete_action,
                                      None, self.selectall_action]
            self.search_menu_actions = [self.find_action, self.find_next_action,
                                        self.find_previous_action,
                                        self.replace_action]
            self.search_toolbar_actions = [self.find_action,
                                           self.find_next_action,
                                           self.replace_action]

        namespace = None
        if not self.light:
            self.debug_print("  ..toolbars")
            # File menu/toolbar
            self.file_menu = self.menuBar().addMenu(_("&File"))
            self.file_menu.aboutToShow.connect(self.update_file_menu)
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
                                         icon='configure.png',
                                         triggered=self.edit_preferences)
            self.register_shortcut(prefs_action, "_", "Preferences")
            add_shortcut_to_tooltip(prefs_action, context="_",
                                    name="Preferences")
            spyder_path_action = create_action(self,
                                    _("PYTHONPATH manager"),
                                    None, 'pythonpath_mgr.png',
                                    triggered=self.path_manager_callback,
                                    tip=_("Python Path Manager"),
                                    menurole=QAction.ApplicationSpecificRole)
            update_modules_action = create_action(self,
                                        _("Update module names list"),
                                        triggered=lambda:
                                                  module_completion.reset(),
                                        tip=_("Refresh list of module names "
                                              "available in PYTHONPATH"))
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
            self.tools_menu_actions += [None, update_modules_action]

            # External Tools submenu
            self.external_tools_menu = QMenu(_("External Tools"))
            self.external_tools_menu_actions = []
            # Python(x,y) launcher
            self.xy_action = create_action(self,
                                   _("Python(x,y) launcher"),
                                   icon=get_icon('pythonxy.png'),
                                   triggered=lambda:
                                   programs.run_python_script('xy', 'xyhome'))
            if os.name == 'nt' and is_module_installed('xy'):
                self.external_tools_menu_actions.append(self.xy_action)
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
            if additact and (is_module_installed('winpython') or \
              is_module_installed('xy')):
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
                                            triggered=self.maximize_dockwidget)
            self.register_shortcut(self.maximize_action, "_",
                                   "Maximize pane")
            self.__update_maximize_action()

            # Fullscreen mode
            self.fullscreen_action = create_action(self,
                                            _("Fullscreen mode"),
                                            triggered=self.toggle_fullscreen)
            self.register_shortcut(self.fullscreen_action, "_",
                                   "Fullscreen mode")
            add_shortcut_to_tooltip(self.fullscreen_action, context="_",
                                    name="Fullscreen mode")

            # Main toolbar
            self.main_toolbar_actions = [self.maximize_action,
                                         self.fullscreen_action, None,
                                         prefs_action, spyder_path_action]

            self.main_toolbar = self.create_toolbar(_("Main toolbar"),
                                                    "main_toolbar")

            # Internal console plugin
            self.debug_print("  ..plugin: internal console")
            from spyderlib.plugins.console import Console
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
            from spyderlib.plugins.workingdirectory import WorkingDirectory
            self.workingdirectory = WorkingDirectory(self, self.init_workdir, main=self)
            self.workingdirectory.register_plugin()
            self.toolbarslist.append(self.workingdirectory)

            # Object inspector plugin
            if CONF.get('inspector', 'enable'):
                self.set_splash(_("Loading object inspector..."))
                from spyderlib.plugins.inspector import ObjectInspector
                self.inspector = ObjectInspector(self)
                self.inspector.register_plugin()

            # Outline explorer widget
            if CONF.get('outline_explorer', 'enable'):
                self.set_splash(_("Loading outline explorer..."))
                from spyderlib.plugins.outlineexplorer import OutlineExplorer
                fullpath_sorting = CONF.get('editor', 'fullpath_sorting', True)
                self.outlineexplorer = OutlineExplorer(self,
                                            fullpath_sorting=fullpath_sorting)
                self.outlineexplorer.register_plugin()

            # Editor plugin
            self.set_splash(_("Loading editor..."))
            from spyderlib.plugins.editor import Editor
            self.editor = Editor(self)
            self.editor.register_plugin()

            # Populating file menu entries
            quit_action = create_action(self, _("&Quit"),
                                        icon='exit.png', tip=_("Quit"),
                                        triggered=self.console.quit)
            self.register_shortcut(quit_action, "_", "Quit")
            restart_action = create_action(self, _("&Restart"),
                                           icon='restart.png',
                                           tip=_("Restart"),
                                           triggered=self.restart)
            self.register_shortcut(restart_action, "_", "Restart")

            self.file_menu_actions += [self.load_temp_session_action,
                                       self.load_session_action,
                                       self.save_session_action,
                                       None, restart_action, quit_action]
            self.set_splash("")

            self.debug_print("  ..widgets")
            # Find in files
            if CONF.get('find_in_files', 'enable'):
                from spyderlib.plugins.findinfiles import FindInFiles
                self.findinfiles = FindInFiles(self)
                self.findinfiles.register_plugin()

            # Explorer
            if CONF.get('explorer', 'enable'):
                self.set_splash(_("Loading file explorer..."))
                from spyderlib.plugins.explorer import Explorer
                self.explorer = Explorer(self)
                self.explorer.register_plugin()

            # History log widget
            if CONF.get('historylog', 'enable'):
                self.set_splash(_("Loading history plugin..."))
                from spyderlib.plugins.history import HistoryLog
                self.historylog = HistoryLog(self)
                self.historylog.register_plugin()

            # Online help widget
            try:    # Qt >= v4.4
                from spyderlib.plugins.onlinehelp import OnlineHelp
            except ImportError:    # Qt < v4.4
                OnlineHelp = None  # analysis:ignore
            if CONF.get('onlinehelp', 'enable') and OnlineHelp is not None:
                self.set_splash(_("Loading online help..."))
                self.onlinehelp = OnlineHelp(self)
                self.onlinehelp.register_plugin()

            # Project explorer widget
            if CONF.get('project_explorer', 'enable'):
                self.set_splash(_("Loading project explorer..."))
                from spyderlib.plugins.projectexplorer import ProjectExplorer
                self.projectexplorer = ProjectExplorer(self)
                self.projectexplorer.register_plugin()

        # External console
        if self.light:
            # This is necessary to support the --working-directory option:
            if self.init_workdir is not None:
                os.chdir(self.init_workdir)
        else:
            self.set_splash(_("Loading external console..."))
        from spyderlib.plugins.externalconsole import ExternalConsole
        self.extconsole = ExternalConsole(self, light_mode=self.light)
        self.extconsole.register_plugin()

        # Namespace browser
        if not self.light:
            # In light mode, namespace browser is opened inside external console
            # Here, it is opened as an independent plugin, in its own dockwidget
            self.set_splash(_("Loading namespace browser..."))
            from spyderlib.plugins.variableexplorer import VariableExplorer
            self.variableexplorer = VariableExplorer(self)
            self.variableexplorer.register_plugin()

        # IPython console
        if IPYTHON_QT_INSTALLED and not self.light:
            self.set_splash(_("Loading IPython console..."))
            from spyderlib.plugins.ipythonconsole import IPythonConsole
            self.ipyconsole = IPythonConsole(self)
            self.ipyconsole.register_plugin()

        if not self.light:
            nsb = self.variableexplorer.add_shellwidget(self.console.shell)
            self.console.shell.refresh.connect(nsb.refresh_table)
            nsb.auto_refresh_button.setEnabled(False)

            self.set_splash(_("Setting up main window..."))

            # Help menu            
            dep_action = create_action(self, _("Optional dependencies..."),
                                       triggered=self.show_dependencies,
                                       icon='advanced.png')
            report_action = create_action(self,
                                          _("Report issue..."),
                                          icon=get_icon('bug.png'),
                                          triggered=self.report_issue)
            support_action = create_action(self,
                                           _("Spyder support..."),
                                           triggered=self.google_group)
            self.check_updates_action = create_action(self,
                                                  _("Check for updates..."),
                                                  triggered=self.check_updates)

            # Spyder documentation
            doc_path = get_module_data_path('spyderlib', relpath="doc",
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
                spyder_doc = osp.join(get_module_source_path('spyderlib'),
                                      os.pardir, 'build', 'lib', 'spyderlib',
                                      'doc', "index.html")
            # * If we totally fail, point to our web build
            if not osp.isfile(spyder_doc):
                spyder_doc = 'http://pythonhosted.org/spyder'
            else:
                spyder_doc = file_uri(spyder_doc)
            doc_action = create_action( self, _("Spyder documentation"), shortcut="F1", 
                                       icon=get_std_icon('DialogHelpButton'),
                                       triggered=lambda : programs.start_file(spyder_doc))

            tut_action = create_action(self, _("Spyder tutorial"),
                                       triggered=self.inspector.show_tutorial)

        #----- Tours
            self.tour = tour.AnimatedTour(self)
            self.tours_menu = QMenu(_("Spyder tours"))
            self.tour_menu_actions = []
            self.tours_available = tour.get_tours()

            for i, tour_available in enumerate(self.tours_available):
                self.tours_available[i]['last'] = 0
                tour_name = tour_available['name']

                def trigger(i=i, self=self):  # closure needed!
                    return lambda: self.show_tour(i)

                temp_action = create_action(self, tour_name, tip=_(""),
                                            triggered=trigger())
                self.tour_menu_actions += [temp_action]

            self.tours_menu.addActions(self.tour_menu_actions)

            if not DEV:
                self.tours_menu = None

            self.help_menu_actions = [doc_action, tut_action, self.tours_menu,
                                      None,
                                      report_action, dep_action,
                                      self.check_updates_action, support_action,
                                      None]
            # Python documentation
            if get_python_doc_path() is not None:
                pydoc_act = create_action(self, _("Python documentation"),
                                  triggered=lambda:
                                  programs.start_file(get_python_doc_path()))
                self.help_menu_actions.append(pydoc_act)
            # IPython documentation
            if self.ipyconsole is not None:
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
                path = file_uri(path)
                action = create_action(self, text,
                       icon='%s.png' % osp.splitext(path)[1][1:],
                       triggered=lambda path=path: programs.start_file(path))
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
            # Documentation provided by Python(x,y), if available
            try:
                from xy.config import DOC_PATH as xy_doc_path
                xydoc = osp.join(xy_doc_path, "Libraries")
                def add_xydoc(text, pathlist):
                    for path in pathlist:
                        if osp.exists(path):
                            add_ipm_action(text, path)
                            break
                add_xydoc(_("Python(x,y) documentation folder"),
                          [xy_doc_path])
                add_xydoc(_("IPython documentation"),
                          [osp.join(xydoc, "IPython", "ipythondoc.chm")])
                add_xydoc(_("guidata documentation"),
                          [osp.join(xydoc, "guidata", "guidatadoc.chm"),
                           r"D:\Python\guidata\build\doc_chm\guidatadoc.chm"])
                add_xydoc(_("guiqwt documentation"),
                          [osp.join(xydoc, "guiqwt", "guiqwtdoc.chm"),
                           r"D:\Python\guiqwt\build\doc_chm\guiqwtdoc.chm"])
                add_xydoc(_("Matplotlib documentation"),
                          [osp.join(xydoc, "matplotlib", "Matplotlibdoc.chm"),
                           osp.join(xydoc, "matplotlib", "Matplotlib.pdf")])
                add_xydoc(_("NumPy documentation"),
                          [osp.join(xydoc, "NumPy", "numpy.chm")])
                add_xydoc(_("NumPy reference guide"),
                          [osp.join(xydoc, "NumPy", "numpy-ref.pdf")])
                add_xydoc(_("NumPy user guide"),
                          [osp.join(xydoc, "NumPy", "numpy-user.pdf")])
                add_xydoc(_("SciPy documentation"),
                          [osp.join(xydoc, "SciPy", "scipy.chm"),
                           osp.join(xydoc, "SciPy", "scipy-ref.pdf")])
            except (ImportError, KeyError, RuntimeError):
                pass
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
                                    icon=get_std_icon('MessageBoxInformation'),
                                    triggered=self.about)
            self.help_menu_actions += [None, about_action]

            # Status bar widgets
            from spyderlib.widgets.status import MemoryStatus, CPUStatus
            self.mem_status = MemoryStatus(self, status)
            self.cpu_status = CPUStatus(self, status)
            self.apply_statusbar_settings()

            # Third-party plugins
            for mod in get_spyderplugins_mods(prefix='p_', extension='.py'):
                try:
                    plugin = mod.PLUGIN_CLASS(self)
                    self.thirdparty_plugins.append(plugin)
                    plugin.register_plugin()
                except AttributeError as error:
                    print("%s: %s" % (mod, str(error)), file=STDERR)


    #----- View
            # View menu
            self.plugins_menu = QMenu(_("Panes"), self)
            self.toolbars_menu = QMenu(_("Toolbars"), self)
            self.view_menu.addMenu(self.plugins_menu)
            self.view_menu.addMenu(self.toolbars_menu)
            self.quick_layout_menu = QMenu(_("Custom window layouts"), self)
            self.quick_layout_set_menu()

            if set_attached_console_visible is not None:
                cmd_act = create_action(self,
                                    _("Attached console window (debugging)"),
                                    toggled=set_attached_console_visible)
                cmd_act.setChecked(is_attached_console_visible())
                add_actions(self.view_menu, (None, cmd_act))
            add_actions(self.view_menu, (None, self.fullscreen_action,
                                         self.maximize_action,
                                         self.close_dockwidget_action, None,
                                         self.toggle_previous_layout_action,
                                         self.toggle_next_layout_action,
                                         self.quick_layout_menu))

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
        #self.remove_deprecated_shortcuts()

        # Emitting the signal notifying plugins that main window menu and
        # toolbar actions are all defined:
        self.all_actions_defined.emit()

        # Window set-up
        self.debug_print("Setting up window...")
        self.setup_layout(default=False)

        self.splash.hide()

        # Enabling tear off for all menus except help menu
        if CONF.get('main', 'tear_off_menus'):
            for child in self.menuBar().children():
                if isinstance(child, QMenu) and child != self.help_menu:
                    child.setTearOffEnabled(True)

        # Menu about to show
        for child in self.menuBar().children():
            if isinstance(child, QMenu):
                child.aboutToShow.connect(self.update_edit_menu)

        self.debug_print("*** End of MainWindow setup ***")
        self.is_starting_up = False

    def post_visible_setup(self):
        """Actions to be performed only after the main window's `show` method
        was triggered"""
        self.restore_scrollbar_position.emit()

        if self.projectexplorer is not None:
            self.projectexplorer.check_for_io_errors()

        # Remove our temporary dir
        atexit.register(self.remove_tmpdir)

        # Remove settings test directory
        if TEST is not None:
            import tempfile
            conf_dir = osp.join(tempfile.gettempdir(), SUBFOLDER)
            atexit.register(shutil.rmtree, conf_dir, ignore_errors=True)

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
            import subprocess
            idx = __file__.index(MAC_APP_NAME)
            app_path = __file__[:idx]
            subprocess.call(['open', app_path + MAC_APP_NAME])

        # Server to maintain just one Spyder instance and open files in it if
        # the user tries to start other instances with
        # $ spyder foo.py
        if CONF.get('main', 'single_instance') and not self.new_instance:
            t = threading.Thread(target=self.start_open_files_server)
            t.setDaemon(True)
            t.start()

            # Connect the window to the signal emmited by the previous server
            # when it gets a client connected to it
            self.sig_open_external_file.connect(self.open_external_file)

        # Create Plugins and toolbars submenus
        if not self.light:
            self.create_plugins_menu()
            self.create_toolbars_menu()

        # Open a Python console for light mode
        if self.light:
            self.extconsole.open_interpreter()
        self.extconsole.setMinimumHeight(0)

        if not self.light:
            # Hide Internal Console so that people don't use it instead of
            # the External or IPython ones
            if self.console.dockwidget.isVisible() and DEV is None:
                self.console.toggle_view_action.setChecked(False)
                self.console.dockwidget.hide()

            # Show the Object Inspector and Consoles by default
            plugins_to_show = [self.inspector]
            if self.ipyconsole is not None:
                if self.ipyconsole.isvisible:
                    plugins_to_show += [self.extconsole, self.ipyconsole]
                else:
                    plugins_to_show += [self.ipyconsole, self.extconsole]
            else:
                plugins_to_show += [self.extconsole]
            for plugin in plugins_to_show:
                if plugin.dockwidget.isVisible():
                    plugin.dockwidget.raise_()

            # Show history file if no console is visible
            ipy_visible = self.ipyconsole is not None and self.ipyconsole.isvisible
            if not self.extconsole.isvisible and not ipy_visible:
                self.historylog.add_history(get_conf_path('history.py'))

            # Give focus to the Editor
            if self.editor.dockwidget.isVisible():
                try:
                    self.editor.get_focus_widget().setFocus()
                except AttributeError:
                    pass

        # Check for spyder updates
        if DEV is None and CONF.get('main', 'check_updates_on_startup'):
            self.give_updates_feedback = False 
            self.check_updates()

        self.is_setting_up = False

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
        if not self.light:
            # Window layout
            if hexstate:
                self.restoreState( QByteArray().fromHex(str(hexstate)) )
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
        if not self.light:
            self.maximize_dockwidget(restore=True)# Restore non-maximized layout
            qba = self.saveState()
            CONF.set(section, prefix+'state', qbytearray_to_str(qba))
            CONF.set(section, prefix+'statusbar',
                     not self.statusBar().isHidden())

    def tabify_plugins(self, first, second):
        """Tabify plugin dockwigdets"""
        self.tabifyDockWidget(first.dockwidget, second.dockwidget)

    def setup_layout(self, default=False):
        """Setup window layout"""
        prefix = ('lightwindow' if self.light else 'window') + '/'
        settings = self.load_window_settings(prefix, default)
        hexstate = settings[0]
        
        self.first_spyder_run = False
        if hexstate is None and not self.light:
            # First Spyder execution:
            self.first_spyder_run = True
            self.setup_default_layouts('default', settings)
            self.extconsole.setMinimumHeight(250)

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
            plugin.initialize_plugin_in_mainwindow_layout()

     # for reference   
#    def setup_layout(self, default=False):
#        """Setup window layout"""
#        prefix = ('lightwindow' if self.light else 'window') + '/'
#        (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
#         is_fullscreen) = self.load_window_settings(prefix, default)
#        
#        if hexstate is None and not self.light:
#            # First Spyder execution:
#            # trying to set-up the dockwidget/toolbar positions to the best 
#            # appearance possible
#            splitting = (
#                         (self.projectexplorer, self.editor, Qt.Horizontal),
#                         (self.editor, self.outlineexplorer, Qt.Horizontal),
#                         (self.outlineexplorer, self.inspector, Qt.Horizontal),
#                         (self.inspector, self.console, Qt.Vertical),
#                         )
#            for first, second, orientation in splitting:
#                if first is not None and second is not None:
#                    self.splitDockWidget(first.dockwidget, second.dockwidget,
#                                         orientation)
#            for first, second in ((self.console, self.extconsole),
#                                  (self.extconsole, self.ipyconsole),
#                                  (self.ipyconsole, self.historylog),
#                                  (self.inspector, self.variableexplorer),
#                                  (self.variableexplorer, self.onlinehelp),
#                                  (self.onlinehelp, self.explorer),
#                                  (self.explorer, self.findinfiles),
#                                  ):
#                if first is not None and second is not None:
#                    self.tabify_plugins(first, second)
#            for plugin in [self.findinfiles, self.onlinehelp, self.console,
#                           ]+self.thirdparty_plugins:
#                if plugin is not None:
#                    plugin.dockwidget.close()
#            for plugin in (self.inspector, self.extconsole):
#                if plugin is not None:
#                    plugin.dockwidget.raise_()
#            self.extconsole.setMinimumHeight(250)
#            hidden_toolbars = [self.source_toolbar, self.edit_toolbar,
#                               self.search_toolbar]
#            for toolbar in hidden_toolbars:
#                toolbar.close()
#            for plugin in (self.projectexplorer, self.outlineexplorer):
#                plugin.dockwidget.close()
#
#        self.set_window_settings(hexstate, window_size, prefs_dialog_size, pos,
#                                 is_maximized, is_fullscreen)
#
#        for plugin in self.widgetlist:
#            plugin.initialize_plugin_in_mainwindow_layout()        
       
    def setup_default_layouts(self, index, settings):
        """Setup default layouts when run for the first time"""
        self.set_window_settings(*settings)
        self.setUpdatesEnabled(False)

        # IMPORTANT: order has to be the same as defined in the config file
        MATLAB, RSTUDIO, VERTICAL, HORIZONTAL = range(4)

        # define widgets locally
        editor = self.editor
        console_ipy = self.ipyconsole
        console_ext = self.extconsole
        console_int = self.console
        outline = self.outlineexplorer
        explorer_project = self.projectexplorer
        explorer_file = self.explorer
        explorer_variable = self.variableexplorer
        history = self.historylog
        finder = self.findinfiles
        inspector = self.inspector
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
                    [[inspector, explorer_variable, helper, explorer_file,
                      finder] + plugins,
                     [console_int, console_ext, console_ipy, history]]
                    ],
                    'width fraction': [0.0,
                                       0.55,            # column 1 width
                                       0.0,
                                       0.45],           # column 3 width
                    'height fraction': [[1.0],          # column 0, row heights
                                        [1.0],   # column 1, row heights
                                        [0.55, 0.45],          # column 2, row heights
                                        [1.0]],   # column 0, row heights
                    'hidden widgets': [outline],
                    'hidden toolbars': [],                               
                    }
        r_layout = {'widgets': [
                    # column 0
                    [[editor],
                     [console_ipy, console_ext, console_int]],
                    # column 1
                    [[explorer_variable, history, outline, finder] + plugins,
                     [explorer_file, explorer_project, inspector, helper]]
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
                     [console_ipy, console_ext, console_int]],
                    # column 2
                    [[explorer_variable, finder] + plugins,
                     [history, inspector, helper]]
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
                     [console_ipy, console_ext, console_int, explorer_file,
                      explorer_project, inspector, explorer_variable,
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
                    [[console_ipy, console_ext, console_int, explorer_file,
                      explorer_project, inspector, explorer_variable,
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

        # make every widget visible
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

        # arrange rows vertically 
        for column in widgets_layout :
            for i in range(len(column) - 1):
                first_row, second_row = column[i], column[i+1]
                if first_row is not None and second_row is not None:
                    self.splitDockWidget(first_row[0].dockwidget,
                                         second_row[0].dockwidget,
                                         Qt.Vertical)
        # tabify
        for column in widgets_layout :
            for row in column:
                for i in range(len(row) - 1):
                    first, second = row[i], row[i+1]
                    if first is not None and second is not None:
                        self.tabify_plugins(first, second)

                # raise front widget pero row
                row[0].dockwidget.show()
                row[0].dockwidget.raise_()

        # hide toolbars
        hidden_toolbars = global_hidden_toolbars + layout['hidden toolbars']
        for toolbar in hidden_toolbars:
            if toolbar is not None:
                toolbar.close()

        # hide widgets
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
#            print(c, widgets_layout[c][0][0], new_width)
        
        # fix column height
        for c, column in enumerate(widgets_layout):
            for r in range(len(column) - 1):
                widget = column[r][0].dockwidget
                min_h, max_h = widget.minimumHeight(), widget.maximumHeight()

                info = {'widget': widget,
                        'min height': min_h,
                        'max height': max_h}
                self._layout_widget_info.append(info)
                new_height = int(layout['height fraction'][c][r] * height * 0.95)
                widget.setMinimumHeight(new_height)
                widget.setMaximumHeight(new_height)

        self._custom_layout_timer = QTimer(self)
        self._custom_layout_timer.timeout.connect(self.layout_fix_timer)
        self._custom_layout_timer.setSingleShot(True)
        self._custom_layout_timer.start(100)

    def layout_fix_timer(self):
        """ """
        info = self._layout_widget_info
        for i in info:
            widget = i['widget']
            if 'min width' in i:
                widget.setMinimumWidth(i['min width'])
                widget.setMaximumWidth(i['max width'])
            if 'min height' in i:
                widget.setMinimumHeight(i['min height'])
                widget.setMaximumHeight(i['max height'])
            widget.updateGeometry()

        self.setUpdatesEnabled(True)

    def toggle_previous_layout(self):
        """ """
        self.toggle_layout('previous')

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

        self.register_shortcut(self.ql_save, "_", _("Save current layout"))
        self.register_shortcut(self.ql_preferences, "_",
                               _("Layout preferences"))

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
                                             _("Layout <b>{0}</b> will be \
                                               overwritten. Do you want to \
                                               continue?".format(name)),
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

    def plugin_focus_changed(self):
        """Focus has changed from one plugin to another"""
        if self.light:
            #  There is currently no point doing the following in light mode
            return
        self.update_edit_menu()
        self.update_search_menu()

        # Now deal with Python shell and IPython plugins
        shell = get_focus_python_shell()
        if shell is not None:
            # A Python shell widget has focus
            self.last_console_plugin_focus_was_python = True
            if self.inspector is not None:
                #  The object inspector may be disabled in .spyder.ini
                self.inspector.set_shell(shell)
            from spyderlib.widgets.externalshell import pythonshell
            if isinstance(shell, pythonshell.ExtPythonShellWidget):
                shell = shell.parent()
            self.variableexplorer.set_shellwidget_from_id(id(shell))
        elif self.ipyconsole is not None:
            focus_client = self.ipyconsole.get_focus_client()
            if focus_client is not None:
                self.last_console_plugin_focus_was_python = False
                kwid = focus_client.kernel_widget_id
                if kwid is not None:
                    idx = self.extconsole.get_shell_index_from_id(kwid)
                    if idx is not None:
                        kw = self.extconsole.shellwidgets[idx]
                        if self.inspector is not None:
                            self.inspector.set_shell(kw)
                        self.variableexplorer.set_shellwidget_from_id(kwid)
                        # Setting the kernel widget as current widget for the
                        # external console's tabwidget: this is necessary for
                        # the editor/console link to be working (otherwise,
                        # features like "Execute in current interpreter" will
                        # not work with IPython clients unless the associated
                        # IPython kernel has been selected in the external
                        # console... that's not brilliant, but it works for
                        # now: we shall take action on this later
                        self.extconsole.tabwidget.setCurrentWidget(kw)
                        focus_client.get_control().setFocus()

    def update_file_menu(self):
        """Update file menu"""
        self.load_temp_session_action.setEnabled(osp.isfile(TEMP_SESSION_PATH))

    def update_edit_menu(self):
        """Update edit menu"""
        if self.menuBar().hasFocus():
            return
        # Disabling all actions to begin with
        for child in self.edit_menu.actions():
            child.setEnabled(False)

        widget, textedit_properties = get_focus_widget_properties()
        if textedit_properties is None: # widget is not an editor/console
            return
        #!!! Below this line, widget is expected to be a QPlainTextEdit instance
        console, not_readonly, readwrite_editor = textedit_properties

        # Editor has focus and there is no file opened in it
        if not console and not_readonly and not self.editor.is_file_opened():
            return

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
        self.delete_action.setEnabled(has_selection and not_readonly)

        # Comment, uncomment, indent, unindent...
        if not console and not_readonly:
            # This is the editor and current file is writable
            for action in self.editor.edit_menu_actions:
                action.setEnabled(True)

    def update_search_menu(self):
        """Update search menu"""
        if self.menuBar().hasFocus():
            return
        # Disabling all actions to begin with
        for child in [self.find_action, self.find_next_action,
                      self.find_previous_action, self.replace_action]:
            child.setEnabled(False)

        widget, textedit_properties = get_focus_widget_properties()
        for action in self.editor.search_menu_actions:
            action.setEnabled(self.editor.isAncestorOf(widget))
        if textedit_properties is None: # widget is not an editor/console
            return
        #!!! Below this line, widget is expected to be a QPlainTextEdit instance
        _x, _y, readwrite_editor = textedit_properties
        for action in [self.find_action, self.find_next_action,
                       self.find_previous_action]:
            action.setEnabled(True)
        self.replace_action.setEnabled(readwrite_editor)
        self.replace_action.setEnabled(readwrite_editor)

    def create_plugins_menu(self):
        order = ['editor', 'console', 'ipython_console', 'variable_explorer',
                 'inspector', None, 'explorer', 'outline_explorer',
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
        if self.light:
            menu = self.createPopupMenu()
        else:
            menu = QMenu('', self)
            actions = self.help_menu_actions[:3] + \
                      [None, self.help_menu_actions[-1]]
            add_actions(menu, actions)
        return menu

    def set_splash(self, message):
        """Set splash message"""
        if message:
            self.debug_print(message)
        self.splash.show()
        self.splash.showMessage(message, Qt.AlignBottom | Qt.AlignCenter |
                                Qt.AlignAbsolute, QColor(Qt.white))
        QApplication.processEvents()

    def remove_tmpdir(self):
        """Remove Spyder temporary directory"""
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
        if not self.light:
            for plugin in self.widgetlist:
                if plugin.isAncestorOf(self.last_focused_widget):
                    plugin.visibility_changed(True)
        QMainWindow.hideEvent(self, event)

    def change_last_focused_widget(self, old, now):
        """To keep track of to the last focused widget"""
        if (now is None and QApplication.activeWindow() is not None):
            QApplication.activeWindow().setFocus()
            self.last_focused_widget = QApplication.focusWidget()
        elif now is not None:
            self.last_focused_widget = now

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
        prefix = ('lightwindow' if self.light else 'window') + '/'
        self.save_current_window_settings(prefix)
        if CONF.get('main', 'single_instance'):
            self.open_files_server.close()
        for plugin in self.thirdparty_plugins:
            if not plugin.closing_plugin(cancelable):
                return False
        for widget in self.widgetlist:
            if not widget.closing_plugin(cancelable):
                return False
        self.dialog_manager.close_all()
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

    def __update_maximize_action(self):
        if self.state_before_maximizing is None:
            text = _("Maximize current pane")
            tip = _("Maximize current pane")
            icon = "maximize.png"
        else:
            text = _("Restore current pane")
            tip = _("Restore pane to its original size")
            icon = "unmaximize.png"
        self.maximize_action.setText(text)
        self.maximize_action.setIcon(get_icon(icon))
        self.maximize_action.setToolTip(tip)

    @Slot()
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
            icon = "window_nofullscreen.png"
        else:
            icon = "window_fullscreen.png"
        self.fullscreen_action.setIcon(get_icon(icon))

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
            <p>Copyright &copy; 2009 - 2015 Pierre Raybaut
            <br>Copyright &copy; 2010 - 2015 The Spyder Development Team
            <br>Licensed under the terms of the MIT License
            <p>Created by Pierre Raybaut
            <br>Developed and maintained by the
            <a href="%s/blob/master/AUTHORS">Spyder Development Team</a>
            <br>Many thanks to all the Spyder beta-testers and regular users.
            <p>Most of the icons come from the Crystal Project
            (&copy; 2006-2007 Everaldo Coelho). Other icons by
            <a href="http://p.yusukekamiyamane.com/"> Yusuke Kamiyamane</a>
            (all rights reserved) and by
            <a href="http://www.oxygen-icons.org/">
            The Oxygen icon theme</a>.
            <p>For bug reports and feature requests, please go
            to our <a href="%s">Github website</a>. For discussions around the
            project, please go to our <a href="%s">Google Group</a>
            <p>This project is part of a larger effort to promote and
            facilitate the use of Python for scientific and engineering
            software development. The popular Python distributions
            <a href="http://continuum.io/downloads">Anaconda</a>,
            <a href="https://winpython.github.io/">WinPython</a> and
            <a href="http://code.google.com/p/pythonxy/">Python(x,y)</a>
            also contribute to this plan.
            <p>Python %s %dbits, Qt %s, %s %s on %s"""
            % (versions['spyder'], revlink, __project_url__,
               __project_url__, __forum_url__, versions['python'],
               versions['bitness'], versions['qt'], versions['qt_api'],
               versions['qt_api_ver'], versions['system']))

    @Slot()
    def show_dependencies(self):
        """Show Spyder's Optional Dependencies dialog box"""
        from spyderlib.widgets.dependencies import DependenciesDialog
        dlg = DependenciesDialog(None)
        dlg.set_data(dependencies.DEPENDENCIES)
        dlg.show()
        dlg.exec_()

    @Slot()
    def report_issue(self):
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

* *What steps will reproduce the problem?*
1.
2.
3.

* *What is the expected output? What do you see instead?*


* *Please provide any additional information below*


## Version and main components

* Spyder Version:  %s %s
* Python Version:  %s
* Qt Version    :  %s, %s %s on %s

## Optional dependencies

%s
""" % (versions['spyder'],
       revision,
       versions['python'],
       versions['qt'],
       versions['qt_api'],
       versions['qt_api_ver'],
       versions['system'],
       dependencies.status())

        url = QUrl("https://github.com/spyder-ide/spyder/issues/new")
        url.addEncodedQueryItem("body", quote(issue_template))
        QDesktopServices.openUrl(url)

    @Slot()
    def google_group(self):
        url = QUrl("http://groups.google.com/group/spyderlib")
        QDesktopServices.openUrl(url)

    #---- Global callbacks (called from plugins)
    def get_current_editor_plugin(self):
        """Return editor plugin which has focus:
        console, extconsole, editor, inspector or historylog"""
        if self.light:
            return self.extconsole
        widget = QApplication.focusWidget()
        from spyderlib.widgets.editor import TextEditBaseWidget
        from spyderlib.widgets.shell import ShellBaseWidget
        if not isinstance(widget, (TextEditBaseWidget, ShellBaseWidget)):
            return
        for plugin in self.widgetlist:
            if plugin.isAncestorOf(widget):
                return plugin
        else:
            # External Editor window
            plugin = widget
            from spyderlib.widgets.editor import EditorWidget
            while not isinstance(plugin, EditorWidget):
                plugin = plugin.parent()
            return plugin

    @Slot()
    def find(self):
        """Global find callback"""
        plugin = self.get_current_editor_plugin()
        if plugin is not None:
            plugin.find_widget.show()
            plugin.find_widget.search_text.setFocus()
            return plugin

    @Slot()
    def find_next(self):
        """Global find next callback"""
        plugin = self.get_current_editor_plugin()
        if plugin is not None:
            plugin.find_widget.find_next()

    @Slot()
    def find_previous(self):
        """Global find previous callback"""
        plugin = self.get_current_editor_plugin()
        if plugin is not None:
            plugin.find_widget.find_previous()

    @Slot()
    def replace(self):
        """Global replace callback"""
        plugin = self.find()
        if plugin is not None:
            plugin.find_widget.show_replace()

    @Slot()
    def global_callback(self):
        """Global callback"""
        widget = QApplication.focusWidget()
        action = self.sender()
        callback = from_qvariant(action.data(), to_text_string)
        from spyderlib.widgets.editor import TextEditBaseWidget
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
        else:
            self.extconsole.visibility_changed(True)
            self.extconsole.raise_()
            self.extconsole.start(
                fname=to_text_string(fname), wdir=to_text_string(wdir),
                args=to_text_string(args), interact=interact,
                debug=debug, python=python, post_mortem=post_mortem,
                python_args=to_text_string(python_args) )

    def execute_in_external_console(self, lines, focus_to_editor):
        """Execute lines in external or IPython console
        and eventually set focus to editor"""
        console = self.extconsole
        if self.ipyconsole is None\
           or self.last_console_plugin_focus_was_python:
            console = self.extconsole
        else:
            console = self.ipyconsole
        console.visibility_changed(True)
        console.raise_()
        console.execute_python_code(lines)
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
        if ext in EDIT_EXT:
            self.editor.load(fname)
        elif self.variableexplorer is not None and ext in IMPORT_EXT:
            self.variableexplorer.import_data(fname)
        elif encoding.is_text_file(fname):
            self.editor.load(fname)
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

    #---- PYTHONPATH management, etc.
    def get_spyder_pythonpath(self):
        """Return Spyder PYTHONPATH"""
        return self.path+self.project_path

    def add_path_to_sys_path(self):
        """Add Spyder path to sys.path"""
        for path in reversed(self.get_spyder_pythonpath()):
            sys.path.insert(1, path)

    def remove_path_from_sys_path(self):
        """Remove Spyder path from sys.path"""
        sys_path = sys.path
        while sys_path[1] in self.get_spyder_pythonpath():
            sys_path.pop(1)

    @Slot()
    def path_manager_callback(self):
        """Spyder path manager"""
        from spyderlib.widgets.pathmanager import PathManager
        self.remove_path_from_sys_path()
        project_pathlist = self.projectexplorer.get_pythonpath()
        dialog = PathManager(self, self.path, project_pathlist, sync=True)
        dialog.redirect_stdio.connect(self.redirect_internalshell_stdio)
        dialog.exec_()
        self.add_path_to_sys_path()
        encoding.writelines(self.path, self.SPYDER_PATH) # Saving path
        self.sig_pythonpath_changed.emit()

    def pythonpath_changed(self):
        """Project Explorer PYTHONPATH contribution has changed"""
        self.remove_path_from_sys_path()
        self.project_path = self.projectexplorer.get_pythonpath()
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
        qapp.setStyle(CONF.get('main', 'windows_style', self.default_style))

        default = self.DOCKOPTIONS
        if CONF.get('main', 'vertical_tabs'):
            default = default|QMainWindow.VerticalTabs
        if CONF.get('main', 'animated_docks'):
            default = default|QMainWindow.AnimatedDocks
        self.setDockOptions(default)

        for child in self.widgetlist:
            features = child.FEATURES
            if CONF.get('main', 'vertical_dockwidget_titlebars'):
                features = features|QDockWidget.DockWidgetVerticalTitleBar
            child.dockwidget.setFeatures(features)
            child.update_margins()

        self.apply_statusbar_settings()

    def apply_statusbar_settings(self):
        """Update status bar widgets settings"""
        for widget, name in ((self.mem_status, 'memory_usage'),
                             (self.cpu_status, 'cpu_usage')):
            if widget is not None:
                widget.setVisible(CONF.get('main', '%s/enable' % name))
                widget.set_interval(CONF.get('main', '%s/timeout' % name))

    @Slot()
    def edit_preferences(self):
        """Edit Spyder preferences"""
        from spyderlib.plugins.configdialog import ConfigDialog
        dlg = ConfigDialog(self)
        dlg.size_change.connect(self.set_prefs_size)
        if self.prefs_dialog_size is not None:
            dlg.resize(self.prefs_dialog_size)
        for PrefPageClass in self.general_prefs:
            widget = PrefPageClass(dlg, main=self)
            widget.initialize()
            dlg.add_page(widget)
        for plugin in [self.workingdirectory, self.editor,
                       self.projectexplorer, self.extconsole, self.ipyconsole,
                       self.historylog, self.inspector, self.variableexplorer,
                       self.onlinehelp, self.explorer, self.findinfiles
                       ]+self.thirdparty_plugins:
            if plugin is not None:
                widget = plugin.create_configwidget(dlg)
                if widget is not None:
                    dlg.add_page(widget)
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
                          default=NoDefault):
        """
        Register QAction or QShortcut to Spyder main application,
        with shortcut (context, name, default)
        """
        self.shortcut_data.append( (qaction_or_qshortcut,
                                    context, name, default) )
        self.apply_shortcuts()

    def remove_deprecated_shortcuts(self):
        """Remove deprecated shortcuts"""
        data = [(context, name) for (qobject, context, name,
                default) in self.shortcut_data]
        remove_deprecated_shortcuts(data)

    def apply_shortcuts(self):
        """Apply shortcuts settings to all widgets/plugins"""
        toberemoved = []
        for index, (qobject, context, name,
                    default) in enumerate(self.shortcut_data):
            keyseq = QKeySequence( get_shortcut(context, name, default) )
            try:
                if isinstance(qobject, QAction):
                    qobject.setShortcut(keyseq)
                elif isinstance(qobject, QShortcut):
                    qobject.setKey(keyseq)
            except RuntimeError:
                # Object has been deleted
                toberemoved.append(index)
        for index in sorted(toberemoved, reverse=True):
            self.shortcut_data.pop(index)

    #---- Sessions
    @Slot()
    def load_session(self, filename=None):
        """Load session"""
        if filename is None:
            self.redirect_internalshell_stdio(False)
            filename, _selfilter = getopenfilename(self, _("Open session"),
                        getcwd(), _("Spyder sessions")+" (*.session.tar)")
            self.redirect_internalshell_stdio(True)
            if not filename:
                return
        if self.close():
            self.next_session_name = filename

    @Slot()
    def save_session(self):
        """Save session and quit application"""
        self.redirect_internalshell_stdio(False)
        filename, _selfilter = getsavefilename(self, _("Save session"),
                        getcwd(), _("Spyder sessions")+" (*.session.tar)")
        self.redirect_internalshell_stdio(True)
        if filename:
            if self.close():
                self.save_session_name = filename

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
            if not self.light:
                fname = fname.decode('utf-8')
                self.sig_open_external_file.emit(fname)
            req.sendall(b' ')

    # ---- Quit and restart
    def restart(self):
        """Quit and Restart Spyder application"""
        # Get start path to use in restart script
        spyder_start_directory  = get_module_path('spyderlib')
        restart_script = osp.join(spyder_start_directory, 'restart_app.py')

        # Get any initial argument passed when spyder was started
        # Note: Variables defined in bootstrap.py and spyderlib\start_app.py
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
            print(error)
            print(command)

    # ---- Interactive Tours
    def show_tour(self, index):
        """ """
        frames = self.tours_available[index]
        self.tour.set_tour(index, frames, self)
        self.tour.start_tour()

    # ---- Check for Spyder Updates
    def _check_updates_ready(self):
        """Called by WorkerUpdates when ready"""
        from spyderlib.workers.updates import MessageCheckBox

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
        box = MessageCheckBox()
        box.setWindowTitle(_("Spyder updates"))
        box.set_checkbox_text(_("Check for updates on startup"))
        box.setStandardButtons(QMessageBox.Ok)
        box.setDefaultButton(QMessageBox.Ok)
        box.setIcon(QMessageBox.Information)

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
                msg = _("<b>Spyder {0} is available!</b> <br><br>Please use "
                        "your package manager to update Spyder or go to our "
                        "<a href=\"{1}\">Releases</a> page to download this "
                        "new version. <br><br>If you are not sure how to "
                        "proceed to update Spyder please refer to our "
                        " <a href=\"{2}\">Installation</a> instructions."
                        "" .format(latest_release, url_r, url_i))
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

    def check_updates(self):
        """
        Check for spyder updates on github releases using a QThread.
        """
        from spyderlib.workers.updates import WorkerUpdates

        # Disable check_updates_action while the thread is working
        self.check_updates_action.setDisabled(True)

        if self.thread_updates is not None:
            self.thread_updates.terminate()

        self.thread_updates = QThread(self)
        self.worker_updates = WorkerUpdates(self)
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

    #----Monkey patching PyQt4.QtGui.QApplication
    class FakeQApplication(QApplication):
        """Spyder's fake QApplication"""
        def __init__(self, args):
            self = app  # analysis:ignore
        @staticmethod
        def exec_():
            """Do nothing because the Qt mainloop is already running"""
            pass
    from spyderlib.qt import QtGui
    QtGui.QApplication = FakeQApplication

    #----Monkey patching rope
    try:
        from spyderlib import rope_patch
        rope_patch.apply()
    except ImportError:
        # rope 0.9.2/0.9.3 is not installed
        pass

    #----Monkey patching sys.exit
    def fake_sys_exit(arg=[]):
        pass
    sys.exit = fake_sys_exit

    # Removing arguments from sys.argv as in standard Python interpreter
    sys.argv = ['']

    # Selecting Qt4 backend for Enthought Tool Suite (if installed)
    try:
        from enthought.etsconfig.api import ETSConfig
        ETSConfig.toolkit = 'qt4'
    except ImportError:
        pass

    #----Monkey patching rope (if installed)
    #       Compatibility with new Mercurial API (>= 1.3).
    #       New versions of rope (> 0.9.2) already handle this issue
    try:
        import rope
        if rope.VERSION == '0.9.2':
            import rope.base.fscommands

            class MercurialCommands(rope.base.fscommands.MercurialCommands):
                def __init__(self, root):
                    self.hg = self._import_mercurial()
                    self.normal_actions = rope.base.fscommands.FileSystemCommands()
                    try:
                        self.ui = self.hg.ui.ui(
                            verbose=False, debug=False, quiet=True,
                            interactive=False, traceback=False,
                            report_untrusted=False)
                    except:
                        self.ui = self.hg.ui.ui()
                        self.ui.setconfig('ui', 'interactive', 'no')
                        self.ui.setconfig('ui', 'debug', 'no')
                        self.ui.setconfig('ui', 'traceback', 'no')
                        self.ui.setconfig('ui', 'verbose', 'no')
                        self.ui.setconfig('ui', 'report_untrusted', 'no')
                        self.ui.setconfig('ui', 'quiet', 'yes')
                    self.repo = self.hg.hg.repository(self.ui, root)

            rope.base.fscommands.MercurialCommands = MercurialCommands
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

    app.exec_()
    return main


def __remove_temp_session():
    if osp.isfile(TEMP_SESSION_PATH):
        os.remove(TEMP_SESSION_PATH)


#==============================================================================
# Main
#==============================================================================
def main():
    """Session manager"""
    __remove_temp_session()

    # **** Collect command line options ****
    # Note regarding Options:
    # It's important to collect options before monkey patching sys.exit,
    # otherwise, optparse won't be able to exit if --help option is passed
    options, args = get_options()

    if set_attached_console_visible is not None:
        set_attached_console_visible(DEBUG or options.show_console\
                                     or options.reset_session\
                                     or options.reset_to_defaults\
                                     or options.optimize)

    app = initialize()
    if options.reset_session:
        # <!> Remove all configuration files!
        reset_session()
#        CONF.reset_to_defaults(save=True)
        return
    elif options.reset_to_defaults:
        # Reset Spyder settings to defaults
        CONF.reset_to_defaults(save=True)
        return
    elif options.optimize:
        # Optimize the whole Spyder's source code directory
        import spyderlib
        programs.run_python_script(module="compileall",
                                   args=[spyderlib.__path__[0]], p_args=['-O'])
        return

    if CONF.get('main', 'crash', False):
        CONF.set('main', 'crash', False)
        SPLASH.hide()
        QMessageBox.information(None, "Spyder",
            "Spyder crashed during last session.<br><br>"
            "If Spyder does not start at all and <u>before submitting a "
            "bug report</u>, please try to reset settings to defaults by "
            "running Spyder with the command line option '--reset':<br>"
            "<span style=\'color: #555555\'><b>python spyder --reset"
            "</b></span><br><br>"
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

    next_session_name = options.startup_session
    while is_text_string(next_session_name):
        if next_session_name:
            error_message = load_session(next_session_name)
            if next_session_name == TEMP_SESSION_PATH:
                __remove_temp_session()
            if error_message is None:
                CONF.load_from_ini()
            else:
                print(error_message)
                QMessageBox.critical(None, "Load session",
                    u("<b>Unable to load '%s'</b><br><br>Error message:<br>%s")
                    % (osp.basename(next_session_name), error_message))
        mainwindow = None
        try:
            mainwindow = run_spyder(app, options, args)
        except BaseException:
            CONF.set('main', 'crash', True)
            import traceback
            traceback.print_exc(file=STDERR)
            traceback.print_exc(file=open('spyder_crash.log', 'w'))
        if mainwindow is None:
            # An exception occured
            SPLASH.hide()
            return
        next_session_name = mainwindow.next_session_name
        save_session_name = mainwindow.save_session_name
        if next_session_name is not None:
            #-- Loading session
            # Saving current session in a temporary file
            # but only if we are not currently trying to reopen it!
            if next_session_name != TEMP_SESSION_PATH:
                save_session_name = TEMP_SESSION_PATH
        if save_session_name:
            #-- Saving session
            error_message = save_session(save_session_name)
            if error_message is not None:
                QMessageBox.critical(None, "Save session",
                    u("<b>Unable to save '%s'</b><br><br>Error message:<br>%s")
                    % (osp.basename(save_session_name), error_message))
    ORIGINAL_SYS_EXIT()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
#
# Copyright © 2009-2013 Pierre Raybaut
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
# Windows platforms only: support for hiding the attached console window
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
# Don't show IPython ShimWarning's to our users
# TODO: Move to Jupyter imports in 3.1
#==============================================================================
try:
    import warnings
    from IPython.utils.shimmodule import ShimWarning
    warnings.simplefilter('ignore', ShimWarning)
except:
    pass


#==============================================================================
# Qt imports
#==============================================================================
from spyderlib.qt.QtGui import (QApplication, QMainWindow, QSplashScreen,
                                QPixmap, QMessageBox, QMenu, QColor, QShortcut,
                                QKeySequence, QDockWidget, QAction,
                                QDesktopServices, QStyleFactory)
from spyderlib.qt.QtCore import (SIGNAL, QPoint, Qt, QSize, QByteArray, QUrl,
                                 QCoreApplication)
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
from spyderlib.baseconfig import _, get_image_path
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
                                  running_in_mac_app)
from spyderlib.config import (CONF, EDIT_EXT, IMPORT_EXT, OPEN_FILES_PORT,
                              is_gtk_desktop)
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
        
        self.debug_print("Start of MainWindow constructor")

        # Use a custom Qt stylesheet
        if sys.platform == 'darwin':
            spy_path = get_module_source_path('spyderlib')
            mac_style = open(osp.join(spy_path, 'mac_stylesheet.qss')).read()
            self.setStyleSheet(mac_style)

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
        
        # Preferences
        from spyderlib.plugins.configdialog import (MainConfigPage,
                                                    ColorSchemeConfigPage)
        from spyderlib.plugins.shortcuts import ShortcutsConfigPage
        from spyderlib.plugins.runconfig import RunConfigPage
        self.general_prefs = [MainConfigPage, ShortcutsConfigPage,
                              ColorSchemeConfigPage, RunConfigPage]
        self.prefs_index = None
        self.prefs_dialog_size = None
        
        # Actions
        self.close_dockwidget_action = None
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
        
        self.floating_dockwidgets = []
        self.window_size = None
        self.window_position = None
        self.state_before_maximizing = None
        self.current_quick_layout = None
        self.previous_layout_settings = None
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
            self.connect(self.file_menu, SIGNAL("aboutToShow()"),
                         self.update_file_menu)
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
                                        triggered=module_completion.reset,
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
            if is_module_installed('guidata'):
                from guidata import configtools
                from guidata import config  # (loading icons) analysis:ignore
                guidata_icon = configtools.get_icon('guidata.svg')
                guidata_act = create_python_script_action(self,
                               _("guidata examples"), guidata_icon, "guidata",
                               osp.join("tests", "__init__"))
                if guidata_act:
                    gdgq_act += [guidata_act]
                if is_module_installed('guiqwt'):
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
            self.workingdirectory = WorkingDirectory(self, self.init_workdir)
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
            self.file_menu_actions += [self.load_temp_session_action,
                                       self.load_session_action,
                                       self.save_session_action,
                                       None, quit_action]
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
            self.connect(self.console.shell, SIGNAL('refresh()'),
                         nsb.refresh_table)
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
            doc_action = create_bookmark_action(self, spyder_doc,
                               _("Spyder documentation"), shortcut="F1",
                               icon=get_std_icon('DialogHelpButton'))
            tut_action = create_action(self, _("Spyder tutorial"),
                                       triggered=self.inspector.show_tutorial)
            self.help_menu_actions = [doc_action, tut_action, None,
                                      report_action, dep_action, support_action,
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
            qta_exe = "assistant-qt4" if sys.platform.startswith('linux') else \
                      "assistant"
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
                                
            # View menu
            self.plugins_menu = QMenu(_("Panes"), self)
            self.toolbars_menu = QMenu(_("Toolbars"), self)
            self.view_menu.addMenu(self.plugins_menu)
            self.view_menu.addMenu(self.toolbars_menu)
            reset_layout_action = create_action(self, _("Reset window layout"),
                                            triggered=self.reset_window_layout)
            quick_layout_menu = QMenu(_("Custom window layouts"), self)
            ql_actions = []
            for index in range(1, 4):
                if index > 0:
                    ql_actions += [None]
                qli_act = create_action(self,
                                        _("Switch to/from layout %d") % index,
                                        triggered=lambda i=index:
                                        self.quick_layout_switch(i))
                self.register_shortcut(qli_act, "_",
                                       "Switch to/from layout %d" % index)
                qlsi_act = create_action(self, _("Set layout %d") % index,
                                         triggered=lambda i=index:
                                         self.quick_layout_set(i))
                self.register_shortcut(qlsi_act, "_", "Set layout %d" % index)
                ql_actions += [qli_act, qlsi_act]
            add_actions(quick_layout_menu, ql_actions)
            if set_attached_console_visible is not None:
                cmd_act = create_action(self,
                                    _("Attached console window (debugging)"),
                                    toggled=set_attached_console_visible)
                cmd_act.setChecked(is_attached_console_visible())
                add_actions(self.view_menu, (None, cmd_act))
            add_actions(self.view_menu, (None, self.fullscreen_action,
                                         self.maximize_action,
                                         self.close_dockwidget_action, None,
                                         reset_layout_action,
                                         quick_layout_menu))
            
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
        self.emit(SIGNAL('all_actions_defined()'))
        
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
                self.connect(child, SIGNAL("aboutToShow()"),
                             self.update_edit_menu)

        self.debug_print("*** End of MainWindow setup ***")
        self.is_starting_up = False
        
    def post_visible_setup(self):
        """Actions to be performed only after the main window's `show` method 
        was triggered"""
        self.emit(SIGNAL('restore_scrollbar_position()'))
        
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
            self.connect(self, SIGNAL('open_external_file(QString)'),
                         lambda fname: self.open_external_file(fname))
        
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
        (hexstate, window_size, prefs_dialog_size, pos, is_maximized,
         is_fullscreen) = self.load_window_settings(prefix, default)
        
        if hexstate is None and not self.light:
            # First Spyder execution:
            # trying to set-up the dockwidget/toolbar positions to the best 
            # appearance possible
            splitting = (
                         (self.projectexplorer, self.editor, Qt.Horizontal),
                         (self.editor, self.outlineexplorer, Qt.Horizontal),
                         (self.outlineexplorer, self.inspector, Qt.Horizontal),
                         (self.inspector, self.console, Qt.Vertical),
                         )
            for first, second, orientation in splitting:
                if first is not None and second is not None:
                    self.splitDockWidget(first.dockwidget, second.dockwidget,
                                         orientation)
            for first, second in ((self.console, self.extconsole),
                                  (self.extconsole, self.ipyconsole),
                                  (self.ipyconsole, self.historylog),
                                  (self.inspector, self.variableexplorer),
                                  (self.variableexplorer, self.onlinehelp),
                                  (self.onlinehelp, self.explorer),
                                  (self.explorer, self.findinfiles),
                                  ):
                if first is not None and second is not None:
                    self.tabify_plugins(first, second)
            for plugin in [self.findinfiles, self.onlinehelp, self.console,
                           ]+self.thirdparty_plugins:
                if plugin is not None:
                    plugin.dockwidget.close()
            for plugin in (self.inspector, self.extconsole):
                if plugin is not None:
                    plugin.dockwidget.raise_()
            self.extconsole.setMinimumHeight(250)
            hidden_toolbars = [self.source_toolbar, self.edit_toolbar,
                               self.search_toolbar]
            for toolbar in hidden_toolbars:
                toolbar.close()
            for plugin in (self.projectexplorer, self.outlineexplorer):
                plugin.dockwidget.close()

        self.set_window_settings(hexstate, window_size, prefs_dialog_size, pos,
                                 is_maximized, is_fullscreen)

        for plugin in self.widgetlist:
            plugin.initialize_plugin_in_mainwindow_layout()

    def reset_window_layout(self):
        """Reset window layout to default"""
        answer = QMessageBox.warning(self, _("Warning"),
                     _("Window layout will be reset to default settings: "
                       "this affects window position, size and dockwidgets.\n"
                       "Do you want to continue?"),
                     QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.setup_layout(default=True)
            
    def quick_layout_switch(self, index):
        """Switch to quick layout number *index*"""
        if self.current_quick_layout == index:
            self.set_window_settings(*self.previous_layout_settings)
            self.current_quick_layout = None
        else:
            try:
                settings = self.load_window_settings('layout_%d/' % index,
                                                     section='quick_layouts')
            except cp.NoOptionError:
                QMessageBox.critical(self, _("Warning"),
                                     _("Quick switch layout #%d has not yet "
                                       "been defined.") % index)
                return
            self.previous_layout_settings = self.get_window_settings()
            self.set_window_settings(*settings)
            self.current_quick_layout = index
    
    def quick_layout_set(self, index):
        """Save current window settings as quick layout number *index*"""
        self.save_current_window_settings('layout_%d/' % index,
                                          section='quick_layouts')

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
        
    def moveEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.fullscreen_flag:
            self.window_position = self.pos()
        QMainWindow.moveEvent(self, event)
    
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
        prefix = ('lightwindow' if self.light else 'window') + '/'
        self.save_current_window_settings(prefix)
        if CONF.get('main', 'single_instance'):
            self.open_files_server.close()
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

    def show_dependencies(self):
        """Show Spyder's Optional Dependencies dialog box"""
        from spyderlib.widgets.dependencies import DependenciesDialog
        dlg = DependenciesDialog(None)
        dlg.set_data(dependencies.DEPENDENCIES)
        dlg.show()
        dlg.exec_()

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

**What steps will reproduce the problem?**

1. 
2. 
3. 

**What is the expected output? What do you see instead?**


**Please provide any additional information below**


## Version and main components

* Spyder Version: %s %s
* Python Version: %s
* Qt Versions:  %s, %s %s on %s

## Optional dependencies
```
%s
```
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
    
    def find(self):
        """Global find callback"""
        plugin = self.get_current_editor_plugin()
        if plugin is not None:
            plugin.find_widget.show()
            plugin.find_widget.search_text.setFocus()
            return plugin
    
    def find_next(self):
        """Global find next callback"""
        plugin = self.get_current_editor_plugin()
        if plugin is not None:
            plugin.find_widget.find_next()
            
    def find_previous(self):
        """Global find previous callback"""
        plugin = self.get_current_editor_plugin()
        if plugin is not None:
            plugin.find_widget.find_previous()
        
    def replace(self):
        """Global replace callback"""
        plugin = self.find()
        if plugin is not None:
            plugin.find_widget.show_replace()

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
                              python_args, systerm):
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
                debug=debug, python=python,
                python_args=to_text_string(python_args) )

    def execute_in_external_console(self, lines, focus_to_editor):
        """
        Execute lines in external or IPython console and eventually set focus
        to the editor
        """
        console = self.extconsole
        if self.ipyconsole is None or self.last_console_plugin_focus_was_python:
            console = self.extconsole
        else:
            console = self.ipyconsole
        console.visibility_changed(True)
        console.raise_()
        console.execute_python_code(lines)
        if focus_to_editor:
            self.editor.visibility_changed(True)

    def new_file(self, text):
        self.editor.new(text=text)
        
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
        
    def path_manager_callback(self):
        """Spyder path manager"""
        from spyderlib.widgets.pathmanager import PathManager
        self.remove_path_from_sys_path()
        project_pathlist = self.projectexplorer.get_pythonpath()
        dialog = PathManager(self, self.path, project_pathlist, sync=True)
        self.connect(dialog, SIGNAL('redirect_stdio(bool)'),
                     self.redirect_internalshell_stdio)
        dialog.exec_()
        self.add_path_to_sys_path()
        encoding.writelines(self.path, self.SPYDER_PATH) # Saving path
        self.emit(SIGNAL("pythonpath_changed()"))
        
    def pythonpath_changed(self):
        """Project Explorer PYTHONPATH contribution has changed"""
        self.remove_path_from_sys_path()
        self.project_path = self.projectexplorer.get_pythonpath()
        self.add_path_to_sys_path()
        self.emit(SIGNAL("pythonpath_changed()"))
    
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
            qapp.setStyle(CONF.get('main', 'windows_style',
                                   self.default_style))
        
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
        
    def edit_preferences(self):
        """Edit Spyder preferences"""
        from spyderlib.plugins.configdialog import ConfigDialog
        dlg = ConfigDialog(self)
        self.connect(dlg, SIGNAL("size_change(QSize)"),
                     lambda s: self.set_prefs_size(s))
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
        self.connect(dlg.pages_widget, SIGNAL("currentChanged(int)"),
                     self.__preference_page_changed)
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
                raise
            fname = req.recv(1024)
            if not self.light:
                fname = fname.decode('utf-8')
                self.emit(SIGNAL('open_external_file(QString)'), fname)
            req.sendall(b' ')


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
        main.connect(app, SIGNAL('open_external_file(QString)'),
                     lambda fname: main.open_external_file(fname))
    
    # To give focus again to the last focused widget after restoring
    # the window
    main.connect(app, SIGNAL('focusChanged(QWidget*, QWidget*)'),
                 main.change_last_focused_widget)

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

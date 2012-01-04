# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder, the Scientific PYthon Development EnviRonment
=====================================================

Developped and maintained by Pierre Raybaut

Copyright © 2009-2011 Pierre Raybaut
Licensed under the terms of the MIT License
(see spyderlib/__init__.py for details)
"""

import os
try:
    # Test if IPython v0.11+ is installed
    from IPython import deathrow #analysis:ignore
    if os.environ.get('QT_API', 'pyqt') == 'pyqt':
        # If PyQt is the selected GUI toolkit (at this stage, only the
        # bootstrap script has eventually set this option),
        # switch to PyQt API #2 by simply importing the IPython qt module
        os.environ['QT_API'] = 'pyqt'
        from IPython.external import qt #analysis:ignore
except ImportError:
    pass
from spyderlib import qt #analysis:ignore

# Check requirements
from spyderlib import requirements
requirements.check_path()
requirements.check_qt()

import sys
import os.path as osp
import platform
import re

# Keeping a reference to the original sys.exit before patching it
ORIGINAL_SYS_EXIT = sys.exit

# Windows platforms only: support for hiding the attached console window
set_attached_console_visible = None
is_attached_console_visible = None
if os.name == 'nt':
    try:
        import win32gui, win32console, win32con
        win32console.GetConsoleWindow() # do nothing, this is just a test
        def set_attached_console_visible(state):
            """Show/hide console window attached to current window
            
            This is for Windows platforms only. Requires pywin32 library."""
            win32gui.ShowWindow(win32console.GetConsoleWindow(),
                                win32con.SW_SHOW if state else win32con.SW_HIDE)
        def is_attached_console_visible():
            """Return True if attached console window is visible"""
            return win32gui.IsWindowVisible(win32console.GetConsoleWindow())
    except (ImportError, NotImplementedError):
        # This is not a Windows platform (ImportError)
        # or pywin32 is not installed (ImportError)
        # or GetConsoleWindow is not implemented on current platform
        pass

# Workaround: importing rope.base.project here, otherwise this module can't
# be imported if Spyder was executed from another folder than spyderlib
try:
    import rope.base.project #@UnusedImport
except ImportError:
    pass

from spyderlib.qt.QtGui import (QApplication, QMainWindow, QSplashScreen,
                                QPixmap, QMessageBox, QMenu, QColor, QShortcut,
                                QKeySequence, QDockWidget, QAction, QLineEdit,
                                QInputDialog, QDesktopServices)
from spyderlib.qt.QtCore import SIGNAL, QPoint, Qt, QSize, QByteArray, QUrl
from spyderlib.qt.compat import (from_qvariant, getopenfilename,
                                 getsavefilename)

# Local imports
from spyderlib import __version__, __project_url__, __forum_url__
from spyderlib.utils import encoding
try:
    from spyderlib.utils.environ import WinUserEnvDialog
except ImportError:
    WinUserEnvDialog = None
from spyderlib.widgets.pathmanager import PathManager
from spyderlib.plugins.configdialog import (ConfigDialog, MainConfigPage,
                                            ColorSchemeConfigPage)
from spyderlib.plugins.shortcuts import ShortcutsConfigPage
from spyderlib.plugins.console import Console
from spyderlib.plugins.workingdirectory import WorkingDirectory
from spyderlib.plugins.editor import Editor
from spyderlib.plugins.history import HistoryLog
from spyderlib.plugins.inspector import ObjectInspector
try:
    # Assuming Qt >= v4.4
    from spyderlib.plugins.onlinehelp import OnlineHelp
except ImportError:
    # Qt < v4.4
    OnlineHelp = None
from spyderlib.plugins.explorer import Explorer
from spyderlib.plugins.externalconsole import ExternalConsole
from spyderlib.plugins.variableexplorer import VariableExplorer
from spyderlib.plugins.findinfiles import FindInFiles
from spyderlib.plugins.projectexplorer import ProjectExplorer
from spyderlib.plugins.outlineexplorer import OutlineExplorer
from spyderlib.utils.qthelpers import (create_action, add_actions, get_std_icon,
                                       create_module_bookmark_actions,
                                       create_bookmark_action,
                                       create_program_action, DialogManager,
                                       keybinding, qapplication,
                                       create_python_script_action, file_uri)
from spyderlib.baseconfig import (get_conf_path, _, get_module_data_path,
                                  get_module_source_path, STDOUT, STDERR)
from spyderlib.config import (get_icon, get_image_path, CONF, get_shortcut,
                              EDIT_EXT, IMPORT_EXT)
from spyderlib.otherplugins import get_spyderplugins_mods
from spyderlib.utils.programs import (run_python_script, is_module_installed,
                                      start_file, run_python_script_in_terminal)
from spyderlib.utils.iofuncs import load_session, save_session, reset_session
from spyderlib.userconfig import NoDefault, NoOptionError
from spyderlib.utils.module_completion import getRootModules, MODULES_PATH


TEMP_SESSION_PATH = get_conf_path('.temp.session.tar')


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

class MainWindow(QMainWindow):
    """Spyder main window"""
    DOCKOPTIONS = QMainWindow.AllowTabbedDocks|QMainWindow.AllowNestedDocks
    spyder_path = get_conf_path('.path')
    BOOKMARKS = (
         ('PyQt4',
          "http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/pyqt4ref.html",
          _("PyQt4 Reference Guide"), "qt.png"),
         ('PyQt4',
          "http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/classes.html",
          _("PyQt4 API Reference"), "qt.png"),
         ('xy', "http://www.pythonxy.com",
          _("Python(x,y)"), "pythonxy.png"),
         ('numpy', "http://docs.scipy.org/doc/",
          _("Numpy and Scipy documentation"),
          "scipy.png"),
         ('matplotlib', "http://matplotlib.sourceforge.net/contents.html",
          _("Matplotlib documentation"),
          "matplotlib.png"),
                )
    
    def __init__(self, options=None):
        QMainWindow.__init__(self)
        
        qapp = QApplication.instance()
        self.default_style = str(qapp.style().objectName())
        
        self.dialog_manager = DialogManager()
        
        self.init_workdir = options.working_directory
        self.debug = options.debug
        self.profile = options.profile
        self.multithreaded = options.multithreaded
        self.light = options.light
        
        self.debug_print("Start of MainWindow constructor")
        
#        self.setStyleSheet(STYLESHEET)

        # Shortcut management data
        self.shortcut_data = []
        
        # Loading Spyder path
        self.path = []
        self.project_path = []
        if osp.isfile(self.spyder_path):
            self.path, _x = encoding.readlines(self.spyder_path)
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
        self.ipython_frontends = []
        self.variableexplorer = None
        self.findinfiles = None
        self.thirdparty_plugins = []
        
        # Preferences
        self.general_prefs = [MainConfigPage, ShortcutsConfigPage,
                              ColorSchemeConfigPage]
        self.prefs_index = None
        
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
        self.interact_menu = None
        self.interact_menu_actions = []
        self.tools_menu = None
        self.tools_menu_actions = []
        self.external_tools_menu = None # We must keep a reference to this,
        # otherwise the external tools menu is lost after leaving setup method
        self.external_tools_menu_actions = []
        self.view_menu = None
        self.windows_toolbars_menu = None
        self.help_menu = None
        self.help_menu_actions = []
        
        # Toolbars
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
        
        # Set Window title and icon
        title = "Spyder"
        if self.debug:
            title += " (DEBUG MODE)"
        self.setWindowTitle(title)
        icon_name = 'spyder_light.svg' if self.light else 'spyder.svg'
        self.setWindowIcon(get_icon(icon_name))
        
        # Showing splash screen
        pixmap = QPixmap(get_image_path('splash.png'), 'png')
        self.splash = QSplashScreen(pixmap)
        font = self.splash.font()
        font.setPixelSize(10)
        self.splash.setFont(font)
        if not self.light:
            self.splash.show()
            self.set_splash(_("Initializing..."))
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
        
        self.apply_settings()
        
        self.debug_print("End of MainWindow constructor")
        
    def debug_print(self, message):
        """Debug prints"""
        if self.debug:
            print >>STDOUT, message
        
    #---- Window setup
    def create_toolbar(self, title, object_name, iconsize=24):
        """Create and return toolbar with *title* and *object_name*"""
        toolbar = self.addToolBar(title)
        toolbar.setObjectName(object_name)
        toolbar.setIconSize( QSize(iconsize, iconsize) )
        return toolbar
    
    def setup(self):
        """Setup main window"""
        self.debug_print("*** Start of MainWindow setup ***")
        if not self.light:
            self.close_dockwidget_action = create_action(self,
                                        _("Close current dockwidget"),
                                        triggered=self.close_current_dockwidget,
                                        context=Qt.ApplicationShortcut)
            self.register_shortcut(self.close_dockwidget_action,
                                   "_", "Close dockwidget", "Shift+Ctrl+F4")
            
            _text = _("&Find text")
            self.find_action = create_action(self, _text, icon='find.png',
                                             tip=_text, triggered=self.find,
                                             context=Qt.WidgetShortcut)
            self.register_shortcut(self.find_action, "Editor",
                                   "Find text", "Ctrl+F")
            self.find_next_action = create_action(self, _("Find &next"),
                  icon='findnext.png', triggered=self.find_next,
                  context=Qt.WidgetShortcut)
            self.register_shortcut(self.find_next_action, "Editor",
                                   "Find next", "F3")
            self.find_previous_action = create_action(self,
                        _("Find &previous"),
                        icon='findprevious.png', triggered=self.find_previous,
                        context=Qt.WidgetShortcut)
            self.register_shortcut(self.find_previous_action, "Editor",
                                   "Find previous", "Shift+F3")
            _text = _("&Replace text")
            self.replace_action = create_action(self, _text, icon='replace.png',
                                            tip=_text, triggered=self.replace,
                                            context=Qt.WidgetShortcut)
            self.register_shortcut(self.replace_action, "Editor",
                                   "Replace text", "Ctrl+H")
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
            # Maximize current plugin
            self.maximize_action = create_action(self, '',
                                             triggered=self.maximize_dockwidget)
            self.register_shortcut(self.maximize_action, "_",
                                   "Maximize dockwidget", "Ctrl+Alt+Shift+M")
            self.__update_maximize_action()
            
            # Fullscreen mode
            self.fullscreen_action = create_action(self,
                                            _("Fullscreen mode"),
                                            triggered=self.toggle_fullscreen)
            self.register_shortcut(self.fullscreen_action, "_",
                                   "Fullscreen mode", "F11")
            self.main_toolbar_actions = [self.maximize_action,
                                         self.fullscreen_action, None]
            
            # Main toolbar
            self.main_toolbar = self.create_toolbar(_("Main toolbar"),
                                                    "main_toolbar")
            
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
            
            # Interact menu/toolbar
            self.interact_menu = self.menuBar().addMenu(_("&Interpreters"))
            
            # Tools menu
            self.tools_menu = self.menuBar().addMenu(_("&Tools"))
            
            # View menu will be inserted afterwards
            
            # Help menu
            self.help_menu = self.menuBar().addMenu("?")
                    
            # Status bar
            status = self.statusBar()
            status.setObjectName("StatusBar")
            status.showMessage(_("Welcome to Spyder!"), 5000)
            
            
            # Tools + External Tools
            prefs_action = create_action(self, _("Pre&ferences"),
                                         icon='configure.png',
                                         triggered=self.edit_preferences)
            self.register_shortcut(prefs_action, "_", "Preferences",
                                   "Ctrl+Alt+Shift+P")
            spyder_path_action = create_action(self,
                                        _("PYTHONPATH manager"),
                                        None, 'pythonpath_mgr.png',
                                        triggered=self.path_manager_callback,
                                        tip=_("Open Spyder path manager"))
            update_modules_action = create_action(self,
                                        _("Update module names list"),
                                        None, 'reload.png',
                                        triggered=self.update_modules,
                                        tip=_("Update the list of names of all "
                                              "the modules available in your "
                                              "PYTHONPATH"))
            self.tools_menu_actions = [prefs_action, spyder_path_action]
            self.tools_menu_actions += [update_modules_action, None]
            self.main_toolbar_actions += [prefs_action, spyder_path_action]
            if WinUserEnvDialog is not None:
                winenv_action = create_action(self,
                        _("Current user environment variables..."),
                        icon='win_env.png',
                        tip=_("Show and edit current user environment "
                              "variables in Windows registry "
                              "(i.e. for all sessions)"),
                        triggered=self.win_env)
                self.tools_menu_actions.append(winenv_action)
            
            # External Tools submenu
            self.external_tools_menu = QMenu(_("External Tools"))
            self.external_tools_menu_actions = []
            # Python(x,y) launcher
            self.xy_action = create_action(self,
                                       _("Python(x,y) launcher"),
                                       icon=get_icon('pythonxy.png'),
                                       triggered=lambda:
                                       run_python_script('xy', 'xyhome'))
            self.external_tools_menu_actions.append(self.xy_action)
            if not is_module_installed('xy'):
                self.xy_action.setDisabled(True)
                self.xy_action.setToolTip(self.xy_action.toolTip() + \
                                          '\nPlease install Python(x,y) to '
                                          'enable this feature')
            # Qt-related tools
            additact = [None]
            for name in ("designer-qt4", "designer"):
                qtdact = create_program_action(self, _("Qt Designer"),
                                               'qtdesigner.png', name)
                if qtdact:
                    break
            for name in ("linguist-qt4", "linguist"):
                qtlact = create_program_action(self, _("Qt Linguist"),
                                               'qtlinguist.png', "linguist")
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
            if len(additact) > 1:
                self.external_tools_menu_actions += additact
                
            # Sift
            if is_module_installed('guidata') \
               and is_module_installed('guiqwt'):
                from guidata import configtools
                from guiqwt import config  # (loading icons) analysis:ignore
                sift_icon = configtools.get_icon('sift.svg')
                sift_act = create_python_script_action(self, _("Sift"),
                               sift_icon, "guiqwt", osp.join("tests", "sift"))
                if sift_act:
                    self.external_tools_menu_actions += [None, sift_act]
                
            # ViTables
            vitables_act = create_program_action(self, _("ViTables"),
                                                 'vitables.png', "vitables")
            if vitables_act:
                self.external_tools_menu_actions += [None, vitables_act]
            
            
            # Internal console plugin
            self.console = Console(self, namespace, debug=self.debug,
                                   exitfunc=self.closing, profile=self.profile,
                                   multithreaded=self.multithreaded)
            self.console.register_plugin()
            
            # Working directory plugin
            self.workingdirectory = WorkingDirectory(self, self.init_workdir)
            self.workingdirectory.register_plugin()
        
            # Object inspector plugin
            if CONF.get('inspector', 'enable'):
                self.set_splash(_("Loading object inspector..."))
                self.inspector = ObjectInspector(self)
                self.inspector.register_plugin()
            
            # Outline explorer widget
            if CONF.get('outline_explorer', 'enable'):
                self.set_splash(_("Loading outline explorer..."))
                fullpath_sorting = CONF.get('editor', 'fullpath_sorting', True)
                self.outlineexplorer = OutlineExplorer(self,
                                            fullpath_sorting=fullpath_sorting)
                self.outlineexplorer.register_plugin()
            
            # Editor plugin
            self.set_splash(_("Loading editor..."))
            self.editor = Editor(self)
            self.editor.register_plugin()
            
            # Populating file menu entries
            quit_action = create_action(self, _("&Quit"),
                                        icon='exit.png', tip=_("Quit"),
                                        triggered=self.console.quit)
            self.register_shortcut(quit_action, "_", "Quit", "Ctrl+Q")
            self.file_menu_actions += [self.load_temp_session_action,
                                       self.load_session_action,
                                       self.save_session_action,
                                       None, quit_action]
            self.set_splash("")
        
            # Find in files
            if CONF.get('find_in_files', 'enable'):
                self.findinfiles = FindInFiles(self)
                self.findinfiles.register_plugin()
            
            # Explorer
            if CONF.get('explorer', 'enable'):
                self.set_splash(_("Loading file explorer..."))
                self.explorer = Explorer(self)
                self.explorer.register_plugin()

            # History log widget
            if CONF.get('historylog', 'enable'):
                self.set_splash(_("Loading history plugin..."))
                self.historylog = HistoryLog(self)
                self.historylog.register_plugin()
                
            # Online help widget
            if CONF.get('onlinehelp', 'enable') and OnlineHelp is not None:
                self.set_splash(_("Loading online help..."))
                self.onlinehelp = OnlineHelp(self)
                self.onlinehelp.register_plugin()
                
            # Project explorer widget
            if CONF.get('project_explorer', 'enable'):
                self.set_splash(_("Loading project explorer..."))
                self.projectexplorer = ProjectExplorer(self)
                self.projectexplorer.register_plugin()
            
        # External console
        if self.light:
            # This is necessary to support the --working-directory option:
            if self.init_workdir is not None:
                os.chdir(self.init_workdir)
        else:
            self.set_splash(_("Loading external console..."))
        self.extconsole = ExternalConsole(self, light_mode=self.light)
        self.extconsole.register_plugin()
        
        # Namespace browser
        if not self.light:
            # In light mode, namespace browser is opened inside external console
            # Here, it is opened as an independent plugin, in its own dockwidget
            self.set_splash(_("Loading namespace browser..."))
            self.variableexplorer = VariableExplorer(self)
            self.variableexplorer.register_plugin()

        if not self.light:
            nsb = self.variableexplorer.add_shellwidget(self.console.shell)
            self.connect(self.console.shell, SIGNAL('refresh()'),
                         nsb.refresh_table)
            nsb.auto_refresh_button.setEnabled(False)
            
            self.set_splash(_("Setting up main window..."))
            
            # ? menu
            about_action = create_action(self,
                                    _("About %s...") % "Spyder",
                                    icon=get_std_icon('MessageBoxInformation'),
                                    triggered=self.about)
            report_action = create_action(self,
                                    _("Report issue..."),
                                    icon=get_icon('bug.png'),
                                    triggered=self.report_issue
                                    )
            # Spyder documentation
            doc_path = get_module_data_path('spyderlib', relpath="doc",
                                            attr_name='DOCPATH')
            # * Trying to find the chm doc
            spyder_doc = osp.join(doc_path, "Spyderdoc.chm")
            if not osp.isfile(spyder_doc):
                spyder_doc = osp.join(doc_path, os.pardir, os.pardir,
                                      "Spyderdoc.chm")
            # * Trying to find the html doc
            if not osp.isfile(spyder_doc):
                spyder_doc = osp.join(doc_path, "index.html")
                if not osp.isfile(spyder_doc):  # development version
                    spyder_doc = osp.join(get_module_source_path('spyderlib'),
                                          os.pardir, 'build', 'lib',
                                          'spyderlib', 'doc', "index.html")
            spyder_doc = file_uri(spyder_doc)
            doc_action = create_bookmark_action(self, spyder_doc,
                               _("Spyder documentation"), shortcut="F1",
                               icon=get_std_icon('DialogHelpButton'))
            self.help_menu_actions = [about_action, report_action, doc_action]
            # Python documentation
            if get_python_doc_path() is not None:
                pydoc_act = create_action(self, _("Python documentation"),
                                          icon=get_icon('python.png'),
                                          triggered=lambda:
                                          start_file(get_python_doc_path()))
                self.help_menu_actions += [None, pydoc_act]
            # Qt assistant link
            qta_act = create_program_action(self, _("Qt Assistant"),
                                            'qtassistant.png', "assistant")
            if qta_act:
                self.help_menu_actions.append(qta_act)
            # Documentation provided by Python(x,y), if available
            try:
                from xy.config import DOC_PATH as xy_doc_path
                xydoc = osp.join(xy_doc_path, "Libraries")
                def add_xydoc(text, pathlist):
                    for path in pathlist:
                        if osp.exists(path):
                            ext = osp.splitext(path)[1]
                            if ext:
                                icon = get_icon(ext[1:]+".png")
                            else:
                                icon = get_std_icon("DirIcon")
                            path = file_uri(path)
                            action = create_action(self, text, icon=icon,
                                                   triggered=lambda path=path:
                                                             start_file(path))
                            self.help_menu_actions.append(action)
                            break
                self.help_menu_actions.append(None)
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
                self.help_menu_actions.append(None)
            except (ImportError, KeyError, RuntimeError):
                pass
            # Online documentation
            web_resources = QMenu(_("Web Resources"))
            web_resources.setIcon(get_icon("browser.png"))
            add_actions(web_resources,
                        create_module_bookmark_actions(self, self.BOOKMARKS))
            self.help_menu_actions.append(web_resources)
            
            # IPython frontend action
            if is_module_installed('IPython', '0.12'):
                ipf_action = create_action(self, _("New IPython frontend..."),
                                           icon="ipython.png",
                                           triggered=self.new_ipython_frontend)
                self.interact_menu_actions += [None, ipf_action]

            # Third-party plugins
            for mod in get_spyderplugins_mods(prefix='p_', extension='.py'):
                try:
                    plugin = mod.PLUGIN_CLASS(self)
                    self.thirdparty_plugins.append(plugin)
                    plugin.register_plugin()
                except AttributeError, error:
                    print >>STDERR, "%s: %s" % (mod, str(error))
                                
            # View menu
            self.view_menu = self.menuBar().addMenu(_("&View"))
            self.windows_toolbars_menu = QMenu(_("Windows and toolbars"), self)
            self.connect(self.windows_toolbars_menu, SIGNAL("aboutToShow()"),
                         self.update_windows_toolbars_menu)
            self.view_menu.addMenu(self.windows_toolbars_menu)
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
                                       "Switch to/from layout %d" % index,
                                       "Shift+Alt+F%d" % index)
                qlsi_act = create_action(self, _("Set layout %d") % index,
                                         triggered=lambda i=index:
                                         self.quick_layout_set(i))
                self.register_shortcut(qlsi_act, "_",
                                       "Set layout %d" % index,
                                       "Ctrl+Shift+Alt+F%d" % index)
                ql_actions += [qli_act, qlsi_act]
            add_actions(quick_layout_menu, ql_actions)
            if set_attached_console_visible is not None:
                cmd_act = create_action(self,
                                    _("Attached console window (debugging)"),
                                    toggled=set_attached_console_visible)
                cmd_act.setChecked(is_attached_console_visible())
                add_actions(self.view_menu, (None, cmd_act))
            add_actions(self.view_menu, (None, self.maximize_action,
                                         self.fullscreen_action, None,
                                         reset_layout_action, quick_layout_menu,
                                         None, self.close_dockwidget_action))
            self.menuBar().insertMenu(self.help_menu.menuAction(),
                                      self.view_menu)
            
            # Adding external tools action to "Tools" menu
            external_tools_act = create_action(self, _("External Tools"),
                                               icon="ext_tools.png")
            external_tools_act.setMenu(self.external_tools_menu)
            self.tools_menu_actions.append(external_tools_act)
            self.main_toolbar_actions.append(external_tools_act)
            
            # Filling out menu/toolbar entries:
            add_actions(self.file_menu, self.file_menu_actions)
            add_actions(self.edit_menu, self.edit_menu_actions)
            add_actions(self.search_menu, self.search_menu_actions)
            add_actions(self.source_menu, self.source_menu_actions)
            add_actions(self.run_menu, self.run_menu_actions)
            add_actions(self.interact_menu, self.interact_menu_actions)
            add_actions(self.tools_menu, self.tools_menu_actions)
            add_actions(self.external_tools_menu,
                        self.external_tools_menu_actions)
            add_actions(self.help_menu, self.help_menu_actions)
            
            add_actions(self.main_toolbar, self.main_toolbar_actions)
            add_actions(self.file_toolbar, self.file_toolbar_actions)
            add_actions(self.edit_toolbar, self.edit_toolbar_actions)
            add_actions(self.search_toolbar, self.search_toolbar_actions)
            add_actions(self.source_toolbar, self.source_toolbar_actions)
            add_actions(self.run_toolbar, self.run_toolbar_actions)
        
        # Apply all defined shortcuts (plugins + 3rd-party plugins)
        self.apply_shortcuts()
        
        # Emitting the signal notifying plugins that main window menu and 
        # toolbar actions are all defined:
        self.emit(SIGNAL('all_actions_defined()'))
        
        # Window set-up
        self.debug_print("Setting up window...")
        self.setup_layout(default=False)
            
        self.splash.hide()
        
        # Enabling tear off for all menus except help menu
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
        self.extconsole.open_interpreter_at_startup()
        self.extconsole.setMinimumHeight(0)
        if self.projectexplorer is not None:
            self.projectexplorer.check_for_io_errors()
        # [Workaround for Issue 880]
        # QDockWidget objects are not painted if restored as floating 
        # windows, so we must dock them before showing the mainwindow,
        # then set them again as floating windows here.
        for widget in self.floating_dockwidgets:
            widget.setFloating(True)
        
    def load_window_settings(self, prefix, default=False, section='main'):
        """Load window layout settings from userconfig-based configuration
        with *prefix*, under *section*
        default: if True, do not restore inner layout"""
        get_func = CONF.get_default if default else CONF.get
        width, height = get_func(section, prefix+'size')
        if default:
            hexstate = None
        else:
            hexstate = get_func(section, prefix+'state', None)
        posx, posy =    get_func(section, prefix+'position')
        is_maximized =  get_func(section, prefix+'is_maximized')
        is_fullscreen = get_func(section, prefix+'is_fullscreen')
        return hexstate, width, height, posx, posy, is_maximized, is_fullscreen
    
    def get_window_settings(self):
        """Return current window settings
        Symetric to the 'set_window_settings' setter"""
        size = self.window_size
        width, height = size.width(), size.height()
        is_fullscreen = self.isFullScreen()
        if is_fullscreen:
            is_maximized = self.maximized_flag
        else:
            is_maximized = self.isMaximized()
        pos = self.window_position
        posx, posy = pos.x(), pos.y()
        hexstate = str(self.saveState().toHex())
        return hexstate, width, height, posx, posy, is_maximized, is_fullscreen
        
    def set_window_settings(self, hexstate, width, height, posx, posy,
                            is_maximized, is_fullscreen):
        """Set window settings
        Symetric to the 'get_window_settings' accessor"""
        self.setUpdatesEnabled(False)
        self.window_size = QSize(width, height)
        self.window_position = QPoint(posx, posy)
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
        size = self.window_size
        CONF.set(section, prefix+'size', (size.width(), size.height()))
        CONF.set(section, prefix+'is_maximized', self.isMaximized())
        CONF.set(section, prefix+'is_fullscreen', self.isFullScreen())
        pos = self.window_position
        CONF.set(section, prefix+'position', (pos.x(), pos.y()))
        if not self.light:
            self.maximize_dockwidget(restore=True)# Restore non-maximized layout
            qba = self.saveState()
            CONF.set(section, prefix+'state', str(qba.toHex()))
            CONF.set(section, prefix+'statusbar',
                     not self.statusBar().isHidden())
        
    def setup_layout(self, default=False):
        """Setup window layout"""
        prefix = ('lightwindow' if self.light else 'window') + '/'
        (hexstate, width, height, posx, posy, is_maximized,
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
                                  (self.extconsole, self.historylog),

                                  (self.inspector, self.variableexplorer),
                                  (self.variableexplorer, self.onlinehelp),
                                  (self.onlinehelp, self.explorer),
                                  (self.explorer, self.findinfiles),
                                  ):
                if first is not None and second is not None:
                    self.tabifyDockWidget(first.dockwidget, second.dockwidget)
            for plugin in [self.findinfiles, self.onlinehelp, self.console,
                           ]+self.thirdparty_plugins:
                if plugin is not None:
                    plugin.dockwidget.close()
            for plugin in (self.inspector, self.extconsole):
                if plugin is not None:
                    plugin.dockwidget.raise_()
            self.extconsole.setMinimumHeight(250)
            for toolbar in (self.run_toolbar, self.edit_toolbar):
                toolbar.close()
            for plugin in (self.projectexplorer, self.outlineexplorer):
                plugin.dockwidget.close()
                
        self.set_window_settings(hexstate, width, height, posx, posy,
                                 is_maximized, is_fullscreen)

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
            except NoOptionError:
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

    def __focus_shell(self):
        """Return Python shell widget which has focus, if any"""
        widget = QApplication.focusWidget()
        from spyderlib.widgets.shell import PythonShellWidget
        from spyderlib.widgets.externalshell.pythonshell import ExternalPythonShell
        if isinstance(widget, PythonShellWidget):
            return widget
        elif isinstance(widget, ExternalPythonShell):
            return widget.shell
        
    def plugin_focus_changed(self):
        """Focus has changed from one plugin to another"""
        self.update_edit_menu()
        self.update_search_menu()
        shell = self.__focus_shell()
        if shell is not None and self.inspector is not None:
            self.inspector.set_shell(shell)
            from spyderlib.widgets.externalshell import pythonshell
            if isinstance(shell, pythonshell.ExtPythonShellWidget):
                shell = shell.parent()
            self.variableexplorer.set_shellwidget(shell)
        else:
            widget = QApplication.focusWidget()
            for ipf in self.ipython_frontends:
                if widget is ipf or widget is ipf.get_focus_widget():
                    if ipf.kernel_widget is not None:
                        self.variableexplorer.set_shellwidget(
                        ipf.kernel_widget)
        
    def update_file_menu(self):
        """Update file menu"""
        self.load_temp_session_action.setEnabled(osp.isfile(TEMP_SESSION_PATH))
        
    def __focus_widget_properties(self):
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
        
    def update_edit_menu(self):
        """Update edit menu"""
        if self.menuBar().hasFocus():
            return
        # Disabling all actions to begin with
        for child in self.edit_menu.actions():
            child.setEnabled(False)        
        
        widget, textedit_properties = self.__focus_widget_properties()
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
        
        widget, textedit_properties = self.__focus_widget_properties()
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
        
    def update_windows_toolbars_menu(self):
        """Update windows&toolbars menu"""
        self.windows_toolbars_menu.clear()
        popmenu = self.createPopupMenu()
        add_actions(self.windows_toolbars_menu, popmenu.actions())
        
    def set_splash(self, message):
        """Set splash message"""
        if message:
            self.debug_print(message)
        self.splash.show()
        self.splash.showMessage(message, Qt.AlignBottom | Qt.AlignCenter | 
                                Qt.AlignAbsolute, QColor(Qt.white))
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
        
    def moveEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.fullscreen_flag:
            self.window_position = self.pos()
        QMainWindow.moveEvent(self, event)
        
    def closing(self, cancelable=False):
        """Exit tasks"""
        if self.already_closed or self.is_starting_up:
            return True
        prefix = ('lightwindow' if self.light else 'window') + '/'
        self.save_current_window_settings(prefix)
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
            text = _("Maximize current plugin")
            tip = _("Maximize current plugin to fit the whole "
                    "application window")
            icon = "maximize.png"
        else:
            text = _("Restore current plugin")
            tip = _("Restore current plugin to its original size and "
                    "position within the application window")
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
        not_installed = _('(not installed)')
        try:
            from pyflakes import __version__ as pyflakes_version
        except ImportError:
            pyflakes_version = not_installed
        try:
            from rope import VERSION as rope_version
        except ImportError:
            rope_version = not_installed
        import spyderlib.qt.QtCore
        qt_api = os.environ['QT_API']
        qt_lib = {'pyqt': 'PyQt4', 'pyside': 'PySide'}[qt_api]
        if qt_api == 'pyqt':
            import sip
            try:
                qt_lib += (" (API v%d)" % sip.getapi('QString'))
            except AttributeError:
                pass
        QMessageBox.about(self,
            _("About %s") % "Spyder",
            """<b>%s %s</b>
            <br>Scientific PYthon Development EnviRonment
            <p>Copyright &copy; 2009-2011 Pierre Raybaut
            <br>Licensed under the terms of the MIT License
            <p>Created by Pierre Raybaut
            <br>Developed and maintained by the 
            <a href="%s/people/list">Spyder Development Team</a>
            <br>Many thanks to all the Spyder beta-testers and regular users.
            <p>Source code editor: Python code real-time analysis is powered by 
            %spyflakes %s%s (&copy; 2005 
            <a href="http://www.divmod.com/">Divmod, Inc.</a>) and other code 
            introspection features (completion, go-to-definition, ...) are 
            powered by %srope %s%s (&copy; 2006-2009 Ali Gholami Rudi)
            <br>Most of the icons are coming from the %sCrystal Project%s 
            (&copy; 2006-2007 Everaldo Coelho)
            <p>Spyder's community:
            <ul><li>Bug reports and feature requests: 
            <a href="%s">Google Code</a>
            </li><li>Discussions around the project: 
            <a href="%s">Google Group</a>
            </li></ul>
            <p>This project is part of 
            <a href="http://www.pythonxy.com">Python(x,y) distribution</a>
            <p>Python %s, Qt %s, %s %s on %s"""
            % ("Spyder", __version__, __project_url__,
                 "<span style=\'color: #444444\'><b>",
                 pyflakes_version,
                 "</b></span>",
                 "<span style=\'color: #444444\'><b>",
                 rope_version,
                 "</b></span>",
                 "<span style=\'color: #444444\'><b>",
                 "</b></span>",
                 __project_url__, __forum_url__,
                 platform.python_version(),
                 spyderlib.qt.QtCore.__version__,
                 qt_lib, spyderlib.qt.__version__,
                 platform.system()) )

    def report_issue(self):
        qt_api = os.environ['QT_API']
        qt_lib = {'pyqt': 'PyQt4', 'pyside': 'PySide'}[qt_api]
        if qt_api == 'pyqt':
            import sip
            try:
                qt_lib += (" (API v%d)" % sip.getapi('QString'))
            except AttributeError:
                pass
        import spyderlib.qt.QtCore
        issue_template = """\
Spyder Version:  %s
Python Version:  %s
Qt Version:      %s, %s %s on %s

What steps will reproduce the problem?
1.
2.
3.

What is the expected output? What do you see instead?


Please provide any additional information below.
""" % (__version__,
       platform.python_version(),
       spyderlib.qt.QtCore.__version__, qt_lib, spyderlib.qt.__version__,
       platform.system())
       
        url = QUrl("http://code.google.com/p/spyderlib/issues/entry")
        url.addQueryItem("comment", issue_template)
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
        callback = from_qvariant(action.data(), unicode)
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
                run_python_script_in_terminal(fname, wdir, args, interact,
                                              debug, python_args)
            except NotImplementedError:
                QMessageBox.critical(self, _("Run"),
                                     _("Running an external system terminal "
                                       "is not supported on platform %s."
                                       ) % os.name)
        else:
            self.extconsole.setVisible(True)
            self.extconsole.raise_()
            self.extconsole.start(
                fname=unicode(fname), wdir=unicode(wdir), args=unicode(args),
                interact=interact, debug=debug, python=python,
                python_args=unicode(python_args) )
        
    def execute_python_code_in_external_console(self, lines):
        """Execute lines in external console"""
        self.extconsole.setVisible(True)
        self.extconsole.raise_()
        self.extconsole.execute_python_code(lines)
        
    def open_file(self, fname):
        """
        Open filename with the appropriate application
        Redirect to the right widget (txt -> editor, spydata -> workspace, ...)
        or open file outside Spyder (if extension is not supported)
        """
        fname = unicode(fname)
        ext = osp.splitext(fname)[1]
        if ext in EDIT_EXT:
            self.editor.load(fname)
        elif self.variableexplorer is not None and ext in IMPORT_EXT\
             and ext in ('.spydata', '.mat', '.npy', '.h5'):
            self.variableexplorer.import_data(fname)
        else:
            fname = file_uri(fname)
            start_file(fname)
            
    def new_ipython_frontend(self, args=None,
                             kernel_widget=None, kernel_name=None):
        """Create a new IPython frontend"""
        if args is None:
            example = '(example: --existing --shell=56742 --iopub=52543 '\
                      '--stdin=60596 --hb=1644)'
            while True:
                args, valid = QInputDialog.getText(self, _('IPython'),
                                  _('IPython kernel parameters:')+'\n'+example,
                                  QLineEdit.Normal)
                if valid:
                    args = unicode(args)
                    if re.match('^--existing --shell=(\d+) --iopub=(\d+) '\
                                '--stdin=(\d+) --hb=(\d+)$', args)\
                       or re.match('^--existing kernel-(\d+).json', args):
                        kernel_name = args
                        break
                else:
                    return
        from spyderlib.plugins.ipython import IPythonPlugin
        ipython_plugin = IPythonPlugin(self, args, kernel_widget, kernel_name)
        ipython_plugin.register_plugin()
        self.ipython_frontends.append(ipython_plugin)
        
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
        self.remove_path_from_sys_path()
        project_pathlist = self.projectexplorer.get_pythonpath()
        dialog = PathManager(self, self.path, project_pathlist, sync=True)
        self.connect(dialog, SIGNAL('redirect_stdio(bool)'),
                     self.redirect_internalshell_stdio)
        dialog.exec_()
        self.add_path_to_sys_path()
        encoding.writelines(self.path, self.spyder_path) # Saving path
        
    def update_modules(self):
        """Update module names list"""
        from spyderlib.utils.external.pickleshare import PickleShareDB
        db = PickleShareDB(MODULES_PATH)
        del db['rootmodules']
        
    def pythonpath_changed(self):
        """Project Explorer PYTHONPATH contribution has changed"""
        self.remove_path_from_sys_path()
        self.project_path = self.projectexplorer.get_pythonpath()
        self.add_path_to_sys_path()
    
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
        
    def edit_preferences(self):
        """Edit Spyder preferences"""
        dlg = ConfigDialog(self)
        for PrefPageClass in self.general_prefs:
            widget = PrefPageClass(dlg, main=self)
            widget.initialize()
            dlg.add_page(widget)
        for plugin in [self.workingdirectory, self.editor, self.projectexplorer,
                       self.extconsole, self.historylog, self.inspector,
                       self.variableexplorer, self.onlinehelp, self.explorer,
                       self.findinfiles]+self.thirdparty_plugins:
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
                        os.getcwdu(), _("Spyder sessions")+" (*.session.tar)")
            self.redirect_internalshell_stdio(True)
            if not filename:
                return
        if self.close():
            self.next_session_name = filename
    
    def save_session(self):
        """Save session and quit application"""
        self.redirect_internalshell_stdio(False)
        filename, _selfilter = getsavefilename(self, _("Save session"),
                        os.getcwdu(), _("Spyder sessions")+" (*.session.tar)")
        self.redirect_internalshell_stdio(True)
        if filename:
            if self.close():
                self.save_session_name = filename

        
def get_options():
    """
    Convert options into commands
    return commands, message
    """
    import optparse
    parser = optparse.OptionParser(usage="spyder [options]")
    parser.add_option('-l', '--light', dest="light", action='store_true',
                      default=False,
                      help="Light version (all add-ons are disabled)")
    parser.add_option('--session', dest="startup_session", default='',
                      help="Startup session")
    parser.add_option('--defaults', dest="reset_to_defaults",
                      action='store_true', default=False,
                      help="Reset to configuration settings to defaults")
    parser.add_option('--reset', dest="reset_session",
                      action='store_true', default=False,
                      help="Remove all configuration files!")
    parser.add_option('--optimize', dest="optimize",
                      action='store_true', default=False,
                      help="Optimize Spyder bytecode (this may require "
                           "administrative privileges)")
    parser.add_option('-w', '--workdir', dest="working_directory", default=None,
                      help="Default working directory")
    parser.add_option('-d', '--debug', dest="debug", action='store_true',
                      default=False,
                      help="Debug mode (stds are not redirected)")
    parser.add_option('--showconsole', dest="show_console",
                      action='store_true', default=False,
                      help="Show parent console (Windows only)")
    parser.add_option('--multithread', dest="multithreaded",
                      action='store_true', default=False,
                      help="Internal console is executed in another thread "
                           "(separate from main application thread)")
    parser.add_option('--profile', dest="profile", action='store_true',
                      default=False,
                      help="Profile mode (internal test, "
                           "not related with Python profiling)")
    options, _args = parser.parse_args()
    return options


def initialize():
    """Initialize Qt, patching sys.exit and eventually setting up ETS"""
    app = qapplication()
    
    #----Monkey patching PyQt4.QtGui.QApplication
    class FakeQApplication(QApplication):
        """Spyder's fake QApplication"""
        def __init__(self, args):
            self = app
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


def run_spyder(app, options):
    """
    Create and show Spyder's main window
    Patch matplotlib for figure integration
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
    app.exec_()
    return main


def __remove_temp_session():
    if osp.isfile(TEMP_SESSION_PATH):
        os.remove(TEMP_SESSION_PATH)

def main():
    """Session manager"""
    __remove_temp_session()
    
    # **** Collect command line options ****
    # Note regarding Options:
    # It's important to collect options before monkey patching sys.exit,
    # otherwise, optparse won't be able to exit if --help option is passed
    options = get_options()

    if set_attached_console_visible is not None:
        set_attached_console_visible(options.debug or options.show_console\
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
        run_python_script(module="compileall", args=[spyderlib.__path__[0]],
                          p_args=['-O'])
        return

    if CONF.get('main', 'crash', False):
        CONF.set('main', 'crash', False)
        QMessageBox.information(None, "Spyder",
            u"Spyder crashed during last session.<br><br>"
            u"If Spyder does not start at all and <u>before submitting a "
            u"bug report</u>, please try to reset settings to defaults by "
            u"running Spyder with the command line option '--reset':<br>"
            u"<span style=\'color: #555555\'><b>python spyder --reset"
            u"</b></span><br><br>"
            u"<span style=\'color: #ff5555\'><b>Warning:</b></span> "
            u"this command will remove all your Spyder configuration files "
            u"located in '%s').<br><br>"
            u"If restoring the default settings does not help, please take "
            u"the time to search for <a href=\"%s\">known bugs</a> or "
            u"<a href=\"%s\">discussions</a> matching your situation before "
            u"eventually creating a new issue <a href=\"%s\">here</a>. "
            u"Your feedback will always be greatly appreciated."
            u"" % (get_conf_path(), __project_url__,
                   __forum_url__, __project_url__))
        
    next_session_name = options.startup_session
    while isinstance(next_session_name, basestring):
        if next_session_name:
            error_message = load_session(next_session_name)
            if next_session_name == TEMP_SESSION_PATH:
                __remove_temp_session()
            if error_message is None:
                CONF.load_from_ini()
            else:
                print error_message
                QMessageBox.critical(None, "Load session",
                                     u"<b>Unable to load '%s'</b>"
                                     u"<br><br>Error message:<br>%s"
                                      % (osp.basename(next_session_name),
                                         error_message))
        mainwindow = None
        try:
            mainwindow = run_spyder(app, options)
            if not osp.isfile(get_conf_path('db/rootmodules')):
                getRootModules()
        except BaseException:
            CONF.set('main', 'crash', True)
            import traceback
            traceback.print_exc(file=STDERR)
            traceback.print_exc(file=open('spyder_crash.log', 'wb'))            
        if mainwindow is None:
            # An exception occured
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
                                     u"<b>Unable to save '%s'</b>"
                                     u"<br><br>Error message:<br>%s"
                                       % (osp.basename(save_session_name),
                                          error_message))
    ORIGINAL_SYS_EXIT()

if __name__ == "__main__":
    main()

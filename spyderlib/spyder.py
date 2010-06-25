# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder, the Scientific PYthon Development EnviRonment
=====================================================

Developped and maintained by Pierre Raybaut

Copyright © 2009 Pierre Raybaut
Licensed under the terms of the MIT License
(see spyderlib/__init__.py for details)
"""

# Check requirements
import spyderlib.requirements #@UnusedImport

import sys, os, platform, re, webbrowser, os.path as osp
original_sys_exit = sys.exit

# Force Python to search modules in the current directory first:
sys.path.insert(0, '')

# For debugging purpose only
STDOUT = sys.stdout
STDERR = sys.stderr

from PyQt4.QtGui import (QApplication, QMainWindow, QSplashScreen, QPixmap,
                         QMessageBox, QMenu, QColor, QFileDialog, QShortcut,
                         QKeySequence)
from PyQt4.QtCore import (SIGNAL, PYQT_VERSION_STR, QT_VERSION_STR, QPoint, Qt,
                          QSize, QByteArray)

# Local imports
from spyderlib import __version__
from spyderlib.utils import encoding
try:
    from spyderlib.utils.environ import WinUserEnvDialog
except ImportError:
    WinUserEnvDialog = None
from spyderlib.widgets.pathmanager import PathManager
from spyderlib.plugins.console import Console
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
from spyderlib.plugins.pylintgui import Pylint
from spyderlib.utils.qthelpers import (create_action, add_actions, get_std_icon,
                                       create_module_bookmark_actions,
                                       create_bookmark_action,
                                       create_program_action,
                                       keybinding, translate, qapplication,
                                       create_python_gui_script_action)
from spyderlib.config import (get_icon, get_image_path, CONF, get_conf_path,
                              DOC_PATH)
from spyderlib.utils.programs import run_python_gui_script, is_module_installed
from spyderlib.utils.iofuncs import load_session, save_session, reset_session


TEMP_SESSION_PATH = get_conf_path('.temp.session.tar')


def get_python_doc_path():
    """
    Return Python documentation path
    (Windows: return the PythonXX.chm path if available)
    """
    python_doc = ''
    doc_path = osp.join(sys.prefix, "Doc")
    if osp.isdir(doc_path):
        if os.name == 'nt':
            python_chm = [ path for path in  os.listdir(doc_path) \
                           if re.match(r"(?i)Python[0-9]{3}.chm", path) ]
            if python_chm:
                python_doc = osp.join(doc_path, python_chm[0])
        if not python_doc:
            python_doc = osp.join(doc_path, "index.html")
    if osp.isfile(python_doc):
        return python_doc
    
def open_python_doc():
    """
    Open Python documentation
    (Windows: open .chm documentation if found)
    """
    python_doc = get_python_doc_path()
    if os.name == 'nt':
        os.startfile(python_doc)
    else:
        webbrowser.open(python_doc)


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
    
    spyder_path = get_conf_path('.path')
    BOOKMARKS = (
         ('PyQt4',
          "http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/pyqt4ref.html",
          translate("MainWindow", "PyQt4 Reference Guide"), "qt.png"),
         ('PyQt4',
          "http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/classes.html",
          translate("MainWindow", "PyQt4 API Reference"), "qt.png"),
         ('xy', "http://www.pythonxy.com",
          translate("MainWindow", "Python(x,y)"), "pythonxy.png"),
         ('numpy', "http://docs.scipy.org/doc/",
          translate("MainWindow", "Numpy and Scipy documentation"),
          "scipy.png"),
         ('matplotlib', "http://matplotlib.sourceforge.net/contents.html",
          translate("MainWindow", "Matplotlib documentation"),
          "matplotlib.png"),
                )
    
    def __init__(self, options=None):
        super(MainWindow, self).__init__()
        
        self.debug = options.debug
        self.profile = options.profile
        self.multithreaded = options.multithreaded
        self.light = options.light
        
        self.debug_print("Start of MainWindow constructor")
        
#        self.setStyleSheet(STYLESHEET)
        
        # Area occupied by a dock widget can be split in either direction
        # to contain more dock widgets:
        self.setDockNestingEnabled(True)
        
        # Loading Spyder path
        self.path = []
        self.project_path = []
        if osp.isfile(self.spyder_path):
            self.path, _ = encoding.readlines(self.spyder_path)
            self.path = [name for name in self.path if osp.isdir(name)]
        self.remove_path_from_sys_path()
        self.add_path_to_sys_path()
        self.load_temp_session_action = create_action(self,
                                        self.tr("Reload last session"),
                                        triggered=lambda:
                                        self.load_session(TEMP_SESSION_PATH))
        self.load_session_action = create_action(self,
                                        self.tr("Load session..."),
                                        None, 'fileopen.png',
                                        triggered=self.load_session,
                                        tip=self.tr("Load Spyder session"))
        self.save_session_action = create_action(self,
                                        self.tr("Save session and quit..."),
                                        None, 'filesaveas.png',
                                        triggered=self.save_session,
                                        tip=self.tr("Save current session "
                                                    "and quit application"))
        self.spyder_path_action = create_action(self,
                                        self.tr("PYTHONPATH manager"),
                                        None, 'pythonpath.png',
                                        triggered=self.path_manager_callback,
                                        tip=self.tr("Open Spyder path manager"))
        
        # Widgets
        self.console = None
        self.editor = None
        self.explorer = None
        self.inspector = None
        self.onlinehelp = None
        self.projectexplorer = None
        self.historylog = None
        self.extconsole = None
        self.variableexplorer = None
        self.findinfiles = None
        self.pylint = None
        
        # Actions
        self.find_action = None
        self.find_next_action = None
        self.replace_action = None
        self.findinfiles_action = None        
        self.undo_action = None
        self.redo_action = None
        self.copy_action = None
        self.cut_action = None
        self.paste_action = None
        self.delete_action = None
        self.selectall_action = None
        self.edit_menu_actions = None
        self.search_menu_actions = None
        self.maximize_action = None
        self.fullscreen_action = None
        self.quit_action = None
        self.tools_menu_actions = None
        self.help_menu_actions = None
        
        # Menu bars
        self.file_menu = None
        self.edit_menu = None
        self.search_menu = None
        self.view_menu = None
        
        # Set Window title and icon
        title = "Spyder"
        if self.debug:
            title += " (DEBUG MODE)"
        self.setWindowTitle(title)
        self.setWindowIcon(get_icon('spyder.svg'))
        
        # Showing splash screen
        pixmap = QPixmap(get_image_path('splash.png'), 'png')
        self.splash = QSplashScreen(pixmap)
        font = self.splash.font()
        font.setPixelSize(11)
        self.splash.setFont(font)
        if not self.light:
            self.splash.show()
            self.set_splash(self.tr("Initializing..."))
        
        # List of satellite widgets (registered in add_dockwidget):
        self.widgetlist = []
        
        # Flag used if closing() is called by the exit() shell command
        self.already_closed = False
        
        self.window_size = None
        self.last_window_state = None
        self.last_plugin = None
        self.fullscreen_flag = None # isFullscreen does not work as expected
        
        # Session manager
        self.next_session_name = None
        self.save_session_name = None
        
        self.debug_print("End of MainWindow constructor")
        
    def debug_print(self, message):
        """Debug prints"""
        if self.debug:
            print >>STDOUT, message
        
    def create_toolbar(self, title, object_name, iconsize=24):
        toolbar = self.addToolBar(title)
        toolbar.setObjectName(object_name)
        toolbar.setIconSize( QSize(iconsize, iconsize) )
        return toolbar
        
    def setup(self):
        """Setup main window"""
        self.debug_print("*** Start of MainWindow setup ***")
        if self.light:
            QShortcut(QKeySequence("Ctrl+F"), self, self.find)
        else:
            _text = translate("FindReplace", "Find text")
            self.find_action = create_action(self, _text, "Ctrl+F", 'find.png',
                                             _text, triggered=self.find)
            self.find_next_action = create_action(self, translate("FindReplace",
                  "Find next"), "F3", 'findnext.png', triggered=self.find_next)
            _text = translate("FindReplace", "Replace text")
            self.replace_action = create_action(self, _text, "Ctrl+H",
                                                'replace.png', _text,
                                                triggered=self.replace)
            self.findinfiles_action = create_action(self,
                                self.tr("&Find in files"),
                                "Ctrl+Shift+F", 'findf.png',
                                triggered=self.findinfiles_callback,
                                tip=self.tr("Search text in multiple files"))        
            def create_edit_action(text, icon_name):
                return create_action(self, translate("SimpleEditor", text),
                                     shortcut=keybinding(text.replace(' ', '')),
                                     icon=get_icon(icon_name),
                                     triggered=self.global_callback,
                                     data=text.lower(),
                                     context=Qt.WidgetShortcut)
            self.undo_action = create_edit_action("Undo",'undo.png')
            self.redo_action = create_edit_action("Redo", 'redo.png')
            self.copy_action = create_edit_action("Copy", 'editcopy.png')
            self.cut_action = create_edit_action("Cut", 'editcut.png')
            self.paste_action = create_edit_action("Paste", 'editpaste.png')
            self.delete_action = create_edit_action("Delete", 'editdelete.png')
            self.selectall_action = create_edit_action("Select All",
                                                       'selectall.png')
            self.edit_menu_actions = [self.undo_action, self.redo_action,
                                      None, self.cut_action, self.copy_action,
                                      self.paste_action, self.delete_action,
                                      None, self.selectall_action]
            self.search_menu_actions = [self.find_action, self.find_next_action,
                                        self.replace_action]

        namespace = None
        if not self.light:
            main_toolbar = self.create_toolbar(self.tr("Main toolbar"),
                                               "main_toolbar")
            # Maximize current plugin
            self.maximize_action = create_action(self, '',
                                             shortcut="Ctrl+Alt+Shift+M",
                                             triggered=self.maximize_dockwidget)
            self.__update_maximize_action()
            main_toolbar.addAction(self.maximize_action)
            
            # Fullscreen mode
            self.fullscreen_action = create_action(self,
                                           self.tr("Fullscreen mode"),
                                           shortcut="F11",
                                           triggered=self.toggle_fullscreen)
            main_toolbar.addAction(self.fullscreen_action)
            main_toolbar.addSeparator()
            
            # File menu
            self.file_menu = self.menuBar().addMenu(self.tr("&File"))
            self.connect(self.file_menu, SIGNAL("aboutToShow()"),
                         self.update_file_menu)
            
            # Edit menu
            self.edit_menu = self.menuBar().addMenu(self.tr("&Edit"))
            add_actions(self.edit_menu, self.edit_menu_actions)
            
            # Search menu
            self.search_menu = self.menuBar().addMenu(self.tr("&Search"))
                    
            # Status bar
            status = self.statusBar()
            status.setObjectName("StatusBar")
            status.showMessage(self.tr("Welcome to Spyder!"), 5000)
            
            # Internal console widget
            self.console = Console(self, namespace, debug=self.debug,
                                   exitfunc=self.closing, profile=self.profile,
                                   multithreaded=self.multithreaded)
            self.connect(self.console, SIGNAL('focus_changed()'),
                         self.plugin_focus_changed)
            self.add_dockwidget(self.console)
            self.quit_action = create_action(self, self.tr("&Quit"),
                             self.tr("Ctrl+Q"), 'exit.png', self.tr("Quit"),
                             triggered=self.console.quit)
                                    
            # Editor widget
            self.set_splash(self.tr("Loading editor..."))
            self.editor = Editor(self)
            self.connect(self, SIGNAL('restore_scrollbar_position()'),
                         self.editor.restore_scrollbar_position)
            self.connect(self.editor, SIGNAL('focus_changed()'),
                         self.plugin_focus_changed)
            self.connect(self.console, SIGNAL("edit_goto(QString,int,QString)"),
                         self.editor.load)
            self.connect(self.editor,
                         SIGNAL("open_external_console(QString,QString,bool,bool,bool,bool)"),
                         self.open_external_console)
            self.connect(self.editor,
                         SIGNAL('external_console_execute_lines(QString)'),
                         self.execute_python_code_in_external_console)
            self.connect(self.editor, SIGNAL('redirect_stdio(bool)'),
                         self.redirect_internalshell_stdio)
            self.add_dockwidget(self.editor)
            self.add_to_menubar(self.editor, self.tr("&Source"))
            file_toolbar = self.create_toolbar(self.tr("File toolbar"),
                                               "file_toolbar")
            add_actions(file_toolbar, self.editor.file_toolbar_actions)
            analysis_toolbar = self.create_toolbar(self.tr("Analysis toolbar"),
                                                   "analysis_toolbar")
            add_actions(analysis_toolbar, self.editor.analysis_toolbar_actions)
            run_toolbar = self.create_toolbar(self.tr("Run toolbar"),
                                              "run_toolbar")
            add_actions(run_toolbar, self.editor.run_toolbar_actions)
            edit_toolbar = self.create_toolbar(self.tr("Edit toolbar"),
                                               "edit_toolbar")
            add_actions(edit_toolbar, self.editor.edit_toolbar_actions)
            
            # Populating file menu entries
            file_actions = self.editor.file_menu_actions[:]
            file_actions += [self.load_temp_session_action,
                             self.load_session_action, self.save_session_action,
                             None, self.spyder_path_action]
            if WinUserEnvDialog is not None:
                winenv_action = create_action(self,
                    self.tr("Current user environment variables..."),
                    icon = 'win_env.png',
                    tip = self.tr("Show and edit current user environment "
                                  "variables in Windows registry "
                                  "(i.e. for all sessions)"),
                    triggered=self.win_env)
                file_actions.append(winenv_action)
            file_actions += (None, self.quit_action)
        
            # Find in files
            if CONF.get('find_in_files', 'enable'):
                self.set_splash(self.tr("Loading find in files plugin..."))
                self.findinfiles = FindInFiles(self)
                self.findinfiles.set_pythonpath_callback( \
                                                  self.get_spyder_pythonpath)
                self.add_dockwidget(self.findinfiles)
                self.connect(self.findinfiles,
                             SIGNAL("edit_goto(QString,int,QString)"),
                             self.editor.load)
                self.connect(self.findinfiles, SIGNAL('redirect_stdio(bool)'),
                             self.redirect_internalshell_stdio)
                self.connect(self, SIGNAL('find_files(QString)'),
                             self.findinfiles.set_search_text)
                self.search_menu_actions += [None, self.findinfiles_action]
                
            # Populating search menu and toolbar
            add_actions(self.search_menu, self.search_menu_actions)
            search_toolbar = self.create_toolbar(self.tr("Search toolbar"),
                                                 "search_toolbar")
            add_actions(search_toolbar, self.search_menu_actions)
            
            # Explorer
            if CONF.get('explorer', 'enable'):
                self.set_splash(self.tr("Loading file explorer..."))
                self.explorer = Explorer(self)
                self.add_dockwidget(self.explorer)
                valid_types = self.editor.get_valid_types()
                self.explorer.set_editor_valid_types(valid_types)
                self.connect(self.explorer, SIGNAL("edit(QString)"),
                             self.editor.load)
                self.connect(self.explorer, SIGNAL("removed(QString)"),
                             self.editor.removed)
                self.connect(self.explorer, SIGNAL("renamed(QString,QString)"),
                             self.editor.renamed)
                self.connect(self.editor, SIGNAL("open_dir(QString)"),
                             self.explorer.chdir)
#                self.connect(self.explorer, SIGNAL("import_data(QString)"),
#                             self.workspace.import_data)
                self.connect(self.explorer, SIGNAL("run(QString)"),
                             lambda fname:
                             self.open_external_console(unicode(fname),
                                                osp.dirname(unicode(fname)),
                                                False, False, False, True))
                # Signal "refresh_explorer()" will eventually force the
                # explorer to change the opened directory:
                self.connect(self.console.shell, SIGNAL("refresh_explorer()"),
                             lambda:
                             self.explorer.refresh_plugin(force_current=True))
                # Signal "refresh_explorer(QString)" will refresh only the
                # contents of path passed by the signal in explorer:
                self.connect(self.console.shell,
                             SIGNAL("refresh_explorer(QString)"),
                             self.explorer.refresh_folder)
                self.connect(self.editor, SIGNAL("refresh_explorer(QString)"),
                             self.explorer.refresh_folder)

            # History log widget
            if CONF.get('historylog', 'enable'):
                self.set_splash(self.tr("Loading history plugin..."))
                self.historylog = HistoryLog(self)
                self.connect(self.historylog, SIGNAL('focus_changed()'),
                             self.plugin_focus_changed)
                self.add_dockwidget(self.historylog)
#                self.console.set_historylog(self.historylog)
                self.connect(self.console.shell, SIGNAL("refresh()"),
                             self.historylog.refresh_plugin)
        
            # Object inspector widget
            if CONF.get('inspector', 'enable'):
                self.set_splash(self.tr("Loading object inspector..."))
                self.inspector = ObjectInspector(self)
                self.connect(self.inspector, SIGNAL('focus_changed()'),
                             self.plugin_focus_changed)
                self.add_dockwidget(self.inspector)
                self.console.set_inspector(self.inspector)
                
            # Online help widget
            if CONF.get('onlinehelp', 'enable') and OnlineHelp is not None:
                self.set_splash(self.tr("Loading online help..."))
                self.onlinehelp = OnlineHelp(self)
                self.add_dockwidget(self.onlinehelp)
                
            # Project explorer widget
            if CONF.get('project_explorer', 'enable'):
                self.set_splash(self.tr("Loading project explorer..."))
                self.projectexplorer = ProjectExplorer(self)
                file_actions.insert(1, self.projectexplorer.new_project_action)
                self.pythonpath_changed()
                valid_types = self.editor.get_valid_types()
                self.projectexplorer.set_editor_valid_types(valid_types)
                self.connect(self, SIGNAL('restore_scrollbar_position()'),
                             self.projectexplorer.restore_scrollbar_position)
                self.connect(self.projectexplorer,
                             SIGNAL("pythonpath_changed()"),
                             self.pythonpath_changed)
                self.connect(self.projectexplorer,
                             SIGNAL("create_module(QString)"), self.editor.new)
                self.connect(self.projectexplorer, SIGNAL("edit(QString)"),
                             self.editor.load)
                self.connect(self.projectexplorer, SIGNAL("removed(QString)"),
                             self.editor.removed)
                self.connect(self.projectexplorer,
                             SIGNAL("removed_tree(QString)"),
                             self.editor.removed_tree)
                self.connect(self.projectexplorer,
                             SIGNAL("renamed(QString,QString)"),
                             self.editor.renamed)
#                self.connect(self.projectexplorer,
#                             SIGNAL("import_data(QString)"),
#                             self.workspace.import_data)
                self.add_dockwidget(self.projectexplorer)
            add_actions(self.file_menu, file_actions)
                
            # Pylint widget
            if CONF.get('pylint', 'enable'):
                self.set_splash(self.tr("Loading pylint plugin..."))
                self.pylint = Pylint(self)
                self.connect(self.editor, SIGNAL('run_pylint(QString)'),
                             self.pylint.analyze)
                self.connect(self.pylint,
                             SIGNAL("edit_goto(QString,int,QString)"),
                             self.editor.load)
                self.connect(self.pylint, SIGNAL('redirect_stdio(bool)'),
                             self.redirect_internalshell_stdio)
                self.add_dockwidget(self.pylint)
            
        # External console menu
        if not self.light:
            self.set_splash(self.tr("Loading external console..."))
        self.extconsole = ExternalConsole(self, light_mode=self.light)
        if self.light:
            self.setCentralWidget(self.extconsole)
            self.widgetlist.append(self.extconsole)
        else:
            self.extconsole.set_inspector(self.inspector)
            self.extconsole.set_historylog(self.historylog)
            self.connect(self.extconsole,
                         SIGNAL("edit_goto(QString,int,QString)"),
                         self.editor.load)
            self.connect(self.editor,
                         SIGNAL('run_script_in_external_console(QString)'),
                         self.extconsole.run_script_in_current_shell)
            self.connect(self.editor, SIGNAL("open_dir(QString)"),
                     self.extconsole.set_current_shell_working_directory)
            self.add_dockwidget(self.extconsole)
            self.add_to_menubar(self.extconsole)
            self.connect(self.extconsole, SIGNAL('focus_changed()'),
                         self.plugin_focus_changed)
            self.connect(self.extconsole, SIGNAL('redirect_stdio(bool)'),
                         self.redirect_internalshell_stdio)
            self.connect(self.explorer, SIGNAL("open_terminal(QString)"),
                         self.extconsole.open_terminal)
            self.connect(self.explorer, SIGNAL("open_interpreter(QString)"),
                         self.extconsole.open_interpreter)
            self.connect(self.explorer, SIGNAL("open_ipython(QString)"),
                         self.extconsole.open_ipython)
            self.connect(self.projectexplorer, SIGNAL("open_terminal(QString)"),
                         self.extconsole.open_terminal)
            self.connect(self.projectexplorer,
                         SIGNAL("open_interpreter(QString)"),
                         self.extconsole.open_interpreter)
            self.connect(self.projectexplorer, SIGNAL("open_ipython(QString)"),
                         self.extconsole.open_ipython)

            # Namespace browser
            self.set_splash(self.tr("Loading namespace browser..."))
            self.variableexplorer = VariableExplorer(self)
            self.extconsole.set_variableexplorer(self.variableexplorer)
            self.add_dockwidget(self.variableexplorer)

        self.extconsole.open_interpreter_at_startup()
            
        if not self.light:
            self.set_splash(self.tr("Setting up main window..."))
            # View menu
            self.view_menu = self.createPopupMenu()
            self.view_menu.setTitle(self.tr("&View"))
            add_actions(self.view_menu, (None, self.maximize_action,
                                         self.fullscreen_action))
            self.menuBar().addMenu(self.view_menu)
            
            # Tools menu
            tools_menu = self.menuBar().addMenu(self.tr("&Tools"))
            self.tools_menu_actions = []
            # Python(x,y) launcher
            self.xy_action = create_action(self,
                                       self.tr("Python(x,y) launcher"),
                                       icon=get_icon('pythonxy.png'),
                                       triggered=lambda:
                                       run_python_gui_script('xy', 'xyhome'))
            self.tools_menu_actions.append(self.xy_action)
            if not is_module_installed('xy'):
                self.xy_action.setDisabled(True)
                self.xy_action.setToolTip(self.xy_action.toolTip() + \
                                          '\nPlease install Python(x,y) to '
                                          'enable this feature')
            # Qt-related tools
            additact = [None]
            qtdact = create_program_action(self, self.tr("Qt Designer"),
                                           'qtdesigner.png', "designer")
            qtlact = create_program_action(self, self.tr("Qt Linguist"),
                                           'qtlinguist.png', "linguist")
            qteact = create_python_gui_script_action(self,
                                   self.tr("Qt examples"), 'qt.png', "PyQt4",
                                   osp.join("examples", "demos",
                                            "qtdemo", "qtdemo"))
            for act in (qtdact, qtlact, qteact):
                if act:
                    additact.append(act)
            if len(additact) > 1:
                self.tools_menu_actions += additact
                
            # ViTables
            vitables_act = create_program_action(self, self.tr("ViTables"),
                                                 'vitables.png', "vitables")
            if vitables_act:
                self.tools_menu_actions += [None, vitables_act]
                
            add_actions(tools_menu, self.tools_menu_actions)
            add_actions(main_toolbar, self.tools_menu_actions)
                    
            # ? menu
            help_menu = self.menuBar().addMenu("?")
            about_action = create_action(self,
                                    self.tr("About %1...").arg("Spyder"),
                                    icon=get_std_icon('MessageBoxInformation'),
                                    triggered=self.about)
            spyder_doc = osp.join(DOC_PATH, "Spyderdoc.chm")
            if not osp.isfile(spyder_doc):
                spyder_doc = osp.join(DOC_PATH, "index.html")
            doc_action = create_bookmark_action(self, spyder_doc,
                               self.tr("Spyder documentation"), shortcut="F1",
                               icon=get_std_icon('DialogHelpButton'))
            self.help_menu_actions = [about_action, doc_action]
            if get_python_doc_path() is not None:
                pydoc_act = create_action(self, self.tr("Python documentation"),
                                          icon=get_icon('python.png'),
                                          triggered=open_python_doc)
                self.help_menu_actions += [None, pydoc_act]
            # Qt assistant link
            qta_act = create_program_action(self, self.tr("Qt Assistant"),
                                            'qtassistant.png', "assistant")
            if qta_act:
                self.help_menu_actions.append(qta_act)
            self.help_menu_actions += create_module_bookmark_actions(self,
                                                                self.BOOKMARKS)
            add_actions(help_menu, self.help_menu_actions)
        
        # Emitting the signal notifying plugins that main window menu and 
        # toolbar actions are all defined:
        self.emit(SIGNAL('all_actions_defined'))
        
        # Window set-up
        prefix = ('lightwindow' if self.light else 'window') + '/'
        self.debug_print("Setting up window...")
        width, height = CONF.get('main', prefix+'size')
        hexstate = CONF.get('main', prefix+'state', None)
        first_spyder_execution = hexstate is None
        if first_spyder_execution and not self.light:
            # First Spyder execution:
            # trying to set-up the dockwidget/toolbar positions to the best 
            # appearance possible
            splitting = (
                         (self.projectexplorer, self.editor, Qt.Horizontal),
                         (self.editor, self.inspector, Qt.Horizontal),
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
                                  (self.findinfiles, self.pylint),
                                  ):
                if first is not None and second is not None:
                    self.tabifyDockWidget(first.dockwidget, second.dockwidget)
            for plugin in (self.pylint, self.findinfiles, self.onlinehelp,
                           self.console):
                if plugin is not None:
                    plugin.dockwidget.close()
            for plugin in (self.inspector, self.extconsole):
                if plugin is not None:
                    plugin.dockwidget.raise_()
            for toolbar in (run_toolbar, edit_toolbar):
                toolbar.close()
            self.projectexplorer.dockwidget.close()
        self.resize( QSize(width, height) )
        self.window_size = self.size()
        posx, posy = CONF.get('main', prefix+'position')
        self.move( QPoint(posx, posy) )
        
        if not self.light:
            # Window layout
            if not first_spyder_execution:
                self.restoreState( QByteArray().fromHex(str(hexstate)) )
            # Is maximized?
            if CONF.get('main', prefix+'is_maximized'):
                self.setWindowState(Qt.WindowMaximized)
            # Is fullscreen?
            if CONF.get('main', prefix+'is_fullscreen'):
                self.setWindowState(Qt.WindowFullScreen)
            self.__update_fullscreen_action()
            
        self.splash.hide()
        
        # Enabling tear off for all menus except help menu
        for child in self.menuBar().children():
            if isinstance(child, QMenu) and child != help_menu:
                child.setTearOffEnabled(True)
        
        # Menu about to show
        for child in self.menuBar().children():
            if isinstance(child, QMenu):
                self.connect(child, SIGNAL("aboutToShow()"),
                             self.update_edit_menu)
        
        self.debug_print("*** End of MainWindow setup ***")

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
            self.variableexplorer.set_shellwidget(shell.parent())
        
    def update_file_menu(self):
        """Update file menu"""
        self.load_temp_session_action.setEnabled(osp.isfile(TEMP_SESSION_PATH))
        
    def __focus_widget_properties(self):
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
        #!!! Below this line, widget is expected to be a QsciScintilla
        #    or QPlainTextEdit instance
        console, not_readonly, readwrite_editor = textedit_properties
        
        # Editor has focus and there is no file opened in it
        if not console and not_readonly and not self.editor.is_file_opened():
            return
        
        self.selectall_action.setEnabled(True)
        
        # Undo, redo
        self.undo_action.setEnabled( readwrite_editor \
                                     and widget.isUndoAvailable() )
        self.redo_action.setEnabled( readwrite_editor \
                                     and widget.isRedoAvailable() )

        # Copy, cut, paste, delete
        has_selection = widget.hasSelectedText()
        self.copy_action.setEnabled(has_selection)
        self.cut_action.setEnabled(has_selection and not_readonly)
        self.paste_action.setEnabled(not_readonly)
        self.delete_action.setEnabled(has_selection and not_readonly)
        
    def update_search_menu(self):
        """Update search menu"""
        if self.menuBar().hasFocus():
            return        
        # Disabling all actions to begin with
        for child in [self.find_action, self.find_next_action,
                      self.replace_action]:
            child.setEnabled(False)
        
        _, textedit_properties = self.__focus_widget_properties()
        if textedit_properties is None: # widget is not an editor/console
            return
        #!!! Below this line, widget is expected to be a QsciScintilla instance
        _, _, readwrite_editor = textedit_properties
        self.find_action.setEnabled(True)
        self.find_next_action.setEnabled(True)
        self.replace_action.setEnabled(readwrite_editor)
        self.replace_action.setEnabled(readwrite_editor)
        
    def set_splash(self, message):
        """Set splash message"""
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
        
    def closing(self, cancelable=False):
        """Exit tasks"""
        if self.already_closed:
            return True
        size = self.window_size
        prefix = ('lightwindow' if self.light else 'window') + '/'
        CONF.set('main', prefix+'size', (size.width(), size.height()))
        CONF.set('main', prefix+'is_maximized', self.isMaximized())
        CONF.set('main', prefix+'is_fullscreen', self.isFullScreen())
        pos = self.pos()
        CONF.set('main', prefix+'position', (pos.x(), pos.y()))
        if not self.light:
            self.maximize_dockwidget(restore=True)# Restore non-maximized layout
            qba = self.saveState()
            CONF.set('main', prefix+'state', str(qba.toHex()))
            CONF.set('main', prefix+'statusbar',
                     not self.statusBar().isHidden())
        for widget in self.widgetlist:
            if not widget.closing_plugin(cancelable):
                return False
        self.already_closed = True
        return True
        
    def add_dockwidget(self, child):
        """Add QDockWidget and toggleViewAction"""
        dockwidget, location = child.create_dockwidget()
        self.addDockWidget(location, dockwidget)
        self.widgetlist.append(child)
        
    def __update_maximize_action(self):
        if self.last_window_state is None:
            text = self.tr("Maximize current plugin")
            tip = self.tr("Maximize current plugin to fit the whole "
                          "application window")
            icon = "maximize.png"
        else:
            text = self.tr("Restore current plugin")
            tip = self.tr("Restore current plugin to its original size and "
                          "position within the application window")
            icon = "unmaximize.png"
        self.maximize_action.setText(text)
        self.maximize_action.setIcon(get_icon(icon))
        self.maximize_action.setToolTip(tip)
        
    def maximize_dockwidget(self, restore=False):
        """
        Shortcut: Ctrl+Alt+Shift+M
        First call: maximize current dockwidget
        Second call (or restore=True): restore original window layout
        """
        if self.last_window_state is None:
            if restore:
                return
            # No plugin is currently maximized: maximizing focus plugin
            self.last_window_state = self.saveState()
            focus_widget = QApplication.focusWidget()
            for plugin in self.widgetlist:
                plugin.dockwidget.hide()
                if plugin.isAncestorOf(focus_widget):
                    self.last_plugin = plugin
            self.last_plugin.dockwidget.toggleViewAction().setDisabled(True)
            self.setCentralWidget(self.last_plugin)
            self.last_plugin.ismaximized = True
            # Workaround to solve an issue with editor's class browser:
            # (otherwise the whole plugin is hidden and so is the class browser
            #  and the latter won't be refreshed if not visible)
            self.last_plugin.show()
            self.last_plugin.visibility_changed(True)
        else:
            # Restore original layout (before maximizing current dockwidget)
            self.last_plugin.dockwidget.setWidget(self.last_plugin)
            self.last_plugin.dockwidget.toggleViewAction().setEnabled(True)
            self.setCentralWidget(None)
            self.last_plugin.ismaximized = False
            self.restoreState(self.last_window_state)
            self.last_window_state = None
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
        else:
            self.fullscreen_flag = True
            self.showFullScreen()
        self.__update_fullscreen_action()
    
    def add_to_menubar(self, widget, title=None, existing_menu=None):
        """Add menu and actions to menubar"""
        actions = widget.menu_actions
        if actions is not None:
            if not title:
                title = widget.get_plugin_title()
            if existing_menu is None:
                menu = self.menuBar().addMenu(title)
                add_actions(menu, actions)
                return menu
            else:
                first_action = existing_menu.actions()[0]
                add_actions(existing_menu, actions+(None,),
                            insert_before=first_action)

    def add_to_toolbar(self, toolbar, widget):
        """Add widget actions to toolbar"""
        actions = widget.toolbar_actions
        if actions is not None:
            add_actions(toolbar, actions)
        
    def about(self):
        """About Spyder"""
        try:
            from PyQt4.Qsci import QSCINTILLA_VERSION_STR as qsci
            qsci = ", QScintilla "+ qsci
            qsci_not_installed = ''
        except ImportError:
            qsci = ""
            qsci_not_installed = self.tr(' (QScintilla is not installed)')
        try:
            from pyflakes import __version__ as pyflakes_version
        except ImportError:
            pyflakes_version = self.tr('(not installed)')
        QMessageBox.about(self,
            self.tr("About %1").arg("Spyder"),
            self.tr("""<b>%1 %2</b>
            <br>Scientific PYthon Development EnviRonment
            <p>Copyright &copy; 2009 Pierre Raybaut
            <br>Licensed under the terms of the MIT License
            <p>Developed and maintained by %8Pierre Raybaut%9
            <p>Many thanks to %8Christopher Brown%9 (beta-tester from the 
            very beginning), 
            %8Alexandre Radicchi%9 (especially for his contributions to the 
            <i>Workspace</i> plugin and the <i>DictEditor</i> widget), 
            %8Ludovic Aubry%9 (for his great ideas, suggestions and 
            technical solutions - without him, the <i>external console</i> 
            wouldn't have so many features)
            and all the Spyder beta-testers and regular users.
            <p>Integrated Python code analysis powered by %8pyflakes %10%9:
            <br>Copyright (c) 2005 Divmod, Inc., http://www.divmod.com/
            <p>Most of the icons are coming from the %8Crystal Project%9:
            <br>Copyright &copy; 2006-2007 Everaldo Coelho
            <p>Spyder is based on spyderlib module v%2
            <br>Bug reports and feature requests: 
            <a href="http://spyderlib.googlecode.com">Google Code</a><br>
            Discussions around the project: 
            <a href="http://groups.google.com/group/spyderlib">Google Group</a>
            <p>This project is part of 
            <a href="http://www.pythonxy.com">Python(x,y) distribution</a>
            <p>Python %3, Qt %4, PyQt %5%6 on %7%11""") \
            .arg("Spyder").arg(__version__) \
            .arg(platform.python_version()).arg(QT_VERSION_STR) \
            .arg(PYQT_VERSION_STR).arg(qsci).arg(platform.system()) \
            .arg("<span style=\'color: #444444\'><b>").arg("</b></span>") \
            .arg(pyflakes_version).arg(qsci_not_installed))
    
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
        if widget is self.console.shell:
            plugin = self.console
        elif widget is self.inspector.editor:
            plugin = self.inspector
        elif widget in self.historylog.editors:
            plugin = self.historylog
        elif isinstance(widget, ShellBaseWidget):
            plugin = self.extconsole
        else:
            # Editor plugin
            plugin = self.editor
            if not plugin.isAncestorOf(widget):
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
        
    def replace(self):
        """Global replace callback"""
        plugin = self.find()
        if plugin is not None:
            plugin.find_widget.show_replace()
            
    def findinfiles_callback(self):
        """Find in files callback"""
        widget = QApplication.focusWidget()
        if not self.findinfiles.ismaximized:
            self.findinfiles.dockwidget.setVisible(True)
            self.findinfiles.dockwidget.raise_()
        text = ''
        from spyderlib.widgets.editor import TextEditBaseWidget
        if isinstance(widget, TextEditBaseWidget):
            if widget.hasSelectedText():
                text = widget.selectedText()
        self.emit(SIGNAL('find_files(QString)'), text)
    
    def global_callback(self):
        """Global callback"""
        widget = QApplication.focusWidget()
        action = self.sender()
        callback = unicode(action.data().toString())
        from spyderlib.widgets.editor import TextEditBaseWidget
        if isinstance(widget, TextEditBaseWidget):
            getattr(widget, callback)()
        
    def redirect_internalshell_stdio(self, state):
        if state:
            self.console.shell.interpreter.redirect_stds()
        else:
            self.console.shell.interpreter.restore_stds()
        
    def open_external_console(self, fname, wdir,
                              ask_for_arguments, interact, debug, python):
        """Open external console"""
        self.extconsole.setVisible(True)
        self.extconsole.raise_()
        if fname is not None:
            fname = unicode(fname)
        self.extconsole.start(fname, wdir,
                              ask_for_arguments, interact, debug, python)
        
    def execute_python_code_in_external_console(self, lines):
        """Execute lines in external console"""
        self.extconsole.setVisible(True)
        self.extconsole.raise_()
        self.extconsole.execute_python_code(lines)
        
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
        
    def pythonpath_changed(self):
        """Project Explorer PYTHONPATH contribution has changed"""
        self.remove_path_from_sys_path()
        self.project_path = self.projectexplorer.get_pythonpath()
        self.add_path_to_sys_path()
    
    def win_env(self):
        """Show Windows current user environment variables"""
        dlg = WinUserEnvDialog(self)
        dlg.exec_()
        
    def load_session(self, filename=None):
        """Load session"""
        if filename is None:
            self.redirect_internalshell_stdio(False)
            filename = QFileDialog.getOpenFileName(self,
                                  self.tr("Open session"), os.getcwdu(),
                                  self.tr("Spyder sessions")+" (*.session.tar)")
            self.redirect_internalshell_stdio(True)
            if filename:
                filename = unicode(filename)
            else:
                return
        if self.close():
            self.next_session_name = filename
    
    def save_session(self):
        """Save session and quit application"""
        self.redirect_internalshell_stdio(False)
        filename = QFileDialog.getSaveFileName(self,
                                  self.tr("Save session"), os.getcwdu(),
                                  self.tr("Spyder sessions")+" (*.session.tar)")
        self.redirect_internalshell_stdio(True)
        if filename:
            if self.close():
                self.save_session_name = unicode(filename)

        
def get_options():
    """
    Convert options into commands
    return commands, message
    """
    import optparse
    parser = optparse.OptionParser("Spyder")
    parser.add_option('-l', '--light', dest="light", action='store_true',
                      default=False,
                      help="Light version (all add-ons are disabled)")
    parser.add_option('--session', dest="startup_session", default='',
                      help="Startup session")
    parser.add_option('--reset', dest="reset_session",
                      action='store_true', default=False,
                      help="Reset to default session")
    parser.add_option('-d', '--debug', dest="debug", action='store_true',
                      default=False,
                      help="Debug mode (stds are not redirected)")
    parser.add_option('--onethread', dest="multithreaded",
                      action='store_false', default=True,
                      help="Internal console run in the same thread as main "
                           "application")
    parser.add_option('--profile', dest="profile", action='store_true',
                      default=False,
                      help="Profile mode (internal test, "
                           "not related with Python profiling)")
    options, _args = parser.parse_args()
    return options


def initialize(debug):
    """Initialize Qt, patching sys.exit and eventually setting up ETS"""
    enable_translation = CONF.get('main', 'translation') and not debug
    app = qapplication(translate=enable_translation)
    
    #----Monkey patching PyQt4.QtGui.QApplication
    class FakeQApplication(QApplication):
        """Spyder's fake QApplication"""
        def __init__(self, args):
            self = app
        @staticmethod
        def exec_():
            """Do nothing because the Qt mainloop is already running"""
            pass
    from PyQt4 import QtGui
    QtGui.QApplication = FakeQApplication
    
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
    
    return app


def run_spyder(app, options):
    """
    Create and show Spyder's main window
    Patch matplotlib for figure integration
    Start QApplication event loop
    """
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
    main.emit(SIGNAL('restore_scrollbar_position()'))
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
    
    app = initialize(debug=options.debug)
    if options.reset_session:
        reset_session()
#        CONF.reset_to_defaults(save=True)
        return

    if CONF.get('main', 'crash', False):
        CONF.set('main', 'crash', False)
        QMessageBox.information(None, "Spyder",
                                u"Spyder crashed during last session.<br><br>"
                                u"If Spyder does not start at all, please try "
                                u"to run Spyder with the command line option "
                                u"<b>--reset</b> before submitting a bug "
                                u"report.")
        
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
        try:
            mainwindow = run_spyder(app, options)
        except BaseException:
            CONF.set('main', 'crash', True)
            import traceback
            traceback.print_exc(file=STDERR)
            traceback.print_exc(file=open('spyder_crash.log', 'wb'))            
        if mainwindow is None:
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
    original_sys_exit()

if __name__ == "__main__":
    main()
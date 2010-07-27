# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Editor Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

#TODO: Make a plugin for the class browser ?

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QMessageBox, QPrintDialog,
                         QSplitter, QToolBar, QAction, QApplication, QDialog,
                         QWidget, QPrinter, QActionGroup, QInputDialog, QMenu,
                         QFontDialog, QAbstractPrintDialog, QGroupBox,
                         QPushButton, QTabWidget)
from PyQt4.QtCore import SIGNAL, QStringList, QVariant, QByteArray, Qt

import os, sys, time, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import encoding, sourcecode
from spyderlib.config import get_conf_path, get_icon
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import (create_action, add_actions, get_std_icon,
                                       get_filetype_icon, create_toolbutton)
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.pylintgui import is_pylint_installed
from spyderlib.widgets.editortools import ClassBrowser
from spyderlib.widgets.editor import (ReadWriteStatus, EncodingStatus,
                                      CursorPositionStatus, EOLStatus,
                                      EditorSplitter, EditorStack,
                                      EditorMainWindow, CodeEditor, Printer)
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage


WINPDB_PATH = programs.get_nt_program_name('winpdb')

def is_winpdb_installed():
    return programs.is_program_installed(WINPDB_PATH)


class EditorConfigPage(PluginConfigPage):
    def setup_page(self):
        template_btn = QPushButton(self.tr("Edit template for new modules"))
        self.connect(template_btn, SIGNAL('clicked()'),
                     self.plugin.edit_template)
        
        interface_group = QGroupBox(self.tr("Interface"))
        font_btn = QPushButton(self.tr("Set text and margin font style"))
        self.connect(font_btn, SIGNAL('clicked()'),
                     self.plugin.change_font)
        newcb = self.create_checkbox
        cbvis_box = newcb(self.tr("Show class browser"),
                          'class_browser/visibility')
        fpsorting_box = newcb(self.tr("Sort files according to full path"),
                              'fullpath_sorting')
        showtabbar_box = newcb(self.tr("Show tab bar"), 'show_tab_bar')

        interface_layout = QVBoxLayout()
        interface_layout.addWidget(font_btn)
        interface_layout.addWidget(cbvis_box)
        interface_layout.addWidget(fpsorting_box)
        interface_layout.addWidget(showtabbar_box)
        interface_group.setLayout(interface_layout)

        margins_group = QGroupBox(self.tr("Margins"))
        linenumbers_box = newcb(self.tr("Show line numbers"), 'line_numbers')
        occurence_box = newcb(self.tr("Highlight occurences"),
                              'occurence_highlighting', default=True)
        codeanalysis_box = newcb(self.tr("Code analysis (pyflakes)"),
                                 'code_analysis', default=True)
        codeanalysis_box.setToolTip(self.tr("If enabled, Python source code "
                        "will be analyzed using pyflakes, lines containing "
                        "errors or warnings will be highlighted"))
        codeanalysis_box.setEnabled(programs.is_module_installed('pyflakes'))
        todolist_box = newcb(self.tr("Tasks (TODO, FIXME, XXX)"),
                             'todo_list', default=True)
        
        margins_layout = QVBoxLayout()
        margins_layout.addWidget(linenumbers_box)
        margins_layout.addWidget(occurence_box)
        margins_layout.addWidget(codeanalysis_box)
        margins_layout.addWidget(todolist_box)
        margins_group.setLayout(margins_layout)
        
        sourcecode_group = QGroupBox(self.tr("Source code"))
        completion_box = newcb(self.tr("Automatic code completion"),
                               'codecompletion/auto')
        comp_enter_box = newcb(self.tr("Enter key selects completion"),
                               'codecompletion/enter-key')
        tab_mode_box = newcb(self.tr("Tab always indent"),
                             'tab_always_indent', default=True,
                             tip=self.tr("If enabled, pressing Tab will always "
                                         "indent, even when the cursor is not "
                                         "at the beginning of a line"))
        wrap_mode_box = newcb(self.tr("Wrap lines"), 'wrap')
        check_eol_box = newcb(self.tr("Show warning when fixing newline chars"),
                              'check_eol_chars', default=True)
        
        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(completion_box)
        sourcecode_layout.addWidget(comp_enter_box)
        sourcecode_layout.addWidget(tab_mode_box)
        sourcecode_layout.addWidget(wrap_mode_box)
        sourcecode_group.setLayout(sourcecode_layout)
        
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(interface_group, sourcecode_group),
                    self.tr("Basics"))
        tabs.addTab(self.create_tab(template_btn, margins_group,
                                    check_eol_box),
                    self.tr("Advanced"))
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)


class Editor(SpyderPluginWidget):
    """
    Multi-file Editor widget
    """
    ID = 'editor'
    CONFIGWIDGET_CLASS = EditorConfigPage
    TEMPFILE_PATH = get_conf_path('.temp.py')
    TEMPLATE_PATH = get_conf_path('template.py')
    DISABLE_ACTIONS_WHEN_HIDDEN = False # SpyderPluginWidget class attribute
    def __init__(self, parent, ignore_last_opened_files=False):
        self.__set_eol_mode = True
        
        # Creating template if it doesn't already exist
        if not osp.isfile(self.TEMPLATE_PATH):
            header = ['# -*- coding: utf-8 -*-', '"""', 'Created on %(date)s',
                      '', '@author: %(username)s', '"""', '']
            encoding.write(os.linesep.join(header), self.TEMPLATE_PATH, 'utf-8')

        self.projectexplorer = None
        self.inspector = None

        self.editorstacks = None
        self.editorwindows = None
        self.editorwindows_to_be_created = None
        
        self.file_dependent_actions = []
        self.pythonfile_dependent_actions = []
        self.dock_toolbar_actions = None
        self.edit_menu_actions = None #XXX: find another way to notify Spyder
        # (see spyder.py: 'update_edit_menu' method)
        self.stack_menu_actions = None
        SpyderPluginWidget.__init__(self, parent)

        self.filetypes = ((self.tr("Python files"), ('.py', '.pyw')),
                          (self.tr("Pyrex files"), ('.pyx',)),
                          (self.tr("C files"), ('.c', '.h')),
                          (self.tr("C++ files"), ('.cc', '.cpp', '.h',
                                                  '.cxx', '.hpp', '.hh')),
                          (self.tr("Fortran files"),
                           ('.f', '.for', '.f90', '.f95', '.f2k')),
                          (self.tr("Patch and diff files"),
                           ('.patch', '.diff', '.rej')),
                          (self.tr("Batch files"),
                           ('.bat', '.cmd')),
                          (self.tr("Text files"), ('.txt',)),
                          (self.tr("reStructured Text files"), ('.txt', '.rst')),
                          (self.tr("gettext files"), ('.po', '.pot')),
                          (self.tr("Web page files"),
                           ('.css', '.htm', '.html',)),
                          (self.tr("Configuration files"),
                           ('.properties', '.session', '.ini', '.inf',
                            '.reg', '.cfg')),
                          (self.tr("All files"), ('.*',)))
        
        statusbar = self.main.statusBar()
        self.readwrite_status = ReadWriteStatus(self, statusbar)
        self.eol_status = EOLStatus(self, statusbar)
        self.encoding_status = EncodingStatus(self, statusbar)
        self.cursorpos_status = CursorPositionStatus(self, statusbar)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.dock_toolbar = QToolBar(self)
        add_actions(self.dock_toolbar, self.dock_toolbar_actions)
        layout.addWidget(self.dock_toolbar)
        
        # Class browser
        self.classbrowser = ClassBrowser(self,
           show_fullpath=self.get_option('class_browser/show_fullpath', False),
           fullpath_sorting=self.get_option('fullpath_sorting', True),
           show_all_files=self.get_option('class_browser/show_all_files', True))
        self.connect(self.classbrowser,
                     SIGNAL("edit_goto(QString,int,QString)"), self.load)
        cb_enabled = self.get_option('class_browser')
        if cb_enabled:
            cb_state = self.get_option('class_browser/visibility', False)
        else:
            cb_state = False
        self.classbrowser.visibility_action.setChecked(cb_state)
        self.classbrowser.visibility_action.setEnabled(cb_enabled)
        
        self.editorstacks = []
        self.editorwindows = []
        self.editorwindows_to_be_created = []
        self.toolbar_list = None
        self.menu_list = None
        
        # Setup new windows:
        self.connect(self.main, SIGNAL('all_actions_defined'),
                     self.setup_other_windows)
        
        # Find widget
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        
        # Tabbed editor widget + Find/Replace widget
        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        self.editorsplitter = EditorSplitter(self, self,
                                         self.stack_menu_actions, first=True)
        editor_layout.addWidget(self.editorsplitter)
        editor_layout.addWidget(self.find_widget)

        # Splitter: editor widgets (see above) + class browser
        self.splitter = QSplitter(self)
        self.splitter.addWidget(editor_widgets)
        self.splitter.addWidget(self.classbrowser)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        
        # Editor's splitter state
        state = self.get_option('splitter_state', None)
        if state is not None:
            self.splitter.restoreState( QByteArray().fromHex(str(state)) )
        
        self.recent_files = self.get_option('recent_files', [])
        
        self.untitled_num = 0

        self.last_focus_editorstack = None
                
        filenames = self.get_option('filenames', [])
        if filenames and not ignore_last_opened_files:
            self.load(filenames)
            layout = self.get_option('layout_settings', None)
            if layout is not None:
                self.editorsplitter.set_layout_settings(layout)
            win_layout = self.get_option('windows_layout_settings', None)
            if win_layout:
                for layout_settings in win_layout:
                    self.editorwindows_to_be_created.append(layout_settings)
            self.last_focus_editorstack = self.editorstacks[0]
        else:
            self.__load_temp_file()
        
        self.connect(self, SIGNAL("focus_changed()"),
                     self.save_focus_editorstack)
        
        # Parameters of last file execution:
        self.__last_ic_exec = None # internal console
        self.__last_ec_exec = None # external console
        
        # Restoring class browser state
        expanded_state = self.get_option('class_browser/expanded_state', None)
        if expanded_state is not None:
            self.classbrowser.treewidget.set_expanded_state(expanded_state)
        
    def set_projectexplorer(self, projectexplorer):
        self.projectexplorer = projectexplorer
        for editorstack in self.editorstacks:
            editorstack.set_projectexplorer(self.projectexplorer)
        
    def set_inspector(self, inspector):
        self.inspector = inspector
        for editorstack in self.editorstacks:
            editorstack.set_inspector(self.inspector)
        
    #------ Private API --------------------------------------------------------
    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        scrollbar_pos = self.get_option(
                                 'class_browser/scrollbar_position', None)
        if scrollbar_pos is not None:
            self.classbrowser.treewidget.set_scrollbar_position(scrollbar_pos)
        # Widget is now visible, we may center cursor on top level editor:
        self.get_current_editor()._center_cursor()
            
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        return self.tr('Editor')
    
    def get_plugin_icon(self):
        """Return widget icon"""
        return get_icon('edit.png')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.get_current_editor()

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        SpyderPluginWidget.visibility_changed(self, enable)
        if self.dockwidget.isWindow():
            self.dock_toolbar.show()
        else:
            self.dock_toolbar.hide()
        if enable:
            self.refresh_plugin()
    
    def refresh_plugin(self):
        """Refresh editor plugin"""
        editorstack = self.get_current_editorstack()
        editorstack.refresh()
        self.refresh_save_all_action()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        for option, value in self.classbrowser.get_options().items():
            self.set_option('class_browser/%s' % option, value)
        state = self.splitter.saveState()
        self.set_option('splitter_state', str(state.toHex()))
        filenames = []
        editorstack = self.editorstacks[0]
        filenames += [finfo.filename for finfo in editorstack.data]
        self.set_option('layout_settings',
                        self.editorsplitter.get_layout_settings())
        self.set_option('windows_layout_settings',
                    [win.get_layout_settings() for win in self.editorwindows])
        self.set_option('filenames', filenames)
        self.set_option('recent_files', self.recent_files)
        is_ok = True
        for editorstack in self.editorstacks:
            is_ok = is_ok and editorstack.save_if_changed(cancelable)
            if not is_ok and cancelable:
                break
        if is_ok:
            for win in self.editorwindows[:]:
                win.close()
        return is_ok

    def get_plugin_actions(self):
        """Setup actions"""
        self.new_action = create_action(self, self.tr("New file..."), "Ctrl+N",
            'filenew.png', self.tr("Create a new Python script"),
            triggered = self.new)
        self.open_action = create_action(self, self.tr("Open..."), "Ctrl+O",
            'fileopen.png', self.tr("Open text file"),
            triggered = self.load)
        self.save_action = create_action(self, self.tr("Save"), "Ctrl+S",
            'filesave.png', self.tr("Save current file"),
            triggered = self.save)
        self.save_all_action = create_action(self, self.tr("Save all"),
            "Ctrl+Shift+S", 'save_all.png', self.tr("Save all opened files"),
            triggered = self.save_all)
        save_as_action = create_action(self, self.tr("Save as..."), None,
            'filesaveas.png', self.tr("Save current file as..."),
            triggered = self.save_as)
        print_preview_action = create_action(self, self.tr("Print preview..."),
            tip=self.tr("Print preview..."), triggered=self.print_preview)
        print_action = create_action(self, self.tr("Print..."), None,
            'print.png', self.tr("Print current file..."),
            triggered = self.print_file)
        self.close_action = create_action(self, self.tr("Close"), "Ctrl+W",
            'fileclose.png', self.tr("Close current file"),
            triggered = self.close_file)
        self.close_all_action = create_action(self, self.tr("Close all"),
            "Ctrl+Shift+W", 'filecloseall.png',
            self.tr("Close all opened files"),
            triggered = self.close_all_files)
        
        run_new_action = create_action(self,
            self.tr("Run"), "F5", 'run_new.png',
            self.tr("Run active script in a new external console"),
            triggered=lambda: self.run_script_extconsole(current=False))
        run_interact_action = create_action(self,
            self.tr("Run and interact"), "Shift+F5", 'run.png',
            tip=self.tr("Run current script in external console and interact "
                        "\nwith Python interpreter when program has finished"),
            triggered=lambda: self.run_script_extconsole(interact=True))
        run_args_action = create_action(self,
            self.tr("Run with arguments"), "Alt+F5", 'run_args.png',
            tip=self.tr("Run current script in external console specifying "
                        "command line arguments"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.run_script_extconsole( \
                                           ask_for_arguments=True))
        run_debug_action = create_action(self,
            self.tr("Debug"), "Ctrl+Shift+F5", 'bug.png',
            tip=self.tr("Debug current script in external console"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.run_script_extconsole( \
                                           ask_for_arguments=True, debug=True))
        re_run_action = create_action(self,
            self.tr("Re-run last script"), "Ctrl+Alt+F5", 'run_again.png',
            self.tr("Run again last script in external console with the "
                    "same options"),
            triggered=self.re_run_extconsole)
        
        run_inside_action = create_action(self,
            self.tr("Run inside interpreter"), "F6", 'run.png',
            self.tr("Run active script in current external console's "
                    "interpreter"),
            triggered=lambda: self.run_script_extconsole(current=True))
        run_args_inside_action = create_action(self,
            self.tr("Run inside interpreter with arguments"), "Alt+F6",
            'run_args.png',
            tip=self.tr("Run current script in external console specifying "
                        "command line arguments"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.run_script_extconsole(current=True,
                                                        ask_for_arguments=True))
        run_selected_action = create_action(self,
            self.tr("Run &selection or current block"), "Ctrl+F6",
            'run_selection.png',
            tip=self.tr("Run selected text or current block of lines \n"
                        "inside current external console's interpreter"),
            triggered=lambda: self.run_selection_or_block(external=True))
        
        self.todo_list_action = create_action(self,
            self.tr("Show todo list"), icon='todo_list.png',
            tip=self.tr("Show TODO/FIXME/XXX comments list"),
            triggered=self.go_to_next_todo)
        self.todo_menu = QMenu(self)
        self.todo_list_action.setMenu(self.todo_menu)
        self.connect(self.todo_menu, SIGNAL("aboutToShow()"),
                     self.update_todo_menu)
        
        self.warning_list_action = create_action(self,
            self.tr("Show warning/error list"), icon='wng_list.png',
            tip=self.tr("Show code analysis warnings/errors"),
            triggered=self.go_to_next_warning)
        self.warning_menu = QMenu(self)
        self.warning_list_action.setMenu(self.warning_menu)
        self.connect(self.warning_menu, SIGNAL("aboutToShow()"),
                     self.update_warning_menu)
        self.previous_warning_action = create_action(self,
            self.tr("Previous warning/error"), icon='prev_wng.png',
            tip=self.tr("Go to previous code analysis warning/error"),
            triggered=self.go_to_previous_warning)
        self.next_warning_action = create_action(self,
            self.tr("Next warning/error"), icon='next_wng.png',
            tip=self.tr("Go to next code analysis warning/error"),
            triggered=self.go_to_next_warning)
        
        self.comment_action = create_action(self, self.tr("Comment"), "Ctrl+3",
            'comment.png', self.tr("Comment current line or selection"),
            triggered=self.comment)
        self.uncomment_action = create_action(self, self.tr("Uncomment"),
            "Ctrl+2",
            'uncomment.png', self.tr("Uncomment current line or selection"),
            triggered=self.uncomment)
        blockcomment_action = create_action(self,
            self.tr("Add block comment"), "Ctrl+4",
            tip = self.tr("Add block comment around current line or selection"),
            triggered=self.blockcomment)
        unblockcomment_action = create_action(self,
            self.tr("Remove block comment"), "Ctrl+5",
            tip = self.tr("Remove comment block around "
                          "current line or selection"),
            triggered=self.unblockcomment)
                
        # ----------------------------------------------------------------------
        # The following action shortcuts are hard-coded in CodeEditor
        # keyPressEvent handler (the shortcut is here only to inform user):
        # (context=Qt.WidgetShortcut -> disable shortcut for other widgets)
        self.indent_action = create_action(self, self.tr("Indent"), "Tab",
            'indent.png', self.tr("Indent current line or selection"),
            triggered=self.indent, context=Qt.WidgetShortcut)
        self.unindent_action = create_action(self, self.tr("Unindent"),
            "Shift+Tab",
            'unindent.png', self.tr("Unindent current line or selection"),
            triggered=self.unindent, context=Qt.WidgetShortcut)
        # ----------------------------------------------------------------------
        
        pylint_action = create_action(self, self.tr("Run pylint code analysis"),
                                      "F7", triggered=self.run_pylint)
        pylint_action.setEnabled(is_pylint_installed())
        
        self.winpdb_action = create_action(self, self.tr("Debug with winpdb"),
                                           "F8", triggered=self.run_winpdb)
        self.winpdb_action.setEnabled(is_winpdb_installed())
        
        self.win_eol_action = create_action(self,
                           self.tr("Carriage return and line feed (Windows)"),
                           toggled=lambda: self.toggle_eol_chars('nt'))
        self.linux_eol_action = create_action(self,
                           self.tr("Line feed (UNIX)"),
                           toggled=lambda: self.toggle_eol_chars('posix'))
        self.mac_eol_action = create_action(self,
                           self.tr("Carriage return (Mac)"),
                           toggled=lambda: self.toggle_eol_chars('mac'))
        eol_action_group = QActionGroup(self)
        eol_actions = (self.win_eol_action, self.linux_eol_action,
                       self.mac_eol_action)
        add_actions(eol_action_group, eol_actions)
        eol_menu = QMenu(self.tr("Convert end-of-line characters"), self)
        add_actions(eol_menu, eol_actions)
        
        trailingspaces_action = create_action(self,
                                      self.tr("Remove trailing spaces"),
                                      triggered=self.remove_trailing_spaces)
        fixindentation_action = create_action(self, self.tr("Fix indentation"),
                      tip=self.tr("Replace tab characters by space characters"),
                      triggered=self.fix_indentation)

        workdir_action = create_action(self,
                self.tr("Set console working directory"),
                icon=get_std_icon('DirOpenIcon'),
                tip=self.tr("Set current console (and file explorer) working "
                            "directory to current script directory"),
                triggered=self.__set_workdir)

        self.max_recent_action = create_action(self,
            self.tr("Maximum number of recent files..."),
            triggered=self.change_max_recent_files)
        self.clear_recent_action = create_action(self,
            self.tr("Clear this list"), tip=self.tr("Clear recent files list"),
            triggered=self.clear_recent_files)
        self.recent_file_menu = QMenu(self.tr("Open &recent"), self)
        self.connect(self.recent_file_menu, SIGNAL("aboutToShow()"),
                     self.update_recent_file_menu)

        file_menu_actions = [self.new_action, self.open_action,
                             self.recent_file_menu, self.save_action,
                             self.save_all_action, save_as_action,
                             None, print_preview_action, print_action,
                             None, self.close_action,
                             self.close_all_action, None]
        self.main.file_menu_actions += file_menu_actions
        file_toolbar_actions = [self.new_action, self.open_action,
                                self.save_action, self.save_all_action,
                                print_action]
        self.main.file_toolbar_actions += file_toolbar_actions
        
        self.edit_menu_actions = [self.comment_action, self.uncomment_action,
                                  blockcomment_action, unblockcomment_action,
                                  self.indent_action, self.unindent_action]
        self.main.edit_menu_actions += [None]+self.edit_menu_actions
        edit_toolbar_actions = [self.comment_action, self.uncomment_action,
                                self.indent_action, self.unindent_action]
        self.main.edit_toolbar_actions += edit_toolbar_actions
        
        run_menu_actions = [run_new_action, run_interact_action,
                            run_args_action, run_debug_action,
                            re_run_action, None, run_inside_action,
                            run_args_inside_action, run_selected_action]
        self.main.run_menu_actions += run_menu_actions
        run_toolbar_actions = [run_new_action, run_inside_action,
                               run_selected_action, re_run_action]
        self.main.run_toolbar_actions += run_toolbar_actions
        
        source_menu_actions = [eol_menu, trailingspaces_action,
                               fixindentation_action, None,
                               pylint_action, self.winpdb_action]
        self.main.source_menu_actions += source_menu_actions
        
        source_toolbar_actions = [self.todo_list_action,
                self.warning_list_action, self.previous_warning_action,
                self.next_warning_action]
        self.main.source_toolbar_actions += source_toolbar_actions
        
        self.dock_toolbar_actions = file_toolbar_actions + [None] + \
                                    source_toolbar_actions + [None] + \
                                    run_toolbar_actions + [None] + \
                                    edit_toolbar_actions
        self.pythonfile_dependent_actions = (run_new_action, run_inside_action,
                run_args_inside_action, re_run_action, run_interact_action,
                run_selected_action, run_args_action, run_debug_action,
                blockcomment_action, unblockcomment_action, pylint_action,
                self.winpdb_action)
        self.file_dependent_actions = self.pythonfile_dependent_actions + \
                (self.save_action, save_as_action, print_preview_action,
                 print_action, self.save_all_action, workdir_action,
                 self.close_action, self.close_all_action,
                 self.comment_action, self.uncomment_action,
                 self.indent_action, self.unindent_action)
        self.stack_menu_actions = (self.save_action, save_as_action,
                                   print_action, run_new_action,
                                   run_inside_action, workdir_action,
                                   self.close_action)
        return (source_menu_actions, self.dock_toolbar_actions)        
    
        
    #------ Focus tabwidget
    def __get_focus_editorstack(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, CodeEditor):
            for editorstack in self.editorstacks:
                if fwidget is editorstack.get_current_editor():
                    return editorstack
        elif isinstance(fwidget, EditorStack):
            return fwidget
        
    def save_focus_editorstack(self):
        editorstack = self.__get_focus_editorstack()
        if editorstack is not None:
            self.last_focus_editorstack = editorstack
    
        
    #------ Handling editorstacks
    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        
        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            editorstack.set_closable( len(self.editorstacks) > 1 )
            editorstack.set_classbrowser(self.classbrowser)
            editorstack.set_projectexplorer(self.projectexplorer)
            editorstack.set_inspector(self.inspector)
            editorstack.set_find_widget(self.find_widget)
            self.connect(editorstack, SIGNAL('reset_statusbar()'),
                         self.readwrite_status.hide)
            self.connect(editorstack, SIGNAL('reset_statusbar()'),
                         self.encoding_status.hide)
            self.connect(editorstack, SIGNAL('reset_statusbar()'),
                         self.cursorpos_status.hide)
            self.connect(editorstack, SIGNAL('readonly_changed(bool)'),
                         self.readwrite_status.readonly_changed)
            self.connect(editorstack, SIGNAL('encoding_changed(QString)'),
                         self.encoding_status.encoding_changed)
            self.connect(editorstack, SIGNAL('cursorPositionChanged(int,int)'),
                         self.cursorpos_status.cursor_position_changed)
            self.connect(editorstack, SIGNAL('refresh_eol_mode(QString)'),
                         self.eol_status.eol_changed)
            cb_btn = create_toolbutton(self, text_beside_icon=False)
            cb_btn.setDefaultAction(self.classbrowser.visibility_action)
            editorstack.add_widget_to_header(cb_btn, space_before=True)
            
        editorstack.set_io_actions(self.new_action, self.open_action,
                                   self.save_action)
        editorstack.set_tempfile_path(self.TEMPFILE_PATH)
        editorstack.set_filetype_filters(self.get_filetype_filters())
        editorstack.set_valid_types(self.get_valid_types())
        settings = (('set_codeanalysis_enabled',   'code_analysis'),
                    ('set_todolist_enabled',       'todo_list'),
                    ('set_linenumbers_enabled',    'line_numbers'),
                    ('set_classbrowser_enabled',   'class_browser'),
                    ('set_codecompletion_auto_enabled',
                                                    'codecompletion/auto'),
                    ('set_codecompletion_enter_enabled',
                                                    'codecompletion/enter-key'),
                    ('set_wrap_enabled',           'wrap'),
                    ('set_tabmode_enabled',        'tab_always_indent'),
                    ('set_occurence_highlighting_enabled',
                                                   'occurence_highlighting'),
                    ('set_checkeolchars_enabled',  'check_eol_chars'),
                    ('set_fullpath_sorting_enabled',
                                                   'fullpath_sorting'),
                    ('set_tabbar_visible',         'show_tab_bar'))
        for method, setting in settings:
            getattr(editorstack, method)(self.get_option(setting))
        editorstack.set_default_font(self.get_plugin_font())
        
        self.connect(editorstack, SIGNAL('starting_long_process(QString)'),
                     self.starting_long_process)
        self.connect(editorstack, SIGNAL('ending_long_process(QString)'),
                     self.ending_long_process)
        
        # Redirect signals
        self.connect(editorstack, SIGNAL("refresh_explorer(QString)"),
                     lambda text:
                     self.emit(SIGNAL("refresh_explorer(QString)"), text))
        self.connect(editorstack, SIGNAL('redirect_stdio(bool)'),
                     lambda state:
                     self.emit(SIGNAL('redirect_stdio(bool)'), state))
        self.connect(editorstack,
                     SIGNAL('external_console_execute_lines(QString)'),
                     lambda text:
                     self.emit(SIGNAL('external_console_execute_lines(QString)'), text))
        
        self.connect(editorstack, SIGNAL('close_file(int)'),
                     self.close_file_in_all_editorstacks)
        self.connect(editorstack, SIGNAL('file_saved(int)'),
                     self.file_saved_in_editorstack)
        
        self.connect(editorstack, SIGNAL("create_new_window()"),
                     self.create_new_window)
        
        self.last_focus_editorstack = editorstack
        self.connect(editorstack, SIGNAL('opened_files_list_changed()'),
                     self.opened_files_list_changed)
        self.connect(editorstack, SIGNAL('analysis_results_changed()'),
                     self.analysis_results_changed)
        self.connect(editorstack, SIGNAL('todo_results_changed()'),
                     self.todo_results_changed)
        self.connect(editorstack, SIGNAL('update_code_analysis_actions()'),
                     self.update_code_analysis_actions)
        self.connect(editorstack, SIGNAL('update_code_analysis_actions()'),
                     self.update_todo_actions)
        self.connect(editorstack,
                     SIGNAL('refresh_file_dependent_actions()'),
                     self.refresh_file_dependent_actions)
        self.connect(editorstack, SIGNAL('refresh_save_all_action()'),
                     self.refresh_save_all_action)
        self.connect(editorstack, SIGNAL('refresh_eol_mode(QString)'),
                     self.refresh_eol_mode)
        
        self.connect(editorstack, SIGNAL('plugin_load(QString)'), self.load)
        self.connect(editorstack, SIGNAL("edit_goto(QString,int,QString)"),
                     self.load)
        
        if self.main.inspector is not None:
            self.connect(editorstack, SIGNAL("inspector_show_help(QString)"),
                         self.main.inspector.show_help)
        
    def unregister_editorstack(self, editorstack):
        """Removing editorstack only if it's not the last remaining"""
        if self.last_focus_editorstack is editorstack:
            self.last_focus_editorstack = None
        if len(self.editorstacks) > 1:
            index = self.editorstacks.index(editorstack)
            self.editorstacks.pop(index)
            return True
        else:
            # editorstack was not removed!
            return False
        
    def clone_editorstack(self, editorstack):
        editorstack.clone_from(self.editorstacks[0])
        
    def __get_editorstack_from_id(self, t_id):
        for editorstack in self.editorstacks:
            if id(editorstack) == t_id:
                return editorstack
            
    def close_file_in_all_editorstacks(self, index):
        sender = self.sender()
        for editorstack in self.editorstacks:
            if editorstack is not sender:
                editorstack.blockSignals(True)
                editorstack.close_file(index)
                editorstack.blockSignals(False)
                
    def file_saved_in_editorstack(self, index):
        """A file was saved in editorstack, this notifies others"""
        sender = self.sender()
        for editorstack in self.editorstacks:
            if editorstack is not sender:
                editorstack.file_saved_in_other_editorstack(index)
        
        
    #------ Handling editor windows    
    def setup_other_windows(self):
        """Setup toolbars and menus for 'New window' instances"""
        self.toolbar_list = (
            (self.tr("File toolbar"), self.main.file_toolbar_actions),
            (self.tr("Search toolbar"), self.main.search_menu_actions),
            (self.tr("Source toolbar"), self.main.source_toolbar_actions),
            (self.tr("Run toolbar"), self.main.run_toolbar_actions),
            (self.tr("Edit toolbar"), self.main.edit_toolbar_actions),
                             )
        self.menu_list = (
                          (self.tr("&File"), self.main.file_menu_actions),
                          (self.tr("&Edit"), self.main.edit_menu_actions),
                          (self.tr("&Search"), self.main.search_menu_actions),
                          (self.tr("&Source"), self.main.source_menu_actions),
                          (self.tr("&Tools"), self.main.tools_menu_actions),
                          (self.tr("?"), self.main.help_menu_actions),
                          )
        # Create pending new windows:
        for layout_settings in self.editorwindows_to_be_created:
            win = self.create_new_window()
            win.set_layout_settings(layout_settings)
        
    def create_new_window(self):
        window = EditorMainWindow(self, self.stack_menu_actions,
           self.toolbar_list, self.menu_list,
           show_fullpath=self.get_option('class_browser/show_fullpath', False),
           fullpath_sorting=self.get_option('fullpath_sorting', True),
           show_all_files=self.get_option('class_browser/show_all_files', True))
        window.resize(self.size())
        window.show()
        self.register_editorwindow(window)
        self.connect(window, SIGNAL("destroyed()"),
                     lambda win=window: self.unregister_editorwindow(win))
        return window
    
    def register_editorwindow(self, window):
        self.editorwindows.append(window)
        
    def unregister_editorwindow(self, window):
        self.editorwindows.pop(self.editorwindows.index(window))
    
        
    #------ Accessors
    def get_filetype_filters(self):
        filters = []
        for title, ftypes in self.filetypes:
            filters.append("%s (*%s)" % (title, " *".join(ftypes)))
        return "\n".join(filters)

    def get_valid_types(self):
        ftype_list = []
        for _title, ftypes in self.filetypes:
            ftype_list += list(ftypes)
        return ftype_list

    def get_filenames(self):
        return [finfo.filename for finfo in self.editorstacks[0].data]

    def get_filename_index(self, filename):
        return self.editorstacks[0].has_filename(filename)

    def get_current_editorstack(self):
        if len(self.editorstacks) == 1:
            return self.editorstacks[0]
        else:
            editorstack = self.__get_focus_editorstack()
            if editorstack is None:
                return self.last_focus_editorstack
            else:
                return editorstack
        
    def get_current_editor(self):
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            return editorstack.get_current_editor()
        
    def get_current_finfo(self):
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            return editorstack.get_current_finfo()
        
    def get_current_filename(self):
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            return editorstack.get_current_filename()
        
    def is_file_opened(self, filename=None):
        return self.editorstacks[0].is_file_opened(filename)
        
    def set_current_filename(self, filename):
        """Set focus to *filename* if this file has been opened
        Return the editor instance associated to *filename*"""
        editorstack = self.get_current_editorstack()
        return editorstack.set_current_filename(filename)
    
    
    #------ Refresh methods
    def refresh_file_dependent_actions(self):
        """Enable/disable file dependent actions
        (only if dockwidget is visible)"""
        if self.dockwidget and self.dockwidget.isVisible():
            enable = self.get_current_editor() is not None
            for action in self.file_dependent_actions:
                action.setEnabled(enable)
                
    def refresh_save_all_action(self):
        state = False
        editorstack = self.editorstacks[0]
        if editorstack.get_stack_count() > 1:
            state = state or any([finfo.editor.isModified()
                                  for finfo in editorstack.data])
        self.save_all_action.setEnabled(state)
            
    def update_warning_menu(self):
        """Update warning list menu"""
        editorstack = self.get_current_editorstack()
        check_results = editorstack.get_analysis_results()
        self.warning_menu.clear()
        for message, line0, error in check_results:
            text = message[:1].upper()+message[1:]
            icon = get_icon('error.png' if error else 'warning.png')
            slot = lambda _l=line0: self.get_current_editor().go_to_line(_l)
            action = create_action(self, text=text, icon=icon, triggered=slot)
            self.warning_menu.addAction(action)
            
    def analysis_results_changed(self):
        """
        Synchronize analysis results between editorstacks
        Refresh analysis navigation buttons
        """
        editorstack = self.get_current_editorstack()
        results = editorstack.get_analysis_results()
        index = editorstack.get_stack_index()
        if index != -1:
            for other_editorstack in self.editorstacks:
                if other_editorstack is not editorstack:
                    other_editorstack.set_analysis_results(index, results)
        self.update_code_analysis_actions()
            
    def update_todo_menu(self):
        """Update todo list menu"""
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        self.todo_menu.clear()
        for text, line0 in results:
            icon = get_icon('todo.png')
            slot = lambda _l=line0: self.get_current_editor().go_to_line(_l)
            action = create_action(self, text=text, icon=icon, triggered=slot)
            self.todo_menu.addAction(action)
        self.update_todo_actions()
            
    def todo_results_changed(self):
        """
        Synchronize todo results between editorstacks
        Refresh todo list navigation buttons
        """
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        index = editorstack.get_stack_index()
        if index != -1:
            for other_editorstack in self.editorstacks:
                if other_editorstack is not editorstack:
                    other_editorstack.set_todo_results(index, results)
        self.update_todo_actions()
            
    def refresh_eol_mode(self, os_name):
        os_name = unicode(os_name)
        self.__set_eol_mode = False
        if os_name == 'nt':
            self.win_eol_action.setChecked(True)
        elif os_name == 'posix':
            self.linux_eol_action.setChecked(True)
        else:
            self.mac_eol_action.setChecked(True)
        self.__set_eol_mode = True
    
    
    #------ Slots
    def opened_files_list_changed(self):
        """
        Opened files list has changed:
        --> open/close file action
        --> modification ('*' added to title)
        --> current edited file has changed
        """
        # Refresh Python file dependent actions:
        editor = self.get_current_editor()
        if editor:
            enable = editor.is_python()
            for action in self.pythonfile_dependent_actions:
                if action is self.winpdb_action:
                    enable = enable and is_winpdb_installed()
                action.setEnabled(enable)
                
    def update_code_analysis_actions(self):
        editorstack = self.get_current_editorstack()
        results = editorstack.get_analysis_results()
        
        # Update code analysis buttons
        state = self.get_option('code_analysis') \
                and results is not None and len(results)
        for action in (self.warning_list_action, self.previous_warning_action,
                       self.next_warning_action):
            action.setEnabled(state)
            
    def update_todo_actions(self):
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        state = self.get_option('todo_list') \
                and results is not None and len(results)
        self.todo_list_action.setEnabled(state)
        
                
    #------ File I/O
    def __load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if not osp.isfile(self.TEMPFILE_PATH):
            # Creating temporary file
            default = ['# -*- coding: utf-8 -*-',
                       '"""', self.tr("Spyder Editor"), '',
                       self.tr("This temporary script file is located here:"),
                       self.TEMPFILE_PATH,
                       '"""', '', '']
            text = os.linesep.join([encoding.to_unicode(qstr)
                                    for qstr in default])
            encoding.write(unicode(text), self.TEMPFILE_PATH, 'utf-8')
        self.load(self.TEMPFILE_PATH)

    def __set_workdir(self):
        """Set current script directory as working directory"""
        fname = self.get_current_filename()
        if fname is not None:
            directory = osp.dirname(osp.abspath(fname))
            self.emit(SIGNAL("open_dir(QString)"), directory)
                
    def __add_recent_file(self, fname):
        """Add to recent file list"""
        if fname is None:
            return
        if not fname in self.recent_files:
            self.recent_files.insert(0, fname)
            if len(self.recent_files) > self.get_option('max_recent_files'):
                self.recent_files.pop(-1)
    
    def new(self, fname=None, editorstack=None):
        """
        Create a new file - Untitled
        
        fname=None --> fname will be 'untitledXX.py' but do not create file
        fname=<basestring> --> create file
        """
        # Creating template
        text, enc = encoding.read(self.TEMPLATE_PATH)
        encoding_match = re.search('-*- coding: ?([a-z0-9A-Z\-]*) -*-', text)
        if encoding_match:
            enc = encoding_match.group(1)
        try:
            text = text % {'date': time.ctime(),
                           'username': os.environ.get('USERNAME', '-')}
        except:
            pass
        create_fname = lambda n: unicode(self.tr("untitled")) + ("%d.py" % n)
        # Creating editor widget
        if editorstack is None:
            editorstack = self.get_current_editorstack()
        if fname is None:
            while True:
                fname = create_fname(self.untitled_num)
                self.untitled_num += 1
                if not osp.isfile(fname):
                    break
            editorstack.new(fname, enc, text)
        else:
            # QString when triggered by a Qt signal
            fname = osp.abspath(unicode(fname))
            index = editorstack.has_filename(fname)
            if index and not editorstack.close_file(index):
                return
            editorstack.new(osp.abspath(fname), enc, text)
            editorstack.save(force=True)
                
    def edit_template(self):
        """Edit new file template"""
        self.load(self.TEMPLATE_PATH)
        
    def update_recent_file_menu(self):
        """Update recent file menu"""
        recent_files = []
        for fname in self.recent_files:
            if not self.is_file_opened(fname) and osp.isfile(fname):
                recent_files.append(fname)
        self.recent_file_menu.clear()
        if recent_files:
            for i, fname in enumerate(recent_files):
                if i < 10:
                    accel = "%d" % ((i+1) % 10)
                else:
                    accel = chr(i-10+ord('a'))
                action = create_action(self, "&%s %s" % (accel, fname),
                                       icon=get_filetype_icon(fname),
                                       triggered=self.load)
                action.setData(QVariant(fname))
                self.recent_file_menu.addAction(action)
        self.clear_recent_action.setEnabled(len(recent_files) > 0)
        add_actions(self.recent_file_menu, (None, self.max_recent_action,
                                            self.clear_recent_action))
        
    def clear_recent_files(self):
        """Clear recent files list"""
        self.recent_files = []
        
    def change_max_recent_files(self):
        "Change max recent files entries"""
        editorstack = self.get_current_editorstack()
        mrf, valid = QInputDialog.getInteger(editorstack, self.tr('Editor'),
                               self.tr('Maximum number of recent files'),
                               self.get_option('max_recent_files'), 1, 100)
        if valid:
            self.set_option('max_recent_files', mrf)
        
    def load(self, filenames=None, goto=None, word=''):
        """Load a text file"""
        if not filenames:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filenames = unicode(action.data().toString())
        if not filenames:
            basedir = os.getcwdu()
            fname = self.get_current_filename()
            if fname is not None and fname != self.TEMPFILE_PATH:
                basedir = osp.dirname(fname)
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            editorstack = self.get_current_editorstack()
            filenames = QFileDialog.getOpenFileNames(editorstack,
                     self.tr("Open file"), basedir, self.get_filetype_filters())
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            filenames = list(filenames)
            if len(filenames):
                filenames = [osp.normpath(unicode(fname)) \
                             for fname in filenames]
            else:
                return
            
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        
        if not isinstance(filenames, (list, QStringList)):
            filenames = [osp.abspath(encoding.to_unicode(filenames))]
        else:
            filenames = [osp.abspath(encoding.to_unicode(fname)) \
                         for fname in list(filenames)]
        if isinstance(goto, int):
            goto = [goto]
        elif goto is not None and len(goto) != len(filenames):
            goto = None
            
        for index, filename in enumerate(filenames):
            # -- Do not open an already opened file
            current_editor = self.set_current_filename(filename)
            new_editors = []
            if current_editor is None:
                # -- Not a valid filename:
                if not osp.isfile(filename):
                    continue
                # --
                current = self.get_current_editorstack()
                for editorstack in self.editorstacks:
                    is_current = editorstack is current
                    editor = editorstack.load(filename, set_current=is_current)
                    if is_current:
                        current_editor = editor
                    new_editors.append(editor)
                current.analyze_script() # Analyze script only once (and update
                # all other editor instances in other editorstacks)
                self.__add_recent_file(filename)
            if goto is not None: # 'word' is assumed to be None as well
                current_editor.go_to_line(goto[index], word=word)
            current_editor.clearFocus()
            current_editor.setFocus()
            current_editor.window().raise_()
            QApplication.processEvents()

    def print_file(self):
        """Print current file"""
        editor = self.get_current_editor()
        filename = self.get_current_filename()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=self.get_plugin_font('printer_header'))
        printDialog = QPrintDialog(printer, editor)
        if editor.hasSelectedText():
            printDialog.addEnabledOption(QAbstractPrintDialog.PrintSelection)
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        answer = printDialog.exec_()
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if answer == QDialog.Accepted:
            self.starting_long_process(self.tr("Printing..."))
            printer.setDocName(filename)
            from PyQt4.QtGui import QPlainTextEdit
            if isinstance(editor, QPlainTextEdit):
                editor.print_(printer)
                ok = True
            else:
                if printDialog.printRange() == QAbstractPrintDialog.Selection:
                    from_line, _index, to_line, to_index = editor.getSelection()
                    if to_index == 0:
                        to_line -= 1
                    ok = printer.printRange(editor, from_line, to_line-1)
                else:
                    ok = printer.printRange(editor)
            self.ending_long_process()
            if not ok:
                QMessageBox.critical(editor, self.tr("Print"),
                            self.tr("<b>Unable to print document '%1'</b>") \
                            .arg(osp.basename(filename)))

    def print_preview(self):
        """Print preview for current file"""
        from PyQt4.QtGui import QPrintPreviewDialog
        editor = self.get_current_editor()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=self.get_plugin_font('printer_header'))
        preview = QPrintPreviewDialog(printer, self)
        self.connect(preview, SIGNAL("paintRequested(QPrinter*)"),
                     lambda printer: printer.printRange(editor))
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        preview.exec_()
        self.emit(SIGNAL('redirect_stdio(bool)'), True)

    def close_file(self):
        """Close current file"""
        editorstack = self.get_current_editorstack()
        editorstack.close_file()
            
    def close_all_files(self):
        """Close all opened scripts"""
        self.editorstacks[0].close_all_files()
                
    def save(self, index=None, force=False):
        """Save file"""
        editorstack = self.get_current_editorstack()
        return editorstack.save(index=index, force=force)
                
    def save_as(self):
        """Save *as* the currently edited file"""
        editorstack = self.get_current_editorstack()
        editorstack.save_as()
        self.__add_recent_file(editorstack.get_current_filename())
        
    def save_all(self):
        """Save all opened files"""
        self.editorstacks[0].save_all()
    
    
    #------ Explorer widget
    def __close(self, filename):
        filename = osp.abspath(unicode(filename))
        index = self.editorstacks[0].has_filename(filename)
        if index is not None:
            self.editorstacks[0].close_file(index)
                
    def removed(self, filename):
        """File was removed in file explorer widget or in project explorer"""
        self.__close(filename)
    
    def removed_tree(self, dirname):
        """Directory was removed in project explorer widget"""
        dirname = osp.abspath(unicode(dirname))
        for fname in self.get_filenames():
            if osp.abspath(fname).startswith(dirname):
                self.__close(fname)
    
    def renamed(self, source, dest):
        """File was renamed in file explorer widget or in project explorer"""
        filename = osp.abspath(unicode(source))
        index = self.editorstacks[0].has_filename(filename)
        if index is not None:
            for editorstack in self.editorstacks:
                editorstack.rename_in_data(index, new_filename=unicode(dest))
        
    
    #------ Source code
    def indent(self):
        """Indent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.indent()

    def unindent(self):
        """Unindent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unindent()
    
    def comment(self):
        """Comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.comment()

    def uncomment(self):
        """Uncomment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.uncomment()
    
    def blockcomment(self):
        """Block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.blockcomment()

    def unblockcomment(self):
        """Un-block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unblockcomment()
    
    def go_to_next_todo(self):
        editor = self.get_current_editor()
        editor.go_to_next_todo()
    
    def go_to_next_warning(self):
        editor = self.get_current_editor()
        editor.go_to_next_warning()
    
    def go_to_previous_warning(self):
        editor = self.get_current_editor()
        editor.go_to_previous_warning()
            
    def run_pylint(self):
        """Run pylint code analysis"""
        fname = self.get_current_filename()
        self.emit(SIGNAL('run_pylint(QString)'), fname)
        
    def run_winpdb(self):
        """Run winpdb to debug current file"""
        if self.save():
            fname = self.get_current_filename()
            programs.run_program(WINPDB_PATH, fname)
        
    def toggle_eol_chars(self, os_name):
        editor = self.get_current_editor()
        if self.__set_eol_mode:
            editor.set_eol_mode(sourcecode.get_eol_chars_from_os_name(os_name))
        
    def remove_trailing_spaces(self):
        editorstack = self.get_current_editorstack()
        editorstack.remove_trailing_spaces()
        
    def fix_indentation(self):
        editorstack = self.get_current_editorstack()
        editorstack.fix_indentation()
        
    #------ Run Python script
    def run_script_extconsole(self, ask_for_arguments=False,
                              interact=False, debug=False, current=False):
        """Run current script in another process"""
        editorstack = self.get_current_editorstack()
        if editorstack.save():
            editor = self.get_current_editor()
            fname = osp.abspath(self.get_current_filename())
            wdir = osp.dirname(fname)
            python = True # Note: in the future, it may be useful to run
            # something in a terminal instead of a Python interp.
            self.__last_ec_exec = (fname, wdir, ask_for_arguments,
                                   interact, debug, python, current)
            self.re_run_extconsole()
            if not interact and not debug:
                # If external console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # current external shell automatically
                # (see SpyderPluginWidget.visibility_changed method)
                editor.setFocus()
                
    def re_run_extconsole(self):
        """Re-run script in external console"""
        if self.__last_ec_exec is None:
            return
        (fname, wdir, ask_for_arguments,
         interact, debug, python, current) = self.__last_ec_exec
        if current:
            self.emit(SIGNAL('run_script_in_external_console(QString,bool)'),
                      fname, ask_for_arguments)
        else:
            self.emit(SIGNAL('open_external_console(QString,QString,bool,bool,bool,bool)'),
                      fname, wdir, ask_for_arguments, interact, debug, python)

    def run_selection_or_block(self):
        """Run selection or current line in external console"""
        editorstack = self.get_current_editorstack()
        editorstack.run_selection_or_block()
        
        
    #------ Options
    def change_font(self):
        """Change editor font"""
        editorstack = self.get_current_editorstack()
        font, valid = QFontDialog.getFont(self.get_plugin_font(), editorstack,
                                          self.tr("Select a new font"))
        if valid:
            for editorstack in self.editorstacks:
                editorstack.set_default_font(font)
            self.set_plugin_font(font)
            
    def apply_plugin_settings(self):
        """Apply configuration file's plugin settings"""
        # toggle_classbrowser_visibility
        checked = self.get_option('class_browser/visibility')
        self.classbrowser.setVisible(checked)
        if checked:
            self.classbrowser.update()
            editorstack = self.get_current_editorstack()
            editorstack._refresh_classbrowser(update=True)
        # toggle_fullpath_sorting
        checked = self.get_option('fullpath_sorting')
        if self.editorstacks is not None:
            if self.classbrowser is not None:
                self.classbrowser.set_fullpath_sorting(checked)
            for window in self.editorwindows:
                window.editorwidget.classbrowser.set_fullpath_sorting(checked)
            for editorstack in self.editorstacks:
                editorstack.set_fullpath_sorting_enabled(checked)
        # toggle_tabbar_visibility
        checked = self.get_option('show_tab_bar')
        if self.editorstacks is not None:
            for editorstack in self.editorstacks:
                editorstack.set_tabbar_visible(checked)
        # toggle_linenumbers
        checked = self.get_option('line_numbers')
        if self.editorstacks is not None:
            finfo = self.get_current_finfo()
            for editorstack in self.editorstacks:
                editorstack.set_linenumbers_enabled(checked,
                                                    current_finfo=finfo)
        # toggle_occurence_highlighting
        checked = self.get_option('occurence_highlighting')
        if self.editorstacks is not None:
            for editorstack in self.editorstacks:
                editorstack.set_occurence_highlighting_enabled(checked)
        # toggle_todo_list
        checked = self.get_option('todo_list')
        if self.editorstacks is not None:
            finfo = self.get_current_finfo()
            for editorstack in self.editorstacks:
                editorstack.set_todolist_enabled(checked,
                                                 current_finfo=finfo)
            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            if checked:
                finfo.run_todo_finder()
        # toggle_code_analysis
        checked = self.get_option('code_analysis')
        if self.editorstacks is not None:
            finfo = self.get_current_finfo()
            for editorstack in self.editorstacks:
                editorstack.set_codeanalysis_enabled(checked,
                                                     current_finfo=finfo)
            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            if checked:
                finfo.run_code_analysis()
        # toggle_wrap_mode
        checked = self.get_option('wrap')
        if self.editorstacks is not None:
            for editorstack in self.editorstacks:
                editorstack.set_wrap_enabled(checked)
        # toggle_tab_mode
        checked = self.get_option('tab_always_indent')
        if self.editorstacks is not None:
            for editorstack in self.editorstacks:
                editorstack.set_tabmode_enabled(checked)
        # toggle_codecompletion
        checked = self.get_option('codecompletion/auto')
        if self.editorstacks is not None:
            for editorstack in self.editorstacks:
                editorstack.set_codecompletion_auto_enabled(checked)
        # toggle_codecompletion_enter
        checked = self.get_option('codecompletion/enter-key')
        if self.editorstacks is not None:
            for editorstack in self.editorstacks:
                editorstack.set_codecompletion_enter_enabled(checked)
        
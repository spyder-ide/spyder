# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Editor Plugin"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from spyderlib.qt.QtGui import (QVBoxLayout, QFileDialog, QPrintDialog,
                                QSplitter, QToolBar, QAction, QApplication,
                                QDialog, QWidget, QPrinter, QActionGroup,
                                QInputDialog, QMenu, QAbstractPrintDialog,
                                QGroupBox, QTabWidget, QLabel, QFontComboBox,
                                QHBoxLayout)
from spyderlib.qt.QtCore import SIGNAL, QStringList, QVariant, QByteArray, Qt

import os, sys, time, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import encoding, sourcecode
from spyderlib.baseconfig import get_conf_path, _
from spyderlib.config import get_icon, CONF, get_color_scheme
from spyderlib.utils import programs
from spyderlib.utils.qthelpers import (create_action, add_actions,
                                       get_std_icon, get_filetype_icon)
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.editor import (ReadWriteStatus, EncodingStatus,
                                      CursorPositionStatus, EOLStatus,
                                      EditorSplitter, EditorStack, Printer,
                                      EditorMainWindow)
from spyderlib.widgets.sourcecode import codeeditor
from spyderlib.plugins import SpyderPluginWidget, PluginConfigPage
from spyderlib.plugins.runconfig import (RunConfigDialog, RunConfigOneDialog,
                                         get_run_configuration)


def _load_all_breakpoints():
    bp_dict = CONF.get('run', 'breakpoints', {})
    for filename in bp_dict.keys():
        if not osp.isfile(filename):
            bp_dict.pop(filename)
    return bp_dict

def load_breakpoints(filename):
    breakpoints = _load_all_breakpoints().get(filename, [])
    if breakpoints and isinstance(breakpoints[0], int):
        # Old breakpoints format
        breakpoints = [(lineno, None) for lineno in breakpoints]
    return breakpoints

def save_breakpoints(filename, breakpoints):
    if not osp.isfile(filename):
        return
    bp_dict = _load_all_breakpoints()
    bp_dict[filename] = breakpoints
    CONF.set('run', 'breakpoints', bp_dict)
    
def clear_all_breakpoints():
    CONF.set('run', 'breakpoints', {})


WINPDB_PATH = programs.get_nt_program_name('winpdb')

def is_winpdb_installed():
    return programs.is_program_installed(WINPDB_PATH)


class EditorConfigPage(PluginConfigPage):
    def __init__(self, plugin, parent):
        PluginConfigPage.__init__(self, plugin, parent)
        self.get_name = lambda: _("Editor")
    
    def setup_page(self):
        template_btn = self.create_button(_("Edit template for new modules"),
                                    self.plugin.edit_template)
        
        interface_group = QGroupBox(_("Interface"))
        font_group = self.create_fontgroup(option=None,
                                    text=_("Text and margin font style"),
                                    fontfilters=QFontComboBox.MonospacedFonts)
        newcb = self.create_checkbox
        fpsorting_box = newcb(_("Sort files according to full path"),
                              'fullpath_sorting')
        showtabbar_box = newcb(_("Show tab bar"), 'show_tab_bar')

        interface_layout = QVBoxLayout()
        interface_layout.addWidget(fpsorting_box)
        interface_layout.addWidget(showtabbar_box)
        interface_group.setLayout(interface_layout)
        
        display_group = QGroupBox(_("Source code"))
        linenumbers_box = newcb(_("Show line numbers"), 'line_numbers')
        edgeline_box = newcb(_("Show vertical line after"), 'edge_line')
        edgeline_spin = self.create_spinbox("", _("characters"),
                                            'edge_line_column', 80, 1, 500)
        self.connect(edgeline_box, SIGNAL("toggled(bool)"),
                     edgeline_spin.setEnabled)
        edgeline_spin.setEnabled(self.get_option('edge_line'))
        edgeline_layout = QHBoxLayout()
        edgeline_layout.addWidget(edgeline_box)
        edgeline_layout.addWidget(edgeline_spin)
        currentline_box = newcb(_("Highlight current line"),
                                'highlight_current_line', default=True)
        occurence_box = newcb(_("Highlight occurences"),
                              'occurence_highlighting', default=True)
        wrap_mode_box = newcb(_("Wrap lines"), 'wrap')
        names = CONF.get('color_schemes', 'names')
        choices = zip(names, names)
        cs_combo = self.create_combobox(_("Syntax color scheme: "),
                                        choices, 'color_scheme_name')
        
        display_layout = QVBoxLayout()
        display_layout.addWidget(linenumbers_box)
        display_layout.addLayout(edgeline_layout)
        display_layout.addWidget(currentline_box)
        display_layout.addWidget(occurence_box)
        display_layout.addWidget(wrap_mode_box)
        display_layout.addWidget(cs_combo)
        display_group.setLayout(display_layout)

        run_group = QGroupBox(_("Run"))
        saveall_box = newcb(_("Save all files before running script"),
                            'save_all_before_run', True)
        
        introspection_group = QGroupBox(_("Introspection"))
        rope_is_installed = programs.is_module_installed('rope')
        if rope_is_installed:
            completion_box = newcb(_("Automatic code completion"),
                                   'codecompletion/auto')
            case_comp_box = newcb(_("Case sensitive code completion"),
                                  'codecompletion/case_sensitive')
            show_single_box = newcb(_("Show single completion"),
                                    'codecompletion/show_single')
            comp_enter_box = newcb(_("Enter key selects completion"),
                                   'codecompletion/enter_key')
            calltips_box = newcb(_("Balloon tips"), 'calltips')
            gotodef_box = newcb(_("Link to object definition"),
                  'go_to_definition',
                  tip=_("If this option is enabled, clicking on an object\n"
                        "name (left-click + Ctrl key) will go this object\n"
                        "definition (if resolved)."))
            inspector_box = newcb(
                  _("Automatic notification to object inspector"),
                  'object_inspector', default=True,
                  tip=_("If this option is enabled, object inspector\n"
                        "will automatically show informations on functions\n"
                        "entered in editor (this is triggered when entering\n"
                        "a left parenthesis after a valid function name)"))
        else:
            rope_label = QLabel(_("<b>Warning:</b><br>"
                                  "The Python module <i>rope</i> is not "
                                  "installed on this computer: calltips, "
                                  "code completion and go-to-definition "
                                  "features won't be available."))
            rope_label.setWordWrap(True)
        
        sourcecode_group = QGroupBox(_("Source code"))
        closepar_box = newcb(_("Automatic parentheses, braces and "
                                     "brackets insertion"),
                             'close_parentheses')
        autounindent_box = newcb(_("Automatic indentation after 'else', "
                                   "'elif', etc."), 'auto_unindent')
        indent_chars_box = self.create_combobox(_("Indentation characters: "),
                                        ((_("4 spaces"), '*    *'),
                                         (_("2 spaces"), '*  *'),
                                         (_("tab"), '*\t*')), 'indent_chars')
        tabwidth_spin = self.create_spinbox(_("Tab stop width:"), _("pixels"),
                                            'tab_stop_width', 40, 10, 1000, 10)
        tab_mode_box = newcb(_("Tab always indent"),
                      'tab_always_indent', default=False,
                      tip=_("If enabled, pressing Tab will always indent,\n"
                            "even when the cursor is not at the beginning\n"
                            "of a line (when this option is enabled, code\n"
                            "completion may be triggered using the alternate\n"
                            "shortcut: Ctrl+Space)"))
        ibackspace_box = newcb(_("Intelligent backspace"),
                               'intelligent_backspace', default=True)
        removetrail_box = newcb(_("Automatically remove trailing spaces "
                                  "when saving files"),
                               'always_remove_trailing_spaces', default=False)
        
        analysis_group = QGroupBox(_("Analysis"))
        pyflakes_label = QLabel(_("Note: add <b>pyflakes:ignore</b> in "
                                  "a comment to ignore code analysis "
                                  "warnings."))
        pyflakes_label.setWordWrap(True)
        codeanalysis_box = newcb(_("Code analysis (pyflakes)"),
                      'code_analysis', default=True,
                      tip=_("If enabled, Python source code will be analyzed\n"
                            "using pyflakes, lines containing errors or \n"
                            "warnings will be highlighted"))
        codeanalysis_box.setEnabled(programs.is_module_installed('pyflakes'))
        todolist_box = newcb(_("Tasks (TODO, FIXME, XXX, HINT, TIP)"),
                             'todo_list', default=True)
        ancb_layout = QHBoxLayout()
        ancb_layout.addWidget(codeanalysis_box)
        ancb_layout.addWidget(todolist_box)
        realtime_radio = self.create_radiobutton(
                                            _("Perform analysis when "
                                                    "saving file and every"),
                                            'realtime_analysis', True)
        saveonly_radio = self.create_radiobutton(
                                            _("Perform analysis only "
                                                    "when saving file"),
                                            'onsave_analysis', False)
        af_spin = self.create_spinbox("", " ms", 'realtime_analysis/timeout',
                                      min_=100, max_=1000000, step=100)
        af_layout = QHBoxLayout()
        af_layout.addWidget(realtime_radio)
        af_layout.addWidget(af_spin)
        
        run_layout = QVBoxLayout()
        run_layout.addWidget(saveall_box)
        run_group.setLayout(run_layout)
        
        introspection_layout = QVBoxLayout()
        if rope_is_installed:
            introspection_layout.addWidget(calltips_box)
            introspection_layout.addWidget(completion_box)
            introspection_layout.addWidget(case_comp_box)
            introspection_layout.addWidget(show_single_box)
            introspection_layout.addWidget(comp_enter_box)
            introspection_layout.addWidget(gotodef_box)
            introspection_layout.addWidget(inspector_box)
        else:
            introspection_layout.addWidget(rope_label)
        introspection_group.setLayout(introspection_layout)
        
        analysis_layout = QVBoxLayout()
        analysis_layout.addWidget(pyflakes_label)
        analysis_layout.addLayout(ancb_layout)
        analysis_layout.addLayout(af_layout)
        analysis_layout.addWidget(saveonly_radio)
        analysis_group.setLayout(analysis_layout)
        
        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(closepar_box)
        sourcecode_layout.addWidget(autounindent_box)
        sourcecode_layout.addWidget(indent_chars_box)
        sourcecode_layout.addWidget(tabwidth_spin)
        sourcecode_layout.addWidget(tab_mode_box)
        sourcecode_layout.addWidget(ibackspace_box)
        sourcecode_layout.addWidget(removetrail_box)
        sourcecode_group.setLayout(sourcecode_layout)

        eol_group = QGroupBox(_("End-of-line characters"))
        eol_label = QLabel(_("When opening a text file containing "
                             "mixed end-of-line characters (this may "
                             "raise syntax errors in Python interpreter "
                             "on Windows platforms), Spyder may fix the "
                             "file automatically."))
        eol_label.setWordWrap(True)
        check_eol_box = newcb(_("Fix automatically and show warning "
                                "message box"),
                              'check_eol_chars', default=True)

        eol_layout = QVBoxLayout()
        eol_layout.addWidget(eol_label)
        eol_layout.addWidget(check_eol_box)
        eol_group.setLayout(eol_layout)
        
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(font_group, interface_group, display_group),
                    _("Display"))
        tabs.addTab(self.create_tab(introspection_group, analysis_group),
                    _("Code Introspection/Analysis"))
        tabs.addTab(self.create_tab(template_btn, run_group, sourcecode_group,
                                    eol_group),
                    _("Advanced settings"))
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(tabs)
        self.setLayout(vlayout)


class Editor(SpyderPluginWidget):
    """
    Multi-file Editor widget
    """
    CONF_SECTION = 'editor'
    CONFIGWIDGET_CLASS = EditorConfigPage
    TEMPFILE_PATH = get_conf_path('.temp.py')
    TEMPLATE_PATH = get_conf_path('template.py')
    DISABLE_ACTIONS_WHEN_HIDDEN = False # SpyderPluginWidget class attribute
    def __init__(self, parent, ignore_last_opened_files=False):
        self.__set_eol_chars = True
        
        self.set_default_color_scheme()
        
        # Creating template if it doesn't already exist
        if not osp.isfile(self.TEMPLATE_PATH):
            header = ['# -*- coding: utf-8 -*-', '"""', 'Created on %(date)s',
                      '', '@author: %(username)s', '"""', '']
            encoding.write(os.linesep.join(header), self.TEMPLATE_PATH, 'utf-8')

        self.projectexplorer = None
        self.outlineexplorer = None
        self.inspector = None

        self.editorstacks = None
        self.editorwindows = None
        self.editorwindows_to_be_created = None
        
        self.file_dependent_actions = []
        self.pythonfile_dependent_actions = []
        self.dock_toolbar_actions = None
        self.edit_menu_actions = None #XXX: find another way to notify Spyder
        # (see spyder.py: 'update_edit_menu' method)
        self.search_menu_actions = None #XXX: same thing ('update_search_menu')
        self.stack_menu_actions = None
        SpyderPluginWidget.__init__(self, parent)

        self.filetypes = ((_("Python files"), ('.py', '.pyw', '.ipy')),
                          (_("Cython/Pyrex files"), ('.pyx', '.pxd', '.pxi')),
                          (_("C files"), ('.c', '.h')),
                          (_("C++ files"),
                           ('.cc', '.cpp', '.h', '.cxx', '.hpp', '.hh')),
                          (_("OpenCL files"), ('.cl', )),
                          (_("Fortran files"),
                           ('.f', '.for', '.f90', '.f95', '.f2k')),
                          (_("Patch and diff files"),
                           ('.patch', '.diff', '.rej')),
                          (_("Batch files"), ('.bat', '.cmd')),
                          (_("Text files"), ('.txt',)),
                          (_("reStructured Text files"), ('.txt', '.rst')),
                          (_("gettext files"), ('.po', '.pot')),
                          (_("Web page files"), ('.css', '.htm', '.html',)),
                          (_("Configuration files"),
                           ('.properties', '.session', '.ini', '.inf',
                            '.reg', '.cfg')),
                          (_("All files"), ('',)))
        
        statusbar = self.main.statusBar()
        self.readwrite_status = ReadWriteStatus(self, statusbar)
        self.eol_status = EOLStatus(self, statusbar)
        self.encoding_status = EncodingStatus(self, statusbar)
        self.cursorpos_status = CursorPositionStatus(self, statusbar)
        
        layout = QVBoxLayout()
        self.dock_toolbar = QToolBar(self)
        add_actions(self.dock_toolbar, self.dock_toolbar_actions)
        layout.addWidget(self.dock_toolbar)

        self.last_edit_cursor_pos = None
        self.cursor_pos_history = []
        self.cursor_pos_index = None
        self.__ignore_cursor_position = True
        
        self.editorstacks = []
        self.last_focus_editorstack = {}
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
        self.register_widget_shortcuts("Editor", self.find_widget)
        
        # Tabbed editor widget + Find/Replace widget
        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        self.editorsplitter = EditorSplitter(self, self,
                                         self.stack_menu_actions, first=True)
        editor_layout.addWidget(self.editorsplitter)
        editor_layout.addWidget(self.find_widget)

        # Splitter: editor widgets (see above) + outline explorer
        self.splitter = QSplitter(self)
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(editor_widgets)
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
            self.set_last_focus_editorstack(self, self.editorstacks[0])
        else:
            self.__load_temp_file()
        
        self.connect(self, SIGNAL("focus_changed()"),
                     self.save_focus_editorstack)
        
        # Parameters of last file execution:
        self.__last_ic_exec = None # internal console
        self.__last_ec_exec = None # external console
            
        self.__ignore_cursor_position = False
        current_editor = self.get_current_editor()
        if current_editor is not None:
            filename = self.get_current_filename()
            position = current_editor.get_position('cursor')
            self.add_cursor_position_to_history(filename, position)
        self.update_cursorpos_actions()
        
    def set_projectexplorer(self, projectexplorer):
        self.projectexplorer = projectexplorer
        
    def show_hide_project_explorer(self):
        if self.projectexplorer is not None:
            dw = self.projectexplorer.dockwidget
            if dw.isVisible():
                dw.hide()
            else:
                dw.show()
                dw.raise_()
            self.switch_to_plugin()
        
    def set_outlineexplorer(self, outlineexplorer):
        self.outlineexplorer = outlineexplorer
        for editorstack in self.editorstacks:
            editorstack.set_outlineexplorer(self.outlineexplorer)
        self.connect(self.outlineexplorer,
                     SIGNAL("edit_goto(QString,int,QString)"),
                     lambda filenames, goto, word:
                     self.load(filenames=filenames, goto=goto, word=word,
                               editorwindow=self))
            
    def show_hide_outline_explorer(self):
        if self.outlineexplorer is not None:
            dw = self.outlineexplorer.dockwidget
            if dw.isVisible():
                dw.hide()
            else:
                dw.show()
                dw.raise_()
            self.switch_to_plugin()
        
    def set_inspector(self, inspector):
        self.inspector = inspector
        for editorstack in self.editorstacks:
            editorstack.set_inspector(self.inspector)
        
    #------ Private API --------------------------------------------------------
    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        # Widget is now visible, we may center cursor on top level editor:
        self.get_current_editor()._center_cursor()
            
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        title = _('Editor')
        filename = self.get_current_filename()
        if filename:
            title += ' - '+unicode(filename)
        return title
    
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
        """Return a list of actions related to plugin"""
        self.toggle_outline_action = create_action(self,
                                _("Show/hide outline explorer"),
                                triggered=self.show_hide_outline_explorer,
                                context=Qt.WidgetWithChildrenShortcut)
        self.register_shortcut(self.toggle_outline_action, context="Editor",
                               name="Show/hide outline", default="Ctrl+Alt+O")
        self.toggle_project_action = create_action(self,
                                _("Show/hide project explorer"),
                                triggered=self.show_hide_project_explorer,
                                context=Qt.WidgetWithChildrenShortcut)
        self.register_shortcut(self.toggle_project_action, context="Editor",
                               name="Show/hide project explorer",
                               default="Ctrl+Alt+P")
        self.addActions([self.toggle_outline_action, self.toggle_project_action])
        
        self.new_action = create_action(self, _("&New file..."),
                icon='filenew.png', tip=_("Create a new Python script"),
                triggered=self.new)
        self.register_shortcut(self.new_action, context="Editor",
                               name="New file", default="Ctrl+N")
        self.open_action = create_action(self, _("&Open..."),
                icon='fileopen.png', tip=_("Open text file"),
                triggered=self.load)
        self.revert_action = create_action(self, _("&Revert"),
                icon='revert.png', tip=_("Revert file from disk"),
                triggered=self.revert)
        self.register_shortcut(self.open_action, context="Editor",
                               name="Open file", default="Ctrl+O")
        self.save_action = create_action(self, _("&Save"),
                icon='filesave.png', tip=_("Save current file"),
                triggered=self.save)
        self.register_shortcut(self.save_action, context="Editor",
                               name="Save file", default="Ctrl+S")
        self.save_all_action = create_action(self, _("Sav&e all"),
                icon='save_all.png', tip=_("Save all opened files"),
                triggered=self.save_all)
        self.register_shortcut(self.save_all_action, context="Editor",
                               name="Save all", default="Ctrl+Shift+S")
        save_as_action = create_action(self, _("Save &as..."), None,
                'filesaveas.png', _("Save current file as..."),
                triggered=self.save_as)
        print_preview_action = create_action(self, _("Print preview..."),
                tip=_("Print preview..."), triggered=self.print_preview)
        print_action = create_action(self, _("&Print..."),
                icon='print.png', tip=_("Print current file..."),
                triggered=self.print_file)
        self.close_action = create_action(self, _("&Close"),
                icon='fileclose.png', tip=_("Close current file"),
                triggered=self.close_file)
        self.register_shortcut(self.close_action, context="Editor",
                               name="Close file", default="Ctrl+W")
        self.close_all_action = create_action(self, _("C&lose all"),
                icon='filecloseall.png', tip=_("Close all opened files"),
                triggered=self.close_all_files)
        self.register_shortcut(self.close_all_action, context="Editor",
                               name="Close all", default="Ctrl+Shift+W")
        
        set_clear_breakpoint_action = create_action(self,
                                    _("Set/Clear breakpoint"),
                                    icon=get_icon("breakpoint.png"),
                                    triggered=self.set_or_clear_breakpoint,
                                    context=Qt.WidgetShortcut)
        self.register_shortcut(set_clear_breakpoint_action, context="Editor",
                               name="Breakpoint", default="F12")
        set_cond_breakpoint_action = create_action(self,
                            _("Set/Edit conditional breakpoint"),
                            icon=get_icon("breakpoint_cond.png"),
                            triggered=self.set_or_edit_conditional_breakpoint,
                            context=Qt.WidgetShortcut)
        self.register_shortcut(set_cond_breakpoint_action, context="Editor",
                               name="Conditional breakpoint",
                               default="Shift+F12")
        clear_all_breakpoints_action = create_action(self,
                                    _("Clear breakpoints in all files"),
                                    triggered=self.clear_all_breakpoints)
        breakpoints_menu = QMenu(_("Breakpoints"), self)
        add_actions(breakpoints_menu, (set_clear_breakpoint_action,
                                       set_cond_breakpoint_action, None,
                                       clear_all_breakpoints_action))
        
        run_action = create_action(self, _("&Run"), icon='run.png',
                tip=_("Run active script in a new Python interpreter"),
                triggered=self.run_file)
        self.register_shortcut(run_action, context="Editor",
                               name="Run", default="F5")
        debug_action = create_action(self, _("&Debug"), icon='bug.png',
                tip=_("Debug current script in external console"
                            "\n(external console is executed in a "
                            "separate process)"),
                triggered=self.debug_file)
        self.register_shortcut(debug_action, context="Editor",
                               name="Debug", default="Ctrl+F5")
        configure_action = create_action(self,
                _("&Configure..."), icon='configure.png',
                tip=_("Edit run configurations"),
                triggered=self.edit_run_configurations)
        self.register_shortcut(configure_action, context="Editor",
                               name="Configure", default="F6")
        re_run_action = create_action(self,
                _("Re-run &last script"), icon='run_again.png',
                tip=_("Run again last script in external console "
                            "with the same options"),
                triggered=self.re_run_file)
        self.register_shortcut(re_run_action, context="Editor",
                               name="Re-run last script", default="Ctrl+F6")
        
        run_selected_action = create_action(self,
                _("Run &selection or current block"),
                icon='run_selection.png',
                tip=_("Run selected text or current block of lines \n"
                            "inside current external console's interpreter"),
                triggered=self.run_selection_or_block)
        self.register_shortcut(run_selected_action, context="Editor",
                               name="Run selection", default="F9")
        
        self.todo_list_action = create_action(self,
                _("Show todo list"), icon='todo_list.png',
                tip=_("Show TODO/FIXME/XXX/HINT/TIP comments list"),
                triggered=self.go_to_next_todo)
        self.todo_menu = QMenu(self)
        self.todo_list_action.setMenu(self.todo_menu)
        self.connect(self.todo_menu, SIGNAL("aboutToShow()"),
                     self.update_todo_menu)
        
        self.warning_list_action = create_action(self,
                _("Show warning/error list"), icon='wng_list.png',
                tip=_("Show code analysis warnings/errors"),
                triggered=self.go_to_next_warning)
        self.warning_menu = QMenu(self)
        self.warning_list_action.setMenu(self.warning_menu)
        self.connect(self.warning_menu, SIGNAL("aboutToShow()"),
                     self.update_warning_menu)
        self.previous_warning_action = create_action(self,
                _("Previous warning/error"), icon='prev_wng.png',
                tip=_("Go to previous code analysis warning/error"),
                triggered=self.go_to_previous_warning)
        self.next_warning_action = create_action(self,
                _("Next warning/error"), icon='next_wng.png',
                tip=_("Go to next code analysis warning/error"),
                triggered=self.go_to_next_warning)
        
        self.previous_edit_cursor_action = create_action(self,
                _("Last edit location"), icon='last_edit_location.png',
                tip=_("Go to last edit location"),
                triggered=self.go_to_last_edit_location)
        self.register_shortcut(self.previous_edit_cursor_action,
                               context="Editor",
                               name="Last edit location",
                               default="Ctrl+Alt+Shift+Left")
        self.previous_cursor_action = create_action(self,
                _("Previous cursor position"), icon='prev_cursor.png',
                tip=_("Go to previous cursor position"),
                triggered=self.go_to_previous_cursor_position)
        self.register_shortcut(self.previous_cursor_action,
                               context="Editor",
                               name="Previous cursor position",
                               default="Ctrl+Alt+Left")
        self.next_cursor_action = create_action(self,
                _("Next cursor position"), icon='next_cursor.png',
                tip=_("Go to next cursor position"),
                triggered=self.go_to_next_cursor_position)
        self.register_shortcut(self.next_cursor_action,
                               context="Editor", name="Next cursor position",
                               default="Ctrl+Alt+Right")
        
        self.toggle_comment_action = create_action(self,
                _("Comment")+"/"+_("Uncomment"), icon='comment.png',
                tip=_("Comment current line or selection"),
                triggered=self.toggle_comment, context=Qt.WidgetShortcut)
        self.register_shortcut(self.toggle_comment_action, context="Editor",
                               name="Toggle comment", default="Ctrl+1")
        blockcomment_action = create_action(self, _("Add &block comment"),
                tip=_("Add block comment around "
                            "current line or selection"),
                triggered=self.blockcomment, context=Qt.WidgetShortcut)
        self.register_shortcut(blockcomment_action, context="Editor",
                               name="Blockcomment", default="Ctrl+4")
        unblockcomment_action = create_action(self,
                _("R&emove block comment"),
                tip = _("Remove comment block around "
                              "current line or selection"),
                triggered=self.unblockcomment, context=Qt.WidgetShortcut)
        self.register_shortcut(unblockcomment_action, context="Editor",
                               name="Unblockcomment", default="Ctrl+5")
                
        # ----------------------------------------------------------------------
        # The following action shortcuts are hard-coded in CodeEditor
        # keyPressEvent handler (the shortcut is here only to inform user):
        # (context=Qt.WidgetShortcut -> disable shortcut for other widgets)
        self.indent_action = create_action(self,
                _("Indent"), "Tab", icon='indent.png',
                tip=_("Indent current line or selection"),
                triggered=self.indent, context=Qt.WidgetShortcut)
        self.unindent_action = create_action(self,
                _("Unindent"), "Shift+Tab", icon='unindent.png',
                tip=_("Unindent current line or selection"),
                triggered=self.unindent, context=Qt.WidgetShortcut)
        # ----------------------------------------------------------------------
        
        self.winpdb_action = create_action(self, _("Debug with winpdb"),
                                           triggered=self.run_winpdb)
        self.winpdb_action.setEnabled(is_winpdb_installed())
        self.register_shortcut(self.winpdb_action, context="Editor",
                               name="Debug with winpdb", default="F7")
        
        self.win_eol_action = create_action(self,
                           _("Carriage return and line feed (Windows)"),
                           toggled=lambda: self.toggle_eol_chars('nt'))
        self.linux_eol_action = create_action(self,
                           _("Line feed (UNIX)"),
                           toggled=lambda: self.toggle_eol_chars('posix'))
        self.mac_eol_action = create_action(self,
                           _("Carriage return (Mac)"),
                           toggled=lambda: self.toggle_eol_chars('mac'))
        eol_action_group = QActionGroup(self)
        eol_actions = (self.win_eol_action, self.linux_eol_action,
                       self.mac_eol_action)
        add_actions(eol_action_group, eol_actions)
        eol_menu = QMenu(_("Convert end-of-line characters"), self)
        add_actions(eol_menu, eol_actions)
        
        trailingspaces_action = create_action(self,
                                      _("Remove trailing spaces"),
                                      triggered=self.remove_trailing_spaces)
        fixindentation_action = create_action(self, _("Fix indentation"),
                      tip=_("Replace tab characters by space characters"),
                      triggered=self.fix_indentation)

        gotoline_action = create_action(self, _("Go to line..."),
                                        icon=get_icon("gotoline.png"),
                                        triggered=self.go_to_line,
                                        context=Qt.WidgetShortcut)
        self.register_shortcut(gotoline_action, context="Editor",
                               name="Go to line", default="Ctrl+L")

        workdir_action = create_action(self,
                _("Set console working directory"),
                icon=get_std_icon('DirOpenIcon'),
                tip=_("Set current console (and file explorer) working "
                            "directory to current script directory"),
                triggered=self.__set_workdir)

        self.max_recent_action = create_action(self,
            _("Maximum number of recent files..."),
            triggered=self.change_max_recent_files)
        self.clear_recent_action = create_action(self,
            _("Clear this list"), tip=_("Clear recent files list"),
            triggered=self.clear_recent_files)
        self.recent_file_menu = QMenu(_("Open &recent"), self)
        self.connect(self.recent_file_menu, SIGNAL("aboutToShow()"),
                     self.update_recent_file_menu)

        file_menu_actions = [self.new_action, self.open_action,
                             self.recent_file_menu, self.save_action,
                             self.save_all_action, save_as_action,
                             self.revert_action, 
                             None, print_preview_action, print_action,
                             None, self.close_action,
                             self.close_all_action, None]
        self.main.file_menu_actions += file_menu_actions
        file_toolbar_actions = [self.new_action, self.open_action,
                                self.save_action, self.save_all_action,
                                print_action]
        self.main.file_toolbar_actions += file_toolbar_actions
        
        self.edit_menu_actions = [self.toggle_comment_action,
                                  blockcomment_action, unblockcomment_action,
                                  self.indent_action, self.unindent_action]
        self.main.edit_menu_actions += [None]+self.edit_menu_actions
        edit_toolbar_actions = [self.toggle_comment_action,
                                self.unindent_action, self.indent_action]
        self.main.edit_toolbar_actions += edit_toolbar_actions
        
        self.search_menu_actions = [gotoline_action]
        self.main.search_menu_actions += self.search_menu_actions
        self.main.search_toolbar_actions += [gotoline_action]
        
        run_menu_actions = [run_action, debug_action, configure_action,
                            breakpoints_menu, None,
                            re_run_action, run_selected_action]
        self.main.run_menu_actions += run_menu_actions
        run_toolbar_actions = [run_action, debug_action, configure_action,
                               run_selected_action, re_run_action]
        self.main.run_toolbar_actions += run_toolbar_actions
        
        source_menu_actions = [eol_menu, trailingspaces_action,
                               fixindentation_action, None, self.winpdb_action]
        self.main.source_menu_actions += source_menu_actions
        
        source_toolbar_actions = [self.todo_list_action,
                self.warning_list_action, self.previous_warning_action,
                self.next_warning_action, None,
                self.previous_edit_cursor_action,
                self.previous_cursor_action, self.next_cursor_action]
        self.main.source_toolbar_actions += source_toolbar_actions
        
        self.dock_toolbar_actions = file_toolbar_actions + [None] + \
                                    source_toolbar_actions + [None] + \
                                    run_toolbar_actions + [None] + \
                                    edit_toolbar_actions
        self.pythonfile_dependent_actions = [run_action, configure_action,
                set_clear_breakpoint_action, set_cond_breakpoint_action,
                debug_action, re_run_action, run_selected_action,
                blockcomment_action, unblockcomment_action, self.winpdb_action]
        self.file_dependent_actions = self.pythonfile_dependent_actions + \
                [self.save_action, save_as_action, print_preview_action,
                 print_action, self.save_all_action, gotoline_action,
                 workdir_action, self.close_action, self.close_all_action,
                 self.toggle_comment_action, self.revert_action,
                 self.indent_action, self.unindent_action]
        self.stack_menu_actions = [self.save_action, save_as_action,
                                   print_action, None, run_action, debug_action,
                                   configure_action, None, gotoline_action,
                                   workdir_action, None, self.close_action]
        
        return self.file_dependent_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.connect(self.main, SIGNAL('restore_scrollbar_position()'),
                     self.restore_scrollbar_position)
        self.connect(self, SIGNAL('focus_changed()'),
                     self.main.plugin_focus_changed)
        self.connect(self.main.console,
                     SIGNAL("edit_goto(QString,int,QString)"), self.load)
        self.connect(self, SIGNAL("open_external_console(QString,QString,QString,bool,bool,bool,QString)"),
                     self.main.open_external_console)
        self.connect(self, SIGNAL('external_console_execute_lines(QString)'),
                     self.main.execute_python_code_in_external_console)
        self.connect(self, SIGNAL('redirect_stdio(bool)'),
                     self.main.redirect_internalshell_stdio)
        self.connect(self, SIGNAL("open_dir(QString)"),
                     self.main.workingdirectory.chdir)
        self.set_inspector(self.main.inspector)
        self.set_outlineexplorer(self.main.outlineexplorer)
        self.main.add_dockwidget(self)
    
        
    #------ Focus tabwidget
    def __get_focus_editorstack(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, codeeditor.CodeEditor):
            for editorstack in self.editorstacks:
                if fwidget is editorstack.get_current_editor():
                    return editorstack
        elif isinstance(fwidget, EditorStack):
            return fwidget
        
    def set_last_focus_editorstack(self, editorwindow, editorstack):
        self.last_focus_editorstack[editorwindow] = editorstack
        self.last_focus_editorstack[None] = editorstack # very last editorstack
        
    def get_last_focus_editorstack(self, editorwindow=None):
        return self.last_focus_editorstack[editorwindow]
    
    def remove_last_focus_editorstack(self, editorstack):
        for editorwindow, widget in self.last_focus_editorstack.items():
            if widget is editorstack:
                self.last_focus_editorstack[editorwindow] = None
        
    def save_focus_editorstack(self):
        editorstack = self.__get_focus_editorstack()
        if editorstack is not None:
            for win in [self]+self.editorwindows:
                if win.isAncestorOf(editorstack):
                    self.set_last_focus_editorstack(win, editorstack)
    
        
    #------ Handling editorstacks
    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        
        self.register_widget_shortcuts("Editor", editorstack)
        
        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            self.set_last_focus_editorstack(self, editorstack)
            editorstack.set_closable( len(self.editorstacks) > 1 )
            if self.outlineexplorer is not None:
                editorstack.set_outlineexplorer(self.outlineexplorer)
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
            self.connect(editorstack, SIGNAL('refresh_eol_chars(QString)'),
                         self.eol_status.eol_changed)
            
        editorstack.set_inspector(self.inspector)
        editorstack.set_io_actions(self.new_action, self.open_action,
                                   self.save_action, self.revert_action)
        editorstack.set_tempfile_path(self.TEMPFILE_PATH)
        editorstack.set_filetype_filters(self.get_filetype_filters())
        editorstack.set_valid_types(self.get_valid_types())
        settings = (
            ('set_codeanalysis_enabled',            'code_analysis'),
            ('set_todolist_enabled',                'todo_list'),
            ('set_realtime_analysis_enabled',       'realtime_analysis'),
            ('set_realtime_analysis_timeout',       'realtime_analysis/timeout'),
            ('set_linenumbers_enabled',             'line_numbers'),
            ('set_edgeline_enabled',                'edge_line'),
            ('set_edgeline_column',                 'edge_line_column'),
            ('set_outlineexplorer_enabled',         'outline_explorer'),
            ('set_codecompletion_auto_enabled',     'codecompletion/auto'),
            ('set_codecompletion_case_enabled',     'codecompletion/case_sensitive'),
            ('set_codecompletion_single_enabled',   'codecompletion/show_single'),
            ('set_codecompletion_enter_enabled',    'codecompletion/enter_key'),
            ('set_calltips_enabled',                'calltips'),
            ('set_go_to_definition_enabled',        'go_to_definition'),
            ('set_close_parentheses_enabled',       'close_parentheses'),
            ('set_auto_unindent_enabled',           'auto_unindent'),
            ('set_indent_chars',                    'indent_chars'),
            ('set_tab_stop_width',                  'tab_stop_width'),
            ('set_inspector_enabled',               'object_inspector'),
            ('set_wrap_enabled',                    'wrap'),
            ('set_tabmode_enabled',                 'tab_always_indent'),
            ('set_intelligent_backspace_enabled',   'intelligent_backspace'),
            ('set_highlight_current_line_enabled',  'highlight_current_line'),
            ('set_occurence_highlighting_enabled',  'occurence_highlighting'),
            ('set_checkeolchars_enabled',           'check_eol_chars'),
            ('set_fullpath_sorting_enabled',        'fullpath_sorting'),
            ('set_tabbar_visible',                  'show_tab_bar'),
            ('set_always_remove_trailing_spaces',   'always_remove_trailing_spaces'),
                    )
        for method, setting in settings:
            getattr(editorstack, method)(self.get_option(setting))
        color_scheme = get_color_scheme(self.get_option('color_scheme_name'))
        editorstack.set_default_font(self.get_plugin_font(), color_scheme)
        
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
                     lambda text: self.emit(
                     SIGNAL('external_console_execute_lines(QString)'), text))
        self.connect(editorstack, SIGNAL("update_plugin_title()"),
                     lambda: self.emit(SIGNAL("update_plugin_title()")))
        
        self.connect(editorstack, SIGNAL('close_file(int)'),
                     self.close_file_in_all_editorstacks)
        self.connect(editorstack, SIGNAL('file_saved(int)'),
                     self.file_saved_in_editorstack)
        
        self.connect(editorstack, SIGNAL("create_new_window()"),
                     self.create_new_window)
        
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
        self.connect(editorstack, SIGNAL('refresh_eol_chars(QString)'),
                     self.refresh_eol_chars)
        
        self.connect(editorstack, SIGNAL("save_breakpoints(QString,QString)"),
                     self.save_breakpoints)
        
        self.connect(editorstack, SIGNAL('text_changed_at(QString,int)'),
                     self.text_changed_at)
        self.connect(editorstack, SIGNAL('current_file_changed(QString,int)'),
                     self.current_file_changed)
        
        self.connect(editorstack, SIGNAL('plugin_load(QString)'), self.load)
        self.connect(editorstack, SIGNAL("edit_goto(QString,int,QString)"),
                     self.load)
        
    def unregister_editorstack(self, editorstack):
        """Removing editorstack only if it's not the last remaining"""
        self.remove_last_focus_editorstack(editorstack)
        if len(self.editorstacks) > 1:
            index = self.editorstacks.index(editorstack)
            self.editorstacks.pop(index)
            return True
        else:
            # editorstack was not removed!
            return False
        
    def clone_editorstack(self, editorstack):
        editorstack.clone_from(self.editorstacks[0])
        
    def close_file_in_all_editorstacks(self, index):
        sender = self.sender()
        for editorstack in self.editorstacks:
            if editorstack is not sender:
                editorstack.blockSignals(True)
                editorstack.close_file(index, force=True)
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
            (_("File toolbar"), self.main.file_toolbar_actions),
            (_("Search toolbar"), self.main.search_menu_actions),
            (_("Source toolbar"), self.main.source_toolbar_actions),
            (_("Run toolbar"), self.main.run_toolbar_actions),
            (_("Edit toolbar"), self.main.edit_toolbar_actions),
                             )
        self.menu_list = (
                          (_("&File"), self.main.file_menu_actions),
                          (_("&Edit"), self.main.edit_menu_actions),
                          (_("&Search"), self.main.search_menu_actions),
                          (_("Sour&ce"), self.main.source_menu_actions),
                          (_("&Run"), self.main.run_menu_actions),
                          (_("&Tools"), self.main.tools_menu_actions),
                          (_("?"), self.main.help_menu_actions),
                          )
        # Create pending new windows:
        for layout_settings in self.editorwindows_to_be_created:
            win = self.create_new_window()
            win.set_layout_settings(layout_settings)
        
    def create_new_window(self):
        oe_options = self.outlineexplorer.get_options()
        fullpath_sorting=self.get_option('fullpath_sorting', True),
        window = EditorMainWindow(self, self.stack_menu_actions,
                                  self.toolbar_list, self.menu_list,
                                  show_fullpath=oe_options['show_fullpath'],
                                  fullpath_sorting=fullpath_sorting,
                                  show_all_files=oe_options['show_all_files'],
                                  show_comments=oe_options['show_comments'])
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

    def get_current_editorstack(self, editorwindow=None):
        if self.editorstacks is not None:
            if len(self.editorstacks) == 1:
                return self.editorstacks[0]
            else:
                editorstack = self.__get_focus_editorstack()
                if editorstack is None or editorwindow is not None:
                    return self.get_last_focus_editorstack(editorwindow)
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
        
    def set_current_filename(self, filename, editorwindow=None):
        """Set focus to *filename* if this file has been opened
        Return the editor instance associated to *filename*"""
        editorstack = self.get_current_editorstack(editorwindow)
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
            state = state or any([finfo.editor.document().isModified()
                                  for finfo in editorstack.data])
        self.save_all_action.setEnabled(state)
            
    def update_warning_menu(self):
        """Update warning list menu"""
        editorstack = self.get_current_editorstack()
        check_results = editorstack.get_analysis_results()
        self.warning_menu.clear()
        filename = self.get_current_filename()
        for message, line0, error in check_results:
            text = message[:1].upper()+message[1:]
            icon = get_icon('error.png' if error else 'warning.png')
            slot = lambda _l=line0: self.load(filename, goto=_l)
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
        filename = self.get_current_filename()
        for text, line0 in results:
            icon = get_icon('todo.png')
            slot = lambda _l=line0: self.load(filename, goto=_l)
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
            
    def refresh_eol_chars(self, os_name):
        os_name = unicode(os_name)
        self.__set_eol_chars = False
        if os_name == 'nt':
            self.win_eol_action.setChecked(True)
        elif os_name == 'posix':
            self.linux_eol_action.setChecked(True)
        else:
            self.mac_eol_action.setChecked(True)
        self.__set_eol_chars = True
    
    
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
                    action.setEnabled(enable and is_winpdb_installed())
                else:
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

            
    #------ Breakpoints
    def save_breakpoints(self, filename, breakpoints):
        filename, breakpoints = unicode(filename), unicode(breakpoints)
        filename = osp.normpath(osp.abspath(filename))
        if breakpoints:
            breakpoints = eval(breakpoints)
        else:
            breakpoints = []
        save_breakpoints(filename, breakpoints)
        
                
    #------ File I/O
    def __load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if not osp.isfile(self.TEMPFILE_PATH):
            # Creating temporary file
            default = ['# -*- coding: utf-8 -*-',
                       '"""', _("Spyder Editor"), '',
                       _("This temporary script file is located here:"),
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
    
    def _clone_file_everywhere(self, from_editorstack):
        """Clone current file in all editorstacks"""
        finfo = self.get_current_finfo()
        for editorstack in self.editorstacks:
            if editorstack is not from_editorstack:
                editor = editorstack.clone_editor_from(finfo,
                                                       set_current=False)
                self.register_widget_shortcuts("Editor", editor)
    
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
        create_fname = lambda n: unicode(_("untitled")) + ("%d.py" % n)
        # Creating editor widget
        if editorstack is None:
            editorstack = self.get_current_editorstack()
        created_from_here = fname is None
        if created_from_here:
            while True:
                fname = create_fname(self.untitled_num)
                self.untitled_num += 1
                if not osp.isfile(fname):
                    break
            basedir = os.getcwdu()
            if CONF.get('workingdir', 'editor/new/browse_scriptdir'):
                c_fname = self.get_current_filename()
                if c_fname is not None and c_fname != self.TEMPFILE_PATH:
                    basedir = osp.dirname(c_fname)
            fname = osp.abspath(osp.join(basedir, fname))
        else:
            # QString when triggered by a Qt signal
            fname = osp.abspath(unicode(fname))
            index = editorstack.has_filename(fname)
            if index and not editorstack.close_file(index):
                return
        
        editor = editorstack.new(fname, enc, text)
        self.register_widget_shortcuts("Editor", editor)
        self._clone_file_everywhere(from_editorstack=editorstack)
        if not created_from_here:
            self.save(force=True)
                
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
        mrf, valid = QInputDialog.getInteger(editorstack, _('Editor'),
                               _('Maximum number of recent files'),
                               self.get_option('max_recent_files'), 1, 35)
        if valid:
            self.set_option('max_recent_files', mrf)
        
    def load(self, filenames=None, goto=None, word='', editorwindow=None):
        """
        Load a text file
        editorwindow: load in this editorwindow (useful when clicking on 
        outline explorer with multiple editor windows)
        """
        editor0 = self.get_current_editor()
        if editor0 is not None:
            position0 = editor0.get_position('cursor')
            filename0 = self.get_current_filename()
        else:
            position0, filename0 = None, None
        if not filenames:
            # Recent files action
            action = self.sender()
            if isinstance(action, QAction):
                filenames = unicode(action.data().toString())
        if not filenames:
            basedir = os.getcwdu()
            if CONF.get('workingdir', 'editor/open/browse_scriptdir'):
                c_fname = self.get_current_filename()
                if c_fname is not None and c_fname != self.TEMPFILE_PATH:
                    basedir = osp.dirname(c_fname)
            self.emit(SIGNAL('redirect_stdio(bool)'), False)
            parent_widget = self.get_current_editorstack()
            filenames = QFileDialog.getOpenFileNames(parent_widget,
                     _("Open file"), basedir, self.get_filetype_filters())
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            filenames = list(filenames)
            if len(filenames):
                filenames = [osp.normpath(unicode(fname)) \
                             for fname in filenames]
                if CONF.get('workingdir', 'editor/open/auto_set_to_basedir'):
                    directory = osp.dirname(filenames[0])
                    self.emit(SIGNAL("open_dir(QString)"), directory)

            else:
                return
            
        if self.dockwidget and not self.ismaximized:
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()
        
        def _convert(fname):
            fname = osp.abspath(encoding.to_unicode(fname))
            if os.name == 'nt' and len(fname) >= 2 and fname[1] == ':':
                fname = fname[0].upper()+fname[1:]
            return fname
        if not isinstance(filenames, (list, QStringList)):
            filenames = [_convert(filenames)]
        else:
            filenames = [_convert(fname) for fname in list(filenames)]
        if isinstance(goto, int):
            goto = [goto]
        elif goto is not None and len(goto) != len(filenames):
            goto = None
            
        for index, filename in enumerate(filenames):
            # -- Do not open an already opened file
            current_editor = self.set_current_filename(filename, editorwindow)
            if current_editor is None:
                # -- Not a valid filename:
                if not osp.isfile(filename):
                    continue
                # --
                current = self.get_current_editorstack(editorwindow)
                current_editor = current.load(filename, set_current=True)
                current_editor.set_breakpoints(load_breakpoints(filename))
                self.register_widget_shortcuts("Editor", current_editor)
                self._clone_file_everywhere(from_editorstack=current)
                current.analyze_script()
                self.__add_recent_file(filename)
            if goto is not None: # 'word' is assumed to be None as well
                current_editor.go_to_line(goto[index], word=word)
                position = current_editor.get_position('cursor')
                self.cursor_moved(filename0, position0, filename, position)
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
        if editor.has_selected_text():
            printDialog.addEnabledOption(QAbstractPrintDialog.PrintSelection)
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        answer = printDialog.exec_()
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if answer == QDialog.Accepted:
            self.starting_long_process(_("Printing..."))
            printer.setDocName(filename)
            editor.print_(printer)
            self.ending_long_process()

    def print_preview(self):
        """Print preview for current file"""
        from spyderlib.qt.QtGui import QPrintPreviewDialog
        editor = self.get_current_editor()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=self.get_plugin_font('printer_header'))
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowFlags(Qt.Window)
        self.connect(preview, SIGNAL("paintRequested(QPrinter*)"),
                     lambda printer: editor.print_(printer))
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
        if editorstack.save_as():
            fname = editorstack.get_current_filename()
            if CONF.get('workingdir', 'editor/save/auto_set_to_basedir'):
                self.emit(SIGNAL("open_dir(QString)"), osp.dirname(fname))
            self.__add_recent_file(fname)
        
    def save_all(self):
        """Save all opened files"""
        self.get_current_editorstack().save_all()
        
    def revert(self):
        """Revert the currently edited file from disk"""
        editorstack = self.get_current_editorstack()
        editorstack.revert()
    
    
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
    
    def toggle_comment(self):
        """Comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.toggle_comment()
    
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
        position = editor.go_to_next_todo()
        filename = self.get_current_filename()
        self.add_cursor_position_to_history(filename, position)
    
    def go_to_next_warning(self):
        editor = self.get_current_editor()
        position = editor.go_to_next_warning()
        filename = self.get_current_filename()
        self.add_cursor_position_to_history(filename, position)
    
    def go_to_previous_warning(self):
        editor = self.get_current_editor()
        position = editor.go_to_previous_warning()
        filename = self.get_current_filename()
        self.add_cursor_position_to_history(filename, position)
                
    def run_winpdb(self):
        """Run winpdb to debug current file"""
        if self.save():
            fname = self.get_current_filename()
            programs.run_program(WINPDB_PATH, [fname])
        
    def toggle_eol_chars(self, os_name):
        editor = self.get_current_editor()
        if self.__set_eol_chars:
            editor.set_eol_chars(sourcecode.get_eol_chars_from_os_name(os_name))
        
    def remove_trailing_spaces(self):
        editorstack = self.get_current_editorstack()
        editorstack.remove_trailing_spaces()
        
    def fix_indentation(self):
        editorstack = self.get_current_editorstack()
        editorstack.fix_indentation()
                    
    #------ Cursor position history management
    def update_cursorpos_actions(self):
        self.previous_edit_cursor_action.setEnabled(
                                        self.last_edit_cursor_pos is not None)
        self.previous_cursor_action.setEnabled(
               self.cursor_pos_index is not None and self.cursor_pos_index > 0)
        self.next_cursor_action.setEnabled(self.cursor_pos_index is not None \
                    and self.cursor_pos_index < len(self.cursor_pos_history)-1)
        
    def add_cursor_position_to_history(self, filename, position, fc=False):
        if self.__ignore_cursor_position:
            return
        for index, (fname, pos) in enumerate(self.cursor_pos_history[:]):
            if fname == filename:
                if pos == position or pos == 0:
                    if fc:
                        self.cursor_pos_history[index] = (filename, position)
                        self.cursor_pos_index = index
                        self.update_cursorpos_actions()
                        return
                    else:
                        if self.cursor_pos_index >= index:
                            self.cursor_pos_index -= 1
                        self.cursor_pos_history.pop(index)
                        break
        if self.cursor_pos_index is not None:
            self.cursor_pos_history = \
                        self.cursor_pos_history[:self.cursor_pos_index+1]
        self.cursor_pos_history.append((filename, position))
        self.cursor_pos_index = len(self.cursor_pos_history)-1
        self.update_cursorpos_actions()
    
    def cursor_moved(self, filename0, position0, filename1, position1):
        """Cursor was just moved: 'go to'"""
        if position0 is not None:
            self.add_cursor_position_to_history(filename0, position0)
        self.add_cursor_position_to_history(filename1, position1)
        
    def text_changed_at(self, filename, position):
        self.last_edit_cursor_pos = (unicode(filename), position)
        
    def current_file_changed(self, filename, position):
        self.add_cursor_position_to_history(unicode(filename), position,
                                            fc=True)
        
    def go_to_last_edit_location(self):
        if self.last_edit_cursor_pos is not None:
            filename, position = self.last_edit_cursor_pos
            if not osp.isfile(filename):
                self.last_edit_cursor_pos = None
                return
            else:
                self.load(filename)
                editor = self.get_current_editor()
                if position < editor.document().characterCount():
                    editor.set_cursor_position(position)
            
    def __move_cursor_position(self, index_move):
        if self.cursor_pos_index is None:
            return
        filename, _position = self.cursor_pos_history[self.cursor_pos_index]
        self.cursor_pos_history[self.cursor_pos_index] = ( filename,
                            self.get_current_editor().get_position('cursor') )
        self.__ignore_cursor_position = True
        old_index = self.cursor_pos_index
        self.cursor_pos_index = min([
                                     len(self.cursor_pos_history)-1,
                                     max([0, self.cursor_pos_index+index_move])
                                     ])
        filename, position = self.cursor_pos_history[self.cursor_pos_index]
        if not osp.isfile(filename):
            self.cursor_pos_history.pop(self.cursor_pos_index)
            if self.cursor_pos_index < old_index:
                old_index -= 1
            self.cursor_pos_index = old_index
        else:
            self.load(filename)
            editor = self.get_current_editor()
            if position < editor.document().characterCount():
                editor.set_cursor_position(position)
        self.__ignore_cursor_position = False
        self.update_cursorpos_actions()
            
    def go_to_previous_cursor_position(self):
        self.__move_cursor_position(-1)
            
    def go_to_next_cursor_position(self):
        self.__move_cursor_position(1)
        
    def go_to_line(self):
        """Open 'go to line' dialog"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.go_to_line()
            
    def set_or_clear_breakpoint(self):
        """Set/Clear breakpoint"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.set_or_clear_breakpoint()
            
    def set_or_edit_conditional_breakpoint(self):
        """Set/Edit conditional breakpoint"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.set_or_edit_conditional_breakpoint()
            
    def clear_all_breakpoints(self):
        """Clear breakpoints in all files"""
        clear_all_breakpoints()
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            for data in editorstack.data:
                data.editor.clear_breakpoints()
        
    
    #------ Run Python script
    def edit_run_configurations(self):
        dialog = RunConfigDialog(self)
        fname = osp.abspath(self.get_current_filename())
        dialog.setup(fname)
        if dialog.exec_():
            fname = dialog.file_to_run
            if fname is not None:
                self.load(fname)
                self.run_file()
        
    def run_file(self, debug=False):
        """Run script inside current interpreter or in a new one"""
        editorstack = self.get_current_editorstack()
        if editorstack.save():
            editor = self.get_current_editor()
            fname = osp.abspath(self.get_current_filename())
            
            runconf = get_run_configuration(fname)
            if runconf is None:
                dialog = RunConfigOneDialog(self)
                dialog.setup(fname)
                if not dialog.exec_():
                    return
                runconf = dialog.get_configuration()
                
            wdir = runconf.get_working_directory()
            args = runconf.get_arguments()
            python_args = runconf.get_python_arguments()
            interact = runconf.interact
            current = runconf.current
            
            python = True # Note: in the future, it may be useful to run
            # something in a terminal instead of a Python interp.
            self.__last_ec_exec = (fname, wdir, args, interact, debug,
                                   python, python_args, current)
            self.re_run_file()
            if not interact and not debug:
                # If external console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # current external shell automatically
                # (see SpyderPluginWidget.visibility_changed method)
                editor.setFocus()
                
    def debug_file(self):
        """Debug current script"""
        self.run_file(debug=True)
        
    def re_run_file(self):
        """Re-run last script"""
        if self.get_option('save_all_before_run', True):
            self.save_all()
        if self.__last_ec_exec is None:
            return
        (fname, wdir, args, interact, debug,
         python, python_args, current) = self.__last_ec_exec
        if current:
            self.emit(SIGNAL('run_in_current_console(QString,QString,QString,bool)'),
                      fname, wdir, args, debug)
        else:
            self.emit(SIGNAL('open_external_console(QString,QString,QString,bool,bool,bool,QString)'),
                      fname, wdir, args, interact, debug, python, python_args)

    def run_selection_or_block(self):
        """Run selection or current line in external console"""
        editorstack = self.get_current_editorstack()
        editorstack.run_selection_or_block()
        
        
    #------ Options
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        # toggle_fullpath_sorting
        if self.editorstacks is not None:
            color_scheme_n = 'color_scheme_name'
            color_scheme_o = get_color_scheme(self.get_option(color_scheme_n))
            font_n = 'plugin_font'
            font_o = self.get_plugin_font()
            fpsorting_n = 'fullpath_sorting'
            fpsorting_o = self.get_option(fpsorting_n)
            tabbar_n = 'show_tab_bar'
            tabbar_o = self.get_option(tabbar_n)
            linenb_n = 'line_numbers'
            linenb_o = self.get_option(linenb_n)
            edgeline_n = 'edge_line'
            edgeline_o = self.get_option(edgeline_n)
            edgelinecol_n = 'edge_line_column'
            edgelinecol_o = self.get_option(edgelinecol_n)
            currentline_n = 'highlight_current_line'
            currentline_o = self.get_option(currentline_n)
            occurence_n = 'occurence_highlighting'
            occurence_o = self.get_option(occurence_n)
            wrap_n = 'wrap'
            wrap_o = self.get_option(wrap_n)
            tabindent_n = 'tab_always_indent'
            tabindent_o = self.get_option(tabindent_n)
            ibackspace_n = 'intelligent_backspace'
            ibackspace_o = self.get_option(ibackspace_n)
            removetrail_n = 'always_remove_trailing_spaces'
            removetrail_o = self.get_option(removetrail_n)
            autocomp_n = 'codecompletion/auto'
            autocomp_o = self.get_option(autocomp_n)
            case_comp_n = 'codecompletion/case_sensitive'
            case_comp_o = self.get_option(case_comp_n)
            show_single_n = 'codecompletion/show_single'
            show_single_o = self.get_option(show_single_n)
            enter_key_n = 'codecompletion/enter_key'
            enter_key_o = self.get_option(enter_key_n)
            calltips_n = 'calltips'
            calltips_o = self.get_option(calltips_n)
            gotodef_n = 'go_to_definition'
            gotodef_o = self.get_option(gotodef_n)
            closepar_n = 'close_parentheses'
            closepar_o = self.get_option(closepar_n)
            autounindent_n = 'auto_unindent'
            autounindent_o = self.get_option(autounindent_n)
            indent_chars_n = 'indent_chars'
            indent_chars_o = self.get_option(indent_chars_n)
            tab_stop_width_n = 'tab_stop_width'
            tab_stop_width_o = self.get_option(tab_stop_width_n)
            inspector_n = 'object_inspector'
            inspector_o = self.get_option(inspector_n)
            todo_n = 'todo_list'
            todo_o = self.get_option(todo_n)
            analysis_n = 'code_analysis'
            analysis_o = self.get_option(analysis_n)
            rt_analysis_n = 'realtime_analysis'
            rt_analysis_o = self.get_option(rt_analysis_n)
            rta_timeout_n = 'realtime_analysis/timeout'
            rta_timeout_o = self.get_option(rta_timeout_n)
            finfo = self.get_current_finfo()
            if fpsorting_n in options:
                if self.outlineexplorer is not None:
                    self.outlineexplorer.set_fullpath_sorting(fpsorting_o)
                for window in self.editorwindows:
                    window.editorwidget.outlineexplorer.set_fullpath_sorting(
                                                                    fpsorting_o)
            for editorstack in self.editorstacks:
                if font_n in options:
                    scs = color_scheme_o if color_scheme_n in options else None
                    editorstack.set_default_font(font_o, scs)
                elif color_scheme_n in options:
                    editorstack.set_color_scheme(color_scheme_o)
                if fpsorting_n in options:
                    editorstack.set_fullpath_sorting_enabled(fpsorting_o)
                if tabbar_n in options:
                    editorstack.set_tabbar_visible(tabbar_o)
                if linenb_n in options:
                    editorstack.set_linenumbers_enabled(linenb_o,
                                                        current_finfo=finfo)
                if edgeline_n in options:
                    editorstack.set_edgeline_enabled(edgeline_o)
                if edgelinecol_n in options:
                    editorstack.set_edgeline_column(edgelinecol_o)
                if currentline_n in options:
                    editorstack.set_highlight_current_line_enabled(
                                                                currentline_o)
                if occurence_n in options:
                    editorstack.set_occurence_highlighting_enabled(occurence_o)
                if wrap_n in options:
                    editorstack.set_wrap_enabled(wrap_o)
                if tabindent_n in options:
                    editorstack.set_tabmode_enabled(tabindent_o)
                if ibackspace_n in options:
                    editorstack.set_intelligent_backspace_enabled(ibackspace_o)
                if removetrail_n in options:
                    editorstack.set_always_remove_trailing_spaces(removetrail_o)
                if autocomp_n in options:
                    editorstack.set_codecompletion_auto_enabled(autocomp_o)
                if case_comp_n in options:
                    editorstack.set_codecompletion_case_enabled(case_comp_o)
                if show_single_n in options:
                    editorstack.set_codecompletion_single_enabled(show_single_o)
                if enter_key_n in options:
                    editorstack.set_codecompletion_enter_enabled(enter_key_o)
                if calltips_n in options:
                    editorstack.set_calltips_enabled(calltips_o)
                if gotodef_n in options:
                    editorstack.set_go_to_definition_enabled(gotodef_o)
                if closepar_n in options:
                    editorstack.set_close_parentheses_enabled(closepar_o)
                if autounindent_n in options:
                    editorstack.set_auto_unindent_enabled(autounindent_o)
                if indent_chars_n in options:
                    editorstack.set_indent_chars(indent_chars_o)
                if tab_stop_width_n in options:
                    editorstack.set_tab_stop_width(tab_stop_width_o)
                if inspector_n in options:
                    editorstack.set_inspector_enabled(inspector_o)
                if todo_n in options:
                    editorstack.set_todolist_enabled(todo_o,
                                                     current_finfo=finfo)
                if analysis_n in options:
                    editorstack.set_codeanalysis_enabled(analysis_o,
                                                         current_finfo=finfo)
                if rt_analysis_n in options:
                    editorstack.set_realtime_analysis_enabled(rt_analysis_o)
                if rta_timeout_n in options:
                    editorstack.set_realtime_analysis_timeout(rta_timeout_o)
            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            if todo_n in options and todo_o and finfo is not None:
                finfo.run_todo_finder()
            if analysis_n in options and analysis_o and finfo is not None:
                finfo.run_code_analysis()

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Plugin"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Standard library imports
import os
import os.path as osp
import re
import time

# Third party imports
from qtpy import API
from qtpy.compat import from_qvariant, getopenfilenames, to_qvariant
from qtpy.QtCore import QByteArray, Qt, Signal, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtPrintSupport import QAbstractPrintDialog, QPrintDialog, QPrinter
from qtpy.QtWidgets import (QAction, QActionGroup, QApplication, QDialog,
                            QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
                            QInputDialog, QLabel, QMenu, QSplitter, QTabWidget,
                            QToolBar, QVBoxLayout, QWidget)

# Local imports
from spyder import dependencies
from spyder.config.base import _, get_conf_path, PYTEST, debug_print
from spyder.config.main import (CONF, RUN_CELL_SHORTCUT,
                                RUN_CELL_AND_ADVANCE_SHORTCUT)
from spyder.config.utils import (get_edit_filetypes, get_edit_filters,
                                 get_filter)
from spyder.py3compat import PY2, qbytearray_to_str, to_text_string
from spyder.utils import codeanalysis, encoding, programs, sourcecode
from spyder.utils import icon_manager as ima
from spyder.utils.introspection.manager import IntrospectionManager
from spyder.utils.qthelpers import create_action, add_actions, MENU_SEPARATOR
from spyder.utils.misc import getcwd_or_home
from spyder.widgets.findreplace import FindReplace
from spyder.plugins.editor.widgets.editor import (EditorMainWindow, Printer,
                                                  EditorSplitter, EditorStack,)
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.widgets.status import (CursorPositionStatus, EncodingStatus,
                                   EOLStatus, ReadWriteStatus)
from spyder.api.plugins import SpyderPluginWidget
from spyder.api.preferences import PluginConfigPage
from spyder.preferences.runconfig import (ALWAYS_OPEN_FIRST_RUN_OPTION,
                                      get_run_configuration,
                                      RunConfigDialog, RunConfigOneDialog)


# Dependencies
NBCONVERT_REQVER = ">=4.0"
dependencies.add("nbconvert", _("Manipulate Jupyter notebooks on the Editor"),
                 required_version=NBCONVERT_REQVER)


def _load_all_breakpoints():
    bp_dict = CONF.get('run', 'breakpoints', {})
    for filename in list(bp_dict.keys()):
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


def clear_breakpoint(filename, lineno):
    breakpoints = load_breakpoints(filename)
    if breakpoints:
        for breakpoint in breakpoints[:]:
            if breakpoint[0] == lineno:
                breakpoints.remove(breakpoint)
        save_breakpoints(filename, breakpoints)


WINPDB_PATH = programs.find_program('winpdb')


class EditorConfigPage(PluginConfigPage):
    def get_name(self):
        return _("Editor")
        
    def get_icon(self):
        return ima.icon('edit')
    
    def setup_page(self):
        template_btn = self.create_button(_("Edit template for new modules"),
                                    self.plugin.edit_template)
        
        interface_group = QGroupBox(_("Interface"))
        newcb = self.create_checkbox
        showtabbar_box = newcb(_("Show tab bar"), 'show_tab_bar')
        showclassfuncdropdown_box = newcb(
                _("Show selector for classes and functions"),
                'show_class_func_dropdown')
        showindentguides_box = newcb(_("Show Indent Guides"),
                                      'indent_guides')

        interface_layout = QVBoxLayout()
        interface_layout.addWidget(showtabbar_box)
        interface_layout.addWidget(showclassfuncdropdown_box)
        interface_layout.addWidget(showindentguides_box)
        interface_group.setLayout(interface_layout)
        
        display_group = QGroupBox(_("Source code"))
        linenumbers_box = newcb(_("Show line numbers"), 'line_numbers')
        blanks_box = newcb(_("Show blank spaces"), 'blank_spaces')
        edgeline_box = newcb(_("Show vertical lines after"), 'edge_line')
        edgeline_edit = self.create_lineedit("", 'edge_line_columns',
                                             tip="Enter values separated by commas ','",
                                             alignment=Qt.Horizontal,
                                             regex="[0-9]+(,[0-9]+)*")
        edgeline_edit_label = QLabel(_("characters"))
        edgeline_box.toggled.connect(edgeline_edit.setEnabled)
        edgeline_box.toggled.connect(edgeline_edit_label.setEnabled)
        edgeline_edit.setEnabled(self.get_option('edge_line'))
        edgeline_edit_label.setEnabled(self.get_option('edge_line'))

        currentline_box = newcb(_("Highlight current line"),
                                'highlight_current_line')
        currentcell_box = newcb(_("Highlight current cell"),
                                'highlight_current_cell')
        occurrence_box = newcb(_("Highlight occurrences after"),
                              'occurrence_highlighting')
        occurrence_spin = self.create_spinbox("", _(" ms"),
                                             'occurrence_highlighting/timeout',
                                             min_=100, max_=1000000, step=100)
        occurrence_box.toggled.connect(occurrence_spin.spinbox.setEnabled)
        occurrence_box.toggled.connect(occurrence_spin.slabel.setEnabled)
        occurrence_spin.spinbox.setEnabled(
                self.get_option('occurrence_highlighting'))
        occurrence_spin.slabel.setEnabled(
                self.get_option('occurrence_highlighting'))

        wrap_mode_box = newcb(_("Wrap lines"), 'wrap')
        scroll_past_end_box = newcb(_("Scroll past the end"),
                                    'scroll_past_end')

        display_layout = QGridLayout()
        display_layout.addWidget(linenumbers_box, 0, 0)
        display_layout.addWidget(blanks_box, 1, 0)
        display_layout.addWidget(edgeline_box, 2, 0)
        display_layout.addWidget(edgeline_edit, 2, 1)
        display_layout.addWidget(edgeline_edit_label, 2, 2)
        display_layout.addWidget(currentline_box, 3, 0)
        display_layout.addWidget(currentcell_box, 4, 0)
        display_layout.addWidget(occurrence_box, 5, 0)
        display_layout.addWidget(occurrence_spin.spinbox, 5, 1)
        display_layout.addWidget(occurrence_spin.slabel, 5, 2)
        display_layout.addWidget(wrap_mode_box, 6, 0)
        display_layout.addWidget(scroll_past_end_box, 7, 0)
        display_h_layout = QHBoxLayout()
        display_h_layout.addLayout(display_layout)
        display_h_layout.addStretch(1)
        display_group.setLayout(display_h_layout)

        run_group = QGroupBox(_("Run"))
        saveall_box = newcb(_("Save all files before running script"),
                            'save_all_before_run')

        run_selection_group = QGroupBox(_("Run selection"))
        focus_box = newcb(_("Maintain focus in the Editor after running cells "
                            "or selections"), 'focus_to_editor')

        introspection_group = QGroupBox(_("Introspection"))
        rope_is_installed = programs.is_module_installed('rope')
        if rope_is_installed:
            completion_box = newcb(_("Automatic code completion"),
                                   'codecompletion/auto')
            case_comp_box = newcb(_("Case sensitive code completion"),
                                  'codecompletion/case_sensitive')
            comp_enter_box = newcb(_("Enter key selects completion"),
                                   'codecompletion/enter_key')
            calltips_box = newcb(_("Display balloon tips"), 'calltips')
            gotodef_box = newcb(_("Link to object definition"),
                  'go_to_definition',
                  tip=_("If this option is enabled, clicking on an object\n"
                        "name (left-click + Ctrl key) will go this object\n"
                        "definition (if resolved)."))
        else:
            rope_label = QLabel(_("<b>Warning:</b><br>"
                                  "The Python module <i>rope</i> is not "
                                  "installed on this computer: calltips, "
                                  "code completion and go-to-definition "
                                  "features won't be available."))
            rope_label.setWordWrap(True)
        
        sourcecode_group = QGroupBox(_("Source code"))
        closepar_box = newcb(_("Automatic insertion of parentheses, braces "
                                                               "and brackets"),
                             'close_parentheses')
        close_quotes_box = newcb(_("Automatic insertion of closing quotes"),
                             'close_quotes')
        add_colons_box = newcb(_("Automatic insertion of colons after 'for', "
                                                          "'if', 'def', etc"),
                               'add_colons')
        autounindent_box = newcb(_("Automatic indentation after 'else', "
                                   "'elif', etc."), 'auto_unindent')
        indent_chars_box = self.create_combobox(_("Indentation characters: "),
                                        ((_("2 spaces"), '*  *'),
                                         (_("3 spaces"), '*   *'),
                                         (_("4 spaces"), '*    *'),
                                         (_("5 spaces"), '*     *'),
                                         (_("6 spaces"), '*      *'),
                                         (_("7 spaces"), '*       *'),
                                         (_("8 spaces"), '*        *'),
                                         (_("Tabulations"), '*\t*')), 'indent_chars')
        tabwidth_spin = self.create_spinbox(_("Tab stop width:"), _("spaces"),
                                            'tab_stop_width_spaces', 4, 1, 8, 1)
        def enable_tabwidth_spin(index):
            if index == 7:  # Tabulations
                tabwidth_spin.plabel.setEnabled(True)
                tabwidth_spin.spinbox.setEnabled(True)
            else:
                tabwidth_spin.plabel.setEnabled(False)
                tabwidth_spin.spinbox.setEnabled(False)

        indent_chars_box.combobox.currentIndexChanged.connect(enable_tabwidth_spin)

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
        pep_url = '<a href="http://www.python.org/dev/peps/pep-0008/">PEP8</a>'
        pep8_label = QLabel(_("<i>(Refer to the {} page)</i>").format(pep_url))
        pep8_label.setOpenExternalLinks(True)
        is_pyflakes = codeanalysis.is_pyflakes_installed()
        is_pep8 = codeanalysis.get_checker_executable(
                'pycodestyle') is not None
        pyflakes_box = newcb(_("Real-time code analysis"),
                      'code_analysis/pyflakes', default=True,
                      tip=_("<p>If enabled, Python source code will be analyzed "
                            "using pyflakes, lines containing errors or "
                            "warnings will be highlighted.</p>"
                            "<p><u>Note</u>: add <b>analysis:ignore</b> in "
                            "a comment to ignore code analysis "
                            "warnings.</p>"))
        pyflakes_box.setEnabled(is_pyflakes)
        if not is_pyflakes:
            pyflakes_box.setToolTip(_("Code analysis requires pyflakes %s+") %
                                    codeanalysis.PYFLAKES_REQVER)
        pep8_box = newcb(_("Real-time code style analysis"),
                      'code_analysis/pep8', default=False,
                      tip=_("<p>If enabled, Python source code will be analyzed "
                            "using pycodestyle, lines that are not following PEP8 "
                            "style guide will be highlighted.</p>"
                            "<p><u>Note</u>: add <b>analysis:ignore</b> in "
                            "a comment to ignore style analysis "
                            "warnings.</p>"))
        pep8_box.setEnabled(is_pep8)
        todolist_box = newcb(_("Code annotations (TODO, FIXME, XXX, HINT, TIP,"
                               " @todo, HACK, BUG, OPTIMIZE, !!!, ???)"),
                             'todo_list', default=True)
        realtime_radio = self.create_radiobutton(
                                            _("Perform analysis when "
                                                    "saving file and every"),
                                            'realtime_analysis', True)
        saveonly_radio = self.create_radiobutton(
                                            _("Perform analysis only "
                                                    "when saving file"),
                                            'onsave_analysis')
        af_spin = self.create_spinbox("", _(" ms"), 'realtime_analysis/timeout',
                                      min_=100, max_=1000000, step=100)
        af_layout = QHBoxLayout()
        af_layout.addWidget(realtime_radio)
        af_layout.addWidget(af_spin)
        
        run_layout = QVBoxLayout()
        run_layout.addWidget(saveall_box)
        run_group.setLayout(run_layout)
        
        run_selection_layout = QVBoxLayout()
        run_selection_layout.addWidget(focus_box)
        run_selection_group.setLayout(run_selection_layout)
        
        introspection_layout = QVBoxLayout()
        if rope_is_installed:
            introspection_layout.addWidget(calltips_box)
            introspection_layout.addWidget(completion_box)
            introspection_layout.addWidget(case_comp_box)
            introspection_layout.addWidget(comp_enter_box)
            introspection_layout.addWidget(gotodef_box)
        else:
            introspection_layout.addWidget(rope_label)
        introspection_group.setLayout(introspection_layout)
        
        analysis_layout = QVBoxLayout()
        analysis_layout.addWidget(pyflakes_box)
        analysis_pep_layout = QHBoxLayout() 
        analysis_pep_layout.addWidget(pep8_box)
        analysis_pep_layout.addWidget(pep8_label)
        analysis_layout.addLayout(analysis_pep_layout)
        analysis_layout.addWidget(todolist_box)
        analysis_layout.addLayout(af_layout)
        analysis_layout.addWidget(saveonly_radio)
        analysis_group.setLayout(analysis_layout)
        
        sourcecode_layout = QVBoxLayout()
        sourcecode_layout.addWidget(closepar_box)
        sourcecode_layout.addWidget(autounindent_box)
        sourcecode_layout.addWidget(add_colons_box)
        sourcecode_layout.addWidget(close_quotes_box)
        indent_tab_layout = QHBoxLayout()
        indent_tab_grid_layout = QGridLayout()
        indent_tab_grid_layout.addWidget(indent_chars_box.label, 0, 0)
        indent_tab_grid_layout.addWidget(indent_chars_box.combobox, 0, 1)
        indent_tab_grid_layout.addWidget(tabwidth_spin.plabel, 1, 0)
        indent_tab_grid_layout.addWidget(tabwidth_spin.spinbox, 1, 1)
        indent_tab_grid_layout.addWidget(tabwidth_spin.slabel, 1, 2)
        indent_tab_layout.addLayout(indent_tab_grid_layout)
        indent_tab_layout.addStretch(1)
        sourcecode_layout.addLayout(indent_tab_layout)
        sourcecode_layout.addWidget(tab_mode_box)
        sourcecode_layout.addWidget(ibackspace_box)
        sourcecode_layout.addWidget(removetrail_box)
        sourcecode_group.setLayout(sourcecode_layout)

        eol_group = QGroupBox(_("End-of-line characters"))
        eol_label = QLabel(_("When opening a text file containing "
                             "mixed end-of-line characters (this may "
                             "raise syntax errors in the consoles "
                             "on Windows platforms), Spyder may fix the "
                             "file automatically."))
        eol_label.setWordWrap(True)
        check_eol_box = newcb(_("Fix automatically and show warning "
                                "message box"),
                              'check_eol_chars', default=True)
        convert_eol_on_save_box = newcb(_("On Save: convert EOL characters"
                                          " to"),
                                        'convert_eol_on_save', default=False)
        eol_combo_choices = ((_("LF (UNIX)"), 'LF'),
                             (_("CRLF (Windows)"), 'CRLF'),
                             (_("CR (Mac)"), 'CR'),
                             )
        convert_eol_on_save_combo = self.create_combobox("",
                                                         eol_combo_choices,
                                                         'convert_eol_on_save_to',
                                                         )
        convert_eol_on_save_box.toggled.connect(convert_eol_on_save_combo.setEnabled)
        convert_eol_on_save_combo.setEnabled(
                self.get_option('convert_eol_on_save'))

        eol_on_save_layout = QHBoxLayout()
        eol_on_save_layout.addWidget(convert_eol_on_save_box)
        eol_on_save_layout.addWidget(convert_eol_on_save_combo)

        eol_layout = QVBoxLayout()
        eol_layout.addWidget(eol_label)
        eol_layout.addWidget(check_eol_box)
        eol_layout.addLayout(eol_on_save_layout)
        eol_group.setLayout(eol_layout)
        
        tabs = QTabWidget()
        tabs.addTab(self.create_tab(interface_group, display_group),
                    _("Display"))
        tabs.addTab(self.create_tab(introspection_group, analysis_group),
                    _("Code Introspection/Analysis"))
        tabs.addTab(self.create_tab(template_btn, run_group, run_selection_group,
                                    sourcecode_group, eol_group),
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
    TEMPFILE_PATH = get_conf_path('temp.py')
    TEMPLATE_PATH = get_conf_path('template.py')
    DISABLE_ACTIONS_WHEN_HIDDEN = False # SpyderPluginWidget class attribute
    
    # Signals
    run_in_current_ipyclient = Signal(str, str, str, bool, bool, bool, bool)
    exec_in_extconsole = Signal(str, bool)
    redirect_stdio = Signal(bool)
    open_dir = Signal(str)
    breakpoints_saved = Signal()
    run_in_current_extconsole = Signal(str, str, str, bool, bool)
    open_file_update = Signal(str)

    def __init__(self, parent, ignore_last_opened_files=False):
        SpyderPluginWidget.__init__(self, parent)

        self.__set_eol_chars = True

        # Creating template if it doesn't already exist
        if not osp.isfile(self.TEMPLATE_PATH):
            if os.name == "nt":
                shebang = []
            else:
                shebang = ['#!/usr/bin/env python' + ('2' if PY2 else '3')]
            header = shebang + [
                '# -*- coding: utf-8 -*-',
                '"""', 'Created on %(date)s', '',
                '@author: %(username)s', '"""', '', '']
            encoding.write(os.linesep.join(header), self.TEMPLATE_PATH, 'utf-8')

        self.projects = None
        self.outlineexplorer = None
        self.help = None

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
        self.checkable_actions = {}
        
        # Initialize plugin
        self.initialize_plugin()
        self.options_button.hide()
        
        # Configuration dialog size
        self.dialog_size = None
        
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

        # Don't start IntrospectionManager when running tests because
        # it consumes a lot of memory
        if PYTEST and not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
            try:
                from unittest.mock import Mock
            except ImportError:
                from mock import Mock # Python 2
            self.introspector = Mock()
        else:
            self.introspector = IntrospectionManager(
                    extra_path=self.main.get_spyder_pythonpath())

        # Setup new windows:
        self.main.all_actions_defined.connect(self.setup_other_windows)

        # Change module completions when PYTHONPATH changes
        self.main.sig_pythonpath_changed.connect(self.set_path)

        # Find widget
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        self.find_widget.visibility_changed.connect(
                                          lambda vs: self.rehighlight_cells())
        self.register_widget_shortcuts(self.find_widget)

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
        self.setFocusPolicy(Qt.ClickFocus)
        
        # Editor's splitter state
        state = self.get_option('splitter_state', None)
        if state is not None:
            self.splitter.restoreState( QByteArray().fromHex(
                    str(state).encode('utf-8')) )
        
        self.recent_files = self.get_option('recent_files', [])
        self.untitled_num = 0

        # Parameters of last file execution:
        self.__last_ic_exec = None # internal console
        self.__last_ec_exec = None # external console

        # File types and filters used by the Open dialog
        self.edit_filetypes = None
        self.edit_filters = None

        self.__ignore_cursor_position = False
        current_editor = self.get_current_editor()
        if current_editor is not None:
            filename = self.get_current_filename()
            position = current_editor.get_position('cursor')
            self.add_cursor_position_to_history(filename, position)
        self.update_cursorpos_actions()
        self.set_path()
        
    def set_projects(self, projects):
        self.projects = projects

    @Slot()
    def show_hide_projects(self):
        if self.projects is not None:
            dw = self.projects.dockwidget
            if dw.isVisible():
                dw.hide()
            else:
                dw.show()
                dw.raise_()
            self.switch_to_plugin()
        
    def set_outlineexplorer(self, outlineexplorer):
        self.outlineexplorer = outlineexplorer
        for editorstack in self.editorstacks:
            # Pass the OutlineExplorer widget to the stacks because they
            # don't need the plugin
            editorstack.set_outlineexplorer(self.outlineexplorer.explorer)
        self.editorstacks[0].initialize_outlineexplorer()
        self.outlineexplorer.explorer.edit_goto.connect(
                           lambda filenames, goto, word:
                           self.load(filenames=filenames, goto=goto, word=word,
                                     editorwindow=self))
        self.outlineexplorer.explorer.edit.connect(
                             lambda filenames:
                             self.load(filenames=filenames, editorwindow=self))

    def set_help(self, help_plugin):
        self.help = help_plugin
        for editorstack in self.editorstacks:
            editorstack.set_help(self.help)

    #------ Private API --------------------------------------------------------
    def restore_scrollbar_position(self):
        """Restoring scrollbar position after main window is visible"""
        # Widget is now visible, we may center cursor on top level editor:
        try:
            self.get_current_editor().centerCursor()
        except AttributeError:
            pass
            
    #------ SpyderPluginWidget API ---------------------------------------------    
    def get_plugin_title(self):
        """Return widget title"""
        title = _('Editor')
        if self.dockwidget:
            filename = self.get_current_filename()
            if self.dockwidget.dock_tabbar:
                if filename and self.dockwidget.dock_tabbar.count() < 2:
                    title += ' - ' + to_text_string(filename)
            else:
                 title += ' - ' + to_text_string(filename)
        return title

    def get_plugin_icon(self):
        """Return widget icon."""
        return ima.icon('edit')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to.

        This happens when plugin's dockwidget is raised on top-level.
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
        self.sig_update_plugin_title.emit()
    
    def refresh_plugin(self):
        """Refresh editor plugin"""
        editorstack = self.get_current_editorstack()
        editorstack.refresh()
        self.refresh_save_all_action()
        
    def closing_plugin(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        state = self.splitter.saveState()
        self.set_option('splitter_state', qbytearray_to_str(state))
        filenames = []
        editorstack = self.editorstacks[0]

        active_project_path = None
        if self.projects is not None:
             active_project_path = self.projects.get_active_project_path()
        if not active_project_path:
            self.set_open_filenames()
        else:
            self.projects.set_project_filenames(
                [finfo.filename for finfo in editorstack.data])

        self.set_option('layout_settings',
                        self.editorsplitter.get_layout_settings())
        self.set_option('windows_layout_settings',
                    [win.get_layout_settings() for win in self.editorwindows])
#        self.set_option('filenames', filenames)
        self.set_option('recent_files', self.recent_files)
        try:
            if not editorstack.save_if_changed(cancelable) and cancelable:
                return False
            else:
                for win in self.editorwindows[:]:
                    win.close()
                return True
        except IndexError:
            return True

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        # ---- File menu and toolbar ----
        self.new_action = create_action(
                self,
                _("&New file..."),
                icon=ima.icon('filenew'), tip=_("New file"),
                triggered=self.new,
                context=Qt.WidgetShortcut
        )
        self.register_shortcut(self.new_action, context="Editor",
                               name="New file", add_sc_to_tip=True)

        self.open_last_closed_action = create_action(
                self,
                _("O&pen last closed"),
                tip=_("Open last closed"),
                triggered=self.open_last_closed
        )
        self.register_shortcut(self.open_last_closed_action, context="Editor",
                               name="Open last closed")
        
        self.open_action = create_action(self, _("&Open..."),
                icon=ima.icon('fileopen'), tip=_("Open file"),
                triggered=self.load,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.open_action, context="Editor",
                               name="Open file", add_sc_to_tip=True)

        self.revert_action = create_action(self, _("&Revert"),
                icon=ima.icon('revert'), tip=_("Revert file from disk"),
                triggered=self.revert)

        self.save_action = create_action(self, _("&Save"),
                icon=ima.icon('filesave'), tip=_("Save file"),
                triggered=self.save,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.save_action, context="Editor",
                               name="Save file", add_sc_to_tip=True)

        self.save_all_action = create_action(self, _("Sav&e all"),
                icon=ima.icon('save_all'), tip=_("Save all files"),
                triggered=self.save_all,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.save_all_action, context="Editor",
                               name="Save all", add_sc_to_tip=True)

        save_as_action = create_action(self, _("Save &as..."), None,
                ima.icon('filesaveas'), tip=_("Save current file as..."),
                triggered=self.save_as,
                context=Qt.WidgetShortcut)
        self.register_shortcut(save_as_action, "Editor", "Save As")

        save_copy_as_action = create_action(self, _("Save copy as..."), None,
                ima.icon('filesaveas'), _("Save copy of current file as..."),
                triggered=self.save_copy_as)

        print_preview_action = create_action(self, _("Print preview..."),
                tip=_("Print preview..."), triggered=self.print_preview)
        self.print_action = create_action(self, _("&Print..."),
                icon=ima.icon('print'), tip=_("Print current file..."),
                triggered=self.print_file)
        # Shortcut for close_action is defined in widgets/editor.py
        self.close_action = create_action(self, _("&Close"),
                icon=ima.icon('fileclose'), tip=_("Close current file"),
                triggered=self.close_file)

        self.close_all_action = create_action(self, _("C&lose all"),
                icon=ima.icon('filecloseall'), tip=_("Close all opened files"),
                triggered=self.close_all_files,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.close_all_action, context="Editor",
                               name="Close all")

        # ---- Find menu and toolbar ----
        _text = _("&Find text")
        find_action = create_action(self, _text, icon=ima.icon('find'),
                                    tip=_text, triggered=self.find,
                                    context=Qt.WidgetShortcut)
        self.register_shortcut(find_action, context="_",
                               name="Find text", add_sc_to_tip=True)
        find_next_action = create_action(self, _("Find &next"),
                                         icon=ima.icon('findnext'),
                                         triggered=self.find_next,
                                         context=Qt.WidgetShortcut)
        self.register_shortcut(find_next_action, context="_",
                               name="Find next")
        find_previous_action = create_action(self, _("Find &previous"),
                                             icon=ima.icon('findprevious'),
                                             triggered=self.find_previous,
                                             context=Qt.WidgetShortcut)
        self.register_shortcut(find_previous_action, context="_",
                               name="Find previous")
        _text = _("&Replace text")
        replace_action = create_action(self, _text, icon=ima.icon('replace'),
                                       tip=_text, triggered=self.replace,
                                       context=Qt.WidgetShortcut)
        self.register_shortcut(replace_action, context="_",
                               name="Replace text")

        # ---- Debug menu and toolbar ----
        set_clear_breakpoint_action = create_action(self,
                                    _("Set/Clear breakpoint"),
                                    icon=ima.icon('breakpoint_big'),
                                    triggered=self.set_or_clear_breakpoint,
                                    context=Qt.WidgetShortcut)
        self.register_shortcut(set_clear_breakpoint_action, context="Editor",
                               name="Breakpoint")
        set_cond_breakpoint_action = create_action(self,
                            _("Set/Edit conditional breakpoint"),
                            icon=ima.icon('breakpoint_cond_big'),
                            triggered=self.set_or_edit_conditional_breakpoint,
                            context=Qt.WidgetShortcut)
        self.register_shortcut(set_cond_breakpoint_action, context="Editor",
                               name="Conditional breakpoint")
        clear_all_breakpoints_action = create_action(self,
                                    _('Clear breakpoints in all files'),
                                    triggered=self.clear_all_breakpoints)
        self.winpdb_action = create_action(self, _("Debug with winpdb"),
                                           triggered=self.run_winpdb)
        self.winpdb_action.setEnabled(WINPDB_PATH is not None and PY2)

        # --- Debug toolbar ---
        debug_action = create_action(self, _("&Debug"),
                                     icon=ima.icon('debug'),
                                     tip=_("Debug file"),
                                     triggered=self.debug_file)
        self.register_shortcut(debug_action, context="_", name="Debug",
                               add_sc_to_tip=True)

        debug_next_action = create_action(self, _("Step"),
               icon=ima.icon('arrow-step-over'), tip=_("Run current line"),
               triggered=lambda: self.debug_command("next"))
        self.register_shortcut(debug_next_action, "_", "Debug Step Over",
                               add_sc_to_tip=True)

        debug_continue_action = create_action(self, _("Continue"),
               icon=ima.icon('arrow-continue'),
               tip=_("Continue execution until next breakpoint"),
               triggered=lambda: self.debug_command("continue"))
        self.register_shortcut(debug_continue_action, "_", "Debug Continue",
                               add_sc_to_tip=True)

        debug_step_action = create_action(self, _("Step Into"),
               icon=ima.icon('arrow-step-in'),
               tip=_("Step into function or method of current line"),
               triggered=lambda: self.debug_command("step"))
        self.register_shortcut(debug_step_action, "_", "Debug Step Into",
                               add_sc_to_tip=True)

        debug_return_action = create_action(self, _("Step Return"),
               icon=ima.icon('arrow-step-out'),
               tip=_("Run until current function or method returns"),
               triggered=lambda: self.debug_command("return"))
        self.register_shortcut(debug_return_action, "_", "Debug Step Return",
                               add_sc_to_tip=True)

        debug_exit_action = create_action(self, _("Stop"),
               icon=ima.icon('stop_debug'), tip=_("Stop debugging"),
               triggered=lambda: self.debug_command("exit"))
        self.register_shortcut(debug_exit_action, "_", "Debug Exit",
                               add_sc_to_tip=True)

        # --- Run toolbar ---
        run_action = create_action(self, _("&Run"), icon=ima.icon('run'),
                                   tip=_("Run file"),
                                   triggered=self.run_file)
        self.register_shortcut(run_action, context="_", name="Run",
                               add_sc_to_tip=True)

        configure_action = create_action(self, _("&Configuration per file..."),
                                         icon=ima.icon('run_settings'),
                               tip=_("Run settings"),
                               menurole=QAction.NoRole,
                               triggered=self.edit_run_configurations)
        self.register_shortcut(configure_action, context="_",
                               name="Configure", add_sc_to_tip=True)

        re_run_action = create_action(self, _("Re-run &last script"),
                                      icon=ima.icon('run_again'),
                            tip=_("Run again last file"),
                            triggered=self.re_run_file)
        self.register_shortcut(re_run_action, context="_",
                               name="Re-run last script",
                               add_sc_to_tip=True)

        run_selected_action = create_action(self, _("Run &selection or "
                                                    "current line"),
                                            icon=ima.icon('run_selection'),
                                            tip=_("Run selection or "
                                                  "current line"),
                                            triggered=self.run_selection,
                                            context=Qt.WidgetShortcut)
        self.register_shortcut(run_selected_action, context="Editor",
                               name="Run selection", add_sc_to_tip=True)

        run_cell_action = create_action(self,
                            _("Run cell"),
                            icon=ima.icon('run_cell'),
                            shortcut=QKeySequence(RUN_CELL_SHORTCUT),
                            tip=_("Run current cell (Ctrl+Enter)\n"
                                  "[Use #%% to create cells]"),
                            triggered=self.run_cell,
                            context=Qt.WidgetShortcut)

        run_cell_advance_action = create_action(self,
                   _("Run cell and advance"),
                   icon=ima.icon('run_cell_advance'),
                   shortcut=QKeySequence(RUN_CELL_AND_ADVANCE_SHORTCUT),
                   tip=_("Run current cell and go to the next one "
                         "(Shift+Enter)"),
                   triggered=self.run_cell_and_advance,
                   context=Qt.WidgetShortcut)

        re_run_last_cell_action = create_action(self,
                   _("Re-run last cell"),
                   tip=_("Re run last cell "),
                   triggered=self.re_run_last_cell,
                   context=Qt.WidgetShortcut)
        self.register_shortcut(re_run_last_cell_action,
                               context="Editor",
                               name='re-run last cell',
                               add_sc_to_tip=True)

        # --- Source code Toolbar ---
        self.todo_list_action = create_action(self,
                _("Show todo list"), icon=ima.icon('todo_list'),
                tip=_("Show comments list (TODO/FIXME/XXX/HINT/TIP/@todo/"
                      "HACK/BUG/OPTIMIZE/!!!/???)"),
                triggered=self.go_to_next_todo)
        self.todo_menu = QMenu(self)
        self.todo_list_action.setMenu(self.todo_menu)
        self.todo_menu.aboutToShow.connect(self.update_todo_menu)
        
        self.warning_list_action = create_action(self,
                _("Show warning/error list"), icon=ima.icon('wng_list'),
                tip=_("Show code analysis warnings/errors"),
                triggered=self.go_to_next_warning)
        self.warning_menu = QMenu(self)
        self.warning_list_action.setMenu(self.warning_menu)
        self.warning_menu.aboutToShow.connect(self.update_warning_menu)
        self.previous_warning_action = create_action(self,
                _("Previous warning/error"), icon=ima.icon('prev_wng'),
                tip=_("Go to previous code analysis warning/error"),
                triggered=self.go_to_previous_warning,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.previous_warning_action,
                               context="Editor",
                               name="Previous warning",
                               add_sc_to_tip=True)
        self.next_warning_action = create_action(self,
                _("Next warning/error"), icon=ima.icon('next_wng'),
                tip=_("Go to next code analysis warning/error"),
                triggered=self.go_to_next_warning,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.next_warning_action,
                               context="Editor",
                               name="Next warning",
                               add_sc_to_tip=True)
        
        self.previous_edit_cursor_action = create_action(self,
                _("Last edit location"), icon=ima.icon('last_edit_location'),
                tip=_("Go to last edit location"),
                triggered=self.go_to_last_edit_location,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.previous_edit_cursor_action,
                               context="Editor",
                               name="Last edit location",
                               add_sc_to_tip=True)
        self.previous_cursor_action = create_action(self,
                _("Previous cursor position"), icon=ima.icon('prev_cursor'),
                tip=_("Go to previous cursor position"),
                triggered=self.go_to_previous_cursor_position,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.previous_cursor_action,
                               context="Editor", 
                               name="Previous cursor position",
                               add_sc_to_tip=True)
        self.next_cursor_action = create_action(self,
                _("Next cursor position"), icon=ima.icon('next_cursor'),
                tip=_("Go to next cursor position"),
                triggered=self.go_to_next_cursor_position,
                context=Qt.WidgetShortcut)
        self.register_shortcut(self.next_cursor_action,
                               context="Editor",
                               name="Next cursor position",
                               add_sc_to_tip=True)

        # --- Edit Toolbar ---
        self.toggle_comment_action = create_action(self,
                _("Comment")+"/"+_("Uncomment"), icon=ima.icon('comment'),
                tip=_("Comment current line or selection"),
                triggered=self.toggle_comment, context=Qt.WidgetShortcut)
        self.register_shortcut(self.toggle_comment_action, context="Editor",
                               name="Toggle comment")
        blockcomment_action = create_action(self, _("Add &block comment"),
                tip=_("Add block comment around "
                            "current line or selection"),
                triggered=self.blockcomment, context=Qt.WidgetShortcut)
        self.register_shortcut(blockcomment_action, context="Editor",
                               name="Blockcomment")
        unblockcomment_action = create_action(self,
                _("R&emove block comment"),
                tip = _("Remove comment block around "
                              "current line or selection"),
                triggered=self.unblockcomment, context=Qt.WidgetShortcut)
        self.register_shortcut(unblockcomment_action, context="Editor",
                               name="Unblockcomment")
                
        # ----------------------------------------------------------------------
        # The following action shortcuts are hard-coded in CodeEditor
        # keyPressEvent handler (the shortcut is here only to inform user):
        # (context=Qt.WidgetShortcut -> disable shortcut for other widgets)
        self.indent_action = create_action(self,
                _("Indent"), "Tab", icon=ima.icon('indent'),
                tip=_("Indent current line or selection"),
                triggered=self.indent, context=Qt.WidgetShortcut)
        self.unindent_action = create_action(self,
                _("Unindent"), "Shift+Tab", icon=ima.icon('unindent'),
                tip=_("Unindent current line or selection"),
                triggered=self.unindent, context=Qt.WidgetShortcut)

        self.text_uppercase_action = create_action(self,
                _("Toggle Uppercase"),
                tip=_("Change to uppercase current line or selection"),
                triggered=self.text_uppercase, context=Qt.WidgetShortcut)
        self.register_shortcut(self.text_uppercase_action, context="Editor",
                               name="transform to uppercase")

        self.text_lowercase_action = create_action(self,
                _("Toggle Lowercase"),
                tip=_("Change to lowercase current line or selection"),
                triggered=self.text_lowercase, context=Qt.WidgetShortcut)
        self.register_shortcut(self.text_lowercase_action, context="Editor",
                               name="transform to lowercase")
        # ----------------------------------------------------------------------
        
        self.win_eol_action = create_action(self,
                           _("Carriage return and line feed (Windows)"),
                           toggled=lambda checked: self.toggle_eol_chars('nt', checked))
        self.linux_eol_action = create_action(self,
                           _("Line feed (UNIX)"),
                           toggled=lambda checked: self.toggle_eol_chars('posix', checked))
        self.mac_eol_action = create_action(self,
                           _("Carriage return (Mac)"),
                           toggled=lambda checked: self.toggle_eol_chars('mac', checked))
        eol_action_group = QActionGroup(self)
        eol_actions = (self.win_eol_action, self.linux_eol_action,
                       self.mac_eol_action)
        add_actions(eol_action_group, eol_actions)
        eol_menu = QMenu(_("Convert end-of-line characters"), self)
        add_actions(eol_menu, eol_actions)
        
        trailingspaces_action = create_action(self,
                                      _("Remove trailing spaces"),
                                      triggered=self.remove_trailing_spaces)

        # Checkable actions
        showblanks_action = self._create_checkable_action(
                _("Show blank spaces"), 'blank_spaces', 'set_blanks_enabled')

        scrollpastend_action = self._create_checkable_action(
                 _("Scroll past the end"), 'scroll_past_end',
                 'set_scrollpastend_enabled')

        showindentguides_action = self._create_checkable_action(
                _("Show indent guides."), 'indent_guides', 'set_indent_guides')

        show_classfunc_dropdown_action = self._create_checkable_action(
                _("Show selector for classes and functions."),
                'show_class_func_dropdown', 'set_classfunc_dropdown_visible')

        showcode_analysis_pep8_action = self._create_checkable_action(
                _("Show code style warnings (pep8)"),
                'code_analysis/pep8', 'set_pep8_enabled')

        self.checkable_actions = {
                'blank_spaces': showblanks_action,
                'scroll_past_end': scrollpastend_action,
                'indent_guides': showindentguides_action,
                'show_class_func_dropdown': show_classfunc_dropdown_action,
                'code_analysis/pep8': showcode_analysis_pep8_action}

        fixindentation_action = create_action(self, _("Fix indentation"),
                      tip=_("Replace tab characters by space characters"),
                      triggered=self.fix_indentation)

        gotoline_action = create_action(self, _("Go to line..."),
                                        icon=ima.icon('gotoline'),
                                        triggered=self.go_to_line,
                                        context=Qt.WidgetShortcut)
        self.register_shortcut(gotoline_action, context="Editor",
                               name="Go to line")

        workdir_action = create_action(self,
                _("Set console working directory"),
                icon=ima.icon('DirOpenIcon'),
                tip=_("Set current console (and file explorer) working "
                            "directory to current script directory"),
                triggered=self.__set_workdir)

        self.max_recent_action = create_action(self,
            _("Maximum number of recent files..."),
            triggered=self.change_max_recent_files)
        self.clear_recent_action = create_action(self,
            _("Clear this list"), tip=_("Clear recent files list"),
            triggered=self.clear_recent_files)

        # ---- File menu/toolbar construction ----
        self.recent_file_menu = QMenu(_("Open &recent"), self)
        self.recent_file_menu.aboutToShow.connect(self.update_recent_file_menu)

        file_menu_actions = [self.new_action,
                             MENU_SEPARATOR,
                             self.open_action,
                             self.open_last_closed_action,
                             self.recent_file_menu,
                             MENU_SEPARATOR,
                             MENU_SEPARATOR,
                             self.save_action,
                             self.save_all_action,
                             save_as_action,
                             save_copy_as_action,
                             self.revert_action,
                             MENU_SEPARATOR,
                             print_preview_action,
                             self.print_action,
                             MENU_SEPARATOR,
                             self.close_action,
                             self.close_all_action,
                             MENU_SEPARATOR]

        self.main.file_menu_actions += file_menu_actions
        file_toolbar_actions = ([self.new_action, self.open_action,
                                self.save_action, self.save_all_action] +
                                self.main.file_toolbar_actions)

        self.main.file_toolbar_actions = file_toolbar_actions

        # ---- Find menu/toolbar construction ----
        self.main.search_menu_actions = [find_action,
                                         find_next_action,
                                         find_previous_action,
                                         replace_action]
        self.main.search_toolbar_actions = [find_action,
                                            find_next_action,
                                            replace_action]

        # ---- Edit menu/toolbar construction ----
        self.edit_menu_actions = [self.toggle_comment_action,
                                  blockcomment_action, unblockcomment_action,
                                  self.indent_action, self.unindent_action,
                                  self.text_uppercase_action,
                                  self.text_lowercase_action]
        self.main.edit_menu_actions += [MENU_SEPARATOR] + self.edit_menu_actions
        edit_toolbar_actions = [self.toggle_comment_action,
                                self.unindent_action, self.indent_action]
        self.main.edit_toolbar_actions += edit_toolbar_actions

        # ---- Search menu/toolbar construction ----
        self.search_menu_actions = [gotoline_action]
        self.main.search_menu_actions += self.search_menu_actions
        self.main.search_toolbar_actions += [gotoline_action]
          
        # ---- Run menu/toolbar construction ----
        run_menu_actions = [run_action, run_cell_action,
                            run_cell_advance_action,
                            re_run_last_cell_action, MENU_SEPARATOR,
                            run_selected_action, re_run_action,
                            configure_action, MENU_SEPARATOR]
        self.main.run_menu_actions += run_menu_actions
        run_toolbar_actions = [run_action, run_cell_action,
                               run_cell_advance_action, run_selected_action,
                               re_run_action]
        self.main.run_toolbar_actions += run_toolbar_actions

        # ---- Debug menu/toolbar construction ----
        # NOTE: 'list_breakpoints' is used by the breakpoints 
        # plugin to add its "List breakpoints" action to this
        # menu
        debug_menu_actions = [debug_action,
                              debug_next_action,
                              debug_step_action,
                              debug_return_action,
                              debug_continue_action,
                              debug_exit_action,
                              MENU_SEPARATOR,
                              set_clear_breakpoint_action,
                              set_cond_breakpoint_action,
                              clear_all_breakpoints_action,
                              'list_breakpoints',
                              MENU_SEPARATOR,
                              self.winpdb_action]
        self.main.debug_menu_actions += debug_menu_actions
        debug_toolbar_actions = [debug_action, debug_next_action,
                                 debug_step_action, debug_return_action,
                                 debug_continue_action, debug_exit_action]
        self.main.debug_toolbar_actions += debug_toolbar_actions

        # ---- Source menu/toolbar construction ----
        source_menu_actions = [eol_menu,
                               showblanks_action,
                               scrollpastend_action,
                               showindentguides_action,
                               show_classfunc_dropdown_action,
                               showcode_analysis_pep8_action,
                               trailingspaces_action,
                               fixindentation_action,
                               MENU_SEPARATOR,
                               self.todo_list_action,
                               self.warning_list_action,
                               self.previous_warning_action,
                               self.next_warning_action,
                               MENU_SEPARATOR,
                               self.previous_edit_cursor_action,
                               self.previous_cursor_action,
                               self.next_cursor_action]
        self.main.source_menu_actions += source_menu_actions

        source_toolbar_actions = [self.todo_list_action,
                                  self.warning_list_action,
                                  self.previous_warning_action,
                                  self.next_warning_action,
                                  MENU_SEPARATOR,
                                  self.previous_edit_cursor_action,
                                  self.previous_cursor_action,
                                  self.next_cursor_action]
        self.main.source_toolbar_actions += source_toolbar_actions

        # ---- Dock widget and file dependent actions ----
        self.dock_toolbar_actions = (file_toolbar_actions +
                                     [MENU_SEPARATOR] +
                                     source_toolbar_actions +
                                     [MENU_SEPARATOR] +
                                     run_toolbar_actions +
                                     [MENU_SEPARATOR] +
                                     debug_toolbar_actions +
                                     [MENU_SEPARATOR] +
                                     edit_toolbar_actions)
        self.pythonfile_dependent_actions = [run_action, configure_action,
                                             set_clear_breakpoint_action,
                                             set_cond_breakpoint_action,
                                             debug_action, run_selected_action,
                                             run_cell_action,
                                             run_cell_advance_action,
                                             re_run_last_cell_action,
                                             blockcomment_action,
                                             unblockcomment_action,
                                             self.winpdb_action]
        self.cythonfile_compatible_actions = [run_action, configure_action]
        self.file_dependent_actions = self.pythonfile_dependent_actions + \
                [self.save_action, save_as_action, save_copy_as_action,
                 print_preview_action, self.print_action,
                 self.save_all_action, gotoline_action, workdir_action,
                 self.close_action, self.close_all_action,
                 self.toggle_comment_action, self.revert_action,
                 self.indent_action, self.unindent_action]
        self.stack_menu_actions = [gotoline_action, workdir_action]
        
        return self.file_dependent_actions
    
    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.main.restore_scrollbar_position.connect(
                                               self.restore_scrollbar_position)
        self.main.console.edit_goto.connect(self.load)
        self.exec_in_extconsole.connect(self.main.execute_in_external_console)
        self.redirect_stdio.connect(self.main.redirect_internalshell_stdio)
        self.open_dir.connect(self.main.workingdirectory.chdir)
        self.set_help(self.main.help)
        if self.main.outlineexplorer is not None:
            self.set_outlineexplorer(self.main.outlineexplorer)
        editorstack = self.get_current_editorstack()
        if not editorstack.data:
            self.__load_temp_file()
        self.main.add_dockwidget(self)
        self.main.add_to_fileswitcher(self, editorstack.tabs, editorstack.data,
                                      ima.icon('TextFileIcon'))

    def update_font(self):
        """Update font from Preferences"""
        font = self.get_plugin_font()
        color_scheme = self.get_color_scheme()
        for editorstack in self.editorstacks:
            editorstack.set_default_font(font, color_scheme)
            completion_size = CONF.get('main', 'completion/size')
            for finfo in editorstack.data:
                comp_widget = finfo.editor.completion_widget
                comp_widget.setup_appearance(completion_size, font)

    def _create_checkable_action(self, text, conf_name, editorstack_method):
        """Helper function to create a checkable action.

        Args:
            text (str): Text to be displayed in the action.
            conf_name (str): configuration setting associated with the action
            editorstack_method (str): name of EditorStack class that will be
                used to update the changes in each editorstack.
        """
        def toogle(checked):
            self._toggle_checkable_action(checked, editorstack_method,
                                          conf_name)
        action = create_action(self, text, toggled=toogle)
        action.setChecked(CONF.get('editor', conf_name))
        return action

    @Slot(bool, str, str)
    def _toggle_checkable_action(self, checked, editorstack_method, conf_name):
        """Handle the toogle of a checkable action.

        Update editorstacks and the configuration.

        Args:
            checked (bool): State of the action.
            editorstack_method (str): name of EditorStack class that will be
                used to update the changes in each editorstack.
            conf_name (str): configuration setting associated with the action.
        """
        if self.editorstacks:
            for editorstack in self.editorstacks:
                try:
                    editorstack.__getattribute__(editorstack_method)(checked)
                except AttributeError as e:
                    debug_print("Error {}".format(str))
                # Run code analysis when `set_pep8_enabled` is toggled
                if editorstack_method == 'set_pep8_enabled':
                    for finfo in editorstack.data:
                        finfo.run_code_analysis(
                                self.get_option('code_analysis/pyflakes'),
                                checked)
        CONF.set('editor', conf_name, checked)

    #------ Focus tabwidget
    def __get_focus_editorstack(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, EditorStack):
            return fwidget
        else:
            for editorstack in self.editorstacks:
                if editorstack.isAncestorOf(fwidget):
                    return editorstack
        
    def set_last_focus_editorstack(self, editorwindow, editorstack):
        self.last_focus_editorstack[editorwindow] = editorstack
        self.last_focus_editorstack[None] = editorstack # very last editorstack
        
    def get_last_focus_editorstack(self, editorwindow=None):
        return self.last_focus_editorstack[editorwindow]
    
    def remove_last_focus_editorstack(self, editorstack):
        for editorwindow, widget in list(self.last_focus_editorstack.items()):
            if widget is editorstack:
                self.last_focus_editorstack[editorwindow] = None
        
    def save_focus_editorstack(self):
        editorstack = self.__get_focus_editorstack()
        if editorstack is not None:
            for win in [self]+self.editorwindows:
                if win.isAncestorOf(editorstack):
                    self.set_last_focus_editorstack(win, editorstack)

    # ------ Handling editorstacks
    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        self.register_widget_shortcuts(editorstack)
        if len(self.editorstacks) > 1 and self.main is not None:
            # The first editostack is registered automatically with Spyder's
            # main window through the `register_plugin` method. Only additional
            # editors added by splitting need to be registered.
            # See Issue #5057.
            self.main.fileswitcher.sig_goto_file.connect(
                      editorstack.set_stack_index)

        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            self.set_last_focus_editorstack(self, editorstack)
            editorstack.set_closable( len(self.editorstacks) > 1 )
            if self.outlineexplorer is not None:
                editorstack.set_outlineexplorer(self.outlineexplorer.explorer)
            editorstack.set_find_widget(self.find_widget)
            editorstack.reset_statusbar.connect(self.readwrite_status.hide)
            editorstack.reset_statusbar.connect(self.encoding_status.hide)
            editorstack.reset_statusbar.connect(self.cursorpos_status.hide)
            editorstack.readonly_changed.connect(
                                        self.readwrite_status.readonly_changed)
            editorstack.encoding_changed.connect(
                                         self.encoding_status.encoding_changed)
            editorstack.sig_editor_cursor_position_changed.connect(
                                 self.cursorpos_status.cursor_position_changed)
            editorstack.sig_refresh_eol_chars.connect(self.eol_status.eol_changed)

        editorstack.set_help(self.help)
        editorstack.set_io_actions(self.new_action, self.open_action,
                                   self.save_action, self.revert_action)
        editorstack.set_tempfile_path(self.TEMPFILE_PATH)
        editorstack.set_introspector(self.introspector)

        settings = (
            ('set_pyflakes_enabled',                'code_analysis/pyflakes'),
            ('set_pep8_enabled',                    'code_analysis/pep8'),
            ('set_todolist_enabled',                'todo_list'),
            ('set_realtime_analysis_enabled',       'realtime_analysis'),
            ('set_realtime_analysis_timeout',       'realtime_analysis/timeout'),
            ('set_blanks_enabled',                  'blank_spaces'),
            ('set_scrollpastend_enabled',           'scroll_past_end'),
            ('set_linenumbers_enabled',             'line_numbers'),
            ('set_edgeline_enabled',                'edge_line'),
            ('set_edgeline_columns',                'edge_line_columns'),
            ('set_indent_guides',                   'indent_guides'),
            ('set_codecompletion_auto_enabled',     'codecompletion/auto'),
            ('set_codecompletion_case_enabled',     'codecompletion/case_sensitive'),
            ('set_codecompletion_enter_enabled',    'codecompletion/enter_key'),
            ('set_calltips_enabled',                'calltips'),
            ('set_go_to_definition_enabled',        'go_to_definition'),
            ('set_focus_to_editor',                 'focus_to_editor'),
            ('set_close_parentheses_enabled',       'close_parentheses'),
            ('set_close_quotes_enabled',            'close_quotes'),
            ('set_add_colons_enabled',              'add_colons'),
            ('set_auto_unindent_enabled',           'auto_unindent'),
            ('set_indent_chars',                    'indent_chars'),
            ('set_tab_stop_width_spaces',           'tab_stop_width_spaces'),
            ('set_wrap_enabled',                    'wrap'),
            ('set_tabmode_enabled',                 'tab_always_indent'),
            ('set_intelligent_backspace_enabled',   'intelligent_backspace'),
            ('set_highlight_current_line_enabled',  'highlight_current_line'),
            ('set_highlight_current_cell_enabled',  'highlight_current_cell'),
            ('set_occurrence_highlighting_enabled',  'occurrence_highlighting'),
            ('set_occurrence_highlighting_timeout',  'occurrence_highlighting/timeout'),
            ('set_checkeolchars_enabled',           'check_eol_chars'),
            ('set_fullpath_sorting_enabled',        'fullpath_sorting'),
            ('set_tabbar_visible',                  'show_tab_bar'),
            ('set_classfunc_dropdown_visible',      'show_class_func_dropdown'),
            ('set_always_remove_trailing_spaces',   'always_remove_trailing_spaces'),
            ('set_convert_eol_on_save',             'convert_eol_on_save'),
            ('set_convert_eol_on_save_to',          'convert_eol_on_save_to'),
                    )
        for method, setting in settings:
            getattr(editorstack, method)(self.get_option(setting))
        editorstack.set_help_enabled(CONF.get('help', 'connect/editor'))
        color_scheme = self.get_color_scheme()
        editorstack.set_default_font(self.get_plugin_font(), color_scheme)

        editorstack.starting_long_process.connect(self.starting_long_process)
        editorstack.ending_long_process.connect(self.ending_long_process)

        # Redirect signals
        editorstack.redirect_stdio.connect(
                                 lambda state: self.redirect_stdio.emit(state))
        editorstack.exec_in_extconsole.connect(
                                    lambda text, option:
                                    self.exec_in_extconsole.emit(text, option))
        editorstack.update_plugin_title.connect(
                                   lambda: self.sig_update_plugin_title.emit())
        editorstack.editor_focus_changed.connect(self.save_focus_editorstack)
        editorstack.editor_focus_changed.connect(self.set_editorstack_for_introspection)
        editorstack.editor_focus_changed.connect(self.main.plugin_focus_changed)
        editorstack.zoom_in.connect(lambda: self.zoom(1))
        editorstack.zoom_out.connect(lambda: self.zoom(-1))
        editorstack.zoom_reset.connect(lambda: self.zoom(0))
        editorstack.sig_new_file.connect(lambda s: self.new(text=s))
        editorstack.sig_new_file[()].connect(self.new)
        editorstack.sig_close_file.connect(self.close_file_in_all_editorstacks)
        editorstack.file_saved.connect(self.file_saved_in_editorstack)
        editorstack.file_renamed_in_data.connect(
                                      self.file_renamed_in_data_in_editorstack)
        editorstack.sig_undock_window.connect(self.undock_plugin)
        editorstack.opened_files_list_changed.connect(
                                                self.opened_files_list_changed)
        editorstack.analysis_results_changed.connect(
                                                 self.analysis_results_changed)
        editorstack.todo_results_changed.connect(self.todo_results_changed)
        editorstack.update_code_analysis_actions.connect(
                                             self.update_code_analysis_actions)
        editorstack.update_code_analysis_actions.connect(
                                                      self.update_todo_actions)
        editorstack.refresh_file_dependent_actions.connect(
                                           self.refresh_file_dependent_actions)
        editorstack.refresh_save_all_action.connect(self.refresh_save_all_action)
        editorstack.sig_refresh_eol_chars.connect(self.refresh_eol_chars)
        editorstack.save_breakpoints.connect(self.save_breakpoints)
        editorstack.text_changed_at.connect(self.text_changed_at)
        editorstack.current_file_changed.connect(self.current_file_changed)
        editorstack.plugin_load.connect(self.load)
        editorstack.plugin_load[()].connect(self.load)
        editorstack.edit_goto.connect(self.load)
        editorstack.sig_save_as.connect(self.save_as)
        editorstack.sig_prev_edit_pos.connect(self.go_to_last_edit_location)
        editorstack.sig_prev_cursor.connect(self.go_to_previous_cursor_position)
        editorstack.sig_next_cursor.connect(self.go_to_next_cursor_position)
        editorstack.sig_prev_warning.connect(self.go_to_previous_warning)
        editorstack.sig_next_warning.connect(self.go_to_next_warning)

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
        for finfo in editorstack.data:
            self.register_widget_shortcuts(finfo.editor)

    @Slot(str, str)
    def close_file_in_all_editorstacks(self, editorstack_id_str, filename):
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.blockSignals(True)
                index = editorstack.get_index_from_filename(filename)
                editorstack.close_file(index, force=True)
                editorstack.blockSignals(False)

    @Slot(str, str, str)
    def file_saved_in_editorstack(self, editorstack_id_str,
                                  original_filename, filename):
        """A file was saved in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.file_saved_in_other_editorstack(original_filename,
                                                            filename)

    @Slot(str, str, str)
    def file_renamed_in_data_in_editorstack(self, editorstack_id_str,
                                            original_filename, filename):
        """A file was renamed in data in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.rename_in_data(original_filename, filename)

    def set_editorstack_for_introspection(self):
        """
        Set the current editorstack to be used by the IntrospectionManager
        instance
        """
        editorstack = self.__get_focus_editorstack()
        if editorstack is not None:
            self.introspector.set_editor_widget(editorstack)

            # Disconnect active signals
            try:
                self.introspector.send_to_help.disconnect()
                self.introspector.edit_goto.disconnect()
            except TypeError:
                pass

            # Reconnect signals again
            self.introspector.send_to_help.connect(editorstack.send_to_help)
            self.introspector.edit_goto.connect(
                lambda fname, lineno, name:
                editorstack.edit_goto.emit(fname, lineno, name))

    #------ Handling editor windows
    def setup_other_windows(self):
        """Setup toolbars and menus for 'New window' instances"""

        self.toolbar_list = ((_("File toolbar"), "file_toolbar",
                              self.main.file_toolbar_actions),
                             (_("Search toolbar"), "search_toolbar",
                              self.main.search_menu_actions),
                             (_("Source toolbar"), "source_toolbar",
                              self.main.source_toolbar_actions),
                             (_("Run toolbar"), "run_toolbar",
                              self.main.run_toolbar_actions),
                             (_("Debug toolbar"), "debug_toolbar",
                              self.main.debug_toolbar_actions),
                             (_("Edit toolbar"), "edit_toolbar",
                              self.main.edit_toolbar_actions))
        self.menu_list = ((_("&File"), self.main.file_menu_actions),
                          (_("&Edit"), self.main.edit_menu_actions),
                          (_("&Search"), self.main.search_menu_actions),
                          (_("Sour&ce"), self.main.source_menu_actions),
                          (_("&Run"), self.main.run_menu_actions),
                          (_("&Tools"), self.main.tools_menu_actions),
                          (_("&View"), []),
                          (_("&Help"), self.main.help_menu_actions))
        # Create pending new windows:
        for layout_settings in self.editorwindows_to_be_created:
            win = self.create_new_window()
            win.set_layout_settings(layout_settings)

    @Slot()
    def create_window(self):
        """Open a new window instance of the Editor instead of undocking it."""
        if (self.dockwidget.isFloating() and not self.undocked and
                self.dockwidget.main.dockwidgets_locked):
            self.dockwidget.setVisible(False)
            self.create_new_window()
            self.toggle_view_action.setChecked(False)
            self.dockwidget.setFloating(False)
        self.undocked = False
        if self.get_current_editorstack():
            self.get_current_editorstack().new_window = False

    def undock_plugin(self):
        """Undocks the Editor window."""
        super(Editor, self).undock_plugin()
        self.get_current_editorstack().new_window = True

    def switch_to_plugin(self):
        """
        Reimplemented method to desactivate shortcut when
        opening a new window.
        """
        if not self.editorwindows or self.dockwidget.isVisible():
            super(Editor, self).switch_to_plugin()

    def create_new_window(self):
        oe_options = self.outlineexplorer.explorer.get_options()
        fullpath_sorting=self.get_option('fullpath_sorting', True),
        window = EditorMainWindow(self, self.stack_menu_actions,
                                  self.toolbar_list, self.menu_list,
                                  show_fullpath=oe_options['show_fullpath'],
                                  fullpath_sorting=fullpath_sorting,
                                  show_all_files=oe_options['show_all_files'],
                                  show_comments=oe_options['show_comments'])
        window.add_toolbars_to_menu("&View", window.get_toolbars())
        window.load_toolbars()
        window.resize(self.size())
        window.show()
        window.editorwidget.editorsplitter.editorstack.new_window = True
        self.register_editorwindow(window)
        window.destroyed.connect(lambda: self.unregister_editorwindow(window))
        return window
    
    def register_editorwindow(self, window):
        self.editorwindows.append(window)
        
    def unregister_editorwindow(self, window):
        if len(self.editorwindows) == 1:
            self.toggle_view_action.setChecked(True)
        self.editorwindows.pop(self.editorwindows.index(window))
    
        
    #------ Accessors
    def get_filenames(self):
        return [finfo.filename for finfo in self.editorstacks[0].data]

    def get_filename_index(self, filename):
        return self.editorstacks[0].has_filename(filename)

    def get_current_editorstack(self, editorwindow=None):
        if self.editorstacks is not None:
            if len(self.editorstacks) == 1:
                editorstack = self.editorstacks[0]
            else:
                editorstack = self.__get_focus_editorstack()
                if editorstack is None or editorwindow is not None:
                    editorstack = self.get_last_focus_editorstack(editorwindow)
                    if editorstack is None:
                        editorstack = self.editorstacks[0]
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
        
    def set_current_filename(self, filename, editorwindow=None, focus=True):
        """Set focus to *filename* if this file has been opened.

        Return the editor instance associated to *filename*.
        """
        editorstack = self.get_current_editorstack(editorwindow)
        return editorstack.set_current_filename(filename, focus)

    def set_path(self):
        for finfo in self.editorstacks[0].data:
            finfo.path = self.main.get_spyder_pythonpath()
        if self.introspector:
            self.introspector.change_extra_path(
                    self.main.get_spyder_pythonpath())
    
    #------ FileSwitcher API
    def get_current_tab_manager(self):
        """Get the widget with the TabWidget attribute."""
        return self.get_current_editorstack()

    #------ Refresh methods
    def refresh_file_dependent_actions(self):
        """Enable/disable file dependent actions
        (only if dockwidget is visible)"""
        if self.dockwidget and self.dockwidget.isVisible():
            enable = self.get_current_editor() is not None
            for action in self.file_dependent_actions:
                action.setEnabled(enable)
                
    def refresh_save_all_action(self):
        """Enable 'Save All' if there are files to be saved"""
        editorstack = self.get_current_editorstack()
        if editorstack:
            state = any(finfo.editor.document().isModified() or finfo.newly_created
                        for finfo in editorstack.data)
            self.save_all_action.setEnabled(state)
            
    def update_warning_menu(self):
        """Update warning list menu"""
        editorstack = self.get_current_editorstack()
        check_results = editorstack.get_analysis_results()
        self.warning_menu.clear()
        filename = self.get_current_filename()
        for message, line_number in check_results:
            error = 'syntax' in message
            text = message[:1].upper()+message[1:]
            icon = ima.icon('error') if error else ima.icon('warning')
            # QAction.triggered works differently for PySide and PyQt
            if not API == 'pyside':
                slot = lambda _checked, _l=line_number: self.load(filename, goto=_l)
            else:
                slot = lambda _l=line_number: self.load(filename, goto=_l)
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
            filename = editorstack.data[index].filename
            for other_editorstack in self.editorstacks:
                if other_editorstack is not editorstack:
                    other_editorstack.set_analysis_results(filename, results)
        self.update_code_analysis_actions()
            
    def update_todo_menu(self):
        """Update todo list menu"""
        editorstack = self.get_current_editorstack()
        results = editorstack.get_todo_results()
        self.todo_menu.clear()
        filename = self.get_current_filename()
        for text, line0 in results:
            icon = ima.icon('todo')
            # QAction.triggered works differently for PySide and PyQt
            if not API == 'pyside':
                slot = lambda _checked, _l=line0: self.load(filename, goto=_l)
            else:
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
            filename = editorstack.data[index].filename
            for other_editorstack in self.editorstacks:
                if other_editorstack is not editorstack:
                    other_editorstack.set_todo_results(filename, results)
        self.update_todo_actions()
            
    def refresh_eol_chars(self, os_name):
        os_name = to_text_string(os_name)
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
            python_enable = editor.is_python()
            cython_enable = python_enable or (
                programs.is_module_installed('Cython') and editor.is_cython())
            for action in self.pythonfile_dependent_actions:
                if action in self.cythonfile_compatible_actions:
                    enable = cython_enable
                else:
                    enable = python_enable
                if action is self.winpdb_action:
                    action.setEnabled(enable and WINPDB_PATH is not None)
                else:
                    action.setEnabled(enable)
            self.open_file_update.emit(self.get_current_filename())

    def update_code_analysis_actions(self):
        editorstack = self.get_current_editorstack()
        results = editorstack.get_analysis_results()
        
        # Update code analysis buttons
        state = (self.get_option('code_analysis/pyflakes') \
                 or self.get_option('code_analysis/pep8')) \
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

    def rehighlight_cells(self):
        """Rehighlight cells of current editor"""
        editor = self.get_current_editor()
        editor.rehighlight_cells()
        QApplication.processEvents()


    #------ Breakpoints
    def save_breakpoints(self, filename, breakpoints):
        filename = to_text_string(filename)
        breakpoints = to_text_string(breakpoints)
        filename = osp.normpath(osp.abspath(filename))
        if breakpoints:
            breakpoints = eval(breakpoints)
        else:
            breakpoints = []
        save_breakpoints(filename, breakpoints)
        self.breakpoints_saved.emit()
        
    #------ File I/O
    def __load_temp_file(self):
        """Load temporary file from a text file in user home directory"""
        if not osp.isfile(self.TEMPFILE_PATH):
            # Creating temporary file
            default = ['# -*- coding: utf-8 -*-',
                       '"""', _("Spyder Editor"), '',
                       _("This is a temporary script file."),
                       '"""', '', '']
            text = os.linesep.join([encoding.to_unicode(qstr)
                                    for qstr in default])
            encoding.write(to_text_string(text), self.TEMPFILE_PATH, 'utf-8')
        self.load(self.TEMPFILE_PATH)

    @Slot()
    def __set_workdir(self):
        """Set current script directory as working directory"""
        fname = self.get_current_filename()
        if fname is not None:
            directory = osp.dirname(osp.abspath(fname))
            self.open_dir.emit(directory)
                
    def __add_recent_file(self, fname):
        """Add to recent file list"""
        if fname is None:
            return
        if fname in self.recent_files:
            self.recent_files.remove(fname)
        self.recent_files.insert(0, fname)
        if len(self.recent_files) > self.get_option('max_recent_files'):
            self.recent_files.pop(-1)

    def _clone_file_everywhere(self, finfo):
        """Clone file (*src_editor* widget) in all editorstacks
        Cloning from the first editorstack in which every single new editor
        is created (when loading or creating a new file)"""
        for editorstack in self.editorstacks[1:]:
            editor = editorstack.clone_editor_from(finfo, set_current=False)
            self.register_widget_shortcuts(editor)

    @Slot()
    @Slot(str)
    def new(self, fname=None, editorstack=None, text=None):
        """
        Create a new file - Untitled
        
        fname=None --> fname will be 'untitledXX.py' but do not create file
        fname=<basestring> --> create file
        """
        # If no text is provided, create default content
        if text is None:
            default_content = True
            text, enc = encoding.read(self.TEMPLATE_PATH)
            enc_match = re.search('-*- coding: ?([a-z0-9A-Z\-]*) -*-', text)
            if enc_match:
                enc = enc_match.group(1)
            # Initialize template variables
            # Windows
            username = encoding.to_unicode_from_fs(os.environ.get('USERNAME',
                                                                  ''))
            # Linux, Mac OS X
            if not username:
                username = encoding.to_unicode_from_fs(os.environ.get('USER',
                                                                      '-'))
            VARS = {
                'date': time.ctime(),
                'username': username,
            }
            try:
                text = text % VARS
            except:
                pass
        else:
            default_content = False
            enc = encoding.read(self.TEMPLATE_PATH)[1]

        create_fname = lambda n: to_text_string(_("untitled")) + ("%d.py" % n)
        # Creating editor widget
        if editorstack is None:
            current_es = self.get_current_editorstack()
        else:
            current_es = editorstack
        created_from_here = fname is None
        if created_from_here:
            while True:
                fname = create_fname(self.untitled_num)
                self.untitled_num += 1
                if not osp.isfile(fname):
                    break
            basedir = getcwd_or_home()

            if self.main.projects.get_active_project() is not None:
                basedir = self.main.projects.get_active_project_path()
            else:
                c_fname = self.get_current_filename()
                if c_fname is not None and c_fname != self.TEMPFILE_PATH:
                    basedir = osp.dirname(c_fname)
            fname = osp.abspath(osp.join(basedir, fname))
        else:
            # QString when triggered by a Qt signal
            fname = osp.abspath(to_text_string(fname))
            index = current_es.has_filename(fname)
            if index is not None and not current_es.close_file(index):
                return
        
        # Creating the editor widget in the first editorstack (the one that
        # can't be destroyed), then cloning this editor widget in all other
        # editorstacks:
        finfo = self.editorstacks[0].new(fname, enc, text, default_content)
        finfo.path = self.main.get_spyder_pythonpath()
        self._clone_file_everywhere(finfo)
        current_editor = current_es.set_current_filename(finfo.filename)
        self.register_widget_shortcuts(current_editor)
        if not created_from_here:
            self.save(force=True)

    def edit_template(self):
        """Edit new file template"""
        self.load(self.TEMPLATE_PATH)

    def update_recent_file_menu(self):
        """Update recent file menu"""
        recent_files = []
        for fname in self.recent_files:
            if self.is_file_opened(fname) is None and osp.isfile(fname):
                recent_files.append(fname)
        self.recent_file_menu.clear()
        if recent_files:
            for fname in recent_files:
                action = create_action(self, fname,
                                       icon=ima.icon('FileIcon'),
                                       triggered=self.load)
                action.setData(to_qvariant(fname))
                self.recent_file_menu.addAction(action)
        self.clear_recent_action.setEnabled(len(recent_files) > 0)
        add_actions(self.recent_file_menu, (None, self.max_recent_action,
                                            self.clear_recent_action))

    @Slot()
    def clear_recent_files(self):
        """Clear recent files list"""
        self.recent_files = []

    @Slot()
    def change_max_recent_files(self):
        "Change max recent files entries"""
        editorstack = self.get_current_editorstack()
        mrf, valid = QInputDialog.getInt(editorstack, _('Editor'),
                               _('Maximum number of recent files'),
                               self.get_option('max_recent_files'), 1, 35)
        if valid:
            self.set_option('max_recent_files', mrf)

    @Slot()
    @Slot(str)
    @Slot(str, int, str)
    @Slot(str, int, str, object)
    def load(self, filenames=None, goto=None, word='', editorwindow=None,
             processevents=True):
        """
        Load a text file
        editorwindow: load in this editorwindow (useful when clicking on
        outline explorer with multiple editor windows)
        processevents: determines if processEvents() should be called at the
        end of this method (set to False to prevent keyboard events from
        creeping through to the editor during debugging)
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
                filenames = from_qvariant(action.data(), to_text_string)
        if not filenames:
            basedir = getcwd_or_home()
            if self.edit_filetypes is None:
                self.edit_filetypes = get_edit_filetypes()
            if self.edit_filters is None:
                self.edit_filters = get_edit_filters()

            c_fname = self.get_current_filename()
            if c_fname is not None and c_fname != self.TEMPFILE_PATH:
                basedir = osp.dirname(c_fname)
            self.redirect_stdio.emit(False)
            parent_widget = self.get_current_editorstack()
            if filename0 is not None:
                selectedfilter = get_filter(self.edit_filetypes,
                                            osp.splitext(filename0)[1])
            else:
                selectedfilter = ''
            if not PYTEST:
                filenames, _sf = getopenfilenames(
                                    parent_widget,
                                    _("Open file"), basedir,
                                    self.edit_filters,
                                    selectedfilter=selectedfilter,
                                    options=QFileDialog.HideNameFilterDetails)
            else:
                # Use a Qt (i.e. scriptable) dialog for pytest
                dialog = QFileDialog(parent_widget, _("Open file"),
                                     options=QFileDialog.DontUseNativeDialog)
                if dialog.exec_():
                    filenames = dialog.selectedFiles()
            self.redirect_stdio.emit(True)
            if filenames:
                filenames = [osp.normpath(fname) for fname in filenames]
            else:
                return

        focus_widget = QApplication.focusWidget()
        if self.editorwindows and not self.dockwidget.isVisible():
            # We override the editorwindow variable to force a focus on
            # the editor window instead of the hidden editor dockwidget.
            # See PR #5742.
            if editorwindow not in self.editorwindows:
                editorwindow = self.editorwindows[0]
            editorwindow.setFocus()
            editorwindow.raise_()
        elif (self.dockwidget and not self.ismaximized
              and not self.dockwidget.isAncestorOf(focus_widget)
              and not isinstance(focus_widget, CodeEditor)):
            self.dockwidget.setVisible(True)
            self.dockwidget.setFocus()
            self.dockwidget.raise_()

        def _convert(fname):
            fname = osp.abspath(encoding.to_unicode_from_fs(fname))
            if os.name == 'nt' and len(fname) >= 2 and fname[1] == ':':
                fname = fname[0].upper()+fname[1:]
            return fname

        if hasattr(filenames, 'replaceInStrings'):
            # This is a QStringList instance (PyQt API #1), converting to list:
            filenames = list(filenames)
        if not isinstance(filenames, list):
            filenames = [_convert(filenames)]
        else:
            filenames = [_convert(fname) for fname in list(filenames)]
        if isinstance(goto, int):
            goto = [goto]
        elif goto is not None and len(goto) != len(filenames):
            goto = None

        for index, filename in enumerate(filenames):
            # -- Do not open an already opened file
            if index == 0:  # this is the last file focused in previous session
                focus = True
            else:
                focus = False
            current_editor = self.set_current_filename(filename,
                                                       editorwindow,
                                                       focus=focus)
            if current_editor is None:
                # -- Not a valid filename:
                if not osp.isfile(filename):
                    continue
                # --
                current_es = self.get_current_editorstack(editorwindow)
                # Creating the editor widget in the first editorstack
                # (the one that can't be destroyed), then cloning this
                # editor widget in all other editorstacks:
                finfo = self.editorstacks[0].load(filename, set_current=False)
                finfo.path = self.main.get_spyder_pythonpath()
                self._clone_file_everywhere(finfo)
                current_editor = current_es.set_current_filename(filename,
                                                                 focus=focus)
                current_editor.set_breakpoints(load_breakpoints(filename))
                self.register_widget_shortcuts(current_editor)
                current_es.analyze_script()
                self.__add_recent_file(filename)
            if goto is not None: # 'word' is assumed to be None as well
                current_editor.go_to_line(goto[index], word=word)
                position = current_editor.get_position('cursor')
                self.cursor_moved(filename0, position0, filename, position)
            current_editor.clearFocus()
            current_editor.setFocus()
            current_editor.window().raise_()
            if processevents:
                QApplication.processEvents()

    @Slot()
    def print_file(self):
        """Print current file"""
        editor = self.get_current_editor()
        filename = self.get_current_filename()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=self.get_plugin_font('printer_header'))
        printDialog = QPrintDialog(printer, editor)
        if editor.has_selected_text():
            printDialog.setOption(QAbstractPrintDialog.PrintSelection, True)
        self.redirect_stdio.emit(False)
        answer = printDialog.exec_()
        self.redirect_stdio.emit(True)
        if answer == QDialog.Accepted:
            self.starting_long_process(_("Printing..."))
            printer.setDocName(filename)
            editor.print_(printer)
            self.ending_long_process()

    @Slot()
    def print_preview(self):
        """Print preview for current file"""
        from qtpy.QtPrintSupport import QPrintPreviewDialog

        editor = self.get_current_editor()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=self.get_plugin_font('printer_header'))
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowFlags(Qt.Window)
        preview.paintRequested.connect(lambda printer: editor.print_(printer))
        self.redirect_stdio.emit(False)
        preview.exec_()
        self.redirect_stdio.emit(True)

    @Slot()
    def close_file(self):
        """Close current file"""
        editorstack = self.get_current_editorstack()
        editorstack.close_file()

    @Slot()
    def close_all_files(self):
        """Close all opened scripts"""
        self.editorstacks[0].close_all_files()
    
    @Slot()
    def save(self, index=None, force=False):
        """Save file"""
        editorstack = self.get_current_editorstack()
        return editorstack.save(index=index, force=force)
    
    @Slot()
    def save_as(self):
        """Save *as* the currently edited file"""
        editorstack = self.get_current_editorstack()
        if editorstack.save_as():
            fname = editorstack.get_current_filename()
            self.__add_recent_file(fname)

    @Slot()
    def save_copy_as(self):
        """Save *copy as* the currently edited file"""
        editorstack = self.get_current_editorstack()
        editorstack.save_copy_as()

    @Slot()
    def save_all(self):
        """Save all opened files"""
        self.get_current_editorstack().save_all()
    
    @Slot()
    def revert(self):
        """Revert the currently edited file from disk"""
        editorstack = self.get_current_editorstack()
        editorstack.revert()

    @Slot()
    def find(self):
        """Find slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.show()
        editorstack.find_widget.search_text.setFocus()

    @Slot()
    def find_next(self):
        """Fnd next slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.find_next()

    @Slot()
    def find_previous(self):
        """Find previous slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.find_previous()

    @Slot()
    def replace(self):
        """Replace slot"""
        editorstack = self.get_current_editorstack()
        editorstack.find_widget.show_replace()
    
    def open_last_closed(self):
        """ Reopens the last closed tab."""
        editorstack = self.get_current_editorstack()
        last_closed_files = editorstack.get_last_closed_files()
        if (len(last_closed_files) > 0):
            file_to_open = last_closed_files[0]
            last_closed_files.remove(file_to_open)
            editorstack.set_last_closed_files(last_closed_files)
            self.load(file_to_open)
    
    #------ Explorer widget
    def close_file_from_name(self, filename):
        """Close file from its name"""
        filename = osp.abspath(to_text_string(filename))
        index = self.editorstacks[0].has_filename(filename)
        if index is not None:
            self.editorstacks[0].close_file(index)
                
    def removed(self, filename):
        """File was removed in file explorer widget or in project explorer"""
        self.close_file_from_name(filename)
    
    def removed_tree(self, dirname):
        """Directory was removed in project explorer widget"""
        dirname = osp.abspath(to_text_string(dirname))
        for fname in self.get_filenames():
            if osp.abspath(fname).startswith(dirname):
                self.close_file_from_name(fname)
    
    def renamed(self, source, dest):
        """File was renamed in file explorer widget or in project explorer"""
        filename = osp.abspath(to_text_string(source))
        index = self.editorstacks[0].has_filename(filename)
        if index is not None:
            for editorstack in self.editorstacks:
                editorstack.rename_in_data(filename,
                                           new_filename=to_text_string(dest))
        
    
    #------ Source code
    @Slot()
    def indent(self):
        """Indent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.indent()

    @Slot()
    def unindent(self):
        """Unindent current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unindent()

    @Slot()
    def text_uppercase (self):
        """Change current line or selection to uppercase."""
        editor = self.get_current_editor()
        if editor is not None:
            editor.transform_to_uppercase()

    @Slot()
    def text_lowercase(self):
        """Change current line or selection to lowercase."""
        editor = self.get_current_editor()
        if editor is not None:
            editor.transform_to_lowercase()

    @Slot()
    def toggle_comment(self):
        """Comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.toggle_comment()

    @Slot()
    def blockcomment(self):
        """Block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.blockcomment()

    @Slot()
    def unblockcomment(self):
        """Un-block comment current line or selection"""
        editor = self.get_current_editor()
        if editor is not None:
            editor.unblockcomment()
    @Slot()
    def go_to_next_todo(self):
        editor = self.get_current_editor()
        position = editor.go_to_next_todo()
        filename = self.get_current_filename()
        self.add_cursor_position_to_history(filename, position)

    @Slot()
    def go_to_next_warning(self):
        editor = self.get_current_editor()
        position = editor.go_to_next_warning()
        filename = self.get_current_filename()
        self.add_cursor_position_to_history(filename, position)

    @Slot()
    def go_to_previous_warning(self):
        editor = self.get_current_editor()
        position = editor.go_to_previous_warning()
        filename = self.get_current_filename()
        self.add_cursor_position_to_history(filename, position)

    @Slot()
    def run_winpdb(self):
        """Run winpdb to debug current file"""
        if self.save():
            fname = self.get_current_filename()
            runconf = get_run_configuration(fname)
            if runconf is None:
                args = []
                wdir = None
            else:
                args = runconf.get_arguments().split()
                wdir = runconf.get_working_directory()
            # Handle the case where wdir comes back as an empty string
            # when the working directory dialog checkbox is unchecked.
            # (subprocess "cwd" default is None, so empty str
            # must be changed to None in this case.)
            programs.run_program(WINPDB_PATH, [fname] + args, cwd=wdir or None)
        
    def toggle_eol_chars(self, os_name, checked):
        if checked:
            editor = self.get_current_editor()
            if self.__set_eol_chars:
                editor.set_eol_chars(sourcecode.get_eol_chars_from_os_name(os_name))

    @Slot()
    def remove_trailing_spaces(self):
        editorstack = self.get_current_editorstack()
        editorstack.remove_trailing_spaces()

    @Slot()
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
        self.last_edit_cursor_pos = (to_text_string(filename), position)
        
    def current_file_changed(self, filename, position):
        self.add_cursor_position_to_history(to_text_string(filename), position,
                                            fc=True)

    @Slot()
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

    @Slot()
    def go_to_previous_cursor_position(self):
        self.__move_cursor_position(-1)

    @Slot()
    def go_to_next_cursor_position(self):
        self.__move_cursor_position(1)

    @Slot()
    def go_to_line(self, line=None):
        """Open 'go to line' dialog"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.go_to_line(line)

    @Slot()
    def set_or_clear_breakpoint(self):
        """Set/Clear breakpoint"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.set_or_clear_breakpoint()

    @Slot()
    def set_or_edit_conditional_breakpoint(self):
        """Set/Edit conditional breakpoint"""
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            editorstack.set_or_edit_conditional_breakpoint()

    @Slot()
    def clear_all_breakpoints(self):
        """Clear breakpoints in all files"""
        clear_all_breakpoints()
        self.breakpoints_saved.emit()
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            for data in editorstack.data:
                data.editor.clear_breakpoints()
        self.refresh_plugin()
                
    def clear_breakpoint(self, filename, lineno):
        """Remove a single breakpoint"""
        clear_breakpoint(filename, lineno)
        self.breakpoints_saved.emit()
        editorstack = self.get_current_editorstack()
        if editorstack is not None:
            index = self.is_file_opened(filename)
            if index is not None:
                editorstack.data[index].editor.add_remove_breakpoint(lineno)
                
    def debug_command(self, command):
        """Debug actions"""
        self.main.ipyconsole.write_to_stdin(command)
        focus_widget = self.main.ipyconsole.get_focus_widget()
        if focus_widget:
            focus_widget.setFocus()

    #------ Run Python script
    @Slot()
    def edit_run_configurations(self):
        dialog = RunConfigDialog(self)
        dialog.size_change.connect(lambda s: self.set_dialog_size(s))
        if self.dialog_size is not None:
            dialog.resize(self.dialog_size)
        fname = osp.abspath(self.get_current_filename())
        dialog.setup(fname)
        if dialog.exec_():
            fname = dialog.file_to_run
            if fname is not None:
                self.load(fname)
                self.run_file()

    @Slot()
    def run_file(self, debug=False):
        """Run script inside current interpreter or in a new one"""
        editorstack = self.get_current_editorstack()
        if editorstack.save():
            editor = self.get_current_editor()
            fname = osp.abspath(self.get_current_filename())
            
            # Escape single and double quotes in fname (Fixes Issue 2158)
            fname = fname.replace("'", r"\'")
            fname = fname.replace('"', r'\"')
            
            runconf = get_run_configuration(fname)
            if runconf is None:
                dialog = RunConfigOneDialog(self)
                dialog.size_change.connect(lambda s: self.set_dialog_size(s))
                if self.dialog_size is not None:
                    dialog.resize(self.dialog_size)
                dialog.setup(fname)
                if CONF.get('run', 'open_at_least_once', not PYTEST):
                    # Open Run Config dialog at least once: the first time 
                    # a script is ever run in Spyder, so that the user may 
                    # see it at least once and be conscious that it exists
                    show_dlg = True
                    CONF.set('run', 'open_at_least_once', False)
                else:
                    # Open Run Config dialog only 
                    # if ALWAYS_OPEN_FIRST_RUN_OPTION option is enabled
                    show_dlg = CONF.get('run', ALWAYS_OPEN_FIRST_RUN_OPTION)
                if show_dlg and not dialog.exec_():
                    return
                runconf = dialog.get_configuration()

            args = runconf.get_arguments()
            python_args = runconf.get_python_arguments()
            interact = runconf.interact
            post_mortem = runconf.post_mortem
            current = runconf.current
            systerm = runconf.systerm
            clear_namespace = runconf.clear_namespace

            if runconf.file_dir:
                wdir = osp.dirname(fname)
            elif runconf.cw_dir:
                wdir = ''
            elif osp.isdir(runconf.dir):
                wdir = runconf.dir
            else:
                wdir = ''

            python = True # Note: in the future, it may be useful to run
            # something in a terminal instead of a Python interp.
            self.__last_ec_exec = (fname, wdir, args, interact, debug,
                                   python, python_args, current, systerm, 
                                   post_mortem, clear_namespace)
            self.re_run_file()
            if not interact and not debug:
                # If external console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # current external shell automatically
                # (see SpyderPluginWidget.visibility_changed method)
                editor.setFocus()
                
    def set_dialog_size(self, size):
        self.dialog_size = size

    @Slot()
    def debug_file(self):
        """Debug current script"""
        self.run_file(debug=True)

    @Slot()
    def re_run_file(self):
        """Re-run last script"""
        if self.get_option('save_all_before_run'):
            self.save_all()
        if self.__last_ec_exec is None:
            return
        (fname, wdir, args, interact, debug,
         python, python_args, current, systerm,
         post_mortem, clear_namespace) = self.__last_ec_exec
        if not systerm:
            self.run_in_current_ipyclient.emit(fname, wdir, args,
                                               debug, post_mortem,
                                               current, clear_namespace)
        else:
            self.main.open_external_console(fname, wdir, args, interact,
                                            debug, python, python_args,
                                            systerm, post_mortem)

    @Slot()
    def run_selection(self):
        """Run selection or current line in external console"""
        editorstack = self.get_current_editorstack()
        editorstack.run_selection()

    @Slot()
    def run_cell(self):
        """Run current cell"""
        editorstack = self.get_current_editorstack()
        editorstack.run_cell()

    @Slot()
    def run_cell_and_advance(self):
        """Run current cell and advance to the next one"""
        editorstack = self.get_current_editorstack()
        editorstack.run_cell_and_advance()

    @Slot()
    def re_run_last_cell(self):
        """Run last executed cell."""
        editorstack = self.get_current_editorstack()
        editorstack.re_run_last_cell()

    #------ Zoom in/out/reset
    def zoom(self, factor):
        """Zoom in/out/reset"""
        editor = self.get_current_editorstack().get_current_editor()
        if factor == 0:
            font = self.get_plugin_font()
            editor.set_font(font)
        else:
            font = editor.font()
            size = font.pointSize() + factor
            if size > 0:
                font.setPointSize(size)
                editor.set_font(font)
        editor.update_tab_stop_width_spaces()

    #------ Options
    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        # toggle_fullpath_sorting
        if self.editorstacks is not None:
            # --- syntax highlight and text rendering settings
            color_scheme_n = 'color_scheme_name'
            color_scheme_o = self.get_color_scheme()
            currentline_n = 'highlight_current_line'
            currentline_o = self.get_option(currentline_n)
            currentcell_n = 'highlight_current_cell'
            currentcell_o = self.get_option(currentcell_n)            
            occurrence_n = 'occurrence_highlighting'
            occurrence_o = self.get_option(occurrence_n)
            occurrence_timeout_n = 'occurrence_highlighting/timeout'
            occurrence_timeout_o = self.get_option(occurrence_timeout_n)
            focus_to_editor_n = 'focus_to_editor'
            focus_to_editor_o = self.get_option(focus_to_editor_n)
            
            for editorstack in self.editorstacks:
                if color_scheme_n in options:
                    editorstack.set_color_scheme(color_scheme_o)
                if currentline_n in options:
                    editorstack.set_highlight_current_line_enabled(
                                                                currentline_o)
                if currentcell_n in options:
                    editorstack.set_highlight_current_cell_enabled(
                                                                currentcell_o)              
                if occurrence_n in options:
                    editorstack.set_occurrence_highlighting_enabled(occurrence_o)
                if occurrence_timeout_n in options:
                    editorstack.set_occurrence_highlighting_timeout(
                                                           occurrence_timeout_o)
                if focus_to_editor_n in options:
                    editorstack.set_focus_to_editor(focus_to_editor_o)

            # --- everything else
            fpsorting_n = 'fullpath_sorting'
            fpsorting_o = self.get_option(fpsorting_n)
            tabbar_n = 'show_tab_bar'
            tabbar_o = self.get_option(tabbar_n)
            classfuncdropdown_n = 'show_class_func_dropdown'
            classfuncdropdown_o = self.get_option(classfuncdropdown_n)
            linenb_n = 'line_numbers'
            linenb_o = self.get_option(linenb_n)
            blanks_n = 'blank_spaces'
            blanks_o = self.get_option(blanks_n)
            scrollpastend_n = 'scroll_past_end'
            scrollpastend_o = self.get_option(scrollpastend_n)
            edgeline_n = 'edge_line'
            edgeline_o = self.get_option(edgeline_n)
            edgelinecols_n = 'edge_line_columns'
            edgelinecols_o = self.get_option(edgelinecols_n)
            wrap_n = 'wrap'
            wrap_o = self.get_option(wrap_n)
            indentguides_n = 'indent_guides'
            indentguides_o = self.get_option(indentguides_n)
            tabindent_n = 'tab_always_indent'
            tabindent_o = self.get_option(tabindent_n)
            ibackspace_n = 'intelligent_backspace'
            ibackspace_o = self.get_option(ibackspace_n)
            removetrail_n = 'always_remove_trailing_spaces'
            removetrail_o = self.get_option(removetrail_n)
            converteol_n = 'convert_eol_on_save'
            converteol_o = self.get_option(converteol_n)
            converteolto_n = 'convert_eol_on_save_to'
            converteolto_o = self.get_option(converteolto_n)
            autocomp_n = 'codecompletion/auto'
            autocomp_o = self.get_option(autocomp_n)
            case_comp_n = 'codecompletion/case_sensitive'
            case_comp_o = self.get_option(case_comp_n)
            enter_key_n = 'codecompletion/enter_key'
            enter_key_o = self.get_option(enter_key_n)
            calltips_n = 'calltips'
            calltips_o = self.get_option(calltips_n)
            gotodef_n = 'go_to_definition'
            gotodef_o = self.get_option(gotodef_n)
            closepar_n = 'close_parentheses'
            closepar_o = self.get_option(closepar_n)
            close_quotes_n = 'close_quotes'
            close_quotes_o = self.get_option(close_quotes_n)
            add_colons_n = 'add_colons'
            add_colons_o = self.get_option(add_colons_n)
            autounindent_n = 'auto_unindent'
            autounindent_o = self.get_option(autounindent_n)
            indent_chars_n = 'indent_chars'
            indent_chars_o = self.get_option(indent_chars_n)
            tab_stop_width_spaces_n = 'tab_stop_width_spaces'
            tab_stop_width_spaces_o = self.get_option(tab_stop_width_spaces_n)
            help_n = 'connect_to_oi'
            help_o = CONF.get('help', 'connect/editor')
            todo_n = 'todo_list'
            todo_o = self.get_option(todo_n)
            pyflakes_n = 'code_analysis/pyflakes'
            pyflakes_o = self.get_option(pyflakes_n)
            pep8_n = 'code_analysis/pep8'
            pep8_o = self.get_option(pep8_n)
            rt_analysis_n = 'realtime_analysis'
            rt_analysis_o = self.get_option(rt_analysis_n)
            rta_timeout_n = 'realtime_analysis/timeout'
            rta_timeout_o = self.get_option(rta_timeout_n)
            finfo = self.get_current_finfo()
            if fpsorting_n in options:
                if self.outlineexplorer is not None:
                    self.outlineexplorer.explorer.set_fullpath_sorting(
                        fpsorting_o)
                for window in self.editorwindows:
                    window.editorwidget.outlineexplorer.set_fullpath_sorting(
                        fpsorting_o)
            for editorstack in self.editorstacks:
                if fpsorting_n in options:
                    editorstack.set_fullpath_sorting_enabled(fpsorting_o)
                if tabbar_n in options:
                    editorstack.set_tabbar_visible(tabbar_o)
                if linenb_n in options:
                    editorstack.set_linenumbers_enabled(linenb_o,
                                                        current_finfo=finfo)
                if edgeline_n in options:
                    editorstack.set_edgeline_enabled(edgeline_o)
                if edgelinecols_n in options:
                    editorstack.set_edgeline_columns(edgelinecols_o)
                if wrap_n in options:
                    editorstack.set_wrap_enabled(wrap_o)
                if tabindent_n in options:
                    editorstack.set_tabmode_enabled(tabindent_o)
                if ibackspace_n in options:
                    editorstack.set_intelligent_backspace_enabled(ibackspace_o)
                if removetrail_n in options:
                    editorstack.set_always_remove_trailing_spaces(removetrail_o)
                if converteol_n in options:
                    editorstack.set_convert_eol_on_save(converteol_o)
                if converteolto_n in options:
                    editorstack.set_convert_eol_on_save_to(converteolto_o)
                if autocomp_n in options:
                    editorstack.set_codecompletion_auto_enabled(autocomp_o)
                if case_comp_n in options:
                    editorstack.set_codecompletion_case_enabled(case_comp_o)
                if enter_key_n in options:
                    editorstack.set_codecompletion_enter_enabled(enter_key_o)
                if calltips_n in options:
                    editorstack.set_calltips_enabled(calltips_o)
                if gotodef_n in options:
                    editorstack.set_go_to_definition_enabled(gotodef_o)
                if closepar_n in options:
                    editorstack.set_close_parentheses_enabled(closepar_o)
                if close_quotes_n in options:
                    editorstack.set_close_quotes_enabled(close_quotes_o)
                if add_colons_n in options:
                    editorstack.set_add_colons_enabled(add_colons_o)
                if autounindent_n in options:
                    editorstack.set_auto_unindent_enabled(autounindent_o)
                if indent_chars_n in options:
                    editorstack.set_indent_chars(indent_chars_o)
                if tab_stop_width_spaces_n in options:
                    editorstack.set_tab_stop_width_spaces(tab_stop_width_spaces_o)
                if help_n in options:
                    editorstack.set_help_enabled(help_o)
                if todo_n in options:
                    editorstack.set_todolist_enabled(todo_o,
                                                     current_finfo=finfo)
                if pyflakes_n in options:
                    editorstack.set_pyflakes_enabled(pyflakes_o,
                                                     current_finfo=finfo)
                if pep8_n in options:
                    editorstack.set_pep8_enabled(pep8_o, current_finfo=finfo)
                if rt_analysis_n in options:
                    editorstack.set_realtime_analysis_enabled(rt_analysis_o)
                if rta_timeout_n in options:
                    editorstack.set_realtime_analysis_timeout(rta_timeout_o)

            for name, action in self.checkable_actions.items():
                if name in options:
                    state = self.get_option(name)
                    action.setChecked(state)
                    action.trigger()
            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            if finfo is not None:
                if todo_n in options and todo_o:
                    finfo.run_todo_finder()
                if pyflakes_n in options or pep8_n in options:
                    finfo.run_code_analysis(pyflakes_o, pep8_o)

    # --- Open files
    def get_open_filenames(self):
        """Get the list of open files in the current stack"""
        editorstack = self.editorstacks[0]
        filenames = []
        filenames += [finfo.filename for finfo in editorstack.data]
        return filenames
        
    def set_open_filenames(self):
        """
        Set the recent opened files on editor based on active project.

        If no project is active, then editor filenames are saved, otherwise
        the opened filenames are stored in the project config info.
        """
        if self.projects is not None:
            if not self.projects.get_active_project():
                filenames = self.get_open_filenames()
                self.set_option('filenames', filenames)
 
    def setup_open_files(self):
        """Open the list of saved files per project"""
        self.set_create_new_file_if_empty(False)
        active_project_path = None
        if self.projects is not None:
             active_project_path = self.projects.get_active_project_path()

        if active_project_path:
            filenames = self.projects.get_project_filenames()
        else:
            filenames = self.get_option('filenames', default=[])
        self.close_all_files()

        if filenames and any([osp.isfile(f) for f in filenames]):
            filenames = self.reorder_filenames(filenames)
            layout = self.get_option('layout_settings', None)
            is_vertical, cfname, clines = layout.get('splitsettings')[0]
            self.load(filenames, goto=clines)
            if layout is not None:
                self.editorsplitter.set_layout_settings(layout,
                                                        dont_goto=filenames[0])
            win_layout = self.get_option('windows_layout_settings', None)
            if win_layout:
                for layout_settings in win_layout:
                    self.editorwindows_to_be_created.append(layout_settings)
            self.set_last_focus_editorstack(self, self.editorstacks[0])
        else:
            self.__load_temp_file()
        self.set_create_new_file_if_empty(True)

    def reorder_filenames(self, filenames):
        """Take the last session filenames and put the last open on first.

        It takes a list of filenames and using the current filename from the 
        layout settings, sets the one that had focused last in the position 0. 
        It also reorders the current lines for each file (supposing that they 
        are in the same order as the filenames) and sets them back in the 
        layout settings.
        """
        layout = self.get_option('layout_settings', None)
        if layout is None:
            return filenames
        splitsettings = layout.get('splitsettings')
        index_first_file = 0
        reordered_splitsettings = []
        for index, (is_vertical, cfname, clines) in enumerate(splitsettings):
            #the first element of filenames is now the one that last had focus
            if index == 0:
                if cfname in filenames:
                    index_first_file = filenames.index(cfname)
                    filenames.pop(index_first_file)
                    filenames.insert(0, cfname)
                    clines_first_file = clines[index_first_file]
                    clines.pop(index_first_file)
                    clines.insert(0, clines_first_file)
                else:
                    cfname = filenames[0]
                    index_first_file = 0
            reordered_splitsettings.append((is_vertical, cfname, clines))
        layout['splitsettings'] = reordered_splitsettings
        self.set_option('layout_settings', layout)
        return filenames

    def save_open_files(self):
        """Save the list of open files"""
        self.set_option('filenames', self.get_open_filenames())

    def set_create_new_file_if_empty(self, value):
        """Change the value of create_new_file_if_empty"""
        for editorstack in self.editorstacks:
            editorstack.create_new_file_if_empty = value

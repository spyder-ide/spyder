# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor Widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

# Local imports
from __future__ import print_function
import os
import os.path as osp
import sys
from collections import MutableSequence

# Third party imports
from qtpy import is_pyqt46
from qtpy.compat import getsavefilename
from qtpy.QtCore import (QByteArray, QFileInfo, QObject, QPoint, QSize, Qt,
                         QThread, QTimer, Signal, Slot)
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (QAction, QApplication, QHBoxLayout, QMainWindow,
                            QMessageBox, QMenu, QSplitter, QVBoxLayout,
                            QWidget, QListWidget, QListWidgetItem)

# Local imports
from spyder.config.base import _, DEBUG, STDERR, STDOUT
from spyder.config.gui import config_shortcut, get_shortcut
from spyder.config.utils import (get_edit_filetypes, get_edit_filters,
                                 get_filter)
from spyder.py3compat import qbytearray_to_str, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import (codeanalysis, encoding, sourcecode,
                          syntaxhighlighters)
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, mimedata2url)
from spyder.widgets.editortools import OutlineExplorerWidget
from spyder.widgets.fileswitcher import FileSwitcher
from spyder.widgets.findreplace import FindReplace
from spyder.widgets.sourcecode import codeeditor
from spyder.widgets.sourcecode.base import TextEditBaseWidget  # analysis:ignore
from spyder.widgets.sourcecode.codeeditor import Printer       # analysis:ignore
from spyder.widgets.sourcecode.codeeditor import get_file_language
from spyder.widgets.status import (CursorPositionStatus, EncodingStatus,
                                   EOLStatus, ReadWriteStatus)
from spyder.widgets.tabs import BaseTabs
from spyder.config.main import CONF
from spyder.widgets.explorer import show_in_external_file_explorer

DEBUG_EDITOR = DEBUG >= 3


class AnalysisThread(QThread):
    """Analysis thread"""
    def __init__(self, parent, checker, source_code):
        super(AnalysisThread, self).__init__(parent)
        self.checker = checker
        self.results = None
        self.source_code = source_code

    def run(self):
        """Run analysis"""
        try:
            self.results = self.checker(self.source_code)
        except Exception:
            if DEBUG_EDITOR:
                import traceback
                traceback.print_exc(file=STDERR)


class ThreadManager(QObject):
    """Analysis thread manager"""
    def __init__(self, parent, max_simultaneous_threads=2):
        super(ThreadManager, self).__init__(parent)
        self.max_simultaneous_threads = max_simultaneous_threads
        self.started_threads = {}
        self.pending_threads = []
        self.end_callbacks = {}

    def close_threads(self, parent):
        """Close threads associated to parent_id"""
        if DEBUG_EDITOR:
            print("Call to 'close_threads'", file=STDOUT)
        if parent is None:
            # Closing all threads
            self.pending_threads = []
            threadlist = []
            for threads in list(self.started_threads.values()):
                threadlist += threads
        else:
            parent_id = id(parent)
            self.pending_threads = [(_th, _id) for (_th, _id)
                                    in self.pending_threads
                                    if _id != parent_id]
            threadlist = self.started_threads.get(parent_id, [])
        for thread in threadlist:
            if DEBUG_EDITOR:
                print("Waiting for thread %r to finish" % thread, file=STDOUT)
            while thread.isRunning():
                # We can't terminate thread safely, so we simply wait...
                QApplication.processEvents()

    def close_all_threads(self):
        """Close all threads"""
        if DEBUG_EDITOR:
            print("Call to 'close_all_threads'", file=STDOUT)
        self.close_threads(None)

    def add_thread(self, checker, end_callback, source_code, parent):
        """Add thread to queue"""
        parent_id = id(parent)
        thread = AnalysisThread(self, checker, source_code)
        self.end_callbacks[id(thread)] = end_callback
        self.pending_threads.append((thread, parent_id))
        if DEBUG_EDITOR:
            print("Added thread %r to queue" % thread, file=STDOUT)
        QTimer.singleShot(50, self.update_queue)

    def update_queue(self):
        """Update queue"""
        started = 0
        for parent_id, threadlist in list(self.started_threads.items()):
            still_running = []
            for thread in threadlist:
                if thread.isFinished():
                    end_callback = self.end_callbacks.pop(id(thread))
                    if thread.results is not None:
                        #  The thread was executed successfully
                        end_callback(thread.results)
                    thread.setParent(None)
                    thread = None
                else:
                    still_running.append(thread)
                    started += 1
            threadlist = None
            if still_running:
                self.started_threads[parent_id] = still_running
            else:
                self.started_threads.pop(parent_id)
        if DEBUG_EDITOR:
            print("Updating queue:", file=STDOUT)
            print("    started:", started, file=STDOUT)
            print("    pending:", len(self.pending_threads), file=STDOUT)
        if self.pending_threads and started < self.max_simultaneous_threads:
            thread, parent_id = self.pending_threads.pop(0)
            thread.finished.connect(self.update_queue)
            threadlist = self.started_threads.get(parent_id, [])
            self.started_threads[parent_id] = threadlist+[thread]
            if DEBUG_EDITOR:
                print("===>starting:", thread, file=STDOUT)
            thread.start()


class FileInfo(QObject):
    """File properties"""
    analysis_results_changed = Signal()
    todo_results_changed = Signal()
    save_breakpoints = Signal(str, str)
    text_changed_at = Signal(str, int)
    edit_goto = Signal(str, int, str)
    send_to_help = Signal(str, str, str, str, bool)

    def __init__(self, filename, encoding, editor, new, threadmanager,
                 introspection_plugin):
        QObject.__init__(self)
        self.threadmanager = threadmanager
        self.filename = filename
        self.newly_created = new
        self.default = False      # Default untitled file
        self.encoding = encoding
        self.editor = editor
        self.path = []

        self.classes = (filename, None, None)
        self.analysis_results = []
        self.todo_results = []
        self.lastmodified = QFileInfo(filename).lastModified()

        self.editor.textChanged.connect(self.text_changed)
        self.editor.breakpoints_changed.connect(self.breakpoints_changed)

        self.pyflakes_results = None
        self.pep8_results = None

    def text_changed(self):
        """Editor's text has changed"""
        self.default = False
        self.text_changed_at.emit(self.filename,
                                  self.editor.get_position('cursor'))

    def get_source_code(self):
        """Return associated editor source code"""
        return to_text_string(self.editor.toPlainText())

    def run_code_analysis(self, run_pyflakes, run_pep8):
        """Run code analysis"""
        run_pyflakes = run_pyflakes and codeanalysis.is_pyflakes_installed()
        run_pep8 = run_pep8 and\
                   codeanalysis.get_checker_executable('pycodestyle') is not None
        self.pyflakes_results = []
        self.pep8_results = []
        if self.editor.is_python():
            enc = self.encoding.replace('-guessed', '').replace('-bom', '')
            source_code, enc = encoding.encode(self.get_source_code(), enc)
            if run_pyflakes:
                self.pyflakes_results = None
            if run_pep8:
                self.pep8_results = None
            if run_pyflakes:
                self.threadmanager.add_thread(codeanalysis.check_with_pyflakes,
                                              self.pyflakes_analysis_finished,
                                              source_code, self)
            if run_pep8:
                self.threadmanager.add_thread(codeanalysis.check_with_pep8,
                                              self.pep8_analysis_finished,
                                              source_code, self)

    def pyflakes_analysis_finished(self, results):
        """Pyflakes code analysis thread has finished"""
        self.pyflakes_results = results
        if self.pep8_results is not None:
            self.code_analysis_finished()

    def pep8_analysis_finished(self, results):
        """Pep8 code analysis thread has finished"""
        self.pep8_results = results
        if self.pyflakes_results is not None:
            self.code_analysis_finished()

    def code_analysis_finished(self):
        """Code analysis thread has finished"""
        self.set_analysis_results(self.pyflakes_results+self.pep8_results)
        self.analysis_results_changed.emit()

    def set_analysis_results(self, results):
        """Set analysis results and update warning markers in editor"""
        self.analysis_results = results
        self.editor.process_code_analysis(results)

    def cleanup_analysis_results(self):
        """Clean-up analysis results"""
        self.analysis_results = []
        self.editor.cleanup_code_analysis()

    def run_todo_finder(self):
        """Run TODO finder"""
        if self.editor.is_python():
            self.threadmanager.add_thread(codeanalysis.find_tasks,
                                          self.todo_finished,
                                          self.get_source_code(), self)

    def todo_finished(self, results):
        """Code analysis thread has finished"""
        self.set_todo_results(results)
        self.todo_results_changed.emit()

    def set_todo_results(self, results):
        """Set TODO results and update markers in editor"""
        self.todo_results = results
        self.editor.process_todo(results)

    def cleanup_todo_results(self):
        """Clean-up TODO finder results"""
        self.todo_results = []

    def breakpoints_changed(self):
        """Breakpoint list has changed"""
        breakpoints = self.editor.get_breakpoints()
        if self.editor.breakpoints != breakpoints:
            self.editor.breakpoints = breakpoints
            self.save_breakpoints.emit(self.filename, repr(breakpoints))


class StackHistory(MutableSequence):
    """Handles editor stack history.

    Works as a list of numbers corresponding to tab indexes.
    Internally elements are saved using objects id's.
    """

    def __init__(self, editor):
        self.history = list()
        self.id_list = list()
        self.editor = editor

    def _update_id_list(self):
        """Update list of corresponpding ids and tabs."""
        self.id_list = [id(self.editor.tabs.widget(_i))
                        for _i in range(self.editor.tabs.count())]

    def refresh(self):
        """Remove editors that are not longer open."""
        self._update_id_list()
        for _id in self.history[:]:
            if _id not in self.id_list:
                self.history.remove(_id)

    def __len__(self):
        return len(self.history)

    def __getitem__(self, i):
        return self.id_list.index(self.history[i])

    def __delitem__(self, i):
        del self.history[i]

    def __setitem__(self, i, v):
        _id = id(self.editor.tabs.widget(v))
        self.history[i] = _id

    def __str__(self):
        return str(list(self))

    def insert(self, i, tab_index):
        """Insert the widget (at tab index) in the position i (index)."""
        _id = id(self.editor.tabs.widget(tab_index))
        self.history.insert(i, _id)

    def remove(self, tab_index):
        """Remove the widget at the corresponding tab_index."""
        _id = id(self.editor.tabs.widget(tab_index))
        if _id in self.history:
            self.history.remove(_id)


class TabSwitcherWidget(QListWidget):
    """Show tabs in mru order and change between them."""

    def __init__(self, parent, stack_history, tabs):
        QListWidget.__init__(self, parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)

        self.editor = parent
        self.stack_history = stack_history
        self.tabs = tabs

        self.setSelectionMode(QListWidget.SingleSelection)
        self.itemActivated.connect(self.item_selected)

        self.id_list = []
        self.load_data()
        size = CONF.get('main', 'completion/size')
        self.resize(*size)
        self.set_dialog_position()
        self.setCurrentRow(0)

    def load_data(self):
        """Fill ListWidget with the tabs texts.

        Add elements in inverse order of stack_history.
        """

        for index in reversed(self.stack_history):
            text = self.tabs.tabText(index)
            text = text.replace('&', '')
            item = QListWidgetItem(ima.icon('TextFileIcon'), text)
            self.addItem(item)

    def item_selected(self, item=None):
        """Change to the selected document and hide this widget."""
        if item is None:
            item = self.currentItem()

        # stack history is in inverse order
        index = self.stack_history[-(self.currentRow()+1)]

        self.editor.set_stack_index(index)
        self.editor.current_changed(index)
        self.hide()

    def select_row(self, steps):
        """Move selected row a number of steps.

        Iterates in a cyclic behaviour.
        """
        row = (self.currentRow() + steps) % self.count()
        self.setCurrentRow(row)

    def set_dialog_position(self):
        """Positions the tab switcher in the top-center of the editor."""
        parent = self.parent()
        left = parent.geometry().width()/2 - self.width()/2
        top = 0

        self.move(left, top + self.tabs.tabBar().geometry().height())


class EditorStack(QWidget):
    reset_statusbar = Signal()
    readonly_changed = Signal(bool)
    encoding_changed = Signal(str)
    sig_editor_cursor_position_changed = Signal(int, int)
    sig_refresh_eol_chars = Signal(str)
    starting_long_process = Signal(str)
    ending_long_process = Signal(str)
    redirect_stdio = Signal(bool)
    exec_in_extconsole = Signal(str, bool)
    update_plugin_title = Signal()
    editor_focus_changed = Signal()
    zoom_in = Signal()
    zoom_out = Signal()
    zoom_reset = Signal()
    sig_close_file = Signal(str, int)
    file_saved = Signal(str, int, str)
    file_renamed_in_data = Signal(str, int, str)
    create_new_window = Signal()
    opened_files_list_changed = Signal()
    analysis_results_changed = Signal()
    todo_results_changed = Signal()
    update_code_analysis_actions = Signal()
    refresh_file_dependent_actions = Signal()
    refresh_save_all_action = Signal()
    save_breakpoints = Signal(str, str)
    text_changed_at = Signal(str, int)
    current_file_changed = Signal(str ,int)
    plugin_load = Signal((str,), ())
    edit_goto = Signal(str, int, str)
    split_vertically = Signal()
    split_horizontally = Signal()
    sig_new_file = Signal((str,), ())
    sig_save_as = Signal()
    sig_prev_edit_pos = Signal()
    sig_prev_cursor = Signal()
    sig_next_cursor = Signal()

    def __init__(self, parent, actions):
        QWidget.__init__(self, parent)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.threadmanager = ThreadManager(self)

        self.newwindow_action = None
        self.horsplit_action = None
        self.versplit_action = None
        self.close_action = None
        self.__get_split_actions()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.menu = None
        self.fileswitcher_dlg = None
#        self.filelist_btn = None
#        self.previous_btn = None
#        self.next_btn = None
        self.tabs = None
        self.tabs_switcher = None

        self.stack_history = StackHistory(self)

        self.setup_editorstack(parent, layout)

        self.find_widget = None

        self.data = []
        fileswitcher_action = create_action(self, _("File switcher..."),
                icon=ima.icon('filelist'),
                triggered=self.open_fileswitcher_dlg)
        symbolfinder_action = create_action(self,
                _("Find symbols in file..."),
                icon=ima.icon('symbol_find'),
                triggered=self.open_symbolfinder_dlg)
        copy_to_cb_action = create_action(self, _("Copy path to clipboard"),
                icon=ima.icon('editcopy'),
                triggered=lambda:
                QApplication.clipboard().setText(self.get_current_filename()))
        close_right = create_action(self, _("Close all to the right"),
                                    triggered=self.close_all_right)
        close_all_but_this = create_action(self, _("Close all but this"),
                                           triggered=self.close_all_but_this)
        
        if sys.platform == 'darwin':
           text=_("Show in Finder")
        else:
           text= _("Show in external file explorer")
        external_fileexp_action = create_action(self, text,
                                triggered=self.show_in_external_file_explorer)
                
        actions.append(external_fileexp_action)
        
        self.menu_actions = actions + [None, fileswitcher_action,
                                       symbolfinder_action,
                                       copy_to_cb_action, None, close_right,
                                       close_all_but_this]
        self.outlineexplorer = None
        self.help = None
        self.unregister_callback = None
        self.is_closable = False
        self.new_action = None
        self.open_action = None
        self.save_action = None
        self.revert_action = None
        self.tempfile_path = None
        self.title = _("Editor")
        self.pyflakes_enabled = True
        self.pep8_enabled = False
        self.todolist_enabled = True
        self.realtime_analysis_enabled = False
        self.is_analysis_done = False
        self.linenumbers_enabled = True
        self.blanks_enabled = False
        self.edgeline_enabled = True
        self.edgeline_column = 79
        self.codecompletion_auto_enabled = True
        self.codecompletion_case_enabled = False
        self.codecompletion_enter_enabled = False
        self.calltips_enabled = True
        self.go_to_definition_enabled = True
        self.close_parentheses_enabled = True
        self.close_quotes_enabled = True
        self.add_colons_enabled = True
        self.auto_unindent_enabled = True
        self.indent_chars = " "*4
        self.tab_stop_width_spaces = 4
        self.help_enabled = False
        self.default_font = None
        self.wrap_enabled = False
        self.tabmode_enabled = False
        self.intelligent_backspace_enabled = True
        self.highlight_current_line_enabled = False
        self.highlight_current_cell_enabled = False
        self.occurrence_highlighting_enabled = True
        self.occurrence_highlighting_timeout=1500
        self.checkeolchars_enabled = True
        self.always_remove_trailing_spaces = False
        self.fullpath_sorting_enabled = None
        self.focus_to_editor = True
        self.set_fullpath_sorting_enabled(False)
        self.create_new_file_if_empty = True
        ccs = 'Spyder'
        if ccs not in syntaxhighlighters.COLOR_SCHEME_NAMES:
            ccs = syntaxhighlighters.COLOR_SCHEME_NAMES[0]
        self.color_scheme = ccs
        self.introspector = None
        self.__file_status_flag = False

        # Real-time code analysis
        self.analysis_timer = QTimer(self)
        self.analysis_timer.setSingleShot(True)
        self.analysis_timer.setInterval(2000)
        self.analysis_timer.timeout.connect(self.analyze_script)

        # Accepting drops
        self.setAcceptDrops(True)

        # Local shortcuts
        self.shortcuts = self.create_shortcuts()

        #For opening last closed tabs
        self.last_closed_files = []

    @Slot()
    def show_in_external_file_explorer(self, fnames=None):
        """Show file in external file explorer"""
        if fnames is None:
            fnames = self.get_current_filename()
        show_in_external_file_explorer(fnames)

    def create_shortcuts(self):
        """Create local shortcuts"""
        # --- Configurable shortcuts
        inspect = config_shortcut(self.inspect_current_object, context='Editor',
                                  name='Inspect current object', parent=self)
        set_breakpoint = config_shortcut(self.set_or_clear_breakpoint,
                                         context='Editor', name='Breakpoint',
                                         parent=self)
        set_cond_breakpoint = config_shortcut(
                                    self.set_or_edit_conditional_breakpoint,
                                    context='Editor',
                                    name='Conditional breakpoint',
                                    parent=self)
        gotoline = config_shortcut(self.go_to_line, context='Editor',
                                   name='Go to line', parent=self)
        tab = config_shortcut(lambda: self.tab_navigation_mru(forward=False),
                              context='Editor',
                              name='Go to previous file', parent=self)
        tabshift = config_shortcut(self.tab_navigation_mru, context='Editor',
                                   name='Go to next file', parent=self)
        run_selection = config_shortcut(self.run_selection, context='Editor',
                                        name='Run selection', parent=self)
        new_file = config_shortcut(lambda : self.sig_new_file[()].emit(),
                                   context='Editor', name='New file',
                                   parent=self)
        open_file = config_shortcut(lambda : self.plugin_load[()].emit(),
                                    context='Editor', name='Open file',
                                    parent=self)
        save_file = config_shortcut(self.save, context='Editor',
                                    name='Save file', parent=self)
        save_all = config_shortcut(self.save_all, context='Editor',
                                   name='Save all', parent=self)
        save_as = config_shortcut(lambda : self.sig_save_as.emit(),
                                  context='Editor', name='Save As',
                                  parent=self)
        close_all = config_shortcut(self.close_all_files, context='Editor',
                                    name='Close all', parent=self)
        prev_edit_pos = config_shortcut(lambda : self.sig_prev_edit_pos.emit(),
                                        context="Editor",
                                        name="Last edit location",
                                        parent=self)
        prev_cursor = config_shortcut(lambda : self.sig_prev_cursor.emit(),
                                      context="Editor",
                                      name="Previous cursor position",
                                      parent=self)
        next_cursor = config_shortcut(lambda : self.sig_next_cursor.emit(),
                                      context="Editor",
                                      name="Next cursor position",
                                      parent=self)
        zoom_in_1 = config_shortcut(lambda : self.zoom_in.emit(),
                                      context="Editor",
                                      name="zoom in 1",
                                      parent=self)
        zoom_in_2 = config_shortcut(lambda : self.zoom_in.emit(),
                                      context="Editor",
                                      name="zoom in 2",
                                      parent=self)
        zoom_out = config_shortcut(lambda : self.zoom_out.emit(),
                                      context="Editor",
                                      name="zoom out",
                                      parent=self)
        zoom_reset = config_shortcut(lambda: self.zoom_reset.emit(),
                                      context="Editor",
                                      name="zoom reset",
                                      parent=self)
        close_file_1 = config_shortcut(self.close_file,
                                      context="Editor",
                                      name="close file 1",
                                      parent=self)
        close_file_2 = config_shortcut(self.close_file,
                                      context="Editor",
                                      name="close file 2",
                                      parent=self)
        run_cell = config_shortcut(self.run_cell,
                                      context="Editor",
                                      name="run cell",
                                      parent=self)
        run_cell_and_advance = config_shortcut(self.run_cell_and_advance,
                                      context="Editor",
                                      name="run cell and advance",
                                      parent=self)
        go_to_next_cell = config_shortcut(self.advance_cell,
                                          context="Editor",
                                          name="go to next cell",
                                          parent=self)
        go_to_previous_cell = config_shortcut(lambda: self.advance_cell(reverse=True),
                                              context="Editor",
                                              name="go to previous cell",
                                              parent=self)
        re_run_last_cell = config_shortcut(self.re_run_last_cell,
                                      context="Editor",
                                      name="re-run last cell",
                                      parent=self)

        # Return configurable ones
        return [inspect, set_breakpoint, set_cond_breakpoint, gotoline, tab,
                tabshift, run_selection, new_file, open_file, save_file,
                save_all, save_as, close_all, prev_edit_pos, prev_cursor,
                next_cursor, zoom_in_1, zoom_in_2, zoom_out, zoom_reset,
                close_file_1, close_file_2, run_cell, run_cell_and_advance,
                go_to_next_cell, go_to_previous_cell, re_run_last_cell]

    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [sc.data for sc in self.shortcuts]

    def setup_editorstack(self, parent, layout):
        """Setup editorstack's layout"""
        menu_btn = create_toolbutton(self, icon=ima.icon('tooloptions'),
                                     tip=_('Options'))
        self.menu = QMenu(self)
        menu_btn.setMenu(self.menu)
        menu_btn.setPopupMode(menu_btn.InstantPopup)
        self.menu.aboutToShow.connect(self.__setup_menu)

#        self.filelist_btn = create_toolbutton(self,
#                             icon=ima.icon('filelist'),
#                             tip=_("File list management"),
#                             triggered=self.open_fileswitcher_dlg)
#
#        self.previous_btn = create_toolbutton(self,
#                             icon=ima.icon('previous'),
#                             tip=_("Previous file"),
#                             triggered=self.go_to_previous_file)
#
#        self.next_btn = create_toolbutton(self,
#                             icon=ima.icon('next'),
#                             tip=_("Next file"),
#                             triggered=self.go_to_next_file)

        # Optional tabs
#        corner_widgets = {Qt.TopRightCorner: [self.previous_btn,
#                                              self.filelist_btn, self.next_btn,
#                                              5, menu_btn]}
        corner_widgets = {Qt.TopRightCorner: [menu_btn]}
        self.tabs = BaseTabs(self, menu=self.menu, menu_use_tooltips=True,
                             corner_widgets=corner_widgets)
        self.tabs.tabBar().setObjectName('plugin-tab')
        self.tabs.set_close_function(self.close_file)
        self.tabs.setMovable(True)

        self.stack_history.refresh()

        if hasattr(self.tabs, 'setDocumentMode') \
           and not sys.platform == 'darwin':
            # Don't set document mode to true on OSX because it generates
            # a crash when the editor is detached from the main window
            # Fixes Issue 561
            self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self.current_changed)

        if sys.platform == 'darwin':
            tab_container = QWidget()
            tab_container.setObjectName('tab-container')
            tab_layout = QHBoxLayout(tab_container)
            tab_layout.setContentsMargins(0, 0, 0, 0)
            tab_layout.addWidget(self.tabs)
            layout.addWidget(tab_container)
        else:
            layout.addWidget(self.tabs)

    def add_corner_widgets_to_tabbar(self, widgets):
        self.tabs.add_corner_widgets(widgets)

    def closeEvent(self, event):
        self.threadmanager.close_all_threads()
        self.analysis_timer.timeout.disconnect(self.analyze_script)
        QWidget.closeEvent(self, event)
        if is_pyqt46:
            self.destroyed.emit()

    def clone_editor_from(self, other_finfo, set_current):
        fname = other_finfo.filename
        enc = other_finfo.encoding
        new = other_finfo.newly_created
        finfo = self.create_new_editor(fname, enc, "",
                                       set_current=set_current, new=new,
                                       cloned_from=other_finfo.editor)
        finfo.set_analysis_results(other_finfo.analysis_results)
        finfo.set_todo_results(other_finfo.todo_results)
        return finfo.editor

    def clone_from(self, other):
        """Clone EditorStack from other instance"""
        for other_finfo in other.data:
            self.clone_editor_from(other_finfo, set_current=True)
        self.set_stack_index(other.get_stack_index())

    @Slot()
    def open_fileswitcher_dlg(self):
        """Open file list management dialog box"""
        if not self.tabs.count():
            return
        if self.fileswitcher_dlg is not None and \
          self.fileswitcher_dlg.is_visible:
            self.fileswitcher_dlg.hide()
            self.fileswitcher_dlg.is_visible = False
            return
        self.fileswitcher_dlg = FileSwitcher(self, self, self.tabs, self.data,
                                             ima.icon('TextFileIcon'))
        self.fileswitcher_dlg.sig_goto_file.connect(self.set_stack_index)
        self.fileswitcher_dlg.setup()
        self.fileswitcher_dlg.show()
        self.fileswitcher_dlg.is_visible = True

    @Slot()
    def open_symbolfinder_dlg(self): 
        self.open_fileswitcher_dlg()
        self.fileswitcher_dlg.set_search_text('@')
        
    def update_fileswitcher_dlg(self):
        """Synchronize file list dialog box with editor widget tabs"""
        if self.fileswitcher_dlg:
            self.fileswitcher_dlg.setup()

    def get_current_tab_manager(self):
        """Get the widget with the TabWidget attribute."""
        return self

    def go_to_line(self):
        """Go to line dialog"""
        if self.data:
            self.get_current_editor().exec_gotolinedialog()

    def set_or_clear_breakpoint(self):
        """Set/clear breakpoint"""
        if self.data:
            editor = self.get_current_editor()
            editor.add_remove_breakpoint()

    def set_or_edit_conditional_breakpoint(self):
        """Set conditional breakpoint"""
        if self.data:
            editor = self.get_current_editor()
            editor.add_remove_breakpoint(edit_condition=True)

    def inspect_current_object(self):
        """Inspect current object in the Help plugin"""
        if self.introspector:
            editor = self.get_current_editor()
            position = editor.get_position('cursor')
            self.help.switch_to_editor_source()
            self.introspector.show_object_info(position, auto=False)
        else:
            text = self.get_current_editor().get_current_object()
            if text:
                self.send_to_help(text, force=True)

    #------ Editor Widget Settings
    def set_closable(self, state):
        """Parent widget must handle the closable state"""
        self.is_closable = state

    def set_io_actions(self, new_action, open_action,
                       save_action, revert_action):
        self.new_action = new_action
        self.open_action = open_action
        self.save_action = save_action
        self.revert_action = revert_action

    def set_find_widget(self, find_widget):
        self.find_widget = find_widget

    def set_outlineexplorer(self, outlineexplorer):
        self.outlineexplorer = outlineexplorer
        self.outlineexplorer.outlineexplorer_is_visible.connect(
                                                 self._refresh_outlineexplorer)

    def initialize_outlineexplorer(self):
        """This method is called separately from 'set_oulineexplorer' to avoid
        doing unnecessary updates when there are multiple editor windows"""
        for index in range(self.get_stack_count()):
            if index != self.get_stack_index():
                self._refresh_outlineexplorer(index=index)

    def add_outlineexplorer_button(self, editor_plugin):
        oe_btn = create_toolbutton(editor_plugin)
        oe_btn.setDefaultAction(self.outlineexplorer.visibility_action)
        self.add_corner_widgets_to_tabbar([5, oe_btn])

    def set_help(self, help_plugin):
        self.help = help_plugin

    def set_tempfile_path(self, path):
        self.tempfile_path = path

    def set_title(self, text):
        self.title = text

    def __update_editor_margins(self, editor):
        editor.setup_margins(linenumbers=self.linenumbers_enabled,
                             markers=self.has_markers())

    def __codeanalysis_settings_changed(self, current_finfo):
        if self.data:
            run_pyflakes, run_pep8 = self.pyflakes_enabled, self.pep8_enabled
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                finfo.cleanup_analysis_results()
                if (run_pyflakes or run_pep8) and current_finfo is not None:
                    if current_finfo is not finfo:
                        finfo.run_code_analysis(run_pyflakes, run_pep8)

    def set_pyflakes_enabled(self, state, current_finfo=None):
        # CONF.get(self.CONF_SECTION, 'code_analysis/pyflakes')
        self.pyflakes_enabled = state
        self.__codeanalysis_settings_changed(current_finfo)

    def set_pep8_enabled(self, state, current_finfo=None):
        # CONF.get(self.CONF_SECTION, 'code_analysis/pep8')
        self.pep8_enabled = state
        self.__codeanalysis_settings_changed(current_finfo)

    def has_markers(self):
        """Return True if this editorstack has a marker margin for TODOs or
        code analysis"""
        return self.todolist_enabled or self.pyflakes_enabled\
               or self.pep8_enabled

    def set_todolist_enabled(self, state, current_finfo=None):
        # CONF.get(self.CONF_SECTION, 'todo_list')
        self.todolist_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                finfo.cleanup_todo_results()
                if state and current_finfo is not None:
                    if current_finfo is not finfo:
                        finfo.run_todo_finder()

    def set_realtime_analysis_enabled(self, state):
        self.realtime_analysis_enabled = state

    def set_realtime_analysis_timeout(self, timeout):
        self.analysis_timer.setInterval(timeout)

    def set_linenumbers_enabled(self, state, current_finfo=None):
        # CONF.get(self.CONF_SECTION, 'line_numbers')
        self.linenumbers_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)

    def set_blanks_enabled(self, state):
        self.blanks_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_blanks_enabled(state)

    def set_edgeline_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'edge_line')
        self.edgeline_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_edge_line_enabled(state)

    def set_edgeline_column(self, column):
        # CONF.get(self.CONF_SECTION, 'edge_line_column')
        self.edgeline_column = column
        if self.data:
            for finfo in self.data:
                finfo.editor.set_edge_line_column(column)

    def set_codecompletion_auto_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'codecompletion_auto')
        self.codecompletion_auto_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_codecompletion_auto(state)

    def set_codecompletion_case_enabled(self, state):
        self.codecompletion_case_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_codecompletion_case(state)

    def set_codecompletion_enter_enabled(self, state):
        self.codecompletion_enter_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_codecompletion_enter(state)

    def set_calltips_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'calltips')
        self.calltips_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_calltips(state)

    def set_go_to_definition_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'go_to_definition')
        self.go_to_definition_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_go_to_definition_enabled(state)

    def set_close_parentheses_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'close_parentheses')
        self.close_parentheses_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_close_parentheses_enabled(state)

    def set_close_quotes_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'close_quotes')
        self.close_quotes_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_close_quotes_enabled(state)

    def set_add_colons_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'add_colons')
        self.add_colons_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_add_colons_enabled(state)

    def set_auto_unindent_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'auto_unindent')
        self.auto_unindent_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_auto_unindent_enabled(state)

    def set_indent_chars(self, indent_chars):
        # CONF.get(self.CONF_SECTION, 'indent_chars')
        indent_chars = indent_chars[1:-1] # removing the leading/ending '*'
        self.indent_chars = indent_chars
        if self.data:
            for finfo in self.data:
                finfo.editor.set_indent_chars(indent_chars)

    def set_tab_stop_width_spaces(self, tab_stop_width_spaces):
        # CONF.get(self.CONF_SECTION, 'tab_stop_width')
        self.tab_stop_width_spaces = tab_stop_width_spaces
        if self.data:
            for finfo in self.data:
                finfo.editor.setTabStopWidth(tab_stop_width_spaces
                                             * self.fontMetrics().width('9'))

    def set_help_enabled(self, state):
        self.help_enabled = state

    def set_default_font(self, font, color_scheme=None):
        self.default_font = font
        if color_scheme is not None:
            self.color_scheme = color_scheme
        if self.data:
            for finfo in self.data:
                finfo.editor.set_font(font, color_scheme)

    def set_color_scheme(self, color_scheme):
        self.color_scheme = color_scheme
        if self.data:
            for finfo in self.data:
                finfo.editor.set_color_scheme(color_scheme)

    def set_wrap_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'wrap')
        self.wrap_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_wrap_mode(state)

    def set_tabmode_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'tab_always_indent')
        self.tabmode_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_tab_mode(state)

    def set_intelligent_backspace_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'intelligent_backspace')
        self.intelligent_backspace_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_intelligent_backspace(state)

    def set_occurrence_highlighting_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'occurrence_highlighting')
        self.occurrence_highlighting_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurrence_highlighting(state)

    def set_occurrence_highlighting_timeout(self, timeout):
        # CONF.get(self.CONF_SECTION, 'occurrence_highlighting/timeout')
        self.occurrence_highlighting_timeout = timeout
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurrence_timeout(timeout)

    def set_highlight_current_line_enabled(self, state):
        self.highlight_current_line_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_highlight_current_line(state)

    def set_highlight_current_cell_enabled(self, state):
        self.highlight_current_cell_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_highlight_current_cell(state)

    def set_checkeolchars_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'check_eol_chars')
        self.checkeolchars_enabled = state

    def set_fullpath_sorting_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'fullpath_sorting')
        self.fullpath_sorting_enabled = state
        if self.data:
            finfo = self.data[self.get_stack_index()]
            new_index = self.data.index(finfo)
            self.__repopulate_stack()
            self.set_stack_index(new_index)

    def set_always_remove_trailing_spaces(self, state):
        # CONF.get(self.CONF_SECTION, 'always_remove_trailing_spaces')
        self.always_remove_trailing_spaces = state

    def set_focus_to_editor(self, state):
        self.focus_to_editor = state

    def set_introspector(self, introspector):
        self.introspector = introspector

    #------ Stacked widget management
    def get_stack_index(self):
        return self.tabs.currentIndex()

    def get_current_finfo(self):
        if self.data:
            return self.data[self.get_stack_index()]

    def get_current_editor(self):
        return self.tabs.currentWidget()

    def get_stack_count(self):
        return self.tabs.count()

    def set_stack_index(self, index, instance=None):
        if instance == self or instance == None:
            self.tabs.setCurrentIndex(index)

    def set_tabbar_visible(self, state):
        self.tabs.tabBar().setVisible(state)

    def remove_from_data(self, index):
        self.tabs.blockSignals(True)
        self.tabs.removeTab(index)
        self.data.pop(index)
        self.tabs.blockSignals(False)
        self.update_actions()
        self.update_fileswitcher_dlg()

    def __modified_readonly_title(self, title, is_modified, is_readonly):
        if is_modified is not None and is_modified:
            title += "*"
        if is_readonly is not None and is_readonly:
            title = "(%s)" % title
        return title

    def get_tab_text(self, index, is_modified=None, is_readonly=None):
        """Return tab title."""
        files_path_list = [finfo.filename for finfo in self.data]
        fname = self.data[index].filename
        fname = sourcecode.disambiguate_fname(files_path_list, fname)
        return self.__modified_readonly_title(fname,
                                              is_modified, is_readonly)

    def get_tab_tip(self, filename, is_modified=None, is_readonly=None):
        """Return tab menu title"""
        if self.fullpath_sorting_enabled:
            text = filename
        else:
            text = u"%s — %s"
        text = self.__modified_readonly_title(text,
                                              is_modified, is_readonly)
        if self.tempfile_path is not None\
           and filename == encoding.to_unicode_from_fs(self.tempfile_path):
            temp_file_str = to_text_string(_("Temporary file"))
            if self.fullpath_sorting_enabled:
                return "%s (%s)" % (text, temp_file_str)
            else:
                return text % (temp_file_str, self.tempfile_path)
        else:
            if self.fullpath_sorting_enabled:
                return text
            else:
                return text % (osp.basename(filename), osp.dirname(filename))

    def add_to_data(self, finfo, set_current):
        self.data.append(finfo)
        index = self.data.index(finfo)
        editor = finfo.editor
        self.tabs.insertTab(index, editor, self.get_tab_text(index))
        self.set_stack_title(index, False)
        if set_current:
            self.set_stack_index(index)
            self.current_changed(index)
        self.update_actions()
        self.update_fileswitcher_dlg()

    def __repopulate_stack(self):
        self.tabs.blockSignals(True)
        self.tabs.clear()
        for finfo in self.data:
            if finfo.newly_created:
                is_modified = True
            else:
                is_modified = None
            index = self.data.index(finfo)
            tab_text = self.get_tab_text(index, is_modified)
            tab_tip = self.get_tab_tip(finfo.filename)
            index = self.tabs.addTab(finfo.editor, tab_text)
            self.tabs.setTabToolTip(index, tab_tip)
        self.tabs.blockSignals(False)
        self.update_fileswitcher_dlg()

    def rename_in_data(self, index, new_filename):
        finfo = self.data[index]
        if osp.splitext(finfo.filename)[1] != osp.splitext(new_filename)[1]:
            # File type has changed!
            txt = to_text_string(finfo.editor.get_text_with_eol())
            language = get_file_language(new_filename, txt)
            finfo.editor.set_language(language)
        set_new_index = index == self.get_stack_index()
        current_fname = self.get_current_filename()
        finfo.filename = new_filename
        new_index = self.data.index(finfo)
        self.__repopulate_stack()
        if set_new_index:
            self.set_stack_index(new_index)
        else:
            # Fixes Issue 1287
            self.set_current_filename(current_fname)
        if self.outlineexplorer is not None:
            self.outlineexplorer.file_renamed(finfo.editor, finfo.filename)
        return new_index

    def set_stack_title(self, index, is_modified):
        finfo = self.data[index]
        fname = finfo.filename
        is_modified = (is_modified or finfo.newly_created) and not finfo.default
        is_readonly = finfo.editor.isReadOnly()
        tab_text = self.get_tab_text(index, is_modified, is_readonly)
        tab_tip = self.get_tab_tip(fname, is_modified, is_readonly)

        # Only update tab text if have changed, otherwise an unwanted scrolling
        # will happen when changing tabs. See Issue #1170.
        if tab_text != self.tabs.tabText(index):
            self.tabs.setTabText(index, tab_text)
        self.tabs.setTabToolTip(index, tab_tip)


    #------ Context menu
    def __setup_menu(self):
        """Setup tab context menu before showing it"""
        self.menu.clear()
        if self.data:
            actions = self.menu_actions
        else:
            actions = (self.new_action, self.open_action)
            self.setFocus() # --> Editor.__get_focus_editortabwidget
        add_actions(self.menu, list(actions)+self.__get_split_actions())
        self.close_action.setEnabled(self.is_closable)


    #------ Hor/Ver splitting
    def __get_split_actions(self):
        # New window
        self.newwindow_action = create_action(self, _("New window"),
                icon=ima.icon('newwindow'), tip=_("Create a new editor window"),
                triggered=lambda: self.create_new_window.emit())
        # Splitting
        self.versplit_action = create_action(self, _("Split vertically"),
                icon=ima.icon('versplit'),
                tip=_("Split vertically this editor window"),
                triggered=lambda: self.split_vertically.emit())
        self.horsplit_action = create_action(self, _("Split horizontally"),
                icon=ima.icon('horsplit'),
                tip=_("Split horizontally this editor window"),
                triggered=lambda: self.split_horizontally.emit())
        self.close_action = create_action(self, _("Close this panel"),
                icon=ima.icon('close_panel'), triggered=self.close)
        return [None, self.newwindow_action, None,
                self.versplit_action, self.horsplit_action, self.close_action]

    def reset_orientation(self):
        self.horsplit_action.setEnabled(True)
        self.versplit_action.setEnabled(True)

    def set_orientation(self, orientation):
        self.horsplit_action.setEnabled(orientation == Qt.Horizontal)
        self.versplit_action.setEnabled(orientation == Qt.Vertical)

    def update_actions(self):
        state = self.get_stack_count() > 0
        self.horsplit_action.setEnabled(state)
        self.versplit_action.setEnabled(state)


    #------ Accessors
    def get_current_filename(self):
        if self.data:
            return self.data[self.get_stack_index()].filename

    def has_filename(self, filename):
        fixpath = lambda path: osp.normcase(osp.realpath(path))
        for index, finfo in enumerate(self.data):
            if fixpath(filename) == fixpath(finfo.filename):
                return index

    def set_current_filename(self, filename):
        """Set current filename and return the associated editor instance"""
        index = self.has_filename(filename)
        if index is not None:
            self.set_stack_index(index)
            editor = self.data[index].editor
            editor.setFocus()
            return editor

    def is_file_opened(self, filename=None):
        if filename is None:
            # Is there any file opened?
            return len(self.data) > 0
        else:
            return self.has_filename(filename)


    #------ Close file, tabwidget...
    def close_file(self, index=None, force=False):
        """Close file (index=None -> close current file)
        Keep current file index unchanged (if current file
        that is being closed)"""
        current_index = self.get_stack_index()
        count = self.get_stack_count()

        if index is None:
            if count > 0:
                index = current_index
            else:
                self.find_widget.set_editor(None)
                return

        new_index = None
        if count > 1:
            if current_index == index:
                new_index = self._get_previous_file_index()
            else:
                new_index = current_index

        is_ok = force or self.save_if_changed(cancelable=True, index=index)
        if is_ok:
            finfo = self.data[index]
            self.threadmanager.close_threads(finfo)
            # Removing editor reference from outline explorer settings:
            if self.outlineexplorer is not None:
                self.outlineexplorer.remove_editor(finfo.editor)

            self.remove_from_data(index)

            # We pass self object ID as a QString, because otherwise it would
            # depend on the platform: long for 64bit, int for 32bit. Replacing
            # by long all the time is not working on some 32bit platforms
            # (see Issue 1094, Issue 1098)
            self.sig_close_file.emit(str(id(self)), index)

            if not self.data and self.is_closable:
                # editortabwidget is empty: removing it
                # (if it's not the first editortabwidget)
                self.close()

            self.opened_files_list_changed.emit()
            self.update_code_analysis_actions.emit()
            self._refresh_outlineexplorer()
            self.refresh_file_dependent_actions.emit()
            self.update_plugin_title.emit()

            editor = self.get_current_editor()
            if editor:
                editor.setFocus()

            if new_index is not None:
                if index < new_index:
                    new_index -= 1
                self.set_stack_index(new_index)

            self.add_last_closed_file(finfo.filename)

        if self.get_stack_count() == 0 and self.create_new_file_if_empty:
            self.sig_new_file[()].emit()
            return False
        self.__modify_stack_title()
        return is_ok

    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass

    def close_all_right(self):
        """ Close all files opened to the right """
        num = self.get_stack_index()
        n = self.get_stack_count()
        for i in range(num, n-1):
            self.close_file(num+1)
    
    def close_all_but_this(self):
        """Close all files but the current one"""
        self.close_all_right()
        for i in range(0, self.get_stack_count()-1  ):
            self.close_file(0)
            
    def add_last_closed_file(self, fname):
        """Add to last closed file list."""
        if fname in self.last_closed_files:
            self.last_closed_files.remove(fname)
        self.last_closed_files.insert(0, fname)
        if len(self.last_closed_files) > 10: 
            self.last_closed_files.pop(-1)

    def get_last_closed_files(self):
        return self.last_closed_files

    def set_last_closed_files(self, fnames):
        self.last_closed_files = fnames

    #------ Save
    def save_if_changed(self, cancelable=False, index=None):
        """Ask user to save file if modified"""
        if index is None:
            indexes = list(range(self.get_stack_count()))
        else:
            indexes = [index]
        buttons = QMessageBox.Yes | QMessageBox.No
        if cancelable:
            buttons |= QMessageBox.Cancel
        unsaved_nb = 0
        for index in indexes:
            if self.data[index].editor.document().isModified():
                unsaved_nb += 1
        if not unsaved_nb:
            # No file to save
            return True
        if unsaved_nb > 1:
            buttons |= QMessageBox.YesAll | QMessageBox.NoAll
        yes_all = False
        for index in indexes:
            self.set_stack_index(index)
            finfo = self.data[index]
            if finfo.filename == self.tempfile_path or yes_all:
                if not self.save():
                    return False
            elif finfo.editor.document().isModified():
                answer = QMessageBox.question(self, self.title,
                            _("<b>%s</b> has been modified."
                              "<br>Do you want to save changes?"
                              ) % osp.basename(finfo.filename),
                            buttons)
                if answer == QMessageBox.Yes:
                    if not self.save():
                        return False
                elif answer == QMessageBox.YesAll:
                    if not self.save():
                        return False
                    yes_all = True
                elif answer == QMessageBox.NoAll:
                    return True
                elif answer == QMessageBox.Cancel:
                    return False
        return True

    def save(self, index=None, force=False):
        """Save file"""
        if index is None:
            # Save the currently edited file
            if not self.get_stack_count():
                return
            index = self.get_stack_index()

        finfo = self.data[index]
        if not (finfo.editor.document().isModified() or
                finfo.newly_created) and not force:
            return True
        if not osp.isfile(finfo.filename) and not force:
            # File has not been saved yet
            return self.save_as(index=index)
        if self.always_remove_trailing_spaces:
            self.remove_trailing_spaces(index)
        txt = to_text_string(finfo.editor.get_text_with_eol())
        try:
            finfo.encoding = encoding.write(txt, finfo.filename,
                                            finfo.encoding)
            finfo.newly_created = False
            self.encoding_changed.emit(finfo.encoding)
            finfo.lastmodified = QFileInfo(finfo.filename).lastModified()

            # We pass self object ID as a QString, because otherwise it would
            # depend on the platform: long for 64bit, int for 32bit. Replacing
            # by long all the time is not working on some 32bit platforms
            # (see Issue 1094, Issue 1098)
            self.file_saved.emit(str(id(self)), index, finfo.filename)

            finfo.editor.document().setModified(False)
            self.modification_changed(index=index)
            self.analyze_script(index)
            self.introspector.validate()

            #XXX CodeEditor-only: re-scan the whole text to rebuild outline
            # explorer data from scratch (could be optimized because
            # rehighlighting text means searching for all syntax coloring
            # patterns instead of only searching for class/def patterns which
            # would be sufficient for outline explorer data.
            finfo.editor.rehighlight()

            self._refresh_outlineexplorer(index)
            return True
        except EnvironmentError as error:
            QMessageBox.critical(self, _("Save"),
                                 _("<b>Unable to save file '%s'</b>"
                                   "<br><br>Error message:<br>%s"
                                   ) % (osp.basename(finfo.filename),
                                        str(error)))
            return False

    def file_saved_in_other_editorstack(self, index, filename):
        """
        File was just saved in another editorstack, let's synchronize!
        This avoid file to be automatically reloaded

        Filename is passed in case file was just saved as another name
        """
        finfo = self.data[index]
        finfo.newly_created = False
        finfo.filename = to_text_string(filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()

    def select_savename(self, original_filename):
        self.redirect_stdio.emit(False)
        filename, _selfilter = getsavefilename(self, _("Save file"),
                                       original_filename,
                                       get_edit_filters(),
                                       get_filter(get_edit_filetypes(),
                                           osp.splitext(original_filename)[1]))
        self.redirect_stdio.emit(True)
        if filename:
            return osp.normpath(filename)

    def save_as(self, index=None):
        """Save file as..."""
        if index is None:
            # Save the currently edited file
            index = self.get_stack_index()
        finfo = self.data[index]
        # The next line is necessary to avoid checking if the file exists
        # While running __check_file_status
        # See issues 3678 and 3026
        finfo.newly_created = True
        filename = self.select_savename(finfo.filename)
        if filename:
            ao_index = self.has_filename(filename)
            # Note: ao_index == index --> saving an untitled file
            if ao_index and ao_index != index:
                if not self.close_file(ao_index):
                    return
                if ao_index < index:
                    index -= 1

            new_index = self.rename_in_data(index, new_filename=filename)

            # We pass self object ID as a QString, because otherwise it would
            # depend on the platform: long for 64bit, int for 32bit. Replacing
            # by long all the time is not working on some 32bit platforms
            # (see Issue 1094, Issue 1098)
            self.file_renamed_in_data.emit(str(id(self)), index, filename)

            ok = self.save(index=new_index, force=True)
            self.refresh(new_index)
            self.set_stack_index(new_index)
            return ok
        else:
            return False

    def save_copy_as(self, index=None):
        """Save copy of file as..."""
        if index is None:
            # Save the currently edited file
            index = self.get_stack_index()
        finfo = self.data[index]
        filename = self.select_savename(finfo.filename)
        if filename:
            ao_index = self.has_filename(filename)
            # Note: ao_index == index --> saving an untitled file
            if ao_index and ao_index != index:
                if not self.close_file(ao_index):
                    return
                if ao_index < index:
                    index -= 1
            txt = to_text_string(finfo.editor.get_text_with_eol())
            try:
                finfo.encoding = encoding.write(txt, filename, finfo.encoding)
                self.file_saved.emit(str(id(self)), index, filename)

                # open created copy file
                self.plugin_load.emit(filename)
                return True
            except EnvironmentError as error:
                QMessageBox.critical(self, _("Save"),
                                     _("<b>Unable to save file '%s'</b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (osp.basename(finfo.filename),
                                            str(error)))
        else:
            return False

    def save_all(self):
        """Save all opened files"""
        folders = set()
        for index in range(self.get_stack_count()):
            if self.data[index].editor.document().isModified():
                folders.add(osp.dirname(self.data[index].filename))
                self.save(index)

    #------ Update UI
    def start_stop_analysis_timer(self):
        self.is_analysis_done = False
        if self.realtime_analysis_enabled:
            self.analysis_timer.stop()
            self.analysis_timer.start()

    def analyze_script(self, index=None):
        """Analyze current script with pyflakes + find todos"""
        if self.is_analysis_done:
            return
        if index is None:
            index = self.get_stack_index()
        if self.data:
            finfo = self.data[index]
            run_pyflakes, run_pep8 = self.pyflakes_enabled, self.pep8_enabled
            if run_pyflakes or run_pep8:
                finfo.run_code_analysis(run_pyflakes, run_pep8)
            if self.todolist_enabled:
                finfo.run_todo_finder()
        self.is_analysis_done = True

    def set_analysis_results(self, index, analysis_results):
        """Synchronize analysis results between editorstacks"""
        self.data[index].set_analysis_results(analysis_results)

    def get_analysis_results(self):
        if self.data:
            return self.data[self.get_stack_index()].analysis_results

    def set_todo_results(self, index, todo_results):
        """Synchronize todo results between editorstacks"""
        self.data[index].set_todo_results(todo_results)

    def get_todo_results(self):
        if self.data:
            return self.data[self.get_stack_index()].todo_results

    def current_changed(self, index):
        """Stack index has changed"""
#        count = self.get_stack_count()
#        for btn in (self.filelist_btn, self.previous_btn, self.next_btn):
#            btn.setEnabled(count > 1)

        editor = self.get_current_editor()
        if index != -1:
            editor.setFocus()
            if DEBUG_EDITOR:
                print("setfocusto:", editor, file=STDOUT)
        else:
            self.reset_statusbar.emit()
        self.opened_files_list_changed.emit()

        self.stack_history.refresh()

        while index in self.stack_history:
            self.stack_history.remove(index)
        self.stack_history.append(index)
        if DEBUG_EDITOR:
            print("current_changed:", index, self.data[index].editor, end=' ', file=STDOUT)
            print(self.data[index].editor.get_document_id(), file=STDOUT)

        self.update_plugin_title.emit()
        if editor is not None:
            self.current_file_changed.emit(self.data[index].filename,
                                           editor.get_position('cursor'))

    def _get_previous_file_index(self):
        if len(self.stack_history) > 1:
            last = len(self.stack_history)-1
            w_id = self.stack_history.pop(last)
            self.stack_history.insert(0, w_id)

            return self.stack_history[last]

    def tab_navigation_mru(self, forward=True):
        """
        Tab navigation with "most recently used" behaviour.

        It's fired when pressing 'go to previous file' or 'go to next file'
        shortcuts.

        forward:
            True: move to next file
            False: move to previous file
        """
        if self.tabs_switcher is None or not self.tabs_switcher.isVisible():
            self.tabs_switcher = TabSwitcherWidget(self, self.stack_history,
                                                   self.tabs)
            self.tabs_switcher.show()

        self.tabs_switcher.select_row(1 if forward else -1)

    def focus_changed(self):
        """Editor focus has changed"""
        fwidget = QApplication.focusWidget()
        for finfo in self.data:
            if fwidget is finfo.editor:
                self.refresh()
        self.editor_focus_changed.emit()

    def _refresh_outlineexplorer(self, index=None, update=True, clear=False):
        """Refresh outline explorer panel"""
        oe = self.outlineexplorer
        if oe is None:
            return
        if index is None:
            index = self.get_stack_index()
        enable = False
        if self.data:
            finfo = self.data[index]
            if finfo.editor.is_python():
                enable = True
                oe.setEnabled(True)
                oe.set_current_editor(finfo.editor, finfo.filename,
                                      update=update, clear=clear)
        if not enable:
            oe.setEnabled(False)

    def __refresh_statusbar(self, index):
        """Refreshing statusbar widgets"""
        finfo = self.data[index]
        self.encoding_changed.emit(finfo.encoding)
        # Refresh cursor position status:
        line, index = finfo.editor.get_cursor_line_column()
        self.sig_editor_cursor_position_changed.emit(line, index)

    def __refresh_readonly(self, index):
        finfo = self.data[index]
        read_only = not QFileInfo(finfo.filename).isWritable()
        if not osp.isfile(finfo.filename):
            # This is an 'untitledX.py' file (newly created)
            read_only = False
        finfo.editor.setReadOnly(read_only)
        self.readonly_changed.emit(read_only)

    def __check_file_status(self, index):
        """Check if file has been changed in any way outside Spyder:
        1. removed, moved or renamed outside Spyder
        2. modified outside Spyder"""
        if self.__file_status_flag:
            # Avoid infinite loop: when the QMessageBox.question pops, it
            # gets focus and then give it back to the CodeEditor instance,
            # triggering a refresh cycle which calls this method
            return
        self.__file_status_flag = True

        finfo = self.data[index]
        name = osp.basename(finfo.filename)

        if finfo.newly_created:
            # File was just created (not yet saved): do nothing
            # (do not return because of the clean-up at the end of the method)
            pass

        elif not osp.isfile(finfo.filename):
            # File doesn't exist (removed, moved or offline):
            answer = QMessageBox.warning(self, self.title,
                                _("<b>%s</b> is unavailable "
                                  "(this file may have been removed, moved "
                                  "or renamed outside Spyder)."
                                  "<br>Do you want to close it?") % name,
                                QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.Yes:
                self.close_file(index)
            else:
                finfo.newly_created = True
                finfo.editor.document().setModified(True)
                self.modification_changed(index=index)

        else:
            # Else, testing if it has been modified elsewhere:
            lastm = QFileInfo(finfo.filename).lastModified()
            if to_text_string(lastm.toString()) \
               != to_text_string(finfo.lastmodified.toString()):
                if finfo.editor.document().isModified():
                    answer = QMessageBox.question(self,
                                self.title,
                                _("<b>%s</b> has been modified outside Spyder."
                                  "<br>Do you want to reload it and lose all "
                                  "your changes?") % name,
                                QMessageBox.Yes | QMessageBox.No)
                    if answer == QMessageBox.Yes:
                        self.reload(index)
                    else:
                        finfo.lastmodified = lastm
                else:
                    self.reload(index)

        # Finally, resetting temporary flag:
        self.__file_status_flag = False

    def __modify_stack_title(self):
        for index, finfo in enumerate(self.data):
            state = finfo.editor.document().isModified()
            self.set_stack_title(index, state)

    def refresh(self, index=None):
        """Refresh tabwidget"""
        if index is None:
            index = self.get_stack_index()
        # Set current editor
        if self.get_stack_count():
            index = self.get_stack_index()
            finfo = self.data[index]
            editor = finfo.editor
            editor.setFocus()
            self._refresh_outlineexplorer(index, update=False)
            self.update_code_analysis_actions.emit()
            self.__refresh_statusbar(index)
            self.__refresh_readonly(index)
            self.__check_file_status(index)
            self.__modify_stack_title()
            self.update_plugin_title.emit()
        else:
            editor = None
        # Update the modification-state-dependent parameters
        self.modification_changed()
        # Update FindReplace binding
        self.find_widget.set_editor(editor, refresh=False)

    def modification_changed(self, state=None, index=None, editor_id=None):
        """
        Current editor's modification state has changed
        --> change tab title depending on new modification state
        --> enable/disable save/save all actions
        """
        if editor_id is not None:
            for index, _finfo in enumerate(self.data):
                if id(_finfo.editor) == editor_id:
                    break
        # This must be done before refreshing save/save all actions:
        # (otherwise Save/Save all actions will always be enabled)
        self.opened_files_list_changed.emit()
        # --
        if index is None:
            index = self.get_stack_index()
        if index == -1:
            return
        finfo = self.data[index]
        if state is None:
            state = finfo.editor.document().isModified() or finfo.newly_created
        self.set_stack_title(index, state)
        # Toggle save/save all actions state
        self.save_action.setEnabled(state)
        self.refresh_save_all_action.emit()
        # Refreshing eol mode
        eol_chars = finfo.editor.get_line_separator()
        self.refresh_eol_chars(eol_chars)
        self.stack_history.refresh()

    def refresh_eol_chars(self, eol_chars):
        os_name = sourcecode.get_os_name_from_eol_chars(eol_chars)
        self.sig_refresh_eol_chars.emit(os_name)


    #------ Load, reload
    def reload(self, index):
        """Reload file from disk"""
        finfo = self.data[index]
        txt, finfo.encoding = encoding.read(finfo.filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
        position = finfo.editor.get_position('cursor')
        finfo.editor.set_text(txt)
        finfo.editor.document().setModified(False)
        finfo.editor.set_cursor_position(position)
        self.introspector.validate()

        #XXX CodeEditor-only: re-scan the whole text to rebuild outline
        # explorer data from scratch (could be optimized because
        # rehighlighting text means searching for all syntax coloring
        # patterns instead of only searching for class/def patterns which
        # would be sufficient for outline explorer data.
        finfo.editor.rehighlight()

        self._refresh_outlineexplorer(index)

    def revert(self):
        """Revert file from disk"""
        index = self.get_stack_index()
        finfo = self.data[index]
        filename = finfo.filename
        if finfo.editor.document().isModified():
            answer = QMessageBox.warning(self, self.title,
                                _("All changes to <b>%s</b> will be lost."
                                  "<br>Do you want to revert file from disk?"
                                  ) % osp.basename(filename),
                                  QMessageBox.Yes|QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self.reload(index)

    def create_new_editor(self, fname, enc, txt, set_current, new=False,
                          cloned_from=None):
        """
        Create a new editor instance
        Returns finfo object (instead of editor as in previous releases)
        """
        editor = codeeditor.CodeEditor(self)
        introspector = self.introspector
        editor.get_completions.connect(introspector.get_completions)
        editor.sig_show_object_info.connect(introspector.show_object_info)
        editor.go_to_definition.connect(introspector.go_to_definition)

        finfo = FileInfo(fname, enc, editor, new, self.threadmanager,
                         self.introspector)

        self.add_to_data(finfo, set_current)
        finfo.send_to_help.connect(self.send_to_help)
        finfo.analysis_results_changed.connect(
                                  lambda: self.analysis_results_changed.emit())
        finfo.todo_results_changed.connect(
                                      lambda: self.todo_results_changed.emit())
        finfo.edit_goto.connect(lambda fname, lineno, name:
                                self.edit_goto.emit(fname, lineno, name))
        finfo.save_breakpoints.connect(lambda s1, s2:
                                       self.save_breakpoints.emit(s1, s2))
        editor.run_selection.connect(self.run_selection)
        editor.run_cell.connect(self.run_cell)
        editor.run_cell_and_advance.connect(self.run_cell_and_advance)
        editor.re_run_last_cell.connect(self.re_run_last_cell)
        editor.sig_new_file.connect(self.sig_new_file.emit)
        language = get_file_language(fname, txt)
        editor.setup_editor(
                linenumbers=self.linenumbers_enabled,
                show_blanks=self.blanks_enabled,
                edge_line=self.edgeline_enabled,
                edge_line_column=self.edgeline_column, language=language,
                markers=self.has_markers(), font=self.default_font,
                color_scheme=self.color_scheme,
                wrap=self.wrap_enabled, tab_mode=self.tabmode_enabled,
                intelligent_backspace=self.intelligent_backspace_enabled,
                highlight_current_line=self.highlight_current_line_enabled,
                highlight_current_cell=self.highlight_current_cell_enabled,
                occurrence_highlighting=self.occurrence_highlighting_enabled,
                occurrence_timeout=self.occurrence_highlighting_timeout,
                codecompletion_auto=self.codecompletion_auto_enabled,
                codecompletion_case=self.codecompletion_case_enabled,
                codecompletion_enter=self.codecompletion_enter_enabled,
                calltips=self.calltips_enabled,
                go_to_definition=self.go_to_definition_enabled,
                close_parentheses=self.close_parentheses_enabled,
                close_quotes=self.close_quotes_enabled,
                add_colons=self.add_colons_enabled,
                auto_unindent=self.auto_unindent_enabled,
                indent_chars=self.indent_chars,
                tab_stop_width_spaces=self.tab_stop_width_spaces,
                cloned_from=cloned_from,
                filename=fname)
        if cloned_from is None:
            editor.set_text(txt)
            editor.document().setModified(False)
        finfo.text_changed_at.connect(
                                    lambda fname, position:
                                    self.text_changed_at.emit(fname, position))
        editor.sig_cursor_position_changed.connect(
                                           self.editor_cursor_position_changed)
        editor.textChanged.connect(self.start_stop_analysis_timer)
        editor.modificationChanged.connect(
                     lambda state: self.modification_changed(state,
                                                    editor_id=id(editor)))
        editor.focus_in.connect(self.focus_changed)
        editor.zoom_in.connect(lambda: self.zoom_in.emit())
        editor.zoom_out.connect(lambda: self.zoom_out.emit())
        editor.zoom_reset.connect(lambda: self.zoom_reset.emit())
        editor.sig_eol_chars_changed.connect(lambda eol_chars: self.refresh_eol_chars(eol_chars))
        if self.outlineexplorer is not None:
            # Removing editor reference from outline explorer settings:
            editor.destroyed.connect(lambda obj=editor:
                                     self.outlineexplorer.remove_editor(obj))

        self.find_widget.set_editor(editor)

        self.refresh_file_dependent_actions.emit()
        self.modification_changed(index=self.data.index(finfo))

        # Needs to reset the highlighting on startup in case the PygmentsSH
        # is in use
        editor.run_pygments_highlighter()

        return finfo

    def editor_cursor_position_changed(self, line, index):
        """Cursor position of one of the editor in the stack has changed"""
        self.sig_editor_cursor_position_changed.emit(line, index)

    def send_to_help(self, qstr1, qstr2=None, qstr3=None, qstr4=None,
                     force=False):
        """qstr1: obj_text, qstr2: argpspec, qstr3: note, qstr4: doc_text"""
        if not force and not self.help_enabled:
            return
        if self.help is not None \
          and (force or self.help.dockwidget.isVisible()):
            # Help plugin exists and is visible
            if qstr4 is None:
                self.help.set_object_text(qstr1, ignore_unknown=True,
                                          force_refresh=force)
            else:
                objtxt = to_text_string(qstr1)
                name = objtxt.split('.')[-1]
                argspec = to_text_string(qstr2)
                note = to_text_string(qstr3)
                docstring = to_text_string(qstr4)
                doc = {'obj_text': objtxt, 'name': name, 'argspec': argspec,
                       'note': note, 'docstring': docstring}
                self.help.set_editor_doc(doc, force_refresh=force)
            editor = self.get_current_editor()
            editor.setFocus()

    def new(self, filename, encoding, text, default_content=False):
        """
        Create new filename with *encoding* and *text*
        """
        finfo = self.create_new_editor(filename, encoding, text,
                                       set_current=False, new=True)
        finfo.editor.set_cursor_position('eof')
        finfo.editor.insert_text(os.linesep)
        if default_content:
            finfo.default = True
            finfo.editor.document().setModified(False)
        return finfo

    def load(self, filename, set_current=True):
        """
        Load filename, create an editor instance and return it
        *Warning* This is loading file, creating editor but not executing
        the source code analysis -- the analysis must be done by the editor
        plugin (in case multiple editorstack instances are handled)
        """
        filename = osp.abspath(to_text_string(filename))
        self.starting_long_process.emit(_("Loading %s...") % filename)
        text, enc = encoding.read(filename)
        finfo = self.create_new_editor(filename, enc, text, set_current)
        index = self.data.index(finfo)
        self._refresh_outlineexplorer(index, update=True)
        self.ending_long_process.emit("")
        if self.isVisible() and self.checkeolchars_enabled \
           and sourcecode.has_mixed_eol_chars(text):
            name = osp.basename(filename)
            QMessageBox.warning(self, self.title,
                                _("<b>%s</b> contains mixed end-of-line "
                                  "characters.<br>Spyder will fix this "
                                  "automatically.") % name,
                                QMessageBox.Ok)
            self.set_os_eol_chars(index)
        self.is_analysis_done = False
        return finfo

    def set_os_eol_chars(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        eol_chars = sourcecode.get_eol_chars_from_os_name(os.name)
        finfo.editor.set_eol_chars(eol_chars)
        finfo.editor.document().setModified(True)

    def remove_trailing_spaces(self, index=None):
        """Remove trailing spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.remove_trailing_spaces()

    def fix_indentation(self, index=None):
        """Replace tab characters by spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.fix_indentation()

    #------ Run
    def run_selection(self):
        """
        Run selected text or current line in console. 

        If some text is selected, then execute that text in console.

        If no text is selected, then execute current line, unless current line
        is empty. Then, advance cursor to next line. If cursor is on last line
        and that line is not empty, then add a new blank line and move the
        cursor there. If cursor is on last line and that line is empty, then do
        not move cursor.
        """
        text = self.get_current_editor().get_selection_as_executable_code()
        if text:
            self.exec_in_extconsole.emit(text, self.focus_to_editor)
            return
        editor = self.get_current_editor()
        line = editor.get_current_line()
        text = line.lstrip()
        if text:
            self.exec_in_extconsole.emit(text, self.focus_to_editor)
        if editor.is_cursor_on_last_line() and text:
            editor.append(editor.get_line_separator())
        editor.move_cursor_to_next('line', 'down')

    def run_cell(self):
        """Run current cell"""
        text = self.get_current_editor().get_cell_as_executable_code()
        finfo = self.get_current_finfo()
        if finfo.editor.is_python() and text:
            self.exec_in_extconsole.emit(text, self.focus_to_editor)

    def run_cell_and_advance(self):
        """Run current cell and advance to the next one"""
        self.run_cell()
        self.advance_cell()

    def advance_cell(self, reverse=False):
        """Advance to the next cell.

        reverse = True --> go to previous cell.
        """
        if not reverse:
            move_func = self.get_current_editor().go_to_next_cell
        else:
            move_func = self.get_current_editor().go_to_previous_cell

        if self.focus_to_editor:
            move_func()
        else:
            term = QApplication.focusWidget()
            move_func()
            term.setFocus()
            term = QApplication.focusWidget()
            move_func()
            term.setFocus()

    def re_run_last_cell(self):
        text = self.get_current_editor().get_last_cell_as_executable_code()
        finfo = self.get_current_finfo()
        if finfo.editor.is_python() and text:
            self.exec_in_extconsole.emit(text, self.focus_to_editor)

    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        # The second check is necessary on Windows, where source.hasUrls()
        # can return True but source.urls() is []
        if source.hasUrls() and source.urls():
            all_urls = mimedata2url(source)
            text = [encoding.is_text_file(url) for url in all_urls]
            if any(text):
                event.acceptProposedAction()
            else:
                event.ignore()
        elif source.hasText():
            event.acceptProposedAction()
        elif os.name == 'nt':
            # This covers cases like dragging from compressed files,
            # which can be opened by the Editor if they are plain
            # text, but doesn't come with url info.
            # Fixes Issue 2032
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        if source.hasUrls():
            files = mimedata2url(source)
            files = [f for f in files if encoding.is_text_file(f)]
            files = set(files or [])
            for fname in files:
                self.plugin_load.emit(fname)
        elif source.hasText():
            editor = self.get_current_editor()
            if editor is not None:
                editor.insert_text( source.text() )
        event.acceptProposedAction()

    def keyReleaseEvent(self, event):
        """Reimplement Qt method.

        Handle "most recent used" tab behavior,
        When ctrl is released and tab_switcher is visible, tab will be changed.
        """
        if self.tabs_switcher is not None and self.tabs_switcher.isVisible():
            qsc = get_shortcut(context='Editor', name='Go to next file')

            for key in qsc.split('+'):
                key = key.lower()
                if ((key == 'ctrl' and event.key() == Qt.Key_Control) or
                   (key == 'alt' and event.key() == Qt.Key_Alt)):
                        self.tabs_switcher.item_selected()
                        self.tabs_switcher = None
                        return

        super(EditorStack, self).keyPressEvent(event)


class EditorSplitter(QSplitter):
    def __init__(self, parent, plugin, menu_actions, first=False,
                 register_editorstack_cb=None, unregister_editorstack_cb=None):
        QSplitter.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setChildrenCollapsible(False)

        self.toolbar_list = None
        self.menu_list = None

        self.plugin = plugin

        if register_editorstack_cb is None:
            register_editorstack_cb = self.plugin.register_editorstack
        self.register_editorstack_cb = register_editorstack_cb
        if unregister_editorstack_cb is None:
            unregister_editorstack_cb = self.plugin.unregister_editorstack
        self.unregister_editorstack_cb = unregister_editorstack_cb

        self.menu_actions = menu_actions
        self.editorstack = EditorStack(self, menu_actions)
        self.register_editorstack_cb(self.editorstack)
        if not first:
            self.plugin.clone_editorstack(editorstack=self.editorstack)
        self.editorstack.destroyed.connect(lambda: self.editorstack_closed())
        self.editorstack.split_vertically.connect(
                     lambda: self.split(orientation=Qt.Vertical))
        self.editorstack.split_horizontally.connect(
                     lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editorstack)

    def closeEvent(self, event):
        QSplitter.closeEvent(self, event)
        if is_pyqt46:
            self.destroyed.emit()

    def __give_focus_to_remaining_editor(self):
        focus_widget = self.plugin.get_focus_widget()
        if focus_widget is not None:
            focus_widget.setFocus()

    def editorstack_closed(self):
        if DEBUG_EDITOR:
            print("method 'editorstack_closed':", file=STDOUT)
            print("    self  :", self, file=STDOUT)
#            print >>STDOUT, "    sender:", self.sender()
        self.unregister_editorstack_cb(self.editorstack)
        self.editorstack = None
        try:
            close_splitter = self.count() == 1
        except RuntimeError:
            # editorsplitter has been destroyed (happens when closing a
            # EditorMainWindow instance)
            return
        if close_splitter:
            # editorstack just closed was the last widget in this QSplitter
            self.close()
            return
        self.__give_focus_to_remaining_editor()

    def editorsplitter_closed(self):
        if DEBUG_EDITOR:
            print("method 'editorsplitter_closed':", file=STDOUT)
            print("    self  :", self, file=STDOUT)
#            print >>STDOUT, "    sender:", self.sender()
        try:
            close_splitter = self.count() == 1 and self.editorstack is None
        except RuntimeError:
            # editorsplitter has been destroyed (happens when closing a
            # EditorMainWindow instance)
            return
        if close_splitter:
            # editorsplitter just closed was the last widget in this QSplitter
            self.close()
            return
        elif self.count() == 2 and self.editorstack:
            # back to the initial state: a single editorstack instance,
            # as a single widget in this QSplitter: orientation may be changed
            self.editorstack.reset_orientation()
        self.__give_focus_to_remaining_editor()

    def split(self, orientation=Qt.Vertical):
        self.setOrientation(orientation)
        self.editorstack.set_orientation(orientation)
        editorsplitter = EditorSplitter(self.parent(), self.plugin,
                    self.menu_actions,
                    register_editorstack_cb=self.register_editorstack_cb,
                    unregister_editorstack_cb=self.unregister_editorstack_cb)
        self.addWidget(editorsplitter)
        editorsplitter.destroyed.connect(lambda: self.editorsplitter_closed())
        current_editor = editorsplitter.editorstack.get_current_editor()
        if current_editor is not None:
            current_editor.setFocus()

    def iter_editorstacks(self):
        editorstacks = [(self.widget(0), self.orientation())]
        if self.count() > 1:
            editorsplitter = self.widget(1)
            editorstacks += editorsplitter.iter_editorstacks()
        return editorstacks

    def get_layout_settings(self):
        """Return layout state"""
        splitsettings = []
        for editorstack, orientation in self.iter_editorstacks():
            clines = [finfo.editor.get_cursor_line_number()
                      for finfo in editorstack.data]
            cfname = editorstack.get_current_filename()
            splitsettings.append((orientation == Qt.Vertical, cfname, clines))
        return dict(hexstate=qbytearray_to_str(self.saveState()),
                    sizes=self.sizes(), splitsettings=splitsettings)

    def set_layout_settings(self, settings):
        """Restore layout state"""
        splitsettings = settings.get('splitsettings')
        if splitsettings is None:
            return
        splitter = self
        editor = None
        for index, (is_vertical, cfname, clines) in enumerate(splitsettings):
            if index > 0:
                splitter.split(Qt.Vertical if is_vertical else Qt.Horizontal)
                splitter = splitter.widget(1)
            editorstack = splitter.widget(0)
            for index, finfo in enumerate(editorstack.data):
                editor = finfo.editor
                # FIXME: Temporal fix
                try:
                    editor.go_to_line(clines[index])
                except IndexError:
                    pass
            editorstack.set_current_filename(cfname)
        hexstate = settings.get('hexstate')
        if hexstate is not None:
            self.restoreState( QByteArray().fromHex(
                    str(hexstate).encode('utf-8')) )
        sizes = settings.get('sizes')
        if sizes is not None:
            self.setSizes(sizes)
        if editor is not None:
            editor.clearFocus()
            editor.setFocus()


class EditorWidget(QSplitter):
    def __init__(self, parent, plugin, menu_actions, show_fullpath,
                 fullpath_sorting, show_all_files, show_comments):
        QSplitter.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        statusbar = parent.statusBar() # Create a status bar
        self.readwrite_status = ReadWriteStatus(self, statusbar)
        self.eol_status = EOLStatus(self, statusbar)
        self.encoding_status = EncodingStatus(self, statusbar)
        self.cursorpos_status = CursorPositionStatus(self, statusbar)

        self.editorstacks = []

        self.plugin = plugin

        self.find_widget = FindReplace(self, enable_replace=True)
        self.plugin.register_widget_shortcuts(self.find_widget)
        self.find_widget.hide()
        self.outlineexplorer = OutlineExplorerWidget(self,
                                            show_fullpath=show_fullpath,
                                            fullpath_sorting=fullpath_sorting,
                                            show_all_files=show_all_files,
                                            show_comments=show_comments)
        self.outlineexplorer.edit_goto.connect(
                     lambda filenames, goto, word:
                     plugin.load(filenames=filenames, goto=goto, word=word,
                                 editorwindow=self.parent()))

        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        editorsplitter = EditorSplitter(self, plugin, menu_actions,
                        register_editorstack_cb=self.register_editorstack,
                        unregister_editorstack_cb=self.unregister_editorstack)
        self.editorsplitter = editorsplitter
        editor_layout.addWidget(editorsplitter)
        editor_layout.addWidget(self.find_widget)

        splitter = QSplitter(self)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(editor_widgets)
        splitter.addWidget(self.outlineexplorer)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        # Refreshing outline explorer
        editorsplitter.editorstack.initialize_outlineexplorer()

    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        if DEBUG_EDITOR:
            print("EditorWidget.register_editorstack:", editorstack, file=STDOUT)
            self.__print_editorstacks()
        self.plugin.last_focus_editorstack[self.parent()] = editorstack
        editorstack.set_closable( len(self.editorstacks) > 1 )
        editorstack.set_outlineexplorer(self.outlineexplorer)
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
        self.plugin.register_editorstack(editorstack)
        oe_btn = create_toolbutton(self)
        oe_btn.setDefaultAction(self.outlineexplorer.visibility_action)
        editorstack.add_corner_widgets_to_tabbar([5, oe_btn])

    def __print_editorstacks(self):
        print("%d editorstack(s) in editorwidget:" \
                        % len(self.editorstacks), file=STDOUT)
        for edst in self.editorstacks:
            print("    ", edst, file=STDOUT)

    def unregister_editorstack(self, editorstack):
        if DEBUG_EDITOR:
            print("EditorWidget.unregister_editorstack:", editorstack, file=STDOUT)
        self.plugin.unregister_editorstack(editorstack)
        self.editorstacks.pop(self.editorstacks.index(editorstack))
        if DEBUG_EDITOR:
            self.__print_editorstacks()


class EditorMainWindow(QMainWindow):
    def __init__(self, plugin, menu_actions, toolbar_list, menu_list,
                 show_fullpath, fullpath_sorting, show_all_files,
                 show_comments):
        QMainWindow.__init__(self)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.window_size = None

        self.editorwidget = EditorWidget(self, plugin, menu_actions,
                                         show_fullpath, fullpath_sorting,
                                         show_all_files, show_comments)
        self.setCentralWidget(self.editorwidget)

        # Give focus to current editor to update/show all status bar widgets
        editorstack = self.editorwidget.editorsplitter.editorstack
        editor = editorstack.get_current_editor()
        if editor is not None:
            editor.setFocus()

        self.setWindowTitle("Spyder - %s" % plugin.windowTitle())
        self.setWindowIcon(plugin.windowIcon())

        if toolbar_list:
            self.toolbars = []
            for title, object_name, actions in toolbar_list:
                toolbar = self.addToolBar(title)
                toolbar.setObjectName(object_name)
                add_actions(toolbar, actions)
                self.toolbars.append(toolbar)
        if menu_list:
            quit_action = create_action(self, _("Close window"),
                                        icon="close_panel.png",
                                        tip=_("Close this window"),
                                        triggered=self.close)
            self.menus = []
            for index, (title, actions) in enumerate(menu_list):
                menu = self.menuBar().addMenu(title)
                if index == 0:
                    # File menu
                    add_actions(menu, actions+[None, quit_action])
                else:
                    add_actions(menu, actions)
                self.menus.append(menu)

    def get_toolbars(self):
        """Get the toolbars."""
        return self.toolbars

    def add_toolbars_to_menu(self, menu_title, actions):
        """Add toolbars to a menu."""
        # Six is the position of the view menu in menus list
        # that you can find in plugins/editor.py setup_other_windows. 
        view_menu = self.menus[6]
        if actions == self.toolbars and view_menu:
            toolbars = []
            for toolbar in self.toolbars:
                action = toolbar.toggleViewAction()
                toolbars.append(action)
            add_actions(view_menu, toolbars)

    def load_toolbars(self):
        """Loads the last visible toolbars from the .ini file."""
        toolbars_names = CONF.get('main', 'last_visible_toolbars', default=[])
        if toolbars_names:            
            dic = {}
            for toolbar in self.toolbars:
                dic[toolbar.objectName()] = toolbar
                toolbar.toggleViewAction().setChecked(False)
                toolbar.setVisible(False)
            for name in toolbars_names:
                if name in dic:
                    dic[name].toggleViewAction().setChecked(True)
                    dic[name].setVisible(True)

    def resizeEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.isFullScreen():
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)

    def closeEvent(self, event):
        """Reimplement Qt method"""
        QMainWindow.closeEvent(self, event)
        if is_pyqt46:
            self.destroyed.emit()
            for editorstack in self.editorwidget.editorstacks[:]:
                if DEBUG_EDITOR:
                    print("--> destroy_editorstack:", editorstack, file=STDOUT)
                editorstack.destroyed.emit()

    def get_layout_settings(self):
        """Return layout state"""
        splitsettings = self.editorwidget.editorsplitter.get_layout_settings()
        return dict(size=(self.window_size.width(), self.window_size.height()),
                    pos=(self.pos().x(), self.pos().y()),
                    is_maximized=self.isMaximized(),
                    is_fullscreen=self.isFullScreen(),
                    hexstate=qbytearray_to_str(self.saveState()),
                    splitsettings=splitsettings)

    def set_layout_settings(self, settings):
        """Restore layout state"""
        size = settings.get('size')
        if size is not None:
            self.resize( QSize(*size) )
            self.window_size = self.size()
        pos = settings.get('pos')
        if pos is not None:
            self.move( QPoint(*pos) )
        hexstate = settings.get('hexstate')
        if hexstate is not None:
            self.restoreState( QByteArray().fromHex(
                    str(hexstate).encode('utf-8')) )
        if settings.get('is_maximized'):
            self.setWindowState(Qt.WindowMaximized)
        if settings.get('is_fullscreen'):
            self.setWindowState(Qt.WindowFullScreen)
        splitsettings = settings.get('splitsettings')
        if splitsettings is not None:
            self.editorwidget.editorsplitter.set_layout_settings(splitsettings)


class EditorPluginExample(QSplitter):
    def __init__(self):
        QSplitter.__init__(self)

        menu_actions = []

        self.editorstacks = []
        self.editorwindows = []

        self.last_focus_editorstack = {} # fake

        self.find_widget = FindReplace(self, enable_replace=True)
        self.outlineexplorer = OutlineExplorerWidget(self, show_fullpath=False,
                                                     show_all_files=False)
        self.outlineexplorer.edit_goto.connect(self.go_to_file)
        self.editor_splitter = EditorSplitter(self, self, menu_actions,
                                              first=True)

        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        editor_layout.addWidget(self.editor_splitter)
        editor_layout.addWidget(self.find_widget)

        self.setContentsMargins(0, 0, 0, 0)
        self.addWidget(editor_widgets)
        self.addWidget(self.outlineexplorer)

        self.setStretchFactor(0, 5)
        self.setStretchFactor(1, 1)

        self.menu_actions = menu_actions
        self.toolbar_list = None
        self.menu_list = None
        self.setup_window([], [])

    def go_to_file(self, fname, lineno, text):
        editorstack = self.editorstacks[0]
        editorstack.set_current_filename(to_text_string(fname))
        editor = editorstack.get_current_editor()
        editor.go_to_line(lineno, word=text)

    def closeEvent(self, event):
        for win in self.editorwindows[:]:
            win.close()
        if DEBUG_EDITOR:
            print(len(self.editorwindows), ":", self.editorwindows, file=STDOUT)
            print(len(self.editorstacks), ":", self.editorstacks, file=STDOUT)

        event.accept()

    def load(self, fname):
        QApplication.processEvents()
        editorstack = self.editorstacks[0]
        editorstack.load(fname)
        editorstack.analyze_script()

    def register_editorstack(self, editorstack):
        if DEBUG_EDITOR:
            print("FakePlugin.register_editorstack:", editorstack, file=STDOUT)
        self.editorstacks.append(editorstack)
        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            editorstack.set_fullpath_sorting_enabled(True)
            editorstack.set_closable( len(self.editorstacks) > 1 )
            editorstack.set_outlineexplorer(self.outlineexplorer)
            editorstack.set_find_widget(self.find_widget)
            oe_btn = create_toolbutton(self)
            oe_btn.setDefaultAction(self.outlineexplorer.visibility_action)
            editorstack.add_corner_widgets_to_tabbar([5, oe_btn])

        action = QAction(self)
        editorstack.set_io_actions(action, action, action, action)
        font = QFont("Courier New")
        font.setPointSize(10)
        editorstack.set_default_font(font, color_scheme='Spyder')

        editorstack.sig_close_file.connect(self.close_file_in_all_editorstacks)
        editorstack.file_saved.connect(self.file_saved_in_editorstack)
        editorstack.file_renamed_in_data.connect(
                                      self.file_renamed_in_data_in_editorstack)
        editorstack.create_new_window.connect(self.create_new_window)
        editorstack.plugin_load.connect(self.load)

    def unregister_editorstack(self, editorstack):
        if DEBUG_EDITOR:
            print("FakePlugin.unregister_editorstack:", editorstack, file=STDOUT)
        self.editorstacks.pop(self.editorstacks.index(editorstack))

    def clone_editorstack(self, editorstack):
        editorstack.clone_from(self.editorstacks[0])

    def setup_window(self, toolbar_list, menu_list):
        self.toolbar_list = toolbar_list
        self.menu_list = menu_list

    def create_new_window(self):
        window = EditorMainWindow(self, self.menu_actions,
                                  self.toolbar_list, self.menu_list,
                                  show_fullpath=False, fullpath_sorting=True,
                                  show_all_files=False, show_comments=True)
        window.resize(self.size())
        window.show()
        self.register_editorwindow(window)
        window.destroyed.connect(lambda: self.unregister_editorwindow(window))

    def register_editorwindow(self, window):
        if DEBUG_EDITOR:
            print("register_editorwindowQObject*:", window, file=STDOUT)
        self.editorwindows.append(window)

    def unregister_editorwindow(self, window):
        if DEBUG_EDITOR:
            print("unregister_editorwindow:", window, file=STDOUT)
        self.editorwindows.pop(self.editorwindows.index(window))

    def get_focus_widget(self):
        pass

    @Slot(str, int)
    def close_file_in_all_editorstacks(self, editorstack_id_str, index):
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.blockSignals(True)
                editorstack.close_file(index, force=True)
                editorstack.blockSignals(False)

    # This method is never called in this plugin example. It's here only
    # to show how to use the file_saved signal (see above).
    @Slot(str, int, str)
    def file_saved_in_editorstack(self, editorstack_id_str, index, filename):
        """A file was saved in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.file_saved_in_other_editorstack(index, filename)

    # This method is never called in this plugin example. It's here only
    # to show how to use the file_saved signal (see above).
    @Slot(str, int, str)
    def file_renamed_in_data_in_editorstack(self, editorstack_id_str,
                                            index, filename):
        """A file was renamed in data in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.rename_in_data(index, filename)

    def register_widget_shortcuts(self, widget):
        """Fake!"""
        pass


def test():
    from spyder.utils.qthelpers import qapplication
    from spyder.config.base import get_module_path
    from spyder.utils.introspection.manager import IntrospectionManager

    cur_dir = osp.join(get_module_path('spyder'), 'widgets')
    app = qapplication(test_time=8)
    introspector = IntrospectionManager()

    test = EditorPluginExample()
    test.resize(900, 700)
    test.show()

    editorstack = test.editor_splitter.editorstack
    editorstack.set_introspector(introspector)
    introspector.set_editor_widget(editorstack)

    import time
    t0 = time.time()
    test.load(osp.join(cur_dir, "editor.py"))
    test.load(osp.join(cur_dir, "explorer.py"))
    test.load(osp.join(cur_dir, "variableexplorer", "collectionseditor.py"))
    test.load(osp.join(cur_dir, "sourcecode", "codeeditor.py"))
    print("Elapsed time: %.3f s" % (time.time()-t0))  # spyder: test-skip

    sys.exit(app.exec_())


if __name__ == "__main__":
    test()

# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Editor Widget"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import print_function

from spyderlib.qt import is_pyqt46
from spyderlib.qt.QtGui import (QVBoxLayout, QMessageBox, QMenu, QFont,
                                QAction, QApplication, QWidget, QHBoxLayout,
                                QLabel, QKeySequence, QMainWindow,
                                QSplitter, QListWidget, QListWidgetItem,
                                QDialog, QLineEdit)
from spyderlib.qt.QtCore import (SIGNAL, Qt, QFileInfo, QThread, QObject,
                                 QByteArray, QSize, QPoint, QTimer, Slot)
from spyderlib.qt.compat import getsavefilename

import os
import sys
import os.path as osp

# Local imports
from spyderlib.utils import encoding, sourcecode, codeanalysis
from spyderlib.utils import introspection
from spyderlib.baseconfig import _, DEBUG, STDOUT, STDERR
from spyderlib.config import EDIT_FILTERS, EDIT_EXT, get_filter, EDIT_FILETYPES
from spyderlib.guiconfig import create_shortcut, new_shortcut
from spyderlib.utils.qthelpers import (get_icon, create_action, add_actions,
                                       mimedata2url, get_filetype_icon,
                                       create_toolbutton)
from spyderlib.widgets.tabs import BaseTabs
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.editortools import OutlineExplorerWidget
from spyderlib.widgets.status import (ReadWriteStatus, EOLStatus,
                                      EncodingStatus, CursorPositionStatus)
from spyderlib.widgets.sourcecode import syntaxhighlighters, codeeditor
from spyderlib.widgets.sourcecode.base import TextEditBaseWidget  #analysis:ignore
from spyderlib.widgets.sourcecode.codeeditor import Printer  #analysis:ignore
from spyderlib.widgets.sourcecode.codeeditor import get_file_language
from spyderlib.py3compat import to_text_string, qbytearray_to_str, u


DEBUG_EDITOR = DEBUG >= 3


class FileListDialog(QDialog):
    def __init__(self, parent, tabs, fullpath_sorting):
        QDialog.__init__(self, parent)
        
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.indexes = None
        
        self.setWindowIcon(get_icon('filelist.png'))
        self.setWindowTitle(_("File list management"))
        
        self.setModal(True)
        
        flabel = QLabel(_("Filter:"))
        self.edit = QLineEdit(self)
        self.connect(self.edit, SIGNAL("returnPressed()"), self.edit_file)
        self.connect(self.edit, SIGNAL("textChanged(QString)"),
                     lambda text: self.synchronize(0))
        fhint = QLabel(_("(press <b>Enter</b> to edit file)"))
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(flabel)
        edit_layout.addWidget(self.edit)
        edit_layout.addWidget(fhint)
        
        self.listwidget = QListWidget(self)
        self.listwidget.setResizeMode(QListWidget.Adjust)
        self.connect(self.listwidget, SIGNAL("itemSelectionChanged()"),
                     self.item_selection_changed)
        self.connect(self.listwidget, SIGNAL("itemActivated(QListWidgetItem*)"),
                     self.edit_file)
        
        btn_layout = QHBoxLayout()
        edit_btn = create_toolbutton(self, icon=get_icon('edit.png'),
                     text=_("&Edit file"), autoraise=False,
                     triggered=self.edit_file, text_beside_icon=True)
        edit_btn.setMinimumHeight(28)
        btn_layout.addWidget(edit_btn)
        
        btn_layout.addStretch()
        btn_layout.addSpacing(150)
        btn_layout.addStretch()
        
        close_btn = create_toolbutton(self, text=_("&Close file"),
              icon=get_icon("fileclose.png"),
              autoraise=False, text_beside_icon=True,
              triggered=lambda: self.emit(SIGNAL("close_file(int)"),
                                  self.indexes[self.listwidget.currentRow()]))
        close_btn.setMinimumHeight(28)
        btn_layout.addWidget(close_btn)

        hint = QLabel(_("Hint: press <b>Alt</b> to show accelerators"))
        hint.setAlignment(Qt.AlignCenter)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(edit_layout)
        vlayout.addWidget(self.listwidget)
        vlayout.addLayout(btn_layout)
        vlayout.addWidget(hint)
        self.setLayout(vlayout)
        
        self.tabs = tabs
        self.fullpath_sorting = fullpath_sorting
        self.buttons = (edit_btn, close_btn)
        
    def edit_file(self):
        row = self.listwidget.currentRow()
        if self.listwidget.count() > 0 and row >= 0:
            self.emit(SIGNAL("edit_file(int)"), self.indexes[row])
            self.accept()
            
    def item_selection_changed(self):
        for btn in self.buttons:
            btn.setEnabled(self.listwidget.currentRow() >= 0)
        
    def synchronize(self, stack_index):
        count = self.tabs.count()
        if count == 0:
            self.accept()
            return
        self.listwidget.setTextElideMode(Qt.ElideMiddle
                                         if self.fullpath_sorting
                                         else Qt.ElideRight)
        current_row = self.listwidget.currentRow()
        if current_row >= 0:
            current_text = to_text_string(self.listwidget.currentItem().text())
        else:
            current_text = ""
        self.listwidget.clear()
        self.indexes = []
        new_current_index = stack_index
        filter_text = to_text_string(self.edit.text())
        lw_index = 0
        for index in range(count):
            text = to_text_string(self.tabs.tabText(index))
            if len(filter_text) == 0 or filter_text in text:
                if text == current_text:
                    new_current_index = lw_index
                lw_index += 1
                item = QListWidgetItem(self.tabs.tabIcon(index),
                                       text, self.listwidget)
                item.setSizeHint(QSize(0, 25))
                self.listwidget.addItem(item)
                self.indexes.append(index)
        if new_current_index < self.listwidget.count():
            self.listwidget.setCurrentRow(new_current_index)
        for btn in self.buttons:
            btn.setEnabled(lw_index > 0)


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
            self.connect(thread, SIGNAL('finished()'), self.update_queue)
            threadlist = self.started_threads.get(parent_id, [])
            self.started_threads[parent_id] = threadlist+[thread]
            if DEBUG_EDITOR:
                print("===>starting:", thread, file=STDOUT)
            thread.start()


class FileInfo(QObject):
    """File properties"""
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

        self.connect(self.editor, SIGNAL('textChanged()'),
                     self.text_changed)
        self.connect(self.editor, SIGNAL('breakpoints_changed()'),
                     self.breakpoints_changed)

        self.pyflakes_results = None
        self.pep8_results = None

    def text_changed(self):
        """Editor's text has changed"""
        self.default = False
        self.emit(SIGNAL('text_changed_at(QString,int)'),
                  self.filename, self.editor.get_position('cursor'))

    def get_source_code(self):
        """Return associated editor source code"""
        return to_text_string(self.editor.toPlainText())
    
    def run_code_analysis(self, run_pyflakes, run_pep8):
        """Run code analysis"""
        run_pyflakes = run_pyflakes and codeanalysis.is_pyflakes_installed()
        run_pep8 = run_pep8 and\
                   codeanalysis.get_checker_executable('pep8') is not None
        self.pyflakes_results = []
        self.pep8_results = []
        if self.editor.is_python():
            enc = self.encoding.replace('-guessed', '').replace('-bom', '')
            source_code = self.get_source_code().encode(enc)
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
        self.emit(SIGNAL('analysis_results_changed()'))
        
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
        self.emit(SIGNAL('todo_results_changed()'))
        
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
            self.emit(SIGNAL("save_breakpoints(QString,QString)"),
                      self.filename, repr(breakpoints))
        

class EditorStack(QWidget):
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
        self.filelist_dlg = None
#        self.filelist_btn = None
#        self.previous_btn = None
#        self.next_btn = None
        self.tabs = None

        self.stack_history = []
        
        self.setup_editorstack(parent, layout)

        self.find_widget = None

        self.data = []
        
        filelist_action = create_action(self, _("File list management"),
                                 icon=get_icon('filelist.png'),
                                 triggered=self.open_filelistdialog)
        copy_to_cb_action = create_action(self, _("Copy path to clipboard"),
                icon="editcopy.png",
                triggered=lambda:
                QApplication.clipboard().setText(self.get_current_filename()))
        self.menu_actions = actions+[None, filelist_action, copy_to_cb_action]
        self.outlineexplorer = None
        self.inspector = None
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
        self.tab_stop_width = 40
        self.inspector_enabled = False
        self.default_font = None
        self.wrap_enabled = False
        self.tabmode_enabled = False
        self.intelligent_backspace_enabled = True
        self.highlight_current_line_enabled = False
        self.highlight_current_cell_enabled = False        
        self.occurence_highlighting_enabled = True
        self.checkeolchars_enabled = True
        self.always_remove_trailing_spaces = False
        self.fullpath_sorting_enabled = None
        self.focus_to_editor = True
        self.set_fullpath_sorting_enabled(False)
        ccs = 'Spyder'
        if ccs not in syntaxhighlighters.COLOR_SCHEME_NAMES:
            ccs = syntaxhighlighters.COLOR_SCHEME_NAMES[0]
        self.color_scheme = ccs
        self.introspector = introspection.PluginManager(self)

        self.introspector.send_to_inspector.connect(self.send_to_inspector)
        self.introspector.edit_goto.connect(
             lambda fname, lineno, name:
             self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                              fname, lineno, name))

        self.__file_status_flag = False
        
        # Real-time code analysis
        self.analysis_timer = QTimer(self)
        self.analysis_timer.setSingleShot(True)
        self.analysis_timer.setInterval(2000)
        self.connect(self.analysis_timer, SIGNAL("timeout()"), 
                     self.analyze_script)
        
        # Accepting drops
        self.setAcceptDrops(True)
        
        # Local shortcuts
        self.shortcuts = self.create_shortcuts()

    def create_shortcuts(self):
        """Create local shortcuts"""
        # Configurable shortcuts
        inspect = create_shortcut(self.inspect_current_object, context='Editor',
                                  name='Inspect current object', parent=self)
        breakpoint = create_shortcut(self.set_or_clear_breakpoint,
                                     context='Editor', name='Breakpoint',
                                     parent=self)
        cbreakpoint = create_shortcut(self.set_or_edit_conditional_breakpoint,
                                      context='Editor',
                                      name='Conditional breakpoint',
                                      parent=self)
        gotoline = create_shortcut(self.go_to_line, context='Editor',
                                   name='Go to line', parent=self)
        filelist = create_shortcut(self.open_filelistdialog, context='Editor',
                                   name='File list management', parent=self)
        tab = create_shortcut(self.go_to_previous_file, context='Editor',
                              name='Go to previous file', parent=self)
        tabshift = create_shortcut(self.go_to_next_file, context='Editor',
                                   name='Go to next file', parent=self)
        # Fixed shortcuts
        new_shortcut(QKeySequence.ZoomIn, self,
                     lambda: self.emit(SIGNAL('zoom_in()')))
        new_shortcut("Ctrl+=", self, lambda: self.emit(SIGNAL('zoom_in()')))
        new_shortcut(QKeySequence.ZoomOut, self,
                     lambda: self.emit(SIGNAL('zoom_out()')))
        new_shortcut("Ctrl+0", self, lambda: self.emit(SIGNAL('zoom_reset()')))
        new_shortcut("Ctrl+W", self, self.close_file)
        new_shortcut("Ctrl+F4", self, self.close_file)
        # Return configurable ones
        return [inspect, breakpoint, cbreakpoint, gotoline, filelist, tab,
                tabshift]

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
        menu_btn = create_toolbutton(self, icon=get_icon("tooloptions.png"),
                                     tip=_("Options"))
        self.menu = QMenu(self)
        menu_btn.setMenu(self.menu)
        menu_btn.setPopupMode(menu_btn.InstantPopup)
        self.connect(self.menu, SIGNAL("aboutToShow()"), self.__setup_menu)

#        self.filelist_btn = create_toolbutton(self,
#                             icon=get_icon('filelist.png'),
#                             tip=_("File list management"),
#                             triggered=self.open_filelistdialog)
#        
#        self.previous_btn = create_toolbutton(self,
#                             icon=get_icon('previous.png'),
#                             tip=_("Previous file"),
#                             triggered=self.go_to_previous_file)
#        
#        self.next_btn = create_toolbutton(self,
#                             icon=get_icon('next.png'),
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

        if hasattr(self.tabs, 'setDocumentMode') \
           and not sys.platform == 'darwin':
            # Don't set document mode to true on OSX because it generates
            # a crash when the editor is detached from the main window
            # Fixes Issue 561
            self.tabs.setDocumentMode(True)
        self.connect(self.tabs, SIGNAL('currentChanged(int)'),
                     self.current_changed)

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
        self.disconnect(self.analysis_timer, SIGNAL("timeout()"),
                        self.analyze_script)
        QWidget.closeEvent(self, event)
        if is_pyqt46:
            self.emit(SIGNAL('destroyed()'))        
    
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
        
    def open_filelistdialog(self):
        """Open file list management dialog box"""
        self.filelist_dlg = dlg = FileListDialog(self, self.tabs,
                                                 self.fullpath_sorting_enabled)
        self.connect(dlg, SIGNAL("edit_file(int)"), self.set_stack_index)
        self.connect(dlg, SIGNAL("close_file(int)"), self.close_file)
        dlg.synchronize(self.get_stack_index())
        dlg.exec_()
        self.filelist_dlg = None
        
    def update_filelistdialog(self):
        """Synchronize file list dialog box with editor widget tabs"""
        if self.filelist_dlg is not None:
            self.filelist_dlg.synchronize(self.get_stack_index())
            
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
        """Inspect current object in Object Inspector"""
        if self.introspector:
            editor = self.get_current_editor()
            position = editor.get_position('cursor')
            self.inspector.switch_to_editor_source()
            self.introspector.show_object_info(position, auto=False)
        else:
            text = self.get_current_editor().get_current_object()
            if text:
                self.send_to_inspector(text, force=True)
        
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
        self.connect(self.outlineexplorer,
                     SIGNAL("outlineexplorer_is_visible()"),
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
        
    def set_inspector(self, inspector):
        self.inspector = inspector
        
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

    def set_tab_stop_width(self, tab_stop_width):
        # CONF.get(self.CONF_SECTION, 'tab_stop_width')
        self.tab_stop_width = tab_stop_width
        if self.data:
            for finfo in self.data:
                finfo.editor.setTabStopWidth(tab_stop_width)
                
    def set_inspector_enabled(self, state):
        self.inspector_enabled = state
        
    def set_default_font(self, font, color_scheme=None):
        # get_font(self.CONF_SECTION)
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
        
    def set_occurence_highlighting_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'occurence_highlighting')
        self.occurence_highlighting_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurence_highlighting(state)
                
    def set_occurence_highlighting_timeout(self, timeout):
        # CONF.get(self.CONF_SECTION, 'occurence_highlighting/timeout')
        self.occurence_highlighting_timeout = timeout
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurence_timeout(timeout)
                
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
            self.data.sort(key=self.__get_sorting_func())
            new_index = self.data.index(finfo)
            self.__repopulate_stack()
            self.set_stack_index(new_index)
        
    def set_always_remove_trailing_spaces(self, state):
        # CONF.get(self.CONF_SECTION, 'always_remove_trailing_spaces')
        self.always_remove_trailing_spaces = state
            
    def set_focus_to_editor(self, state):
        self.focus_to_editor = state
    
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
    
    def set_stack_index(self, index):
        self.tabs.setCurrentIndex(index)
            
    def set_tabbar_visible(self, state):
        self.tabs.tabBar().setVisible(state)
    
    def remove_from_data(self, index):
        self.tabs.blockSignals(True)
        self.tabs.removeTab(index)
        self.data.pop(index)
        self.tabs.blockSignals(False)
        self.update_actions()
        self.update_filelistdialog()
    
    def __modified_readonly_title(self, title, is_modified, is_readonly):
        if is_modified is not None and is_modified:
            title += "*"
        if is_readonly is not None and is_readonly:
            title = "(%s)" % title
        return title
    
    def get_tab_text(self, filename, is_modified=None, is_readonly=None):
        """Return tab title"""
        return self.__modified_readonly_title(osp.basename(filename),
                                              is_modified, is_readonly)
                
    def get_tab_tip(self, filename, is_modified=None, is_readonly=None):
        """Return tab menu title"""
        if self.fullpath_sorting_enabled:
            text = filename
        else:
            text = u("%s — %s")
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
        
    def __get_sorting_func(self):
        if self.fullpath_sorting_enabled:
            return lambda item: osp.join(osp.dirname(item.filename),
                                         '_'+osp.basename(item.filename))
        else:
            return lambda item: osp.basename(item.filename)
    
    def add_to_data(self, finfo, set_current):
        self.data.append(finfo)
        self.data.sort(key=self.__get_sorting_func())
        index = self.data.index(finfo)
        fname, editor = finfo.filename, finfo.editor
        self.tabs.insertTab(index, editor, get_filetype_icon(fname),
                            self.get_tab_text(fname))
        self.set_stack_title(index, False)
        if set_current:
            self.set_stack_index(index)
            self.current_changed(index)
        self.update_actions()
        self.update_filelistdialog()
        
    def __repopulate_stack(self):
        self.tabs.blockSignals(True)
        self.tabs.clear()
        for finfo in self.data:
            icon = get_filetype_icon(finfo.filename)
            if finfo.newly_created:
                is_modified = True
            else:
                is_modified = None
            tab_text = self.get_tab_text(finfo.filename, is_modified)
            tab_tip = self.get_tab_tip(finfo.filename)
            index = self.tabs.addTab(finfo.editor, icon, tab_text)
            self.tabs.setTabToolTip(index, tab_tip)
        self.tabs.blockSignals(False)
        self.update_filelistdialog()
        
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
        self.data.sort(key=self.__get_sorting_func())
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
        tab_text = self.get_tab_text(fname, is_modified, is_readonly)
        tab_tip = self.get_tab_tip(fname, is_modified, is_readonly)
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
                icon="newwindow.png", tip=_("Create a new editor window"),
                triggered=lambda: self.emit(SIGNAL("create_new_window()")))
        # Splitting
        self.versplit_action = create_action(self, _("Split vertically"),
                icon="versplit.png",
                tip=_("Split vertically this editor window"),
                triggered=lambda: self.emit(SIGNAL("split_vertically()")))
        self.horsplit_action = create_action(self, _("Split horizontally"),
                icon="horsplit.png",
                tip=_("Split horizontally this editor window"),
                triggered=lambda: self.emit(SIGNAL("split_horizontally()")))
        self.close_action = create_action(self, _("Close this panel"),
                icon="close_panel.png", triggered=self.close)
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
            self.emit(SIGNAL('close_file(QString,int)'), str(id(self)), index)
            
            if not self.data and self.is_closable:
                # editortabwidget is empty: removing it
                # (if it's not the first editortabwidget)
                self.close()
            self.emit(SIGNAL('opened_files_list_changed()'))
            self.emit(SIGNAL('update_code_analysis_actions()'))
            self._refresh_outlineexplorer()
            self.emit(SIGNAL('refresh_file_dependent_actions()'))
            self.emit(SIGNAL('update_plugin_title()'))
            editor = self.get_current_editor()
            if editor:
                editor.setFocus()
            
            if new_index is not None:
                if index < new_index:
                    new_index -= 1
                self.set_stack_index(new_index)
        if self.get_stack_count() == 0:
            self.emit(SIGNAL('sig_new_file()'))
            return False
        return is_ok

    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass
        

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
        if not finfo.editor.document().isModified() and not force:
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
            self.emit(SIGNAL('encoding_changed(QString)'), finfo.encoding)
            finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
            
            # We pass self object ID as a QString, because otherwise it would 
            # depend on the platform: long for 64bit, int for 32bit. Replacing 
            # by long all the time is not working on some 32bit platforms 
            # (see Issue 1094, Issue 1098)
            self.emit(SIGNAL('file_saved(QString,int,QString)'),
                      str(id(self)), index, finfo.filename)

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
                                 _("<b>Unable to save script '%s'</b>"
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
        selectedfilter = get_filter(EDIT_FILETYPES,
                                    osp.splitext(original_filename)[1])
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename, _selfilter = getsavefilename(self, _("Save Python script"),
                               original_filename, EDIT_FILTERS, selectedfilter)
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            return osp.normpath(filename)
    
    def save_as(self, index=None):
        """Save file as..."""
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

            new_index = self.rename_in_data(index, new_filename=filename)

            # We pass self object ID as a QString, because otherwise it would 
            # depend on the platform: long for 64bit, int for 32bit. Replacing 
            # by long all the time is not working on some 32bit platforms 
            # (see Issue 1094, Issue 1098)
            self.emit(SIGNAL('file_renamed_in_data(QString,int,QString)'),
                      str(id(self)), index, filename)

            ok = self.save(index=new_index, force=True)
            self.refresh(new_index)
            self.set_stack_index(new_index)
            return ok
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
            self.emit(SIGNAL('reset_statusbar()'))
        self.emit(SIGNAL('opened_files_list_changed()'))
        
        # Index history management
        id_list = [id(self.tabs.widget(_i))
                   for _i in range(self.tabs.count())]
        for _id in self.stack_history[:]:
            if _id not in id_list:
                self.stack_history.pop(self.stack_history.index(_id))
        current_id = id(self.tabs.widget(index))
        while current_id in self.stack_history:
            self.stack_history.pop(self.stack_history.index(current_id))
        self.stack_history.append(current_id)
        if DEBUG_EDITOR:
            print("current_changed:", index, self.data[index].editor, end=' ', file=STDOUT)
            print(self.data[index].editor.get_document_id(), file=STDOUT)
            
        self.emit(SIGNAL('update_plugin_title()'))
        if editor is not None:
            self.emit(SIGNAL('current_file_changed(QString,int)'),
                      self.data[index].filename, editor.get_position('cursor'))
        
    def _get_previous_file_index(self):
        if len(self.stack_history) > 1:
            last = len(self.stack_history)-1
            w_id = self.stack_history.pop(last)
            self.stack_history.insert(0, w_id)
            last_id = self.stack_history[last]
            for _i in range(self.tabs.count()):
                if id(self.tabs.widget(_i)) == last_id:
                    return _i
        
    def go_to_previous_file(self):
        """Ctrl+Tab"""
        prev_index = self._get_previous_file_index()
        if prev_index is not None:
            self.set_stack_index(prev_index)
        elif len(self.stack_history) == 0 and self.get_stack_count():
            self.stack_history = [id(self.tabs.currentWidget())]
    
    def go_to_next_file(self):
        """Ctrl+Shift+Tab"""
        if len(self.stack_history) > 1:
            last = len(self.stack_history)-1
            w_id = self.stack_history.pop(0)
            self.stack_history.append(w_id)
            last_id = self.stack_history[last]
            for _i in range(self.tabs.count()):
                if id(self.tabs.widget(_i)) == last_id:
                    self.set_stack_index(_i)
                    break
        elif len(self.stack_history) == 0 and self.get_stack_count():
            self.stack_history = [id(self.tabs.currentWidget())]
    
    def focus_changed(self):
        """Editor focus has changed"""
        fwidget = QApplication.focusWidget()
        for finfo in self.data:
            if fwidget is finfo.editor:
                self.refresh()
        self.emit(SIGNAL("editor_focus_changed()"))
        
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
        self.emit(SIGNAL('encoding_changed(QString)'), finfo.encoding)
        # Refresh cursor position status:
        line, index = finfo.editor.get_cursor_line_column()
        self.emit(SIGNAL('editor_cursor_position_changed(int,int)'),
                  line, index)
        
    def __refresh_readonly(self, index):
        finfo = self.data[index]
        read_only = not QFileInfo(finfo.filename).isWritable()
        if not osp.isfile(finfo.filename):
            # This is an 'untitledX.py' file (newly created)
            read_only = False
        finfo.editor.setReadOnly(read_only)
        self.emit(SIGNAL('readonly_changed(bool)'), read_only)
        
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
            self.emit(SIGNAL('update_code_analysis_actions()'))
            self.__refresh_statusbar(index)
            self.__refresh_readonly(index)
            self.__check_file_status(index)
            self.emit(SIGNAL('update_plugin_title()'))
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
        self.emit(SIGNAL('opened_files_list_changed()'))
        # --
        if index is None:
            index = self.get_stack_index()
        if index == -1:
            return
        finfo = self.data[index]
        if state is None:
            state = finfo.editor.document().isModified()
        self.set_stack_title(index, state)
        # Toggle save/save all actions state
        self.save_action.setEnabled(state)
        self.emit(SIGNAL('refresh_save_all_action()'))
        # Refreshing eol mode
        eol_chars = finfo.editor.get_line_separator()
        os_name = sourcecode.get_os_name_from_eol_chars(eol_chars)
        self.emit(SIGNAL('refresh_eol_chars(QString)'), os_name)
        

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
        self.connect(editor, SIGNAL("get_completions(bool)"),
                     introspector.get_completions)
        self.connect(editor, SIGNAL("show_object_info(int)"),
                     introspector.show_object_info)
        self.connect(editor, SIGNAL("go_to_definition(int)"),
                     introspector.go_to_definition)

        finfo = FileInfo(fname, enc, editor, new, self.threadmanager,
                         self.introspector)
        self.add_to_data(finfo, set_current)
        self.connect(finfo, SIGNAL(
                    "send_to_inspector(QString,QString,QString,QString,bool)"),
                    self.send_to_inspector)
        self.connect(finfo, SIGNAL('analysis_results_changed()'),
                     lambda: self.emit(SIGNAL('analysis_results_changed()')))
        self.connect(finfo, SIGNAL('todo_results_changed()'),
                     lambda: self.emit(SIGNAL('todo_results_changed()')))
        self.connect(finfo, SIGNAL("edit_goto(QString,int,QString)"),
                     lambda fname, lineno, name:
                     self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                               fname, lineno, name))
        self.connect(finfo, SIGNAL("save_breakpoints(QString,QString)"),
                     lambda s1, s2:
                     self.emit(SIGNAL("save_breakpoints(QString,QString)"),
                               s1, s2))
        self.connect(editor, SIGNAL("run_selection()"), self.run_selection)
        self.connect(editor, SIGNAL("run_cell()"), self.run_cell)
        self.connect(editor, SIGNAL('run_cell_and_advance()'),
                     self.run_cell_and_advance)
        editor.sig_new_file.connect(lambda s: self.parent().plugin.new(text=s))
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
                occurence_highlighting=self.occurence_highlighting_enabled,
                occurence_timeout=self.occurence_highlighting_timeout,
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
                tab_stop_width=self.tab_stop_width,
                cloned_from=cloned_from)
        if cloned_from is None:
            editor.set_text(txt)
            editor.document().setModified(False)
        self.connect(finfo, SIGNAL('text_changed_at(QString,int)'),
                     lambda fname, position:
                     self.emit(SIGNAL('text_changed_at(QString,int)'),
                               fname, position))
        self.connect(editor, SIGNAL('cursorPositionChanged(int,int)'),
                     self.editor_cursor_position_changed)
        self.connect(editor, SIGNAL('textChanged()'),
                     self.start_stop_analysis_timer)
        self.connect(editor, SIGNAL('modificationChanged(bool)'),
                     lambda state: self.modification_changed(state,
                                                    editor_id=id(editor)))
        self.connect(editor, SIGNAL("focus_in()"), self.focus_changed)
        self.connect(editor, SIGNAL('zoom_in()'),
                     lambda: self.emit(SIGNAL('zoom_in()')))
        self.connect(editor, SIGNAL('zoom_out()'),
                     lambda: self.emit(SIGNAL('zoom_out()')))
        self.connect(editor, SIGNAL('zoom_reset()'),
                     lambda: self.emit(SIGNAL('zoom_reset()')))
        if self.outlineexplorer is not None:
            # Removing editor reference from outline explorer settings:
            self.connect(editor, SIGNAL("destroyed()"),
                         lambda obj=editor:
                         self.outlineexplorer.remove_editor(obj))

        self.find_widget.set_editor(editor)
       
        self.emit(SIGNAL('refresh_file_dependent_actions()'))
        self.modification_changed(index=self.data.index(finfo))
        
        return finfo
    
    def editor_cursor_position_changed(self, line, index):
        """Cursor position of one of the editor in the stack has changed"""
        self.emit(SIGNAL('editor_cursor_position_changed(int,int)'),
                  line, index)
    
    def send_to_inspector(self, qstr1, qstr2=None, qstr3=None,
                          qstr4=None, force=False):
        """qstr1: obj_text, qstr2: argpspec, qstr3: note, qstr4: doc_text"""
        if not force and not self.inspector_enabled:
            return
        if self.inspector is not None \
           and (force or self.inspector.dockwidget.isVisible()):
            # ObjectInspector widget exists and is visible
            if qstr4 is None:
                self.inspector.set_object_text(qstr1, ignore_unknown=True,
                                               force_refresh=force)
            else:
                objtxt = to_text_string(qstr1)
                name = objtxt.split('.')[-1]
                argspec = to_text_string(qstr2)
                note = to_text_string(qstr3)
                docstring = to_text_string(qstr4)
                doc = {'obj_text': objtxt, 'name': name, 'argspec': argspec,
                       'note': note, 'docstring': docstring}
                self.inspector.set_editor_doc(doc, force_refresh=force)
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
        self.emit(SIGNAL('starting_long_process(QString)'),
                  _("Loading %s...") % filename)
        text, enc = encoding.read(filename)
        finfo = self.create_new_editor(filename, enc, text, set_current)
        index = self.data.index(finfo)
        self._refresh_outlineexplorer(index, update=True)
        self.emit(SIGNAL('ending_long_process(QString)'), "")
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
        """Run selected text or current line in console"""
        text = self.get_current_editor().get_selection_as_executable_code()
        if not text:
            line = self.get_current_editor().get_current_line()
            text = line.lstrip()
        self.emit(SIGNAL('exec_in_extconsole(QString,bool)'), text, 
                         self.focus_to_editor)

    def run_cell(self):
        """Run current cell"""
        text = self.get_current_editor().get_cell_as_executable_code()
        finfo = self.get_current_finfo()
        if finfo.editor.is_python() and text:
            self.emit(SIGNAL('exec_in_extconsole(QString,bool)'),
                      text, self.focus_to_editor)

    def run_cell_and_advance(self):
        """Run current cell and advance to the next one"""
        self.run_cell()
        if self.focus_to_editor:
            self.get_current_editor().go_to_next_cell()
        else:
            term = QApplication.focusWidget()
            self.get_current_editor().go_to_next_cell()
            term.setFocus()
            
    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        # The second check is necessary on Windows, where source.hasUrls()
        # can return True but source.urls() is []
        if source.hasUrls() and source.urls():
            if mimedata2url(source, extlist=EDIT_EXT):
                event.acceptProposedAction()
            else:
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
            supported_files = mimedata2url(source, extlist=EDIT_EXT)
            files = set(files or []) | set(supported_files or [])
            for fname in files:
                self.emit(SIGNAL('plugin_load(QString)'), fname)
        elif source.hasText():
            editor = self.get_current_editor()
            if editor is not None:
                editor.insert_text( source.text() )
        event.acceptProposedAction()


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
        self.connect(self.editorstack, SIGNAL("destroyed()"),
                     lambda: self.editorstack_closed())
        self.connect(self.editorstack, SIGNAL("split_vertically()"),
                     lambda: self.split(orientation=Qt.Vertical))
        self.connect(self.editorstack, SIGNAL("split_horizontally()"),
                     lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editorstack)

    def closeEvent(self, event):
        QSplitter.closeEvent(self, event)
        if is_pyqt46:
            self.emit(SIGNAL('destroyed()'))
                                
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
        self.connect(editorsplitter, SIGNAL("destroyed()"),
                     lambda: self.editorsplitter_closed())
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
                editor.go_to_line(clines[index])
            editorstack.set_current_filename(cfname)
        hexstate = settings.get('hexstate')
        if hexstate is not None:
            self.restoreState( QByteArray().fromHex(str(hexstate)) )
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
        self.plugin.register_widget_shortcuts("Editor", self.find_widget)
        self.find_widget.hide()
        self.outlineexplorer = OutlineExplorerWidget(self,
                                            show_fullpath=show_fullpath,
                                            fullpath_sorting=fullpath_sorting,
                                            show_all_files=show_all_files,
                                            show_comments=show_comments)
        self.connect(self.outlineexplorer,
                     SIGNAL("edit_goto(QString,int,QString)"),
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
        self.connect(editorstack,
                     SIGNAL('editor_cursor_position_changed(int,int)'),
                     self.cursorpos_status.cursor_position_changed)
        self.connect(editorstack, SIGNAL('refresh_eol_chars(QString)'),
                     self.eol_status.eol_changed)
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
            toolbars = []
            for title, actions in toolbar_list:
                toolbar = self.addToolBar(title)
                toolbar.setObjectName(str(id(toolbar)))
                add_actions(toolbar, actions)
                toolbars.append(toolbar)
        if menu_list:
            quit_action = create_action(self, _("Close window"),
                                        icon="close_panel.png",
                                        tip=_("Close this window"),
                                        triggered=self.close)
            menus = []
            for index, (title, actions) in enumerate(menu_list):
                menu = self.menuBar().addMenu(title)
                if index == 0:
                    # File menu
                    add_actions(menu, actions+[None, quit_action])
                else:
                    add_actions(menu, actions)
                menus.append(menu)
            
    def resizeEvent(self, event):
        """Reimplement Qt method"""
        if not self.isMaximized() and not self.isFullScreen():
            self.window_size = self.size()
        QMainWindow.resizeEvent(self, event)
                
    def closeEvent(self, event):
        """Reimplement Qt method"""
        QMainWindow.closeEvent(self, event)
        if is_pyqt46:
            self.emit(SIGNAL('destroyed()'))
            for editorstack in self.editorwidget.editorstacks[:]:
                if DEBUG_EDITOR:
                    print("--> destroy_editorstack:", editorstack, file=STDOUT)
                editorstack.emit(SIGNAL('destroyed()'))
                                
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
            self.restoreState( QByteArray().fromHex(str(hexstate)) )
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
        self.connect(self.outlineexplorer,
                     SIGNAL("edit_goto(QString,int,QString)"),
                     self.go_to_file)
        
        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        editor_layout.addWidget(EditorSplitter(self, self, menu_actions,
                                               first=True))
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

        self.connect(editorstack, SIGNAL('close_file(QString,int)'),
                     self.close_file_in_all_editorstacks)
        self.connect(editorstack, SIGNAL('file_saved(QString,int,QString)'),
                     self.file_saved_in_editorstack)
        self.connect(editorstack,
                     SIGNAL('file_renamed_in_data(QString,int,QString)'),
                     self.file_renamed_in_data_in_editorstack)

        self.connect(editorstack, SIGNAL("create_new_window()"),
                     self.create_new_window)
        self.connect(editorstack, SIGNAL('plugin_load(QString)'),
                     self.load)
                    
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
        self.connect(window, SIGNAL("destroyed()"),
                     lambda win=window: self.unregister_editorwindow(win))
        
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

    @Slot(int, int)
    def close_file_in_all_editorstacks(self, editorstack_id_str, index):
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.blockSignals(True)
                editorstack.close_file(index, force=True)
                editorstack.blockSignals(False)

    # This method is never called in this plugin example. It's here only 
    # to show how to use the file_saved signal (see above).
    @Slot(int, int)
    def file_saved_in_editorstack(self, editorstack_id_str, index, filename):
        """A file was saved in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.file_saved_in_other_editorstack(index, filename)

    # This method is never called in this plugin example. It's here only 
    # to show how to use the file_saved signal (see above).
    @Slot(int, int)
    def file_renamed_in_data_in_editorstack(self, editorstack_id_str,
                                            index, filename):
        """A file was renamed in data in editorstack, this notifies others"""
        for editorstack in self.editorstacks:
            if str(id(editorstack)) != editorstack_id_str:
                editorstack.rename_in_data(index, filename)

    def register_widget_shortcuts(self, context, widget):
        """Fake!"""
        pass
    
def test():
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    test = EditorPluginExample()
    test.resize(900, 700)
    test.show()
    import time
    t0 = time.time()
    test.load(__file__)
    test.load("explorer.py")
    test.load("dicteditor.py")
    test.load("sourcecode/codeeditor.py")
    test.load("../spyder.py")
    print("Elapsed time: %.3f s" % (time.time()-t0))
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    test()

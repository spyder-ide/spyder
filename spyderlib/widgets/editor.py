# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Editor Widget"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QMessageBox, QMenu, QFont,
                         QAction, QApplication, QWidget, QHBoxLayout, QSplitter,
                         QComboBox, QKeySequence, QShortcut, QSizePolicy,
                         QMainWindow, QLabel, QListWidget, QListWidgetItem,
                         QDialog, QLineEdit, QIntValidator, QDialogButtonBox,
                         QGridLayout)
from PyQt4.QtCore import (SIGNAL, Qt, QFileInfo, QThread, QObject, QByteArray,
                          PYQT_VERSION_STR, QSize, QPoint, SLOT, QTimer)

import os, sys, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout
DEBUG = False

# Local imports
from spyderlib.utils import encoding, sourcecode
from spyderlib.config import get_icon, get_font
from spyderlib.utils.qthelpers import (create_action, add_actions, mimedata2url,
                                       get_filetype_icon, translate,
                                       create_toolbutton)
from spyderlib.widgets.tabs import BaseTabs
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.editortools import check, OutlineExplorer
from spyderlib.widgets.codeeditor.codeeditor import CodeEditor, get_primary_at
from spyderlib.widgets.codeeditor import syntaxhighlighters
from spyderlib.widgets.codeeditor.codeeditor import Printer #@UnusedImport
from spyderlib.widgets.codeeditor.base import TextEditBaseWidget #@UnusedImport


class GoToLineDialog(QDialog):
    def __init__(self, editor):
        QDialog.__init__(self, editor)
        self.editor = editor
        
        self.setWindowTitle(translate("Editor", "Editor"))
        self.setModal(True)
        
        label = QLabel(translate("Editor", "Go to line:"))
        self.lineedit = QLineEdit()
        validator = QIntValidator(self.lineedit)
        validator.setRange(1, editor.get_line_count())
        self.lineedit.setValidator(validator)        
        cl_label = QLabel(translate("Editor", "Current line:"))
        cl_label_v = QLabel("<b>%d</b>" % editor.get_cursor_line_number())
        last_label = QLabel(translate("Editor", "Line count:"))
        last_label_v = QLabel("%d" % editor.get_line_count())
        
        glayout = QGridLayout()
        glayout.addWidget(label, 0, 0, Qt.AlignVCenter|Qt.AlignRight)
        glayout.addWidget(self.lineedit, 0, 1, Qt.AlignVCenter)
        glayout.addWidget(cl_label, 1, 0, Qt.AlignVCenter|Qt.AlignRight)
        glayout.addWidget(cl_label_v, 1, 1, Qt.AlignVCenter)
        glayout.addWidget(last_label, 2, 0, Qt.AlignVCenter|Qt.AlignRight)
        glayout.addWidget(last_label_v, 2, 1, Qt.AlignVCenter)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel,
                                Qt.Vertical, self)
        self.connect(bbox, SIGNAL("accepted()"), SLOT("accept()"))
        self.connect(bbox, SIGNAL("rejected()"), SLOT("reject()"))
        btnlayout = QVBoxLayout()
        btnlayout.addWidget(bbox)
        btnlayout.addStretch(1)

        ok_button = bbox.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(False)
        self.connect(self.lineedit, SIGNAL("textChanged(QString)"),
                     lambda text: ok_button.setEnabled(len(text) > 0))
        
        layout = QHBoxLayout()
        layout.addLayout(glayout)
        layout.addLayout(btnlayout)
        self.setLayout(layout)

        self.lineedit.setFocus()
        
    def get_line_number(self):
        return int(self.lineedit.text())
        

class FileListDialog(QDialog):
    def __init__(self, parent, combo, fullpath_sorting):
        QDialog.__init__(self, parent)
        
        self.indexes = None
        
        self.setWindowIcon(get_icon('filelist.png'))
        self.setWindowTitle(translate("Editor", "File list management"))
        
        self.setModal(True)
        
        flabel = QLabel(translate("Editor", "Filter:"))
        self.edit = QLineEdit(self)
        self.connect(self.edit, SIGNAL("returnPressed()"), self.edit_file)
        self.connect(self.edit, SIGNAL("textChanged(QString)"),
                     lambda text: self.synchronize(0))
        fhint = QLabel(translate("Editor", "(press <b>Enter</b> to edit file)"))
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(flabel)
        edit_layout.addWidget(self.edit)
        edit_layout.addWidget(fhint)
        
        self.listwidget = QListWidget(self)
        self.listwidget.setResizeMode(QListWidget.Adjust)
        self.connect(self.listwidget, SIGNAL("itemSelectionChanged()"),
                     self.item_selection_changed)
        
        btn_layout = QHBoxLayout()
        edit_btn = create_toolbutton(self, get_icon('edit.png'),
                     text=translate("Editor", "&Edit file"), autoraise=False,
                     triggered=self.edit_file, text_beside_icon=True)
        edit_btn.setMinimumHeight(28)
        btn_layout.addWidget(edit_btn)
        
        btn_layout.addStretch()
        btn_layout.addSpacing(150)
        btn_layout.addStretch()
        
        close_btn = create_toolbutton(self,
              text=translate("Editor", "&Close file"),
              icon=get_icon("fileclose.png"),
              autoraise=False, text_beside_icon=True,
              triggered=lambda: self.emit(SIGNAL("close_file(int)"),
                                  self.indexes[self.listwidget.currentRow()]))
        close_btn.setMinimumHeight(28)
        btn_layout.addWidget(close_btn)

        hint = QLabel(translate("Editor",
                             "Hint: press <b>Alt</b> to show accelerators"))
        hint.setAlignment(Qt.AlignCenter)
        
        vlayout = QVBoxLayout()
        vlayout.addLayout(edit_layout)
        vlayout.addWidget(self.listwidget)
        vlayout.addLayout(btn_layout)
        vlayout.addWidget(hint)
        self.setLayout(vlayout)
        
        self.combo = combo
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
        count = self.combo.count()
        if count == 0:
            self.accept()
            return
        self.listwidget.setTextElideMode(Qt.ElideMiddle if self.fullpath_sorting
                                         else Qt.ElideRight)
        current_row = self.listwidget.currentRow()
        if current_row >= 0:
            current_text = unicode(self.listwidget.currentItem().text())
        else:
            current_text = ""
        self.listwidget.clear()
        self.indexes = []
        new_current_index = stack_index
        filter_text = unicode(self.edit.text())
        lw_index = 0
        for index in range(count):
            text = unicode(self.combo.itemText(index))
            if len(filter_text) == 0 or filter_text in text:
                if text == current_text:
                    new_current_index = lw_index
                lw_index += 1
                item = QListWidgetItem(self.combo.itemIcon(index),
                                       text, self.listwidget)
                item.setSizeHint(QSize(0, 25))
                self.listwidget.addItem(item)
                self.indexes.append(index)
        if new_current_index < self.listwidget.count():
            self.listwidget.setCurrentRow(new_current_index)
        for btn in self.buttons:
            btn.setEnabled(lw_index > 0)
        

class CodeAnalysisThread(QThread):
    """Pyflakes code analysis thread"""
    def __init__(self, editor):
        QThread.__init__(self, editor)
        self.editor = editor
        self.filename = None
        self.analysis_results = []
        
    def set_filename(self, filename):
        self.filename = filename
        
    def run(self):
        source_code = unicode(self.editor.toPlainText()).encode('utf-8')
        self.analysis_results = check(source_code, filename=self.filename)
        
    def get_results(self):
        return self.analysis_results


class ToDoFinderThread(QThread):
    """TODO finder thread"""
    PATTERN = r"# ?TODO ?:[^#]*|# ?FIXME ?:[^#]*|# ?XXX ?:?[^#]*"
    def __init__(self, parent):
        QThread.__init__(self, parent)
        self.text = None
        self.todo_results = []
        
    def set_text(self, text):
        self.text = unicode(text)
        
    def run(self):
        todo_results = []
        for line, text in enumerate(self.text.splitlines()):
            for todo in re.findall(self.PATTERN, text):
                todo_results.append( (todo, line+1) )
        self.todo_results = todo_results
        
    def get_results(self):
        return self.todo_results


class FileInfo(QObject):
    """File properties"""
    def __init__(self, filename, encoding, editor, new):
        QObject.__init__(self)
        self.project = None
        self.filename = filename
        self.newly_created = new
        self.encoding = encoding
        self.editor = editor
        self.classes = (filename, None, None)
        self.analysis_results = []
        self.todo_results = []
        self.lastmodified = QFileInfo(filename).lastModified()
        
        self.connect(editor, SIGNAL('trigger_code_completion(bool)'),
                     self.trigger_code_completion)
        self.connect(editor, SIGNAL('trigger_calltip(int)'),
                     self.trigger_calltip)
        self.connect(editor, SIGNAL("go_to_definition(int)"),
                     self.go_to_definition)
        
        self.connect(editor, SIGNAL('textChanged()'),
                     self.text_changed)
            
        self.analysis_thread = CodeAnalysisThread(self.editor)
        self.connect(self.analysis_thread, SIGNAL('finished()'),
                     self.code_analysis_finished)
        
        self.todo_thread = ToDoFinderThread(self)
        self.connect(self.todo_thread, SIGNAL('finished()'),
                     self.todo_finished)
        
    def set_project(self, project):
        self.project = project
        
    def text_changed(self):
        self.emit(SIGNAL('text_changed_at(QString,int)'),
                  self.filename, self.editor.get_position('cursor'))
        
    def validate_project(self):
        if self.project is None:
            return []
        self.project.validate_rope_project()
        
    def trigger_code_completion(self, automatic):
        if self.project is None:
            return []
        source_code = unicode(self.editor.toPlainText())
        offset = self.editor.get_position('cursor')
        textlist = self.project.get_completion_list(source_code, offset,
                                                    self.filename)
        if textlist:
            text = self.editor.get_text('sol', 'cursor')
            completion_text = re.split(r"[^a-zA-Z0-9_]", text)[-1]
            self.editor.show_completion_list(textlist, completion_text,
                                             automatic)
        
    def trigger_calltip(self, position):
        if self.project is None:
            return
        source_code = unicode(self.editor.toPlainText())
        offset = position
        textlist = self.project.get_calltip_text(source_code, offset,
                                                 self.filename)
        text = ''
        if textlist:
            parpos = textlist[0].find('(')
            if parpos:
                text = textlist[0][:parpos]
        if not text:
            text = get_primary_at(source_code, offset)
        if text and not text.startswith('self.'):
            self.emit(SIGNAL("send_to_inspector(QString)"), text)
        if textlist:
            self.editor.show_calltip("rope", textlist)
                    
    def go_to_definition(self, position):
        if self.project is None:
            return
        source_code = unicode(self.editor.toPlainText())
        offset = position
        fname, lineno = self.project.get_definition_location(source_code,
                                                        offset, self.filename)
        if fname is not None and lineno is not None:
            self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                      fname, lineno, "")
    
    def run_code_analysis(self):
        if self.editor.is_python():
            self.analysis_thread.set_filename(self.filename)
            self.analysis_thread.start()
        
    def code_analysis_finished(self):
        """Code analysis thread has finished"""
        self.set_analysis_results( self.analysis_thread.get_results() )
        self.emit(SIGNAL('analysis_results_changed()'))
        
    def set_analysis_results(self, analysis_results):
        """Set analysis results and update warning markers in editor"""
        self.analysis_results = analysis_results
        self.editor.process_code_analysis(analysis_results)
        
    def cleanup_analysis_results(self):
        self.analysis_results = []
        self.editor.cleanup_code_analysis()
            
    def run_todo_finder(self):
        if self.editor.is_python():
            self.todo_thread.set_text(self.editor.toPlainText())
            self.todo_thread.start()
        
    def todo_finished(self):
        """Code analysis thread has finished"""
        self.set_todo_results( self.todo_thread.get_results() )
        self.emit(SIGNAL('todo_results_changed()'))
        
    def set_todo_results(self, todo_results):
        """Set TODO results and update markers in editor"""
        self.todo_results = todo_results
        self.editor.process_todo(todo_results)
        
    def cleanup_todo_results(self):
        self.todo_results = []


def get_file_language(filename, text=None):
    ext = osp.splitext(filename)[1]
    if ext.startswith('.'):
        ext = ext[1:] # file extension with leading dot
    language = ext
    if not ext:
        if text is None:
            text, _enc = encoding.read(filename)
        for line in text.splitlines():
            if not line.strip():
                continue
            if line.startswith('#!') and \
               line[2:].split() == ['/usr/bin/env', 'python']:
                    language = 'python'
            else:
                break
    return language
        
class EditorStack(QWidget):
    def __init__(self, parent, plugin, actions):
        QWidget.__init__(self, parent)
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.newwindow_action = None
        self.horsplit_action = None
        self.versplit_action = None
        self.close_action = None
        self.__get_split_actions()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.header_layout = None
        self.menu = None
        self.combo = None
        self.default_combo_font = None
        self.filelist_btn = None
        self.filelist_dlg = None
        self.previous_btn = None
        self.next_btn = None
        self.tabs = None
        self.close_btn = None

        self.stack_history = []
        
        self.setup_editorstack(parent, layout, actions)

        self.find_widget = None

        self.data = []
        
        self.menu_actions = actions
        self.outlineexplorer = None
        self.projectexplorer = None
        self.inspector = None
        self.unregister_callback = None
        self.is_closable = False
        self.new_action = None
        self.open_action = None
        self.save_action = None
        self.revert_action = None
        self.tempfile_path = None
        self.title = translate("Editor", "Editor")
        self.filetype_filters = None
        self.valid_types = None
        self.codeanalysis_enabled = True
        self.todolist_enabled = True
        self.realtime_analysis_enabled = False
        self.is_analysis_done = False
        self.linenumbers_enabled = True
        self.outlineexplorer_enabled = True
        self.codecompletion_auto_enabled = False
        self.codecompletion_case_enabled = False
        self.codecompletion_single_enabled = False
        self.codecompletion_enter_enabled = False
        self.calltips_enabled = False
        self.go_to_definition_enabled = False
        self.close_parentheses_enabled = True
        self.auto_unindent_enabled = True
        self.inspector_enabled = False
        self.default_font = None
        self.wrap_enabled = False
        self.tabmode_enabled = False
        self.highlight_current_line_enabled = False
        self.occurence_highlighting_enabled = True
        self.checkeolchars_enabled = True
        self.fullpath_sorting_enabled = None
        self.set_fullpath_sorting_enabled(False)
        ccs = 'Spyder'
        if ccs not in syntaxhighlighters.COLOR_SCHEME_NAMES:
            ccs = syntaxhighlighters.COLOR_SCHEME_NAMES[0]
        self.color_scheme = ccs
        
        self.cursor_position_changed_callback = lambda line, index: \
                self.emit(SIGNAL('cursorPositionChanged(int,int)'), line, index)
        self.focus_changed_callback = lambda: \
                                      plugin.emit(SIGNAL("focus_changed()"))
        
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
        self.inspectsc = QShortcut(QKeySequence("Ctrl+I"), parent,
                                   self.inspect_current_object)
        self.inspectsc.setContext(Qt.WidgetWithChildrenShortcut)
        self.breakpointsc = QShortcut(QKeySequence("F12"), parent,
                                      self.set_or_clear_breakpoint)
        self.breakpointsc.setContext(Qt.WidgetWithChildrenShortcut)
        self.cbreakpointsc = QShortcut(QKeySequence("Shift+F12"), parent,
                                       self.set_or_edit_conditional_breakpoint)
        self.cbreakpointsc.setContext(Qt.WidgetWithChildrenShortcut)
        self.gotolinesc = QShortcut(QKeySequence("Ctrl+L"), parent,
                                    self.go_to_line)
        self.gotolinesc.setContext(Qt.WidgetWithChildrenShortcut)
        self.filelistsc = QShortcut(QKeySequence("Ctrl+E"), parent,
                                    self.open_filelistdialog)
        self.filelistsc.setContext(Qt.WidgetWithChildrenShortcut)
        self.tabsc = QShortcut(QKeySequence("Ctrl+Tab"), parent,
                               self.go_to_previous_file)
        self.tabsc.setContext(Qt.WidgetWithChildrenShortcut)
        self.closesc = QShortcut(QKeySequence("Ctrl+F4"), parent,
                                 self.close_file)
        self.closesc.setContext(Qt.WidgetWithChildrenShortcut)
        self.tabshiftsc = QShortcut(QKeySequence("Ctrl+Shift+Tab"), parent,
                                    self.go_to_next_file)
        self.tabshiftsc.setContext(Qt.WidgetWithChildrenShortcut)
        
    def get_shortcut_data(self):
        """
        Returns shortcut data, a list of tuples (shortcut, text, default)
        shortcut (QShortcut or QAction instance)
        text (string): action/shortcut description
        default (string): default key sequence
        """
        return [
                (self.inspectsc, "Inspect current object", "Ctrl+I"),
                (self.breakpointsc, "Breakpoint", "F12"),
                (self.cbreakpointsc, "Conditional breakpoint", "Shift+F12"),
                (self.gotolinesc, "Go to line", "Ctrl+L"),
                (self.filelistsc, "File list management", "Ctrl+E"),
                ]
        
    def setup_editorstack(self, parent, layout, actions):
        """Setup editorstack's layout"""
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Buttons to the left of file combo box
        menu_btn = create_toolbutton(self, icon=get_icon("tooloptions.png"),
                                     tip=translate("Editor", "Options"))
        self.menu = QMenu(self)
        menu_btn.setMenu(self.menu)
        menu_btn.setPopupMode(menu_btn.InstantPopup)
        self.connect(self.menu, SIGNAL("aboutToShow()"), self.__setup_menu)
        self.add_widget_to_header(menu_btn)

#        newwin_btn = create_toolbutton(self, text_beside_icon=False)
#        newwin_btn.setDefaultAction(self.newwindow_action)
#        self.add_widget_to_header(newwin_btn)
        
#        versplit_btn = create_toolbutton(self, text_beside_icon=False)
#        versplit_btn.setDefaultAction(self.versplit_action)
#        self.add_widget_to_header(versplit_btn)
        
#        horsplit_btn = create_toolbutton(self, text_beside_icon=False)
#        horsplit_btn.setDefaultAction(self.horsplit_action)
#        self.add_widget_to_header(horsplit_btn)

        self.filelist_btn = create_toolbutton(self, get_icon('filelist.png'),
                     tip=translate("Editor", "File list management"),
                     triggered=self.open_filelistdialog)
        self.add_widget_to_header(self.filelist_btn, space_before=True)
        
        self.previous_btn = create_toolbutton(self, get_icon('previous.png'),
                         tip=translate("Editor", "Previous file"),
                         triggered=self.go_to_previous_file)
        self.add_widget_to_header(self.previous_btn, space_before=True)
        
        self.next_btn = create_toolbutton(self, get_icon('next.png'),
                         tip=translate("Editor", "Next file"),
                         triggered=self.go_to_next_file)
        self.add_widget_to_header(self.next_btn)
                
        # File combo box
        self.combo = QComboBox(self)
        self.default_combo_font = self.combo.font()
        self.combo.setMaxVisibleItems(20)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.combo.addAction(create_action(self,
                translate("Editor", "Copy path to clipboard"),
                icon="editcopy.png",
                triggered=lambda:
                QApplication.clipboard().setText(self.get_current_filename())))
        self.connect(self.combo, SIGNAL('currentIndexChanged(int)'),
                     self.current_changed)
        self.add_widget_to_header(self.combo)

        # Buttons to the right of file combo box
        self.close_btn = create_toolbutton(self, triggered=self.close_file,
                                       icon=get_icon("fileclose.png"),
                                       tip=translate("Editor", "Close file"))
        self.add_widget_to_header(self.close_btn)
        layout.addLayout(self.header_layout)
        
        # Optional tabs
        self.tabs = BaseTabs(self, menu=self.menu)
        self.tabs.set_close_function(self.close_file)
        if hasattr(self.tabs, 'setDocumentMode'):
            self.tabs.setDocumentMode(True)
        self.connect(self.combo, SIGNAL('currentIndexChanged(int)'),
                     self.tabs.setCurrentIndex)
        self.connect(self.tabs, SIGNAL('currentChanged(int)'),
                     self.combo.setCurrentIndex)
        layout.addWidget(self.tabs)
        
    def add_widget_to_header(self, widget, space_before=False):
        if space_before:
            self.header_layout.addSpacing(7)
        self.header_layout.addWidget(widget)
        
    def closeEvent(self, event):
        QWidget.closeEvent(self, event)
        if PYQT_VERSION_STR.startswith('4.6'):
            self.emit(SIGNAL('destroyed()'))        
            
    def clone_from(self, other):
        """Clone EditorStack from other instance"""
        for other_finfo in other.data:
            fname = other_finfo.filename
            enc = other_finfo.encoding
            finfo = self.create_new_editor(fname, enc, "", set_current=True,
                                           cloned_from=other_finfo.editor)
            finfo.set_analysis_results(other_finfo.analysis_results)
            finfo.set_todo_results(other_finfo.todo_results)
        self.set_stack_index(other.get_stack_index())
        
    def open_filelistdialog(self):
        """Open file list management dialog box"""
        self.filelist_dlg = dlg = FileListDialog(self, self.combo,
                                                 self.fullpath_sorting_enabled)
        self.connect(dlg, SIGNAL("edit_file(int)"), self.set_stack_index)
        self.connect(dlg, SIGNAL("close_file(int)"), self.close_file)
        dlg.synchronize(self.get_stack_index())
        dlg.exec_()
        self.filelist_dlg = None
        
    def update_filelistdialog(self):
        """Synchronize file list dialog box with file selection combo box"""
        if self.filelist_dlg is not None:
            self.filelist_dlg.synchronize(self.get_stack_index())
            
    def go_to_line(self):
        """Go to line dialog"""
        if self.data:
            editor = self.get_current_editor()
            dlg = GoToLineDialog(editor)
            if dlg.exec_():
                editor.go_to_line(dlg.get_line_number())
                
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
        text = self.get_current_editor().get_current_object()
        if text:
            self.send_to_inspector(text)
        
        
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
        self.outlineexplorer_enabled = True
        self.connect(self.outlineexplorer,
                     SIGNAL("outlineexplorer_is_visible()"),
                     self._refresh_outlineexplorer)
        
    def set_projectexplorer(self, projectexplorer):
        self.projectexplorer = projectexplorer
        for finfo in self.data:
            project = self.projectexplorer.get_source_project(finfo.filename)
            finfo.set_project(project)
        
    def set_inspector(self, inspector):
        self.inspector = inspector
        
    def set_tempfile_path(self, path):
        self.tempfile_path = path
        
    def set_title(self, text):
        self.title = text
        
    def set_filetype_filters(self, filetype_filters):
        self.filetype_filters = filetype_filters
        
    def set_valid_types(self, valid_types):
        self.valid_types = valid_types
        
    def __update_editor_margins(self, editor):
        editor.setup_margins(linenumbers=self.linenumbers_enabled,
                             code_analysis=self.codeanalysis_enabled,
                             todo_list=self.todolist_enabled)
        
    def set_codeanalysis_enabled(self, state, current_finfo=None):
        # CONF.get(self.CONF_SECTION, 'code_analysis')
        self.codeanalysis_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                finfo.cleanup_analysis_results()
                if state and current_finfo is not None:
                    if current_finfo is not finfo:
                        finfo.run_code_analysis()                    
    
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
                
    def set_codecompletion_single_enabled(self, state):
        self.codecompletion_single_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_codecompletion_single(state)
                    
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
                
    def set_auto_unindent_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'auto_unindent')
        self.auto_unindent_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_auto_unindent_enabled(state)
                
    def set_inspector_enabled(self, state):
        self.inspector_enabled = state
        
    def set_outlineexplorer_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'outline_explorer')
        self.outlineexplorer_enabled = state
        
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
        # CONF.get(self.CONF_SECTION, 'tab_always_indent'))
        self.tabmode_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_tab_mode(state)
        
    def set_occurence_highlighting_enabled(self, state):
        # CONF.get(self.CONF_SECTION, 'occurence_highlighting'))
        self.occurence_highlighting_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurence_highlighting(state)
                
    def set_highlight_current_line_enabled(self, state):
        self.highlight_current_line_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_highlight_current_line(state)
        
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
        for widget in (self.tabs, self.combo):
            widget.setCurrentIndex(index)
            
    def set_tabbar_visible(self, state):
        self.tabs.tabBar().setVisible(state)
    
    def remove_from_data(self, index):
        self.tabs.removeTab(index)
        self.data.pop(index)
        self.combo.removeItem(index)
        self.update_actions()
        self.update_filelistdialog()
    
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
        self.combo.blockSignals(True)
        self.tabs.insertTab(index, editor, get_filetype_icon(fname),
                            self.get_tab_title(fname))
        self.combo.insertItem(index, get_filetype_icon(fname),
                              self.get_combo_title(fname))
        if set_current:
            self.set_stack_index(index)
        self.combo.blockSignals(False)
        if set_current:
            self.current_changed(index)
        self.update_actions()
        self.update_filelistdialog()
        
    def __repopulate_stack(self):
        for widget in (self.combo, self.tabs):
            widget.blockSignals(True)
            widget.clear()
        for finfo in self.data:
            icon = get_filetype_icon(finfo.filename)
            self.tabs.addTab(finfo.editor, icon,
                             self.get_tab_title(finfo.filename))
            self.combo.addItem(icon, self.get_combo_title(finfo.filename))
        for widget in (self.combo, self.tabs):
            widget.blockSignals(False)
        self.update_filelistdialog()
        
    def rename_in_data(self, index, new_filename):
        finfo = self.data[index]
        if osp.splitext(finfo.filename)[1] != osp.splitext(new_filename)[1]:
            # File type has changed!
            language = get_file_language(new_filename)
            finfo.editor.set_language(language)
        set_new_index = index == self.get_stack_index()
        finfo.filename = new_filename
        self.data.sort(key=self.__get_sorting_func())
        new_index = self.data.index(finfo)
        self.__repopulate_stack()
        if set_new_index:
            self.set_stack_index(new_index)
        if self.outlineexplorer is not None:
            self.outlineexplorer.file_renamed(finfo.editor, finfo.filename)
        return new_index
        
    def set_stack_title(self, index, combo_title, tab_title):
        self.combo.setItemText(index, combo_title)
        self.tabs.setTabText(index, tab_title)
        
        
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
        self.newwindow_action = create_action(self,
                    translate("Editor", "New window"),
                    icon="newwindow.png",
                    tip=translate("Editor", "Create a new editor window"),
                    triggered=lambda: self.emit(SIGNAL("create_new_window()")))
        # Splitting
        self.versplit_action = create_action(self,
                    translate("Editor", "Split vertically"),
                    icon="versplit.png",
                    tip=translate("Editor",
                                  "Split vertically this editor window"),
                    triggered=lambda: self.emit(SIGNAL("split_vertically()")))
        self.horsplit_action = create_action(self,
                    translate("Editor", "Split horizontally"),
                    icon="horsplit.png",
                    tip=translate("Editor",
                                  "Split horizontally this editor window"),
                    triggered=lambda: self.emit(SIGNAL("split_horizontally()")))
        self.close_action = create_action(self,
                    translate("Editor", "Close this panel"),
                    icon="close_panel.png",
                    triggered=self.close)
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
    def close_file(self, index=None):
        """
        Close file (index=None -> close current file)
        Keep current file index unchanged (if current file that is being closed)
        """
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
        is_ok = self.save_if_changed(cancelable=True, index=index)
        if is_ok:
            finfo = self.data[index]
            # Removing editor reference from outline explorer settings:
            if self.outlineexplorer is not None:
                self.outlineexplorer.remove_editor(finfo.editor)
            # Saving breakpoints
            breakpoints = finfo.editor.get_breakpoints()
            self.emit(SIGNAL("save_breakpoints(QString,QString)"),
                      finfo.filename, repr(breakpoints))
            
            self.remove_from_data(index)
            self.emit(SIGNAL('close_file(int)'), index)
            if not self.data and self.is_closable:
                # editortabwidget is empty: removing it
                # (if it's not the first editortabwidget)
                self.close()
            self.emit(SIGNAL('opened_files_list_changed()'))
            self.emit(SIGNAL('update_code_analysis_actions()'))
            self._refresh_outlineexplorer()
            self.emit(SIGNAL('refresh_file_dependent_actions()'))
            
            if new_index is not None:
                if index < new_index:
                    new_index -= 1
                self.set_stack_index(new_index)
        return is_ok
    
    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass
        

    #------ Save
    def save_if_changed(self, cancelable=False, index=None):
        """Ask user to save file if modified"""
        if index is None:
            indexes = range(self.get_stack_count())
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
                if not self.save(refresh_explorer=False):
                    return False
            elif finfo.editor.document().isModified():
                answer = QMessageBox.question(self, self.title,
                            translate("Editor",
                                      "<b>%1</b> has been modified."
                                      "<br>Do you want to save changes?").arg(
                            osp.basename(finfo.filename)), buttons)
                if answer == QMessageBox.Yes:
                    if not self.save(refresh_explorer=False):
                        return False
                elif answer == QMessageBox.YesAll:
                    if not self.save(refresh_explorer=False):
                        return False
                    yes_all = True
                elif answer == QMessageBox.NoAll:
                    return True
                elif answer == QMessageBox.Cancel:
                    return False
        return True
    
    def save(self, index=None, force=False, refresh_explorer=True):
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
        txt = unicode(finfo.editor.get_text_with_eol())
        try:
            finfo.encoding = encoding.write(txt, finfo.filename, finfo.encoding)
            finfo.newly_created = False
            self.emit(SIGNAL('encoding_changed(QString)'), finfo.encoding)
            finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
            self.emit(SIGNAL('file_saved(int)'), index)
            finfo.editor.document().setModified(False)
            self.modification_changed(index=index)
            self.analyze_script(index)
            finfo.validate_project()
            
            #XXX CodeEditor-only: re-scan the whole text to rebuild outline explorer 
            #    data from scratch (could be optimized because rehighlighting
            #    text means searching for all syntax coloring patterns instead 
            #    of only searching for class/def patterns which would be 
            #    sufficient for outline explorer data.
            finfo.editor.rehighlight()
            
            self._refresh_outlineexplorer(index)
            if refresh_explorer:
                # Refresh the explorer widget if it exists:
                self.emit(SIGNAL("refresh_explorer(QString)"),
                          osp.dirname(finfo.filename))
            return True
        except EnvironmentError, error:
            QMessageBox.critical(self, translate("Editor", "Save"),
                            translate("Editor",
                                      "<b>Unable to save script '%1'</b>"
                                      "<br><br>Error message:<br>%2").arg(
                            osp.basename(finfo.filename)).arg(str(error)))
            return False
        
    def file_saved_in_other_editorstack(self, index):
        """
        File was just saved in another editorstack, let's synchronize!
        This avoid file to be automatically reloaded
        """
        finfo = self.data[index]
        finfo.newly_created = False
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
    
    def select_savename(self, original_filename):
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getSaveFileName(self,
                                   translate("Editor", "Save Python script"),
                                   original_filename, self.filetype_filters)
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            return osp.normpath(unicode(filename))
    
    def save_as(self, index=None):
        """Save file as..."""
        if index is None:
            # Save the currently edited file
            index = self.get_stack_index()
        finfo = self.data[index]
        filename = self.select_savename(finfo.filename)
        if filename:
            ao_index = self.has_filename(filename)
            if ao_index:
                if not self.close_file(ao_index):
                    return
                if ao_index < index:
                    index -= 1
            new_index = self.rename_in_data(index, new_filename=filename)
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
                self.save(index, refresh_explorer=False)
        for folder in folders:
            self.emit(SIGNAL("refresh_explorer(QString)"), folder)
    
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
            if self.codeanalysis_enabled:
                finfo.run_code_analysis()
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
        count = self.get_stack_count()
        if self.close_btn is not None:
            self.close_btn.setEnabled(count > 0)
        for btn in (self.filelist_btn, self.previous_btn, self.next_btn):
            btn.setEnabled(count > 1)
        
        editor = self.get_current_editor()
        if index != -1:
            editor.setFocus()
            if DEBUG:
                print >>STDOUT, "setfocusto:", editor
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
        if DEBUG:
            print >>STDOUT, "current_changed:", index, self.data[index].editor,
            print >>STDOUT, self.data[index].editor.get_document_id()
            
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
        
    def _refresh_outlineexplorer(self, index=None, update=True):
        """Refresh outline explorer panel"""
        if index is None:
            index = self.get_stack_index()
        enable = False
        oe = self.outlineexplorer
        if self.data:
            finfo = self.data[index]
            # oe_visible: if outline explorer is not visible, maybe the whole
            # GUI is not visible (Spyder is starting up) -> in this case,
            # it is necessary to update the outline explorer
            oe_visible = oe.isVisible() or not self.isVisible()
            if self.outlineexplorer_enabled and finfo.editor.is_python() \
               and oe_visible:
                enable = True
                oe.setEnabled(True)
                oe.set_current_editor(finfo.editor, finfo.filename,
                                      update=update)
        if not enable:
            oe.setEnabled(False)
            
    def __refresh_statusbar(self, index):
        """Refreshing statusbar widgets"""
        finfo = self.data[index]
        self.emit(SIGNAL('encoding_changed(QString)'), finfo.encoding)
        # Refresh cursor position status:
        line, index = finfo.editor.get_cursor_line_column()
        self.emit(SIGNAL('cursorPositionChanged(int,int)'), line, index)
        
    def __refresh_readonly(self, index):
        finfo = self.data[index]
        read_only = not QFileInfo(finfo.filename).isWritable()
        if not osp.isfile(finfo.filename):
            # This is an 'untitledX.py' file (newly created)
            read_only = False
        finfo.editor.setReadOnly(read_only)
        self.emit(SIGNAL('readonly_changed(bool)'), read_only)
        
    def __check_file_status(self, index):
        if self.__file_status_flag:
            # Avoid infinite loop: when the QMessageBox.question pops, it
            # gets focus and then give it back to the CodeEditor instance,
            # triggering a refresh cycle which calls this method
            return
        
        finfo = self.data[index]
        if finfo.newly_created:
            return
        
        self.__file_status_flag = True
        name = osp.basename(finfo.filename)
        
        # First, testing if file still exists (removed, moved or offline):
        if not osp.isfile(finfo.filename):
            answer = QMessageBox.warning(self, self.title,
                            translate("Editor",
                                      "<b>%1</b> is unavailable "
                                      "(this file may have been removed, moved "
                                      "or renamed outside Spyder)."
                                      "<br>Do you want to close it?").arg(name),
                            QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.Yes:
                self.close_file(index)
        else:
            # Else, testing if it has been modified elsewhere:
            lastm = QFileInfo(finfo.filename).lastModified()
            if lastm.toString().compare(finfo.lastmodified.toString()):
                if finfo.editor.document().isModified():
                    answer = QMessageBox.question(self,
                        self.title,
                        translate("Editor",
                                  "<b>%1</b> has been modified outside Spyder."
                                  "<br>Do you want to reload it and loose all "
                                  "your changes?").arg(name),
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
        else:
            editor = None
        # Update the modification-state-dependent parameters
        self.modification_changed()
        # Update FindReplace binding
        self.find_widget.set_editor(editor, refresh=False)
                
    def __modified_readonly_title(self, title, is_modified, is_readonly):
        if is_modified is not None and is_modified:
            title += "*"
        if is_readonly is not None and is_readonly:
            title = "(%s)" % title
        return title
    
    def get_tab_title(self, filename, is_modified=None, is_readonly=None):
        """Return tab title"""
        return self.__modified_readonly_title(osp.basename(filename),
                                              is_modified, is_readonly)
                
    def get_combo_title(self, filename, is_modified=None, is_readonly=None):
        """Return combo box title"""
        if self.fullpath_sorting_enabled:
            text = filename
        else:
            text = u"%s — %s"
        text = self.__modified_readonly_title(text,
                                              is_modified, is_readonly)
        if filename == encoding.to_unicode(self.tempfile_path):
            temp_file_str = unicode(translate("Editor", "Temporary file"))
            if self.fullpath_sorting_enabled:
                return "%s (%s)" % (text, temp_file_str)
            else:
                return text % (temp_file_str, self.tempfile_path)
        else:
            if self.fullpath_sorting_enabled:
                return text
            else:
                return text % (osp.basename(filename), osp.dirname(filename))
        
    def get_titles(self, is_modified, finfo):
        """Return combo box and tab titles"""
        fname = finfo.filename
        is_readonly = finfo.editor.isReadOnly()
        combo_title = self.get_combo_title(fname, is_modified, is_readonly)
        tab_title = self.get_tab_title(fname, is_modified, is_readonly)
        return combo_title, tab_title
    
    def modification_changed(self, state=None, index=None):
        """
        Current editor's modification state has changed
        --> change tab title depending on new modification state
        --> enable/disable save/save all actions
        """
        sender = self.sender()
        if isinstance(sender, CodeEditor):
            for index, finfo in enumerate(self.data):
                if finfo.editor is sender:
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
        combo_title, tab_title = self.get_titles(state, finfo)
        self.set_stack_title(index, combo_title, tab_title)
        # Toggle save/save all actions state
        self.save_action.setEnabled(state)
        self.revert_action.setEnabled(state)
        self.emit(SIGNAL('refresh_save_all_action()'))
        # Refreshing eol mode
        eol_chars = finfo.editor.get_line_separator()
        os_name = sourcecode.get_os_name_from_eol_chars(eol_chars)
        self.emit(SIGNAL('refresh_eol_mode(QString)'), os_name)
        

    #------ Load, reload
    def reload(self, index):
        finfo = self.data[index]
        txt, finfo.encoding = encoding.read(finfo.filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
        position = finfo.editor.get_position('cursor')
        finfo.editor.set_text(txt)
        finfo.editor.document().setModified(False)
        finfo.editor.set_cursor_position(position)
        finfo.validate_project()
        
    def revert(self):
        index = self.get_stack_index()
        filename = self.data[index].filename
        answer = QMessageBox.warning(self, self.title,
                    translate("Editor",
                              "All changes to <b>%1</b> will be lost."
                              "<br>Do you want to revert file from disk?").arg(
                    osp.basename(filename)), QMessageBox.Yes|QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.reload(index)
        
    def create_new_editor(self, fname, enc, txt,
                          set_current, new=False, cloned_from=None):
        """
        Create a new editor instance
        Returns finfo object (instead of editor as in previous releases)
        """
        editor = CodeEditor(self)
        finfo = FileInfo(fname, enc, editor, new)
        if self.projectexplorer is not None:
            finfo.set_project(self.projectexplorer.get_source_project(fname))
        self.add_to_data(finfo, set_current)
        self.connect(finfo, SIGNAL("send_to_inspector(QString)"),
                     self.send_to_inspector)
        self.connect(finfo, SIGNAL('analysis_results_changed()'),
                     lambda: self.emit(SIGNAL('analysis_results_changed()')))
        self.connect(finfo, SIGNAL('todo_results_changed()'),
                     lambda: self.emit(SIGNAL('todo_results_changed()')))
        self.connect(finfo, SIGNAL("edit_goto(QString,int,QString)"),
                     lambda fname, lineno, name:
                     self.emit(SIGNAL("edit_goto(QString,int,QString)"),
                               fname, lineno, name))
        language = get_file_language(fname, txt)
        editor.setup_editor(
                linenumbers=self.linenumbers_enabled, language=language,
                code_analysis=self.codeanalysis_enabled,
                todo_list=self.todolist_enabled, font=self.default_font,
                color_scheme=self.color_scheme,
                wrap=self.wrap_enabled, tab_mode=self.tabmode_enabled,
                highlight_current_line=self.highlight_current_line_enabled,
                occurence_highlighting=self.occurence_highlighting_enabled,
                codecompletion_auto=self.codecompletion_auto_enabled,
                codecompletion_case=self.codecompletion_case_enabled,
                codecompletion_single=self.codecompletion_single_enabled,
                codecompletion_enter=self.codecompletion_enter_enabled,
                calltips=self.calltips_enabled,
                go_to_definition=self.go_to_definition_enabled,
                close_parentheses=self.close_parentheses_enabled,
                auto_unindent=self.auto_unindent_enabled,
                cloned_from=cloned_from)
        if cloned_from is None:
            editor.set_text(txt)
            editor.document().setModified(False)
        self.connect(finfo, SIGNAL('text_changed_at(QString,int)'),
                     lambda fname, position:
                     self.emit(SIGNAL('text_changed_at(QString,int)'),
                               fname, position))
        self.connect(editor, SIGNAL('cursorPositionChanged(int,int)'),
                     self.cursor_position_changed_callback)
        self.connect(editor, SIGNAL('textChanged()'),
                     self.start_stop_analysis_timer)
        self.connect(editor, SIGNAL('modificationChanged(bool)'),
                     self.modification_changed)
        self.connect(editor, SIGNAL("focus_in()"), self.focus_changed)
        self.connect(editor, SIGNAL("focus_changed()"),
                     self.focus_changed_callback)
        if self.outlineexplorer is not None:
            # Removing editor reference from outline explorer settings:
            self.connect(editor, SIGNAL("destroyed()"),
                         lambda obj=editor:
                         self.outlineexplorer.remove_editor(obj))

        self.find_widget.set_editor(editor)
       
        self.emit(SIGNAL('refresh_file_dependent_actions()'))
        self.modification_changed()
        
        return finfo
    
    def send_to_inspector(self, qstr):
        if not self.inspector_enabled:
            return
        if self.inspector is not None and self.inspector.dockwidget.isVisible():
            # ObjectInspector widget exists and is visible
            self.inspector.set_object_text(qstr, ignore_unknown=True)
            editor = self.get_current_editor()
            editor.setFocus()
    
    def new(self, filename, encoding, text):
        """
        Create new filename with *encoding* and *text*
        """
        finfo = self.create_new_editor(filename, encoding, text,
                                       set_current=True, new=True)
        finfo.editor.set_cursor_position('eof')
        finfo.editor.insert_text(os.linesep)
        return finfo.editor
        
    def load(self, filename, set_current=True):
        """
        Load filename, create an editor instance and return it
        *Warning* This is loading file, creating editor but not executing
        the source code analysis -- the analysis must be done by the editor
        plugin (in case multiple editorstack instances are handled)
        """
        filename = osp.abspath(unicode(filename))
        self.emit(SIGNAL('starting_long_process(QString)'),
                  translate("Editor", "Loading %1...").arg(filename))
        text, enc = encoding.read(filename)
        finfo = self.create_new_editor(filename, enc, text, set_current)
        index = self.get_stack_index()
        self._refresh_outlineexplorer(index, update=True)
        self.emit(SIGNAL('ending_long_process(QString)'), "")
        if self.isVisible() and self.checkeolchars_enabled \
           and sourcecode.has_mixed_eol_chars(text):
            name = osp.basename(filename)
            QMessageBox.warning(self, self.title,
                            translate("Editor",
                                      "<b>%1</b> contains mixed end-of-line "
                                      "characters.<br>Spyder will fix this "
                                      "automatically.").arg(name),
                            QMessageBox.Ok)
            self.set_os_eol_chars(index)
        return finfo.editor
    
    def set_os_eol_chars(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        eol_mode = sourcecode.get_eol_chars_from_os_name(os.name)
        finfo.editor.set_eol_mode(eol_mode)
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
    def __process_lines(self):
        editor = self.get_current_editor()
        ls = editor.get_line_separator()
        
        _indent = lambda line: len(line)-len(line.lstrip())
        
        line_from, line_to = editor.get_selection_bounds()
        text = editor.get_selected_text()

        lines = text.split(ls)
        if len(lines) > 1:
            # Multiline selection -> eventually fixing indentation
            original_indent = _indent(editor.get_text_line(line_from))
            text = (" "*(original_indent-_indent(lines[0])))+text
        
        # If there is a common indent to all lines, remove it
        min_indent = 999
        for line in text.split(ls):
            if line.strip():
                min_indent = min(_indent(line), min_indent)
        if min_indent:
            text = ls.join([line[min_indent:] for line in text.split(ls)])

        last_line = text.split(ls)[-1]
        if last_line.strip() == editor.get_text_line(line_to).strip():
            # If last line is complete, add an EOL character
            text += ls
        
        return text
    
    def __run_in_external_console(self, lines):
        self.emit(SIGNAL('external_console_execute_lines(QString)'), lines)
    
    def run_selection_or_block(self):
        """
        Run selected text in console and set focus to console
        *or*, if there is no selection,
        Run current block of lines in console and go to next block
        """
        editor = self.get_current_editor()
        if editor.has_selected_text():
            # Run selected text in external console and set focus to console
            self.__run_in_external_console( self.__process_lines() )
        else:
            # Run current block in external console and go to next block
            editor.select_current_block()
            self.__run_in_external_console( self.__process_lines() )
            editor.setFocus()
            editor.move_cursor_to_next('block', 'down')
            
    #------ Drag and drop
    def dragEnterEvent(self, event):
        """Reimplement Qt method
        Inform Qt about the types of data that the widget accepts"""
        source = event.mimeData()
        if source.hasUrls():
            if mimedata2url(source, extlist=self.valid_types):
                event.acceptProposedAction()
            else:
                event.ignore()
        elif source.hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        if source.hasUrls():
            files = mimedata2url(source, extlist=self.valid_types)
            if files:
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
        self.editorstack = EditorStack(self, self.plugin, menu_actions)
        self.register_editorstack_cb(self.editorstack)
        if not first:
            self.plugin.clone_editorstack(editorstack=self.editorstack)
        self.connect(self.editorstack, SIGNAL("destroyed()"),
                     self.editorstack_closed)
        self.connect(self.editorstack, SIGNAL("split_vertically()"),
                     lambda: self.split(orientation=Qt.Vertical))
        self.connect(self.editorstack, SIGNAL("split_horizontally()"),
                     lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editorstack)

    def closeEvent(self, event):
        QSplitter.closeEvent(self, event)
        if PYQT_VERSION_STR.startswith('4.6'):
            self.emit(SIGNAL('destroyed()'))
                                
    def __give_focus_to_remaining_editor(self):
        focus_widget = self.plugin.get_focus_widget()
        if focus_widget is not None:
            focus_widget.setFocus()
        
    def editorstack_closed(self):
        if DEBUG:
            print >>STDOUT, "method 'editorstack_closed':"
            print >>STDOUT, "    self  :", self
            print >>STDOUT, "    sender:", self.sender()
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
        if DEBUG:
            print >>STDOUT, "method 'editorsplitter_closed':"
            print >>STDOUT, "    self  :", self
            print >>STDOUT, "    sender:", self.sender()
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
                     self.editorsplitter_closed)
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
        return dict(hexstate=str(self.saveState().toHex()),
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


#===============================================================================
# Status bar widgets
#===============================================================================
class StatusBarWidget(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)

        self.label_font = font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.hide()
        statusbar.addPermanentWidget(self)

class ReadWriteStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(translate("Editor", "Permissions:")))
        self.readwrite = QLabel()
        self.readwrite.setFont(self.label_font)
        layout.addWidget(self.readwrite)
        layout.addSpacing(20)
        
    def readonly_changed(self, readonly):
        readwrite = "R" if readonly else "RW"
        self.readwrite.setText(readwrite.ljust(3))
        self.show()

class EOLStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(translate("Editor", "End-of-lines:")))
        self.eol = QLabel()
        self.eol.setFont(self.label_font)
        layout.addWidget(self.eol)
        layout.addSpacing(20)
        
    def eol_changed(self, os_name):
        os_name = unicode(os_name)
        self.eol.setText({"nt": "CRLF", "posix": "LF"}.get(os_name, "CR"))
        self.show()

class EncodingStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(translate("Editor", "Encoding:")))
        self.encoding = QLabel()
        self.encoding.setFont(self.label_font)
        layout.addWidget(self.encoding)
        layout.addSpacing(20)
        
    def encoding_changed(self, encoding):
        self.encoding.setText(str(encoding).upper().ljust(15))
        self.show()

class CursorPositionStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(translate("Editor", "Line:")))
        self.line = QLabel()
        self.line.setFont(self.label_font)
        layout.addWidget(self.line)
        layout.addWidget(QLabel(translate("Editor", "Column:")))
        self.column = QLabel()
        self.column.setFont(self.label_font)
        layout.addWidget(self.column)
        self.setLayout(layout)
        
    def cursor_position_changed(self, line, index):
        self.line.setText("%-6d" % (line+1))
        self.column.setText("%-4d" % (index+1))
        self.show()


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
        self.outlineexplorer = OutlineExplorer(self, show_fullpath=show_fullpath,
                                            fullpath_sorting=fullpath_sorting,
                                            show_all_files=show_all_files,
                                            show_comments=show_comments)
        self.connect(self.outlineexplorer,
                     SIGNAL("edit_goto(QString,int,QString)"), plugin.load)
        
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
        for index in range(editorsplitter.editorstack.get_stack_count()):
            editorsplitter.editorstack._refresh_outlineexplorer(index, update=True)
        
    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        if DEBUG:
            print >>STDOUT, "EditorWidget.register_editorstack:", editorstack
            self.__print_editorstacks()
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
        self.connect(editorstack, SIGNAL('cursorPositionChanged(int,int)'),
                     self.cursorpos_status.cursor_position_changed)
        self.connect(editorstack, SIGNAL('refresh_eol_mode(QString)'),
                     self.eol_status.eol_changed)
        self.plugin.register_editorstack(editorstack)
        oe_btn = create_toolbutton(self)
        oe_btn.setDefaultAction(self.outlineexplorer.visibility_action)
        editorstack.add_widget_to_header(oe_btn, space_before=True)
        
    def __print_editorstacks(self):
        print >>STDOUT, "%d editorstack(s) in editorwidget:" \
                        % len(self.editorstacks)
        for edst in self.editorstacks:
            print >>STDOUT, "    ", edst
        
    def unregister_editorstack(self, editorstack):
        if DEBUG:
            print >>STDOUT, "EditorWidget.unregister_editorstack:", editorstack
        self.plugin.unregister_editorstack(editorstack)
        self.editorstacks.pop(self.editorstacks.index(editorstack))
        if DEBUG:
            self.__print_editorstacks()
        

class EditorMainWindow(QMainWindow):
    def __init__(self, plugin, menu_actions, toolbar_list, menu_list,
                 show_fullpath, fullpath_sorting, show_all_files, show_comments):
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
            quit_action = create_action(self,
                                translate("Editor", "Close window"),
                                icon="close_panel.png",
                                tip=translate("Editor", "Close this window"),
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
        if PYQT_VERSION_STR.startswith('4.6'):
            self.emit(SIGNAL('destroyed()'))
            for editorstack in self.editorwidget.editorstacks[:]:
                if DEBUG:
                    print >>STDOUT, "--> destroy_editorstack:", editorstack
                editorstack.emit(SIGNAL('destroyed()'))
                                
    def get_layout_settings(self):
        """Return layout state"""
        splitsettings = self.editorwidget.editorsplitter.get_layout_settings()
        return dict(size=(self.window_size.width(), self.window_size.height()),
                    pos=(self.pos().x(), self.pos().y()),
                    is_maximized=self.isMaximized(),
                    is_fullscreen=self.isFullScreen(),
                    hexstate=str(self.saveState().toHex()),
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


class FakePlugin(QSplitter):
    def __init__(self):
        QSplitter.__init__(self)
                
        menu_actions = []
                
        self.editorstacks = []
        self.editorwindows = []

        self.find_widget = FindReplace(self, enable_replace=True)
        self.outlineexplorer = OutlineExplorer(self, show_fullpath=False,
                                               show_all_files=False)

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
        
    def closeEvent(self, event):
        for win in self.editorwindows[:]:
            win.close()
        if DEBUG:
            print >>STDOUT, len(self.editorwindows), ":", self.editorwindows
            print >>STDOUT, len(self.editorstacks), ":", self.editorstacks
        event.accept()
        
    def load(self, fname):
        editorstack = self.editorstacks[0]
        editorstack.load(fname)
        editorstack.analyze_script()
    
    def register_editorstack(self, editorstack):
        if DEBUG:
            print >>STDOUT, "FakePlugin.register_editorstack:", editorstack
        self.editorstacks.append(editorstack)
        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            editorstack.set_fullpath_sorting_enabled(True)
            editorstack.set_closable( len(self.editorstacks) > 1 )
            editorstack.set_outlineexplorer(self.outlineexplorer)
            editorstack.set_find_widget(self.find_widget)
            oe_btn = create_toolbutton(self)
            oe_btn.setDefaultAction(self.outlineexplorer.visibility_action)
            editorstack.add_widget_to_header(oe_btn, space_before=True)
            
        action = QAction(self)
        editorstack.set_io_actions(action, action, action, action)
        font = QFont("Courier New")
        font.setPointSize(10)
        editorstack.set_default_font(font, color_scheme='Spyder')
        self.connect(editorstack, SIGNAL('close_file(int)'),
                     self.close_file_in_all_editorstacks)
        self.connect(editorstack, SIGNAL("create_new_window()"),
                     self.create_new_window)
        self.connect(editorstack, SIGNAL('plugin_load(QString)'),
                     self.load)
                    
    def unregister_editorstack(self, editorstack):
        if DEBUG:
            print >>STDOUT, "FakePlugin.unregister_editorstack:", editorstack
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
                                  show_all_files=False)
        window.resize(self.size())
        window.show()
        self.register_editorwindow(window)
        self.connect(window, SIGNAL("destroyed()"),
                     lambda win=window: self.unregister_editorwindow(win))
        
    def register_editorwindow(self, window):
        if DEBUG:
            print >>STDOUT, "register_editorwindowQObject*:", window
        self.editorwindows.append(window)
        
    def unregister_editorwindow(self, window):
        if DEBUG:
            print >>STDOUT, "unregister_editorwindow:", window
        self.editorwindows.pop(self.editorwindows.index(window))
    
    def get_focus_widget(self):
        pass

    def close_file_in_all_editorstacks(self, index):
        sender = self.sender()
        for editorstack in self.editorstacks:
            if editorstack is not sender:
                editorstack.blockSignals(True)
                editorstack.close_file(index)
                editorstack.blockSignals(False)
    

def test():
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    test = FakePlugin()
    test.resize(900, 800)
    test.load(__file__)
    test.load("explorer.py")
    test.load("dicteditor.py")
    test.load("codeeditor/codeeditor.py")
    test.show()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    test()
    
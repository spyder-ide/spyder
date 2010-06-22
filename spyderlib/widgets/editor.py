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

#TODO: Add a button "Opened files management" -> opens a qlistwidget with
#      checkboxes + toolbar with "Save", "Close"

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QMessageBox, QMenu, QFont,
                         QAction, QApplication, QWidget, QHBoxLayout, QSplitter,
                         QComboBox, QKeySequence, QShortcut, QSizePolicy,
                         QMainWindow, QLabel)
from PyQt4.QtCore import (SIGNAL, Qt, QFileInfo, QThread, QObject, QByteArray,
                          PYQT_VERSION_STR, QSize, QPoint)

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
from spyderlib.widgets.editortools import check, ClassBrowser
try:
    from spyderlib.widgets.qscieditor.qscieditor import QsciEditor as CodeEditor
    from spyderlib.widgets.qscieditor.qscieditor import Printer #@UnusedImport
    from spyderlib.widgets.qscieditor.qscibase import TextEditBaseWidget #@UnusedImport
except ImportError:
    from spyderlib.widgets.qteditor.qteditor import QtEditor as CodeEditor
    from spyderlib.widgets.qteditor.qteditor import Printer #@UnusedImport
    from spyderlib.widgets.qteditor.qtebase import TextEditBaseWidget #@UnusedImport


class CodeAnalysisThread(QThread):
    """Pyflakes code analysis thread"""
    def __init__(self, parent):
        QThread.__init__(self, parent)
        self.filename = None
        
    def set_filename(self, filename):
        self.filename = filename
        
    def run(self):
        self.analysis_results = check(self.filename)
        
    def get_results(self):
        return self.analysis_results


class ToDoFinderThread(QThread):
    """TODO finder thread"""
    PATTERN = r"# ?TODO ?:[^#]*|# ?FIXME ?:[^#]*|# ?XXX ?:?[^#]*"
    def __init__(self, parent):
        QThread.__init__(self, parent)
        self.text = None
        
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


class TabInfo(QObject):
    """File properties"""
    def __init__(self, filename, encoding, editor, new):
        QObject.__init__(self)
        self.filename = filename
        self.newly_created = new
        self.encoding = encoding
        self.editor = editor
        self.classes = (filename, None, None)
        self.analysis_results = []
        self.todo_results = []
        self.lastmodified = QFileInfo(filename).lastModified()
            
        self.analysis_thread = CodeAnalysisThread(self)
        self.connect(self.analysis_thread, SIGNAL('finished()'),
                     self.code_analysis_finished)
        
        self.todo_thread = ToDoFinderThread(self)
        self.connect(self.todo_thread, SIGNAL('finished()'),
                     self.todo_finished)
    
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
            self.todo_thread.set_text(self.editor.get_text())
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
        self.editor.cleanup_todo_list()


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
        self.setLayout(layout)

        self.header_layout = None
        self.menu = None
        self.combo = None
        self.default_combo_font = None
        self.previous_btn = None
        self.next_btn = None
        self.tabs = None
        self.close_btn = None

        self.stack_history = []
        
        self.setup_editorstack(parent, layout, actions)

        self.find_widget = None

        self.data = []
        
        self.menu_actions = actions
        self.classbrowser = None
        self.unregister_callback = None
        self.is_closable = False
        self.new_action = None
        self.open_action = None
        self.save_action = None
        self.tempfile_path = None
        self.title = translate("Editor", "Editor")
        self.filetype_filters = None
        self.valid_types = None
        self.codeanalysis_enabled = True
        self.todolist_enabled = True
        self.classbrowser_enabled = True
        self.codefolding_enabled = True
        self.default_font = None
        self.wrap_enabled = False
        self.tabmode_enabled = False
        self.occurence_highlighting_enabled = True
        self.checkeolchars_enabled = True
        self.fullpath_sorting_enabled = None
        self.set_fullpath_sorting_enabled(False)
        
        self.cursor_position_changed_callback = lambda line, index: \
                self.emit(SIGNAL('cursorPositionChanged(int,int)'), line, index)
        self.focus_changed_callback = lambda: \
                                      plugin.emit(SIGNAL("focus_changed()"))
        
        self.__file_status_flag = False
        
        # Accepting drops
        self.setAcceptDrops(True)
        
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

        self.previous_btn = create_toolbutton(self, get_icon('previous.png'),
                         tip=translate("Editor", "Previous file (Ctrl+Tab)"),
                         triggered=self.go_to_previous_file)
        self.add_widget_to_header(self.previous_btn, space_before=True)
        
        self.next_btn = create_toolbutton(self, get_icon('next.png'),
                         tip=translate("Editor", "Next file (Ctrl+Shift+Tab)"),
                         triggered=self.go_to_next_file)
        self.add_widget_to_header(self.next_btn)
                
        # File combo box
        self.combo = QComboBox(self)
        self.default_combo_font = self.combo.font()
        self.combo.setMaxVisibleItems(20)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.connect(self.combo, SIGNAL('currentIndexChanged(int)'),
                     self.current_changed)
        self.add_widget_to_header(self.combo)

        # Buttons to the right of file combo box
        self.close_btn = create_toolbutton(self, triggered=self.close_file,
                                       icon=get_icon("fileclose.png"),
                                       tip=translate("Editor", "Close file"))
        self.add_widget_to_header(self.close_btn)
        layout.addLayout(self.header_layout)

        # Local shortcuts
        tabsc = QShortcut(QKeySequence("Ctrl+Tab"), parent,
                          self.go_to_previous_file)
        tabsc.setContext(Qt.WidgetWithChildrenShortcut)
        tabshiftsc = QShortcut(QKeySequence("Ctrl+Shift+Tab"), parent,
                               self.go_to_next_file)
        tabshiftsc.setContext(Qt.WidgetWithChildrenShortcut)
        
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
        super(EditorStack, self).closeEvent(event)
        if PYQT_VERSION_STR.startswith('4.6'):
            self.emit(SIGNAL('destroyed()'))        
            
    def clone_from(self, other):
        """Clone EditorStack from other instance"""
        for other_finfo in other.data:
            fname = other_finfo.filename
            enc = other_finfo.encoding
            finfo = self.create_new_editor(fname, enc, "", set_current=True,
                                           clone=True)
            finfo.editor.set_as_clone(other_finfo.editor)
            finfo.set_analysis_results(other_finfo.analysis_results)
            finfo.set_todo_results(other_finfo.todo_results)
        self.set_stack_index(other.get_stack_index())
        
    #------ Editor Widget Settings
    def set_closable(self, state):
        """Parent widget must handle the closable state"""
        self.is_closable = state
        
    def set_io_actions(self, new_action, open_action, save_action):
        self.new_action = new_action
        self.open_action = open_action
        self.save_action = save_action
        
    def set_find_widget(self, find_widget):
        self.find_widget = find_widget
        
    def set_classbrowser(self, classbrowser):
        self.classbrowser = classbrowser
        self.classbrowser_enabled = True
        self.connect(self.classbrowser, SIGNAL("classbrowser_is_visible()"),
                     self._refresh_classbrowser)
        
    def set_tempfile_path(self, path):
        self.tempfile_path = path
        
    def set_title(self, text):
        self.title = text
        
    def set_filetype_filters(self, filetype_filters):
        self.filetype_filters = filetype_filters
        
    def set_valid_types(self, valid_types):
        self.valid_types = valid_types
        
    def __update_editor_margins(self, editor):
        editor.setup_margins(linenumbers=True,
                             code_folding=self.codefolding_enabled,
                             code_analysis=self.codeanalysis_enabled,
                             todo_list=self.todolist_enabled)
        
    def set_codeanalysis_enabled(self, state, current_finfo=None):
        # CONF.get(self.ID, 'code_analysis')
        self.codeanalysis_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                finfo.cleanup_analysis_results()
                if state and current_finfo is not None:
                    if current_finfo is not finfo:
                        finfo.run_code_analysis()                    
    
    def set_todolist_enabled(self, state, current_finfo=None):
        # CONF.get(self.ID, 'todo_list')
        self.todolist_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                finfo.cleanup_todo_results()
                if state and current_finfo is not None:
                    if current_finfo is not finfo:
                        finfo.run_todo_finder()
        
    def set_codefolding_enabled(self, state):
        # CONF.get(self.ID, 'code_folding')
        self.codefolding_enabled = state
        if self.data:
            for finfo in self.data:
                self.__update_editor_margins(finfo.editor)
                if not state:
                    finfo.editor.unfold_all()
        
    def set_classbrowser_enabled(self, state):
        # CONF.get(self.ID, 'class_browser')
        self.classbrowser_enabled = state
        
    def set_default_font(self, font):
        # get_font(self.ID)
        self.default_font = font
        self.__update_combobox()
        if self.data:
            for finfo in self.data:
                finfo.editor.set_font(font)
        
    def set_wrap_enabled(self, state):
        # CONF.get(self.ID, 'wrap')
        self.wrap_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.toggle_wrap_mode(state)
        
    def set_tabmode_enabled(self, state):
        # CONF.get(self.ID, 'tab_always_indent'))
        self.tabmode_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_tab_mode(state)
        
    def set_occurence_highlighting_enabled(self, state):
        # CONF.get(self.ID, 'occurence_highlighting'))
        self.occurence_highlighting_enabled = state
        if self.data:
            for finfo in self.data:
                finfo.editor.set_occurence_highlighting(state)
        
    def set_checkeolchars_enabled(self, state):
        # CONF.get(self.ID, 'check_eol_chars')
        self.checkeolchars_enabled = state
        
    def __update_combobox(self):
        if self.fullpath_sorting_enabled:
            if self.default_font is not None:
                combo_font = QFont(self.default_font)
                combo_font.setPointSize(combo_font.pointSize()-1)
                self.combo.setFont(combo_font)
            self.combo.setEditable(True)
            self.combo.lineEdit().setReadOnly(True)
        else:
            self.combo.setFont(self.default_combo_font)
            self.combo.setEditable(False)
        
    def set_fullpath_sorting_enabled(self, state):
        # CONF.get(self.ID, 'fullpath_sorting')
        self.fullpath_sorting_enabled = state
        self.__update_combobox()
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
        
    def __repopulate_stack(self):
        self.combo.blockSignals(True)
        for _i in range(self.tabs.count()):
            self.tabs.removeTab(_i)
        self.combo.clear()
        for _i, _fi in enumerate(self.data):
            fname, editor = _fi.filename, _fi.editor
            self.tabs.insertTab(_i, editor, get_filetype_icon(fname),
                                self.get_tab_title(fname))
            self.combo.insertItem(_i, get_filetype_icon(fname),
                                  self.get_combo_title(fname))
        self.combo.blockSignals(False)
        
    def rename_in_data(self, index, new_filename):
        finfo = self.data[index]
        set_new_index = index == self.get_stack_index()
        finfo.filename = new_filename
        self.data.sort(key=self.__get_sorting_func())
        new_index = self.data.index(finfo)
        self.__repopulate_stack()
        if set_new_index:
            self.set_stack_index(new_index)
        if self.classbrowser is not None:
            self.classbrowser.file_renamed(finfo.editor, finfo.filename)
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
        for index, finfo in enumerate(self.data):
            if osp.realpath(filename) == osp.realpath(finfo.filename):
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
        """Close current file"""
        if index is None:
            if self.get_stack_count():
                index = self.get_stack_index()
            else:
                self.find_widget.set_editor(None)
                return
        is_ok = self.save_if_changed(cancelable=True, index=index)
        if is_ok:
            # Removing editor reference from class browser settings:
            if self.classbrowser is not None:
                self.classbrowser.remove_editor(self.data[index].editor)
            
            self.remove_from_data(index)
            self.emit(SIGNAL('close_file(int)'), index)
            if not self.data and self.is_closable:
                # editortabwidget is empty: removing it
                # (if it's not the first editortabwidget)
                self.close()
            self.emit(SIGNAL('opened_files_list_changed()'))
            self.emit(SIGNAL('update_code_analysis_actions()'))
            self._refresh_classbrowser()
            self.emit(SIGNAL('refresh_file_dependent_actions()'))
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
            if self.data[index].editor.isModified():
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
            elif finfo.editor.isModified():
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
        if not finfo.editor.isModified() and not force:
            return True
        if not osp.isfile(finfo.filename) and not force:
            # File has not been saved yet
            filename = self.select_savename(finfo.filename)
            if filename:
                finfo.filename = filename
            else:
                return False
        txt = unicode(finfo.editor.get_text())
        try:
            finfo.encoding = encoding.write(txt, finfo.filename, finfo.encoding)
            finfo.newly_created = False
            self.emit(SIGNAL('encoding_changed(QString)'), finfo.encoding)
            finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
            self.emit(SIGNAL('file_saved(int)'), index)
            finfo.editor.setModified(False)
            self.modification_changed(index=index)
            self.analyze_script(index)
            
            #XXX QtEditor-only: re-scan the whole text to rebuild class browser 
            #    data from scratch (could be optimized because rehighlighting
            #    text means searching for all syntax coloring patterns instead 
            #    of only searching for class/def patterns which would be 
            #    sufficient for class browser data.
            finfo.editor.rehighlight()
            
            self._refresh_classbrowser(index)
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
    
    def save_as(self):
        """Save file as..."""
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
            self.save(index=new_index, force=True)
            self.refresh(new_index)
            self.set_stack_index(new_index)
        
    def save_all(self):
        """Save all opened files"""
        folders = set()
        for index in range(self.get_stack_count()):
            folders.add(osp.dirname(self.data[index].filename))
            self.save(index, refresh_explorer=False)
        for folder in folders:
            self.emit(SIGNAL("refresh_explorer(QString)"), folder)
    
    #------ Update UI
    def analyze_script(self, index=None):
        """Analyze current script with pyflakes + find todos"""
        if index is None:
            index = self.get_stack_index()
        if self.data:
            finfo = self.data[index]
            if self.codeanalysis_enabled:
                finfo.run_code_analysis()
            if self.todolist_enabled:
                finfo.run_todo_finder()
                
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
        for btn in (self.previous_btn, self.next_btn):
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
        
    def go_to_previous_file(self):
        """Ctrl+Tab"""
        if len(self.stack_history) > 1:
            last = len(self.stack_history)-1
            w_id = self.stack_history.pop(last)
            self.stack_history.insert(0, w_id)
            last_id = self.stack_history[last]
            for _i in range(self.tabs.count()):
                if id(self.tabs.widget(_i)) == last_id:
                    self.set_stack_index(_i)
                    break
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
        
    def _refresh_classbrowser(self, index=None, update=True):
        """Refresh class browser panel"""
        if index is None:
            index = self.get_stack_index()
        enable = False
        cb = self.classbrowser
        if self.data:
            finfo = self.data[index]
            # cb_visible: if class browser is not visible, maybe the whole
            # GUI is not visible (Spyder is starting up) -> in this case,
            # it is necessary to update the class browser
            cb_visible = cb.isVisible() or not self.isVisible()
            if self.classbrowser_enabled and finfo.editor.is_python() \
               and cb_visible:
                enable = True
                cb.setEnabled(True)
                cb.set_current_editor(finfo.editor, finfo.filename,
                                      update=update)
        if not enable:
            cb.setEnabled(False)
            
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
            # gets focus and then give it back to the QsciEditor instance,
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
                if finfo.editor.isModified():
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
            self._refresh_classbrowser(index, update=False)
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
            state = finfo.editor.isModified()
        combo_title, tab_title = self.get_titles(state, finfo)
        self.set_stack_title(index, combo_title, tab_title)
        # Toggle save/save all actions state
        self.save_action.setEnabled(state)
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
        finfo.editor.setModified(False)
        finfo.editor.set_cursor_position(position)
        
    def create_new_editor(self, fname, enc, txt,
                          set_current, new=False, clone=False):
        """
        Create a new editor instance
        Returns finfo object (instead of editor as in previous releases)
        """
        ext = osp.splitext(fname)[1]
        if ext.startswith('.'):
            ext = ext[1:] # file extension with leading dot
        language = ext
        if not ext:
            for line in txt.splitlines():
                if not line.strip():
                    continue
                if line.startswith('#!') and \
                   line[2:].split() == ['/usr/bin/env', 'python']:
                        language = 'python'
                else:
                    break
        editor = CodeEditor(self)
        finfo = TabInfo(fname, enc, editor, new)
        self.add_to_data(finfo, set_current)
        self.connect(finfo, SIGNAL('analysis_results_changed()'),
                     lambda: self.emit(SIGNAL('analysis_results_changed()')))
        self.connect(finfo, SIGNAL('todo_results_changed()'),
                     lambda: self.emit(SIGNAL('todo_results_changed()')))
        if not clone:
            editor.setup_editor(linenumbers=True, language=language,
                                code_analysis=self.codeanalysis_enabled,
                                code_folding=self.codefolding_enabled,
                                todo_list=self.todolist_enabled,
                                font=self.default_font,
                                wrap=self.wrap_enabled,
                                tab_mode=self.tabmode_enabled,
                                occurence_highlighting=\
                                self.occurence_highlighting_enabled)
            editor.set_text(txt)
            editor.setModified(False)
        self.connect(editor, SIGNAL('cursorPositionChanged(int,int)'),
                     self.cursor_position_changed_callback)
        self.connect(editor, SIGNAL('modificationChanged(bool)'),
                     self.modification_changed)
        self.connect(editor, SIGNAL("focus_in()"), self.focus_changed)
        self.connect(editor, SIGNAL("focus_changed()"),
                     self.focus_changed_callback)
        if self.classbrowser is not None:
            # Removing editor reference from class browser settings:
            self.connect(editor, SIGNAL("destroyed()"),
                         lambda obj=editor:
                         self.classbrowser.remove_editor(obj))

        self.find_widget.set_editor(editor)
       
        self.emit(SIGNAL('refresh_file_dependent_actions()'))
        self.modification_changed()
        
        return finfo
    
    def new(self, filename, encoding, text):
        """
        Create new filename with *encoding* and *text*
        """
        finfo = self.create_new_editor(filename, encoding, text,
                                       set_current=True, new=True)
        editor = finfo.editor
        editor.set_cursor_position('eof')
        editor.insert_text(os.linesep)
        return editor
        
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
        self._refresh_classbrowser(index, update=True)
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
        finfo.editor.setModified(True)
        
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
        text = unicode(editor.selectedText())

        lines = text.split(ls)
        if len(lines) > 1:
            # Multiline selection -> eventually fixing indentation
            original_indent = _indent(unicode(editor.text(line_from)))
            text = (" "*(original_indent-_indent(lines[0])))+text
        
        # If there is a common indent to all lines, remove it
        min_indent = 999
        for line in text.split(ls):
            if line.strip():
                min_indent = min(_indent(line), min_indent)
        if min_indent:
            text = ls.join([line[min_indent:] for line in text.split(ls)])

        last_line = text.split(ls)[-1]
        if last_line.strip() == unicode(editor.text(line_to)).strip():
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
        if editor.hasSelectedText():
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
        super(EditorSplitter, self).closeEvent(event)
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
    def __init__(self, parent, plugin, menu_actions, toolbar_list, menu_list,
                 show_fullpath, fullpath_sorting, show_all_files):
        super(EditorWidget, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        statusbar = parent.statusBar() # Create a status bar
        self.readwrite_status = ReadWriteStatus(self, statusbar)
        self.eol_status = EOLStatus(self, statusbar)
        self.encoding_status = EncodingStatus(self, statusbar)
        self.cursorpos_status = CursorPositionStatus(self, statusbar)
        
        self.editorstacks = []
        
        self.plugin = plugin
        
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        self.classbrowser = ClassBrowser(self, show_fullpath=show_fullpath,
                                         fullpath_sorting=fullpath_sorting,
                                         show_all_files=show_all_files)
        self.connect(self.classbrowser,
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
        splitter.addWidget(editor_widgets)
        splitter.addWidget(self.classbrowser)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        # Refreshing class browser
        for index in range(editorsplitter.editorstack.get_stack_count()):
            editorsplitter.editorstack._refresh_classbrowser(index, update=True)
        
    def register_editorstack(self, editorstack):
        self.editorstacks.append(editorstack)
        if DEBUG:
            print >>STDOUT, "EditorWidget.register_editorstack:", editorstack
            self.__print_editorstacks()
        editorstack.set_closable( len(self.editorstacks) > 1 )
        editorstack.set_classbrowser(self.classbrowser)
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
        cb_btn = create_toolbutton(self, text_beside_icon=False)
        cb_btn.setDefaultAction(self.classbrowser.visibility_action)
        editorstack.add_widget_to_header(cb_btn, space_before=True)
        
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
                 show_fullpath, fullpath_sorting, show_all_files):
        super(EditorMainWindow, self).__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.window_size = None
        
        self.editorwidget = EditorWidget(self, plugin, menu_actions,
                                         toolbar_list, menu_list,
                                         show_fullpath, fullpath_sorting,
                                         show_all_files)
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
        super(EditorMainWindow, self).closeEvent(event)
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
        self.classbrowser = ClassBrowser(self, show_fullpath=False,
                                         show_all_files=False)

        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        editor_layout.addWidget(EditorSplitter(self, self, menu_actions,
                                               first=True))
        editor_layout.addWidget(self.find_widget)
        
        self.addWidget(editor_widgets)
        self.addWidget(self.classbrowser)
        
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
            editorstack.set_closable( len(self.editorstacks) > 1 )
            editorstack.set_classbrowser(self.classbrowser)
            editorstack.set_find_widget(self.find_widget)
        action = QAction(self)
        editorstack.set_io_actions(action, action, action)
        font = QFont("Courier New")
        font.setPointSize(10)
        editorstack.set_default_font(font)
        self.connect(editorstack, SIGNAL('close_file(int)'),
                     self.close_file_in_all_editorstacks)
        self.connect(editorstack, SIGNAL("create_new_window()"),
                     self.create_new_window)
        self.connect(editorstack, SIGNAL('plugin_load(QString)'),
                     self.load)
        
        cb_btn = create_toolbutton(self, text_beside_icon=False)
        cb_btn.setDefaultAction(self.classbrowser.visibility_action)
        editorstack.add_widget_to_header(cb_btn, space_before=True)
            
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
    test.load("qscieditor/qscieditor.py")
    test.show()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    test()
    
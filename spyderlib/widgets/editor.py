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
                         QStackedWidget, QComboBox, QKeySequence, QShortcut,
                         QSizePolicy, QMainWindow, QLabel)
from PyQt4.QtCore import SIGNAL, Qt, QFileInfo, QThread, QObject

import os, sys
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
from spyderlib.widgets.qscieditor import QsciEditor, check
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.qscieditor import ClassBrowser


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
        self.lastmodified = QFileInfo(filename).lastModified()
            
        self.analysis_thread = CodeAnalysisThread(self)
        self.connect(self.analysis_thread, SIGNAL('finished()'),
                     self.code_analysis_finished)
    
    def run_code_analysis(self):
        if self.editor.is_python():
            self.analysis_thread.set_filename(self.filename)
            self.analysis_thread.start()
        
    def code_analysis_finished(self):
        """Code analysis thread has finished"""
        self.analysis_results = self.analysis_thread.get_results()
        self.editor.process_code_analysis(self.analysis_results)
        self.emit(SIGNAL('analysis_results_changed()'))        


class EditorStack(QWidget):
    def __init__(self, parent, plugin, actions):
        QWidget.__init__(self, parent)
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        menu_btn = create_toolbutton(self, icon=get_icon("tooloptions.png"),
                                     tip=translate("Editor", "Options"))
        self.menu = QMenu(self)
        menu_btn.setMenu(self.menu)
        menu_btn.setPopupMode(menu_btn.InstantPopup)
        self.connect(self.menu, SIGNAL("aboutToShow()"), self.__setup_menu)
        header_layout.addWidget(menu_btn)
        self.previous_btn = create_toolbutton(self, get_icon('previous.png'),
                             tip=translate("Editor", "Previous (Ctrl+Tab)"),
                             triggered=self.go_to_previous_file)
        header_layout.addWidget(self.previous_btn)
        self.next_btn = create_toolbutton(self, get_icon('next.png'),
                             tip=translate("Editor", "Next (Ctrl+Shift+Tab)"),
                             triggered=self.go_to_next_file)
        header_layout.addWidget(self.next_btn)

        # Local shortcuts
        tabsc = QShortcut(QKeySequence("Ctrl+Tab"), parent,
                          self.go_to_previous_file)
        tabsc.setContext(Qt.WidgetWithChildrenShortcut)
        tabshiftsc = QShortcut(QKeySequence("Ctrl+Shift+Tab"), parent,
                               self.go_to_next_file)
        tabshiftsc.setContext(Qt.WidgetWithChildrenShortcut)
        
        self.combo = QComboBox(self)
        self.combo.setMaxVisibleItems(20)
        self.combo.setEditable(True)
        self.combo.lineEdit().setReadOnly(True)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLength)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.connect(self.combo, SIGNAL('currentIndexChanged(int)'),
                     self.current_changed)
        header_layout.addWidget(self.combo)
        
        self.close_btn = create_toolbutton(self, triggered=self.close_file,
                                       icon=get_icon("fileclose.png"),
                                       tip=translate("Editor", "Close file"))
        header_layout.addWidget(self.close_btn)
        layout.addLayout(header_layout)

        self.stack_history = []
        
        self.stack = QStackedWidget(self)
        self.connect(self.combo, SIGNAL('currentIndexChanged(int)'),
                     self.stack.setCurrentIndex)
        layout.addWidget(self.stack)
        
        self.find_widget = None

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
        self.classbrowser_enabled = True
        self.codefolding_enabled = True
        self.showeolchars_enabled = False
        self.showwhitespace_enabled = False
        self.default_font = None
        self.wrap_enabled = False
        self.tabmode_enabled = False
        self.checkeolchars_enabled = True
        
        self.cursor_position_changed_callback = lambda line, index: \
                self.emit(SIGNAL('cursorPositionChanged(int,int)'), line, index)
        self.focus_changed_callback = lambda: \
                                      plugin.emit(SIGNAL("focus_changed()"))
        
        self.data = []
        
        self.__file_status_flag = False
        
        # Accepting drops
        self.setAcceptDrops(True)
        
    def clone_from(self, other):
        """Clone EditorStack from other instance"""
        for other_finfo in other.data:
            fname = other_finfo.filename
            enc = other_finfo.encoding
            finfo = self.create_new_editor(fname, enc, "", set_current=True)
            finfo.editor.set_as_clone(other_finfo.editor)
        
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
        
    def set_tempfile_path(self, path):
        self.tempfile_path = path
        
    def set_title(self, text):
        self.title = text
        
    def set_filetype_filters(self, filetype_filters):
        self.filetype_filters = filetype_filters
        
    def set_valid_types(self, valid_types):
        self.valid_types = valid_types
        
    def set_codeanalysis_enabled(self, state):
        # CONF.get(self.ID, 'code_analysis')
        self.codeanalysis_enabled = state
        
    def set_classbrowser_enabled(self, state):
        # CONF.get(self.ID, 'class_browser')
        self.classbrowser_enabled = state
        
    def set_codefolding_enabled(self, state):
        # CONF.get(self.ID, 'code_folding')
        self.codefolding_enabled = state
        
    def set_showeolchars_enabled(self, state):
        # CONF.get(self.ID, 'show_eol_chars')
        self.showeolchars_enabled = state
        
    def set_showwhitespace_enabled(self, state):
        # CONF.get(self.ID, 'show_whitespace')
        self.showwhitespace_enabled = state
        
    def set_default_font(self, font):
        # get_font(self.ID)
        self.default_font = font
        combo_font = QFont(font)
        combo_font.setPointSize(combo_font.pointSize()-1)
        self.combo.setFont(combo_font)
        
    def set_wrap_enabled(self, state):
        # CONF.get(self.ID, 'wrap')
        self.wrap_enabled = state
        
    def set_tabmode_enabled(self, state):
        # CONF.get(self.ID, 'tab_always_indent'))
        self.tabmode_enabled = state
        
    def set_checkeolchars_enabled(self, state):
        # CONF.get(self.ID, 'check_eol_chars')
        self.checkeolchars_enabled = state
    
    
    #------ Stacked widget management
    def get_stack_index(self):
        return self.stack.currentIndex()
    
    def get_current_editor(self):
        return self.stack.currentWidget()
    
    def get_stack_count(self):
        return self.stack.count()
    
    def set_stack_index(self, index):
        for widget in (self.stack, self.combo):
            widget.setCurrentIndex(index)
    
    def remove_from_data(self, index):
        widget = self.stack.widget(index)
        self.stack.removeWidget(widget)
        self.data.pop(index)
        self.combo.removeItem(index)
    
    def add_to_data(self, finfo, set_current):
        self.data.append(finfo)
        self.data.sort(key=lambda item: item.filename)
        index = self.data.index(finfo)
        fname, editor = finfo.filename, finfo.editor
        title = self.get_title(fname)
        self.combo.blockSignals(True)
        self.stack.insertWidget(index, editor)
        self.combo.insertItem(index, get_filetype_icon(fname), title)
        if set_current:
            self.set_stack_index(index)
        self.combo.blockSignals(False)
        if set_current:
            self.current_changed(index)
        
    def rename_in_data(self, index, new_filename):
        finfo = self.data[index]
        finfo.filename = new_filename
        self.data.sort(key=lambda item: item.filename)
        new_index = self.data.index(finfo)
        
        self.combo.blockSignals(True)
        for _i in range(self.stack.count()):
            self.stack.removeWidget(self.stack.widget(_i))
        self.combo.clear()
        for _i, _fi in enumerate(self.data):
            fname, editor = _fi.filename, _fi.editor
            title = self.get_title(fname)
            self.stack.insertWidget(_i, editor)
            self.combo.insertItem(_i, get_filetype_icon(fname), title)
        self.combo.blockSignals(False)
        self.set_stack_index(new_index)
        
        return new_index
        
    def set_stack_title(self, index, title):
        self.combo.setItemText(index, title)
        
    #------ Tab menu
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
        newwindow_action = create_action(self,
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
        return [None, newwindow_action, None, 
                self.versplit_action, self.horsplit_action, self.close_action]
        
    def reset_orientation(self):
        self.horsplit_action.setEnabled(True)
        self.versplit_action.setEnabled(True)
        
    def set_orientation(self, orientation):
        self.horsplit_action.setEnabled(orientation == Qt.Horizontal)
        self.versplit_action.setEnabled(orientation == Qt.Vertical)
        
    
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
            if not self.data:
                # editortabwidget is empty: removing it
                # (if it's not the first editortabwidget)
                self.close()
            self.emit(SIGNAL('opened_files_list_changed()'))
            self.emit(SIGNAL('analysis_results_changed()'))
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
            finfo.editor.setModified(False)
            finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
            self.modification_changed(index=index)
            self.analyze_script(index)
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
            new_index =self.rename_in_data(index, new_filename=filename)
            self.save(index=new_index, force=True)
            self.refresh(new_index)
        
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
        """Analyze current script with pyflakes"""
        if index is None:
            index = self.get_stack_index()
        if self.data:
            if self.codeanalysis_enabled:
                finfo = self.data[index]
                finfo.run_code_analysis()
        
    def get_analysis_results(self):
        if self.data:
            return self.data[self.get_stack_index()].analysis_results
        
    def current_changed(self, index):
        """Stack index has changed"""
        count = self.get_stack_count()
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
        id_list = [id(self.stack.widget(_i))
                   for _i in range(self.stack.count())]
        for _id in self.stack_history[:]:
            if _id not in id_list:
                self.stack_history.pop(self.stack_history.index(_id))
        current_id = id(self.stack.widget(index))
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
            for _i in range(self.stack.count()):
                if id(self.stack.widget(_i)) == last_id:
                    self.set_stack_index(_i)
                    break
        elif len(self.stack_history) == 0 and self.get_stack_count():
            self.stack_history = [id(self.stack.currentWidget())]
    
    def go_to_next_file(self):
        """Ctrl+Shift+Tab"""
        if len(self.stack_history) > 1:
            last = len(self.stack_history)-1
            w_id = self.stack_history.pop(0)
            self.stack_history.append(w_id)
            last_id = self.stack_history[last]
            for _i in range(self.stack.count()):
                if id(self.stack.widget(_i)) == last_id:
                    self.set_stack_index(_i)
                    break
        elif len(self.stack_history) == 0 and self.get_stack_count():
            self.stack_history = [id(self.stack.currentWidget())]
    
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
        line, index = finfo.editor.getCursorPosition()
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
            self.emit(SIGNAL('analysis_results_changed()'))
            self.__refresh_statusbar(index)
            self.__refresh_readonly(index)
            self.__check_file_status(index)
        else:
            editor = None
        # Update the modification-state-dependent parameters
        self.modification_changed()
        # Update FindReplace binding
        self.find_widget.set_editor(editor, refresh=False)
                
    def get_title(self, filename):
        """Return tab title"""
        if filename != encoding.to_unicode(self.tempfile_path):
            return filename
        else:
            return unicode(translate("Editor", "Temporary file"))
        
    def __get_state_index(self, state, index):
        if index is None:
            index = self.get_stack_index()
        if index == -1:
            return None, None
        if state is None:
            state = self.data[index].editor.isModified()
        return state, index
        
    def get_full_title(self, state=None, index=None):
        state, index = self.__get_state_index(state, index)
        if index is None:
            return
        finfo = self.data[index]
        title = self.get_title(finfo.filename)
        if state:
            title += "*"
        elif title.endswith('*'):
            title = title[:-1]
        if finfo.editor.isReadOnly():
            title = '(' + title + ')'
        return title
    
    def modification_changed(self, state=None, index=None):
        """
        Current editor's modification state has changed
        --> change tab title depending on new modification state
        --> enable/disable save/save all actions
        """
        sender = self.sender()
        if isinstance(sender, QsciEditor):
            for index, finfo in enumerate(self.data):
                if finfo.editor is sender:
                    break
        # This must be done before refreshing save/save all actions:
        # (otherwise Save/Save all actions will always be enabled)
        self.emit(SIGNAL('opened_files_list_changed()'))
        # --
        state, index = self.__get_state_index(state, index)
        title = self.get_full_title(state, index)
        if index is None or title is None:
            return
        self.set_stack_title(index, title)
        # Toggle save/save all actions state
        self.save_action.setEnabled(state)
        self.emit(SIGNAL('refresh_save_all_action()'))
        # Refreshing eol mode
        editor = self.data[index].editor
        eol_chars = editor.get_line_separator()
        os_name = sourcecode.get_os_name_from_eol_chars(eol_chars)
        self.emit(SIGNAL('refresh_eol_mode(QString)'), os_name)
        

    #------ Load, reload
    def reload(self, index):
        finfo = self.data[index]
        txt, finfo.encoding = encoding.read(finfo.filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
        line, index = finfo.editor.getCursorPosition()
        finfo.editor.set_text(txt)
        finfo.editor.setModified(False)
        finfo.editor.setCursorPosition(line, index)
        
    def create_new_editor(self, fname, enc, txt, set_current, new=False):
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
        editor = QsciEditor(self)
        finfo = TabInfo(fname, enc, editor, new)
        self.add_to_data(finfo, set_current)
        self.connect(finfo, SIGNAL('analysis_results_changed()'),
                     lambda: self.emit(SIGNAL('analysis_results_changed()')))
        editor.set_text(txt)
        editor.setup_editor(linenumbers=True, language=language,
                            code_analysis=self.codeanalysis_enabled,
                            code_folding=self.codefolding_enabled,
                            show_eol_chars=self.showeolchars_enabled,
                            show_whitespace=self.showwhitespace_enabled,
                            font=self.default_font,
                            wrap=self.wrap_enabled,
                            tab_mode=self.tabmode_enabled)
        self.connect(editor, SIGNAL('cursorPositionChanged(int,int)'),
                     self.cursor_position_changed_callback)
        self.connect(editor, SIGNAL('modificationChanged(bool)'),
                     self.modification_changed)
        self.connect(editor, SIGNAL("focus_in()"), self.focus_changed)
        self.connect(editor, SIGNAL("focus_changed()"),
                     self.focus_changed_callback)

        self.find_widget.set_editor(editor)
       
        self.emit(SIGNAL('refresh_file_dependent_actions()'))
        self.modification_changed()
        
        editor.setFocus()
        
        return finfo
        
    def load(self, filename, set_current=True):
        """Load filename, create an editor instance and return it"""
        filename = osp.abspath(unicode(filename))
        self.emit(SIGNAL('starting_long_process(QString)'),
                  translate("Editor", "Loading %1...").arg(filename))
        text, enc = encoding.read(filename)
        finfo = self.create_new_editor(filename, enc, text, set_current)
        index = self.get_stack_index()
        self.analyze_script(index)
        self._refresh_classbrowser(index)
        self.emit(SIGNAL('ending_long_process(QString)'), "")
        if self.isVisible() and self.checkeolchars_enabled \
           and sourcecode.has_mixed_eol_chars(text):
            name = osp.basename(filename)
            answer = QMessageBox.warning(self, self.title,
                            translate("Editor",
                                      "<b>%1</b> contains mixed end-of-line "
                                      "characters.<br>Do you want to fix this "
                                      "automatically?").arg(name),
                            QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.Yes:
                self.set_os_eol_chars(index)
                self.convert_eol_chars(index)
        return finfo.editor
    
    def set_os_eol_chars(self, index=None):
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        eol_mode = sourcecode.get_eol_chars_from_os_name(os.name)
        finfo.editor.set_eol_mode(eol_mode)
    
    def convert_eol_chars(self, index=None):
        """Convert end-of-line characters"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.convert_eol_chars()
        
    def remove_trailing_spaces(self, index=None):
        """Remove trailing spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.remove_trailing_spaces()
        
    def fix_indentation(self, index=None):
        """Replace tabs by spaces"""
        if index is None:
            index = self.get_stack_index()
        finfo = self.data[index]
        finfo.editor.fix_indentation()

    #------ Run
    def __process_lines(self):
        editor = self.get_current_editor()
        ls = editor.get_line_separator()
        
        _indent = lambda line: len(line)-len(line.lstrip())
        
        line_from, _index_from, line_to, _index_to = editor.getSelection()
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
    
    def __run_in_interactive_console(self, lines):
        self.emit(SIGNAL('interactive_console_execute_lines(QString)'), lines)

    def __run_in_external_console(self, lines):
        self.emit(SIGNAL('external_console_execute_lines(QString)'), lines)
    
    def run_selection_or_block(self, external=False):
        """
        Run selected text in console and set focus to console
        *or*, if there is no selection,
        Run current block of lines in console and go to next block
        """
        if external:
            run_callback = self.__run_in_external_console
        else:
            run_callback = self.__run_in_interactive_console
        editor = self.get_current_editor()
        if editor.hasSelectedText():
            # Run selected text in interactive console and set focus to console
            run_callback( self.__process_lines() )
        else:
            # Run current block in interactive console and go to next block
            editor.select_current_block()
            run_callback( self.__process_lines() )
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
                    self.load(fname)
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
        self.connect(self.editorstack, SIGNAL("destroyed(QObject*)"),
                     self.editorstack_closed)
        self.connect(self.editorstack, SIGNAL("split_vertically()"),
                     lambda: self.split(orientation=Qt.Vertical))
        self.connect(self.editorstack, SIGNAL("split_horizontally()"),
                     lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editorstack)
            
    def __give_focus_to_remaining_editor(self):
        focus_widget = self.plugin.get_focus_widget()
        if focus_widget is not None:
            focus_widget.setFocus()
        
    def editorstack_closed(self):
        if DEBUG:
            print >>STDOUT, "editorstack_closed:", self
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
            print >>STDOUT, "editorsplitter_closed:", self
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
        self.connect(editorsplitter, SIGNAL("destroyed(QObject*)"),
                     self.editorsplitter_closed)


class EditorWidget(QSplitter):
    def __init__(self, parent, plugin, menu_actions, toolbar_list, menu_list):
        super(EditorWidget, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        statusbar = parent.statusBar() # Create a status bar
        self.readwrite_status = ReadWriteStatus(self, statusbar)
        self.encoding_status = EncodingStatus(self, statusbar)
        self.cursorpos_status = CursorPositionStatus(self, statusbar)
        
        self.editorstacks = []
        
        self.plugin = plugin
        
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        self.classbrowser = ClassBrowser(self, fullpath=False)
        self.connect(self.classbrowser, SIGNAL("edit_goto(QString,int,bool)"),
                     plugin.load)
        
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
        editorstack.set_closable( len(self.editorstacks) > 1 )
        editorstack.set_classbrowser(self.classbrowser)
        editorstack.set_find_widget(self.find_widget)
        self.editorstacks.append(editorstack)
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
        self.plugin.register_editorstack(editorstack)
        
    def unregister_editorstack(self, editorstack):
        if DEBUG:
            print >>STDOUT, "EditorWidget.unregister_editorstack:", editorstack
        self.plugin.unregister_editorstack(editorstack)
        self.editorstacks.pop(self.editorstacks.index(editorstack))


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
        layout.addSpacing(10)
        
    def readonly_changed(self, readonly):
        readwrite = "R" if readonly else "RW"
        self.readwrite.setText(readwrite.ljust(3))
        self.show()

class EncodingStatus(StatusBarWidget):
    def __init__(self, parent, statusbar):
        StatusBarWidget.__init__(self, parent, statusbar)
        layout = self.layout()
        layout.addWidget(QLabel(translate("Editor", "Encoding:")))
        self.encoding = QLabel()
        self.encoding.setFont(self.label_font)
        layout.addWidget(self.encoding)
        layout.addSpacing(10)
        
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
        

class EditorMainWindow(QMainWindow):
    def __init__(self, plugin, menu_actions, toolbar_list, menu_list):
        super(EditorMainWindow, self).__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.editorwidget = EditorWidget(self, plugin, menu_actions,
                                         toolbar_list, menu_list)
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


class FakePlugin(QSplitter):
    def __init__(self):
        QSplitter.__init__(self)
                
        menu_actions = []
                
        self.editorstacks = []
        self.editorwindows = []

        self.find_widget = FindReplace(self, enable_replace=True)
        self.classbrowser = ClassBrowser(self, fullpath=False)

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
    
    def register_editorstack(self, editorstack):
        if DEBUG:
            print >>STDOUT, "FakePlugin.register_editorstack:", editorstack
        if self.isAncestorOf(editorstack):
            # editorstack is a child of the Editor plugin
            editorstack.set_closable( len(self.editorstacks) > 1 )
            editorstack.set_classbrowser(self.classbrowser)
            editorstack.set_find_widget(self.find_widget)
        self.editorstacks.append(editorstack)
        action = QAction(self)
        editorstack.set_io_actions(action, action, action)
        self.connect(editorstack, SIGNAL('close_file(int)'),
                     self.close_file_in_all_editorstacks)
        self.connect(editorstack, SIGNAL("create_new_window()"),
                     self.create_new_window)
            
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
                                  self.toolbar_list, self.menu_list)
        window.resize(self.size())
        window.show()
        self.register_editorwindow(window)
        self.connect(window, SIGNAL("destroyed(QObject*)"),
                     lambda obj, win=window: self.unregister_editorwindow(win))
        
    def register_editorwindow(self, window):
        if DEBUG:
            print >>STDOUT, "register_editorwindow:", window
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
    test.show()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    test()
    
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

from PyQt4.QtGui import (QVBoxLayout, QFileDialog, QMessageBox, QFontDialog,
                         QSplitter, QToolBar, QAction, QApplication, QToolBox,
                         QListWidget, QListWidgetItem, QLabel, QWidget,
                         QHBoxLayout, QPrinter, QPrintDialog, QDialog, QMenu,
                         QAbstractPrintDialog, QActionGroup, QInputDialog)
from PyQt4.QtCore import (SIGNAL, QStringList, Qt, QVariant, QFileInfo,
                          QByteArray)

import os, sys, time, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.utils import encoding, sourcecode
from spyderlib.config import CONF, get_conf_path, get_icon, get_font, set_font
from spyderlib.utils.qthelpers import (create_action, add_actions, mimedata2url,
                                       get_filetype_icon, translate)
from spyderlib.widgets.qscieditor import (QsciEditor, check, Printer,
                                          ClassBrowser)
from spyderlib.widgets.tabs import Tabs
from spyderlib.widgets.findreplace import FindReplace
from spyderlib.widgets.pylintgui import is_pylint_installed
from spyderlib.plugins import PluginWidget


class TabInfo(object):
    """File properties"""
    def __init__(self, filename, encoding, editor, new):
        self.filename = filename
        self.newly_created = new
        self.encoding = encoding
        self.editor = editor
        self.classes = (filename, None, None)
        self.analysis_results = []
        self.lastmodified = QFileInfo(filename).lastModified()

class EditorTabWidget(Tabs):
    """Editor tabwidget"""
    def __init__(self, parent, actions):
        Tabs.__init__(self, parent)
        if hasattr(self, 'setDocumentMode'):
            # Only available with PyQt >= 4.5
            self.setDocumentMode(True)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.original_actions = actions
        self.additional_actions = self.__get_split_actions()
        self.connect(self.menu, SIGNAL("aboutToShow()"), self.__setup_menu)
        
        self.plugin = parent
        self.ID = self.plugin.ID
        self.interactive_console = self.plugin.main.console
        
        self.connect(self, SIGNAL('move_data(int,int)'), self.move_data)
        self.connect(self, SIGNAL('move_tab_finished()'),
                     self.move_tab_finished)
                     
        self.set_close_function(self.close_file)
            
        self.connect(self, SIGNAL('currentChanged(int)'), self.current_changed)
        self.cursor_position_changed_callback = lambda line, index: \
                self.emit(SIGNAL('cursorPositionChanged(int,int)'), line, index)
        self.focus_changed_callback = lambda: \
                self.plugin.emit(SIGNAL("focus_changed()"))
        
        self.data = []
        
        self.__file_status_flag = False
        
        self.already_closed = False
        
        self.plugin.register_editortabwidget(self)
            
        # Accepting drops
        self.setAcceptDrops(True)

    def __setup_menu(self):
        """Setup tab context menu before showing it"""
        self.menu.clear()
        if self.data:
            actions = self.original_actions
        else:
            actions = (self.plugin.new_action, self.plugin.open_action)
            self.setFocus() # --> Editor.__get_focus_editortabwidget
        add_actions(self.menu, actions + self.additional_actions)
        self.close_action.setEnabled( len(self.plugin.editortabwidgets) > 1 )


    #------ Hor/Ver splitting
    def __get_split_actions(self):
        # Splitting
        self.versplit_action = create_action(self,
                    self.tr("Split vertically"), icon="versplit.png",
                    tip=self.tr("Split vertically this editor window"),
                    triggered=lambda: self.emit(SIGNAL("split_vertically()")))
        self.horsplit_action = create_action(self,
                    self.tr("Split horizontally"), icon="horsplit.png",
                    tip=self.tr("Split horizontally this editor window"),
                    triggered=lambda: self.emit(SIGNAL("split_horizontally()")))
        self.close_action = create_action(self,
                    self.tr("Close this panel"), icon="close_panel.png",
                    triggered=self.close_editortabwidget)
        return (None, self.versplit_action, self.horsplit_action,
                self.close_action)
        
    def reset_orientation(self):
        self.horsplit_action.setEnabled(True)
        self.versplit_action.setEnabled(True)
        
    def set_orientation(self, orientation):
        self.horsplit_action.setEnabled(orientation == Qt.Horizontal)
        self.versplit_action.setEnabled(orientation == Qt.Vertical)
        
    
    #------ Accessors
    def get_current_filename(self):
        if self.data:
            return self.data[self.currentIndex()].filename
        
    def has_filename(self, filename):
        for index, finfo in enumerate(self.data):
            if osp.realpath(filename) == osp.realpath(finfo.filename):
                return index
        
    def set_current_filename(self, filename):
        """Set current filename and return the associated editor instance"""
        index = self.has_filename(filename)
        if index is not None:
            self.setCurrentIndex(index)
            editor = self.data[index].editor
            editor.setFocus()
            return editor

        
    #------ Tabs drag'n drop
    def move_data(self, index_from, index_to, editortabwidget_to=None):
        """
        Move tab
        In fact tabs have already been moved by the tabwidget
        but we have to move the self.data elements too
        """
        self.disconnect(self, SIGNAL('currentChanged(int)'),
                        self.current_changed)
        
        finfo = self.data.pop(index_from)
        if editortabwidget_to is None:
            editortabwidget_to = self
        editortabwidget_to.data.insert(index_to, finfo)
        
        if editortabwidget_to is not self:
            self.disconnect(finfo.editor, SIGNAL('modificationChanged(bool)'),
                            self.modification_changed)
            self.disconnect(finfo.editor, SIGNAL("focus_in()"),
                            self.focus_changed)
            self.disconnect(finfo.editor,
                            SIGNAL('cursorPositionChanged(int,int)'),
                            self.cursor_position_changed_callback)
            self.disconnect(finfo.editor, SIGNAL("focus_changed()"),
                            self.focus_changed_callback)
            self.connect(finfo.editor, SIGNAL('modificationChanged(bool)'),
                         editortabwidget_to.modification_changed)
            self.connect(finfo.editor, SIGNAL("focus_in()"),
                         editortabwidget_to.focus_changed)
            self.connect(finfo.editor,
                         SIGNAL('cursorPositionChanged(int,int)'),
                         editortabwidget_to.cursor_position_changed_callback)
            self.connect(finfo.editor, SIGNAL("focus_changed()"),
                         editortabwidget_to.focus_changed_callback)
        
    def move_tab_finished(self):
        """Reconnecting current changed signal"""
        self.connect(self, SIGNAL('currentChanged(int)'), self.current_changed)
    
    
    #------ Close file, tabwidget...
    def close_file(self, index=None):
        """Close current file"""
        if index is None:
            if self.count():
                index = self.currentIndex()
            else:
                self.plugin.find_widget.set_editor(None)
                return
        is_ok = self.save_if_changed(cancelable=True, index=index)
        if is_ok:
            
            # Removing editor reference from class browser settings:
            classbrowser = self.plugin.classbrowser
            classbrowser.remove_editor(self.data[index].editor)
            
            self.data.pop(index)
            self.removeTab(index)
            if not self.data:
                # editortabwidget is empty: removing it
                # (if it's not the first editortabwidget)
                self.close_editortabwidget()
            self.emit(SIGNAL('opened_files_list_changed()'))
            self.emit(SIGNAL('refresh_analysis_results()'))
            self.__refresh_classbrowser()
            self.emit(SIGNAL('refresh_file_dependent_actions()'))
        return is_ok
    
    def close_editortabwidget(self):
        if self.data:
            self.close_all_files()
            if self.already_closed:
                # All opened files were closed and *self* is not the last
                # editortabwidget remaining --> *self* was automatically closed
                return
        removed = self.plugin.unregister_editortabwidget(self)
        if removed:
            self.close()
            
    def close(self):
        Tabs.close(self)
        self.already_closed = True # used in self.close_tabbeeditor

    def close_all_files(self):
        """Close all opened scripts"""
        while self.close_file():
            pass
        

    #------ Save
    def save_if_changed(self, cancelable=False, index=None):
        """Ask user to save file if modified"""
        if index is None:
            indexes = range(self.count())
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
            self.setCurrentIndex(index)
            finfo = self.data[index]
            if finfo.filename == self.plugin.TEMPFILE_PATH or yes_all:
                if not self.save(refresh_explorer=False):
                    return False
            elif finfo.editor.isModified():
                answer = QMessageBox.question(self,
                            self.plugin.get_widget_title(),
                            self.tr("<b>%1</b> has been modified."
                                    "<br>Do you want to save changes?") \
                                    .arg(osp.basename(finfo.filename)),
                            buttons)
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
            if not self.count():
                return
            index = self.currentIndex()
            
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
            self.__refresh_classbrowser(index)
            if refresh_explorer:
                # Refresh the explorer widget if it exists:
                self.plugin.emit(SIGNAL("refresh_explorer(QString)"),
                                 osp.dirname(finfo.filename))
            return True
        except EnvironmentError, error:
            QMessageBox.critical(self, self.tr("Save"),
                            self.tr("<b>Unable to save script '%1'</b>"
                                    "<br><br>Error message:<br>%2") \
                            .arg(osp.basename(finfo.filename)).arg(str(error)))
            return False
    
    def select_savename(self, original_filename):
        self.plugin.emit(SIGNAL('redirect_stdio(bool)'), False)
        filename = QFileDialog.getSaveFileName(self,
                                           self.tr("Save Python script"),
                                           original_filename,
                                           self.plugin.get_filetype_filters())
        self.plugin.emit(SIGNAL('redirect_stdio(bool)'), True)
        if filename:
            return osp.normpath(unicode(filename))
    
    def save_as(self):
        """Save file as..."""
        index = self.currentIndex()
        finfo = self.data[index]
        filename = self.select_savename(finfo.filename)
        if filename:
            finfo.filename = filename
            self.save(index=index, force=True)
            self.setTabToolTip(index, filename)
            self.refresh(index)
        
    def save_all(self):
        """Save all opened files"""
        folders = set()
        for index in range(self.count()):
            folders.add(osp.dirname(self.data[index].filename))
            self.save(index, refresh_explorer=False)
        for folder in folders:
            self.plugin.emit(SIGNAL("refresh_explorer(QString)"), folder)
    

    #------ Update UI
    def analyze_script(self, index=None):
        """Analyze current script with pyflakes"""
        if index is None:
            index = self.currentIndex()
        if self.data:
            finfo = self.data[index]
            fname, editor = finfo.filename, finfo.editor
            if CONF.get(self.ID, 'code_analysis') and editor.is_python():
                finfo.analysis_results = check(fname)
                finfo.editor.process_code_analysis(finfo.analysis_results)
            self.emit(SIGNAL('refresh_analysis_results()'))
        
    def get_analysis_results(self):
        if self.data:
            return self.data[self.currentIndex()].analysis_results
        
    def current_changed(self, index):
        """Tab index has changed"""
        if index != -1:
            self.currentWidget().setFocus()
        else:
            self.emit(SIGNAL('reset_statusbar()'))
        self.emit(SIGNAL('opened_files_list_changed()'))
        
    def focus_changed(self):
        """Editor focus has changed"""
        fwidget = QApplication.focusWidget()
        for finfo in self.data:
            if fwidget is finfo.editor:
                self.refresh()
        
    def __refresh_classbrowser(self, index=None, update=True):
        """Refresh class browser panel"""
        if index is None:
            index = self.currentIndex()
        enable = False
        classbrowser = self.plugin.classbrowser
        if self.data:
            finfo = self.data[index]
            if CONF.get(self.ID, 'class_browser') \
               and finfo.editor.is_python() and classbrowser.isVisible():
                enable = True
                classbrowser.setEnabled(True)
                if update or finfo.editor is not classbrowser.editor:
                    classbrowser.set_editor(finfo.editor, finfo.filename)
        if not enable:
            classbrowser.setEnabled(False)
            classbrowser.clear()
            
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
            answer = QMessageBox.warning(self, self.plugin.get_widget_title(),
                            self.tr("<b>%1</b> is unavailable "
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
                        self.plugin.get_widget_title(),
                        self.tr("<b>%1</b> has been modified outside Spyder."
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
            index = self.currentIndex()
        # Set current editor
        plugin_title = self.plugin.get_widget_title()
        if self.count():
            index = self.currentIndex()
            finfo = self.data[index]
            editor = finfo.editor
            editor.setFocus()
            plugin_title += " - " + osp.abspath(finfo.filename)
            self.__refresh_classbrowser(index, update=False)
            self.emit(SIGNAL('refresh_analysis_results()'))
            self.__refresh_statusbar(index)
            self.__refresh_readonly(index)
            self.__check_file_status(index)
        else:
            editor = None
        if self.plugin.dockwidget:
            self.plugin.dockwidget.setWindowTitle(plugin_title)
        # Update the modification-state-dependent parameters
        self.modification_changed()
        # Update FindReplace binding
        self.plugin.find_widget.set_editor(editor, refresh=False)
                
    def get_title(self, filename):
        """Return tab title"""
        if filename != encoding.to_unicode(self.plugin.TEMPFILE_PATH):
            return osp.basename(filename)
        else:
            return unicode(self.tr("Temporary file"))
        
    def __get_state_index(self, state, index):
        if index is None:
            index = self.currentIndex()
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
        # This must be done before refreshing save/save all actions:
        # (otherwise Save/Save all actions will always be enabled)
        self.emit(SIGNAL('opened_files_list_changed()'))
        # --
        state, index = self.__get_state_index(state, index)
        title = self.get_full_title(state, index)
        if index is None or title is None:
            return
        self.setTabText(index, title)
        # Toggle save/save all actions state
        self.plugin.save_action.setEnabled(state)
        self.plugin.refresh_save_all_action()
        # Refreshing eol mode
        editor = self.data[index].editor
        eol_chars = editor.get_line_separator()
        self.plugin.refresh_eol_mode(eol_chars)
        

    #------ Load, reload
    def reload(self, index):
        finfo = self.data[index]
        txt, finfo.encoding = encoding.read(finfo.filename)
        finfo.lastmodified = QFileInfo(finfo.filename).lastModified()
        line, index = finfo.editor.getCursorPosition()
        finfo.editor.set_text(txt)
        finfo.editor.setModified(False)
        finfo.editor.setCursorPosition(line, index)
        
    def create_new_editor(self, fname, enc, txt, new=False):
        """Create a new editor instance"""
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
        self.data.append( TabInfo(fname, enc, editor, new) )
        editor.set_text(txt)
        editor.setup_editor(linenumbers=True, language=language,
                            code_analysis=CONF.get(self.ID, 'code_analysis'),
                            code_folding=CONF.get(self.ID, 'code_folding'),
                            show_eol_chars=CONF.get(self.ID, 'show_eol_chars'),
                            show_whitespace=CONF.get(self.ID, 'show_whitespace'),
                            font=get_font('editor'),
                            wrap=CONF.get(self.ID, 'wrap'),
                            tab_mode=CONF.get(self.ID, 'tab_always_indent'))
        self.connect(editor, SIGNAL('cursorPositionChanged(int,int)'),
                     self.cursor_position_changed_callback)
        self.connect(editor, SIGNAL('modificationChanged(bool)'),
                     self.modification_changed)
        self.connect(editor, SIGNAL("focus_in()"), self.focus_changed)
        self.connect(editor, SIGNAL("focus_changed()"),
                     self.focus_changed_callback)

        title = self.get_title(fname)
        index = self.addTab(editor, title)
        self.setTabToolTip(index, fname)
        self.setTabIcon(index, get_filetype_icon(fname))
        
        self.plugin.find_widget.set_editor(editor)
       
        self.emit(SIGNAL('refresh_file_dependent_actions()'))
        self.modification_changed()
        
        self.setCurrentIndex(index)
        
        editor.setFocus()
        
        return editor
        
    def load(self, filename):
        """Load filename, create an editor instance and return it"""
        self.plugin.starting_long_process(self.tr("Loading %1...").arg(filename))
        text, enc = encoding.read(filename)
        editor = self.create_new_editor(filename, enc, text)
        index = self.currentIndex()
        self.analyze_script(index)
        self.__refresh_classbrowser(index)
        self.plugin.ending_long_process()
        if self.isVisible() and CONF.get(self.ID, 'check_eol_chars') \
           and sourcecode.has_mixed_eol_chars(text):
            name = osp.basename(filename)
            answer = QMessageBox.warning(self, self.plugin.get_widget_title(),
                            self.tr("<b>%1</b> contains mixed end-of-line "
                                    "characters.<br>Do you want to fix this "
                                    "automatically?"
                                    ).arg(name),
                            QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.Yes:
                self.set_os_eol_chars(index)
                self.convert_eol_chars(index)
        return editor
    
    def set_os_eol_chars(self, index=None):
        if index is None:
            index = self.currentIndex()
        finfo = self.data[index]
        finfo.editor.set_eol_mode(sourcecode.get_eol_chars_from_os_name(os.name))
    
    def convert_eol_chars(self, index=None):
        """Convert end-of-line characters"""
        if index is None:
            index = self.currentIndex()
        finfo = self.data[index]
        finfo.editor.convert_eol_chars()
        
    def remove_trailing_spaces(self, index=None):
        """Remove trailing spaces"""
        if index is None:
            index = self.currentIndex()
        finfo = self.data[index]
        finfo.editor.remove_trailing_spaces()
        
    def fix_indentation(self, index=None):
        """Replace tabs by spaces"""
        if index is None:
            index = self.currentIndex()
        finfo = self.data[index]
        finfo.editor.fix_indentation()

    #------ Run
    def __process_lines(self):
        editor = self.currentWidget()
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
        self.interactive_console.shell.execute_lines(lines)
        self.interactive_console.shell.setFocus()

    def __run_in_external_console(self, lines):
        self.plugin.emit(SIGNAL('external_console_execute_lines(QString)'),
                         lines)
    
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
        editor = self.currentWidget()
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
        if source.hasUrls() or source.hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """Reimplement Qt method
        Unpack dropped data and handle it"""
        source = event.mimeData()
        if source.hasUrls():
            files = mimedata2url(source)
            if files:
                self.plugin.load(files)
        elif source.hasText():
            editor = self.currentWidget()
            if editor is not None:
                editor.insert_text( source.text() )
        event.acceptProposedAction()


#TODO: Transform EditorSplitter into a real generic splittable editor
# -> i.e. all QSplitter widgets must be of the same kind
#    (currently there are editortabwidgets and editorsplitters at the same level)
class EditorSplitter(QSplitter):
    def __init__(self, parent, actions, first=False):
        QSplitter.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setChildrenCollapsible(False)
        self.plugin = parent
        self.tab_actions = actions
        self.editortabwidget = EditorTabWidget(self.plugin, actions)
        if not first:
            self.plugin.new(self.editortabwidget)
        self.connect(self.editortabwidget, SIGNAL("destroyed(QObject*)"),
                     self.editortabwidget_closed)
        self.connect(self.editortabwidget, SIGNAL("split_vertically()"),
                     lambda: self.split(orientation=Qt.Vertical))
        self.connect(self.editortabwidget, SIGNAL("split_horizontally()"),
                     lambda: self.split(orientation=Qt.Horizontal))
        self.addWidget(self.editortabwidget)
        
    def __give_focus_to_remaining_editor(self):
        focus_widget = self.plugin.get_focus_widget()
        if focus_widget is not None:
            focus_widget.setFocus()
        
    def editortabwidget_closed(self):
        self.editortabwidget = None
        if self.count() == 1:
            # editortabwidget just closed was the last widget in this QSplitter
            self.close()
            return
        self.__give_focus_to_remaining_editor()
        
    def editorsplitter_closed(self, obj):
        if self.count() == 1 and self.editortabwidget is None:
            # editorsplitter just closed was the last widget in this QSplitter
            self.close()
            return
        elif self.count() == 2 and self.editortabwidget:
            # back to the initial state: a single editortabwidget instance,
            # as a single widget in this QSplitter: orientation may be changed
            self.editortabwidget.reset_orientation()
        self.__give_focus_to_remaining_editor()
        
    def split(self, orientation=Qt.Vertical):
        self.setOrientation(orientation)
        self.editortabwidget.set_orientation(orientation)
        editorsplitter = EditorSplitter(self.plugin, self.tab_actions)
        self.addWidget(editorsplitter)
        self.connect(editorsplitter, SIGNAL("destroyed(QObject*)"),
                     self.editorsplitter_closed)


#===============================================================================
# Status bar widgets
#===============================================================================
class _ReadWriteStatus(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)
        
        font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(translate("Editor", "Permissions:")))
        self.readwrite = QLabel()
        self.readwrite.setFont(font)
        layout.addWidget(self.readwrite)
        layout.addSpacing(10)
        self.setLayout(layout)
        
        statusbar.addPermanentWidget(self)
        self.hide()
        
    def readonly_changed(self, readonly):
        readwrite = "R" if readonly else "RW"
        self.readwrite.setText(readwrite.ljust(3))
        self.show()

class _EncodingStatus(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)
        
        font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(translate("Editor", "Encoding:")))
        self.encoding = QLabel()
        self.encoding.setFont(font)
        layout.addWidget(self.encoding)
        layout.addSpacing(10)
        self.setLayout(layout)
        
        statusbar.addPermanentWidget(self)
        self.hide()
        
    def encoding_changed(self, encoding):
        self.encoding.setText(str(encoding).upper().ljust(15))
        self.show()

class _CursorPositionStatus(QWidget):
    def __init__(self, parent, statusbar):
        QWidget.__init__(self, parent)
        
        font = get_font('editor')
        font.setPointSize(self.font().pointSize())
        font.setBold(True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(translate("Editor", "Line:")))
        self.line = QLabel()
        self.line.setFont(font)
        layout.addWidget(self.line)
        layout.addWidget(QLabel(translate("Editor", "Column:")))
        self.column = QLabel()
        self.column.setFont(font)
        layout.addWidget(self.column)
        self.setLayout(layout)
        
        statusbar.addPermanentWidget(self)
        self.hide()
        
    def cursor_position_changed(self, line, index):
        self.line.setText("%-6d" % (line+1))
        self.column.setText("%-4d" % (index+1))
        self.show()
        

class Editor(PluginWidget):
    """
    Multi-file Editor widget
    """
    ID = 'editor'
    TEMPFILE_PATH = get_conf_path('.temp.py')
    TEMPLATE_PATH = get_conf_path('template.py')
    def __init__(self, parent, ignore_last_opened_files=False):
        # Creating template if it doesn't already exist
        if not osp.isfile(self.TEMPLATE_PATH):
            header = ['# -*- coding: utf-8 -*-', '"""', 'Created on %(date)s',
                      '', '@author: %(username)s', '"""', '']
            encoding.write(os.linesep.join(header), self.TEMPLATE_PATH, 'utf-8')
        
        self.file_dependent_actions = []
        self.pythonfile_dependent_actions = []
        self.dock_toolbar_actions = None
        self.file_toolbar_actions = None
        self.analysis_toolbar_actions = None
        self.run_toolbar_actions = None
        self.edit_toolbar_actions = None
        PluginWidget.__init__(self, parent)
        
        statusbar = self.main.statusBar()
        self.readwrite_status = _ReadWriteStatus(self, statusbar)
        self.encoding_status = _EncodingStatus(self, statusbar)
        self.cursorpos_status = _CursorPositionStatus(self, statusbar)
        
        layout = QVBoxLayout()
        self.dock_toolbar = QToolBar(self)
        add_actions(self.dock_toolbar, self.dock_toolbar_actions)
        layout.addWidget(self.dock_toolbar)
        
        # Class browser
        self.classbrowser = ClassBrowser(self)
        self.classbrowser.setVisible( CONF.get(self.ID, 'class_browser') )
        self.connect(self.classbrowser, SIGNAL('go_to_line(int)'),
                     self.go_to_line)
        
        # Opened files listwidget
        self.openedfileslistwidget = QListWidget(self)
        self.connect(self.openedfileslistwidget,
                     SIGNAL('itemActivated(QListWidgetItem*)'),
                     self.openedfileslistwidget_clicked)
        
        # Analysis results listwidget
        self.analysislistwidget = QListWidget(self)
        self.analysislistwidget.setWordWrap(True)
        self.connect(self.analysislistwidget,
                     SIGNAL('itemActivated(QListWidgetItem*)'),
                     self.analysislistwidget_clicked)
        
        # Right panel toolbox
        self.toolbox = QToolBox(self)
        self.toolbox.addItem(self.classbrowser, get_icon('class_browser.png'),
                             translate("ClassBrowser", "Classes and functions"))
        self.toolbox.addItem(self.openedfileslistwidget,
                             get_icon('opened_files.png'),
                             self.tr('Opened files'))
        self.toolbox.addItem(self.analysislistwidget,
                             get_icon('analysis_results.png'),
                             self.tr('Code analysis'))
        #TODO: New toolbox item: template list
        self.connect(self.toolbox, SIGNAL('currentChanged(int)'),
                     self.toolbox_current_changed)
        
        self.editortabwidgets = []
        
        # Tabbed editor widget + Find/Replace widget
        editor_widgets = QWidget(self)
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_widgets.setLayout(editor_layout)
        editor_layout.addWidget(EditorSplitter(self, self.tab_actions,
                                               first=True))
        self.find_widget = FindReplace(self, enable_replace=True)
        self.find_widget.hide()
        editor_layout.addWidget(self.find_widget)

        # Splitter: editor widgets (see above) + toolboxes (class browser, ...)
        self.splitter = QSplitter(self)
        self.splitter.addWidget(editor_widgets)
        self.splitter.addWidget(self.toolbox)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        
        # Editor's splitter state
        state = CONF.get('editor', 'splitter_state', None)
        if state is not None:
            self.splitter.restoreState( QByteArray().fromHex(str(state)) )
        
        toolbox_state = CONF.get(self.ID, 'toolbox_panel')
        self.toolbox_action.setChecked(toolbox_state)
        self.toolbox.setVisible(toolbox_state)
        
        self.recent_files = CONF.get(self.ID, 'recent_files', [])
        
        self.untitled_num = 0
        
        filenames = CONF.get(self.ID, 'filenames', [])
        currentlines = CONF.get(self.ID, 'currentlines', [])
        if filenames and not ignore_last_opened_files:
            self.load(filenames, goto=currentlines, highlight=False)
            self.set_current_filename(CONF.get(self.ID, 'current_filename', ''))
        else:
            self.__load_temp_file()
        
        self.last_focus_editortabwidget = None
        self.connect(self, SIGNAL("focus_changed()"),
                     self.save_focus_editortabwidget)
        
        self.filetypes = ((self.tr("Python files"), ('.py', '.pyw')),
                          (self.tr("Pyrex files"), ('.pyx',)),
                          (self.tr("C files"), ('.c', '.h')),
                          (self.tr("C++ files"), ('.cc', '.cpp', '.h', '.cxx',
                                                  '.hpp', '.hh')),
                          (self.tr("Fortran files"),
                           ('.f', '.for', '.f90', '.f95', '.f2k')),
                          (self.tr("Patch and diff files"),
                           ('.patch', '.diff', '.rej')),
                          (self.tr("Batch files"),
                           ('.bat', '.cmd')),
                          (self.tr("Text files"), ('.txt',)),
                          (self.tr("Web page files"),
                           ('.css', '.htm', '.html',)),
                          (self.tr("Configuration files"),
                           ('.properties', '.session', '.ini', '.inf',
                            '.reg', '.cfg')),
                          (self.tr("All files"), ('.*',)))
        
        # Parameters of last file execution:
        self.__last_ic_exec = None # interactive console
        self.__last_ec_exec = None # external console
            
            
    #------ Plugin API
    def get_widget_title(self):
        """Return widget title"""
        return self.tr('Editor')
    
    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.get_current_editor()

    def visibility_changed(self, enable):
        """DockWidget visibility has changed"""
        PluginWidget.visibility_changed(self, enable)
        if self.dockwidget.isWindow():
            self.dock_toolbar.show()
        else:
            self.dock_toolbar.hide()
        if enable:
            self.refresh()
    
    def refresh(self):
        """Refresh editor plugin"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.refresh()
        self.refresh_save_all_action()
        
    def closing(self, cancelable=False):
        """Perform actions before parent main window is closed"""
        state = self.splitter.saveState()
        CONF.set('editor', 'splitter_state', str(state.toHex()))
        filenames = []
        currentlines = []
        for editortabwidget in self.editortabwidgets:
            filenames += [finfo.filename for finfo in editortabwidget.data]
            currentlines += [finfo.editor.get_cursor_line_number()
                             for finfo in editortabwidget.data]
        CONF.set(self.ID, 'filenames', filenames)
        CONF.set(self.ID, 'currentlines', currentlines)
        CONF.set(self.ID, 'current_filename', self.get_current_filename())
        CONF.set(self.ID, 'recent_files', self.recent_files)
        is_ok = True
        for editortabwidget in self.editortabwidgets:
            is_ok = is_ok and editortabwidget.save_if_changed(cancelable)
            if not is_ok and cancelable:
                break
        return is_ok

    def set_actions(self):
        """Setup actions"""
        self.new_action = create_action(self, self.tr("New..."), "Ctrl+N",
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
            "Ctrl+Alt+W", 'filecloseall.png',
            self.tr("Close all opened files"),
            triggered = self.close_all_files)
        run_action = create_action(self,
            self.tr("&Run in interactive console"), "F9", 'run.png',
            self.tr("Run current script in interactive console"),
            triggered=self.run_script)
        re_run_action = create_action(self,
            self.tr("Re-run last script"), "Ctrl+Alt+F9", 'run.png',
            self.tr("Run last script in interactive console"),
            triggered=self.re_run_intconsole)
        run_interact_action = create_action(self,
            self.tr("Run and &interact"), "Shift+F9", 'run_interact.png',
            self.tr("Run current script in interactive console "
                    "and set focus to shell"),
            triggered=self.run_script_and_interact)
        run_selected_action = create_action(self,
            self.tr("Run selection or current block"), "Ctrl+F9",
            'run_selection.png',
            self.tr("Run selected text in interactive console\n"
                    "(or run current block of lines and go to next block "
                    "if there is no selection)"),
            triggered=lambda: self.run_selection_or_block(external=False))
        run_process_action = create_action(self,
            self.tr("Run in e&xternal console"), "F5", 'run_external.png',
            self.tr("Run current script in external console"
                    "\n(external console is executed in a separate process)"),
            triggered=lambda: self.run_script_extconsole())
        re_run_process_action = create_action(self,
            self.tr("Re-run last script"), "Ctrl+Alt+F5", 'run_external.png',
            self.tr("Run last script in external console"),
            triggered=self.re_run_extconsole)
        run_process_interact_action = create_action(self,
            self.tr("Run and interact"), "Shift+F5", 'run_external.png',
            tip=self.tr("Run current script in external console and interact "
                        "\nwith Python interpreter when program has finished"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.run_script_extconsole(interact=True))
        run_selected_extconsole_action = create_action(self,
            self.tr("Run &selection or current block"), "Ctrl+F5",
            'run_external.png',
            tip=self.tr("Run selected text in external console\n"
                    "(or run current block of lines and go to next block "
                    "if there is no selection)"),
            triggered=lambda: self.run_selection_or_block(external=True))
        run_process_args_actionn = create_action(self,
            self.tr("Run with arguments"), "Alt+F5", 'run_external.png',
            tip=self.tr("Run current script in external console specifying "
                        "command line arguments"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.run_script_extconsole( \
                                           ask_for_arguments=True))
        run_process_debug_action = create_action(self,
            self.tr("Debug"), "Ctrl+Shift+F5", 'run_external.png',
            tip=self.tr("Debug current script in external console"
                        "\n(external console is executed in a "
                        "separate process)"),
            triggered=lambda: self.run_script_extconsole( \
                                           ask_for_arguments=True, debug=True))
        
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
        # The following action shortcuts are hard-coded in QsciEditor
        # keyPressEvent handler (the shortcut is here only to inform user):
        # (window_context=False -> disable shortcut for other widgets)
        self.indent_action = create_action(self, self.tr("Indent"), "Tab",
            'indent.png', self.tr("Indent current line or selection"),
            triggered=self.indent, window_context=False)
        self.unindent_action = create_action(self, self.tr("Unindent"),
            "Shift+Tab",
            'unindent.png', self.tr("Unindent current line or selection"),
            triggered=self.unindent, window_context=False)
        # ----------------------------------------------------------------------
        
        pylint_action = create_action(self, self.tr("Run pylint code analysis"),
                                      "F7", triggered=self.run_pylint)
        pylint_action.setEnabled(is_pylint_installed())
        
        convert_eol_action = create_action(self,
                           self.tr("Convert end-of-line characters"),
                           triggered=self.convert_eol_chars)
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
        eol_menu = QMenu(self.tr("End-of-line characters"), self)
        add_actions(eol_menu, eol_actions)
        
        trailingspaces_action = create_action(self,
                                      self.tr("Remove trailing spaces"),
                                      triggered=self.remove_trailing_spaces)
        fixindentation_action = create_action(self, self.tr("Fix indentation"),
                      tip=self.tr("Replace tab characters by space characters"),
                      triggered=self.fix_indentation)
        
        pylint_action.setEnabled(is_pylint_installed())

        template_action = create_action(self, self.tr("Edit template for "
                                                      "new modules"),
                                        triggered=self.edit_template)
        
        font_action = create_action(self, self.tr("&Font..."), None,
            'font.png', self.tr("Set text and margin font style"),
            triggered=self.change_font)
        analyze_action = create_action(self,
            self.tr("Code analysis (pyflakes)"),
            toggled=self.toggle_code_analysis,
            tip=self.tr("If enabled, Python source code will be analyzed "
                        "using pyflakes, lines containing errors or "
                        "warnings will be highlighted"))
        analyze_action.setChecked( CONF.get(self.ID, 'code_analysis') )
        fold_action = create_action(self, self.tr("Code folding"),
                                    toggled=self.toggle_code_folding)
        fold_action.setChecked( CONF.get(self.ID, 'code_folding') )
        checkeol_action = create_action(self,
            self.tr("Always check end-of-line characters"),
            toggled=lambda checked: self.emit(SIGNAL('option_changed'),
                                              'check_eol_chars', checked))
        checkeol_action.setChecked( CONF.get(self.ID, 'check_eol_chars') )
        showeol_action = create_action(self,
                                       self.tr("Show end-of-line characters"),
                                       toggled=self.toggle_show_eol_chars)
        showeol_action.setChecked( CONF.get(self.ID, 'show_eol_chars') )
        showws_action = create_action(self, self.tr("Show whitespace"),
                                      toggled=self.toggle_show_whitespace)
        showws_action.setChecked( CONF.get(self.ID, 'show_whitespace') )
        wrap_action = create_action(self, self.tr("Wrap lines"),
                                    toggled=self.toggle_wrap_mode)
        wrap_action.setChecked( CONF.get(self.ID, 'wrap') )
        tab_action = create_action(self, self.tr("Tab always indent"),
            toggled=self.toggle_tab_mode,
            tip=self.tr("If enabled, pressing Tab will always indent, "
                        "even when the cursor is not at the beginning "
                        "of a line"))
        tab_action.setChecked( CONF.get(self.ID, 'tab_always_indent') )
        workdir_action = create_action(self, self.tr("Set working directory"),
            tip=self.tr("Change working directory to current script directory"),
            triggered=self.__set_workdir)

        self.toolbox_action = create_action(self,
            self.tr("Lateral panel"), None, 'toolbox.png',
            tip=self.tr("Editor lateral panel (class browser, "
                        "opened file list, ...)"),
            toggled=self.toggle_toolbox)
                
        self.max_recent_action = create_action(self,
            self.tr("Maximum number of recent files..."),
            triggered=self.change_max_recent_files)
        self.clear_recent_action = create_action(self,
            self.tr("Clear this list"), tip=self.tr("Clear recent files list"),
            triggered=self.clear_recent_files)
        self.recent_file_menu = QMenu(self.tr("Open &recent"), self)
        self.connect(self.recent_file_menu, SIGNAL("aboutToShow()"),
                     self.update_recent_file_menu)

        self.file_menu_actions = [self.new_action, self.open_action,
                                  self.recent_file_menu,
                                  self.save_action, self.save_all_action,
                                  save_as_action, None,
                                  print_preview_action, print_action, None,
                                  self.close_action,
                                  self.close_all_action, None]
        
        option_menu = QMenu(self.tr("Code source editor settings"), self)
        option_menu.setIcon(get_icon('tooloptions.png'))
        add_actions(option_menu, (template_action, font_action, wrap_action,
                                  tab_action, fold_action, checkeol_action,
                                  showeol_action, showws_action,
                                  analyze_action, self.toolbox_action))
        
        source_menu_actions = (self.comment_action, self.uncomment_action,
                blockcomment_action, unblockcomment_action,
                self.indent_action, self.unindent_action,
                None, run_action, re_run_action, run_interact_action,
                run_selected_action, None, run_process_action,
                re_run_process_action, run_process_interact_action,
                run_selected_extconsole_action,
                run_process_args_actionn,
                run_process_debug_action, None,
                pylint_action, convert_eol_action, eol_menu,
                trailingspaces_action, fixindentation_action, None, option_menu)
        self.file_toolbar_actions = [self.new_action, self.open_action,
                self.save_action, self.save_all_action, print_action]
        self.analysis_toolbar_actions = [self.previous_warning_action,
                self.next_warning_action, self.toolbox_action]
        self.run_toolbar_actions = [run_action, run_interact_action,
                run_selected_action, None, run_process_action]
        self.edit_toolbar_actions = [self.comment_action, self.uncomment_action,
                self.indent_action, self.unindent_action]
        self.dock_toolbar_actions = self.file_toolbar_actions + [None] + \
                                    self.analysis_toolbar_actions + [None] + \
                                    self.run_toolbar_actions + [None] + \
                                    self.edit_toolbar_actions
        self.pythonfile_dependent_actions = (run_action, re_run_action,
                run_interact_action, run_selected_action, run_process_action,
                re_run_process_action, run_process_interact_action,
                run_process_args_actionn, run_process_debug_action,
                blockcomment_action, unblockcomment_action, pylint_action,
                )
        self.file_dependent_actions = self.pythonfile_dependent_actions + \
                (self.save_action, save_as_action,
                 print_preview_action, print_action,
                 self.save_all_action, workdir_action, self.close_action,
                 self.close_all_action,
                 self.comment_action, self.uncomment_action,
                 self.indent_action, self.unindent_action)
        self.tab_actions = (self.save_action, save_as_action, print_action,
                run_action, run_process_action,
                workdir_action, self.close_action)
        return (source_menu_actions, self.dock_toolbar_actions)        
        
        
    #------ Focus tabwidget
    def __get_focus_editortabwidget(self):
        fwidget = QApplication.focusWidget()
        if isinstance(fwidget, QsciEditor):
            for editortabwidget in self.editortabwidgets:
                if fwidget is editortabwidget.currentWidget():
                    return editortabwidget
        elif isinstance(fwidget, EditorTabWidget):
            return fwidget
        
    def save_focus_editortabwidget(self):
        editortabwidget = self.__get_focus_editortabwidget()
        if editortabwidget is not None:
            self.last_focus_editortabwidget = editortabwidget
    
        
    #------ Handling editortabwidgets
    def register_editortabwidget(self, editortabwidget):
        self.editortabwidgets.append(editortabwidget)
        self.last_focus_editortabwidget = editortabwidget
        self.connect(editortabwidget, SIGNAL('reset_statusbar()'),
                     self.readwrite_status.hide)
        self.connect(editortabwidget, SIGNAL('reset_statusbar()'),
                     self.encoding_status.hide)
        self.connect(editortabwidget, SIGNAL('reset_statusbar()'),
                     self.cursorpos_status.hide)
        self.connect(editortabwidget, SIGNAL('readonly_changed(bool)'),
                     self.readwrite_status.readonly_changed)
        self.connect(editortabwidget, SIGNAL('encoding_changed(QString)'),
                     self.encoding_status.encoding_changed)
        self.connect(editortabwidget, SIGNAL('cursorPositionChanged(int,int)'),
                     self.cursorpos_status.cursor_position_changed)
        self.connect(editortabwidget, SIGNAL('opened_files_list_changed()'),
                     self.opened_files_list_changed)
        self.connect(editortabwidget, SIGNAL('refresh_analysis_results()'),
                     self.refresh_analysislistwidget)
        self.connect(editortabwidget,
                     SIGNAL('refresh_file_dependent_actions()'),
                     self.refresh_file_dependent_actions)
        self.connect(editortabwidget, SIGNAL('move_tab(long,long,int,int)'),
                     self.move_tabs_between_editortabwidgets)
        
    def unregister_editortabwidget(self, editortabwidget):
        """Removing editortabwidget only if it's not the last remaining"""
        if len(self.editortabwidgets) > 1:
            index = self.editortabwidgets.index(editortabwidget)
            self.editortabwidgets.pop(index)
            editortabwidget.close() # remove widget from splitter
            return True
        else:
            # Tabbededitor was not removed!
            return False
        
    def __get_editortabwidget_from_id(self, t_id):
        for editortabwidget in self.editortabwidgets:
            if id(editortabwidget) == t_id:
                return editortabwidget
        
    def move_tabs_between_editortabwidgets(self, id_from, id_to,
                                           index_from, index_to):
        """
        Move tab between tabwidgets
        (see editortabwidget.move_data when moving tabs inside one tabwidget)
        Tabs haven't been moved yet since tabwidgets don't have any
        reference towards other tabwidget instances
        """
        tw_from = self.__get_editortabwidget_from_id(id_from)
        tw_to = self.__get_editortabwidget_from_id(id_to)

        tw_from.move_data(index_from, index_to, tw_to)

        tip, text = tw_from.tabToolTip(index_from), tw_from.tabText(index_from)
        icon, widget = tw_from.tabIcon(index_from), tw_from.widget(index_from)
        
        tw_from.removeTab(index_from)
        tw_to.insertTab(index_to, widget, icon, text)
        tw_to.setTabToolTip(index_to, tip)
        
        tw_to.setCurrentIndex(index_to)
        
        if tw_from.count() == 0:
            tw_from.close_editortabwidget
        
        
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
        filenames = []
        for editortabwidget in self.editortabwidgets:
            filenames += [finfo.filename for finfo in editortabwidget.data]
        return filenames

    def get_editortabwidget_index(self, filename):
        for editortabwidget in self.editortabwidgets:
            index = editortabwidget.has_filename(filename)
            if index is not None:
                return (editortabwidget, index)
        else:
            return (None, None)

    def get_current_editortabwidget(self):
        if len(self.editortabwidgets) == 1:
            return self.editortabwidgets[0]
        else:
            editortabwidget = self.__get_focus_editortabwidget()
            if editortabwidget is None:
                return self.last_focus_editortabwidget
            else:
                return editortabwidget
        
    def get_current_editor(self):
        editortabwidget = self.get_current_editortabwidget()
        if editortabwidget is not None:
            return editortabwidget.currentWidget()
        
    def get_current_filename(self):
        editortabwidget = self.get_current_editortabwidget()
        if editortabwidget is not None:
            return editortabwidget.get_current_filename()
        
    def is_file_opened(self, filename=None):
        if filename is None:
            # Is there any file opened?
            return self.get_current_editor() is not None
        else:
            editortabwidget, _index = self.get_editortabwidget_index(filename)
            return editortabwidget
        
    def set_current_filename(self, filename):
        """Set focus to *filename* if this file has been opened
        Return the editor instance associated to *filename*"""
        editortabwidget, _index = self.get_editortabwidget_index(filename)
        if editortabwidget is not None:
            return editortabwidget.set_current_filename(filename)
    
    
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
        for editortabwidget in self.editortabwidgets:
            if editortabwidget.count() > 1:
                state = state or any([finfo.editor.isModified() for finfo \
                                      in editortabwidget.data])
        self.save_all_action.setEnabled(state)
            
    def refresh_analysislistwidget(self):
        """Refresh analysislistwidget *and* analysis navigation buttons"""
        editortabwidget = self.get_current_editortabwidget()
        check_results = editortabwidget.get_analysis_results()
        state = CONF.get(self.ID, 'code_analysis') \
                and check_results is not None and len(check_results)
        self.previous_warning_action.setEnabled(state)
        self.next_warning_action.setEnabled(state)
        if self.analysislistwidget.isHidden():
            return
        self.analysislistwidget.clear()
        self.analysislistwidget.setEnabled(state and check_results is not None)
        if state and check_results:
            for message, line0, error in check_results:
                icon = get_icon('error.png' if error else 'warning.png')
                item = QListWidgetItem(icon, message[:1].upper() + message[1:],
                                       self.analysislistwidget)
                item.setData(Qt.UserRole, QVariant(line0-1))
            
    def refresh_openedfileslistwidget(self):
        if self.openedfileslistwidget.isHidden():
            return
        filenames = self.get_filenames()
        current_filename = self.get_current_filename()
        self.openedfileslistwidget.clear()
        for filename in filenames:
            editortabwidget, index = self.get_editortabwidget_index(filename)
            title = editortabwidget.get_full_title(index=index)
            item = QListWidgetItem(get_filetype_icon(filename),
                                   title, self.openedfileslistwidget)
            item.setData(Qt.UserRole, QVariant(filename))
            if filename == current_filename:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.openedfileslistwidget.addItem(item)
            
    def refresh_eol_mode(self, eol_chars):
        os_name = sourcecode.get_os_name_from_eol_chars(eol_chars)
        if os_name == 'nt':
            self.win_eol_action.setChecked(True)
        elif os_name == 'posix':
            self.linux_eol_action.setChecked(True)
        else:
            self.mac_eol_action.setChecked(True)
    
    
    #------ Slots
    def toolbox_current_changed(self, index=None):
        """Toolbox current index has changed"""
        if self.openedfileslistwidget.isVisible():
            self.refresh_openedfileslistwidget()
        elif self.classbrowser.isVisible():
            # Refreshing class browser
            editortabwidget = self.get_current_editortabwidget()
            editortabwidget.refresh()
        elif self.analysislistwidget.isVisible():
            self.refresh_analysislistwidget()

    def openedfileslistwidget_clicked(self, item):
        filename = unicode(item.data(Qt.UserRole).toString())
        editortabwidget, index = self.get_editortabwidget_index(filename)
        editortabwidget.data[index].editor.setFocus()
        editortabwidget.setCurrentIndex(index)
    
    def analysislistwidget_clicked(self, item):
        line, _ok = item.data(Qt.UserRole).toInt()
        self.get_current_editor().highlight_line(line+1)
    
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
                action.setEnabled(enable)
        # Refresh openedfileslistwidget:
        self.refresh_openedfileslistwidget()
        
                
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
            if len(self.recent_files) > CONF.get(self.ID, 'max_recent_files'):
                self.recent_files.pop(-1)
    
    def new(self, editortabwidget=None):
        """Create a new file - Untitled"""
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
        while True:
            fname = create_fname(self.untitled_num)
            self.untitled_num += 1
            if not osp.isfile(fname):
                break
        # Creating editor widget
        if editortabwidget is None:
            editortabwidget = self.get_current_editortabwidget()
        editor = editortabwidget.create_new_editor(fname, enc, text, new=True)
        editor.set_cursor_position('eof')
        editor.insert_text(os.linesep)
        
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
        mrf, valid = QInputDialog.getInteger(self, self.tr('Editor'),
                               self.tr('Maximum number of recent files'),
                               CONF.get(self.ID, 'max_recent_files'), 1, 100)
        if valid:
            CONF.set(self.ID, 'max_recent_files', mrf)
        
    def load(self, filenames=None, goto=None, highlight=False):
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
            filenames = QFileDialog.getOpenFileNames(self,
                          self.tr("Open Python script"), basedir,
                          self.get_filetype_filters())
            self.emit(SIGNAL('redirect_stdio(bool)'), True)
            filenames = list(filenames)
            if len(filenames):
#                directory = osp.dirname(unicode(filenames[-1]))
#                self.emit(SIGNAL("open_dir(QString)"), directory)
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
        if goto is None:
            goto = [0]*len(filenames)
            
        for index, filename in enumerate(filenames):
            # -- Do not open an already opened file
            editor = self.set_current_filename(filename)
            if editor is None:
                # -- Not a valid filename:
                if not osp.isfile(filename):
                    continue
                # --
                editortabwidget = self.get_current_editortabwidget()
                editor = editortabwidget.load(filename)
                self.__add_recent_file(filename)
            if highlight:
                editor.highlight_line(goto[index])
            else:
                editor.go_to_line(goto[index])
            QApplication.processEvents()

    def print_file(self):
        """Print current file"""
        editor = self.get_current_editor()
        filename = self.get_current_filename()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=get_font('editor', 'printer_header'))
        printDialog = QPrintDialog(printer, self)
        if editor.hasSelectedText():
            printDialog.addEnabledOption(QAbstractPrintDialog.PrintSelection)
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        answer = printDialog.exec_()
        self.emit(SIGNAL('redirect_stdio(bool)'), True)
        if answer == QDialog.Accepted:
            self.starting_long_process(self.tr("Printing..."))
            printer.setDocName(filename)
            if printDialog.printRange() == QAbstractPrintDialog.Selection:
                from_line, _index, to_line, to_index = editor.getSelection()
                if to_index == 0:
                    to_line -= 1
                ok = printer.printRange(editor, from_line, to_line-1)
            else:
                ok = printer.printRange(editor)
            self.ending_long_process()
            if not ok:
                QMessageBox.critical(self, self.tr("Print"),
                            self.tr("<b>Unable to print document '%1'</b>") \
                            .arg(osp.basename(filename)))

    def print_preview(self):
        """Print preview for current file"""
        from PyQt4.QtGui import QPrintPreviewDialog
        editor = self.get_current_editor()
        printer = Printer(mode=QPrinter.HighResolution,
                          header_font=get_font('editor', 'printer_header'))
        preview = QPrintPreviewDialog(printer, self)
        self.connect(preview, SIGNAL("paintRequested(QPrinter*)"),
                     lambda printer: printer.printRange(editor))
        self.emit(SIGNAL('redirect_stdio(bool)'), False)
        preview.exec_()
        self.emit(SIGNAL('redirect_stdio(bool)'), True)

    def close_file(self):
        """Close current file"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.close_file()
            
    def close_all_files(self):
        """Close all opened scripts"""
        for editortabwidget in self.editortabwidgets:
            editortabwidget.close_all_files()
                
    def save(self, index=None, force=False):
        """Save file"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.save(index=index, force=force)
                
    def save_as(self):
        """Save *as* the currently edited file"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.save_as()
        self.__add_recent_file(editortabwidget.get_current_filename())
        
    def save_all(self):
        """Save all opened files"""
        for editortabwidget in self.editortabwidgets:
            editortabwidget.save_all()
    
    
    #------ Explorer widget
    def __close_and_reload(self, filename, new_filename=None):
        filename = osp.abspath(unicode(filename))
        for editortabwidget in self.editortabwidgets:
            index = editortabwidget.has_filename(filename)
            if index is not None:
                editortabwidget.close_file(index)
                if new_filename is not None:
                    self.load(unicode(new_filename))
                
    def removed(self, filename):
        """File was removed in explorer widget"""
        self.__close_and_reload(filename)
    
    def renamed(self, source, dest):
        """File was renamed in explorer widget"""
        self.__close_and_reload(source, new_filename=dest)
        
    
    #------ Source code
    def go_to_line(self, lineno):
        """Go to line lineno and highlight it"""
        self.get_current_editor().highlight_line(lineno)
    
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
        
    def convert_eol_chars(self):
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.convert_eol_chars()
    
    def toggle_eol_chars(self, os_name):
        editor = self.get_current_editor()
        editor.set_eol_mode(sourcecode.get_eol_chars_from_os_name(os_name))
        
    def remove_trailing_spaces(self):
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.remove_trailing_spaces()
        
    def fix_indentation(self):
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.fix_indentation()
        
    #------ Run Python script
    def run_script_extconsole(self, ask_for_arguments=False,
                              interact=False, debug=False):
        """Run current script in another process"""
        editortabwidget = self.get_current_editortabwidget()
        if editortabwidget.save():
            editor = self.get_current_editor()
            fname = osp.abspath(self.get_current_filename())
            wdir = osp.dirname(fname)
            self.__last_ec_exec = (fname, wdir, ask_for_arguments,
                                   interact, debug)
            self.re_run_extconsole()
            if not interact and not debug:
                # If external console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # current external shell automatically
                # (see PluginWidget.visibility_changed method)
                editor.setFocus()
                
    def re_run_extconsole(self):
        """Re-run script in external console"""
        if self.__last_ec_exec is None:
            return
        fname, wdir, ask_for_arguments, interact, debug = self.__last_ec_exec
        self.emit(SIGNAL('open_external_console(QString,QString,bool,bool,bool)'),
                  fname, wdir, ask_for_arguments, interact, debug)
    
    def run_script(self, set_focus=False):
        """Run current script"""
        editortabwidget = self.get_current_editortabwidget()
        if editortabwidget.save():
            filename = self.get_current_filename()
            editor = self.get_current_editor()
            self.__last_ic_exec = (filename, set_focus)
            self.re_run_intconsole()
            if not set_focus:
                # If interactive console dockwidget is hidden, it will be
                # raised in top-level and so focus will be given to the
                # interactive shell automatically
                # (see PluginWidget.visibility_changed method)
                editor.setFocus()
                
    def re_run_intconsole(self):
        """Re-run script in interactive console"""
        if self.__last_ic_exec is None:
            return
        filename, set_focus = self.__last_ic_exec
        self.main.console.run_script(filename, silent=True, set_focus=set_focus)
        
    def run_script_and_interact(self):
        """Run current script and set focus to shell"""
        self.run_script(set_focus=True)
        
    def run_selection_or_block(self, external=False):
        """Run selection or current line in interactive or external console"""
        editortabwidget = self.get_current_editortabwidget()
        editortabwidget.run_selection_or_block(external=external)
        
        
    #------ Options
    def change_font(self):
        """Change editor font"""
        font, valid = QFontDialog.getFont(get_font(self.ID), self,
                                          self.tr("Select a new font"))
        if valid:
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.set_font(font)
            set_font(font, self.ID)
            
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.toggle_wrap_mode(checked)
            CONF.set(self.ID, 'wrap', checked)
            
    def toggle_tab_mode(self, checked):
        """
        Toggle tab mode:
        checked = tab always indent
        (otherwise tab indents only when cursor is at the beginning of a line)
        """
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.set_tab_mode(checked)
            CONF.set(self.ID, 'tab_always_indent', checked)
            
    def toggle_code_folding(self, checked):
        """Toggle code folding"""
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.setup_margins(linenumbers=True,
                              code_folding=checked,
                              code_analysis=CONF.get(self.ID, 'code_analysis'))
                    if not checked:
                        finfo.editor.unfold_all()
            CONF.set(self.ID, 'code_folding', checked)
            
    def toggle_show_eol_chars(self, checked):
        """Toggle show EOL characters"""
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.set_eol_chars_visible(checked)
            CONF.set(self.ID, 'show_eol_chars', checked)
            
    def toggle_show_whitespace(self, checked):
        """Toggle show whitespace"""
        if hasattr(self, 'editortabwidgets'):
            for editortabwidget in self.editortabwidgets:
                for finfo in editortabwidget.data:
                    finfo.editor.set_whitespace_visible(checked)
            CONF.set(self.ID, 'show_whitespace', checked)
            
    def toggle_code_analysis(self, checked):
        """Toggle code analysis"""
        if hasattr(self, 'editortabwidgets'):
            CONF.set(self.ID, 'code_analysis', checked)
            current_editortabwidget = self.get_current_editortabwidget()
            current_index = current_editortabwidget.currentIndex()
            for editortabwidget in self.editortabwidgets:
                for index, finfo in enumerate(editortabwidget.data):
                    finfo.editor.setup_margins(linenumbers=True,
                              code_analysis=checked,
                              code_folding=CONF.get(self.ID, 'code_folding'))
                    if index != current_index:
                        editortabwidget.analyze_script(index)
            # We must update the current editor after the others:
            # (otherwise, code analysis buttons state would correspond to the
            #  last editor instead of showing the one of the current editor)
            current_editortabwidget.analyze_script()

    def toggle_toolbox(self, checked):
        """Toggle toolbox"""
        self.toolbox.setVisible(checked)
        CONF.set(self.ID, 'toolbox_panel', checked)
        self.toolbox_current_changed() # refreshing class browser (workaround)

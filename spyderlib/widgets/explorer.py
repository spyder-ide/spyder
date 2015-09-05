# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Files and Directories Explorer"""

# pylint: disable=C0103
# pylint: disable=R0903
# pylint: disable=R0911
# pylint: disable=R0201

from __future__ import with_statement

from spyderlib.qt.QtGui import (QVBoxLayout, QLabel, QHBoxLayout, QInputDialog,
                                QFileSystemModel, QMenu, QWidget, QToolButton,
                                QLineEdit, QMessageBox, QToolBar, QTreeView,
                                QDrag, QSortFilterProxyModel)
from spyderlib.qt.QtCore import (Qt, SIGNAL, QMimeData, QSize, QDir, QUrl,
                                 Signal, QTimer)
from spyderlib.qt.compat import getsavefilename, getexistingdirectory

import os
import sys
import re
import os.path as osp
import shutil

# Local imports
from spyderlib.utils.qthelpers import (get_icon, create_action, add_actions,
                                       file_uri, get_std_icon)
from spyderlib.utils import misc, encoding, programs, vcs
from spyderlib.baseconfig import _
from spyderlib.py3compat import (to_text_string, to_binary_string, getcwd,
                                 str_lower)

try:
    from IPython.nbconvert import PythonExporter as nbexporter
except:
    nbexporter = None      # analysis:ignore


def fixpath(path):
    """Normalize path fixing case, making absolute and removing symlinks"""
    norm = osp.normcase if os.name == 'nt' else osp.normpath
    return norm(osp.abspath(osp.realpath(path)))


def create_script(fname):
    """Create a new Python script"""
    text = os.linesep.join(["# -*- coding: utf-8 -*-", "", ""])
    encoding.write(to_text_string(text), fname, 'utf-8')


def listdir(path, include='.', exclude=r'\.pyc$|^\.', show_all=False,
            folders_only=False):
    """List files and directories"""
    namelist = []
    dirlist = [to_text_string(osp.pardir)]
    for item in os.listdir(to_text_string(path)):
        if re.search(exclude, item) and not show_all:
            continue
        if osp.isdir(osp.join(path, item)):
            dirlist.append(item)
        elif folders_only:
            continue
        elif re.search(include, item) or show_all:
            namelist.append(item)
    return sorted(dirlist, key=str_lower) + \
           sorted(namelist, key=str_lower)


def has_subdirectories(path, include, exclude, show_all):
    """Return True if path has subdirectories"""
    try:
        # > 1 because of '..'
        return len( listdir(path, include, exclude,
                            show_all, folders_only=True) ) > 1
    except (IOError, OSError):
        return False


class DirView(QTreeView):
    """Base file/directory tree view"""
    def __init__(self, parent=None):
        super(DirView, self).__init__(parent)
        self.name_filters = None
        self.parent_widget = parent
        self.show_all = None
        self.menu = None
        self.common_actions = None
        self.__expanded_state = None
        self._to_be_loaded = None
        self.fsmodel = None
        self.setup_fs_model()
        self._scrollbar_positions = None
                
    #---- Model
    def setup_fs_model(self):
        """Setup filesystem model"""
        filters = QDir.AllDirs | QDir.Files | QDir.Drives | QDir.NoDotAndDotDot
        self.fsmodel = QFileSystemModel(self)
        self.fsmodel.setFilter(filters)
        self.fsmodel.setNameFilterDisables(False)
        
    def install_model(self):
        """Install filesystem model"""
        self.setModel(self.fsmodel)
        
    def setup_view(self):
        """Setup view"""
        self.install_model()
        self.connect(self.fsmodel, SIGNAL('directoryLoaded(QString)'),
                     lambda: self.resizeColumnToContents(0))
        self.setAnimated(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        
    def set_name_filters(self, name_filters):
        """Set name filters"""
        self.name_filters = name_filters
        self.fsmodel.setNameFilters(name_filters)
        
    def set_show_all(self, state):
        """Toggle 'show all files' state"""
        if state:
            self.fsmodel.setNameFilters([])
        else:
            self.fsmodel.setNameFilters(self.name_filters)
            
    def get_filename(self, index):
        """Return filename associated with *index*"""
        if index:
            return osp.normpath(to_text_string(self.fsmodel.filePath(index)))
        
    def get_index(self, filename):
        """Return index associated with filename"""
        return self.fsmodel.index(filename)
        
    def get_selected_filenames(self):
        """Return selected filenames"""
        if self.selectionMode() == self.ExtendedSelection:
            return [self.get_filename(idx) for idx in self.selectedIndexes()]
        else:
            return [self.get_filename(self.currentIndex())]
            
    def get_dirname(self, index):
        """Return dirname associated with *index*"""
        fname = self.get_filename(index)
        if fname:
            if osp.isdir(fname):
                return fname
            else:
                return osp.dirname(fname)
        
    #---- Tree view widget
    def setup(self, name_filters=['*.py', '*.pyw'], show_all=False):
        """Setup tree widget"""
        self.setup_view()
        
        self.set_name_filters(name_filters)
        self.show_all = show_all
        
        # Setup context menu
        self.menu = QMenu(self)
        self.common_actions = self.setup_common_actions()
        
    #---- Context menu
    def setup_common_actions(self):
        """Setup context menu common actions"""
        # Filters
        filters_action = create_action(self, _("Edit filename filters..."),
                                       None, get_icon('filter.png'),
                                       triggered=self.edit_filter)
        # Show all files
        all_action = create_action(self, _("Show all files"),
                                   toggled=self.toggle_all)
        all_action.setChecked(self.show_all)
        self.toggle_all(self.show_all)
        
        return [filters_action, all_action]
        
    def edit_filter(self):
        """Edit name filters"""
        filters, valid = QInputDialog.getText(self, _('Edit filename filters'),
                                              _('Name filters:'),
                                              QLineEdit.Normal,
                                              ", ".join(self.name_filters))
        if valid:
            filters = [f.strip() for f in to_text_string(filters).split(',')]
            self.parent_widget.sig_option_changed.emit('name_filters', filters)
            self.set_name_filters(filters)
            
    def toggle_all(self, checked):
        """Toggle all files mode"""
        self.parent_widget.sig_option_changed.emit('show_all', checked)
        self.show_all = checked
        self.set_show_all(checked)
        
    def create_file_new_actions(self, fnames):
        """Return actions for submenu 'New...'"""
        if not fnames:
            return []
        new_file_act = create_action(self, _("File..."), icon='filenew.png',
                                     triggered=lambda:
                                     self.new_file(fnames[-1]))
        new_module_act = create_action(self, _("Module..."), icon='py.png',
                                       triggered=lambda:
                                         self.new_module(fnames[-1]))
        new_folder_act = create_action(self, _("Folder..."),
                                       icon='folder_new.png',
                                       triggered=lambda:
                                        self.new_folder(fnames[-1]))
        new_package_act = create_action(self, _("Package..."),
                                        icon=get_icon('package_collapsed.png'),
                                        triggered=lambda:
                                         self.new_package(fnames[-1]))
        return [new_file_act, new_folder_act, None,
                new_module_act, new_package_act]
        
    def create_file_import_actions(self, fnames):
        """Return actions for submenu 'Import...'"""
        return []

    def create_file_manage_actions(self, fnames):
        """Return file management actions"""
        only_files = all([osp.isfile(_fn) for _fn in fnames])
        only_modules = all([osp.splitext(_fn)[1] in ('.py', '.pyw', '.ipy')
                            for _fn in fnames])
        only_notebooks = all([osp.splitext(_fn)[1] == '.ipynb'
                              for _fn in fnames])
        only_valid = all([encoding.is_text_file(_fn) for _fn in fnames])
        run_action = create_action(self, _("Run"), icon="run_small.png",
                                   triggered=self.run)
        edit_action = create_action(self, _("Edit"), icon="edit.png",
                                    triggered=self.clicked)
        move_action = create_action(self, _("Move..."),
                                    icon="move.png",
                                    triggered=self.move)
        delete_action = create_action(self, _("Delete..."),
                                      icon="delete.png",
                                      triggered=self.delete)
        rename_action = create_action(self, _("Rename..."),
                                      icon="rename.png",
                                      triggered=self.rename)
        open_action = create_action(self, _("Open"), triggered=self.open)
        ipynb_convert_action = create_action(self, _("Convert to Python script"),
                                             icon="python.png",
                                             triggered=self.convert)
        
        actions = []
        if only_modules:
            actions.append(run_action)
        if only_valid and only_files:
            actions.append(edit_action)
        else:
            actions.append(open_action)
        actions += [delete_action, rename_action]
        basedir = fixpath(osp.dirname(fnames[0]))
        if all([fixpath(osp.dirname(_fn)) == basedir for _fn in fnames]):
            actions.append(move_action)
        actions += [None]
        if only_notebooks and nbexporter is not None:
            actions.append(ipynb_convert_action)
        
        # VCS support is quite limited for now, so we are enabling the VCS
        # related actions only when a single file/folder is selected:
        dirname = fnames[0] if osp.isdir(fnames[0]) else osp.dirname(fnames[0])
        if len(fnames) == 1 and vcs.is_vcs_repository(dirname):
            vcs_ci = create_action(self, _("Commit"),
                                   icon="vcs_commit.png",
                                   triggered=lambda fnames=[dirname]:
                                   self.vcs_command(fnames, 'commit'))
            vcs_log = create_action(self, _("Browse repository"),
                                    icon="vcs_browse.png",
                                    triggered=lambda fnames=[dirname]:
                                    self.vcs_command(fnames, 'browse'))
            actions += [None, vcs_ci, vcs_log]
        
        return actions

    def create_folder_manage_actions(self, fnames):
        """Return folder management actions"""
        actions = []
        if os.name == 'nt':
            _title = _("Open command prompt here")
        else:
            _title = _("Open terminal here")
        action = create_action(self, _title, icon="cmdprompt.png",
                               triggered=lambda fnames=fnames:
                               self.open_terminal(fnames))
        actions.append(action)
        _title = _("Open Python console here")
        action = create_action(self, _title, icon="python.png",
                               triggered=lambda fnames=fnames:
                               self.open_interpreter(fnames))
        actions.append(action)
        return actions
        
    def create_context_menu_actions(self):
        """Create context menu actions"""
        actions = []
        fnames = self.get_selected_filenames()
        new_actions = self.create_file_new_actions(fnames)
        if len(new_actions) > 1:
            # Creating a submenu only if there is more than one entry
            new_act_menu = QMenu(_('New'), self)
            add_actions(new_act_menu, new_actions)
            actions.append(new_act_menu)
        else:
            actions += new_actions
        import_actions = self.create_file_import_actions(fnames)
        if len(import_actions) > 1:
            # Creating a submenu only if there is more than one entry
            import_act_menu = QMenu(_('Import'), self)
            add_actions(import_act_menu, import_actions)
            actions.append(import_act_menu)
        else:
            actions += import_actions
        if actions:
            actions.append(None)
        if fnames:
            actions += self.create_file_manage_actions(fnames)
        if actions:
            actions.append(None)
        if fnames and all([osp.isdir(_fn) for _fn in fnames]):
            actions += self.create_folder_manage_actions(fnames)
        if actions:
            actions.append(None)
        actions += self.common_actions
        return actions

    def update_menu(self):
        """Update context menu"""
        self.menu.clear()
        add_actions(self.menu, self.create_context_menu_actions())
    
    #---- Events
    def viewportEvent(self, event):
        """Reimplement Qt method"""

        # Prevent Qt from crashing or showing warnings like:
        # "QSortFilterProxyModel: index from wrong model passed to 
        # mapFromSource", probably due to the fact that the file system model 
        # is being built. See Issue 1250.
        #
        # This workaround was inspired by the following KDE bug:
        # https://bugs.kde.org/show_bug.cgi?id=172198
        #
        # Apparently, this is a bug from Qt itself.
        self.executeDelayedItemsLayout()
        
        return QTreeView.viewportEvent(self, event)        
                
    def contextMenuEvent(self, event):
        """Override Qt method"""
        self.update_menu()
        self.menu.popup(event.globalPos())

    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.clicked()
        elif event.key() == Qt.Key_F2:
            self.rename()
        elif event.key() == Qt.Key_Delete:
            self.delete()
        else:
            QTreeView.keyPressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        QTreeView.mouseDoubleClickEvent(self, event)
        self.clicked()
        
    def clicked(self):
        """Selected item was double-clicked or enter/return was pressed"""
        fnames = self.get_selected_filenames()
        for fname in fnames:
            if osp.isdir(fname):
                self.directory_clicked(fname)
            else:
                self.open([fname])
                
    def directory_clicked(self, dirname):
        """Directory was just clicked"""
        pass
        
    #---- Drag
    def dragEnterEvent(self, event):
        """Drag and Drop - Enter event"""
        event.setAccepted(event.mimeData().hasFormat("text/plain"))

    def dragMoveEvent(self, event):
        """Drag and Drop - Move event"""
        if (event.mimeData().hasFormat("text/plain")):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()
            
    def startDrag(self, dropActions):
        """Reimplement Qt Method - handle drag event"""
        data = QMimeData()
        data.setUrls([QUrl(fname) for fname in self.get_selected_filenames()])
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.exec_()
        
    #---- File/Directory actions
    def open(self, fnames=None):
        """Open files with the appropriate application"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for fname in fnames:
            if osp.isfile(fname) and encoding.is_text_file(fname):
                self.parent_widget.sig_open_file.emit(fname)
            else:
                self.open_outside_spyder([fname])
        
    def open_outside_spyder(self, fnames):
        """Open file outside Spyder with the appropriate application
        If this does not work, opening unknown file in Spyder, as text file"""
        for path in sorted(fnames):
            path = file_uri(path)
            ok = programs.start_file(path)
            if not ok:
                self.parent_widget.emit(SIGNAL("edit(QString)"), path)
                
    def open_terminal(self, fnames):
        """Open terminal"""
        for path in sorted(fnames):
            self.parent_widget.emit(SIGNAL("open_terminal(QString)"), path)
            
    def open_interpreter(self, fnames):
        """Open interpreter"""
        for path in sorted(fnames):
            self.parent_widget.emit(SIGNAL("open_interpreter(QString)"), path)
        
    def run(self, fnames=None):
        """Run Python scripts"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        for fname in fnames:
            self.parent_widget.emit(SIGNAL("run(QString)"), fname)
    
    def remove_tree(self, dirname):
        """Remove whole directory tree
        Reimplemented in project explorer widget"""
        shutil.rmtree(dirname, onerror=misc.onerror)
    
    def delete_file(self, fname, multiple, yes_to_all):
        """Delete file"""
        if multiple:
            buttons = QMessageBox.Yes|QMessageBox.YesAll| \
                      QMessageBox.No|QMessageBox.Cancel
        else:
            buttons = QMessageBox.Yes|QMessageBox.No
        if yes_to_all is None:
            answer = QMessageBox.warning(self, _("Delete"),
                                 _("Do you really want "
                                   "to delete <b>%s</b>?"
                                   ) % osp.basename(fname), buttons)
            if answer == QMessageBox.No:
                return yes_to_all
            elif answer == QMessageBox.Cancel:
                return False
            elif answer == QMessageBox.YesAll:
                yes_to_all = True
        try:
            if osp.isfile(fname):
                misc.remove_file(fname)
                self.parent_widget.emit(SIGNAL("removed(QString)"),
                                        fname)
            else:
                self.remove_tree(fname)
                self.parent_widget.emit(SIGNAL("removed_tree(QString)"),
                                        fname)
            return yes_to_all
        except EnvironmentError as error:
            action_str = _('delete')
            QMessageBox.critical(self, _("Project Explorer"),
                            _("<b>Unable to %s <i>%s</i></b>"
                              "<br><br>Error message:<br>%s"
                              ) % (action_str, fname, to_text_string(error)))
        return False
        
    def delete(self, fnames=None):
        """Delete files"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        multiple = len(fnames) > 1
        yes_to_all = None
        for fname in fnames:
            yes_to_all = self.delete_file(fname, multiple, yes_to_all)
            if yes_to_all is not None and not yes_to_all:
                # Canceled
                return

    def convert_notebook(self, fname):
        """Convert an IPython notebook to a Python script in editor"""
        try: 
            script = nbexporter().from_filename(fname)[0]
        except Exception as e:
            QMessageBox.critical(self, _('Conversion error'), 
                                 _("It was not possible to convert this "
                                 "notebook. The error is:\n\n") + \
                                 to_text_string(e))
            return
        self.parent_widget.sig_new_file.emit(script)
    
    def convert(self, fnames=None):
        """Convert IPython notebooks to Python scripts in editor"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        for fname in fnames:
            self.convert_notebook(fname)

    def rename_file(self, fname):
        """Rename file"""
        path, valid = QInputDialog.getText(self, _('Rename'),
                              _('New name:'), QLineEdit.Normal,
                              osp.basename(fname))
        if valid:
            path = osp.join(osp.dirname(fname), to_text_string(path))
            if path == fname:
                return
            if osp.exists(path):
                if QMessageBox.warning(self, _("Rename"),
                         _("Do you really want to rename <b>%s</b> and "
                           "overwrite the existing file <b>%s</b>?"
                           ) % (osp.basename(fname), osp.basename(path)),
                         QMessageBox.Yes|QMessageBox.No) == QMessageBox.No:
                    return
            try:
                misc.rename_file(fname, path)
                self.parent_widget.emit( \
                     SIGNAL("renamed(QString,QString)"), fname, path)
                return path
            except EnvironmentError as error:
                QMessageBox.critical(self, _("Rename"),
                            _("<b>Unable to rename file <i>%s</i></b>"
                              "<br><br>Error message:<br>%s"
                              ) % (osp.basename(fname), to_text_string(error)))
    
    def rename(self, fnames=None):
        """Rename files"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        if not isinstance(fnames, (tuple, list)):
            fnames = [fnames]
        for fname in fnames:
            self.rename_file(fname)
        
    def move(self, fnames=None):
        """Move files/directories"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        orig = fixpath(osp.dirname(fnames[0]))
        while True:
            self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), False)
            folder = getexistingdirectory(self, _("Select directory"), orig)
            self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), True)
            if folder:
                folder = fixpath(folder)
                if folder != orig:
                    break
            else:
                return
        for fname in fnames:
            basename = osp.basename(fname)
            try:
                misc.move_file(fname, osp.join(folder, basename))
            except EnvironmentError as error:
                QMessageBox.critical(self, _("Error"),
                                     _("<b>Unable to move <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (basename, to_text_string(error)))
        
    def create_new_folder(self, current_path, title, subtitle, is_package):
        """Create new folder"""
        if current_path is None:
            current_path = ''
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        name, valid = QInputDialog.getText(self, title, subtitle,
                                           QLineEdit.Normal, "")
        if valid:
            dirname = osp.join(current_path, to_text_string(name))
            try:
                os.mkdir(dirname)
            except EnvironmentError as error:
                QMessageBox.critical(self, title,
                                     _("<b>Unable "
                                       "to create folder <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (dirname, to_text_string(error)))
            finally:
                if is_package:
                    fname = osp.join(dirname, '__init__.py')
                    try:
                        with open(fname, 'wb') as f:
                            f.write(to_binary_string('#'))
                        return dirname
                    except EnvironmentError as error:
                        QMessageBox.critical(self, title,
                                             _("<b>Unable "
                                               "to create file <i>%s</i></b>"
                                               "<br><br>Error message:<br>%s"
                                               ) % (fname,
                                                    to_text_string(error)))

    def new_folder(self, basedir):
        """New folder"""
        title = _('New folder')
        subtitle = _('Folder name:')
        self.create_new_folder(basedir, title, subtitle, is_package=False)
    
    def new_package(self, basedir):
        """New package"""
        title = _('New package')
        subtitle = _('Package name:')
        self.create_new_folder(basedir, title, subtitle, is_package=True)
    
    def create_new_file(self, current_path, title, filters, create_func):
        """Create new file
        Returns True if successful"""
        if current_path is None:
            current_path = ''
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), False)
        fname, _selfilter = getsavefilename(self, title, current_path, filters)
        self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), True)
        if fname:
            try:
                create_func(fname)
                return fname
            except EnvironmentError as error:
                QMessageBox.critical(self, _("New file"),
                                     _("<b>Unable to create file <i>%s</i>"
                                       "</b><br><br>Error message:<br>%s"
                                       ) % (fname, to_text_string(error)))

    def new_file(self, basedir):
        """New file"""
        title = _("New file")
        filters = _("All files")+" (*)"
        def create_func(fname):
            """File creation callback"""
            if osp.splitext(fname)[1] in ('.py', '.pyw', '.ipy'):
                create_script(fname)
            else:
                with open(fname, 'wb') as f:
                    f.write(to_binary_string(''))
        fname = self.create_new_file(basedir, title, filters, create_func)
        if fname is not None:
            self.open([fname])
    
    def new_module(self, basedir):
        """New module"""
        title = _("New module")
        filters = _("Python scripts")+" (*.py *.pyw *.ipy)"
        create_func = lambda fname: self.parent_widget.emit( \
                                     SIGNAL("create_module(QString)"), fname)
        self.create_new_file(basedir, title, filters, create_func)
        
    #----- VCS actions
    def vcs_command(self, fnames, action):
        """VCS action (commit, browse)"""
        try:
            for path in sorted(fnames):
                vcs.run_vcs_tool(path, action)
        except vcs.ActionToolNotFound as error:
            msg = _("For %s support, please install one of the<br/> "
                    "following tools:<br/><br/>  %s")\
                        % (error.vcsname, ', '.join(error.tools))
            QMessageBox.critical(self, _("Error"),
                _("""<b>Unable to find external program.</b><br><br>%s""")
                    % to_text_string(msg))
        
    #----- Settings
    def get_scrollbar_position(self):
        """Return scrollbar positions"""
        return (self.horizontalScrollBar().value(),
                self.verticalScrollBar().value())
        
    def set_scrollbar_position(self, position):
        """Set scrollbar positions"""
        # Scrollbars will be restored after the expanded state
        self._scrollbar_positions = position
        if self._to_be_loaded is not None and len(self._to_be_loaded) == 0:
            self.restore_scrollbar_positions()
            
    def restore_scrollbar_positions(self):
        """Restore scrollbar positions once tree is loaded"""
        hor, ver = self._scrollbar_positions
        self.horizontalScrollBar().setValue(hor)
        self.verticalScrollBar().setValue(ver)
        
    def get_expanded_state(self):
        """Return expanded state"""
        self.save_expanded_state()
        return self.__expanded_state
    
    def set_expanded_state(self, state):
        """Set expanded state"""
        self.__expanded_state = state
        self.restore_expanded_state()
    
    def save_expanded_state(self):
        """Save all items expanded state"""
        model = self.model()
        # If model is not installed, 'model' will be None: this happens when
        # using the Project Explorer without having selected a workspace yet
        if model is not None:
            self.__expanded_state = []
            for idx in model.persistentIndexList():
                if self.isExpanded(idx):
                    self.__expanded_state.append(self.get_filename(idx))

    def restore_directory_state(self, fname):
        """Restore directory expanded state"""
        root = osp.normpath(to_text_string(fname))
        if not osp.exists(root):
            # Directory has been (re)moved outside Spyder
            return
        for basename in os.listdir(root):
            path = osp.normpath(osp.join(root, basename))
            if osp.isdir(path) and path in self.__expanded_state:
                self.__expanded_state.pop(self.__expanded_state.index(path))
                if self._to_be_loaded is None:
                    self._to_be_loaded = []
                self._to_be_loaded.append(path)
                self.setExpanded(self.get_index(path), True)
        if not self.__expanded_state:
            self.disconnect(self.fsmodel, SIGNAL('directoryLoaded(QString)'),
                            self.restore_directory_state)
                
    def follow_directories_loaded(self, fname):
        """Follow directories loaded during startup"""
        if self._to_be_loaded is None:
            return
        path = osp.normpath(to_text_string(fname))
        if path in self._to_be_loaded:
            self._to_be_loaded.remove(path)
        if self._to_be_loaded is not None and len(self._to_be_loaded) == 0:
            self.disconnect(self.fsmodel, SIGNAL('directoryLoaded(QString)'),
                            self.follow_directories_loaded)
            if self._scrollbar_positions is not None:
                # The tree view need some time to render branches:
                QTimer.singleShot(50, self.restore_scrollbar_positions)

    def restore_expanded_state(self):
        """Restore all items expanded state"""
        if self.__expanded_state is not None:
            # In the old project explorer, the expanded state was a dictionnary:
            if isinstance(self.__expanded_state, list):
                self.connect(self.fsmodel, SIGNAL('directoryLoaded(QString)'),
                             self.restore_directory_state)
                self.connect(self.fsmodel, SIGNAL('directoryLoaded(QString)'),
                             self.follow_directories_loaded)


class ProxyModel(QSortFilterProxyModel):
    """Proxy model: filters tree view"""
    def __init__(self, parent):
        super(ProxyModel, self).__init__(parent)
        self.root_path = None
        self.path_list = []
        self.setDynamicSortFilter(True)
        
    def setup_filter(self, root_path, path_list):
        """Setup proxy model filter parameters"""
        self.root_path = osp.normpath(to_text_string(root_path))
        self.path_list = [osp.normpath(to_text_string(p)) for p in path_list]
        self.invalidateFilter()

    def sort(self, column, order=Qt.AscendingOrder):
        """Reimplement Qt method"""
        self.sourceModel().sort(column, order)
        
    def filterAcceptsRow(self, row, parent_index):
        """Reimplement Qt method"""
        if self.root_path is None:
            return True
        index = self.sourceModel().index(row, 0, parent_index)
        path = osp.normpath(to_text_string(self.sourceModel().filePath(index)))
        if self.root_path.startswith(path):
            # This is necessary because parent folders need to be scanned
            return True
        else:
            for p in self.path_list:
                if path == p or path.startswith(p+os.sep):
                    return True
            else:
                return False


class FilteredDirView(DirView):
    """Filtered file/directory tree view"""
    def __init__(self, parent=None):
        super(FilteredDirView, self).__init__(parent)
        self.proxymodel = None
        self.setup_proxy_model()
        self.root_path = None
        
    #---- Model
    def setup_proxy_model(self):
        """Setup proxy model"""
        self.proxymodel = ProxyModel(self)
        self.proxymodel.setSourceModel(self.fsmodel)
        
    def install_model(self):
        """Install proxy model"""
        if self.root_path is not None:
            self.fsmodel.setNameFilters(self.name_filters)
            self.setModel(self.proxymodel)
        
    def set_root_path(self, root_path):
        """Set root path"""
        self.root_path = root_path
        self.install_model()
        index = self.fsmodel.setRootPath(root_path)
        self.setRootIndex(self.proxymodel.mapFromSource(index))
        
    def get_index(self, filename):
        """Return index associated with filename"""
        index = self.fsmodel.index(filename)
        if index.isValid() and index.model() is self.fsmodel:
            return self.proxymodel.mapFromSource(index)
        
    def set_folder_names(self, folder_names):
        """Set folder names"""
        assert self.root_path is not None
        path_list = [osp.join(self.root_path, dirname)
                     for dirname in folder_names]
        self.proxymodel.setup_filter(self.root_path, path_list)
        
    def get_filename(self, index):
        """Return filename from index"""
        if index:
            path = self.fsmodel.filePath(self.proxymodel.mapToSource(index))
            return osp.normpath(to_text_string(path))


class ExplorerTreeWidget(DirView):
    """File/directory explorer tree widget
    show_cd_only: Show current directory only
    (True/False: enable/disable the option
     None: enable the option and do not allow the user to disable it)"""
    def __init__(self, parent=None, show_cd_only=None):
        DirView.__init__(self, parent)
                
        self.history = []
        self.histindex = None

        self.show_cd_only = show_cd_only
        self.__original_root_index = None
        self.__last_folder = None

        self.menu = None
        self.common_actions = None
        
        # Enable drag events
        self.setDragEnabled(True)
        
    #---- Context menu
    def setup_common_actions(self):
        """Setup context menu common actions"""
        actions = super(ExplorerTreeWidget, self).setup_common_actions()
        if self.show_cd_only is None:
            # Enabling the 'show current directory only' option but do not
            # allow the user to disable it
            self.show_cd_only = True
        else:
            # Show current directory only
            cd_only_action = create_action(self,
                                           _("Show current directory only"),
                                           toggled=self.toggle_show_cd_only)
            cd_only_action.setChecked(self.show_cd_only)
            self.toggle_show_cd_only(self.show_cd_only)
            actions.append(cd_only_action)
        return actions
            
    def toggle_show_cd_only(self, checked):
        """Toggle show current directory only mode"""
        self.parent_widget.sig_option_changed.emit('show_cd_only', checked)
        self.show_cd_only = checked
        if checked:
            if self.__last_folder is not None:
                self.set_current_folder(self.__last_folder)
        elif self.__original_root_index is not None:
            self.setRootIndex(self.__original_root_index)
        
    #---- Refreshing widget
    def set_current_folder(self, folder):
        """Set current folder and return associated model index"""
        index = self.fsmodel.setRootPath(folder)
        self.__last_folder = folder
        if self.show_cd_only:
            if self.__original_root_index is None:
                self.__original_root_index = self.rootIndex()
            self.setRootIndex(index)
        return index
        
    def refresh(self, new_path=None, force_current=False):
        """Refresh widget
        force=False: won't refresh widget if path has not changed"""
        if new_path is None:
            new_path = getcwd()
        if force_current:
            index = self.set_current_folder(new_path)
            self.expand(index)
            self.setCurrentIndex(index)
        self.emit(SIGNAL("set_previous_enabled(bool)"),
                  self.histindex is not None and self.histindex > 0)
        self.emit(SIGNAL("set_next_enabled(bool)"),
                  self.histindex is not None and \
                  self.histindex < len(self.history)-1)
            
    #---- Events
    def directory_clicked(self, dirname):
        """Directory was just clicked"""
        self.chdir(directory=dirname)
        
    #---- Files/Directories Actions
    def go_to_parent_directory(self):
        """Go to parent directory"""
        self.chdir( osp.abspath(osp.join(getcwd(), os.pardir)) )
        
    def go_to_previous_directory(self):
        """Back to previous directory"""
        self.histindex -= 1
        self.chdir(browsing_history=True)
        
    def go_to_next_directory(self):
        """Return to next directory"""
        self.histindex += 1
        self.chdir(browsing_history=True)
        
    def update_history(self, directory):
        """Update browse history"""
        directory = osp.abspath(to_text_string(directory))
        if directory in self.history:
            self.histindex = self.history.index(directory)
        
    def chdir(self, directory=None, browsing_history=False):
        """Set directory as working directory"""
        if directory is not None:
            directory = osp.abspath(to_text_string(directory))
        if browsing_history:
            directory = self.history[self.histindex]
        elif directory in self.history:
            self.histindex = self.history.index(directory)
        else:
            if self.histindex is None:
                self.history = []
            else:
                self.history = self.history[:self.histindex+1]
            if len(self.history) == 0 or \
               (self.history and self.history[-1] != directory):
                self.history.append(directory)
            self.histindex = len(self.history)-1
        directory = to_text_string(directory)
        os.chdir(directory)
        self.parent_widget.emit(SIGNAL("open_dir(QString)"), directory)
        self.refresh(new_path=directory, force_current=True)


class ExplorerWidget(QWidget):
    """Explorer widget"""
    sig_option_changed = Signal(str, object)
    sig_open_file = Signal(str)
    sig_new_file = Signal(str)
    
    def __init__(self, parent=None, name_filters=['*.py', '*.pyw'],
                 show_all=False, show_cd_only=None, show_icontext=True):
        QWidget.__init__(self, parent)
        
        self.treewidget = ExplorerTreeWidget(self, show_cd_only=show_cd_only)
        self.treewidget.setup(name_filters=name_filters, show_all=show_all)
        self.treewidget.chdir(getcwd())
        
        icontext_action = create_action(self, _("Show icons and text"),
                                        toggled=self.toggle_icontext)
        self.treewidget.common_actions += [None, icontext_action]
        
        # Setup toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))
        
        self.previous_action = create_action(self, text=_("Previous"),
                            icon=get_std_icon("ArrowBack"),
                            triggered=self.treewidget.go_to_previous_directory)
        self.toolbar.addAction(self.previous_action)
        self.previous_action.setEnabled(False)
        self.connect(self.treewidget, SIGNAL("set_previous_enabled(bool)"),
                     self.previous_action.setEnabled)
        
        self.next_action = create_action(self, text=_("Next"),
                            icon=get_std_icon("ArrowForward"),
                            triggered=self.treewidget.go_to_next_directory)
        self.toolbar.addAction(self.next_action)
        self.next_action.setEnabled(False)
        self.connect(self.treewidget, SIGNAL("set_next_enabled(bool)"),
                     self.next_action.setEnabled)
        
        parent_action = create_action(self, text=_("Parent"),
                            icon=get_std_icon("ArrowUp"),
                            triggered=self.treewidget.go_to_parent_directory)
        self.toolbar.addAction(parent_action)
        self.toolbar.addSeparator()

        options_action = create_action(self, text='', tip=_("Options"),
                                       icon=get_icon('tooloptions.png'))
        self.toolbar.addAction(options_action)
        widget = self.toolbar.widgetForAction(options_action)
        widget.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, self.treewidget.common_actions)
        options_action.setMenu(menu)
            
        icontext_action.setChecked(show_icontext)
        self.toggle_icontext(show_icontext)     
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.treewidget)
        self.setLayout(vlayout)

    def toggle_icontext(self, state):
        """Toggle icon text"""
        self.sig_option_changed.emit('show_icontext', state)
        for action in self.toolbar.actions():
            if not action.isSeparator():
                widget = self.toolbar.widgetForAction(action)
                if state:
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                else:
                    widget.setToolButtonStyle(Qt.ToolButtonIconOnly)


class FileExplorerTest(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.explorer = ExplorerWidget(self, show_cd_only=None)
        vlayout.addWidget(self.explorer)
        
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.explorer.sig_open_file.connect(self.label1.setText)
        
        hlayout2 = QHBoxLayout()
        vlayout.addLayout(hlayout2)
        label = QLabel("<b>Open dir:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout2.addWidget(label)
        self.label2 = QLabel()
        hlayout2.addWidget(self.label2)
        self.connect(self.explorer, SIGNAL("open_dir(QString)"),
                     self.label2.setText)
        
        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)
        self.explorer.sig_option_changed.connect(
           lambda x, y: self.label3.setText('option_changed: %r, %r' % (x, y)))

        self.connect(self.explorer, SIGNAL("open_parent_dir()"),
                     lambda: self.explorer.listwidget.refresh('..'))

class ProjectExplorerTest(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        self.treewidget = FilteredDirView(self)
        self.treewidget.setup_view()
        self.treewidget.set_root_path(r'D:\Python')
        self.treewidget.set_folder_names(['spyder', 'spyder-2.0'])
        vlayout.addWidget(self.treewidget)

    
if __name__ == "__main__":
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    test = FileExplorerTest()
#    test = ProjectExplorerTest()
    test.resize(640, 480)
    test.show()
    sys.exit(app.exec_())
    

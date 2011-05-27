# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Files and Directories Explorer"""

# pylint: disable-msg=C0103
# pylint: disable-msg=R0903
# pylint: disable-msg=R0911
# pylint: disable-msg=R0201

from __future__ import with_statement

try:
    # PyQt4 4.3.3 on Windows (static DLLs) with py2exe installed:
    # -> pythoncom must be imported first, otherwise py2exe's boot_com_servers
    #    will raise an exception ("ImportError: DLL load failed [...]") when
    #    calling any of the QFileDialog static methods (getOpenFileName, ...)
    import pythoncom #@UnusedImport
except ImportError:
    pass

from spyderlib.qt.QtGui import (QVBoxLayout, QLabel, QHBoxLayout, QInputDialog,
                                QFileSystemModel, QMenu, QWidget, QToolButton,
                                QLineEdit, QMessageBox, QToolBar, QTreeView,
                                QFileDialog, QDrag, QSortFilterProxyModel)
from spyderlib.qt.QtCore import Qt, SIGNAL, QMimeData, QSize, QDir, QUrl

import os, sys, re
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout

# Local imports
from spyderlib.widgets.formlayout import fedit
from spyderlib.utils.qthelpers import get_std_icon, create_action, add_actions
from spyderlib.utils import encoding, rename_file, remove_file, programs
from spyderlib.baseconfig import _
from spyderlib.config import get_icon


def create_script(fname):
    """Create a new Python script"""
    text = os.linesep.join(["# -*- coding: utf-8 -*-", "", ""])
    encoding.write(unicode(text), fname, 'utf-8')

def listdir(path, include='.', exclude=r'\.pyc$|^\.', show_all=False,
            folders_only=False):
    """List files and directories"""
    namelist = []
    dirlist = [unicode(osp.pardir)]
    for item in os.listdir(unicode(path)):
        if re.search(exclude, item) and not show_all:
            continue
        if osp.isdir(osp.join(path, item)):
            dirlist.append(item)
        elif folders_only:
            continue
        elif re.search(include, item) or show_all:
            namelist.append(item)
    return sorted(dirlist, key=unicode.lower) + \
           sorted(namelist, key=unicode.lower)

def abspardir(path):
    """Return absolute parent dir"""
    return osp.abspath(osp.join(path, os.pardir))

def has_subdirectories(path, include, exclude, show_all):
    try:
        # > 1 because of '..'
        return len( listdir(path, include, exclude,
                            show_all, folders_only=True) ) > 1
    except (IOError, OSError):
        return False
    
def is_drive_path(path):
    path = osp.abspath(path)
    return osp.normpath(osp.join(path, osp.pardir)) == path


class DirView(QTreeView):
    def __init__(self, parent=None):
        super(DirView, self).__init__(parent)
        self.name_filters = None
        self.fsmodel = None
        self.setup_fs_model()

        self.parent_widget = parent
        self.name_filters = None
        self.valid_types = None
        self.show_all = None
                
    #---- Model
    def setup_fs_model(self):
        filters = QDir.AllDirs | QDir.Files | QDir.Drives | QDir.NoDotAndDotDot
        self.fsmodel = QFileSystemModel(self)
        self.fsmodel.setFilter(filters)
        self.fsmodel.setNameFilterDisables(False)
        
    def install_model(self):
        self.setModel(self.fsmodel)
        
    def setup_view(self):
        self.install_model()
        self.connect(self.fsmodel, SIGNAL('directoryLoaded(QString)'),
                     lambda: self.resizeColumnToContents(0))
        self.connect(self, SIGNAL('expanded(QModelIndex)'),
                     lambda: self.resizeColumnToContents(0))
        self.connect(self, SIGNAL('collapsed(QModelIndex)'),
                     lambda: self.resizeColumnToContents(0))
        
        self.setAnimated(False)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.AscendingOrder)
        
    def set_root_folder(self, folder):
        index = self.fsmodel.setRootPath(folder)
        self.setRootIndex(index)
        
    def set_name_filters(self, name_filters):
        self.name_filters = name_filters
        self.fsmodel.setNameFilters(name_filters)
        
    def set_show_all(self, state):
        if state:
            self.fsmodel.setNameFilters([])
        else:
            self.fsmodel.setNameFilters(self.name_filters)
            
    def get_filename(self):
        """Return selected filename"""
        index = self.currentIndex()
        if index:
            return osp.normpath(unicode(self.fsmodel.filePath(index)))
        
    def get_dirname(self):
        """
        Return selected directory path
        or selected filename's directory path
        """
        fname = self.get_filename()
        if osp.isdir(fname):
            return fname
        else:
            return osp.dirname(fname)
        
    #---- Tree view widget
    def setup(self, name_filters=['*.py', '*.pyw'],
              valid_types= ('.py', '.pyw'), show_all=False,
              show_cd_only=False):
        self.setup_view()
        
        self.name_filters = name_filters
        self.valid_types = valid_types
        self.show_all = show_all
        self.show_cd_only = show_cd_only
        
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
            filters = [f.strip() for f in unicode(filters).split(',')]
            self.parent_widget.emit(SIGNAL('option_changed'),
                                    'name_filters', filters)
            self.set_name_filters(filters)
            
    def toggle_all(self, checked):
        """Toggle all files mode"""
        self.parent_widget.emit(SIGNAL('option_changed'), 'show_all', checked)
        self.show_all = checked
        self.set_show_all(checked)
        
    def update_menu(self):
        """Update option menu"""
        self.menu.clear()
        actions = []
        newdir_action = create_action(self, _("New folder..."),
                                      icon="folder_new.png",
                                      triggered=self.new_folder)
        actions.append(newdir_action)
        newfile_action = create_action(self, _("New file..."),
                                       icon="filenew.png",
                                       triggered=self.new_file)
        actions.append(newfile_action)
        fname = self.get_filename()
        if fname is not None:
            is_dir = osp.isdir(fname)
            ext = osp.splitext(fname)[1]
            run_action = create_action(self, _("Run"),
                                       icon="run_small.png",
                                       triggered=self.run)
            edit_action = create_action(self, _("Edit"),
                                        icon="edit.png",
                                        triggered=self.clicked)
            delete_action = create_action(self, _("Delete..."),
                                          icon="delete.png",
                                          triggered=self.delete)
            rename_action = create_action(self, _("Rename..."),
                                          icon="rename.png",
                                          triggered=self.rename)
            browse_action = create_action(self, _("Browse"),
                                          icon=get_std_icon("CommandLink"),
                                          triggered=self.clicked)
            open_action = create_action(self, _("Open"),
                                        triggered=self.startfile)
            if ext in ('.py', '.pyw', '.ipy'):
                actions.append(run_action)
            if ext in self.valid_types or os.name != 'nt':
                actions.append(browse_action if is_dir else edit_action)
            else:
                actions.append(open_action)
            actions += [delete_action, rename_action, None]
            if is_dir and os.name == 'nt':
                # Actions specific to Windows directories
                actions.append( create_action(self,
                                              _("Open in Windows Explorer"),
                                              icon="magnifier.png",
                                              triggered=self.startfile) )
            if is_dir:
                if os.name == 'nt':
                    _title = _("Open command prompt here")
                else:
                    _title = _("Open terminal here")
                action = create_action(self, _title, icon="cmdprompt.png",
                                       triggered=lambda _fn=fname:
                                       self.parent_widget.emit(
                                       SIGNAL("open_terminal(QString)"), _fn))
                actions.append(action)
                _title = _("Open Python interpreter here")
                action = create_action(self, _title, icon="python.png",
                                   triggered=lambda _fn=fname:
                                   self.parent_widget.emit(
                                   SIGNAL("open_interpreter(QString)"), _fn))
                actions.append(action)
                if programs.is_module_installed('IPython', '0.10'):
                    _title = _("Open IPython here")
                    action = create_action(self, _title, icon="ipython.png",
                                       triggered=lambda _fn=fname:
                                       self.parent_widget.emit(
                                       SIGNAL("open_ipython(QString)"), _fn))
                    actions.append(action)
        if actions:
            actions.append(None)
        actions += self.common_actions
        add_actions(self.menu, actions)
    
    #---- Events
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
        else:
            QTreeView.keyPressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """Reimplement Qt method"""
        QTreeView.mouseDoubleClickEvent(self, event)
        self.clicked()
        
    def clicked(self):
        """Selected item was double-clicked or enter/return was pressed"""
        fname = self.get_filename()
        if fname:
            if osp.isdir(fname):
                self.directory_clicked(fname)
            else:
                self.open(fname)
                
    def directory_clicked(self, dirname):
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
        data.setUrls([QUrl(self.get_filename())])
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.exec_()
        
    #---- File/Directory actions
    def open(self, fname):
        """Open filename with the appropriate application"""
        fname = unicode(fname)
        ext = osp.splitext(fname)[1]
        if ext in self.valid_types:
            self.parent_widget.emit(SIGNAL("open_file(QString)"), fname)
        else:
            self.startfile(fname)
        
    def startfile(self, fname=None):
        """Open file in the associated application"""
        if fname is None:
            fname = self.get_filename()
        ok = programs.start_file(fname)
        if not ok:
            self.parent_widget.emit(SIGNAL("edit(QString)"), fname)
        
    def run(self):
        """Run Python script"""
        self.parent_widget.emit(SIGNAL("run(QString)"), self.get_filename())
            
    def delete(self):
        """Delete selected item"""
        fname = self.get_filename()
        if fname:
            answer = QMessageBox.warning(self, _("Delete"),
                                    _("Do you really want to delete <b>%s</b>?"
                                      ) % osp.basename(fname),
                                    QMessageBox.Yes | QMessageBox.No)
            if answer == QMessageBox.No:
                return
            try:
                if osp.isfile(fname):
                    remove_file(fname)
                else:
                    os.rmdir(fname)
                self.parent_widget.emit(SIGNAL("removed(QString)"), fname)
            except EnvironmentError, error:
                QMessageBox.critical(self, _("Delete"),
                                     _("<b>Unable to delete selected file</b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % str(error))
            finally:
                self.refresh_folder(osp.dirname(fname))
            
    def rename(self):
        """Rename selected item"""
        fname = self.get_filename()
        if fname:
            path, valid = QInputDialog.getText(self, _('Rename'),
                                               _('New name:'),
                                               QLineEdit.Normal,
                                               osp.basename(fname))
            if valid:
                path = osp.join(osp.dirname(fname), unicode(path))
                if path == fname:
                    return
                try:
                    rename_file(fname, path)
                    self.parent_widget.emit(SIGNAL("renamed(QString,QString)"),
                                             fname, path)
                except EnvironmentError, error:
                    QMessageBox.critical(self, _("Rename"),
                                    _("<b>Unable to rename selected file</b>"
                                      "<br><br>Error message:<br>%s"
                                      ) % str(error))
                finally:
                    self.refresh_folder(osp.dirname(fname))
        
    def new_folder(self):
        """Create a new folder"""
        datalist = [(_('Folder name'), ''),
                    (_('Python package'), False),]
        answer = fedit( datalist, title=_( "New folder"),
                        parent=self, icon=get_icon('spyder.svg') )
        if answer is not None:
            dirname, pack = answer
            dirname = osp.join(self.get_dirname(), dirname)
            try:
                os.mkdir(dirname)
            except EnvironmentError, error:
                QMessageBox.critical(self, _("New folder"),
                                _("<b>Unable to create folder <i>%s</i></b>"
                                  "<br><br>Error message:<br>%s"
                                  ) % (dirname, str(error)))
            finally:
                if pack:
                    create_script( osp.join(dirname, '__init__.py') )
                self.refresh_folder(osp.dirname(dirname))

    def new_file(self):
        """Create a new file"""
        _temp = sys.stdout
        sys.stdout = None
        fname = QFileDialog.getSaveFileName(self,
                                _("New Python script"), self.get_dirname(),
                                _("Python scripts")+" (*.py ; *.pyw ; *.ipy)"+\
                                "\n"+_( "All files")+" (*)")
        sys.stdout = _temp
        if unicode(fname):
            fname = unicode(fname)
            try:
                if osp.splitext(fname)[1] in ('.py', '.pyw', '.ipy'):
                    create_script(fname)
                else:
                    file(fname, 'wb').write('')
            except EnvironmentError, error:
                QMessageBox.critical(self, _("New file"),
                                     _("<b>Unable to create file <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (fname, str(error)))
            finally:
                self.refresh_folder(osp.dirname(fname))
                self.open(fname)


class ProxyModel(QSortFilterProxyModel):
    def __init__(self, parent):
        super(ProxyModel, self).__init__(parent)
        self.root_path = None
        self.path_list = []
        self.setDynamicSortFilter(True)

    def set_root_path(self, root_path):
        self.root_path = osp.normpath(unicode(root_path))
        
    def set_path_list(self, path_list):
        self.path_list = [osp.normpath(unicode(p)) for p in path_list]

    def sort(self, column, order=Qt.AscendingOrder):
        self.sourceModel().sort(column, order)
        
    def filterAcceptsRow(self, row, parent_index):
        if self.root_path is None:
            return True
        index = self.sourceModel().index(row, 0, parent_index)
        path = osp.normpath(unicode(self.sourceModel().filePath(index)))
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
    def __init__(self, parent=None):
        super(FilteredDirView, self).__init__(parent)
        self.proxymodel = None
        self.setup_proxy_model()
        self.root_path = None
        
    #---- Model
    def setup_proxy_model(self):
        self.proxymodel = ProxyModel(self)
        self.proxymodel.setSourceModel(self.fsmodel)
        
    def install_model(self):
        self.setModel(self.proxymodel)
        
    def set_root_path(self, root_path):
        self.root_path = root_path
        
    def get_index(self, filename):
        return self.proxymodel.mapFromSource(
                        self.fsmodel.setRootPath(filename))
        
    def set_folder_names(self, folder_names):
        assert self.root_path is not None
        path_list = [osp.join(self.root_path, dirname)
                     for dirname in folder_names]
        self.proxymodel.set_root_path(self.root_path)
        self.proxymodel.set_path_list(path_list)
        self.setRootIndex( self.get_index(self.root_path) )
        
    def get_filename(self):
        """Return selected filename"""
        index = self.currentIndex()
        if index:
            path = self.fsmodel.filePath(self.proxymodel.mapToSource(index))
            return osp.normpath(unicode(path))


class ExplorerTreeWidget(DirView):
    def __init__(self, parent=None):
        DirView.__init__(self, parent)
                
        self.history = []
        self.histindex = None

        self.show_cd_only = None
        self.__original_root_index = None
        self.__last_folder = None

        self.menu = None
        self.common_actions = None
        
        # Enable drag events
        self.setDragEnabled(True)
        
    #---- Context menu
    def setup_common_actions(self):
        """Setup context menu common actions"""
        # Show current directory only
        cd_only_action = create_action(self, _("Show current directory only"),
                                       toggled=self.toggle_show_cd_only)
        cd_only_action.setChecked(self.show_cd_only)
        self.toggle_show_cd_only(self.show_cd_only)
        
        actions = super(ExplorerTreeWidget, self).setup_common_actions()
        return actions+[cd_only_action]
            
    def toggle_show_cd_only(self, checked):
        """Toggle show current directory only mode"""
        self.parent_widget.emit(SIGNAL('option_changed'),
                                'show_cd_only', checked)
        self.show_cd_only = checked
        if checked:
            if self.__last_folder is not None:
                self.refresh_folder(self.__last_folder)
        elif self.__original_root_index is not None:
            self.setRootIndex(self.__original_root_index)
        
    #---- Refreshing widget
    def refresh_folder(self, folder):
        index = self.fsmodel.setRootPath(folder)
        self.__last_folder = folder
        if self.show_cd_only:
            if self.__original_root_index is None:
                self.__original_root_index = self.rootIndex()
            self.setRootIndex(index)
        return index
        
    def set_folder(self, folder, force_current=False):
        if not force_current:
            return
        index = self.refresh_folder(folder)
        self.expand(index)
        self.setCurrentIndex(index)
        
    def refresh(self, new_path=None, force_current=False):
        """
        Refresh widget
        force=False: won't refresh widget if path has not changed
        """
        if new_path is None:
            new_path = os.getcwdu()
        self.set_folder(new_path, force_current=force_current)
        self.emit(SIGNAL("set_previous_enabled(bool)"),
                  self.histindex is not None and self.histindex > 0)
        self.emit(SIGNAL("set_next_enabled(bool)"),
                  self.histindex is not None and \
                  self.histindex < len(self.history)-1)
            
    #---- Events
    def directory_clicked(self, dirname):
        self.chdir(directory=dirname)
        
    #---- Files/Directories Actions
    def go_to_parent_directory(self):
        self.chdir( osp.abspath(osp.join(os.getcwdu(), os.pardir)) )
        
    def go_to_previous_directory(self):
        """Back to previous directory"""
        self.histindex -= 1
        self.chdir(browsing_history=True)
        
    def go_to_next_directory(self):
        """Return to next directory"""
        self.histindex += 1
        self.chdir(browsing_history=True)
        
    def update_history(self, directory):
        directory = osp.abspath(unicode(directory))
        if directory in self.history:
            self.histindex = self.history.index(directory)
        
    def chdir(self, directory=None, browsing_history=False):
        """Set directory as working directory"""
        if directory is not None:
            directory = osp.abspath(unicode(directory))
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
        directory = unicode(directory)
        os.chdir(directory)
        self.parent_widget.emit(SIGNAL("open_dir(QString)"), directory)
        self.refresh(new_path=directory, force_current=True)


class ExplorerWidget(QWidget):
    """Explorer widget"""
    def __init__(self, parent=None, name_filters=['*.py', '*.pyw'],
                 valid_types=('.py', '.pyw'), show_all=False,
                 show_cd_only=False, show_toolbar=True, show_icontext=True):
        QWidget.__init__(self, parent)
        
        self.treewidget = ExplorerTreeWidget(self)
        self.treewidget.setup(name_filters=name_filters,
                              valid_types=valid_types, show_all=show_all,
                              show_cd_only=show_cd_only)
        self.treewidget.chdir(os.getcwdu())
        
        toolbar_action = create_action(self, _("Show toolbar"),
                                       toggled=self.toggle_toolbar)
        icontext_action = create_action(self, _("Show icons and text"),
                                        toggled=self.toggle_icontext)
        self.treewidget.common_actions += [None,
                                           toolbar_action, icontext_action]
        
        # Setup toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))
        
        self.previous_action = create_action(self, text=_("Previous"),
                            icon=get_icon('previous.png'),
                            triggered=self.treewidget.go_to_previous_directory)
        self.toolbar.addAction(self.previous_action)
        self.previous_action.setEnabled(False)
        self.connect(self.treewidget, SIGNAL("set_previous_enabled(bool)"),
                     self.previous_action.setEnabled)
        
        self.next_action = create_action(self, text=_("Next"),
                            icon=get_icon('next.png'),
                            triggered=self.treewidget.go_to_next_directory)
        self.toolbar.addAction(self.next_action)
        self.next_action.setEnabled(False)
        self.connect(self.treewidget, SIGNAL("set_next_enabled(bool)"),
                     self.next_action.setEnabled)
        
        parent_action = create_action(self, text=_("Parent"),
                            icon=get_icon('up.png'),
                            triggered=self.treewidget.go_to_parent_directory)
        self.toolbar.addAction(parent_action)

        options_action = create_action(self, text=_("Options"),
                    icon=get_icon('tooloptions.png'))
        self.toolbar.addAction(options_action)
        widget = self.toolbar.widgetForAction(options_action)
        widget.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self)
        add_actions(menu, self.treewidget.common_actions)
        options_action.setMenu(menu)
            
        toolbar_action.setChecked(show_toolbar)
        self.toggle_toolbar(show_toolbar)   
        icontext_action.setChecked(show_icontext)
        self.toggle_icontext(show_icontext)     
        
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.treewidget)
        self.setLayout(vlayout)
        
    def toggle_toolbar(self, state):
        """Toggle toolbar"""
        self.emit(SIGNAL('option_changed'), 'show_toolbar', state)
        self.toolbar.setVisible(state)
            
    def toggle_icontext(self, state):
        """Toggle icon text"""
        self.emit(SIGNAL('option_changed'), 'show_icontext', state)
        for action in self.toolbar.actions():
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
        self.explorer = ExplorerWidget(self)
        vlayout.addWidget(self.explorer)
        
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.connect(self.explorer, SIGNAL("open_file(QString)"),
                     self.label1.setText)
        
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
        self.connect(self.explorer, SIGNAL("option_changed"),
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
    
# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer"""

# pylint: disable=C0103

# Standard library imports
from __future__ import print_function
import os
import os.path as osp
import re
import shutil
import xml.etree.ElementTree as ElementTree

# Third party imports
from qtpy import PYQT5
from qtpy.compat import getexistingdirectory
from qtpy.QtCore import QFileInfo, Qt, Signal, Slot
from qtpy.QtWidgets import (QAbstractItemView, QFileIconProvider, QHBoxLayout,
                            QHeaderView, QInputDialog, QLabel, QLineEdit,
                            QMessageBox, QPushButton, QVBoxLayout, QWidget)

# Local imports
from spyder.config.base import _, get_image_path, STDERR
from spyder.py3compat import getcwd, pickle, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import misc
from spyder.utils.qthelpers import create_action, get_icon
from spyder.widgets.explorer import FilteredDirView, fixpath, listdir
from spyder.widgets.formlayout import fedit
from spyder.widgets.pathmanager import PathManager


def has_children_files(path, include, exclude, show_all):
    """Return True if path has children files"""
    try:
        return len( listdir(path, include, exclude, show_all) ) > 0
    except (IOError, OSError):
        return False


def is_drive_path(path):
    """Return True if path is a drive (Windows)"""
    path = osp.abspath(path)
    return osp.normpath(osp.join(path, osp.pardir)) == path


def get_dir_icon(dirname, project):
    """Return appropriate directory icon"""
    if is_drive_path(dirname):
        return ima.icon('DriveHDIcon')
    prefix = 'pp_' if dirname in project.get_pythonpath() else ''
    if dirname == project.root_path:
        if project.is_opened():
            return get_icon(prefix + 'project.png')
        else:
            return get_icon('project_closed.png')
    elif osp.isfile(osp.join(dirname, '__init__.py')):
        return get_icon(prefix + 'package.png')
    else:
        return get_icon(prefix + 'folder.png')


class Project(object):
    """Spyder project"""
    CONFIG_NAME = '.spyderproject'
    CONFIG_ATTR = ('name', 'related_projects', 'relative_pythonpath', 'opened')
    
    def __init__(self):
        self.name = None
        self.root_path = None
        self.related_projects = [] # storing project path, not project objects
        self.pythonpath = []
        self.opened = True
        self.ioerror_flag = False

    def set_root_path(self, root_path):
        """Set workspace root path"""
        if self.name is None:
            self.name = osp.basename(root_path)
        self.root_path = to_text_string(root_path)
        config_path = self.__get_project_config_path()
        if osp.exists(config_path):
            self.load()
        else:
            if not osp.isdir(self.root_path):
                os.mkdir(self.root_path)
            self.save()
            
    def rename(self, new_name):
        """Rename project and rename its root path accordingly"""
        old_name = self.name
        self.name = new_name
        pypath = self.relative_pythonpath
        self.root_path = self.root_path[:-len(old_name)]+new_name
        self.relative_pythonpath = pypath
        self.save()

    def _get_relative_pythonpath(self):
        """Return PYTHONPATH list as relative paths"""
        # Workaround to replace os.path.relpath (new in Python v2.6):
        offset = len(self.root_path)+len(os.pathsep)
        return [path[offset:] for path in self.pythonpath]

    def _set_relative_pythonpath(self, value):
        """Set PYTHONPATH list relative paths"""
        self.pythonpath = [osp.abspath(osp.join(self.root_path, path))
                           for path in value]
        
    relative_pythonpath = property(_get_relative_pythonpath,
                                   _set_relative_pythonpath)
        
    def __get_project_config_path(self):
        """Return project configuration path"""
        return osp.join(self.root_path, self.CONFIG_NAME)
        
    def load(self):
        """Load project data"""
        fname = self.__get_project_config_path()
        try:
            # Old format (Spyder 2.0-2.1 for Python 2)
            with open(fname, 'U') as fdesc:
                data = pickle.loads(fdesc.read())
        except (pickle.PickleError, TypeError, UnicodeDecodeError,
                AttributeError):
            try:
                # New format (Spyder >=2.2 for Python 2 and Python 3)
                with open(fname, 'rb') as fdesc:
                    data = pickle.loads(fdesc.read())
            except (IOError, OSError, pickle.PickleError):
                self.ioerror_flag = True
                return
        # Compatibilty with old project explorer file format:
        if 'relative_pythonpath' not in data:
            print("Warning: converting old configuration file " \
                            "for project '%s'" % data['name'], file=STDERR)
            self.pythonpath = data['pythonpath']
            data['relative_pythonpath'] = self.relative_pythonpath
        for attr in self.CONFIG_ATTR:
            setattr(self, attr, data[attr])
        self.save()
    
    def save(self):
        """Save project data"""
        data = {}
        for attr in self.CONFIG_ATTR:
            data[attr] = getattr(self, attr)
        try:
            with open(self.__get_project_config_path(), 'wb') as fdesc:
                pickle.dump(data, fdesc, 2)
        except (IOError, OSError):
            self.ioerror_flag = True
        
    def delete(self):
        """Delete project"""
        os.remove(self.__get_project_config_path())
        
    #------Misc.
    def get_related_projects(self):
        """Return related projects path list"""
        return self.related_projects
    
    def set_related_projects(self, related_projects):
        """Set related projects"""
        self.related_projects = related_projects
        self.save()
        
    def open(self):
        """Open project"""
        self.opened = True
        self.save()
        
    def close(self):
        """Close project"""
        self.opened = False
        self.save()
        
    def is_opened(self):
        """Return True if project is opened"""
        return self.opened
    
    def is_file_in_project(self, fname):
        """Return True if file *fname* is in one of the project subfolders"""
        fixed_root = fixpath(self.root_path)
        return fixpath(fname) == fixed_root \
               or fixpath(osp.dirname(fname)).startswith(fixed_root)
               
    def is_root_path(self, dirname):
        """Return True if dirname is project's root path"""
        return fixpath(dirname) == fixpath(self.root_path)
    
    def is_in_pythonpath(self, dirname):
        """Return True if dirname is in project's PYTHONPATH"""
        return fixpath(dirname) in [fixpath(_p) for _p in self.pythonpath]
        
    #------Python Path
    def get_pythonpath(self):
        """Return a copy of pythonpath attribute"""
        return self.pythonpath[:]
    
    def set_pythonpath(self, pythonpath):
        """Set project's PYTHONPATH"""
        self.pythonpath = pythonpath
        self.save()
        
    def remove_from_pythonpath(self, path):
        """Remove path from project's PYTHONPATH
        Return True if path was removed, False if it was not found"""
        pathlist = self.get_pythonpath()
        if path in pathlist:
            pathlist.pop(pathlist.index(path))
            self.set_pythonpath(pathlist)
            return True
        else:
            return False
        
    def add_to_pythonpath(self, path):
        """Add path to project's PYTHONPATH
        Return True if path was added, False if it was already there"""
        pathlist = self.get_pythonpath()
        if path in pathlist:
            return False
        else:
            pathlist.insert(0, path)
            self.set_pythonpath(pathlist)
            return True


class Workspace(object):
    """Spyder workspace
    Set of projects with common root path parent directory"""
    CONFIG_NAME = '.spyderworkspace'
    CONFIG_ATTR = ('name', 'project_paths', )
    
    def __init__(self):
        self.name = None
        self.root_path = None
        self.projects = []
        self.ioerror_flag = False
        
    def _get_project_paths(self):
        """Return workspace projects root path list"""
        # Convert project absolute paths to paths relative to Workspace root
        offset = len(self.root_path)+len(os.pathsep)
        return [proj.root_path[offset:] for proj in self.projects]

    def _set_project_paths(self, pathlist):
        """Set workspace projects root path list"""
        # Convert paths relative to Workspace root to project absolute paths
        for path in pathlist:
            if path.startswith(self.root_path):
                # do nothing, this is the old Workspace format
                root_path = path
            else:
                root_path = osp.join(self.root_path, path)
            self.add_project(root_path)
            
    project_paths = property(_get_project_paths, _set_project_paths)
    
    def is_valid(self):
        """Return True if workspace is valid (i.e. root path is defined)"""
        return self.root_path is not None and osp.isdir(self.root_path)
    
    def is_empty(self):
        """Return True if workspace is empty (i.e. no project)"""
        if not self.is_valid():
            return
        return len(self.projects) == 0

    def set_root_path(self, root_path):
        """Set workspace root path"""
        if self.name is None:
            self.name = osp.basename(root_path)
        self.root_path = to_text_string(osp.abspath(root_path))
        config_path = self.__get_workspace_config_path()
        if osp.exists(config_path):
            self.load()
        else:
            self.save()
            
    def set_name(self, name):
        """Set workspace name"""
        self.name = name
        self.save()
        
    def __get_workspace_config_path(self):
        """Return project configuration path"""
        return osp.join(self.root_path, self.CONFIG_NAME)
        
    def load(self):
        """Load workspace data"""
        fname = self.__get_workspace_config_path()
        try:
            # Old format (Spyder 2.0-2.1 for Python 2)
            with open(fname, 'U') as fdesc:
                data = pickle.loads(fdesc.read())
        except (pickle.PickleError, TypeError, UnicodeDecodeError):
            try:
                # New format (Spyder >=2.2 for Python 2 and Python 3)
                with open(fname, 'rb') as fdesc:
                    data = pickle.loads(fdesc.read())
            except (IOError, OSError, pickle.PickleError):
                self.ioerror_flag = True
                return
        for attr in self.CONFIG_ATTR:
            setattr(self, attr, data[attr])
        self.save()
    
    def save(self):
        """Save workspace data"""
        data = {}
        for attr in self.CONFIG_ATTR:
            data[attr] = getattr(self, attr)
        try:
            with open(self.__get_workspace_config_path(), 'wb') as fdesc:
                pickle.dump(data, fdesc, 2)
        except (IOError, OSError):
            self.ioerror_flag = True
        
    def delete(self):
        """Delete workspace"""
        os.remove(self.__get_workspace_config_path())
        
    #------Misc.
    def get_ioerror_warning_message(self):
        """Return a warning message if IOError exception was raised when 
        loading/saving the workspace or one of its projects"""
        txt = ""
        projlist = [_p.name for _p in self.projects if _p.ioerror_flag]
        if self.ioerror_flag:
            txt += _("its own configuration file")
            if projlist:
                txt += _(" and ")
            else:
                txt += "."
        if projlist:
            txt += _("the following projects:<br>%s") % ", ".join(projlist)
        return txt
        
    def is_file_in_workspace(self, fname):
        """Return True if file *fname* is in one of the projects"""
        return any([proj.is_file_in_project(fname) for proj in self.projects])
        
    def is_file_in_closed_project(self, fname):
        """Return True if file *fname* is in one of the closed projects"""
        return any([proj.is_file_in_project(fname) for proj in self.projects
                    if not proj.is_opened()])
    
    def is_in_pythonpath(self, dirname):
        """Return True if dirname is in workspace's PYTHONPATH"""
        return any([proj.is_in_pythonpath(dirname) for proj in self.projects])
    
    def has_project(self, root_path_or_name):
        """Return True if workspace has a project
        with given root path or name"""
        checklist = [project.root_path for project in self.projects
                     ]+[project.name for project in self.projects]
        return root_path_or_name in checklist

    def get_source_project(self, fname):
        """Return project which contains source *fname*"""
        for project in self.projects:
            if project.is_file_in_project(fname):
                return project
        
    def get_project_from_name(self, name):
        """Return project's object from name"""
        for project in self.projects:
            if project.name == name:
                return project

    def get_folder_names(self):
        """Return all project folder names (root path basename)"""
        return [osp.basename(proj.root_path) for proj in self.projects]
        
    def add_project(self, root_path):
        """Create project from root path, add it to workspace
        Return the created project instance"""
        project = Project()
        try:
            project.set_root_path(root_path)
        except OSError:
            #  This may happens when loading a Workspace with absolute paths
            #  which has just been moved to a different location
            return
        self.projects.append(project)
        self.save()
        
    def open_projects(self, projects, open_related=True):
        """Open projects"""
        for project in projects:
            project.open()
            related_projects = project.get_related_projects()
            if open_related:
                for projname in related_projects:
                    for relproj in self.projects:
                        if relproj.name == projname:
                            self.open_projects(relproj, open_related=False)
        self.save()
        
    def close_projects(self, projects):
        """Close projects"""
        for project in projects:
            project.close()
        self.save()
        
    def remove_projects(self, projects):
        """Remove projects"""
        for project in projects:
            project.delete()
            self.projects.pop(self.projects.index(project))
        self.save()
        
    def close_unrelated_projects(self, projects):
        """Close unrelated projects"""
        unrelated_projects = []
        for project in projects:
            for proj in self.projects:
                if proj is project:
                    continue
                if proj.name in project.get_related_projects():
                    continue
                if project.name in proj.get_related_projects():
                    continue
                unrelated_projects.append(proj)
        self.close_projects(unrelated_projects)
        self.save()
        return unrelated_projects
        
    def rename_project(self, project, new_name):
        """Rename project, update the related projects if necessary"""
        old_name = project.name
        for proj in self.projects:
            relproj = proj.get_related_projects()
            if old_name in relproj:
                relproj[relproj.index(old_name)] = new_name
                proj.set_related_projects(relproj)
        project.rename(new_name)
        self.save()
        
    def get_other_projects(self, project):
        """Return all projects, except given project"""
        return [_p for _p in self.projects if _p is not project]
        
    #------Python Path
    def get_pythonpath(self):
        """Return global PYTHONPATH (for all opened projects"""
        pythonpath = []
        for project in self.projects:
            if project.is_opened():
                pythonpath += project.get_pythonpath()
        return pythonpath


def get_pydev_project_infos(project_path):
    """Return Pydev project infos: name, related projects and PYTHONPATH"""
    root = ElementTree.parse(osp.join(project_path, ".pydevproject"))
    path = []
    project_root = osp.dirname(project_path)
    for element in root.getiterator():
        if element.tag == 'path':
            path.append(osp.abspath(osp.join(project_root, element.text[1:])))

    root = ElementTree.parse(osp.join(project_path, ".project"))
    related_projects = []
    name = None
    for element in root.getiterator():
        if element.tag == 'project':
            related_projects.append(element.text)
        elif element.tag == 'name' and name is None:
            name = element.text
            
    return name, related_projects, path


class IconProvider(QFileIconProvider):
    """Project tree widget icon provider"""
    def __init__(self, treeview):
        super(IconProvider, self).__init__()
        self.treeview = treeview
        
    @Slot(int)
    @Slot(QFileInfo)
    def icon(self, icontype_or_qfileinfo):
        """Reimplement Qt method"""
        if isinstance(icontype_or_qfileinfo, QFileIconProvider.IconType):
            return super(IconProvider, self).icon(icontype_or_qfileinfo)
        else:
            qfileinfo = icontype_or_qfileinfo
            fname = osp.normpath(to_text_string(qfileinfo.absoluteFilePath()))
            if osp.isdir(fname):
                return ima.icon('DirOpenIcon')
            else:
                return ima.icon('FileIcon')


class ExplorerTreeWidget(FilteredDirView):
    """Explorer tree widget"""

    def __init__(self, parent, show_hscrollbar=True):
        FilteredDirView.__init__(self, parent)
        self.fsmodel.modelReset.connect(self.reset_icon_provider)
        self.reset_icon_provider()
        self.last_folder = None
        self.setSelectionMode(FilteredDirView.ExtendedSelection)
        self.setHeaderHidden(True)
        self.show_hscrollbar = show_hscrollbar

        # Enable drag & drop events
        self.setDragEnabled(True)
        self.setDragDropMode(FilteredDirView.DragDrop)

    #------DirView API---------------------------------------------------------
    def setup_view(self):
        """Setup view"""
        FilteredDirView.setup_view(self)

    def create_context_menu_actions(self):
        """Reimplement DirView method"""
        return FilteredDirView.create_context_menu_actions(self)

    def setup_common_actions(self):
        """Setup context menu common actions"""
        actions = FilteredDirView.setup_common_actions(self)

        # Toggle horizontal scrollbar
        hscrollbar_action = create_action(self, _("Show horizontal scrollbar"),
                                          toggled=self.toggle_hscrollbar)
        hscrollbar_action.setChecked(self.show_hscrollbar)
        self.toggle_hscrollbar(self.show_hscrollbar)

        return actions + [hscrollbar_action]

    #------Public API----------------------------------------------------------
    @Slot(bool)
    def toggle_hscrollbar(self, checked):
        """Toggle horizontal scrollbar"""
        self.parent_widget.sig_option_changed.emit('show_hscrollbar', checked)
        self.show_hscrollbar = checked
        self.header().setStretchLastSection(not checked)
        self.header().setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        if PYQT5:
            self.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        else:
            self.header().setResizeMode(QHeaderView.ResizeToContents)

    def reset_icon_provider(self):
        """Reset file system model icon provider
        The purpose of this is to refresh files/directories icons"""
        self.fsmodel.setIconProvider(IconProvider(self))

    def get_pythonpath(self):
        """Return global PYTHONPATH (for all opened projects"""
        # FIXME!!
        return []
    
    def show_properties(self, fnames):
        """Show properties"""
        pathlist = sorted(fnames)
        dirlist = [path for path in pathlist if osp.isdir(path)]
        for path in pathlist[:]:
            for folder in dirlist:
                if path != folder and path.startswith(folder):
                    pathlist.pop(pathlist.index(path))
        files, lines = 0, 0
        for path in pathlist:
            f, l = misc.count_lines(path)
            files += f
            lines += l
        QMessageBox.information(self, _("Project Explorer"),
                                _("Statistics on source files only:<br>"
                                  "(Python, Cython, IPython, Enaml,"
                                  "C/C++, Fortran)<br><br>"
                                  "<b>%s</b> files.<br>"
                                  "<b>%s</b> lines of code."
                                  ) % (str(files), str(lines)))
            
    #---- Internal drag & drop
    def dragMoveEvent(self, event):
        """Reimplement Qt method"""
        index = self.indexAt(event.pos())
        if index:
            dst = self.get_filename(index)
            if osp.isdir(dst):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Reimplement Qt method"""
        event.ignore()
        action = event.dropAction()
        if action not in (Qt.MoveAction, Qt.CopyAction):
            return
        
#        # QTreeView must not remove the source items even in MoveAction mode:
#        event.setDropAction(Qt.CopyAction)
        
        dst = self.get_filename(self.indexAt(event.pos()))
        yes_to_all, no_to_all = None, None
        src_list = [to_text_string(url.toString())
                    for url in event.mimeData().urls()]
        if len(src_list) > 1:
            buttons = QMessageBox.Yes|QMessageBox.YesAll| \
                      QMessageBox.No|QMessageBox.NoAll|QMessageBox.Cancel
        else:
            buttons = QMessageBox.Yes|QMessageBox.No
        for src in src_list:
            if src == dst:
                continue
            dst_fname = osp.join(dst, osp.basename(src))
            if osp.exists(dst_fname):
                if yes_to_all is not None or no_to_all is not None:
                    if no_to_all:
                        continue
                elif osp.isfile(dst_fname):
                    answer = QMessageBox.warning(self, _('Project explorer'),
                              _('File <b>%s</b> already exists.<br>'
                                'Do you want to overwrite it?') % dst_fname,
                              buttons)
                    if answer == QMessageBox.No:
                        continue
                    elif answer == QMessageBox.Cancel:
                        break
                    elif answer == QMessageBox.YesAll:
                        yes_to_all = True
                    elif answer == QMessageBox.NoAll:
                        no_to_all = True
                        continue
                else:
                    QMessageBox.critical(self, _('Project explorer'),
                                         _('Folder <b>%s</b> already exists.'
                                           ) % dst_fname, QMessageBox.Ok)
                    event.setDropAction(Qt.CopyAction)
                    return
            try:
                if action == Qt.CopyAction:
                    if osp.isfile(src):
                        shutil.copy(src, dst)
                    else:
                        shutil.copytree(src, dst)
                else:
                    if osp.isfile(src):
                        misc.move_file(src, dst)
                    else:
                        shutil.move(src, dst)
                    self.parent_widget.removed.emit(src)
            except EnvironmentError as error:
                if action == Qt.CopyAction:
                    action_str = _('copy')
                else:
                    action_str = _('move')
                QMessageBox.critical(self, _("Project Explorer"),
                                     _("<b>Unable to %s <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (action_str, src,
                                            to_text_string(error)))


class ProjectExplorerWidget(QWidget):
    """Project Explorer"""
    sig_option_changed = Signal(str, object)
    sig_open_file = Signal(str)
    pythonpath_changed = Signal()

    def __init__(self, parent, name_filters=['*.py', '*.pyw'],
                 show_all=False, show_hscrollbar=True):
        QWidget.__init__(self, parent)
        self.treewidget = None
        self.setup_layout(name_filters, show_all, show_hscrollbar)
        
    def setup_layout(self, name_filters, show_all, show_hscrollbar):
        """Setup project explorer widget layout"""

        self.treewidget = ExplorerTreeWidget(self, show_hscrollbar=show_hscrollbar)
        self.treewidget.setup(name_filters=name_filters, show_all=show_all)
        self.treewidget.setup_view()

        # FIXME!!
        self.treewidget.set_root_path(osp.dirname(osp.abspath(__file__)))
        self.treewidget.set_folder_names(['variableexplorer'])
        self.treewidget.setup_project_view()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

    def check_for_io_errors(self):
        """Check for I/O errors that may occured when loading/saving 
        projects or the workspace itself and warn the user"""
        self.treewidget.check_for_io_errors()

    def closing_widget(self):
        """Perform actions before widget is closed"""
        pass

    def get_pythonpath(self):
        """Return PYTHONPATH"""
        return self.treewidget.get_pythonpath()


#==============================================================================
# Tests
#==============================================================================
class Test(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        self.explorer = ProjectExplorerWidget(None, show_all=True)
        vlayout.addWidget(self.explorer)
        
        hlayout1 = QHBoxLayout()
        vlayout.addLayout(hlayout1)
        label = QLabel("<b>Open file:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout1.addWidget(label)
        self.label1 = QLabel()
        hlayout1.addWidget(self.label1)
        self.explorer.sig_open_file.connect(self.label1.setText)
        
        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)
        self.explorer.sig_option_changed.connect(
           lambda x, y: self.label3.setText('option_changed: %r, %r' % (x, y)))


def test():
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    test = Test()
    test.resize(250, 480)
    test.show()
    app.exec_()


if __name__ == "__main__":
    test()
